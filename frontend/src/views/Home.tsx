import { ReactNode, useEffect, useState } from "react";
import { api, User } from "../api";
import { Badge, Button, Card, PageHeader, icons } from "../components/ui";

export type GuideItem = { id: string; label: string; desc: string; icon: ReactNode; cap?: string; who?: string; can?: string[] };

const STEPS: [string, string][] = [
  ["Ask", "You type a question in plain language."],
  ["Check permissions", "The server works out which documents your role may read — before anything is searched."],
  ["Answer with sources", "The model sees only those documents and cites the passages it used."],
  ["Final re-check", "Just before release, every source is verified again. If access changed, the answer is discarded."],
];

export default function Home({ user, desc, all, go }: { user: User; desc: string; all: GuideItem[]; go: (id: any) => void }) {
  const [docs, setDocs] = useState<number | null>(null);
  useEffect(() => { api("/api/stats").then(s => setDocs(s.documents)).catch(() => {}); }, []);
  const guide = all.filter(g => g.id !== "home");

  return (
    <div className="mx-auto grid max-w-5xl gap-6">
      <PageHeader title="Home" desc={desc} />

      <Card title="Your access" right={docs !== null && <Badge tone="info">{docs} document{docs === 1 ? "" : "s"} readable</Badge>}>
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-display text-lg font-semibold text-white">{user.display_name}</span>
          {user.roles.map(r => <Badge key={r} tone="info">{r}</Badge>)}
        </div>
        <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-slate-300">
          What you can read, and which menus you can use, depends on these roles. Menus marked as restricted below are shown so you know they exist, but they open only for the roles named.
        </p>
      </Card>

      <section aria-labelledby="how">
        <h2 id="how" className="mb-4 font-display text-xl font-semibold text-white">How an answer is protected</h2>
        <ol className="grid gap-4 md:grid-cols-4">
          {STEPS.map(([t, d], i) => (
            <li key={t} className="liquid-flat p-5">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full border border-white/40 font-display text-sm font-bold text-white">{i + 1}</div>
              <div className="font-display text-base font-semibold text-white">{t}</div>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{d}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="menus">
        <h2 id="menus" className="mb-1 font-display text-xl font-semibold text-white">What each menu is for</h2>
        <p className="mb-4 text-sm text-slate-400">The bar at the top is your navigation. Here is what each item does and what you can do in it.</p>
        <div className="grid gap-4 md:grid-cols-2">
          {guide.map(g => {
            const open = !g.cap || user.capabilities.includes(g.cap);
            return (
              <div key={g.id} className={`liquid p-6 ${open ? "" : "opacity-70"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white">{g.icon}</span>
                    <h3 className="font-display text-lg font-semibold text-white">{g.label}</h3>
                  </div>
                  {!open && <Badge tone="warn">{g.who || "Restricted"}</Badge>}
                </div>
                <p className="mt-3 text-[15px] leading-relaxed text-slate-300">{g.desc}</p>
                <ul className="mt-4 grid gap-2 text-sm text-slate-300">
                  {g.can?.map(c => (
                    <li key={c} className="flex gap-2.5"><span className="mt-2 h-1 w-3 shrink-0 rounded-full bg-white/70" aria-hidden /><span>{c}</span></li>
                  ))}
                </ul>
                <div className="mt-5">
                  {open
                    ? <Button variant="ghost" className="!py-2" onClick={() => go(g.id)}>Open {g.label} {icons.arrow}</Button>
                    : <span className="text-xs text-slate-500">Available to {g.who?.toLowerCase() || "other roles"}.</span>}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Card title="Reading the status badges">
        <p className="mb-4 max-w-3xl text-sm leading-relaxed text-slate-400">Status is shown by shape and weight, so it reads the same in any lighting and for everyone.</p>
        <ul className="grid gap-4 md:grid-cols-3">
          <li className="flex items-start gap-3"><Badge tone="ok">Released</Badge><span className="text-sm text-slate-300">Filled dot. The answer passed the final check and is shown.</span></li>
          <li className="flex items-start gap-3"><Badge tone="warn">Abstained</Badge><span className="text-sm text-slate-300">Dashed outline. Nothing you may read answers the question, so nothing is shared.</span></li>
          <li className="flex items-start gap-3"><Badge tone="bad">Blocked</Badge><span className="text-sm text-slate-300">Solid cream. The answer was discarded, for example because access changed or a check could not complete.</span></li>
        </ul>
      </Card>
    </div>
  );
}
