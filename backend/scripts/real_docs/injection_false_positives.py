import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
import sys, glob, os, collections, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app.services import extract, injection, ml
root = DATA + "/realdocs"
tot = collections.Counter(); rules = collections.Counter(); ex = {}
for f in sorted(glob.glob(root + "/*/*")):
    name = os.path.basename(f)
    if name.endswith(".docx"): continue
    chunks = extract.chunk_text(extract.extract_text(name, open(f, "rb").read()))
    for c in chunks:
        rg = injection.scan_regex(c); p = ml.injection_prob(c)
        tot["chunks"] += 1
        if rg["flagged"]: tot["regex_flag"] += 1; [rules.update([r]) for r in rg["rules"]]; ex.setdefault(rg["rules"][0], c[:230].replace("\n"," "))
        if p >= 0.5: tot["ml_flag"] += 1
        if p >= 0.8: tot["ml_quarantine"] += 1
        if rg["quarantine"]: tot["regex_quarantine"] += 1
        if rg["flagged"] and p >= 0.5: tot["both"] += 1
        if p >= 0.5 and not rg["flagged"] and "mlex" not in ex: ex["mlex"] = (round(p,2), c[:230].replace("\n"," "))
print(dict(tot)); print("regex rules fired:", dict(rules))
for k, v in ex.items(): print("-", k, "->", v)
