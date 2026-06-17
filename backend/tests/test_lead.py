"""Smoke tests for the lead endpoint and tools.

These run against the deterministic stub path (no ANTHROPIC_API_KEY needed), so
they're fast and hermetic — cheap regression insurance for the response
contract and the trace shape.
"""

import os

os.environ.pop("ANTHROPIC_API_KEY", None)  # force the stub path

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.tools import search_company  # noqa: E402

client = TestClient(app)


def test_health_reports_stub():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "llm": "stub"}


def test_lead_returns_full_contract():
    res = client.post("/api/lead", json={"input": "Northwind Logistics"})
    assert res.status_code == 200
    body = res.json()

    # All four required output sections are present and populated.
    assert set(body) >= {
        "company_overview",
        "pain_points",
        "outreach_angles",
        "outreach_opener",
        "trace",
        "used_stub",
    }
    assert body["used_stub"] is True
    assert body["company_overview"]["name"] == "Northwind Logistics"
    assert body["pain_points"] and body["outreach_angles"]
    assert isinstance(body["outreach_opener"], str) and body["outreach_opener"]


def test_trace_shows_a_tool_call_cycle():
    body = client.post("/api/lead", json={"input": "Aurora Outdoor"}).json()
    types = [step["type"] for step in body["trace"]]
    # The agent must demonstrate calling the tool and integrating its result.
    assert "tool_call" in types
    assert "tool_result" in types
    assert types[-1] == "final"


def test_empty_input_is_rejected():
    res = client.post("/api/lead", json={"input": ""})
    assert res.status_code == 422  # pydantic min_length


def test_search_company_url_parsing():
    rec = search_company("https://acme-robotics.com/about")
    assert rec["name"] == "Acme Robotics"
    assert rec["website"] == "acme-robotics.com"


def test_search_company_is_deterministic():
    assert search_company("Some Unknown Co") == search_company("Some Unknown Co")
