import { useEffect, useState } from "react";
import { api, User } from "../api";
import { Badge, Button, Card, ErrorNote, Input, PageHeader, SplitButton } from "../components/ui";

const ROLES = ["employee", "hr", "finance", "legal", "administrator"];
const SENS = ["public", "internal", "confidential", "restricted"];

export default function Vault({ user, desc }: { user: User; desc: string }) {
  const [docs, setDocs] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>(["employee"]);
  const [sens, setSens] = useState("internal");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sugg, setSugg] = useState<any>(null);
  const manage = user.capabilities.includes("manage_documents");
  async function onFile(f: File | null) {
    setFile(f); setSugg(null);
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try { const r = await api("/api/documents/suggest", { form: fd }); if (r.available) setSugg(r.prediction); } catch {}
  }
  const load = () => api("/api/documents").then(setDocs).catch(e => setErr(e.message));
  useEffect(() => { load(); }, []);

  const run = async (fn: () => Promise<any>, ok: string) => {
    setErr(null); setMsg(null);
    try { await fn(); setMsg(ok); load(); } catch (e: any) { setErr(e.message); }
  };
  const form = (extra?: Record<string, string>) => {
    const f = new FormData(); f.append("file", file!); f.append("title", title); f.append("sensitivity", sens);
    f.append("allowed_roles", roles.join(",")); Object.entries(extra || {}).forEach(([k, v]) => f.append(k, v)); return f;
  };
  const toggleRole = (d: any, r: string) => {
    const next = d.allowed_roles.includes(r) ? d.allowed_roles.filter((x: string) => x !== r) : [...d.allowed_roles, r];
    if (next.length === 0) { setErr("A document needs at least one role (remove the document instead)."); return; }
    run(() => api(`/api/documents/${d.id}/acl`, { method: "PUT", body: { allowed_roles: next } }), "Permissions updated — dependent cached answers invalidated.");
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-5">
      <PageHeader title="Document Vault" desc={desc} />
      <ErrorNote msg={err} />{msg && <div role="status" className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">{msg}</div>}
      {manage && (
        <Card title="Upload or replace a document" right={<Badge tone="mute">PDF · TXT · DOCX · ≤10 MB</Badge>}>
          <div className="grid gap-2 md:grid-cols-3">
            <Input aria-label="Title" placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} />
            <select aria-label="Sensitivity" className="rounded-lg border border-line bg-ink px-3 py-2 text-sm" value={sens} onChange={e => setSens(e.target.value)}>{SENS.map(s => <option key={s}>{s}</option>)}</select>
            <input aria-label="File" type="file" accept=".pdf,.txt,.docx" onChange={e => onFile(e.target.files?.[0] || null)} className="text-sm" />
          </div>
          {sugg && (
            <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-brand/40 bg-brand/10 px-3 py-2 text-sm" role="status">
              <Badge tone="info">AI suggestion · on-server model</Badge>
              <span>looks like <b>{sugg.department}</b> content ({Math.round(sugg.department_confidence * 100)}%), <b>{sugg.sensitivity}</b> ({Math.round(sugg.sensitivity_confidence * 100)}%) → roles: {sugg.suggested_roles.join(", ")}</span>
              <Button variant="ghost" onClick={() => { setRoles(sugg.suggested_roles); setSens(sugg.sensitivity); }}>Apply</Button>
            </div>
          )}
          <fieldset className="mt-3 flex flex-wrap gap-3 text-sm"><legend className="mb-1 text-xs text-slate-400">Roles allowed to read</legend>
            {ROLES.map(r => <label key={r} className="flex items-center gap-1"><input type="checkbox" checked={roles.includes(r)} onChange={() => setRoles(x => x.includes(r) ? x.filter(y => y !== r) : [...x, r])} />{r}</label>)}</fieldset>
          <div className="mt-4"><SplitButton label="Upload" disabled={!file || !title || roles.length === 0} onClick={async () => { setErr(null); setMsg(null); try { const r = await api("/api/documents", { form: form() }); setMsg("Uploaded, scanned for injection/PII, and indexed." + (r.ml_warning ? " Warning: " + r.ml_warning : "")); load(); } catch (e: any) { setErr(e.message); } }} menuLabel="More upload actions"
            items={[{ label: "Apply AI suggestion, then upload", hint: "Use the suggested roles and sensitivity", onClick: () => { if (sugg) { setRoles(sugg.suggested_roles); setSens(sugg.sensitivity); } setTimeout(() => (document.getElementById("vault-upload") as HTMLButtonElement | null)?.click(), 0); } },
                    { label: "Reset form", hint: "Clear file, title and roles", onClick: () => { setFile(null); setTitle(""); setRoles(["employee"]); setSens("internal"); setSugg(null); } }]} /></div>
        </Card>
      )}
      {manage && <p className="text-xs text-slate-500">Administrators manage metadata and permissions here. Reading document <i>content</i> still requires the document's ACL to grant one of your roles.</p>}
      <div className="grid gap-3">
        {docs.map(d => (
          <Card key={d.id} title={<span>{d.title} <Badge tone="mute">v{d.version}</Badge></span>}
            right={<div className="flex gap-1"><Badge tone={d.sensitivity === "restricted" ? "bad" : d.sensitivity === "confidential" ? "warn" : "info"}>{d.sensitivity}</Badge>
              {d.injection_flagged ? <Badge tone="warn">injection flagged</Badge> : null}{d.pii_count ? <Badge tone="info">{d.pii_count} PII</Badge> : null}
              {manage && !d.can_read && <Badge tone="mute">metadata only</Badge>}</div>}>
            {manage ? (
              <>
                <div className="flex flex-wrap gap-3 text-sm">{ROLES.map(r => <label key={r} className="flex items-center gap-1"><input type="checkbox" checked={d.allowed_roles.includes(r)} onChange={() => toggleRole(d, r)} />{r}</label>)}</div>
                {d.denied_users.length > 0 && <p className="mt-2 text-xs text-amber-300">Explicit deny: {d.denied_users.join(", ")}
                  <button className="ml-2 underline" onClick={() => run(() => api(`/api/documents/${d.id}/acl`, { method: "PUT", body: { denied_users: [] } }), "Explicit denies cleared.")}>clear</button></p>}
                <p className="mt-2 text-xs text-slate-500">ACL version {d.acl_version} · {d.versions.length} version(s): {d.versions.map((v: any) => `v${v.version} (${v.chunk_count} chunks, ${v.content_sha256.slice(0, 8)})`).join(" · ")}</p>
                <div className="mt-3"><SplitButton variant="ghost" label="Replace with selected file" disabled={!file} onClick={() => run(() => api(`/api/documents/${d.id}/replace`, { form: form() }), "Replaced with a new version — caches invalidated.")} menuLabel="More document actions"
                  items={[{ label: "Remove document", hint: "Deletes its text and invalidates cached answers", danger: true, onClick: () => confirm(`Remove "${d.title}"?`) && run(() => api(`/api/documents/${d.id}`, { method: "DELETE" }), "Document removed.") }]} /></div>
              </>
            ) : <p className="text-xs text-slate-400">Updated {new Date(d.updated_at).toLocaleString()}</p>}
          </Card>
        ))}
        {docs.length === 0 && <p className="text-slate-400">No documents are available to you.</p>}
      </div>
    </div>
  );
}
