"""Smoke tests for the lead endpoint and tools.

These run against the deterministic stub path (no ANTHROPIC_API_KEY needed), so
they're fast and hermetic — cheap regression insurance for the response
contract and the trace shape.
"""

import os

os.environ.pop("ANTHROPIC_API_KEY", None)  # force the stub path

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.tools import find_decision_makers, search_company  # noqa: E402

client = TestClient(app)


def test_health_reports_stub():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["llm"] == "stub"
    assert "version" in body


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
    # Second tool feeds key_contacts.
    assert body["key_contacts"], "expected at least one decision-maker"
    assert {"name", "title"} <= set(body["key_contacts"][0])


def test_trace_shows_both_tools():
    body = client.post("/api/lead", json={"input": "Aurora Outdoor"}).json()
    trace = body["trace"]
    types = [step["type"] for step in trace]
    labels = " ".join(step["label"] for step in trace)
    # The agent must demonstrate a multi-tool loop: call + result for each tool.
    assert "search_company" in labels
    assert "find_decision_makers" in labels
    assert types.count("tool_call") >= 2
    assert types.count("tool_result") >= 2
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


def test_find_decision_makers_returns_contacts():
    seeded = find_decision_makers("Northwind Logistics")
    assert seeded["contacts"], "seeded company should have contacts"
    assert {"name", "title"} <= set(seeded["contacts"][0])
    # Unknown companies still get deterministic fallback contacts.
    unknown = find_decision_makers("Some Unknown Co")
    assert unknown["contacts"]
    assert unknown == find_decision_makers("Some Unknown Co")
