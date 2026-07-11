"""POST /api/ask — grounded parent Q&A.

Flow (the deterministic spine):
  question
   -> retriever.search  ->  (sections ordered by relevance, max_score)
   -> if max_score < retriever.gap_threshold: skip the LLM, log GAP, hand off
   -> else: answer engine (Haiku, full-context) -> AnswerResponse
   -> routing.route(resp) -> AnswerMode          (CODE decides the UI mode)
   -> log the question with mode + score + sources
   -> return the shaped response
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.config import CONFIG
from backend.core.llm.answer import answer_question
from backend.core.retrieval.index import Retriever
from backend.core.rules.routing import detect_sensitive, route
from backend.core.store.repo import Store
from backend.deps import get_retriever, get_store
from backend.models.ask import AnswerMode, QuestionLog

router = APIRouter(prefix="/api", tags=["ask"])


class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    id: str
    title: str
    content: str


class AskResponse(BaseModel):
    answer: str
    mode: AnswerMode
    confidence: str | None = None
    sources: list[Source] = []
    max_score: float
    needs_human_judgment: bool = False
    sensitive: bool = False


def _handoff_text(mode: AnswerMode) -> str:
    who = CONFIG.director_name
    if mode is AnswerMode.ESCALATED:
        return (
            "This one needs a person, not an app. I've passed it straight to "
            f"{who} (director) — she'll follow up with you directly."
        )
    # GAP
    return (
        "I don't have that in the handbook yet — I've sent it to "
        f"{who} (director). Typical reply is under 15 minutes."
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    retriever: Retriever = Depends(get_retriever),
    store: Store = Depends(get_store),
) -> AskResponse:
    question = req.question.strip()

    # Sensitive-topic pre-check runs BEFORE retrieval. Custody/injury/abuse/
    # staff-complaint/billing-dispute questions have ~zero handbook content
    # overlap by design, so the retrieval gap-gate can't be trusted to let
    # them through to the model — this deterministic check is the backstop.
    if detect_sensitive(question):
        return _log_and_shape(
            store, question, AnswerMode.ESCALATED, 0.0,
            answer=_handoff_text(AnswerMode.ESCALATED), sources=[], sensitive=True,
        )

    ordered, max_score = retriever.search(question)

    # Gap gate — decided by CODE, before the LLM runs. Sub-threshold means no
    # relevant source: skip the model entirely (cost + latency + zero fabrication).
    if max_score < retriever.gap_threshold:
        resp = _log_and_shape(
            store, question, AnswerMode.GAP, max_score,
            answer=_handoff_text(AnswerMode.GAP), sources=[],
        )
        return resp

    # Full-context grounding: hand the model every section, ordered by score.
    try:
        ar = answer_question(question, ordered)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    mode = route(ar)

    if mode in (AnswerMode.GAP, AnswerMode.ESCALATED):
        answer = _handoff_text(mode)
        sources: list[Source] = []
    else:  # GROUNDED or JUDGMENT — show the answer + cited sections
        answer = ar.answer
        by_id = {e.id: e for e in ordered}
        sources = [
            Source(id=e.id, title=e.title, content=e.content)
            for sid in ar.source_ids
            if (e := by_id.get(sid))
        ]

    return _log_and_shape(
        store, question, mode, max_score, answer=answer, sources=sources,
        confidence=ar.confidence, needs_human_judgment=ar.needs_human_judgment,
        sensitive=ar.sensitive,
    )


def _log_and_shape(
    store: Store, question: str, mode: AnswerMode, max_score: float, *,
    answer: str, sources: list[Source], confidence: str | None = None,
    needs_human_judgment: bool = False, sensitive: bool = False,
) -> AskResponse:
    store.add_question(QuestionLog(
        id=uuid.uuid4().hex[:8], ts=datetime.now(), text=question, mode=mode,
        max_cosine=round(max_score, 3), source_ids=[s.id for s in sources],
        answer=answer if mode in (AnswerMode.GROUNDED, AnswerMode.JUDGMENT) else None,
    ))
    return AskResponse(
        answer=answer, mode=mode, confidence=confidence, sources=sources,
        max_score=round(max_score, 3), needs_human_judgment=needs_human_judgment,
        sensitive=sensitive,
    )
