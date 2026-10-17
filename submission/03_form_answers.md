# 03 · Hack2Skill submission form — copy and paste

Form closes **18 October 2026, 10:00 PM IST**. Fill the two `[…]` placeholders (video link) and confirm every link opens in a private window.

**Project title (required format):** `Hacktivists_IBM Z Datathon 2026 Project`

---

## Challenge

AI Secured: Innovation Without Exposure

## What is the Problem you are trying to solve?

Enterprises want employees to query confidential documents (HR, Finance, Legal) in plain language, but typical RAG chatbots retrieve from everything, so restricted text can reach the wrong user. Even permission-filtered RAG fails when access changes: a cached answer or an in-flight generation can still deliver content to someone whose access was just revoked. Retrieved documents can also carry hidden prompt-injection instructions, answers can expose PII, and there is rarely an audit trail explaining why an answer was released. We need an assistant where authorization is enforced when an answer is released, not just when documents are retrieved.

_(652 of 1,024 characters)_

## How are you planning to solve the problem? (Brief Overview)

VaultRAG is a FastAPI + React app. SQLite is the authoritative store for roles, document ACLs, and document/ACL/user versions. Per question: compute the user's allowed document IDs from the DB before retrieval, search only those, re-verify each candidate, quarantine injection-flagged chunks, then call an OpenAI-compatible LLM (Groq) with evidence framed as untrusted data and no tools. Our Revocation-Safe Evidence Gate records each answer's evidence (doc, version, ACL version) and re-checks it in one DB read just before release; if anything changed, the answer is discarded and regenerated or denied. Cached answers are revalidated, nothing streams early, failures fail closed. On-server ML (scikit-learn) classifies uploads and warns on over-exposure, adds an injection classifier, and scores per-user risk with an IsolationForest. PII policy, a hash-linked audit log and 42 tests complete it. Verified on six real public PDF/DOCX/TXT documents across all roles.

_(968 of 1,024 characters)_

## How does your solution leverage IBM Z / LinuxONE technologies?

VaultRAG is deployed and running on an IBM LinuxONE Community Cloud virtual server (s390x, Ubuntu 24.04). The instance is an IBM z17 (machine type 9175) whose CPU reports the nnpa AI-accelerator feature. We run the app, the 42-test suite, benchmark and our scikit-learn models there (trained at startup), and completed IBM's Jupyter AI/ML lab (fraud LSTM, churn, MNIST to ONNX, hybrid ML+LLM loan notebook). The stack is dependency-light (pure-Python retrieval, no native ML wheels), so it ports to s390x without changes; we compiled the only native dependency (lxml) on the instance. Planned: move inference to an NNPA-accelerated path, a local Granite model so no text leaves the server, Z hardware crypto, and quantum-safe-ready TLS. The security controls (DB-authoritative permissions, fail-closed gate) suit Z's role as the system of record for sensitive workloads.

_(870 of 1,024 characters)_

## What value does your solution deliver, and who will benefit from it?

Employees get fast, cited answers from policies and reports while seeing only what their role permits. Security and compliance teams get revocation that takes effect immediately, even for cached or in-flight answers, plus audit records explaining every release or block. Administrators manage documents, roles and revocations without gaining automatic read access to contents. In our synthetic benchmark, conventional RAG disclosed restricted content in 23/23 probes and filtered-only RAG leaked after revocation in 2/2 cached and 2/2 mid-generation cases, while VaultRAG leaked in 0 (small suite; not a proof of zero leakage). Limits: single-node SQLite, a weak injection detector (the design is the defence), no SSO/MFA, and the AI service (Groq) receives only the passages a user may read; a server-side model is planned.

_(824 of 1,024 characters)_

---

## Upload your pitch deck (PDF, max 5 MB)

`01_pitch_deck.pdf` — 14 slides, about 1 MB.

## GitHub link of your project (must be public)

https://github.com/Aadithyaar22/VaultRAG

## Video submission link (YouTube or Vimeo, max 3 minutes, MP4 720p/1080p)

`[VIDEO URL]` — record with `04_video_script.md`; set to **Public** or **Unlisted**.

## Share the link to your pitch deck PDF (only if you cannot upload the file)

https://github.com/Aadithyaar22/VaultRAG/blob/master/submission/01_pitch_deck.pdf

## Link to all open-source resources used

See `06_open_source_links.md` — paste its single-paragraph list.

## Any other document (flowchart or architecture diagram)

Architecture diagram: https://github.com/Aadithyaar22/VaultRAG/blob/master/submission/02_architecture_diagram.png

Full project guide (PDF, 36 pages, plain English first): https://github.com/Aadithyaar22/VaultRAG/blob/master/docs/PROJECT_GUIDE.pdf

Real-document test report: https://github.com/Aadithyaar22/VaultRAG/blob/master/docs/REAL_DOCUMENT_TEST.md

## Live demo (optional, for judges)

http://148.100.99.19:8000 — runs on the IBM LinuxONE instance. Demo logins are on the sign-in screen (synthetic data only).
