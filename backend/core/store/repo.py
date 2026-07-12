"""The Store SEAM.

M0 ships InMemoryStore (dicts seeded at startup). The M2 upgrade drops in a
SqliteStore behind these exact methods — routers never change.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.data.seed_questions import seed_questions
from backend.data.seed_roster import seed_children
from backend.models.ask import QuestionLog
from backend.models.auth import VisitorLogEntry
from backend.models.forms import FlaggedForm
from backend.models.roster import Child


class Store(Protocol):
    def list_children(self) -> list[Child]: ...
    def get_child(self, child_id: str) -> Child | None: ...
    def upsert_child(self, child: Child) -> None: ...
    def match_child_by_name(self, name: str) -> Child | None: ...
    def list_questions(self) -> list[QuestionLog]: ...
    def add_question(self, q: QuestionLog) -> None: ...
    def add_visitor(self, entry: VisitorLogEntry) -> None: ...
    def list_visitors(self) -> list[VisitorLogEntry]: ...
    def add_flagged_form(self, f: FlaggedForm) -> None: ...
    def list_flagged_forms(self) -> list[FlaggedForm]: ...
    def get_flagged_form(self, flag_id: str) -> FlaggedForm | None: ...
    def remove_flagged_form(self, flag_id: str) -> None: ...
    def mark_notified(self, flag_id: str, ts: datetime) -> FlaggedForm | None: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._children: dict[str, Child] = {c.id: c for c in seed_children()}
        self._questions: list[QuestionLog] = list(seed_questions())
        self._visitors: list[VisitorLogEntry] = []
        self._flagged: dict[str, FlaggedForm] = {}

    # --- roster ---
    def list_children(self) -> list[Child]:
        return list(self._children.values())

    def get_child(self, child_id: str) -> Child | None:
        return self._children.get(child_id)

    def upsert_child(self, child: Child) -> None:
        self._children[child.id] = child

    def match_child_by_name(self, name: str) -> Child | None:
        """Fuzzy-ish match on normalized name tokens. Unmatched -> None
        (the validator routes that to needs_review, never a hard reject)."""
        want = {t for t in name.lower().replace(",", " ").split() if t}
        best: tuple[int, Child] | None = None
        for child in self._children.values():
            have = set(child.name.lower().split())
            score = len(want & have)
            if score and (best is None or score > best[0]):
                best = (score, child)
        return best[1] if best else None

    # --- questions ---
    def list_questions(self) -> list[QuestionLog]:
        return sorted(self._questions, key=lambda q: q.ts, reverse=True)

    def add_question(self, q: QuestionLog) -> None:
        self._questions.append(q)

    # --- access-gate visitor log ---
    def add_visitor(self, entry: VisitorLogEntry) -> None:
        self._visitors.append(entry)

    def list_visitors(self) -> list[VisitorLogEntry]:
        return list(self._visitors)

    # --- flagged (rejected/needs_review) scans -- the Dashboard's queue ---
    def add_flagged_form(self, f: FlaggedForm) -> None:
        self._flagged[f.id] = f

    def list_flagged_forms(self) -> list[FlaggedForm]:
        return sorted(self._flagged.values(), key=lambda f: f.scanned_at, reverse=True)

    def get_flagged_form(self, flag_id: str) -> FlaggedForm | None:
        return self._flagged.get(flag_id)

    def remove_flagged_form(self, flag_id: str) -> None:
        self._flagged.pop(flag_id, None)

    def mark_notified(self, flag_id: str, ts: datetime) -> FlaggedForm | None:
        f = self._flagged.get(flag_id)
        if f is None:
            return None
        updated = f.model_copy(update={"notified_at": ts})
        self._flagged[flag_id] = updated
        return updated
