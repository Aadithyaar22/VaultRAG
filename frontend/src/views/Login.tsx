import { useEffect, useState } from "react";
import { api, setToken, User } from "../api";
import { Badge, Button, Card, ErrorNote, Input, Logo, icons } from "../components/ui";

type Demo = { username: string; display_name: string; roles: string[] };
const SEES: Record<string, string> = {
  adam: "Manages documents and roles. No automatic access to HR, Finance or Legal content.",
  alice: "Employee handbook only.",
  hannah: "Handbook and HR documents.",
  frank: "Handbook and Finance documents.",
  leo: "Handbook and Legal documents.",
  maya: "HR and Finance, with one HR memo explicitly denied.",
};

export default function SignIn({ onBack, onLogin }: { onBack: () => void; onLogin: (u: User) => void }) {
  const [demo, setDemo] = useState<Demo[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api<Demo[]>("/api/auth/demo-users").then(setDemo).catch(() => {}); }, []);

  async function submit(u = username, p = password) {
    setErr(null); setBusy(true);
    try {
      const { token } = await api<{ token: string }>("/api/auth/login", { body: { username: u, password: p } });
      setToken(token);
      onLogin(await api<User>("/api/auth/me"));
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col justify-center gap-8 px-5 py-12">
      <div className="rise">
        <button onClick={onBack} className="mb-8 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white">{icons.back} Back</button>
        <div className="flex items-center gap-4"><Logo size={40} /><h1 className="font-display text-4xl font-bold tracking-tight text-white sm:text-5xl">Sign in</h1></div>
        <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-slate-300">Use your account, or open one of the synthetic demo identities below. What you can read depends on your role.</p>
      </div>

      <Card title="Account" className="rise">
        <form className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={e => { e.preventDefault(); submit(); }}>
          <Input aria-label="Username" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" />
          <Input aria-label="Password" placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
          <Button type="submit" busy={busy}>Sign in</Button>
        </form>
        <div className="mt-3"><ErrorNote msg={err} /></div>
      </Card>

      {demo.length > 0 && (
        <Card title="Demo identities" right={<Badge tone="warn">Synthetic data only</Badge>} className="rise">
          <div className="grid gap-3 sm:grid-cols-2">
            {demo.map(d => (
              <button key={d.username} onClick={() => submit(d.username, "demo-pass")} disabled={busy}
                className="liquid-flat p-4 text-left transition duration-200 hover:scale-[1.015] hover:border-teal-200/40 hover:bg-white/8 disabled:opacity-60">
                <div className="font-display text-base font-semibold text-white">{d.display_name}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">{d.roles.map(r => <Badge key={r} tone="info">{r}</Badge>)}</div>
                <p className="mt-2 text-sm leading-snug text-slate-400">{SEES[d.username] || "Role-based access."}</p>
              </button>
            ))}
          </div>
        </Card>
      )}
    </main>
  );
}
