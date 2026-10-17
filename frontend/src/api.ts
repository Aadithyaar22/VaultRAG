export type User = { id: string; username: string; display_name: string; roles: string[]; capabilities: string[] };
export type Citation = { n: number; doc_id: string; title: string; doc_version: number; chunk_id: string; passage: string };
export type ChatResult = {
  request_id: string; status: "answered" | "abstained" | "denied" | "error"; answer: string; citations: Citation[];
  reason: string | null; cache: string; latency_ms: number;
  security: Record<string, any>; llm: { provider: string; generative: boolean } | null;
};
export type AuditEvent = { seq: number; ts: string; event_type: string; request_id: string | null; user_id: string | null; outcome: string; detail: Record<string, any>; hash: string };

let token = sessionStorage.getItem("vr_token") || "";
export const setToken = (t: string) => { token = t; t ? sessionStorage.setItem("vr_token", t) : sessionStorage.removeItem("vr_token"); };
export const hasToken = () => !!token;

export class ApiError extends Error { constructor(public status: number, msg: string) { super(msg); } }

export async function api<T = any>(path: string, opts: { method?: string; body?: any; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }
  const r = await fetch(path, { method: opts.method || (body ? "POST" : "GET"), headers, body });
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new ApiError(r.status, msg);
  }
  return r.json();
}
