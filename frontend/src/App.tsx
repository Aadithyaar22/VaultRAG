import { ReactNode, useEffect, useState } from "react";
import { api, hasToken, setToken, User } from "./api";
import SignIn from "./views/Login";
import Dashboard from "./views/Dashboard";
import Chat from "./views/Chat";
import Vault from "./views/Vault";
import Users from "./views/Users";
import Security from "./views/Security";
import Demo from "./views/Demo";
import { Badge, Button, Logo, icons } from "./components/ui";
import ShaderBackground from "./components/ShaderBackground";

type Tab = "chat" | "dashboard" | "vault" | "users" | "security" | "demo";
type Item = { id: Tab; label: string; desc: string; icon: ReactNode; cap?: string };
const NAV: Item[] = [
  { id: "chat", label: "Secure Chat", icon: icons.chat, desc: "Ask questions in plain language. Answers use only documents your role may read." },
  { id: "dashboard", label: "Dashboard", icon: icons.dashboard, desc: "Live counts of queries, blocked answers and permission changes." },
  { id: "vault", label: "Document Vault", icon: icons.vault, desc: "Upload documents, track versions and decide who can read each one." },
  { id: "users", label: "Users & Roles", icon: icons.users, cap: "manage_roles", desc: "Change a person's roles. Their cached answers are invalidated immediately." },
  { id: "security", label: "Security Center", icon: icons.shield, cap: "review_security", desc: "Audit trail, user risk scores and the models running on this server." },
  { id: "demo", label: "Demo Controls", icon: icons.sliders, cap: "demo_controls", desc: "Run the demo scenario: revoke access, simulate an outage, upload a poisoned file." },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [screen, setScreen] = useState<"hero" | "signin">("hero");
  const [ready, setReady] = useState(!hasToken());

  useEffect(() => {
    if (!hasToken()) return;
    api<User>("/api/auth/me").then(setUser).catch(() => setToken("")).finally(() => setReady(true));
  }, []);

  if (!ready) return null;

  if (!user && screen === "hero") return (
    <>
      <ShaderBackground dim={0.38} />
      <main className="flex min-h-full flex-col items-center justify-center px-6 text-center">
        <h1 className="gradient-text rise font-display font-extrabold leading-[0.95] tracking-[-0.045em]" style={{ fontSize: "clamp(4.2rem, 15vw, 12rem)" }}>VaultRAG</h1>
        <Button className="rise mt-12 !px-9 !py-3.5 !text-base" style={{ animationDelay: "0.25s" }} onClick={() => setScreen("signin")}>
          Sign in {icons.arrow}
        </Button>
      </main>
    </>
  );

  if (!user) return (
    <>
      <ShaderBackground dim={0.7} />
      <SignIn onBack={() => setScreen("hero")} onLogin={(u) => { setUser(u); setTab("chat"); }} />
    </>
  );

  const items = NAV.filter(n => !n.cap || user.capabilities.includes(n.cap));
  const current = items.find(n => n.id === tab) || items[0];
  const logout = () => { setToken(""); setUser(null); setScreen("hero"); };

  return (
    <div className="min-h-full pb-28 md:pb-12">
      <ShaderBackground dim={0.84} />
      <header className="px-4 pt-5 sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="font-display text-lg font-bold tracking-tight text-white">VaultRAG</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden text-right sm:block">
              <div className="text-sm font-semibold leading-tight text-white">{user.display_name}</div>
              <div className="mt-1.5 flex justify-end gap-1">{user.roles.map(r => <Badge key={r} tone="info">{r}</Badge>)}</div>
            </div>
            <Button variant="ghost" className="!px-4 !py-2" onClick={logout}>Sign out</Button>
          </div>
        </div>
      </header>

      <nav aria-label="Main" className="liquid fixed bottom-4 left-1/2 z-40 flex w-max max-w-[calc(100vw-1.5rem)] -translate-x-1/2 items-center gap-1 !rounded-full p-1.5 md:sticky md:bottom-auto md:left-auto md:top-4 md:mx-auto md:mt-5 md:translate-x-0">
        {items.map(n => {
          const active = n.id === current.id;
          return (
            <button key={n.id} onClick={() => setTab(n.id)} title={`${n.label} — ${n.desc}`} aria-label={n.label} aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2 whitespace-nowrap rounded-full px-2.5 py-2.5 text-sm font-medium transition duration-200 sm:px-3.5 ${active ? "bg-gradient-to-r from-teal-300/25 to-sky-300/25 text-white shadow-[inset_0_0_0_1px_rgba(167,243,230,0.35)]" : "text-slate-400 hover:bg-white/10 hover:text-white"}`}>
              {n.icon}<span className={active ? "inline" : "hidden lg:inline"}>{n.label}</span>
            </button>
          );
        })}
      </nav>

      <main className="mx-auto max-w-5xl px-4 pt-10 sm:px-8" key={current.id}>
        {current.id === "chat" && <Chat user={user} desc={current.desc} />}
        {current.id === "dashboard" && <Dashboard user={user} desc={current.desc} />}
        {current.id === "vault" && <Vault user={user} desc={current.desc} />}
        {current.id === "users" && <Users desc={current.desc} />}
        {current.id === "security" && <Security desc={current.desc} />}
        {current.id === "demo" && <Demo desc={current.desc} />}
      </main>
    </div>
  );
}
