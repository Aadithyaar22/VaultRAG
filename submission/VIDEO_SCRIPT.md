# 3-minute demo video — script & shot list (target 2:50, hard limit 3:00)

Format: screen recording + voice-over, MP4, 1080p. Required by the rules: problem, **supporting data**, solution overview, IBM Z tech stack, **live demo of the LinuxONE instance and model**. Screenshots of LinuxONE are judged evidence — show them on screen.

Setup before recording: reset demo data (Admin Demo Controls → Reset). Open two things: (a) terminal SSH'd into the LinuxONE instance, (b) the app via tunnel `ssh -N -L 8001:127.0.0.1:8000 -i keys/hacktivists.pem linux1@148.100.99.19` → http://localhost:8001 (this IS the s390x server).

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Slide 2 (problem) | "Companies want to ask questions of confidential documents — but ordinary RAG chatbots retrieve from everything, and even permission-filtered ones fail when access changes: a cached or in-flight answer can still reach someone who was just revoked. Documents can also carry hidden instructions." |
| 0:20–0:35 | Slide 7 table (supporting data) | "On our test suite, conventional RAG disclosed restricted content in all 23 probes; filter-only RAG leaked in both revocation scenarios. VaultRAG leaked in none — small synthetic suite, not a proof." |
| 0:35–0:55 | Slide 4 (architecture) | "VaultRAG keeps permissions in a database, retrieves only from allowed documents, and our Revocation-Safe Evidence Gate re-checks every supporting document and its version right before releasing an answer. Fail closed." |
| 0:55–1:15 | **Terminal on LinuxONE**: `uname -m` → s390x, `cat /etc/os-release`, `pgrep -af uvicorn`; browser at localhost:8001 | "Everything runs on this IBM LinuxONE Community Cloud server — s390x, Ubuntu 24.04 — and the model is Groq-hosted gpt-oss-120b via an OpenAI-compatible API." |
| 1:15–1:40 | Login **hannah** → ask parental-leave question | "As an HR user: a grounded answer with a citation to the HR policy, version one, and a security badge — released by the gate." |
| 1:40–1:55 | Switch to **alice** → same question | "An employee asks the same: no HR evidence retrieved, no title revealed." |
| 1:55–2:20 | Hannah asks again → "cache: hit revalidated". Then Vault as **adam** → on "HR Parental Leave Policy" untick the **hr** role. Hannah asks again | "Cached — but revalidated. Now the admin revokes access while she's logged in. Same question: the old cached answer is not released." |
| 2:20–2:35 | Demo Controls → **Revoke during generation** → show trace | "Revoke mid-generation: the gate detects it, discards the answer, regenerates from authorized sources, and here it abstains. Audit trail shows why." |
| 2:35–2:50 | Demo Controls → **Upload poisoned document**; Security Center → Verify hash chain | "A poisoned document is flagged and quarantined from the model. Every decision is in a hash-linked audit log. VaultRAG: answers that are safe at the moment they're released." |

Tips: keep Security Center events visible once; zoom the browser to 125%; do one dry run and time it; don't read the API key or `.env` on screen.
