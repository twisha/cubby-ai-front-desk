"""Answer engine (Haiku). Turns a parent question + handbook sections into an
AnswerResponse. Full-context grounding: ALL sections are passed (n<=~20 fits
trivially), ordered by retrieval score. The model fills the structured fields;
CODE (routing.py) decides the UI mode from them.
"""
from __future__ import annotations

from backend.config import CONFIG
from backend.core.llm.client import parse_structured
from backend.models.ask import AnswerResponse
from backend.models.handbook import HandbookEntry

# SPEC system prompt, verbatim (tune only if outputs misbehave).
_SYSTEM = """You are the AI front desk assistant for {center}, a daycare in {town}. \
You answer parents' questions using ONLY the handbook entries provided below. Rules:
1. Never state a fact that is not in the provided entries. If the entries do not \
contain the answer, return empty source_ids and confidence "low".
2. Quote policies faithfully; do not soften or extend them.
3. If the question asks you to apply a policy to a specific child or situation \
(e.g., "can my child come in today with a fever from last night"), answer with the \
relevant policy AND set needs_human_judgment=true.
4. Set sensitive=true for anything involving custody, child injury, abuse or neglect \
concerns, staff complaints, billing disputes, or another family's child. Do not answer \
these; a human will.
5. Warm, brief, parent-friendly tone. No corporate filler.
Return JSON matching the AnswerResponse schema. Handbook entries:
{entries}"""


def _format_entries(entries: list[HandbookEntry]) -> str:
    return "\n".join(
        f"[{e.id}] ({e.category}) {e.title}: {e.content}" for e in entries
    )


def answer_question(question: str, entries: list[HandbookEntry]) -> AnswerResponse:
    system = _SYSTEM.format(
        center=CONFIG.center_name,
        town=CONFIG.center_town,
        entries=_format_entries(entries),
    )
    return parse_structured(
        model=CONFIG.answer_model,
        system=system,
        content=question,
        schema=AnswerResponse,
        max_tokens=600,
    )
