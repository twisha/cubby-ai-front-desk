"""Roster + compliance models. The four parent states are the admin's
in-her-head case-by-case judgment, made into recorded state."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel


ParentState = Literal[
    "compliant",
    "due_soon_acknowledged",   # parent told us the appt; reminders paused (appt <= due)
    "due_soon_unresponsive",   # in a reminder tier, no acknowledgment
    "overdue",
]


class ReminderTier(str, Enum):
    COMPLIANT = "compliant"
    GENTLE = "gentle"          # 60 days out
    STANDARD = "standard"      # 30 days out
    URGENT = "urgent"          # 14 days out
    OVERDUE = "overdue"        # past due
    PAUSED = "paused"          # acknowledged, appt on/before due date
    GRACE_REQUESTED = "grace_requested"  # acknowledged, appt AFTER due -> needs operator OK


class Child(BaseModel):
    id: str
    name: str                             # fictional
    dob: date
    last_exam_date: date | None
    parent_state: ParentState
    acknowledged_appt_date: date | None = None


class ComplianceRow(BaseModel):
    """A Child plus everything the scheduler computes (code, never LLM)."""
    child: Child
    cycle_months: int                     # 6 (<2y) or 12 (>=2y)
    next_due_date: date | None
    tier: ReminderTier
    days_until_due: int | None
