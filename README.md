# 🔐 VaultRAG — Privacy-First Enterprise AI Assistant

IBM Z Datathon 2026 · Track: **AI Secured: Innovation Without Exposure**

Employees ask natural-language questions about confidential documents and get cited answers built **only** from
evidence their roles permit. Its core component, the **Revocation-Safe Evidence Gate (RSEG)**, records which
document versions and ACL versions support every answer, and re-checks authorization immediately before release —
so a permission revoked mid-session or mid-generation can never be bypassed by a cache or a slow model call.

## Architecture

```
 React/TS UI ──► FastAPI ──► RAG pipeline ──► LLM provider (OpenAI-compatible | extractive | none)
                   │             │
                   │   1 authz snapshot (SQLite = source of truth)
                   │   2 cache lookup → REVALIDATE every dependency (doc ver, ACL ver, user ver, live access)
                   │   3 accessible doc IDs computed from DB BEFORE retrieval; vector search limited to them
                   │   4 each candidate independently re-verified; injection-flagged chunks quarantined
                   │   5 LLM sees: fixed system rules + question + <evidence> blocks (untrusted data, no tools)
                   │   6 RSEG final gate (one consistent DB read): revoked/changed → discard whole answer,
                   │        regenerate from current evidence once, else DENY. Nothing is streamed before this.
                   │   7 deterministic post-checks: citation validity, prompt-leak canary, PII policy
                   └─► hash-linked audit log (no raw doc text, no credentials; question stored as hash+length)
```

Fail-closed: authorization-service outage, validation exception or version mismatch ⇒ the response is blocked.
The **administrator** role holds management *capabilities* (documents, roles, security review) but has **no
implicit read access**: document content requires the document's ACL to list one of the user's roles.
Explicit per-user denies override role grants. Cache keys never imply authorization.

Key files: `backend/app/services/{rseg,rag,authz,documents,injection,pii,audit,llm}.py`, `backend/tests/`, `backend/scripts/benchmark.py`.

## Quick start

```bash
cp .env.example .env                       # set LLM_API_KEY for a real model (e.g. Groq), or LLM_PROVIDER=extractive
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd ../frontend && npm install && npm run build      # backend serves frontend/dist
cd ../backend && .venv/bin/uvicorn app.main:app --port 8000   # open http://localhost:8000
# UI dev mode: (cd frontend && npm run dev) → http://localhost:5173 (proxies /api to :8000)
```

Docker: `docker compose up --build` (see Known limitations — not yet exercised on LinuxONE).
Demo identities (synthetic, password `demo-pass`): alice (employee), hannah (employee+HR), frank (finance),
leo (legal), maya (HR+finance, explicitly denied the restructuring memo), adam (administrator).

**LLM configuration** is environment-only (`LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`). With no key
and `openai_compatible`, chat returns an explicit "model not configured" error — it never fabricates answers.
`LLM_PROVIDER=extractive` is an **offline, non-generative** mode (returns best-matching authorized sentences) used
for tests/benchmarks/no-network demos; the UI labels it as such.

## Demo script (≈4 min) — Security → Admin Demo Controls, or log in as each user

1. Sign in as **hannah**, ask *"How many weeks of paid parental leave do primary caregivers receive?"* → cited answer, badge "Released by security gate".
2. Sign in as **alice**, same question → abstains; no HR title/passage is exposed. Vault lists only the handbook.
3. As hannah, ask again → `cache: hit revalidated` (cached answer, but dependencies were re-checked).
4. As **adam** (Document Vault) untick the **hr** role on "HR Parental Leave Policy" (log in as adam in another browser/private window to keep hannah logged in).
5. hannah asks again, still logged in → **cached answer not released**; abstains. Security Center shows `permission_changed`, `cache_invalidated`.
6. Demo Controls → **Revoke during generation** → audit trace shows `revocation_detected_before_release` → discard → regenerate → abstain.
7. Demo Controls → **Simulate outage** → every request incl. cached ones is denied (fail closed). Restore.
8. Demo Controls → **Upload poisoned document**; alice asks about supplier payment → injection flagged on upload, malicious chunk quarantined (never reaches the model), legitimate sentence still answered. Security Center → expand the events and **Verify hash chain**.

## Tests & evaluation

```bash
cd backend && .venv/bin/python -m pytest -q          # 23 tests: RBAC, revocation, cache, versions, races,
                                                     # authz outage, injection, PII, audit, metadata leakage
.venv/bin/python -m scripts.benchmark --out ../docs/BENCHMARK.md
```
Latest benchmark (`docs/BENCHMARK.md`; synthetic data, offline extractive model, in-memory SQLite, tiny suite):

| Metric | Conventional RAG | Filtered RAG | VaultRAG |
|---|---|---|---|
| Unauthorized disclosures / probes | 23/23 | 0/23 | 0/23 |
| Leaks after revocation (cached) | 2/2 | 2/2 | 0/2 |
| Leaks when revoked mid-generation | 2/2 | 2/2 | 0/2 |
| Legit answers correct / false refusals | 10/10 · 0 | 10/10 · 0 | 10/10 · 0 |
| Cache correct after document replacement | no | no | yes |

Latency in this setup is sub-millisecond for all modes (extractive model, in-memory DB) — it shows RSEG's own
overhead (~0.1 ms/cache-hit revalidation), **not** end-to-end latency with a real LLM.

## Implemented / simulated / incomplete / unverified

**Implemented & tested:** roles, DB-authoritative ACLs with versions, explicit user denies, admin-capability separation,
upload/replace/remove with versioning, extraction (TXT/PDF/DOCX), chunking, hashing embeddings (+ optional
OpenAI-compatible embeddings), permission-first retrieval, RSEG (dependency tracking, revalidation, invalidation,
final gate, regenerate-or-deny, fail closed), injection quarantine, PII redact/block policy, hash-linked audit, React UI.
**Simulated:** authorization-service "outage" and mid-generation revocation are injected faults inside one process,
not a distributed failure; "demo ask-as" lets the demo admin run queries as another synthetic user.
**Incomplete:** SQLite + in-process lock (single node; no multi-process/DB-replication story); no streaming (by design);
vector search is a linear scan over SQLite (fine for demo scale; ChromaDB/other store is not wired in);
PDF/DOCX extraction untested on complex layouts; no rate limiting, MFA, or SSO; tokens are bearer HMAC tokens with no revocation list
(roles/active flag are re-read from the DB each request, so disabling/role changes take effect immediately).
**Unverified:** behaviour with a real hosted LLM beyond the OpenAI-compatible request shape; deployment on LinuxONE/s390x;
prompt-injection detector quality beyond the small hand-written suite below; the benchmark is small and the baselines
are our own re-implementations. No claim of novelty has been made — no literature/prior-art review has been done.

**Prompt-injection detector (regex heuristics):** on the 16 malicious / 14 benign hand-written samples in
`backend/tests/injection_cases.py` it flags 16/16 and 0/14 **after two rules were generalised once we saw two misses** —
so that number is optimistic; a held-out set is needed. Heuristics miss paraphrase/obfuscation; the real defences are
architectural (authorization before the model, untrusted-evidence framing, no tools, deterministic release gate).

Never use real personal data; all seeded data is synthetic. Never commit `.env`.
