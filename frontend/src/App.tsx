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

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
function loadAmbient(): boolean {
  try { const v = localStorage.getItem("vr_motion"); if (v === "on") return true; if (v === "off") return false; } catch {}
  return !reducedMotion();
}
type Tab = "chat" | "dashboard" | "vault" | "users" | "security" | "demo";
type Item = { id: Tab; label: string; desc: string; icon: ReactNode; cap?: string; c: string };
const NAV: Item[] = [
  { id: "chat", c: "#5eead4", label: "Secure Chat", icon: icons.chat, desc: "Ask questions in plain language. Answers use only documents your role may read." },
  { id: "dashboard", c: "#60a5fa", label: "Dashboard", icon: icons.dashboard, desc: "Live counts of queries, blocked answers and permission changes." },
  { id: "vault", c: "#a78bfa", label: "Document Vault", icon: icons.vault, desc: "Upload documents, track versions and decide who can read each one." },
  { id: "users", c: "#fbbf24", label: "Users & Roles", icon: icons.users, cap: "manage_roles", desc: "Change a person's roles. Their cached answers are invalidated immediately." },
  { id: "security", c: "#fb7185", label: "Security Center", icon: icons.shield, cap: "review_security", desc: "Audit trail, user risk scores and the models running on this server." },
  { id: "demo", c: "#e879f9", label: "Demo Controls", icon: icons.sliders, cap: "demo_controls", desc: "Run the demo scenario: revoke access, simulate an outage, upload a poisoned file." },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [screen, setScreen] = useState<"hero" | "signin">("hero");
  const [ready, setReady] = useState(!hasToken());
  const [ambient, setAmbient] = useState(loadAmbient);
  const toggleMotion = () => setAmbient(a => { const n = !a; try { localStorage.setItem("vr_motion", n ? "on" : "off"); } catch {} return n; });
  const motion = (
    <button onClick={toggleMotion} aria-pressed={ambient} title={reducedMotion() ? "Your system asks for reduced motion; the pointer still moves the background" : "Toggle the flowing background"}
      className="liquid fixed bottom-20 right-3 z-40 !rounded-full px-4 py-2 text-xs font-medium text-slate-200 transition hover:text-white md:bottom-4 md:right-4">
      Flowing background: <span className="font-semibold text-white">{ambient ? "On" : "Off"}</span>
    </button>
  );

  useEffect(() => {
    if (!hasToken()) return;
    api<User>("/api/auth/me").then(setUser).catch(() => setToken("")).finally(() => setReady(true));
  }, []);

  if (!ready) return null;

  if (!user && screen === "hero") return (
    <>
      <ShaderBackground dim={0.34} ambient={ambient} />
      {motion}
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
      <ShaderBackground dim={0.62} ambient={ambient} />
      {motion}
      <SignIn onBack={() => setScreen("hero")} onLogin={(u) => { setUser(u); setTab("chat"); }} />
    </>
  );

  const items = NAV.filter(n => !n.cap || user.capabilities.includes(n.cap));
  const current = items.find(n => n.id === tab) || items[0];
  const logout = () => { setToken(""); setUser(null); setScreen("hero"); };

  return (
    <div className="min-h-full pb-28 md:pb-12" style={{ ["--accent" as any]: current.c }}>
      <ShaderBackground dim={0.6} ambient={ambient} />
      {motion}
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
              style={active ? { background: `linear-gradient(120deg, ${n.c}38, ${n.c}14)`, boxShadow: `inset 0 0 0 1px ${n.c}77, 0 0 22px -6px ${n.c}` } : undefined}
              className={`flex items-center gap-2 whitespace-nowrap rounded-full px-2.5 py-2.5 text-sm font-medium transition duration-200 sm:px-3.5 ${active ? "text-white" : "text-slate-400 hover:bg-white/10 hover:text-white"}`}>
              <span style={{ color: active ? n.c : undefined }}>{n.icon}</span><span className={active ? "inline" : "hidden lg:inline"}>{n.label}</span>
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
