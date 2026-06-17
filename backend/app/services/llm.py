"""Provider seam.

Returns an OpenAI-compatible client pointed at DashScope (Qwen / 通义千问) when
an API key is set, or `None` to signal the caller (the agent) should run its
deterministic stub instead. Keeping this decision in one place lets the rest of
the code stay oblivious to whether a real LLM is available.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from ..config import DASHSCOPE_BASE_URL, get_api_key


@lru_cache(maxsize=1)
def get_client() -> Optional["object"]:
    """Return a Qwen (DashScope) client, or None when no API key is configured."""
    api_key = get_api_key()
    if not api_key:
        return None
    # Imported lazily so the stub path has no hard dependency on the SDK being
    # importable/configured. Qwen exposes an OpenAI-compatible API, so we use the
    # openai SDK with DashScope's base URL.
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
