# Hack2Skill submission — copy/paste sheet

Deadline shown on the form: **18/10/2026 10:00 PM IST**. Fill the `[...]` placeholders, then confirm every link opens in a private window without requesting access.

**Project title (required format):** `Hacktivists_IBM Z Datathon 2026 Project`

## Challenge

AI Secured: Innovation Without Exposure



## What is the Problem you are trying to solve?

Enterprises want employees to query confidential documents (HR, Finance, Legal) in plain language, but typical RAG chatbots retrieve from everything, so restricted text can reach the wrong user. Even permission-filtered RAG fails when access changes: a cached answer or an in-flight generation can still deliver content to someone whose access was just revoked. Retrieved documents can also carry hidden prompt-injection instructions, answers can expose PII, and there is rarely an audit trail explaining why an answer was released. We need an assistant where authorization is enforced when an answer is released, not just when documents are retrieved.

_(652/1024 chars)_

## How are you planning to solve the problem? (Brief Overview)

VaultRAG is a FastAPI + React app. SQLite is the authoritative store for roles, document ACLs, and document/ACL/user versions. Per question: compute the user's allowed document IDs from the DB before retrieval, search only those, re-verify each candidate, quarantine injection-flagged chunks, then call an OpenAI-compatible LLM (Groq) with evidence framed as untrusted data and no tools. Our Revocation-Safe Evidence Gate records each answer's evidence (doc, version, ACL version) and, immediately before release, re-checks it in one consistent DB read. If anything changed, the answer is discarded and regenerated from current evidence or denied. Cached answers are revalidated, nothing is streamed early, and failures fail closed. PII redact/block policy and a hash-linked audit log complete it. 24 automated tests cover this.

_(828/1024 chars)_

## How does your solution leverage IBM Z / LinuxONE technologies?

VaultRAG is deployed and running on an IBM LinuxONE Community Cloud virtual server (s390x, Ubuntu 24.04). We run the full application, the 24-test suite and the baseline benchmark there. The stack is dependency-light (pure-Python retrieval, no native ML wheels), so it ports to s390x without changes; we compiled the only native dependency (lxml) on the instance. Planned integration: use Z hardware cryptography / pervasive encryption for documents at rest and in transit, quantum-safe-ready TLS, and co-locate retrieval with enterprise data on Z so confidential content never leaves the platform. The security controls (DB-authoritative permissions, fail-closed gate) suit Z's role as the system of record for sensitive workloads.

_(732/1024 chars)_

## What value does your solution deliver, and who will benefit from it?

Employees get fast, cited answers from policies and reports while seeing only what their role permits. Security and compliance teams get revocation that takes effect immediately, even for cached or in-flight answers, plus audit records explaining every release or block. Administrators manage documents, roles and revocations without gaining automatic read access to contents. In our synthetic benchmark, conventional RAG disclosed restricted content in 23/23 probes and filtered-only RAG leaked after revocation in 2/2 cached and 2/2 mid-generation cases, while VaultRAG leaked in 0 (small suite; not a proof of zero leakage). Limits: single-node SQLite, heuristic injection detection, no SSO/MFA yet.

_(702/1024 chars)_

## Pitch deck (PDF, ≤5 MB)

Upload `submission/VaultRAG_pitch_deck.pdf` (9 slides, ~330 KB). Fallback: public link to the same file in the repo.

## GitHub link (must be public)

https://github.com/Aadithyaar22/vaultrag-ibmz-datathon-2026 — repo root contains README, `.env.example`, sample data, tests. Public, pushed.

## Video link (YouTube/Vimeo, ≤3 min, MP4 720p/1080p)

`[VIDEO URL]` — script in `submission/VIDEO_SCRIPT.md`. Set visibility to Unlisted or Public.

## Link to all open-source resources used

FastAPI https://github.com/fastapi/fastapi · Uvicorn https://github.com/encode/uvicorn · Pydantic https://github.com/pydantic/pydantic · pydantic-settings https://github.com/pydantic/pydantic-settings · python-multipart https://github.com/Kludex/python-multipart · pypdf https://github.com/py-pdf/pypdf · python-docx https://github.com/python-openxml/python-docx · lxml https://github.com/lxml/lxml · httpx https://github.com/encode/httpx · pytest https://github.com/pytest-dev/pytest · SQLite https://sqlite.org · React https://github.com/facebook/react · Vite https://github.com/vitejs/vite · Tailwind CSS https://github.com/tailwindlabs/tailwindcss · TypeScript https://github.com/microsoft/TypeScript

Model used via API: Groq-hosted `openai/gpt-oss-120b` (open-weight model by OpenAI; served by Groq, a hosted service).

## Other document (architecture diagram)

Link: https://github.com/Aadithyaar22/vaultrag-ibmz-datathon-2026/blob/master/submission/architecture.png (also https://github.com/Aadithyaar22/vaultrag-ibmz-datathon-2026/blob/master/submission/architecture.svg) (also slide 4 of the deck). Optionally `docs/BENCHMARK.md` and `docs/BENCHMARK_s390x.md`.
