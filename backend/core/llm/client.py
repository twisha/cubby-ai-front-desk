"""Thin Anthropic wrapper. The ONLY module that imports the Anthropic SDK
(besides its siblings in core/llm/). Returns Pydantic objects; contains no
routing/validation/scheduling decisions.

Uses client.messages.parse(...) for structured output — the response is
validated against the given Pydantic model, so callers never hand-parse JSON.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import TypeVar

from langsmith import get_current_run_tree, traceable
from pydantic import BaseModel

from backend.config import CONFIG

T = TypeVar("T", bound=BaseModel)

# Observability: env-gated on LANGSMITH_API_KEY alone — no key, no tracing,
# identical behavior to before this existed. Set at MODULE IMPORT time, not
# lazily inside a traced function: @traceable's tracing_is_enabled() gate is
# checked before the decorated function body runs, so setting these env vars
# from inside parse_structured() would miss the gate on the very first call.
if CONFIG.langsmith_api_key:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", CONFIG.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", CONFIG.langsmith_project)


@lru_cache(maxsize=1)
def _client():
    import anthropic  # lazy: app boots without the SDK / a key (M0.0)

    if not CONFIG.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to .env to enable chat/vision."
        )
    raw = anthropic.Anthropic(api_key=CONFIG.anthropic_api_key)

    if CONFIG.langsmith_api_key:
        from langsmith.wrappers import wrap_anthropic

        return wrap_anthropic(raw)
    return raw


@traceable(name="parse_structured", run_type="llm")
def parse_structured(
    *,
    model: str,
    system: str,
    content: list[dict] | str,
    schema: type[T],
    max_tokens: int = 1024,
) -> T:
    """One structured-output call -> a validated `schema` instance.

    `content` is the user turn: a plain string, or a list of content blocks
    (used for vision — text + image). No thinking/effort params (Haiku rejects
    them; unnecessary for these tasks).

    @traceable wraps this call site directly (self-gates on tracing being
    enabled — a no-op with no LANGSMITH_API_KEY). This is necessary, not
    redundant with wrap_anthropic(): the installed langsmith SDK's Anthropic
    wrapper patches client.messages.create/.stream and client.beta.messages.*,
    but NOT the non-beta client.messages.parse() this app actually calls —
    confirmed by reading langsmith/wrappers/_anthropic.py. Without this
    decorator, every call here would silently go untraced."""
    resp = _client().messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )

    # Tokens/cost don't show up on the LangSmith run for free: @traceable
    # only sees this function's return value (the parsed Pydantic model),
    # not the raw API response `resp` that actually carries `.usage`. Attach
    # it to the active run's metadata under the "usage_metadata" key, which
    # is the exact key langsmith/run_helpers.py's _extract_usage() looks for
    # (confirmed by reading it) — no-ops harmlessly if tracing is off.
    run = get_current_run_tree()
    if run is not None:
        run.metadata["usage_metadata"] = {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
        }

    parsed = resp.parsed_output
    if parsed is None:  # refusal or unparseable
        raise RuntimeError(f"Model returned no parseable {schema.__name__}")
    return parsed
