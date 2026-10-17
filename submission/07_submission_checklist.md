# 07 · Submission checklist

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
