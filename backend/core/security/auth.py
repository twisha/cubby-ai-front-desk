"""Access gate — protects the ANTHROPIC_API_KEY from public-hosting abuse.

One shared code (env ACCESS_CODE), one signed session cookie. Constant-time
compare; HMAC-signed token so a client can't forge a session without the
code. No-ops entirely when ACCESS_CODE is unset — local dev needs no gate,
matching .env.example's documented "may be blank for local dev".
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from backend.config import CONFIG

SESSION_COOKIE_NAME = "cubby_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _sign(payload: str) -> str:
    # ACCESS_CODE doubles as the HMAC secret — deliberately lean: one fewer
    # env var to configure. Fine for this threat model (gate a demo, not
    # defend against a motivated cookie-forging attacker); see DESIGN.md §13.
    mac = hmac.new(CONFIG.access_code.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{mac}"


def _verify(token: str) -> bool:
    try:
        payload, mac = token.rsplit(".", 1)
    except ValueError:
        return False
    expected = hmac.new(CONFIG.access_code.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, expected)


def make_session_token() -> str:
    return _sign(f"ok:{int(time.time())}")


def verify_code(code: str) -> bool:
    """Constant-time compare — timing-safe against a code-guessing attacker."""
    return hmac.compare_digest(code, CONFIG.access_code)


def require_auth(request: Request) -> None:
    """FastAPI dependency, applied server-side to every guarded /api/* route
    (never client-side-only — that would be a decorative splash screen, not
    real protection). Raises 401 if the signed session cookie is missing or
    invalid."""
    if not CONFIG.access_code:
        return
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token or not _verify(token):
        raise HTTPException(status_code=401, detail="Access code required.")
