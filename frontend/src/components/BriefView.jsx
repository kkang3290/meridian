// Renders the structured lead brief. The one-line opener gets visual weight —
// it's the part a salesperson actually copies and sends.

function Field({ label, value }) {
  if (!value) return null;
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <span className="field-value">{value}</span>
    </div>
  );
}

export default function BriefView({ brief }) {
  const c = brief.company_overview;
  return (
    <section className="brief">
      <div className="card">
        <h2>{c.name}</h2>
        <div className="fields">
          <Field label="官网" value={c.website} />
          <Field label="行业" value={c.industry} />
          <Field label="规模" value={c.size} />
          <Field label="总部" value={c.headquarters} />
        </div>
        <p className="summary">{c.summary}</p>
      </div>

      <div className="card">
        <h3>可能的痛点</h3>
        <ul className="bullets">
          {brief.pain_points.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h3>推荐的出海 / 外联切入点</h3>
        <ol className="bullets numbered">
          {brief.outreach_angles.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ol>
      </div>

      <div className="card opener-card">
        <h3>一句话开场白</h3>
        <blockquote className="opener">{brief.outreach_opener}</blockquote>
        <button
          className="copy-btn"
          type="button"
          onClick={() => navigator.clipboard?.writeText(brief.outreach_opener)}
        >
          复制
        </button>
      </div>
    </section>
  );
}
