"""FastAPI entrypoint for the Mini Lead Assistant."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import AgentError, run_lead_agent
from .llm import get_client
from .schemas import LeadBrief, LeadRequest

logger = logging.getLogger("lead_assistant")

app = FastAPI(title="Mini Lead Assistant", version="1.0.0")

# Permissive CORS for local dev (Vite dev server on a different port). The Vite
# proxy also routes /api, so this mainly covers direct browser calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    """Liveness check; also reports whether a real LLM is configured."""
    return {"status": "ok", "llm": "claude" if get_client() else "stub"}


@app.post("/api/lead", response_model=LeadBrief)
def create_lead(req: LeadRequest) -> LeadBrief:
    """Run the agent and return the structured brief + trace."""
    try:
        return run_lead_agent(req.input)
    except AgentError as exc:
        # Expected failure (refusal / truncation) — message is safe to show.
        logger.warning("lead agent declined: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface a clean error to the client
        logger.exception("lead agent failed")
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc
