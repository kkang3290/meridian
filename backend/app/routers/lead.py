"""API routes for the lead assistant."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..config import VERSION
from ..schemas import LeadBrief, LeadRequest
from ..services.agent import AgentError, run_lead_agent
from ..services.llm import get_client

logger = logging.getLogger("lead_assistant")

router = APIRouter(prefix="/api", tags=["lead"])


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness check; also reports version and whether a real LLM is configured."""
    return {"status": "ok", "version": VERSION, "llm": "claude" if get_client() else "stub"}


@router.post("/lead", response_model=LeadBrief)
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
