"""Answer routing — the deterministic mode decision.

PURE function over the model's structured output. Imports no LLM client. This is
the module a reviewer reads to confirm the model never decides the UI mode: it
returns an AnswerResponse; this code decides GROUNDED / JUDGMENT / ESCALATED / GAP.
"""
from __future__ import annotations

from backend.models.ask import AnswerMode, AnswerResponse

# Deterministic pre-check for six sensitive categories: custody / release
# authorization, injury, abuse or neglect, staff complaints, billing
# disputes, another family's child, and a child's personal identifying
# information. Phrase-scoped (not single words like "father") to avoid
# false-positiving ordinary logistics questions.
#
# WHY THIS EXISTS: these topics by design have ~zero content-word overlap with
# the handbook (the handbook correctly does not discuss custody), so the
# retrieval gap-gate scores them near 0 and would otherwise swallow them as
# GAP before the LLM ever runs to classify sensitive=true. Escalation for
# these categories must not depend on retrieval succeeding.
_SENSITIVE_PHRASES: tuple[str, ...] = (
    # custody / release authorization
    "custody", "restraining order", "court order",
    "don't release", "do not release", "won't release", "will not release",
    "shouldn't release", "not release", "unauthorized pickup",
    "not authorized to pick up", "not allowed to pick up",
    # injury / abuse / neglect
    "injured", "injury", "got hurt", "was hurt", "bruise", "bruising",
    "abuse", "neglect", "allegation",
    # staff complaints
    "complaint about", "file a complaint", "report a staff",
    "staff member did", "staff mistreated",
    # billing disputes
    "billing dispute", "overcharged", "refund dispute",
    "dispute a charge", "wrongly charged",
    # another family's child
    "another child", "someone else's child", "another family's child",
    "other parent's child",
    # a child's personal identifying information — narrowly scoped to
    # identity-theft-risk fields (SSN, government/insurance ID numbers), not
    # DOB or address, which come up in ordinary enrollment/compliance
    # questions ("my daughter's date of birth is...") and would false-positive
    "social security", "ssn", "social security number",
    "driver's license", "drivers license", "passport number",
    "medicaid number", "insurance id number",
)


def detect_sensitive(question: str) -> bool:
    """Deterministic keyword pre-check — runs BEFORE retrieval, not an LLM
    classification. See _SENSITIVE_PHRASES for why this must be code, not
    dependent on the gap gate or the model seeing the question at all."""
    q = question.lower()
    return any(phrase in q for phrase in _SENSITIVE_PHRASES)


# Pure conversational closers ("thank you", "ok", "got it") carry no
# handbook content to retrieve, so without this check they fall through the
# gap gate and get the SAME "I've sent this to the director" handoff as a
# real unanswered question -- confusing after a normal exchange. Whole-
# message match only (after stripping case/punctuation), so a real question
# that happens to start with "thanks, but..." still routes normally instead
# of being swallowed here.
_COURTESY_PHRASES: frozenset[str] = frozenset({
    "thank you", "thanks", "ty", "thx", "thank you so much", "thanks so much",
    "thanks a lot", "much appreciated", "appreciate it", "appreciate it thanks",
    "ok", "okay", "got it", "gotcha", "sounds good", "sounds good thanks",
    "great", "great thanks", "perfect", "perfect thanks", "cool", "cool thanks",
    "awesome", "alright", "no problem", "great thank you",
})


def detect_courtesy(question: str) -> bool:
    """See _COURTESY_PHRASES. Deterministic, whole-message match — never an
    LLM classification, so it costs nothing and never misfires on a real
    question embedding one of these words."""
    normalized = question.strip().lower().rstrip("!.,")
    return normalized in _COURTESY_PHRASES


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
