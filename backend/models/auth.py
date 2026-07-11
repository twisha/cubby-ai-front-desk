"""Access-gate models — the shared-code splash for public hosting."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuthRequest(BaseModel):
    email: str
    code: str


class VisitorLogEntry(BaseModel):
    email: str
    ts: datetime
