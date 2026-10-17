import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorNote, PageHeader } from "../components/ui";

const ROLES = ["employee", "hr", "finance", "legal", "administrator"];

export default function Users({ desc }: { desc: string }) {
  const [users, setUsers] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const load = () => api("/api/admin/users").then(setUsers).catch(e => setErr(e.message));
  useEffect(() => { load(); }, []);
  async function toggle(u: any, r: string) {
    const roles = u.roles.includes(r) ? u.roles.filter((x: string) => x !== r) : [...u.roles, r];
    setErr(null);
    try { await api(`/api/admin/users/${u.id}/roles`, { method: "PUT", body: { roles } }); load(); } catch (e: any) { setErr(e.message); }
  }
  return (
    <div className="mx-auto grid max-w-4xl gap-5">
      <PageHeader title="Users & Roles" desc={desc} />
      <p className="-mt-4 max-w-2xl text-sm text-slate-400">The <b className="text-slate-200">administrator</b> role grants management capabilities, not access to document contents.</p>
      <ErrorNote msg={err} />
      {users.map(u => (
        <Card key={u.id} title={<span>{u.display_name} <span className="text-xs text-slate-500">@{u.username}</span></span>} right={<Badge tone="mute">authz v{u.authz_version}</Badge>}>
          <div className="flex flex-wrap gap-3 text-sm">{ROLES.map(r => <label key={r} className="flex items-center gap-1"><input type="checkbox" checked={u.roles.includes(r)} onChange={() => toggle(u, r)} />{r}</label>)}</div>
        </Card>
      ))}
    </div>
  );
}
