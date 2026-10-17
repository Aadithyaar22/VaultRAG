import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
"""Retrieval recall on REAL documents: does the chunk containing the expected fact appear in the top-k?"""
import sys, os, logging, time, importlib
logging.disable(logging.CRITICAL)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app import db, seed
from app.config import get_settings
from app.services import documents, authz, vectorstore
R = DATA + "/realdocs"
db.init_db(":memory:"); seed.seed_all()
FILES = [("fmla", "hr_fmla/hr_fmla_factsheet.pdf", "hr"), ("unt", "hr_unt/hr_unt_leave_policy.pdf", "hr"), ("osha", "gen_osha/general_osha3021_workers_rights.pdf", "employee,hr,finance,legal,administrator"),
         ("irs", "fin_irs463/fin_irs_pub463_travel_expenses.pdf", "finance"), ("wa", "fin_watravel/fin_wa_travel_policies.docx", "finance"), ("apache", "legal_apache/legal_apache_license_2.txt", "legal")]
for key, rel, roles in FILES:
    documents.ingest(title=key, sensitivity="internal", filename=os.path.basename(rel), data=open(f"{R}/{rel}", "rb").read(), allowed_roles=roles.split(","), actor_id="u_adam")
# (question, substring that must appear in a retrieved chunk, user)
QS = [
 ("How many workweeks of leave can an eligible employee take in a 12-month period under the FMLA?", "12 workweeks", "u_hannah"),
 ("What is the maximum length of an authorized leave of absence without pay?", "twelve (12) months", "u_hannah"),
 ("How many days do I have to file a complaint with OSHA if I was retaliated against for using my rights?", "within 30 days", "u_alice"),
 ("What is the standard mileage rate for business use of a car?", "70 cents", "u_frank"),
 ("Who must specify the delegated approval level for control over travel expenses?", "agency head must specify", "u_frank"),
 ("What kind of patent license does each Contributor grant under the Apache License?", "perpetual, worldwide, non-exclusive", "u_leo"),
 ("What is the NIOSH toll-free information service number?", "1-800-232-4636", "u_alice"),
 ("When may an employee take FMLA leave for a serious health condition?", "serious health condition", "u_hannah"),
 ("What expenses can I deduct for business travel away from my tax home?", "tax home", "u_frank"),
 ("Is the work available under the Apache License redistributable with modifications?", "Derivative Works", "u_leo"),
 ("What must an employee do before a leave of absence without pay is approved?", "approval", "u_hannah"),
 ("What records do I need to keep to prove my car expenses?", "records", "u_frank"),
]
def run(k):
    hit = 0; ranks = []
    for q, needle, u in QS:
        cands = vectorstore.search(q, authz.accessible_docs(u), k, 0.0)
        pos = next((i + 1 for i, c in enumerate(cands) if needle.lower() in " ".join(c["text"].split()).lower()), None)
        ranks.append(pos); hit += pos is not None
    return hit, ranks
for k in (4, 6, 8):
    h, ranks = run(k); print(f"k={k}: recall {h}/{len(QS)}  ranks={ranks}")

print("\n--- debug NIOSH ---")
rows = db.q("SELECT c.id, c.idx, c.text, d.title FROM chunks c JOIN documents d ON d.id=c.doc_id WHERE d.title='osha'")
for r in rows:
    t = " ".join(r["text"].split())
    if "232" in t and "4636" in t or "NIOSH" in t: print("chunk idx", r["idx"], "|", t[:420]); print()
cands = vectorstore.search("What is the NIOSH toll-free information service number?", authz.accessible_docs("u_alice"), 8, 0.0)
print("top:", [(c["idx"], c["score"], c["doc_id"][-4:]) for c in cands])
