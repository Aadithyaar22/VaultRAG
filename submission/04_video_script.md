# 04 · Demo video — script, shot list and checklist (limit 3:00 — aim for 2:50)

The rules ask the video to cover: **the problem, supporting data, the solution, how it uses IBM Z/LinuxONE, and a live demo of the LinuxONE instance and the model.** Judges also score clarity, so speak slowly.

## Before you record (10 minutes)
1. Open **one terminal** and start the tunnel (keeps working even if the venue blocks raw IP addresses). Leave it open:
   `ssh -N -i <KEY> -L 8001:127.0.0.1:8000 -L 38888:127.0.0.1:38888 linux1@148.100.99.19`
2. Browser tab 1: `http://localhost:8001` (this IS the LinuxONE server). Tab 2: `http://localhost:38888` for Jupyter (paste the token from `keys/jupyter_token.txt`; never show the token).
3. Sign in as **adam** → Demo Controls → **Reset demo data**. Sign out.
4. Slides open in a PDF viewer: `01_pitch_deck.pdf` (slides 2, 11, 12, 5, 14).
5. Second terminal ready for the evidence command:
   `ssh -i <KEY> linux1@148.100.99.19 'uname -m; lscpu | grep "Machine type"; grep -c nnpa /proc/cpuinfo; sudo docker ps --format "{{.Names}}: {{.Status}}"; systemctl is-active vaultrag'`
6. Browser zoom 125%, bookmarks bar hidden, notifications off. **Nothing with keys, tokens or `.env` on screen.**
7. Do one dry run with a timer.

## Script (narration is word-for-word; times are targets)
| Time | On screen | Say |
|---|---|---|
| 0:00–0:14 | Slide 2 (the problem) | “Companies want to ask AI questions about private documents. But normal tools ignore who is asking, keep answering after access is taken away, and can be tricked by hidden instructions inside files.” |
| 0:14–0:30 | Slide 12 (real documents) | “We tested our system on six real public documents, across six user roles, on the live server. All fifteen authorized questions were answered correctly with sources, and none of twenty-one unauthorized attempts leaked anything.” |
| 0:30–0:45 | Slide 5 (architecture) | “VaultRAG decides permissions in a database before it searches, and re-checks every source right before it shows an answer. We call this the Revocation-Safe Evidence Gate. If anything changed, the answer is thrown away.” |
| 0:45–1:08 | Terminal: evidence command | “Everything runs on IBM LinuxONE. This is s390x, machine type 9175, an IBM z17, and its processor reports the AI accelerator feature. The app runs as a service, and IBM’s AI/ML lab container runs here too.” |
| 1:08–1:20 | Jupyter tab: open a finished notebook (fraud or loan) | “We completed IBM’s lab here: fraud detection, churn, digit recognition exported to ONNX, and the loan notebook.” |
| 1:20–1:45 | Landing page → **Sign in** → *Hannah HR* → ask “How many weeks of paid parental leave do primary caregivers receive?” → open the source | “Hannah is in HR. She gets a cited answer, the document version, and a badge: released by the security gate.” |
| 1:45–1:58 | Sign out → *Alice* → same question | “Alice is an ordinary employee. Same question: nothing. No HR text, not even the document’s name.” |
| 1:58–2:20 | As Hannah ask again (badge “cache: hit revalidated”) → in a private window as **adam**: Document Vault → untick **hr** on *HR Parental Leave Policy* → Hannah asks again | “A saved answer is re-checked before it is shown. Now the admin removes HR access while Hannah is logged in. Asking again: the old answer is not released.” |
| 2:20–2:34 | Demo Controls → **Revoke during generation** → show the trace | “Even if access is removed while the AI is still writing, the final check catches it, throws the answer away, and finds nothing allowed.” |
| 2:34–2:50 | Demo Controls → **Simulate probing** → Security Center: risk score, models card (s390x), **Verify hash chain** | “Models trained on this server score unusual behaviour, and every decision is in a tamper-evident diary.” |
| 2:50–2:58 | Slide 14 (closing) | “VaultRAG: answers that are safe at the moment they are released.” |

## If something goes wrong while recording
- **Chat is slow or shows a model error:** wait 10 seconds and ask again (the AI service can rate-limit). Keep going; you can cut the pause when editing.
- **Browser says “Website not available”:** you opened the raw IP; use `http://localhost:8001` through the tunnel.
- **Demo state looks messy:** Demo Controls → Reset demo data, then start again.
- **Background does not move:** the Mac has *Reduce motion* turned on; harmless.

## After recording
Export MP4 (1080p or 720p, under 3:00) → upload to YouTube as **Unlisted** or **Public** → open the link in a private window → paste it into `03_form_answers.md` and the form.
