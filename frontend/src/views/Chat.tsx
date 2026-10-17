import { useRef, useState } from "react";
import { api, ChatResult, User } from "../api";
import { Badge, Button, Card, ErrorNote, RichText, statusTone } from "../components/ui";

type Turn = { q: string; r?: ChatResult; err?: string };
const SUGGESTIONS = ["What is the Level 5 salary band?", "How many weeks of paid parental leave do primary caregivers receive?", "How many days of annual leave do employees get?", "What is the Q3 marketing budget?"];

const SecurityStrip = ({ r }: { r: ChatResult }) => {
  const label = { answered: "Released by security gate", abstained: "Abstained", denied: "Blocked — failed closed", error: "Error" }[r.status];
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs" aria-label="Security status">
      <Badge tone={statusTone(r.status)}>🛡 {label}</Badge>
      {r.cache !== "miss" && <Badge tone="info">cache: {r.cache.replace("_", " ")}</Badge>}
      {r.reason && <Badge tone="warn">reason: {r.reason}</Badge>}
      {r.security?.quarantined > 0 && <Badge tone="warn">{r.security.quarantined} chunk(s) quarantined (injection)</Badge>}
      {r.security?.pii_action && r.security.pii_action !== "allow" && <Badge tone="warn">PII {r.security.pii_action}ed</Badge>}
      {r.llm && <Badge tone="mute">{r.llm.generative ? `model: ${r.llm.provider}` : "extractive (non-generative)"}</Badge>}
      <Badge tone="mute">{r.latency_ms} ms</Badge>
      <span className="text-slate-500">audit: {r.request_id}</span>
    </div>
  );
};

export default function Chat({ user }: { user: User }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  async function ask(text: string) {
    if (text.trim().length < 3 || busy) return;
    setBusy(true); setQ("");
    const i = turns.length;
    setTurns(t => [...t, { q: text }]);
    try {
      const r = await api<ChatResult>("/api/chat", { body: { question: text } });
      setTurns(t => t.map((x, j) => j === i ? { ...x, r } : x));
    } catch (e: any) { setTurns(t => t.map((x, j) => j === i ? { ...x, err: e.message } : x)); }
    finally { setBusy(false); setTimeout(() => end.current?.scrollIntoView({ behavior: "smooth" }), 50); }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-white">Secure AI Chat</h1>
        <p className="text-sm text-slate-400">Answers use only documents <b>{user.display_name}</b> may read, and are re-validated by the Revocation-Safe Evidence Gate before release.</p>
      </div>
      {turns.length === 0 && (
        <Card title="Try a question">
          <div className="flex flex-wrap gap-2">{SUGGESTIONS.map(s => <Button key={s} variant="ghost" onClick={() => ask(s)}>{s}</Button>)}</div>
        </Card>
      )}
      {turns.map((t, i) => (
        <div key={i} className="grid gap-2">
          <div className="ml-auto max-w-[85%] rounded border border-sapphire/40 bg-sapphire/15 px-3 py-2 text-sm text-white">{t.q}</div>
          <Card>
            {!t.r && !t.err && <p className="text-sm text-slate-400" aria-live="polite">Generating, then validating authorization… (nothing is shown until the gate approves)</p>}
            <ErrorNote msg={t.err || null} />
            {t.r && (
              <>
                {t.r.status === "denied" && <p className="text-sm text-red-300">Access denied: this response was blocked and discarded ({t.r.reason}).</p>}
                {t.r.status === "error" && <p className="text-sm text-red-300">{t.r.answer}</p>}
                {(t.r.status === "answered" || t.r.status === "abstained") && <p className="whitespace-pre-wrap text-sm leading-relaxed"><RichText text={t.r.answer} /></p>}
                {t.r.citations.length > 0 && (
                  <div className="mt-3 grid gap-1">
                    {t.r.citations.map(c => (
                      <details key={c.chunk_id} className="rounded-lg border border-line bg-ink px-3 py-2 text-sm">
                        <summary className="cursor-pointer">[{c.n}] {c.title} <Badge tone="mute">v{c.doc_version}</Badge></summary>
                        <blockquote className="mt-2 border-l-2 border-brand pl-3 text-slate-300">{c.passage}</blockquote>
                      </details>
                    ))}
                  </div>
                )}
                <SecurityStrip r={t.r} />
              </>
            )}
          </Card>
        </div>
      ))}
      <div ref={end} />
      <form className="sticky bottom-2 flex gap-2" onSubmit={e => { e.preventDefault(); ask(q); }}>
        <input aria-label="Question" value={q} onChange={e => setQ(e.target.value)} maxLength={2000} placeholder="Ask about your documents…"
          className="glow-focus flex-1 rounded border border-panel2 bg-ink px-3 py-2.5 font-mono text-sm placeholder:text-slate-500 focus:border-brand" />
        <Button type="submit" disabled={busy || q.trim().length < 3}>{busy ? "…" : "Ask"}</Button>
      </form>
    </div>
  );
}
