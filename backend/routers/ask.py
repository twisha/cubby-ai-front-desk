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
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from langsmith import get_current_run_tree, traceable
from pydantic import BaseModel

from backend.config import CONFIG
from backend.core.llm.answer import answer_question
from backend.core.retrieval.index import Retriever
from backend.core.rules.business_hours import (
    HOURS_LABEL,
    is_business_hours,
    next_business_day_label,
)
from backend.core.rules.routing import detect_courtesy, detect_sensitive, route
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


def _handoff_text(mode: AnswerMode, now: datetime | None = None) -> str:
    """`now` is accepted explicitly (never reads the clock internally) so
    this stays trivially unit-testable — same convention as scheduler.py's
    `today` parameter. Never promise a real-time reply outside business
    hours; that's exactly the kind of false comfort this app exists to
    eliminate."""
    who = CONFIG.director_name
    now = now or datetime.now(timezone.utc)
    open_now = is_business_hours(now)

    if mode is AnswerMode.ESCALATED:
        if open_now:
            return (
                "This needs to go directly to a person — I've flagged it for "
                f"{who} (director) right away. She'll follow up with you directly."
            )
        return (
            "This needs to go directly to a person — I've flagged it for "
            f"{who} (director) right away. We're closed right now, but she'll "
            f"see this first thing when we reopen {next_business_day_label(now)}."
        )

    # GAP
    if open_now:
        return (
            "I don't have that in the handbook yet — I've sent it to "
            f"{who} (director). Typical reply is under 15 minutes."
        )
    return (
        "I don't have that in the handbook yet — I've sent it to "
        f"{who} (director). We're closed right now ({HOURS_LABEL}), so she'll "
        f"get back to you {next_business_day_label(now)}."
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    retriever: Retriever = Depends(get_retriever),
    store: Store = Depends(get_store),
) -> AskResponse:
    return _ask(req.question.strip(), retriever, store)


def _trace_inputs(inputs: dict) -> dict:
    """Only the question is a meaningful trace input — retriever/store are
    long-lived singletons, not per-call data, and aren't safely serializable."""
    return {"question": inputs.get("question")}


@traceable(name="ask", run_type="chain", process_inputs=_trace_inputs)
def _ask(question: str, retriever: Retriever, store: Store) -> AskResponse:
    """Every question gets a LangSmith trace, even the ones that never reach
    the LLM — courtesy, the sensitive pre-check, and the sub-threshold gap
    gate are deterministic-code decisions by design (see routing.py), but an
    operator watching for questions the system struggled with still needs to
    see them. `_log_and_shape` tags this run with mode + sensitive on every
    branch, so filtering by tag in LangSmith surfaces ESCALATED/GAP questions
    whether or not a model call happened underneath."""
    # Pure courtesy ("thank you", "ok") -- answer directly, never hand off to
    # the director or spend an LLM call. Checked before the sensitive-topic
    # pre-check since the two categories can't overlap.
    if detect_courtesy(question):
        return _log_and_shape(
            store, question, AnswerMode.GROUNDED, 1.0,
            answer="You're welcome! Let me know if you have any other questions.",
            sources=[],
        )

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

    # Groundedness enforced in CODE, not just requested in the prompt: the
    # model's claimed citations are validated against the actual handbook
    # BEFORE routing. A hallucinated source id must not buy a GROUNDED badge —
    # if nothing real survives the filter, route() sees empty source_ids and
    # downgrades to GAP (answer discarded, human handoff instead).
    by_id = {e.id: e for e in ordered}
    ar.source_ids = [sid for sid in ar.source_ids if sid in by_id]

    mode = route(ar)

    if mode in (AnswerMode.GAP, AnswerMode.ESCALATED):
        answer = _handoff_text(mode)
        sources: list[Source] = []
    else:  # GROUNDED or JUDGMENT — show the answer + cited sections
        answer = ar.answer
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
        id=uuid.uuid4().hex[:8], ts=datetime.now(timezone.utc), text=question, mode=mode,
        max_cosine=round(max_score, 3), source_ids=[s.id for s in sources],
        answer=answer if mode in (AnswerMode.GROUNDED, AnswerMode.JUDGMENT) else None,
    ))

    # Tag the enclosing `ask` run (see _ask_traced) so GAP/ESCALATED/JUDGMENT
    # questions are filterable in LangSmith by tag regardless of whether an
    # LLM call happened underneath this run — a no-op if tracing is disabled.
    run = get_current_run_tree()
    if run is not None:
        tags = [f"mode:{mode.value}"]
        if sensitive:
            tags.append("sensitive")
        run.add_tags(tags)
        run.add_metadata({
            "mode": mode.value, "max_score": round(max_score, 3), "sensitive": sensitive,
        })

    return AskResponse(
        answer=answer, mode=mode, confidence=confidence, sources=sources,
        max_score=round(max_score, 3), needs_human_judgment=needs_human_judgment,
        sensitive=sensitive,
    )
