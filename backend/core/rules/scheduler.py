"""Deterministic compliance scheduler — pure date math, no LLM ever.

Per 55 Pa. Code Sec 3270.131(b): infant/young toddler (<2y) needs a health
report at least every 6 months; older toddler/preschool (>=2y) at least every
12 months, tracked from the report's signed date.
"""
from __future__ import annotations

import calendar
from datetime import date

from backend.models.roster import Child, ComplianceRow, ReminderTier

_GENTLE_DAYS = 60
_STANDARD_DAYS = 30
_URGENT_DAYS = 14

# Sort key: most urgent first. GRACE_REQUESTED sits ahead of PAUSED/COMPLIANT
# because it's the one state that still needs an operator decision.
_URGENCY_ORDER: dict[ReminderTier, int] = {
    ReminderTier.OVERDUE: 0,
    ReminderTier.URGENT: 1,
    ReminderTier.STANDARD: 2,
    ReminderTier.GENTLE: 3,
    ReminderTier.GRACE_REQUESTED: 4,
    ReminderTier.PAUSED: 5,
    ReminderTier.COMPLIANT: 6,
}


def _age_years(dob: date, on: date) -> float:
    return (on - dob).days / 365.25


def cycle_months(dob: date, on_date: date) -> int:
    """The report cycle currently required for a child of this age.

    Evaluated against `on_date` (today), not the last exam date. Sec
    3270.131(b)'s obligation tracks the child's PRESENT age band: a center
    inspected today is judged against today's required cycle, not the cycle
    that applied when the last report happened to be signed. This is a
    judgment call (the regulation text and DESIGN.md's own sketch don't
    pin down which age to use) but it's the one that makes the age-2
    transition visible on the dashboard as it happens, without waiting for
    a new exam to be filed — which is the whole point of that seed child.
    """
    return 6 if _age_years(dob, on_date) < 2 else 12


def add_months(d: date, months: int) -> date:
    """Public: shared by scheduler.py and validation.py (a form's exam date +
    cycle_months determines whether it's still current)."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_due_date(last_exam_date: date | None, dob: date, today: date) -> date | None:
    if last_exam_date is None:
        return None
    return add_months(last_exam_date, cycle_months(dob, today))


def tier_for(child: Child, next_due: date | None, today: date) -> ReminderTier:
    if next_due is None:
        return ReminderTier.OVERDUE  # no exam on file at all

    # Pause rule: an acknowledged appointment on/before the due date silences
    # the tier entirely — "stop nagging proactive parents."
    if child.parent_state == "due_soon_acknowledged" and child.acknowledged_appt_date:
        if child.acknowledged_appt_date <= next_due:
            return ReminderTier.PAUSED
        # Extension case: appt is AFTER the due date. Do not silently pause —
        # this is the admin's case-by-case judgment made explicit and logged,
        # not a synchronous front-desk negotiation with no trace.
        return ReminderTier.GRACE_REQUESTED

    days_until = (next_due - today).days
    if days_until < 0:
        return ReminderTier.OVERDUE
    if days_until <= _URGENT_DAYS:
        return ReminderTier.URGENT
    if days_until <= _STANDARD_DAYS:
        return ReminderTier.STANDARD
    if days_until <= _GENTLE_DAYS:
        return ReminderTier.GENTLE
    return ReminderTier.COMPLIANT


def compliance_row(child: Child, today: date) -> ComplianceRow:
    due = next_due_date(child.last_exam_date, child.dob, today)
    return ComplianceRow(
        child=child,
        cycle_months=cycle_months(child.dob, today),
        next_due_date=due,
        tier=tier_for(child, due, today),
        days_until_due=(due - today).days if due else None,
    )


def urgency_sort_key(row: ComplianceRow) -> tuple[int, int]:
    days = row.days_until_due if row.days_until_due is not None else 9999
    return (_URGENCY_ORDER[row.tier], days)
