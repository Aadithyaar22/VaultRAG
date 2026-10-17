import { useEffect, useState } from "react";
import { api, ChatResult } from "../api";
import { Badge, Button, Card, ErrorNote, statusTone } from "../components/ui";

const USERS = ["alice", "hannah", "frank", "leo", "maya", "adam"];
const Q = "How many weeks of paid parental leave do primary caregivers receive?";

export default function Demo() {
  const [who, setWho] = useState("hannah");
  const [q, setQ] = useState(Q);
  const [out, setOut] = useState<{ title: string; data: any } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [state, setState] = useState<any>(null);
  const refresh = () => api("/api/admin/demo/state").then(setState).catch(() => {});
  useEffect(() => { refresh(); }, []);
  const act = async (title: string, path: string, body?: any) => {
    setErr(null);
    try { setOut({ title, data: await api(path, { method: "POST", body: body ?? {} }) }); } catch (e: any) { setErr(e.message); } finally { refresh(); }
  };
  const r: ChatResult | undefined = out?.data?.status ? out.data : out?.data?.result;

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <div className="flex items-center gap-2"><h1 className="text-xl font-semibold text-white">Administrator Demo Controls</h1><Badge tone="warn">DEMO_MODE only</Badge></div>
      <p className="text-sm text-slate-400">Drive the mandatory scenario without editing the database. Authorization is always evaluated for the <b>selected user</b>, and every action is audited.</p>
      <ErrorNote msg={err} />
      <Card title="1 · Ask as a user">
        <div className="flex flex-wrap gap-2">
          <select aria-label="Ask as" className="rounded border border-line bg-ink px-2 py-1.5 text-sm" value={who} onChange={e => setWho(e.target.value)}>{USERS.map(u => <option key={u}>{u}</option>)}</select>
          <input aria-label="Question" className="min-w-64 flex-1 rounded border border-line bg-ink px-3 py-1.5 text-sm" value={q} onChange={e => setQ(e.target.value)} />
          <Button onClick={() => act(`Ask as ${who}`, "/api/admin/demo/ask-as", { username: who, question: q })}>Ask</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">Run as <b>hannah</b> → cited answer &amp; cached. Run as <b>alice</b> → abstains (no HR evidence). Then revoke below and re-run as hannah.</p>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="2 · Revoke during generation"><p className="mb-2 text-xs text-slate-400">Answer is generated, then access is revoked just before the gate. Expect: discard → regenerate from authorized evidence or deny.</p>
          <Button variant="danger" onClick={() => act("Revoke during generation", "/api/admin/demo/revoke-during-generation", { username: who, question: q })}>Run race for “{who}”</Button></Card>
        <Card title="3 · Authorization service" right={state && <Badge tone={state.authz_available ? "ok" : "bad"}>{state.authz_available ? "available" : "DOWN"}</Badge>}>
          <p className="mb-2 text-xs text-slate-400">While down, every request fails closed — including cached answers.</p>
          <div className="flex gap-2"><Button variant="danger" onClick={() => act("Simulate outage", "/api/admin/demo/authz-outage", { down: true })}>Simulate outage</Button>
            <Button variant="ghost" onClick={() => act("Restore authz", "/api/admin/demo/authz-outage", { down: false })}>Restore</Button></div></Card>
        <Card title="4b · Probing attack (anomaly detection)"><p className="mb-2 text-xs text-slate-400">Fires 12 restricted-topic questions as “{who}” (all denied/abstained). Watch the user's risk score jump in Security Center.</p>
          <Button variant="danger" onClick={() => act("Simulate probing", "/api/admin/demo/simulate-probing", { username: who, n: 12 })}>Simulate probing as “{who}”</Button></Card>
        <Card title="4 · Malicious document"><p className="mb-2 text-xs text-slate-400">Uploads a note containing override/exfiltration instructions. It is flagged, quarantined from the model context, and audited.</p>
          <Button variant="ghost" onClick={() => act("Upload malicious document", "/api/admin/demo/upload-malicious")}>Upload poisoned document</Button></Card>
        <Card title="5 · Housekeeping" right={state && <Badge tone="mute">{state.cache_entries} cached</Badge>}><div className="flex gap-2">
          <Button variant="ghost" onClick={() => act("Clear cache", "/api/admin/demo/clear-cache")}>Clear cache</Button>
          <Button variant="ghost" onClick={() => confirm("Reset all demo data and audit log?") && act("Reset demo", "/api/admin/demo/reset")}>Reset demo data</Button></div></Card>
      </div>
      {out && (
        <Card title={`Result — ${out.title}`} right={r && <Badge tone={statusTone(r.status)}>{r.status}</Badge>}>
          {r && <p className="mb-2 text-sm">{r.answer || <i>(no answer released: {r.reason})</i>}</p>}
          {out.data.trace && <ol className="mb-2 list-decimal pl-5 text-xs text-slate-300">{out.data.trace.map((e: any) => <li key={e.seq}><code>{e.event_type}</code> — {e.outcome} {e.detail?.reasons ? `(${e.detail.reasons.join(", ")})` : ""}</li>)}</ol>}
          <details><summary className="cursor-pointer text-xs text-slate-400">Raw response</summary><pre className="mt-2 overflow-x-auto rounded bg-ink p-2 text-xs">{JSON.stringify(out.data, null, 2)}</pre></details>
        </Card>
      )}
    </div>
  );
}
