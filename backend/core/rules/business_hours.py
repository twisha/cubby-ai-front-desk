"""Business-hours awareness for handoff copy — pure deterministic logic, no
LLM. Matches backend/data/handbook.md's `hours` section (Mon-Fri, 6:30am-
6:00pm) -- keep both in sync if hours ever change.

6:30am-6pm means Eastern time (Willow Grove is in Wissahocken, PA) -- NOT
whatever OS timezone the server process happens to run in. `now` is
explicitly converted to America/New_York before any comparison. This
matters in practice: local dev on an Eastern-time machine and a UTC
container (e.g. Render) would silently disagree by several hours on "is
it open right now" if `now.time()` were compared directly against
OPEN_TIME/CLOSE_TIME without this conversion -- correct by accident
locally, wrong the moment it's deployed somewhere else.

Known simplification: does not account for holiday closures (handbook.md's
`holidays-2026` section is prose, and parsing dates out of it in code would
fight the project's own "LLM handles unstructured language, code handles
structured data" split). A holiday submission still gets a "tomorrow
morning" promise that won't hold -- an acceptable, documented gap, not a
silent one.
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

OPEN_TIME = time(6, 30)
CLOSE_TIME = time(18, 0)
HOURS_LABEL = "Mon–Fri, 6:30am–6:00pm"
_CENTER_TZ = ZoneInfo("America/New_York")


def _local(now: datetime) -> datetime:
    """Naive `now` is presumed to already be UTC (the convention everywhere
    else in this codebase — see ask.py, seed_questions.py); aware `now` is
    converted from whatever zone it carries. Either way, the comparison
    below always happens in the center's actual local time."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("UTC"))
    return now.astimezone(_CENTER_TZ)


def is_business_hours(now: datetime) -> bool:
    local = _local(now)
    return local.weekday() < 5 and OPEN_TIME <= local.time() < CLOSE_TIME


def next_business_day_label(now: datetime) -> str:
    """Parent-friendly label for when the center is next open. `now` is
    passed in explicitly (never reads the clock itself) so this stays
    trivially unit-testable, matching scheduler.py's `today` convention."""
    local = _local(now)
    weekday = local.weekday()  # Mon=0 ... Sun=6
    if weekday in (5, 6):  # Saturday or Sunday
        return "Monday morning"
    if local.time() < OPEN_TIME:  # weekday, before opening -> reopens later today
        return "later this morning"
    # weekday, after closing
    return "Monday morning" if weekday == 4 else "tomorrow morning"
