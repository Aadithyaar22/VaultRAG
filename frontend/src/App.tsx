import { ReactNode, useEffect, useState } from "react";
import { api, hasToken, setToken, User } from "./api";
import SignIn from "./views/Login";
import Dashboard from "./views/Dashboard";
import Chat from "./views/Chat";
import Home from "./views/Home";
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
type Tab = "home" | "chat" | "dashboard" | "vault" | "users" | "security" | "demo";
type Item = { id: Tab; label: string; desc: string; icon: ReactNode; cap?: string; c: string; who?: string; can?: string[] };
const NAV: Item[] = [
  { id: "home", c: "#ffffff", label: "Home", icon: icons.home, desc: "Start here: what VaultRAG does and what each menu is for." },
  { id: "chat", c: "#ffffff", label: "Secure Chat", icon: icons.chat, desc: "Ask questions in plain language. Answers use only documents your role may read.",
    can: ["Ask about the documents you are allowed to read", "Open the exact passage behind every citation", "See each reply's security status, cache state and audit ID"] },
  { id: "dashboard", c: "#ffffff", label: "Dashboard", icon: icons.dashboard, desc: "Live counts of queries, blocked answers and permission changes.",
    can: ["Watch your own queries, blocks and abstentions", "See revocations and stale-cache rejections", "Administrators also see all users and the audit-chain check"] },
  { id: "vault", c: "#ffffff", label: "Document Vault", icon: icons.vault, desc: "Upload documents, track versions and decide who can read each one.",
    can: ["Browse the documents you can read", "Upload, replace or remove documents (managers)", "Set which roles can read each one, with an AI suggestion at upload"] },
  { id: "users", c: "#ffffff", label: "Users & Roles", icon: icons.users, cap: "manage_roles", who: "Administrators", desc: "Change a person's roles. Their cached answers are invalidated immediately.",
    can: ["Add or remove a role for any user", "See each user's authorization version change", "Know that old cached answers can no longer be served"] },
  { id: "security", c: "#ffffff", label: "Security Center", icon: icons.shield, cap: "review_security", who: "Administrators", desc: "Audit trail, user risk scores and the models running on this server.",
    can: ["Review every decision and verify the tamper-evident chain", "See user risk scores from the anomaly model", "Set the PII policy: redact, block or off"] },
  { id: "demo", c: "#ffffff", label: "Demo Controls", icon: icons.sliders, cap: "demo_controls", who: "Administrators (demo mode)", desc: "Run the demo scenario: revoke access, simulate an outage, upload a poisoned file.",
    can: ["Ask as any demo user and compare what each can see", "Revoke access mid-answer or simulate an authorization outage", "Upload a poisoned document or simulate a probing attack"] },
];

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("home");
  const [screen, setScreen] = useState<"hero" | "signin">("hero");
  const [ready, setReady] = useState(!hasToken());
  const [ambient, setAmbient] = useState(loadAmbient);
  const toggleMotion = () => setAmbient(a => { const n = !a; try { localStorage.setItem("vr_motion", n ? "on" : "off"); } catch {} return n; });
  const motion = (
    <button onClick={toggleMotion} aria-pressed={ambient} title={reducedMotion() ? "Your system asks for reduced motion; the pointer still moves the background" : "Toggle the flowing background"}
      className="liquid fixed bottom-20 right-3 z-40 !rounded-full px-4 py-2 text-xs font-medium text-slate-200 transition hover:text-white md:bottom-4 md:right-4">
      <span className="hidden sm:inline">Flowing background: </span><span className="sm:hidden">Motion: </span><span className="font-semibold text-white">{ambient ? "On" : "Off"}</span>
    </button>
  );

  useEffect(() => {
    if (!hasToken()) return;
    api<User>("/api/auth/me").then(setUser).catch(() => setToken("")).finally(() => setReady(true));
  }, []);

  if (!ready) return null;

  if (!user && screen === "hero") return (
    <>
      <ShaderBackground dim={0.3} ambient={ambient} />
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
      <SignIn onBack={() => setScreen("hero")} onLogin={(u) => { setUser(u); setTab("home"); }} />
    </>
  );

  const items = NAV.filter(n => !n.cap || user.capabilities.includes(n.cap));
  const current = items.find(n => n.id === tab) || items[0];
  const logout = () => { setToken(""); setUser(null); setScreen("hero"); };

  return (
    <div className="min-h-full pb-28 md:pb-12" style={{ ["--accent" as any]: current.c }}>
      <ShaderBackground dim={0.62} ambient={ambient} />
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

      <nav aria-label="Main" className="liquid fixed bottom-4 left-1/2 z-40 flex w-max max-w-[calc(100vw-1.5rem)] -translate-x-1/2 items-center gap-1 overflow-x-auto !rounded-full p-1.5 md:sticky md:bottom-auto md:left-auto md:top-4 md:mx-auto md:mt-5 md:translate-x-0">
        {items.map(n => {
          const active = n.id === current.id;
          return (
            <button key={n.id} onClick={() => setTab(n.id)} title={`${n.label} — ${n.desc}`} aria-label={n.label} aria-current={active ? "page" : undefined}
              style={active ? { background: "linear-gradient(120deg, rgba(255,255,255,0.20), rgba(255,255,255,0.07))", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.45)" } : undefined}
              className={`flex items-center gap-2 whitespace-nowrap rounded-full px-2.5 py-2.5 text-sm font-medium transition duration-200 sm:px-3.5 ${active ? "text-white" : "text-slate-400 hover:bg-white/10 hover:text-white"}`}>
              <span style={{ color: active ? n.c : undefined }}>{n.icon}</span><span className={active ? "hidden sm:inline" : "hidden lg:inline"}>{n.label}</span>
            </button>
          );
        })}
      </nav>

      <main className="mx-auto max-w-5xl px-4 pt-10 sm:px-8" key={current.id}>
        {current.id === "home" && <Home user={user} desc={current.desc} all={NAV} go={setTab} />}
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
