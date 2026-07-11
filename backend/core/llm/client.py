"""Thin Anthropic wrapper. The ONLY module that imports the Anthropic SDK
(besides its siblings in core/llm/). Returns Pydantic objects; contains no
routing/validation/scheduling decisions.

Uses client.messages.parse(...) for structured output — the response is
validated against the given Pydantic model, so callers never hand-parse JSON.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

from backend.config import CONFIG

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=1)
def _client():
    import anthropic  # lazy: app boots without the SDK / a key (M0.0)

    if not CONFIG.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to .env to enable chat/vision."
        )
    return anthropic.Anthropic(api_key=CONFIG.anthropic_api_key)


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
    them; unnecessary for these tasks)."""
    resp = _client().messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )
    parsed = resp.parsed_output
    if parsed is None:  # refusal or unparseable
        raise RuntimeError(f"Model returned no parseable {schema.__name__}")
    return parsed
