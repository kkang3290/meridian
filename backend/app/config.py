"""Application settings and constants.

Centralizes model/agent tuning and credential lookup so the rest of the code
doesn't read os.environ directly. `.env` is loaded here at import time.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Model + agent-loop tuning.
MODEL = "claude-opus-4-8"
# Shared by adaptive thinking AND the visible output, so keep headroom — a tight
# cap can truncate the phase-2 JSON (stop_reason "max_tokens") and break parsing.
MAX_TOKENS = 8000
MAX_TOOL_ITERS = 4


def get_api_key() -> str | None:
    """Return the Anthropic API key, or None when it isn't configured."""
    return os.environ.get("ANTHROPIC_API_KEY")
