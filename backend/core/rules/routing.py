"""Answer routing — the deterministic mode decision.

PURE function over the model's structured output. Imports no LLM client. This is
the module a reviewer reads to confirm the model never decides the UI mode: it
returns an AnswerResponse; this code decides GROUNDED / JUDGMENT / ESCALATED / GAP.
"""
from __future__ import annotations

from backend.models.ask import AnswerMode, AnswerResponse


def route(resp: AnswerResponse) -> AnswerMode:
    """Map an AnswerResponse to a UI mode. Order matters — first match wins.

    The sub-threshold GAP (retrieval found nothing) is decided BEFORE the LLM is
    called, in the router; this function handles everything after the model ran.
    """
    if resp.sensitive:
        return AnswerMode.ESCALATED           # custody/injury/abuse/billing/staff — no AI answer
    if resp.needs_human_judgment:
        return AnswerMode.JUDGMENT            # policy answerable, the decision isn't
    if not resp.source_ids or resp.confidence == "low":
        return AnswerMode.GAP                 # answered from nothing, or not confident -> gap
    return AnswerMode.GROUNDED
