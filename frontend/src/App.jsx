import { useState } from "react";
import { postLead } from "./api/client.js";
import BriefView from "./components/BriefView.jsx";
import TraceView from "./components/TraceView.jsx";

const EXAMPLES = ["Northwind Logistics", "Lumen Analytics", "https://acme-robotics.com"];

export default function App() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function runLookup(value) {
    const query = (value ?? input).trim();
    if (!query || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await postLead(query);
      setResult(data);
    } catch (err) {
      setError(err.message || "出错了，请重试。");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    runLookup();
  }

  return (
    <div className="page">
      <header className="header">
        <h1>AI 销售线索助手</h1>
        <p className="subtitle">
          输入目标公司的<strong>名称 / 官网 / 一句话描述</strong>，AI Agent 会调研并生成结构化的出海销售简报。
        </p>
      </header>

      <form className="search" onSubmit={onSubmit}>
        <input
          type="text"
          value={input}
          placeholder="例如：Northwind Logistics 或 https://acme.com"
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? "调研中…" : "生成简报"}
        </button>
      </form>

      <div className="examples">
        <span>试试：</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="chip"
            type="button"
            disabled={loading}
            onClick={() => {
              setInput(ex);
              runLookup(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>

      {loading && (
        <div className="state">
          <div className="spinner" />
          <span>Agent 正在调用工具并整合结果…</span>
        </div>
      )}

      {error && (
        <div className="state error">
          <strong>请求失败：</strong> {error}
        </div>
      )}

      {result && !loading && (
        <div className="results">
          <BriefView brief={result} />
          <TraceView trace={result.trace} usedStub={result.used_stub} />
        </div>
      )}
    </div>
  );
}
