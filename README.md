# Mini Lead Assistant · AI 销售线索助手

输入一个目标公司的**名称 / 官网 / 一句话描述**，后端的**带工具调用的 LLM Agent** 会调研该公司并产出结构化的「出海销售线索简报」，前端展示**简报**与 Agent 的**工具调用 / 思考轨迹**。

这是子午线（Meridian）全栈工程师 take-home 的实现。

---

## 它能做什么

- **输入**：公司名（`Northwind Logistics`）、网址（`https://acme-robotics.com`）或一句话描述。
- **Agent**：一个最小但真实的 Agent 循环 —— 由 LLM 决定调用 `search_company` 工具收集事实，再据此推理。
- **结构化输出**：公司概况、可能的痛点、推荐的出海/外联切入点、一句话开场白（outreach opener）。
- **轨迹**：返回完整的 thinking / tool_call / tool_result / final 轨迹，前端以时间线展示。
- **零配置可运行**：未设置 `ANTHROPIC_API_KEY` 时自动走**确定性 stub**，全栈可在无密钥、无网络的情况下跑通。

---

## 快速开始

需要 Python 3.10+ 和 Node 18+。开两个终端。

### 1) 后端（FastAPI，默认 8000 端口）

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 可选：使用真实 Claude Agent。不设置则走 stub。
cp .env.example .env          # 然后在 .env 里填入 ANTHROPIC_API_KEY
# 或：export ANTHROPIC_API_KEY=sk-ant-...

uvicorn app.main:app --reload --port 8000
```

健康检查：`curl localhost:8000/api/health` → `{"status":"ok","llm":"stub"}`（或 `"claude"`）。

### 2) 前端（Vite + React，默认 5173 端口）

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 。前端通过 Vite 代理把 `/api` 转发到后端 `:8000`，无需额外配置 CORS。

### 直接调 API

```bash
curl -X POST localhost:8000/api/lead \
  -H 'Content-Type: application/json' \
  -d '{"input":"Northwind Logistics"}'
```

### 测试

后端带一组 hermetic 的 smoke 测试（走 stub 路径，无需密钥）：

```bash
cd backend && source .venv/bin/activate && pytest -q
```

覆盖：响应契约（四个字段齐全）、轨迹中包含完整的 tool_call → tool_result → final、空输入被拒（422）、以及工具的 URL 解析与确定性。

---

## API

`POST /api/lead`

```jsonc
// 请求
{ "input": "Northwind Logistics" }

// 响应（节选）
{
  "company_overview": {
    "name": "Northwind Logistics",
    "website": "northwindlogistics.com",
    "industry": "Freight forwarding & supply-chain software",
    "size": "约 400 人",
    "headquarters": "Rotterdam, Netherlands",
    "summary": "..."
  },
  "pain_points": ["...", "..."],
  "outreach_angles": ["...", "..."],
  "outreach_opener": "你好，注意到 Northwind Logistics 正在...",
  "used_stub": true,
  "trace": [
    { "type": "thinking",   "label": "模型推理", "detail": "..." },
    { "type": "tool_call",  "label": "调用工具 search_company", "data": { "query": "Northwind Logistics" } },
    { "type": "tool_result","label": "search_company 返回结果", "data": { /* 公司事实 */ } },
    { "type": "final",      "label": "生成结构化简报" }
  ]
}
```

---

## Agent 设计

核心在 `backend/app/services/agent.py`。这是一个**手写的 Agent 循环**（没有用 SDK 的 tool-runner），目的就是把每一步都记录进 `trace`，让评审能看清 Agent「怎么想、怎么调工具」。

分两个阶段：

1. **Gather（调研）** —— 带 `search_company` 工具循环调用 Claude。`stop_reason == "tool_use"` 时执行工具、把结果回灌，并把 thinking / tool_call / tool_result 写入轨迹；带最大轮数上限防止失控。
2. **Structure（结构化）** —— 最后一次调用使用 `output_config.format`（JSON Schema 严格模式）强制产出四个字段的合法 JSON，无需正则解析。

**工具**（`backend/app/services/tools.py`）：`search_company(query)` 返回 mock 的公司事实。内置几个典型出海客户画像（垂直 SaaS / 制造业 / DTC 电商），其余查询用基于哈希的**确定性生成**兜底，保证 Agent 永远有可推理的数据。按作业要求，数据真假不是重点，重点是工具调用的设计与全栈打通。

**模型**：`claude-opus-4-8`，开启 adaptive thinking（`display: "summarized"`，因此轨迹里能看到思考摘要）。

---

## 设计取舍（4 小时约束下）

- **手写循环而非 tool-runner**：tool-runner 更省代码，但会把中间步骤藏起来。作业明确要看 Agent 轨迹，所以选择手写循环换取可观测性。
- **Stub 兜底**：没有密钥也能完整跑通全栈，评审零成本上手；`used_stub` 字段诚实地标注是哪条路径产出的结果。Stub 复用同一套工具与轨迹结构，不是另起一套假数据。
- **两阶段（gather → structure）**：把"调研"和"出结构化结果"分开，让结构化输出走 JSON Schema 严格校验，省掉脆弱的字符串解析，前端拿到的一定是合法结构。
- **内存即可、无数据库**：符合约束；Agent 无状态，每次请求独立。
- **Mock 工具数据**：把时间投在 Agent 循环、轨迹设计和前端联调上，而不是去接真实数据源。
- **产品 sense**：一句话开场白在前端单独高亮并可一键复制 —— 这是销售真正会拿去用的东西。

---

## 项目结构

```
backend/
  app/
    main.py              # 应用工厂：create_app() + CORS + 挂载路由
    config.py            # 设置/常量（MODEL、MAX_TOKENS、密钥读取）
    schemas.py           # Pydantic 模型（请求 / 简报 / 轨迹）
    routers/
      lead.py            # APIRouter：POST /api/lead, GET /api/health, 错误处理
    services/
      agent.py           # Agent 循环（真实 Claude）+ stub；结构化输出 schema
      tools.py           # search_company 工具 + mock 数据
      llm.py             # provider seam：有无密钥决定走真实 / stub
  tests/test_lead.py     # smoke 测试（走 stub，无需密钥）
  requirements.txt
  .env.example
frontend/
  src/
    main.jsx                 # 入口
    App.jsx                  # 输入 + loading/error/result 状态
    index.css
    api/client.js            # POST /api/lead
    components/BriefView.jsx # 简报卡片（开场白高亮 + 复制）
    components/TraceView.jsx # 可折叠的 Agent 轨迹时间线
  vite.config.js             # /api 代理到 :8000
```

---

## 实际花费时间

约 **2.5 小时**：后端 Agent 循环与工具 ~1h，前端 ~1h，联调 + README ~0.5h。

---

## 如果再多给我一天

- **真实工具**：把 `search_company` 换成真实的 web search / 抓取（保留 mock 作为离线兜底），并加入第二个工具（如 `find_contacts` 找决策人邮箱），展示多工具编排。
- **流式轨迹**：用 SSE 把 thinking / tool_call 实时推到前端，让用户看着 Agent 一步步工作，而不是等最终结果。
- **缓存与并发**：对相同公司做 prompt caching / 结果缓存；批量输入一次性生成多家简报。
- **可评估性**：在现有 smoke 测试之上加一个 eval 集（输入 → 期望字段质量），用真实 Claude 路径回归 Agent 行为；记录每次调用的 token / 耗时。
- **持久化与导出**：把简报存起来、支持导出 CSV / 推送到 CRM。
- **更强的产品化**：开场白多版本 A/B、按地区/行业的切入点模板、置信度标注（哪些来自工具、哪些是推断）。
