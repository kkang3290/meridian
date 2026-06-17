// Thin client for the backend. Uses a relative path so the Vite dev proxy
// (or same-origin deployment) routes it to FastAPI.
export async function postLead(input) {
  const res = await fetch("/api/lead", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input }),
  });

  if (!res.ok) {
    let detail = `请求失败（HTTP ${res.status}）`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new Error(detail);
  }
  return res.json();
}
