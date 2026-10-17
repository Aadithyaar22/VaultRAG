import { useEffect, useState } from "react";
import { api, hasToken, setToken, User } from "./api";
import Login from "./views/Login";
import Dashboard from "./views/Dashboard";
import Chat from "./views/Chat";
import Vault from "./views/Vault";
import Users from "./views/Users";
import Security from "./views/Security";
import Demo from "./views/Demo";
import { Badge } from "./components/ui";
import ShaderBackground from "./components/ShaderBackground";

type Tab = "dashboard" | "chat" | "vault" | "users" | "security" | "demo";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [ready, setReady] = useState(!hasToken());

  useEffect(() => {
    if (!hasToken()) return;
    api<User>("/api/auth/me").then(setUser).catch(() => setToken("")).finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  if (!user) return (<><ShaderBackground dim={0.62} /><Login onLogin={(u) => { setUser(u); setTab("chat"); }} /></>);

  const caps = user.capabilities;
  const tabs: [Tab, string, boolean][] = [
    ["chat", "Secure Chat", true],
    ["dashboard", "Dashboard", true],
    ["vault", "Document Vault", true],
    ["users", "Users & Roles", caps.includes("manage_roles")],
    ["security", "Security Center", caps.includes("review_security")],
    ["demo", "Admin Demo Controls", caps.includes("demo_controls")],
  ];
  const logout = () => { setToken(""); setUser(null); };

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <ShaderBackground dim={0.82} />
      <aside className="glass !rounded-none border-0 border-b border-line p-4 md:w-64 md:border-b-0 md:border-r">
        <div className="mb-1 flex items-center gap-2 font-display text-lg font-bold text-white"><span aria-hidden>🔐</span> VaultRAG</div>
        <p className="mb-4 text-xs text-slate-400">AI Secured: Innovation Without Exposure</p>
        <nav className="flex flex-wrap gap-1 md:flex-col" aria-label="Main">
          {tabs.filter(t => t[2]).map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} aria-current={tab === id ? "page" : undefined}
              className={`rounded px-3 py-2 text-left text-sm font-medium transition ${tab === id ? "border-l-2 border-brand bg-brand/10 text-brand" : "border-l-2 border-transparent text-slate-300 hover:bg-panel2 hover:text-white"}`}>{label}</button>
          ))}
        </nav>
        <div className="mt-6 hidden rounded border border-line bg-ink/60 p-3 text-xs md:block">
          <div className="font-semibold text-white">{user.display_name}</div>
          <div className="mt-1 flex flex-wrap gap-1">{user.roles.map(r => <Badge key={r} tone="info">{r}</Badge>)}</div>
          <button onClick={logout} className="mt-3 text-slate-400 underline">Sign out</button>
        </div>
      </aside>
      <main className="flex-1 p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between md:hidden"><span className="text-sm">{user.display_name}</span><button onClick={logout} className="text-sm underline">Sign out</button></div>
        {tab === "chat" && <Chat user={user} />}
        {tab === "dashboard" && <Dashboard user={user} />}
        {tab === "vault" && <Vault user={user} />}
        {tab === "users" && <Users />}
        {tab === "security" && <Security />}
        {tab === "demo" && <Demo />}
      </main>
    </div>
  );
}
