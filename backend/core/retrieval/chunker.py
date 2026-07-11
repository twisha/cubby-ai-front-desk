"""Deterministic chunker: handbook.md -> [HandbookEntry], one per ## section.

JSON/objects are the internal representation only; handbook.md is the authored
source of truth. Production path (README, not built): docx -> heading-structured
sections via the same chunker.
"""
from __future__ import annotations

from pathlib import Path

from backend.models.handbook import HandbookEntry

_HANDBOOK = Path(__file__).resolve().parents[2] / "data" / "handbook.md"


def _title_from_id(entry_id: str) -> str:
    return entry_id.replace("-", " ").title()


def chunk_handbook(path: Path | None = None) -> list[HandbookEntry]:
    text = (path or _HANDBOOK).read_text(encoding="utf-8")
    entries: list[HandbookEntry] = []
    entry_id: str | None = None
    category = "operations"
    body: list[str] = []

    def flush() -> None:
        if entry_id and body:
            entries.append(HandbookEntry(
                id=entry_id, category=category,
                title=_title_from_id(entry_id),
                content=" ".join(body).strip(),
            ))

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            flush()
            entry_id = line[3:].strip()
            category = "operations"
            body = []
        elif entry_id is None:
            continue  # skip the H1 title + intro comment
        elif line.lower().startswith("category:"):
            category = line.split(":", 1)[1].strip()
        elif line.startswith("<!--") or not line:
            continue
        else:
            body.append(line)
    flush()
    return entries
