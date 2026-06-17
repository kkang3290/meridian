"""The lead-research agent.

Two entry points share the same output shape (`LeadBrief`):
  - `_run_with_claude`: a manual agentic loop so every step (thinking, tool
    call, tool result, final) is captured into a trace the reviewer can read.
  - `_run_stub`: a deterministic stand-in used when no API key is present, so
    the full stack runs with zero setup. It mimics the same trace shape.

`run_lead_agent` picks between them based on whether a client is available.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import MAX_TOKENS, MAX_TOOL_ITERS, MODEL
from ..schemas import CompanyOverview, Contact, LeadBrief, TraceStep
from .llm import get_client
from .tools import (
    FIND_DECISION_MAKERS_TOOL,
    SEARCH_COMPANY_TOOL,
    find_decision_makers,
    search_company,
)

# Tools advertised to the model, and the name -> executor dispatch the loop uses
# when the model picks one. Adding a tool is: append its schema here + a row in
# EXECUTORS; the loop is otherwise tool-agnostic.
TOOLS = [SEARCH_COMPANY_TOOL, FIND_DECISION_MAKERS_TOOL]
EXECUTORS = {
    "search_company": lambda inp, fallback: search_company(inp.get("query", fallback)),
    "find_decision_makers": lambda inp, fallback: find_decision_makers(inp.get("company", fallback)),
}


class AgentError(Exception):
    """Expected, user-facing agent failure (refusal, truncation, bad output).

    Carries a message safe to show the client; the API maps it to a 502.
    """


SYSTEM_PROMPT = """\
你是子午线（Meridian）的 AI 销售研究助手，专注于帮助企业完成「B2B 出海获客」。
给定一个目标公司（名称 / 网址 / 一句话描述），你的工作是产出一份对真实销售有用的「销售线索简报」。

工作方式：
1. 先调用 search_company 工具收集该公司的事实信息（行业、规模、总部、产品、近期信号等），不要凭空臆测。
2. 再调用 find_decision_makers 工具找到该公司值得对接的关键决策人（姓名、职位）。
3. 基于工具返回的数据进行推理，识别该公司在「出海 / 增长」过程中可能遇到的真实痛点。
4. 给出具体、可执行的出海 / 外联切入点，以及一句自然、个性化、非模板化的开场白；若已知关键联系人，开场白可自然地点名相关角色。

要求：内容务实、贴近销售场景；痛点要由数据支撑；开场白要像真人写的、能直接发出去。"""

# Structured-output schema for phase 2. The schema stays strict (every property
# required, additionalProperties false); optional facts are made nullable via
# anyOf so the model can omit unknown values without breaking validation.
LEAD_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "company_overview": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                # Optional facts use anyOf(string|null) rather than a JSON-Schema
                # type-array — structured outputs documents anyOf but not
                # `{"type": ["string","null"]}`, which can be rejected at compile.
                "website": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "industry": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "size": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "headquarters": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "summary": {"type": "string"},
            },
            "required": ["name", "website", "industry", "size", "headquarters", "summary"],
            "additionalProperties": False,
        },
        "pain_points": {"type": "array", "items": {"type": "string"}},
        "outreach_angles": {"type": "array", "items": {"type": "string"}},
        "outreach_opener": {"type": "string"},
        "key_contacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                    "linkedin": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["name", "title", "linkedin", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "company_overview",
        "pain_points",
        "outreach_angles",
        "outreach_opener",
        "key_contacts",
    ],
    "additionalProperties": False,
}


def run_lead_agent(user_input: str) -> LeadBrief:
    """Produce a structured lead brief for the given company input."""
    client = get_client()
    if client is None:
        return _run_stub(user_input)
    return _run_with_claude(client, user_input)


# --------------------------------------------------------------------------- #
# Real agent: manual loop over the Claude Messages API.
# --------------------------------------------------------------------------- #
def _run_with_claude(client: Any, user_input: str) -> LeadBrief:
    trace: list[TraceStep] = []
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"目标公司输入：{user_input}\n\n请研究该公司并准备销售线索简报。"}
    ]

    # Phase 1 — gather: let the model call the tools until it's satisfied.
    for _ in range(MAX_TOOL_ITERS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            thinking={"type": "adaptive", "display": "summarized"},
            messages=messages,
        )

        tool_uses = []
        for block in response.content:
            if block.type == "thinking" and getattr(block, "thinking", ""):
                trace.append(TraceStep(type="thinking", label="模型推理", detail=block.thinking))
            elif block.type == "tool_use":
                tool_uses.append(block)
                trace.append(
                    TraceStep(
                        type="tool_call",
                        label=f"调用工具 {block.name}",
                        data=block.input,
                    )
                )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for tu in tool_uses:
            executor = EXECUTORS.get(tu.name)
            if executor is None:
                result: Any = {"error": f"unknown tool: {tu.name}"}
            else:
                result = executor(tu.input, user_input)
            trace.append(
                TraceStep(
                    type="tool_result",
                    label=f"{tu.name} 返回结果",
                    detail=result.get("name") or result.get("company"),
                    data=result,
                )
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
        messages.append({"role": "user", "content": tool_results})

    # Phase 2 — structure: force the four output fields as validated JSON.
    messages.append(
        {
            "role": "user",
            "content": "现在，基于以上调研，输出最终的结构化销售线索简报。",
        }
    )
    final = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"format": {"type": "json_schema", "schema": LEAD_BRIEF_SCHEMA}},
        messages=messages,
    )
    for block in final.content:
        if block.type == "thinking" and getattr(block, "thinking", ""):
            trace.append(TraceStep(type="thinking", label="模型推理（整理简报）", detail=block.thinking))

    # Guard the structured turn: a refusal or a max_tokens truncation yields no
    # parseable JSON. Fail with a clear message instead of a StopIteration /
    # JSONDecodeError surfacing as an opaque 500.
    if final.stop_reason == "refusal":
        raise AgentError("模型拒绝了该请求（safety refusal），请换一个输入再试。")

    payload_text = next((b.text for b in final.content if b.type == "text"), None)
    if payload_text is None:
        raise AgentError(f"未能生成结构化简报（stop_reason={final.stop_reason}）。")
    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        # Most likely cause: output truncated at max_tokens.
        raise AgentError(
            f"结构化输出解析失败（stop_reason={final.stop_reason}），可能因输出被截断。"
        ) from exc
    trace.append(TraceStep(type="final", label="生成结构化简报", data=data))

    return LeadBrief(
        company_overview=CompanyOverview(**data["company_overview"]),
        pain_points=data["pain_points"],
        outreach_angles=data["outreach_angles"],
        outreach_opener=data["outreach_opener"],
        key_contacts=[Contact(**c) for c in data.get("key_contacts", [])],
        trace=trace,
        used_stub=False,
    )


# --------------------------------------------------------------------------- #
# Stub agent: deterministic, no API key required. Mirrors the trace shape.
# --------------------------------------------------------------------------- #
def _run_stub(user_input: str) -> LeadBrief:
    trace: list[TraceStep] = [
        TraceStep(
            type="thinking",
            label="模型推理",
            detail=(
                "未配置 ANTHROPIC_API_KEY，使用确定性 stub。先用 search_company 收集事实，"
                "再用 find_decision_makers 找关键联系人，最后据此撰写简报。"
            ),
        ),
        TraceStep(type="tool_call", label="调用工具 search_company", data={"query": user_input}),
    ]
    record = search_company(user_input)
    trace.append(
        TraceStep(
            type="tool_result",
            label="search_company 返回结果",
            detail=record.get("name"),
            data=record,
        )
    )

    name = record["name"]
    industry = record.get("industry", "")
    hq = record.get("headquarters", "")
    products = record.get("products", [])
    signals = record.get("recent_signals", [])

    # Second tool call — mirrors the real multi-tool loop.
    trace.append(TraceStep(type="tool_call", label="调用工具 find_decision_makers", data={"company": name}))
    dm = find_decision_makers(name)
    contacts = [Contact(**c) for c in dm["contacts"]]
    trace.append(
        TraceStep(
            type="tool_result",
            label="find_decision_makers 返回结果",
            detail=f"{len(contacts)} 位联系人",
            data=dm,
        )
    )
    top = contacts[0] if contacts else None

    overview = CompanyOverview(
        name=name,
        website=record.get("website"),
        industry=industry or None,
        size=record.get("size"),
        headquarters=hq or None,
        summary=(
            f"{name} 是一家{('总部位于 ' + hq + ' 的') if hq else ''}{industry or 'B2B'}公司，"
            f"主营 {('、'.join(products) if products else '核心产品')}。"
            + (f"近期信号：{signals[0]}。" if signals else "")
        ),
    )

    pain_points = [
        f"{industry or '该行业'}出海时常面临本地化获客渠道不足、缺乏可信的海外销售线索。",
        "跨境拓展中销售团队对目标市场的客户画像与触达节奏把握不准，转化效率低。",
    ]
    if signals:
        pain_points.append(f"结合近期信号「{signals[0]}」，其增长阶段对高质量出海线索的需求尤为迫切。")

    outreach_angles = [
        f"以「帮助 {name} 用 AI Agent 自动化完成海外 B2B 获客」为核心价值切入。",
        "针对其正在拓展的目标市场，提供按行业/地区筛选的精准线索与自动外联工作流。",
        "用一次小范围试点（如 50 条目标客户 + 自动开场白）证明 ROI，再谈规模化。",
    ]

    greeting = f"你好 {top.name}（{top.title}），" if top else "你好，"
    opener = (
        f"{greeting}注意到 {name} 正在{('（' + signals[0] + '）') if signals else ''}加速增长——"
        f"我们用 AI Agent 帮{industry or 'B2B'}公司自动化完成海外获客与外联，"
        f"想用 15 分钟聊聊能否为你们的出海管道每周稳定产出一批高质量线索？"
    )

    trace.append(
        TraceStep(
            type="final",
            label="生成结构化简报（stub）",
            data={"note": "由 stub 基于两次工具返回数据确定性生成"},
        )
    )

    return LeadBrief(
        company_overview=overview,
        pain_points=pain_points,
        outreach_angles=outreach_angles,
        outreach_opener=opener,
        key_contacts=contacts,
        trace=trace,
        used_stub=True,
    )
