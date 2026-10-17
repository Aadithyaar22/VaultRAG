import { useEffect, useState } from "react";
import { api, AuditEvent, User } from "../api";
import { Badge, Card, PageHeader, Stat, statusTone } from "../components/ui";

export default function Dashboard({ user, desc }: { user: User; desc: string }) {
  const [s, setS] = useState<any>(null);
  const [ev, setEv] = useState<AuditEvent[]>([]);
  const reviewer = user.capabilities.includes("review_security");

  useEffect(() => {
    const load = () => {
      api("/api/stats").then(setS).catch(() => {});
      if (reviewer) api<AuditEvent[]>("/api/security/events?limit=8").then(setEv).catch(() => {});
    };
    load(); const t = setInterval(load, 4000); return () => clearInterval(t);
  }, [reviewer]);

  if (!s) return <p className="text-slate-400">Loading…</p>;
  return (
    <div className="mx-auto grid max-w-5xl gap-5">
      <PageHeader title="Dashboard" desc={desc} right={<div className="flex gap-2"><Badge tone="ok">live measurements</Badge><Badge tone="mute">{s.scope === "all_users" ? "all users" : "your activity only"}</Badge></div>} />
      <p className="text-xs text-slate-500">{s.source}</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Documents you can read" value={s.documents} />
        <Stat label="Queries processed" value={s.queries} />
        <Stat label="Blocked responses" value={s.blocked} />
        <Stat label="Abstentions" value={s.abstained} />
        <Stat label="Revocation events" value={s.revocation_events} />
        <Stat label="Stale-cache rejections" value={s.stale_cache_rejections} />
        <Stat label="Injection detections" value={s.injection_detections} />
        <Stat label="Cache invalidations" value={s.cache_invalidations ?? "—"} hint={s.cache_invalidations == null ? "reviewers only" : undefined} />
      </div>
      {reviewer && (
        <>
          <Card title="Audit chain integrity" right={s.audit_chain && <Badge tone={s.audit_chain.valid ? "ok" : "bad"}>{s.audit_chain.valid ? "verified" : "BROKEN"}</Badge>}>
            <p className="text-xs text-slate-400">{s.audit_chain?.entries} hash-linked entries · head <code>{s.audit_chain?.head.slice(0, 16)}…</code> (tamper-evident, not immutable)</p>
          </Card>
          <Card title="Recent security events">
            <ul className="grid gap-1 text-sm">{ev.map(e => (
              <li key={e.seq} className="flex flex-wrap items-center gap-2"><Badge tone={statusTone(e.outcome)}>{e.outcome}</Badge>
                <span className="font-mono text-xs">{e.event_type}</span><span className="text-xs text-slate-500">{new Date(e.ts).toLocaleTimeString()}</span></li>))}</ul>
          </Card>
        </>
      )}
    </div>
  );
}
