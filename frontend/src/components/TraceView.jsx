// Renders the agent's tool-call / thinking trace as a collapsible timeline.
// This is what shows the reviewer *how* the agent worked, not just the result.
import { useState } from "react";

const META = {
  thinking: { icon: "💭", cls: "t-thinking", name: "思考" },
  tool_call: { icon: "🔧", cls: "t-tool-call", name: "工具调用" },
  tool_result: { icon: "📥", cls: "t-tool-result", name: "工具返回" },
  final: { icon: "✅", cls: "t-final", name: "生成简报" },
};

function StepBody({ step }) {
  return (
    <>
      {step.detail && <p className="step-detail">{step.detail}</p>}
      {step.data != null && (
        <pre className="step-data">{JSON.stringify(step.data, null, 2)}</pre>
      )}
    </>
  );
}

export default function TraceView({ trace, usedStub }) {
  const [open, setOpen] = useState(true);
  if (!trace || trace.length === 0) return null;

  return (
    <section className="trace">
      <div className="trace-head">
        <h3>
          Agent 轨迹
          <span className="count">{trace.length} 步</span>
          {usedStub && <span className="badge stub">stub 模式</span>}
          {!usedStub && <span className="badge live">Claude</span>}
        </h3>
        <button className="toggle" type="button" onClick={() => setOpen((o) => !o)}>
          {open ? "收起" : "展开"}
        </button>
      </div>

      {open && (
        <ol className="timeline">
          {trace.map((step, i) => {
            const m = META[step.type] || { icon: "•", cls: "", name: step.type };
            return (
              <li key={i} className={`step ${m.cls}`}>
                <div className="step-head">
                  <span className="step-icon">{m.icon}</span>
                  <span className="step-kind">{m.name}</span>
                  <span className="step-label">{step.label}</span>
                </div>
                <StepBody step={step} />
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
