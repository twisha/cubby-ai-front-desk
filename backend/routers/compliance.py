"""GET /api/compliance, POST /api/acknowledge — the roster side of the loop.

Deterministic spine: scheduler.py computes every row; this router only moves
data. No LLM anywhere in this file.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core.rules.scheduler import compliance_row, urgency_sort_key
from backend.core.store.repo import Store
from backend.deps import get_store
from backend.models.roster import ComplianceRow

router = APIRouter(prefix="/api", tags=["compliance"])


class AcknowledgeRequest(BaseModel):
    child_id: str
    appt_date: date


@router.get("/compliance", response_model=list[ComplianceRow])
def compliance(store: Store = Depends(get_store)) -> list[ComplianceRow]:
    today = date.today()
    rows = [compliance_row(c, today) for c in store.list_children()]
    rows.sort(key=urgency_sort_key)
    return rows


@router.post("/acknowledge", response_model=ComplianceRow)
def acknowledge(
    req: AcknowledgeRequest, store: Store = Depends(get_store)
) -> ComplianceRow:
    child = store.get_child(req.child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")

    updated = child.model_copy(
        update={
            "parent_state": "due_soon_acknowledged",
            "acknowledged_appt_date": req.appt_date,
        }
    )
    store.upsert_child(updated)
    return compliance_row(updated, date.today())
