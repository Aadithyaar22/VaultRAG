"""Writes the numbered text documents in submission/ (form answers come from answers.py so lengths are always checked)."""
import pathlib
from answers import A
out = pathlib.Path(__file__).parent.parent
REPO = "https://github.com/Aadithyaar22/VaultRAG"

# ---------------- 03 form answers ----------------
md = ["# 03 · Hack2Skill submission form — copy and paste", "",
      "Form closes **18 October 2026, 10:00 PM IST**. Fill the two `[…]` placeholders (video link) and confirm every link opens in a private window.", "",
      "**Project title (required format):** `Hacktivists_IBM Z Datathon 2026 Project`", "", "---", ""]
for k, v in A.items():
    md += [f"## {k}", "", v, ""]
    if k != "Challenge": md += [f"_({len(v)} of 1,024 characters)_", ""]
md += ["---", "", "## Upload your pitch deck (PDF, max 5 MB)", "", "`01_pitch_deck.pdf` — 14 slides, about 1 MB.", "",
       "## GitHub link of your project (must be public)", "", REPO, "",
       "## Video submission link (YouTube or Vimeo, max 3 minutes, MP4 720p/1080p)", "", "`[VIDEO URL]` — record with `04_video_script.md`; set to **Public** or **Unlisted**.", "",
       "## Share the link to your pitch deck PDF (only if you cannot upload the file)", "", f"{REPO}/blob/master/submission/01_pitch_deck.pdf", "",
       "## Link to all open-source resources used", "", "See `06_open_source_links.md` — paste its single-paragraph list.", "",
       "## Any other document (flowchart or architecture diagram)", "",
       f"Architecture diagram: {REPO}/blob/master/submission/02_architecture_diagram.png", "",
       f"Full project guide (PDF, 36 pages, plain English first): {REPO}/blob/master/docs/PROJECT_GUIDE.pdf", "",
       f"Real-document test report: {REPO}/blob/master/docs/REAL_DOCUMENT_TEST.md", "",
       "## Live demo (optional, for judges)", "", "http://148.100.99.19:8000 — runs on the IBM LinuxONE instance. Demo logins are on the sign-in screen (synthetic data only).", ""]
(out / "03_form_answers.md").write_text("\n".join(md))

# ---------------- 04 video script ----------------
(out / "04_video_script.md").write_text('''# 04 · Demo video — script, shot list and checklist (limit 3:00 — aim for 2:50)

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
''')

# ---------------- 05 judges Q&A ----------------
(out / "05_judges_QA.md").write_text('''# 05 · Questions judges may ask — and honest answers

Keep answers short and true. Where we have a weakness, say it first.

**1. How is this different from normal role-based access in a vector database?**
Filtering at search time is not enough: a saved answer, or an answer still being written, can outlive a permission change. We attach every answer to the exact document and permission versions it used and re-check them at release time. The database — not the vector store’s filter — decides.

**2. Is it novel?**
We did not do a prior-art review, so we do not claim novelty. We built and tested a specific combination of known ideas — permission-first retrieval, versioned evidence, release-time re-validation, fail-closed behaviour — and measured it.

**3. What stops a poisoned document from hijacking the AI?**
Mainly the design: the AI has no tools, sees only documents the user may read, treats them as data, and cannot read other documents anyway. On top of that we remove attack-like sentences. The detector itself is weak (about 20% on a public benchmark, 0% for German) — we say so.

**4. Does any data leave the server?**
Yes. The passages a user is allowed to read go to the Groq AI service to write the answer. Passages the user may not read never do. A model on the server (IBM Granite) is the planned fix and the code already supports switching the provider.

**5. How do you use IBM Z?**
The app, the 42 tests, and our ML models run on an IBM LinuxONE z17 (s390x). We completed IBM’s Jupyter AI/ML lab there. The Z AI accelerator and hardware encryption are planned, not used.

**6. Quantum-safe?**
Not implemented. It is on the roadmap.

**7. What if the AI makes things up?**
It must cite numbered evidence; answers without a valid citation are blocked; if the evidence does not answer, it must say so and we show “nothing I may share”. We cannot guarantee the wording is always right.

**8. What if the permission check fails or is down?**
The answer is blocked — even saved ones. There is a demo button and a test for this.

**9. How did you test it?**
42 automated tests; a benchmark against two baselines; a live test with six real public documents across six roles using the real model; an independent public injection benchmark. All reports, including the failures we found, are in the repository.

**10. What did the real documents teach you?**
They exposed eight bugs our own test files hid: DOCX tables unread, garbled PDF fonts, over-flagging of normal text, weak retrieval, citation-format blocking, rate-limit handling, and over-quarantining. All fixed with tests. Authorized answers went from 8/15 correct to 15/15.

**11. Will it scale?**
Not as built: one server and one SQLite file. The permission logic does not depend on that; storage would move to a replicated database and a separate authorization service.

**12. Why does the administrator not see everything?**
Managing documents and reading them are different powers. Separating them reduces insider risk. An admin can change who may read a file but cannot read it unless the file’s list names that role.

**13. Why SQLite and plain-Python search?**
They install on s390x with no native-library surprises, and they are enough for a prototype. A real deployment would use a replicated database and an embeddings model.

**14. What are the biggest weaknesses?**
(1) The injection detector is weak. (2) Allowed text goes to an outside AI service. (3) Quantum-safe security and the Z accelerator are not used. (4) One node, no SSO/MFA, demo accounts. (5) Small tests on public documents, not confidential data.

**15. Where is the code and how do we run it?**
https://github.com/Aadithyaar22/VaultRAG — README has the quick start; `docs/PROJECT_GUIDE.pdf` explains everything; the live demo is at http://148.100.99.19:8000.
''')

# ---------------- 06 open source ----------------
(out / "06_open_source_links.md").write_text('''# 06 · Open-source resources used (paste into the form)

**Single-paragraph version (for the form field):**

FastAPI https://github.com/fastapi/fastapi · Uvicorn https://github.com/encode/uvicorn · Pydantic https://github.com/pydantic/pydantic · pydantic-settings https://github.com/pydantic/pydantic-settings · python-multipart https://github.com/Kludex/python-multipart · pypdf https://github.com/py-pdf/pypdf · pdfminer.six https://github.com/pdfminer/pdfminer.six · python-docx https://github.com/python-openxml/python-docx · lxml https://github.com/lxml/lxml · httpx https://github.com/encode/httpx · scikit-learn https://github.com/scikit-learn/scikit-learn · fonttools https://github.com/fonttools/fonttools · pytest https://github.com/pytest-dev/pytest · SQLite https://sqlite.org · React https://github.com/facebook/react · Vite https://github.com/vitejs/vite · Tailwind CSS https://github.com/tailwindlabs/tailwindcss · TypeScript https://github.com/microsoft/TypeScript · Fonts: Inter, Manrope, Cormorant Garamond, JetBrains Mono (Google Fonts, SIL Open Font License).

**AI model:** `openai/gpt-oss-120b` (open-weight model by OpenAI) served by Groq https://groq.com (a hosted service, used through its OpenAI-compatible API).

**IBM resources:** IBM LinuxONE Community Cloud (instance + the `jupyterlab-image-s390x` container with IBM’s four demo notebooks, used for the mandatory lab).

**Public data used only for testing (not redistributed in the repository):**
- US Department of Labor FMLA Fact Sheet #28; OSHA “Workers’ Rights” (OSHA 3021); IRS Publication 463 (US government works)
- University of North Texas policy 05.069; Washington State DES “Travel Policies and Related Issues”
- Apache License 2.0 https://www.apache.org/licenses/LICENSE-2.0
- `deepset/prompt-injections` dataset (Apache-2.0) https://huggingface.co/datasets/deepset/prompt-injections

All third-party code is used unmodified under its own licence; all project code in the repository was written during the event.
''')

# ---------------- 07 checklist ----------------
(out / "07_submission_checklist.md").write_text('''# 07 · Submission checklist

Deadline on the form: **18 Oct 2026, 10:00 PM IST** (hub times can differ — ask the GAT organisers). Aim to submit **at least two hours early**.

## Ready now
- [x] Project title: `Hacktivists_IBM Z Datathon 2026 Project`
- [x] Track chosen: **AI Secured: Innovation Without Exposure**
- [x] Four text answers, each under 1,024 characters (`03_form_answers.md`)
- [x] Pitch deck PDF under 5 MB (`01_pitch_deck.pdf`)
- [x] Public GitHub repository: https://github.com/Aadithyaar22/VaultRAG (README, `.env.example`, sample data, tests, scripts)
- [x] Architecture diagram (`02_architecture_diagram.png`)
- [x] Open-source list (`06_open_source_links.md`)
- [x] Mandatory IBM lab completed and evidenced (`docs/IBM_LAB_EVIDENCE.md`; executed notebooks in `evidence/`)
- [x] Live demo on the LinuxONE instance: http://148.100.99.19:8000
- [x] Full project guide for the team (`08_project_guide.pdf`)

## Still to do
- [ ] **Record the 3-minute video** (`04_video_script.md`) and upload it (Public or Unlisted)
- [ ] Paste the video link into the form
- [ ] Every teammate registered on Hack2Skill (4–6 members, each in one team)

## Final checks (10 minutes before pressing Submit)
- [ ] Open the GitHub link, the video link and the deck link in a **private/incognito window** — each must open without asking for access
- [ ] The repository shows **no** `.env`, `.pem`, token or database files (search the file list)
- [ ] Video length is **under 3:00**, plays in 720p/1080p, no keys or tokens visible
- [ ] Deck PDF opens and is readable; file is under 5 MB
- [ ] The server is running: `curl http://148.100.99.19:8000/api/health`
- [ ] Demo data reset so judges see a clean demo (Demo Controls → Reset demo data)
- [ ] Press **Submit**, then screenshot the confirmation

## After judging
- [ ] Close port 8000, set `DEMO_MODE=false`, change demo passwords (guide, section C4)
- [ ] **Revoke the Groq API key** in the Groq console
- [ ] Delete unused local keys (`keys/linuxone_key*`)
''')
print("wrote documents")
