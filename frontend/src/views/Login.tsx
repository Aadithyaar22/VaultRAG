import { useEffect, useState } from "react";
import { api, setToken, User } from "../api";
import { Badge, Button, Card, ErrorNote, Input } from "../components/ui";

type Demo = { username: string; display_name: string; roles: string[] };

export default function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [demo, setDemo] = useState<Demo[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api<Demo[]>("/api/auth/demo-users").then(setDemo).catch(() => {}); }, []);

  async function submit(u = username, p = password) {
    setErr(null);
    try {
      const { token } = await api<{ token: string }>("/api/auth/login", { body: { username: u, password: p } });
      setToken(token);
      onLogin(await api<User>("/api/auth/me"));
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col justify-center gap-4 p-4">
      <div><h1 className="text-5xl font-bold text-white">🔐 VaultRAG</h1>
        <p className="text-slate-200">Ask questions about confidential documents — see only what your role permits, with revocation-safe answers.</p></div>
      <Card title="Sign in">
        <form className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <Input aria-label="Username" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" />
          <Input aria-label="Password" placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
          <Button type="submit">Sign in</Button>
        </form>
        <div className="mt-2"><ErrorNote msg={err} /></div>
      </Card>
      {demo.length > 0 && (
        <Card title="Synthetic demo identities" right={<Badge tone="warn">demo mode — synthetic data only</Badge>}>
          <div className="grid gap-2 sm:grid-cols-2">
            {demo.map(d => (
              <button key={d.username} onClick={() => submit(d.username, "demo-pass")}
                className="rounded border border-line bg-ink/50 p-3 text-left transition hover:border-brand/60 hover:bg-panel2">
                <div className="font-semibold text-white">{d.display_name}</div>
                <div className="mt-1 flex flex-wrap gap-1">{d.roles.map(r => <Badge key={r} tone="info">{r}</Badge>)}</div>
              </button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
