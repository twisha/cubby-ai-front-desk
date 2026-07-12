"""POST /api/validate-form — the bulk front-desk vision-scan flow.

Each photo -> extract (Sonnet vision) -> match child by name (store) ->
validate (deterministic). Accepted scans update the roster directly. Rejected
and needs_review scans are persisted as FlaggedForm so they surface on the
Dashboard's "Needs attention" list instead of vanishing once the upload
response is dismissed — the operator's job is to watch the dashboard, not
review each scan one at a time.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from backend.core.llm.extract import extract_form
from backend.core.rules.validation import validate
from backend.core.security.cost_guard import check_batch_budget
from backend.core.store.repo import Store
from backend.deps import get_store
from backend.models.forms import (
    BatchScanItem,
    FlaggedForm,
    ValidationIssue,
    ValidationResult,
)

router = APIRouter(prefix="/api", tags=["forms"])

_MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB per photo — upload-safety cap
_MAX_BATCH_FILES = 20                 # bounds worst-case cost per request


@router.post("/validate-form", response_model=list[BatchScanItem])
async def validate_form(
    request: Request,
    photos: list[UploadFile] = File(...),
    store: Store = Depends(get_store),
) -> list[BatchScanItem]:
    if len(photos) > _MAX_BATCH_FILES:
        raise HTTPException(
            status_code=413, detail=f"Max {_MAX_BATCH_FILES} forms per batch."
        )

    ip = request.client.host if request.client else "unknown"
    check_batch_budget(ip, len(photos))  # fail CLOSED before any LLM call

    items: list[BatchScanItem] = []
    for photo in photos:
        if not (photo.content_type or "").startswith("image/"):
            items.append(_skip(photo.filename, "Not an image file.", "Upload a photo of the form."))
            continue

        data = await photo.read()
        if len(data) > _MAX_UPLOAD_BYTES:
            items.append(_skip(photo.filename, "Image is too large (max 8 MB).", "Re-scan under 8 MB."))
            continue

        try:
            extraction = extract_form(data, media_type=photo.content_type)
        except RuntimeError as e:
            items.append(_skip(photo.filename, str(e), "Re-scan in a moment."))
            continue

        child = store.match_child_by_name(extraction.child_name) if extraction.child_name else None
        result = validate(extraction, child, date.today())

        if result.status == "accepted" and child is not None:
            updated = child.model_copy(update={
                "last_exam_date": extraction.date_of_exam,
                "parent_state": "compliant",
                "acknowledged_appt_date": None,
            })
            store.upsert_child(updated)
        else:
            store.add_flagged_form(FlaggedForm(
                id=str(uuid.uuid4()),
                child_id=child.id if child else None,
                child_name=child.name if child else None,
                parent_name=child.parent_name if child else None,
                status=result.status,
                issues=result.issues,
                scanned_at=datetime.now(timezone.utc),
                extraction=extraction,
            ))

        items.append(BatchScanItem(
            filename=photo.filename or "unknown",
            child_name=child.name if child else extraction.child_name,
            result=result,
        ))

    return items


def _skip(filename: str | None, problem: str, fix: str) -> BatchScanItem:
    return BatchScanItem(
        filename=filename or "unknown",
        child_name=None,
        result=ValidationResult(
            status="needs_review",
            issues=[ValidationIssue(field="file", problem=problem, fix=fix)],
            next_due_date=None,
        ),
    )


@router.get("/flagged-forms", response_model=list[FlaggedForm])
def flagged_forms(store: Store = Depends(get_store)) -> list[FlaggedForm]:
    return store.list_flagged_forms()


@router.post("/flagged-forms/{flag_id}/notify", response_model=FlaggedForm)
def notify_parent(flag_id: str, store: Store = Depends(get_store)) -> FlaggedForm:
    updated = store.mark_notified(flag_id, datetime.now(timezone.utc))
    if updated is None:
        raise HTTPException(status_code=404, detail="Flagged form not found")
    return updated


class AssignRequest(BaseModel):
    child_id: str


class AssignResult(BaseModel):
    resolved: bool                 # True -> accepted, roster updated, gone from the queue
    flagged: FlaggedForm | None    # the updated entry, if still flagged
    next_due_date: date | None = None


@router.post("/flagged-forms/{flag_id}/assign", response_model=AssignResult)
def assign_child(
    flag_id: str, req: AssignRequest, store: Store = Depends(get_store)
) -> AssignResult:
    """Resolve an unmatched scan (illegible/unrecognized name) by picking the
    right child from the roster -- re-validates the SAME extracted data now
    that the child is known, no re-scan needed. Mirrors validate_form's
    accept/flag branching exactly, just entered from a different starting
    point (a known extraction + a manually-supplied child instead of a fresh
    photo + name match)."""
    flagged = store.get_flagged_form(flag_id)
    if flagged is None:
        raise HTTPException(status_code=404, detail="Flagged form not found")
    child = store.get_child(req.child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")

    result = validate(flagged.extraction, child, date.today())

    if result.status == "accepted":
        updated_child = child.model_copy(update={
            "last_exam_date": flagged.extraction.date_of_exam,
            "parent_state": "compliant",
            "acknowledged_appt_date": None,
        })
        store.upsert_child(updated_child)
        store.remove_flagged_form(flag_id)
        return AssignResult(resolved=True, flagged=None, next_due_date=result.next_due_date)

    updated = flagged.model_copy(update={
        "child_id": child.id,
        "child_name": child.name,
        "parent_name": child.parent_name,
        "status": result.status,
        "issues": result.issues,
    })
    store.add_flagged_form(updated)
    return AssignResult(resolved=False, flagged=updated)
