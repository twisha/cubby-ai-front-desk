"""The Retriever SEAM.

M0 ships KeywordRetriever (content-token coverage, score in [0,1]). The M1
upgrade drops in a ChromaRetriever behind this exact Protocol — routing.py and
the /ask router never change. If a retrieval upgrade's diff touches a router or
a decision module, the seam was drawn wrong.

Each retriever declares its own `gap_threshold`, because the "no relevant
source" cutoff is scale-specific: keyword coverage and cosine similarity don't
share a number. The router reads `retriever.gap_threshold`; below it, the LLM is
skipped and the question is logged as a GAP.
"""
from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from backend.models.handbook import HandbookEntry

_WORD = re.compile(r"[a-z0-9]+")

# Small stopword set so coverage focuses on content words. Without this,
# "what is the tuition for infants" is diluted by are/is/the/for.
_STOP = {
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "how",
    "i", "if", "in", "is", "it", "me", "my", "of", "on", "or", "the", "to",
    "we", "what", "when", "where", "who", "you", "your", "with", "this", "that",
    "have", "has", "am", "was", "were", "will", "would", "there", "any",
}


def _tokens(s: str) -> set[str]:
    return {t for t in _WORD.findall(s.lower()) if t not in _STOP}


@runtime_checkable
class Retriever(Protocol):
    gap_threshold: float

    def search(self, query: str) -> tuple[list[HandbookEntry], float]:
        """Return (entries ordered by relevance, max_score in [0,1])."""
        ...


class KeywordRetriever:
    """Coverage = (query content-tokens found in a section) / (query
    content-tokens). Rewards sections that cover the question's meaningful words,
    regardless of section length — unlike Jaccard, which favors short sections.
    Good enough at n~=17 to gate GAP and order sections for full-context
    grounding; not a real vector index (that's M1)."""

    #: Deliberately low. The gate only SKIPS the LLM for clearly out-of-scope
    #: questions (summer camp -> 0.0); the real GAP decision is post-LLM routing
    #: (empty source_ids / low confidence). Borderline single-word matches
    #: (e.g. "can my child wear sunscreen" -> 0.33) should reach the model.
    gap_threshold: float = 0.30

    def __init__(self, entries: list[HandbookEntry]) -> None:
        self._entries = entries
        self._toks = [
            (e, _tokens(e.title + " " + e.content + " " + e.category)) for e in entries
        ]

    def reindex(self, entries: list[HandbookEntry]) -> None:
        self.__init__(entries)

    def search(self, query: str) -> tuple[list[HandbookEntry], float]:
        q = _tokens(query)
        if not q:
            return list(self._entries), 0.0
        scored: list[tuple[float, HandbookEntry]] = []
        for entry, toks in self._toks:
            coverage = len(q & toks) / len(q)
            scored.append((coverage, entry))
        scored.sort(key=lambda t: t[0], reverse=True)
        ordered = [e for _, e in scored]
        max_score = scored[0][0] if scored else 0.0
        return ordered, max_score
