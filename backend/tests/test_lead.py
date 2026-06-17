"""Smoke tests for the lead endpoint and tools.

Most tests run against the deterministic stub path (no API key needed), so
they're fast and hermetic. One test drives the real Qwen tool-calling loop with
a fake OpenAI-compatible client, so the agent loop itself is covered without
hitting the live API.
"""

import json
import os
from types import SimpleNamespace

os.environ.pop("DASHSCOPE_API_KEY", None)  # force the stub path for endpoint tests
os.environ.pop("QWEN_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.agent import _run_with_qwen  # noqa: E402
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


# --------------------------------------------------------------------------- #
# Fake OpenAI-compatible client to exercise the real Qwen tool-calling loop.
# --------------------------------------------------------------------------- #
def _tool_call(call_id, name, args):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _resp(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])


class FakeQwenClient:
    """Scripts a search_company -> find_decision_makers -> JSON-brief sequence."""

    FINAL_JSON = {
        "company_overview": {
            "name": "Northwind Logistics",
            "website": "northwindlogistics.com",
            "industry": "Freight forwarding",
            "size": "约 400 人",
            "headquarters": "Rotterdam, Netherlands",
            "summary": "测试用简报。",
        },
        "pain_points": ["痛点一", "痛点二"],
        "outreach_angles": ["切入点一"],
        "outreach_opener": "你好，注意到贵司正在扩张……",
        "key_contacts": [
            {"name": "Sven de Vries", "title": "VP", "linkedin": None, "note": None}
        ],
    }

    def __init__(self):
        self.phase1_calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        # Phase 2 is identified by the JSON response_format.
        if kwargs.get("response_format"):
            return _resp(SimpleNamespace(content=json.dumps(self.FINAL_JSON), tool_calls=None))
        self.phase1_calls += 1
        if self.phase1_calls == 1:
            return _resp(SimpleNamespace(content="", tool_calls=[_tool_call("c1", "search_company", {"query": "Northwind Logistics"})]))
        if self.phase1_calls == 2:
            return _resp(SimpleNamespace(content="", tool_calls=[_tool_call("c2", "find_decision_makers", {"company": "Northwind Logistics"})]))
        return _resp(SimpleNamespace(content="done", tool_calls=None))


def test_qwen_loop_with_fake_client():
    brief = _run_with_qwen(FakeQwenClient(), "Northwind Logistics")
    assert brief.used_stub is False
    assert brief.company_overview.name == "Northwind Logistics"
    assert brief.pain_points and brief.outreach_angles and brief.outreach_opener
    assert brief.key_contacts[0].name == "Sven de Vries"
    types = [s.type for s in brief.trace]
    labels = " ".join(s.label for s in brief.trace)
    # The loop drove both tools and ended with the structured brief.
    assert "search_company" in labels and "find_decision_makers" in labels
    assert types.count("tool_call") == 2 and types.count("tool_result") == 2
    assert types[-1] == "final"
