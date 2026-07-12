"""Groups GAP-mode questions by shared keyword -- read-only clustering for
M0.4b (see DESIGN.md's milestone table: "gaps grouping (read-only ok)",
explicitly NOT the live draft->approve flywheel, which is M3).

No embeddings, no LLM -- token-overlap union-find over a stopword-filtered
vocabulary, the same "simple and legible" philosophy as KeywordRetriever.
Any two gap questions sharing one significant word end up in the same
cluster, transitively, so a chain of paraphrases merges into one group
without a fixed list of themes to maintain.
"""
from __future__ import annotations

from collections import Counter

from backend.models.ask import AnswerMode, GapGroup, QuestionLog

_STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "did", "you", "your", "i",
    "we", "have", "has", "had", "for", "there", "to", "of", "in", "on", "at",
    "and", "or", "my", "me", "can", "could", "will", "would", "if", "it",
    "its", "this", "that", "what", "when", "where", "how", "why", "who",
    "with", "about", "any", "all", "be", "been", "not", "get", "got",
}


def _tokens(text: str) -> set[str]:
    words = "".join(c if c.isalnum() else " " for c in text.lower()).split()
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def group_gaps(questions: list[QuestionLog]) -> list[GapGroup]:
    gaps = [q for q in questions if q.mode == AnswerMode.GAP]
    tokens = {q.id: _tokens(q.text) for q in gaps}

    parent = {q.id: q.id for q in gaps}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    ids = [q.id for q in gaps]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if tokens[ids[i]] & tokens[ids[j]]:
                union(ids[i], ids[j])

    clusters: dict[str, list[QuestionLog]] = {}
    for q in gaps:
        clusters.setdefault(find(q.id), []).append(q)

    groups: list[GapGroup] = []
    for members in clusters.values():
        shared: Counter[str] = Counter()
        for q in members:
            shared.update(tokens[q.id])
        theme = shared.most_common(1)[0][0].capitalize() if shared else "General"
        groups.append(GapGroup(
            theme=theme,
            count=len(members),
            questions=sorted(members, key=lambda q: q.ts, reverse=True),
        ))

    groups.sort(key=lambda g: g.count, reverse=True)
    return groups
