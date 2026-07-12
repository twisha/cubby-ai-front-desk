"""Eval judges (Sonnet). Generator (Haiku, answer.py) != judge (Sonnet) —
never the same model grading itself. Used only by evals/run_evals.py; no
production route calls these.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from backend.config import CONFIG
from backend.core.llm.client import parse_structured


class GroundednessVerdict(BaseModel):
    verdict: Literal["yes", "partial", "no"]
    failing_claim: str | None  # which claim isn't supported, if not "yes"


class FaithfulnessVerdict(BaseModel):
    verdict: Literal["pass", "fail"]
    reason: str


class AccuracyVerdict(BaseModel):
    verdict: Literal["pass", "fail"]
    reason: str


_GROUNDEDNESS_SYSTEM = """You are a strict fact-checker for an AI front desk. You will be \
given one or more handbook excerpts and an answer that was supposedly based on them. \
Determine whether EVERY factual claim in the answer is directly supported by the excerpts. \
Do not use outside knowledge or assume anything not written in the excerpts. Return verdict \
"yes" if every claim is supported, "partial" if some claims are supported and at least one \
is not, "no" if the core claim is unsupported or contradicted. If the verdict is not "yes", \
name the specific unsupported claim in failing_claim; otherwise leave it null. Return JSON \
matching the schema."""

_FAITHFULNESS_SYSTEM = """You are checking whether an answer states a policy faithfully in \
response to a specific parent QUESTION. You will be given the QUESTION, the SOURCE handbook \
text, and the ANSWER.

An answer does NOT need to restate every fact in the source — a narrow, brief answer to a \
narrow question is fine and often preferred (for example, an answer to "what time do you \
close" does not need to also restate the opening time or weekend closure; that is not a \
faithfulness problem). Only return verdict "fail" if the answer omits, distorts, or softens \
a qualifying condition, exception, or threshold that is DIRECTLY RELEVANT to correctly \
answering THIS question — an omission that would make the answer incomplete, incorrect, or \
misleading for what was actually asked (for example, omitting "without fever-reducing \
medication" from an answer about whether a feverish child can return, since that condition \
changes whether the answer is correct). Do not fail an answer merely for leaving out source \
details unrelated to the question. Explain your verdict briefly in reason. Return JSON \
matching the schema."""

_ACCURACY_SYSTEM = """You are grading an AI front-desk answer against a reference answer for \
a parent's question at an early learning center. Return verdict "pass" if the AI answer \
conveys the same essential information as the reference answer (wording may differ freely), \
"fail" if it materially disagrees with the reference, omits the key point, or gets the \
polarity wrong (for example, saying closed when the reference says open). Explain briefly in \
reason. Return JSON matching the schema."""


def judge_groundedness(cited_text: str, answer: str) -> GroundednessVerdict:
    content = f"Handbook excerpts:\n{cited_text}\n\nAnswer to check:\n{answer}"
    return parse_structured(
        model=CONFIG.judge_model, system=_GROUNDEDNESS_SYSTEM,
        content=content, schema=GroundednessVerdict, max_tokens=600,
    )


def judge_faithfulness(question: str, source_text: str, answer: str) -> FaithfulnessVerdict:
    content = f"Question: {question}\n\nSource handbook text:\n{source_text}\n\nAnswer to check:\n{answer}"
    return parse_structured(
        model=CONFIG.judge_model, system=_FAITHFULNESS_SYSTEM,
        content=content, schema=FaithfulnessVerdict, max_tokens=600,
    )


def judge_accuracy(question: str, reference_answer: str, actual_answer: str) -> AccuracyVerdict:
    content = (
        f"Parent's question: {question}\n\n"
        f"Reference answer: {reference_answer}\n\n"
        f"AI's actual answer: {actual_answer}"
    )
    return parse_structured(
        model=CONFIG.judge_model, system=_ACCURACY_SYSTEM,
        content=content, schema=AccuracyVerdict, max_tokens=600,
    )
