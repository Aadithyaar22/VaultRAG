import { useEffect, useState } from "react";
import { api, AuditEvent } from "../api";
import { Badge, Button, Card, statusTone } from "../components/ui";

const FILTERS = ["", "response_blocked", "revocation_detected_before_release", "stale_cache_rejected", "prompt_injection_quarantined", "prompt_injection_detected_on_upload", "permission_changed", "cache_invalidated", "response_released"];

export default function Security() {
  const [ev, setEv] = useState<AuditEvent[]>([]);
  const [f, setF] = useState("");
  const [v, setV] = useState<any>(null);
  const [pol, setPol] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [risk, setRisk] = useState<any>(null);
  const [mlst, setMlst] = useState<any>(null);
  useEffect(() => {
    const t = () => api("/api/security/risk").then(setRisk).catch(() => {});
    t(); const i = setInterval(t, 4000); api("/api/ml/status").then(setMlst).catch(() => {}); return () => clearInterval(i);
  }, []);
  const load = () => api<AuditEvent[]>(`/api/security/events?limit=150${f ? `&event_type=${f}` : ""}`).then(setEv);
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [f]);
  useEffect(() => { api("/api/security/pii-policy").then(setPol); }, []);
  const savePol = (p: any) => api("/api/security/pii-policy", { method: "PUT", body: p }).then(setPol).catch(e => alert(e.message));

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <h1 className="text-xl font-semibold text-white">Security Center</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Audit chain" right={v && <Badge tone={v.valid ? "ok" : "bad"}>{v.valid ? "valid" : `broken @ seq ${v.first_bad_seq}`}</Badge>}>
          <Button variant="ghost" onClick={() => api("/api/security/audit/verify").then(setV)}>Verify hash chain</Button>
          {v && <p className="mt-2 text-xs text-slate-400">{v.entries} entries · head {v.head.slice(0, 20)}…</p>}
        </Card>
        {pol && (
          <Card title="PII response policy">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <label>Mode <select aria-label="PII mode" className="rounded border border-line bg-ink px-2 py-1" value={pol.mode} onChange={e => savePol({ ...pol, mode: e.target.value })}>
                {["redact", "block", "off"].map(m => <option key={m}>{m}</option>)}</select></label>
              <span className="text-xs text-slate-400">exempt roles: {pol.exempt_roles.join(", ") || "none"}</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Redaction supplements — never replaces — authorization.</p>
          </Card>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="🤖 User risk (IsolationForest, last 10 min)" right={<Badge tone="info">anomaly detection</Badge>}>
          {!risk || risk.users.length === 0 ? <p className="text-sm text-slate-400">No recent activity.</p> : (
            <ul className="grid gap-2 text-sm">{risk.users.map((u: any) => (
              <li key={u.user_id} className="flex flex-wrap items-center gap-2">
                <Badge tone={u.level === "high" ? "bad" : u.level === "elevated" ? "warn" : "ok"}>{u.level} · {u.risk}</Badge>
                <span className="font-mono text-xs">{u.user_id}</span>
                <span className="text-xs text-slate-400">{u.queries} queries · {u.denied_or_abstained} denied/abstained · {u.injection_events} injection</span>
              </li>))}</ul>)}
          <p className="mt-2 text-xs text-slate-500">Score = share of simulated normal activity windows that look more normal. Trained on synthetic baselines — a demo, not a calibrated detector.</p>
        </Card>
        {mlst?.available && (
          <Card title="Models running on this server" right={<Badge tone="ok">{mlst.platform} · {mlst.byteorder}-endian</Badge>}>
            <p className="text-xs text-slate-400">scikit-learn {mlst.sklearn} · Python {mlst.python} · trained at startup in {mlst.train_seconds}s ({Object.entries(mlst.sizes).map(([k, v]) => `${k}: ${v}`).join(", ")})</p>
            <table className="mt-2 w-full text-xs"><tbody>
              {Object.entries(mlst.evaluation.injection).filter(([k]) => k !== "note").map(([k, v]: any) => (
                <tr key={k}><td className="py-0.5 text-slate-300">injection · {k.replace("_", " ")}</td><td>recall {v.recall}</td><td>false pos {v.false_positives}</td></tr>))}
              <tr><td className="py-0.5 text-slate-300">document classifier</td><td>dept {mlst.evaluation.document_classifier.department_correct}</td><td>sens {mlst.evaluation.document_classifier.sensitivity_correct}</td></tr>
            </tbody></table>
            <p className="mt-2 text-xs text-slate-500">{mlst.evaluation.injection.note}</p>
          </Card>)}
      </div>
      <Card title="Security events" right={<select aria-label="Filter events" className="rounded border border-line bg-ink px-2 py-1 text-sm" value={f} onChange={e => setF(e.target.value)}>
        {FILTERS.map(x => <option key={x} value={x}>{x || "all events"}</option>)}</select>}>
        <ul className="divide-y divide-line">
          {ev.map(e => (
            <li key={e.seq} className="py-2 text-sm">
              <button className="flex w-full flex-wrap items-center gap-2 text-left" onClick={() => setOpen(open === e.seq ? null : e.seq)}>
                <Badge tone={statusTone(e.outcome)}>{e.outcome}</Badge><span className="font-mono text-xs">{e.event_type}</span>
                <span className="text-xs text-slate-500">{new Date(e.ts).toLocaleTimeString()} · {e.user_id || "system"} {e.request_id && `· ${e.request_id}`}</span>
              </button>
              {open === e.seq && <pre className="mt-2 overflow-x-auto rounded bg-ink p-2 text-xs text-slate-300">{JSON.stringify(e.detail, null, 2)}{"\n"}hash {e.hash.slice(0, 24)}…</pre>}
            </li>
          ))}
          {ev.length === 0 && <li className="py-2 text-slate-400">No events.</li>}
        </ul>
      </Card>
    </div>
  );
}
