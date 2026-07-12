"""Business-hours awareness for handoff copy — pure deterministic logic, no
LLM. Matches backend/data/handbook.md's `hours` section (Mon-Fri, 6:30am-
6:00pm) -- keep both in sync if hours ever change.

Known simplification: does not account for holiday closures (handbook.md's
`holidays-2026` section is prose, and parsing dates out of it in code would
fight the project's own "LLM handles unstructured language, code handles
structured data" split). A holiday submission still gets a "tomorrow
morning" promise that won't hold -- an acceptable, documented gap, not a
silent one.
"""
from __future__ import annotations

from datetime import datetime, time

OPEN_TIME = time(6, 30)
CLOSE_TIME = time(18, 0)
HOURS_LABEL = "Mon–Fri, 6:30am–6:00pm"


def is_business_hours(now: datetime) -> bool:
    return now.weekday() < 5 and OPEN_TIME <= now.time() < CLOSE_TIME


def next_business_day_label(now: datetime) -> str:
    """Parent-friendly label for when the center is next open. `now` is
    passed in explicitly (never reads the clock itself) so this stays
    trivially unit-testable, matching scheduler.py's `today` convention."""
    weekday = now.weekday()  # Mon=0 ... Sun=6
    if weekday in (5, 6):  # Saturday or Sunday
        return "Monday morning"
    if now.time() < OPEN_TIME:  # weekday, before opening -> reopens later today
        return "later this morning"
    # weekday, after closing
    return "Monday morning" if weekday == 4 else "tomorrow morning"
