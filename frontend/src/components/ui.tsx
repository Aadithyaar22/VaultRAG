import { ReactNode } from "react";

export const Card = ({ title, right, children, className = "" }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={`rounded-xl border border-line bg-panel p-4 ${className}`}>
    {(title || right) && (
      <header className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-wide text-slate-200">{title}</h2>
        {right}
      </header>
    )}
    {children}
  </section>
);

const tones: Record<string, string> = {
  ok: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  warn: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  bad: "bg-red-500/15 text-red-300 border-red-500/30",
  info: "bg-indigo-500/15 text-indigo-200 border-indigo-400/30",
  mute: "bg-slate-500/15 text-slate-300 border-slate-500/30",
};
export const Badge = ({ tone = "mute", children }: { tone?: keyof typeof tones; children: ReactNode }) => (
  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>
);

export const Button = ({ variant = "primary", className = "", ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) => {
  const v = { primary: "bg-brand text-ink hover:brightness-110", ghost: "border border-line text-slate-200 hover:bg-panel2", danger: "bg-red-500/90 text-white hover:bg-red-400" }[variant];
  return <button {...p} className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${v} ${className}`} />;
};

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input {...p} className={`w-full rounded-lg border border-line bg-ink px-3 py-2 text-sm placeholder:text-slate-500 ${p.className || ""}`} />
);

export const Stat = ({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) => (
  <div className="rounded-xl border border-line bg-panel p-4">
    <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
    <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
    {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
  </div>
);

export const statusTone = (s: string) => ({ answered: "ok", abstained: "warn", denied: "bad", error: "bad", released: "ok", blocked: "bad", flagged: "warn", discarded: "bad", ok: "ok" } as Record<string, any>)[s] || "mute";
export const ErrorNote = ({ msg }: { msg: string | null }) => msg ? <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{msg}</div> : null;
