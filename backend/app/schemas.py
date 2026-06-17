"""Pydantic models for the request, the structured lead brief, and the agent trace.

The shapes here are the contract between the FastAPI endpoint and the React
frontend, and the `LeadBrief` fields map 1:1 to what the assignment asks the
agent to output (公司概况 / 痛点 / 切入点 / 开场白).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class LeadRequest(BaseModel):
    """Input to POST /api/lead — a company name, URL, or one-line description."""

    input: str = Field(..., min_length=1, description="公司名 / 网址 / 一句话简述")


class CompanyOverview(BaseModel):
    """公司概况 — the factual snapshot the agent assembled via its tool."""

    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    headquarters: Optional[str] = None
    summary: str


class TraceStep(BaseModel):
    """One entry in the agent's tool-call / thinking trace.

    `type` distinguishes the kind of step so the frontend can render each
    differently:
      - thinking     -> the model's summarized reasoning
      - tool_call    -> the model decided to call a tool (name + input)
      - tool_result  -> the data the tool returned
      - final        -> the structured brief was produced
    """

    type: Literal["thinking", "tool_call", "tool_result", "final"]
    label: str
    detail: Optional[str] = None
    # For tool_call: the arguments. For tool_result: the returned record.
    data: Optional[Any] = None


class LeadBrief(BaseModel):
    """The full response: the structured brief plus the agent trace."""

    company_overview: CompanyOverview
    pain_points: list[str]
    outreach_angles: list[str]
    outreach_opener: str
    trace: list[TraceStep] = Field(default_factory=list)
    # True when the deterministic stub ran (no ANTHROPIC_API_KEY); surfaced so
    # the UI and reviewer can tell which path produced the result.
    used_stub: bool = False
