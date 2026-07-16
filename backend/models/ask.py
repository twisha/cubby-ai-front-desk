"""Q&A models. The LLM returns AnswerResponse; CODE maps it to AnswerMode."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AnswerResponse(BaseModel):
    """LLM structured output for /api/ask. The model fills these fields;
    it never decides the UI mode — routing.py does, from this object."""
    answer: str
    source_ids: list[str]                 # handbook entry ids actually used; [] if none
    confidence: Literal["high", "medium", "low"]
    category: str
    needs_human_judgment: bool            # policy answerable but the decision isn't
    sensitive: bool                       # custody, injury, allegation, billing dispute, staff complaint


class AnswerMode(str, Enum):
    """Decided by CODE, not the model (see core/rules/routing.py)."""
    GROUNDED = "grounded"                 # answer + citation chips
    JUDGMENT = "judgment"                 # answer policy + flag for director
    ESCALATED = "escalated"               # no AI answer; routed to human
    GAP = "gap"                           # no relevant source; logged as knowledge gap


class QuestionLog(BaseModel):
    """A logged question with the signals the operator 'struggled' view needs."""
    id: str
    ts: datetime
    text: str
    mode: AnswerMode
    max_cosine: float                     # retrieval score (keyword-overlap proxy in M0)
    source_ids: list[str] = Field(default_factory=list)
    answer: str | None = None
    thumb: Literal["up", "down"] | None = None
    judge_flag: bool = False              # sampled Sonnet groundedness check failed


class GapCategory(str, Enum):
    """Read-only classification computed at reporting time in
    core/rules/gaps.py. Never touches AnswerMode or the parent-facing
    response -- it's purely a sharper lens the operator gets over the same
    GAP-mode question log, so a genuine content gap doesn't get buried next
    to gibberish or an off-topic question the handbook could never answer."""
    CONTENT_GAP = "content_gap"           # coherent, plausibly in-domain -- actionable
    OFF_TOPIC = "off_topic"               # coherent English, unrelated to a childcare center
    UNCLEAR = "unclear"                   # not real language (or too little signal to tell)


class GapGroup(BaseModel):
    """A cluster of GAP-mode questions sharing a keyword (core/rules/gaps.py).
    Read-only for M0.4b -- no draft/approve action attached yet (that's M3's
    live flywheel, layered on top of this same grouping)."""
    theme: str
    category: GapCategory
    count: int
    questions: list[QuestionLog]
