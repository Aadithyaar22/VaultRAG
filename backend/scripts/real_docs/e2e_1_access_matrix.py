import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
"""Live end-to-end test, part 1: upload real documents with ACLs, then a role x question access matrix."""
import json, time, sys, httpx
B = BASE; R = DATA + "/realdocs"
def login(u): return {"Authorization": "Bearer " + httpx.post(f"{B}/auth/login", json={"username": u, "password": "demo-pass"}, timeout=30).json()["token"]}
H = {}; 
def ask(user, q, timeout=90):
    t = time.time(); r = httpx.post(f"{B}/chat", json={"question": q}, headers=H[user], timeout=timeout).json(); r["_wall"] = round(time.time() - t, 2); return r
AD = login("adam"); print("reset:", httpx.post(f"{B}/admin/demo/reset", headers=AD, timeout=90).json()["reset"])
for u in ["alice", "hannah", "frank", "leo", "maya", "adam"]: H[u] = login(u)
DOCS = [  # key, title, file, mime, roles, sens
 ("fmla", "FMLA Fact Sheet 28 (US Dept of Labor)", "hr_fmla/hr_fmla_factsheet.pdf", "application/pdf", "hr", "confidential"),
 ("unt", "UNT Leave of Absence Without Pay Policy 05.069", "hr_unt/hr_unt_leave_policy.pdf", "application/pdf", "hr", "internal"),
 ("osha", "OSHA Workers' Rights (OSHA 3021)", "gen_osha/general_osha3021_workers_rights.pdf", "application/pdf", "employee,hr,finance,legal,administrator", "internal"),
 ("irs", "IRS Publication 463 Travel Gift and Car Expenses", "fin_irs463/fin_irs_pub463_travel_expenses.pdf", "application/pdf", "finance", "internal"),
 ("wa", "WA DES Travel Policies and Related Issues", "fin_watravel/fin_wa_travel_policies.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "finance", "internal"),
 ("apache", "Apache License 2.0", "legal_apache/legal_apache_license_2.txt", "text/plain", "legal", "internal"),
]
IDS = {}; print("\n== UPLOADS (as administrator) ==")
print(f"{'doc':8s} {'status':6s} {'secs':>5s} {'chunks':>6s} {'extraction':18s} {'inj_flag':>8s} {'pii':>4s} ml_warning")
for key, title, rel, mime, roles, sens in DOCS:
    data = open(f"{R}/{rel}", "rb").read(); t = time.time()
    r = httpx.post(f"{B}/documents", headers=AD, files={"file": (rel.split("/")[-1], data, mime)}, data={"title": title, "sensitivity": sens, "allowed_roles": roles}, timeout=180)
    dt = time.time() - t
    if r.status_code != 200: print(f"{key:8s} {r.status_code} {r.text[:150]}"); continue
    j = r.json(); IDS[key] = j["id"]; ex = j.get("extraction", {}); nchunks = j["versions"][-1]["chunk_count"]
    print(f"{key:8s} {r.status_code:<6d} {dt:5.1f} {nchunks:6d} {ex.get('method','?')+' q='+str(ex.get('quality')):18s} {str(bool(j['injection_flagged'])):>8s} {j['pii_count']:4d} {j.get('ml_warning')}")
json.dump(IDS, open(IDS_FILE, "w"))
Q = [  # id, question, expected tokens (any), allowed users, doc key
 ("Q1 FMLA", "How many workweeks of leave can an eligible employee take in a 12-month period under the FMLA?", ["12 workweeks", "twelve workweeks", "12 work weeks"], {"hannah", "maya"}, "fmla"),
 ("Q2 UNT", "What is the maximum length of an authorized leave of absence without pay?", ["twelve (12) months", "12 months", "twelve months"], {"hannah", "maya"}, "unt"),
 ("Q3 OSHA", "How many days do I have to file a complaint with OSHA if I was retaliated against for using my rights?", ["30 days"], {"alice", "hannah", "frank", "leo", "maya", "adam"}, "osha"),
 ("Q4 IRS", "What is the standard mileage rate for business use of a car?", ["70 cents", "$0.70", "0.70"], {"frank", "maya"}, "irs"),
 ("Q5 WA", "Who must specify the delegated approval level for control over travel expenses?", ["agency head"], {"frank", "maya"}, "wa"),
 ("Q6 Apache", "What kind of patent license does each Contributor grant under the Apache License?", ["perpetual", "royalty-free", "irrevocable", "non-exclusive"], {"leo"}, "apache"),
]
TITLES = {k: t for k, t, *_ in DOCS}
users = ["alice", "hannah", "frank", "leo", "maya", "adam"]
print("\n== ROLE x QUESTION MATRIX (real Groq model; A=answered correct+cited, .=nothing released, !!=LEAK or wrong) ==")
print(f"{'question':10s} " + " ".join(f"{u:>7s}" for u in users) + "   (expected visible to: allowed set)")
res = {"authorized_ok": 0, "authorized_total": 0, "unauth_ok": 0, "unauth_total": 0, "problems": [], "latency_ms": []}
for qid, q, toks, allowed, dk in Q:
    cells = []
    for u in users:
        r = ask(u, q); res["latency_ms"].append(r["latency_ms"]); blob = json.dumps({"a": r["answer"], "c": r["citations"]}).lower()
        cited = [c["title"] for c in r["citations"]]
        if u in allowed:
            res["authorized_total"] += 1
            ok = r["status"] == "answered" and any(t.lower() in blob for t in toks) and TITLES[dk] in cited
            if ok: res["authorized_ok"] += 1; cells.append("A")
            else: cells.append("!!"); res["problems"].append((qid, u, "authorized but " + r["status"], r["answer"][:140], cited))
        else:
            res["unauth_total"] += 1
            leaked = any(t.lower() in blob for t in toks) or TITLES[dk].lower() in blob or TITLES[dk] in cited
            if r["status"] in ("abstained", "denied") and not leaked: res["unauth_ok"] += 1; cells.append(".")
            elif not leaked and r["status"] == "answered" and not any(TITLES[dk] == c for c in cited): res["unauth_ok"] += 1; cells.append("." )  # answered from other readable docs, no leak
            else: cells.append("!!"); res["problems"].append((qid, u, "UNAUTH " + r["status"], r["answer"][:140], cited))
    print(f"{qid:10s} " + " ".join(f"{c:>7s}" for c in cells))
print(f"\nauthorized correct: {res['authorized_ok']}/{res['authorized_total']} | unauthorized properly blocked (no leak): {res['unauth_ok']}/{res['unauth_total']}")
lat = sorted(res["latency_ms"]); print(f"latency ms p50 {lat[len(lat)//2]:.0f}  p95 {lat[int(len(lat)*0.95)]:.0f}  max {lat[-1]:.0f}")
for p in res["problems"]: print("PROBLEM:", p)
json.dump(res, open("/tmp/e2e_part1.json", "w"), default=str)
