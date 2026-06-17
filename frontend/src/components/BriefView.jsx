// Renders the structured lead brief. The one-line opener gets visual weight —
// it's the part a salesperson actually copies and sends.
import { useState } from "react";

function Field({ label, value }) {
  if (!value) return null;
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <span className="field-value">{value}</span>
    </div>
  );
}

function ContactsCard({ contacts }) {
  if (!contacts || contacts.length === 0) return null;
  return (
    <div className="card">
      <h3>关键联系人</h3>
      <ul className="contacts">
        {contacts.map((c, i) => (
          <li key={i} className="contact">
            <div className="contact-head">
              <span className="contact-name">{c.name}</span>
              <span className="contact-title">{c.title}</span>
            </div>
            {c.note && <p className="contact-note">{c.note}</p>}
            {c.linkedin && (
              <a
                className="contact-link"
                href={`https://${c.linkedin.replace(/^https?:\/\//, "")}`}
                target="_blank"
                rel="noreferrer"
              >
                {c.linkedin}
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function OpenerCard({ opener }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard?.writeText(opener);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable (e.g. non-HTTPS) — leave the button as-is
    }
  }

  return (
    <div className="card opener-card">
      <h3>一句话开场白</h3>
      <blockquote className="opener">{opener}</blockquote>
      <button className="copy-btn" type="button" onClick={copy}>
        {copied ? "已复制 ✓" : "复制"}
      </button>
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

      <ContactsCard contacts={brief.key_contacts} />

      <OpenerCard opener={brief.outreach_opener} />
    </section>
  );
}
