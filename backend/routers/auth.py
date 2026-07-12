"""POST /api/auth (login), GET /api/auth/status (session probe).

Both endpoints are intentionally unguarded at the router level: login is the
entry point (nothing to check yet), and status IS the check (its own
require_auth dependency is the answer). Every other /api/* router is guarded
in main.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.config import CONFIG
from backend.core.security.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    make_session_token,
    require_auth,
    verify_code,
)
from backend.core.store.repo import Store
from backend.deps import get_store
from backend.models.auth import AuthRequest, VisitorLogEntry

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("")
def login(
    req: AuthRequest,
    request: Request,
    response: Response,
    store: Store = Depends(get_store),
) -> dict:
    if not CONFIG.access_code:
        return {"ok": True}  # gate disabled — local dev, no code configured

    if not verify_code(req.code):
        raise HTTPException(status_code=401, detail="That code doesn't match — double-check and try again.")

    store.add_visitor(VisitorLogEntry(email=req.email, ts=datetime.now(timezone.utc)))
    response.set_cookie(
        SESSION_COOKIE_NAME,
        make_session_token(),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return {"ok": True}


@router.get("/status", dependencies=[Depends(require_auth)])
def status() -> dict:
    return {"ok": True}
