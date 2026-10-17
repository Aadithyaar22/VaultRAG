import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
"""Live end-to-end test, part 2. Requires part 1 to have uploaded the real documents (ids in /tmp/e2e_ids.json)."""
import json, time, concurrent.futures as cf, httpx
B = BASE; R = DATA + "/realdocs"
IDS = json.load(open(IDS_FILE))
def login(u): return {"Authorization": "Bearer " + httpx.post(f"{B}/auth/login", json={"username": u, "password": "demo-pass"}, timeout=30).json()["token"]}
H = {u: login(u) for u in ["alice", "hannah", "frank", "leo", "maya", "adam"]}
def ask(u, q): return httpx.post(f"{B}/chat", json={"question": q}, headers=H[u], timeout=120).json()
def blob(r): return json.dumps({"a": r["answer"], "c": r["citations"]}).lower()
def put_acl(doc, **body): return httpx.put(f"{B}/documents/{IDS[doc]}/acl", json=body, headers=H["adam"], timeout=30)
def events(n=60, t=None): return httpx.get(f"{B}/security/events?limit={n}" + (f"&event_type={t}" if t else ""), headers=H["adam"], timeout=30).json()
RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail)); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
Q1 = "How many workweeks of leave can an eligible employee take in a 12-month period under the FMLA?"
Q2 = "What is the maximum length of an authorized leave of absence without pay?"
Q4 = "What is the standard mileage rate for business use of a car?"
Q6 = "What kind of patent license does each Contributor grant under the Apache License?"

print("\n--- 1. metadata leakage: each user sees only documents their roles allow ---")
adm = httpx.get(f"{B}/documents", headers=H["adam"], timeout=30).json()
roles = {"alice": {"employee"}, "hannah": {"employee", "hr"}, "frank": {"employee", "finance"}, "leo": {"employee", "legal"}, "maya": {"employee", "hr", "finance"}}
uid = {"alice": "u_alice", "hannah": "u_hannah", "frank": "u_frank", "leo": "u_leo", "maya": "u_maya"}
for u, rs in roles.items():
    expected = sorted(d["title"] for d in adm if (set(d["allowed_roles"]) & rs) and uid[u] not in d["denied_users"])
    got = sorted(d["title"] for d in httpx.get(f"{B}/documents", headers=H[u], timeout=30).json())
    check(f"document list for {u} matches ACL exactly ({len(got)} docs)", got == expected, "" if got == expected else f"extra={set(got)-set(expected)} missing={set(expected)-set(got)}")
r1 = httpx.get(f"{B}/documents/{IDS['fmla']}/passage/{IDS['fmla']}:v1:c0", headers=H["alice"]); r2 = httpx.get(f"{B}/documents/doc_nonexistent/passage/x", headers=H["alice"])
check("restricted passage and nonexistent doc are indistinguishable to alice (404, same body)", r1.status_code == r2.status_code == 404 and r1.json() == r2.json())
ok_passage = httpx.get(f"{B}/documents/{IDS['fmla']}/passage/{IDS['fmla']}:v1:c0", headers=H["hannah"])
check("authorized passage lookup works for hannah", ok_passage.status_code == 200 and len(ok_passage.json()["text"]) > 50)

print("\n--- 2. revocation after a cached answer (hannah, FMLA) ---")
a = ask("hannah", Q1); b = ask("hannah", Q1)
check("hannah gets cited answer, then a revalidated cache hit", a["status"] == "answered" and b["cache"] == "hit_revalidated", f"{a['cache']}→{b['cache']}")
t = time.time(); put_acl("fmla", allowed_roles=["finance"]); c = ask("hannah", Q1); lat = (time.time() - t) * 1000
check("after revocation the cached answer is NOT released", "12 workweeks" not in blob(c) and c["status"] in ("abstained", "denied") and c["cache"] != "hit_revalidated", f"status={c['status']} reason={c['reason']} total {lat:.0f} ms incl. ACL change")
check("audit recorded permission_changed and cache_invalidated", any(e["event_type"] == "permission_changed" for e in events(40)) and any(e["event_type"] == "cache_invalidated" for e in events(40)))
put_acl("fmla", allowed_roles=["hr"]); d = ask("hannah", Q1)
check("access restored → fresh answer again", d["status"] == "answered" and "12 workweeks" in blob(d) and d["cache"] == "miss", f"cache={d['cache']}")

print("\n--- 5. user role change invalidates that user's cache (maya loses finance) ---")
ask("maya", Q4)
httpx.put(f"{B}/admin/users/u_maya/roles", json={"roles": ["employee", "hr"]}, headers=H["adam"], timeout=30)
g = ask("maya", Q4)
check("maya no longer gets finance answer after role change", "70 cents" not in blob(g) and g["status"] != "answered" or ("irs" not in blob(g) and "70 cents" not in blob(g)), f"status={g['status']}")
httpx.put(f"{B}/admin/users/u_maya/roles", json={"roles": ["employee", "hr", "finance"]}, headers=H["adam"], timeout=30)

print("\n--- 6. PII policy on a real document with real phone numbers (OSHA) ---")
qn = "What is the NIOSH toll-free Information Service number?"
pa, ph = ask("alice", qn), ask("hannah", qn)
check("alice (non-exempt) gets the number redacted", "232-4636" not in blob(pa) and ("[redacted:phone]" in blob(pa) or pa["status"] != "answered"), f"status={pa['status']} redact={('[redacted:phone]' in blob(pa))}")
check("hannah (HR exempt per policy) sees the number", "232-4636" in blob(ph), f"status={ph['status']}")

print("\n--- 7. administrator separation + server-side enforcement ---")
leaks = [q for q in (Q1, Q2, Q4, Q6) if any(t in blob(ask("adam", q)) for t in ("12 workweeks", "twelve (12)", "70 cents", "royalty-free", "ninety-nine"))]
check("administrator cannot read HR/Finance/Legal content via chat", not leaks, f"leaked on {leaks}" if leaks else "")
check("non-manager cannot change ACL (403)", httpx.put(f"{B}/documents/{IDS['osha']}/acl", json={"allowed_roles": ["employee"]}, headers=H["alice"]).status_code == 403)
check("non-manager cannot upload (403)", httpx.post(f"{B}/documents", headers=H["alice"], files={"file": ("a.txt", b"hello world " * 20, "text/plain")}, data={"title": "x", "sensitivity": "internal", "allowed_roles": "employee"}).status_code == 403)
check("non-reviewer cannot read security events (403)", httpx.get(f"{B}/security/events", headers=H["hannah"]).status_code == 403)
check("no token → 401", httpx.get(f"{B}/documents").status_code == 401)
check("forged token → 401", httpx.get(f"{B}/documents", headers={"Authorization": "Bearer eyJ1IjoidV9hZGFtIiwiZSI6OTk5OTk5OTk5OX0.deadbeef"}).status_code == 401)

print("\n--- 8. authorization service outage fails closed (also for cached answers) ---")
ask("hannah", "How many days do I have to file a complaint with OSHA if I was retaliated against for using my rights?")
httpx.post(f"{B}/admin/demo/authz-outage", json={"down": True}, headers=H["adam"])
o = ask("hannah", "How many days do I have to file a complaint with OSHA if I was retaliated against for using my rights?")
check("cached + normally-allowed answer is denied while authz is down", o["status"] == "denied" and o["answer"] == "" and o["reason"] == "authorization_service_unavailable", f"reason={o['reason']}")
httpx.post(f"{B}/admin/demo/authz-outage", json={"down": False}, headers=H["adam"])
check("service restored → answers again", ask("hannah", Q1)["status"] == "answered")

print("\n--- 9. revoke DURING generation (frank, IRS publication) ---")
race = httpx.post(f"{B}/admin/demo/revoke-during-generation", json={"username": "frank", "question": "What is the standard mileage rate for business use of a car? (race test)"}, headers=H["adam"], timeout=120).json()
rr = race["result"]; types = [e["event_type"] for e in race["trace"]]
check("answer generated for a user whose access was revoked before release is discarded", "70 cents" not in blob(rr) and rr["status"] in ("abstained", "denied") and "revocation_detected_before_release" in types, f"status={rr['status']} trace={types[-4:]}")
put_acl("irs", denied_users=[])
check("after clearing the deny, frank can read the IRS publication again", ask("frank", Q4)["status"] == "answered")

print("\n--- 10. concurrency: parallel requests from different users never cross-leak ---")
def job(u): r = ask(u, Q1); return u, r
with cf.ThreadPoolExecutor(12) as ex: out = list(ex.map(job, ["alice", "hannah"] * 6))
bad = [u for u, r in out if u == "alice" and ("12 workweeks" in blob(r) or r["citations"] and any("FMLA" in c["title"] for c in r["citations"]))]
good = sum(1 for u, r in out if u == "hannah" and r["status"] == "answered" and "12 workweeks" in blob(r))
check("12 parallel requests (6 alice / 6 hannah): alice never sees FMLA content", not bad, f"hannah correct {good}/6")

print("\n--- 12. upload validation ---")
def up_(name, data, mime="text/plain"): return httpx.post(f"{B}/documents", headers=H["adam"], files={"file": (name, data, mime)}, data={"title": "t", "sensitivity": "internal", "allowed_roles": "employee"}, timeout=90).status_code
check("unsupported type (.png) → 415", up_("x.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png") == 415)
check("empty text file → 422", up_("e.txt", b"   \n  ") == 422)
check("garbled text → 422", up_("g.txt", ("F0zNO2b0wNF ENzPSz CzN0Sb0wNF wV 0fS il6 NA 0fS ilFO sEEL9hIuAdhSRhylIQhdpolhSIcAEIAy1HbT\n\n" * 8).encode()) == 422)
check("file over 10 MB → 413", up_("big.txt", b"lorem ipsum " * 1_000_000) == 413)
check("invalid role name → 422", httpx.post(f"{B}/documents", headers=H["adam"], files={"file": ("a.txt", b"hello world " * 20, "text/plain")}, data={"title": "t", "sensitivity": "internal", "allowed_roles": "wizard"}).status_code == 422)

print("\n--- 13. ML document classifier on the real documents (admin suggest endpoint) ---")
exp = {"fmla": "hr", "unt": "hr", "osha": "general", "irs": "finance", "wa": "finance", "apache": "legal"}
files = {"fmla": "hr_fmla/hr_fmla_factsheet.pdf", "unt": "hr_unt/hr_unt_leave_policy.pdf", "osha": "gen_osha/general_osha3021_workers_rights.pdf", "irs": "fin_irs463/fin_irs_pub463_travel_expenses.pdf", "wa": "fin_watravel/fin_wa_travel_policies.docx", "apache": "legal_apache/legal_apache_license_2.txt"}
right = 0
for k, rel in files.items():
    p = httpx.post(f"{B}/documents/suggest", headers=H["adam"], files={"file": (rel.split("/")[-1], open(f"{R}/{rel}", "rb").read())}, timeout=90).json()["prediction"]
    right += p["department"] == exp[k]; print(f"      {k:7s} → {p['department']:8s} conf {p['department_confidence']:.2f} | sensitivity {p['sensitivity']:12s} conf {p['sensitivity_confidence']:.2f}")
check(f"department predicted correctly on real documents ({right}/6)", right >= 5)

print("\n--- 14. audit trail integrity + dashboard ---")
v = httpx.get(f"{B}/security/audit/verify", headers=H["adam"]).json()
check("hash chain verifies after the whole test", v["valid"], f"{v['entries']} entries")
st = httpx.get(f"{B}/stats", headers=H["adam"]).json()
check("dashboard counters reflect activity", st["queries"] > 50 and st["blocked"] > 0 and st["revocation_events"] > 0, f"queries={st['queries']} blocked={st['blocked']} revocations={st['revocation_events']} stale_cache={st['stale_cache_rejections']}")
risk = httpx.get(f"{B}/security/risk", headers=H["adam"]).json()["users"]
print("      risk:", [(r["user_id"], r["level"], r["risk"]) for r in risk[:5]])
passed = sum(1 for _, ok, _ in RESULTS if ok); print(f"\n==== {passed}/{len(RESULTS)} checks passed ====")
for n, ok, d in RESULTS:
    if not ok: print("FAILED:", n, d)
json.dump(RESULTS, open("/tmp/e2e_part2.json", "w"))
