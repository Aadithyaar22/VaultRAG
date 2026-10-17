import { ReactNode, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/* ---------- icons (custom, stroke-based; no emoji) ---------- */
const I = ({ d, size = 18 }: { d: string; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    {d.split("|").map((p, i) => <path key={i} d={p} />)}
  </svg>
);
export const icons = {
  chat: <I d="M4 5h16v11H9l-5 4z|M8 9h8M8 12h5" />,
  dashboard: <I d="M4 13h6V4H4z|M14 20h6V11h-6z|M4 20h6v-4H4z|M14 8h6V4h-6z" />,
  vault: <I d="M5 8h14v11H5z|M8 8V6a4 4 0 0 1 8 0v2|M12 12v3" />,
  users: <I d="M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z|M3 19c0-3 3-5 6-5s6 2 6 5|M16 5.5a3 3 0 0 1 0 5.5|M18 14c2 .5 3 2.2 3 5" />,
  shield: <I d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z|M9 12l2 2 4-4" />,
  sliders: <I d="M5 6h8M17 6h2M5 12h2M11 12h8M5 18h10M19 18h0|M15 4v4M9 10v4M17 16v4" />,
  chevron: <I d="M7 10l5 5 5-5" size={16} />,
  arrow: <I d="M5 12h14M13 6l6 6-6 6" size={18} />,
  back: <I d="M19 12H5M11 6l-6 6 6 6" size={16} />,
};
/** VaultRAG mark: a droplet-shaped shield with a keyhole — liquid + security in one shape. */
export const Logo = ({ size = 28 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
    <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#a7f3e6" /><stop offset="1" stopColor="#6ea0ff" /></linearGradient></defs>
    <path d="M16 2c6 5 11 7 11 14 0 7-5 12-11 14C10 28 5 23 5 16 5 9 10 7 16 2z" fill="url(#lg)" />
    <circle cx="16" cy="14.5" r="3" fill="#050813" /><path d="M14.6 16.5h2.8l.8 6h-4.4z" fill="#050813" />
  </svg>
);

/* ---------- surfaces ---------- */
export const Card = ({ title, right, children, className = "" }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={`liquid p-6 ${className}`}>
    {(title || right) && (
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-[15px] font-semibold tracking-tight text-white">{title}</h2>
        {right}
      </header>
    )}
    {children}
  </section>
);

export const PageHeader = ({ title, desc, right }: { title: string; desc: string; right?: ReactNode }) => (
  <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
    <div className="max-w-2xl">
      <div className="mb-4 h-1 w-14 rounded-full" style={{ background: ACCENT_BG }} aria-hidden />
      <h1 className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl">{title}</h1>
      <p className="mt-2 text-[15px] leading-relaxed text-slate-300">{desc}</p>
    </div>
    {right}
  </div>
);

const tones: Record<string, string> = {
  ok: "bg-emerald-400/10 text-emerald-300 border-emerald-400/30",
  warn: "bg-amber-400/10 text-amber-300 border-amber-400/30",
  bad: "bg-rose-400/10 text-rose-300 border-rose-400/30",
  info: "bg-violet-400/10 text-violet-200 border-violet-300/30",
  mute: "bg-white/5 text-slate-300 border-white/10",
};
export const Badge = ({ tone = "mute", children }: { tone?: keyof typeof tones; children: ReactNode }) => (
  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold leading-none tracking-wide ${tones[tone]}`}>
    {tone !== "mute" && <span className="bead" aria-hidden />}{children}
  </span>
);

/* ---------- buttons ---------- */
type Variant = "primary" | "ghost" | "danger";
/** Primary buttons follow the current page accent (--accent), falling back to teal. */
const ACCENT_BG = "linear-gradient(120deg, var(--accent, #5eead4), color-mix(in srgb, var(--accent, #5eead4) 45%, #8b7bff))";
const ACCENT_GLOW = "0 0 30px -6px color-mix(in srgb, var(--accent, #5eead4) 70%, transparent)";
const variantCls: Record<Variant, string> = {
  primary: "text-ink",
  ghost: "border border-white/15 bg-white/5 text-slate-100 hover:bg-white/10 hover:border-white/25",
  danger: "border border-rose-400/50 bg-rose-400/10 text-rose-200 hover:bg-rose-400/20 hover:shadow-[0_0_24px_-4px_rgba(251,113,133,0.5)]",
};
export const Button = ({ variant = "primary", busy, className = "", children, ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) => (
  <button {...p} disabled={p.disabled || busy}
    style={{ ...(variant === "primary" ? { background: ACCENT_BG } : {}), ...p.style }}
    onMouseEnter={e => { if (variant === "primary") e.currentTarget.style.boxShadow = ACCENT_GLOW; p.onMouseEnter?.(e); }}
    onMouseLeave={e => { if (variant === "primary") e.currentTarget.style.boxShadow = ""; p.onMouseLeave?.(e); }}
    className={`inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition duration-200 hover:scale-[1.02] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100 ${variantCls[variant]} ${className}`}>
    {busy && <span className="spinner" aria-hidden />}{children}
  </button>
);

export type SplitItem = { label: string; hint?: string; onClick: () => void; danger?: boolean };
/** One control, several related actions: the main segment runs the primary action; the chevron opens alternatives. */
export function SplitButton({ label, onClick, items, variant = "primary", busy, disabled, menuLabel = "More actions" }: {
  label: ReactNode; onClick: () => void; items: SplitItem[]; variant?: Variant; busy?: boolean; disabled?: boolean; menuLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, right: 0 });
  const box = useRef<HTMLDivElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const toggle = () => {
    if (!open && box.current) { const r = box.current.getBoundingClientRect(); setPos({ top: r.bottom + 8, right: Math.max(8, window.innerWidth - r.right) }); }
    setOpen(o => !o);
  };
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { const t = e.target as Node; if (!box.current?.contains(t) && !menu.current?.contains(t)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    const close = () => setOpen(false);
    document.addEventListener("mousedown", away); document.addEventListener("keydown", esc);
    window.addEventListener("scroll", close, true); window.addEventListener("resize", close);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); window.removeEventListener("scroll", close, true); window.removeEventListener("resize", close); };
  }, [open]);
  const seg = `inline-flex items-center gap-2 py-2.5 text-sm font-semibold transition duration-200 disabled:cursor-not-allowed disabled:opacity-50`;
  return (
    <div ref={box} style={variant === "primary" ? { background: ACCENT_BG } : undefined}
      className={`relative inline-flex rounded-full ${variantCls[variant]} transition duration-200`}>
      <button type="button" className={`${seg} rounded-l-full pl-5 pr-3`} onClick={onClick} disabled={disabled || busy}>
        {busy && <span className="spinner" aria-hidden />}{label}
      </button>
      <span className="my-2 w-px bg-current opacity-25" aria-hidden />
      <button type="button" className={`${seg} rounded-r-full pl-2.5 pr-3.5`} aria-haspopup="menu" aria-expanded={open} aria-label={menuLabel} onClick={toggle} disabled={disabled}>
        {icons.chevron}
      </button>
      {open && createPortal(
        <div ref={menu} role="menu" style={{ position: "fixed", top: pos.top, right: pos.right, background: "rgba(11,18,36,0.97)" }}
          className="liquid z-50 min-w-64 max-w-[calc(100vw-1rem)] !rounded-2xl p-1.5 text-left">
          {items.map(it => (
            <button key={it.label} role="menuitem" onClick={() => { setOpen(false); it.onClick(); }}
              className={`block w-full rounded-xl px-3.5 py-2.5 text-left transition hover:bg-white/10 ${it.danger ? "text-rose-300" : "text-slate-100"}`}>
              <span className="block text-sm font-medium">{it.label}</span>
              {it.hint && <span className="mt-0.5 block text-xs font-normal text-slate-400">{it.hint}</span>}
            </button>
          ))}
        </div>, document.body)}
    </div>
  );
}

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input {...p} className={`glow-focus w-full rounded-full border border-white/12 bg-black/30 px-5 py-3 text-sm placeholder:text-slate-500 ${p.className || ""}`} />
);

export const Stat = ({ label, value, hint, c = "#5eead4" }: { label: string; value: ReactNode; hint?: string; c?: string }) => (
  <div className="liquid p-5" style={{ background: `radial-gradient(130% 100% at 0% 0%, ${c}26, transparent 60%), linear-gradient(145deg, rgba(255,255,255,0.075), rgba(255,255,255,0.025))`, boxShadow: `inset 0 2px 0 0 ${c}77, 0 24px 60px -28px rgba(0,0,0,0.75)` }}>
    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.12em] text-slate-300"><span className="h-2 w-2 rounded-full" style={{ background: c, boxShadow: `0 0 10px ${c}` }} aria-hidden />{label}</div>
    <div className="mt-2 font-display text-4xl font-bold tracking-tight text-white">{value}</div>
    {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
  </div>
);

export const statusTone = (s: string) => ({ answered: "ok", abstained: "warn", denied: "bad", error: "bad", released: "ok", blocked: "bad", flagged: "warn", discarded: "bad", ok: "ok" } as Record<string, any>)[s] || "mute";
export const ErrorNote = ({ msg }: { msg: string | null }) => msg ? <div role="alert" className="rounded-2xl border border-rose-400/40 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{msg}</div> : null;

/** Minimal inline markdown (bold only) for model answers; everything else renders as plain text (no HTML injection). */
export const RichText = ({ text }: { text: string }) => (
  <>{text.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith("**") && p.endsWith("**") && p.length > 4 ? <strong key={i} className="font-semibold text-white">{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>)}</>
);
