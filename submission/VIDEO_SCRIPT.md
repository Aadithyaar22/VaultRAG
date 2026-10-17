# 3-minute demo video — script & shot list (target 2:50, hard limit 3:00)

Required by the rules: problem, **supporting data**, solution overview, IBM Z tech stack, **live demo of the LinuxONE instance and model**. Screenshots of the LinuxONE instance are judged evidence — keep the terminal and Jupyter on screen.

## Before recording
1. One terminal, two tunnels (keep it open; works even if the browser filter blocks raw IPs):
   `ssh -N -i "/Users/aadi/Hacktivisits IBM/keys/hacktivists.pem" -L 8001:127.0.0.1:8000 -L 38888:127.0.0.1:38888 linux1@148.100.99.19`
2. App: http://localhost:8001 (this IS the LinuxONE server). Jupyter: http://localhost:38888 — paste the token from `keys/jupyter_token.txt` into the login box (never show the file or the URL with `?token=`).
3. Second terminal ready with the evidence command (below). Reset demo data (Admin Demo Controls → Reset). Browser zoom 125%, hide bookmarks, close notifications.

Evidence command (run on camera):
`ssh -i "/Users/aadi/Hacktivisits IBM/keys/hacktivists.pem" linux1@148.100.99.19 'uname -m; lscpu | grep "Machine type"; grep -c nnpa /proc/cpuinfo; sudo docker ps --format "{{.Names}}: {{.Status}}"; systemctl is-active vaultrag'`

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | Slide 2 | "RAG assistants over confidential documents leak: they ignore who is asking, caches survive revocation, documents carry hidden instructions." |
| 0:15–0:28 | Slide 8 (benchmark table) | "In our synthetic test, conventional RAG disclosed restricted content in 23 of 23 probes; filter-only RAG leaked after revocation. VaultRAG leaked in none — a small suite, not a proof." |
| 0:28–0:42 | Slide 4 (architecture) | "Permissions live in a database. A Revocation-Safe Evidence Gate re-checks every document and version right before an answer is released, and fails closed." |
| 0:42–1:05 | **Evidence terminal** | "This runs on IBM LinuxONE: s390x, machine type 9175, an IBM z17, whose CPU reports the nnpa AI-accelerator feature. The app is a service, and IBM's Jupyter AI/ML container is running." |
| 1:05–1:25 | **Jupyter** → `shared/executed` → open Fraud_LSTM and Loan_Approval outputs (scroll to results) | "We completed IBM's AI/ML lab on this server — fraud LSTM, churn, MNIST to ONNX, and a hybrid ML plus LLM loan notebook all ran." |
| 1:25–1:50 | App as **hannah** → parental leave question; then **alice** same question | "HR gets a cited answer, version one, released by the gate. An employee gets nothing — no title, no passage." |
| 1:50–2:10 | Hannah asks again ("cache: hit revalidated") → as **adam** Vault untick `hr` on that document → Hannah asks again | "Cached, but revalidated. We revoke while she is logged in — the old answer is not released." |
| 2:10–2:25 | Demo Controls → **Revoke during generation** (trace) | "Revoke mid-generation: the gate discards the answer, regenerates from authorized sources, and abstains." |
| 2:25–2:48 | Demo Controls → **Simulate probing** → Security Center: risk score + "Models running on this server" card; mention poisoned document test | "Models trained on this server score behaviour: a probing burst jumps to high risk. Injection classifier plus rules, document classifier, hash-linked audit." |
| 2:48–2:58 | Slide 10 | "VaultRAG: answers that are safe at the moment they're released." |

Tips: do one dry run with a timer; speak slower than feels natural; cut dead air in editing; no API keys, `.env` or token visible.
