"""Handbook entry — the unstructured knowledge unit. One per ## section."""
from __future__ import annotations

from pydantic import BaseModel


class HandbookEntry(BaseModel):
    id: str                  # e.g. "illness-policy"
    category: str            # "health" | "schedule" | "billing" | "operations" | "enrollment"
    title: str
    content: str             # 2-6 sentences, plain language
    source: str = "Parent Handbook"
