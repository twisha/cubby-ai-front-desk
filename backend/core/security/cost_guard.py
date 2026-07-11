"""Cost circuit-breakers — the real backstop on ANTHROPIC_API_KEY spend.

The access gate limits WHO can reach the LLM routes; this limits HOW MUCH,
even if the code leaks or a reviewer scripts something aggressive. Fails
CLOSED: over either cap, the request 429s BEFORE any LLM call — the worst
case is a capped bill, never an open one.

In-memory counters — fine for this single-process demo; a multi-worker
deploy would need a shared store (Redis) for these caps to hold across
processes, which is out of scope here (see DESIGN.md §13).
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from backend.config import CONFIG

_daily_count = 0
_daily_date: str | None = None
_minute_buckets: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))  # ip -> (minute, count)


def _reset_daily_if_needed() -> None:
    global _daily_count, _daily_date
    today = datetime.now(timezone.utc).date().isoformat()
    if _daily_date != today:
        _daily_date = today
        _daily_count = 0


def enforce_cost_limits(request: Request) -> None:
    """Apply to every LLM-calling route (/ask, /validate-form) — never to
    pure-CRUD routes like /compliance, which cost nothing to call."""
    global _daily_count
    _reset_daily_if_needed()

    if _daily_count >= CONFIG.max_daily_llm_calls:
        raise HTTPException(
            status_code=429,
            detail="Daily usage cap reached for this demo — please try again tomorrow.",
        )

    ip = request.client.host if request.client else "unknown"
    current_minute = int(time.time() // 60)
    bucket_minute, count = _minute_buckets[ip]
    if bucket_minute != current_minute:
        bucket_minute, count = current_minute, 0
    if count >= CONFIG.rate_limit_per_min:
        raise HTTPException(status_code=429, detail="Too many requests — please slow down.")

    _minute_buckets[ip] = (bucket_minute, count + 1)
    _daily_count += 1
