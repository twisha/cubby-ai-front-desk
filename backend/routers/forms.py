"""POST /api/validate-form — the front-desk vision-scan flow.

photo -> extract (Sonnet vision) -> match child by name (store) -> validate
(deterministic) -> on accepted, update the roster, closing the loop back
into the compliance dashboard/scheduler built in M0.3.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.core.llm.extract import extract_form
from backend.core.rules.validation import validate
from backend.core.store.repo import Store
from backend.deps import get_store
from backend.models.forms import ValidationResult

router = APIRouter(prefix="/api", tags=["forms"])

_MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB — upload-safety cap


@router.post("/validate-form", response_model=ValidationResult)
async def validate_form(
    photo: UploadFile = File(...),
    store: Store = Depends(get_store),
) -> ValidationResult:
    if not (photo.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    data = await photo.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 8 MB).")

    try:
        extraction = extract_form(data, media_type=photo.content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    child = store.match_child_by_name(extraction.child_name) if extraction.child_name else None
    result = validate(extraction, child, date.today())

    if result.status == "accepted" and child is not None:
        updated = child.model_copy(update={
            "last_exam_date": extraction.date_of_exam,
            "parent_state": "compliant",
            "acknowledged_appt_date": None,
        })
        store.upsert_child(updated)

    return result
