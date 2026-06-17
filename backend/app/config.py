"""Application settings and constants.

Centralizes model/agent tuning and credential lookup so the rest of the code
doesn't read os.environ directly. `.env` is loaded here at import time.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Model + agent-loop tuning.
VERSION = "1.2.0"
# Qwen (通义千问) via the DashScope OpenAI-compatible endpoint. Both the model
# and the base URL are env-overridable (e.g. switch to qwen-max, or the
# international endpoint dashscope-intl.aliyuncs.com).
MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")
DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
# Cap on the visible output; generous so the phase-2 JSON isn't truncated.
MAX_TOKENS = 8000
MAX_TOOL_ITERS = 4


def get_api_key() -> str | None:
    """Return the DashScope/Qwen API key, or None when it isn't configured."""
    return os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")


def get_cors_origins() -> list[str]:
    """Allowed CORS origins — comma-separated CORS_ORIGINS env, default '*'."""
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
