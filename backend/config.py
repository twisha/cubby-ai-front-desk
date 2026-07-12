"""Central config + tunables. Read once at startup.

DESIGN THESIS: the LLM converts language <-> structured data; ALL routing,
validation, and scheduling decisions are deterministic code. Model IDs and
thresholds live here so the decision code never hard-codes them.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # --- Secrets (env only, never shipped to client, never logged) ---
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    access_code: str = os.getenv("ACCESS_CODE", "")

    # --- Model IDs (verified against the claude-api skill, 2026-07) ---
    # Chat + gap draft. Haiku 4.5 does NOT accept `thinking`/`effort` params.
    answer_model: str = os.getenv("ANSWER_MODEL", "claude-haiku-4-5")
    # Vision extraction + eval/runtime judge. Current Sonnet (SPEC's
    # claude-sonnet-4-6 is previous-gen). Generator != judge, by design.
    vision_model: str = os.getenv("VISION_MODEL", "claude-sonnet-5")
    judge_model: str = os.getenv("JUDGE_MODEL", "claude-sonnet-5")

    # --- Retrieval ---
    gap_threshold: float = float(os.getenv("GAP_THRESHOLD", "0.30"))  # below -> skip LLM, log GAP
    retrieval_top_k: int | None = (
        int(os.getenv("RETRIEVAL_TOP_K")) if os.getenv("RETRIEVAL_TOP_K") else None
    )  # None = full-context grounding (M0 default)

    # --- Cost circuit-breakers (protect the API key) ---
    max_daily_llm_calls: int = int(os.getenv("MAX_DAILY_LLM_CALLS", "500"))
    rate_limit_per_min: int = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))

    # --- Async sampled runtime judging ---
    judge_sample_rate: float = float(os.getenv("JUDGE_SAMPLE_RATE", "0.33"))

    # --- Observability (optional). Presence of the key alone is the toggle —
    # core/llm/client.py sets LANGSMITH_TRACING itself; nothing else to set.
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "cubby-ai-front-desk")

    # --- Center identity (per-tenant in production; seeded here) ---
    center_name: str = "Willow Grove Early Learning"
    center_town: str = "Wissahocken, PA"
    director_name: str = "Ms. Donnelly"


CONFIG = Config()
