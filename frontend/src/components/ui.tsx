import { ReactNode } from "react";

export const Card = ({ title, right, children, className = "" }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={`glass p-4 ${className}`}>
    {(title || right) && (
      <header className="mb-3 flex items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold tracking-wide text-slate-100">{title}</h2>
        {right}
      </header>
    )}
    {children}
  </section>
);

const tones: Record<string, string> = {
  ok: "bg-emerald-500/10 text-emerald-300 border-emerald-500/40",
  warn: "bg-amber-500/10 text-amber-300 border-amber-500/40",
  bad: "bg-red-500/10 text-red-300 border-red-500/40",
  info: "bg-cyan-400/10 text-cyan-200 border-cyan-400/30",
  mute: "bg-slate-400/10 text-slate-300 border-slate-400/25",
};
export const Badge = ({ tone = "mute", children }: { tone?: keyof typeof tones; children: ReactNode }) => (
  <span className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${tones[tone]}`}>
    {tone !== "mute" && <span className="bead" aria-hidden />}{children}
  </span>
);

export const Button = ({ variant = "primary", className = "", ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) => {
  const v = {
    primary: "bg-brand text-ink glow-cyan",
    ghost: "border border-blue-800 bg-panel/60 text-brand hover:border-brand hover:bg-sapphire/10",
    danger: "border border-red-500 bg-red-500/10 text-red-400 glow-red hover:bg-red-500/15",
  }[variant];
  return <button {...p} className={`rounded px-3 py-1.5 font-display text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${v} ${className}`} />;
};

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input {...p} className={`glow-focus w-full rounded border border-panel2 bg-ink px-3 py-2 font-mono text-sm placeholder:text-slate-500 focus:border-brand ${p.className || ""}`} />
);

export const Stat = ({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) => (
  <div className="glass p-4">
    <div className="font-mono text-[10px] uppercase tracking-widest text-slate-400">{label}</div>
    <div className="mt-1 font-display text-3xl font-semibold text-white">{value}</div>
    {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
  </div>
);

export const statusTone = (s: string) => ({ answered: "ok", abstained: "warn", denied: "bad", error: "bad", released: "ok", blocked: "bad", flagged: "warn", discarded: "bad", ok: "ok" } as Record<string, any>)[s] || "mute";
export const ErrorNote = ({ msg }: { msg: string | null }) => msg ? <div role="alert" className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{msg}</div> : null;

/** Minimal inline markdown (bold only) for model answers; everything else renders as plain text (no HTML injection). */
export const RichText = ({ text }: { text: string }) => (
  <>{text.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith("**") && p.endsWith("**") && p.length > 4 ? <strong key={i} className="font-semibold text-white">{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>)}</>
);
