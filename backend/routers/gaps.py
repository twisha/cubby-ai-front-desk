"""GET /api/gaps — read-only grouped view of unanswered (GAP-mode) questions.

Pure read over the question log; no LLM call, so this stays outside the
cost guard (same reasoning as /api/compliance).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.rules.gaps import group_gaps
from backend.core.store.repo import Store
from backend.deps import get_store
from backend.models.ask import GapGroup

router = APIRouter(prefix="/api", tags=["gaps"])


@router.get("/gaps", response_model=list[GapGroup])
def gaps(store: Store = Depends(get_store)) -> list[GapGroup]:
    return group_gaps(store.list_questions())
