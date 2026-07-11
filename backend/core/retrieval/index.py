"""The Retriever SEAM.

M0 ships KeywordRetriever (token-overlap, max_score in [0,1]). The M1 upgrade
drops in a ChromaRetriever behind this exact signature — routing.py and the
/ask router never change. If a retrieval upgrade's diff touches a router or a
decision module, the seam was drawn wrong.
"""
from __future__ import annotations

import re
from typing import Protocol

from backend.models.handbook import HandbookEntry

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


class Retriever(Protocol):
    def search(self, query: str) -> tuple[list[HandbookEntry], float]:
        """Return (entries ordered by relevance, max_score in [0,1])."""
        ...


class KeywordRetriever:
    """Jaccard-style token overlap. Good enough at n~=15 to gate GAP and order
    sections for full-context grounding; not a real vector index (that's M1)."""

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
            overlap = len(q & toks)
            score = overlap / len(q | toks) if toks else 0.0
            scored.append((score, entry))
        scored.sort(key=lambda t: t[0], reverse=True)
        ordered = [e for _, e in scored]
        max_score = scored[0][0] if scored else 0.0
        return ordered, max_score
