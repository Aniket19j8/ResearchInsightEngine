"""LLM access with a graceful fallback.

`complete()` calls OpenAI and returns text. If the API key is missing or
the call fails for any reason, it returns None so callers can fall back to
a deterministic keyword tagger. The demo must never die on a network blip.
"""
from __future__ import annotations

from . import config

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not config.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI

        kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.OPENAI_BASE_URL:
            kwargs["base_url"] = config.OPENAI_BASE_URL
        _client = OpenAI(**kwargs)
        return _client
    except Exception:
        return None


def complete(prompt: str, *, json_mode: bool = False) -> str | None:
    """Return the model's text response, or None on any failure."""
    client = _get_client()
    if client is None:
        return None
    try:
        kwargs = {
            "model": config.OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content
    except Exception:
        return None


def is_live() -> bool:
    """True if an OpenAI client could be constructed (key present)."""
    return _get_client() is not None
