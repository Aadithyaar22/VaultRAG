import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
import sys, glob, os, json, logging, statistics
logging.disable(logging.CRITICAL)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app.services import extract, injection, ml
root = DATA + "/realdocs"
D = DATA + "/deepset"
scores = {}
for f in sorted(glob.glob(root + "/*/*")):
    n = os.path.basename(f)
    if n.endswith(".docx"): continue
    ch = extract.chunk_text(extract.extract_text(n, open(f, "rb").read()))
    scores[n] = sorted(ml.injection_prob(c) for c in ch)
tune = scores["fin_irs_pub463_travel_expenses.pdf"]; others = {k: v for k, v in scores.items() if k != "fin_irs_pub463_travel_expenses.pdf"}
print("TUNE doc (IRS 463) chunk score percentiles: p50 %.2f p90 %.2f p95 %.2f p99 %.2f max %.2f" % tuple(tune[int(len(tune)*q)] if q < 1 else tune[-1] for q in (.5,.9,.95,.99,1.0)))
print("threshold | FP IRS(tune) | FP on 4 held-out real docs (chunks) | deepset-train EN recall (prompt) | deepset-train FP")
rows = []
for f in sorted(glob.glob(f"{D}/rows_train_*.json")): rows += [r["row"] for r in json.load(open(f))["rows"]]
import re
DE = re.compile(r"\b(der|die|das|und|ist|nicht|ich|sie|wie|was|eine|einen|zu|mit|für|auf|dem|den|von|sind|werden|bitte)\b", re.I)
en = [r for r in rows if len(DE.findall(r["text"])) < 2 and not re.search(r"[äöüß]", r["text"])]
pos = [ml.injection_prob(r["text"]) for r in en if r["label"] == 1]; neg = [ml.injection_prob(r["text"]) for r in en if r["label"] == 0]
for th in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.93, 0.96):
    fp_t = sum(s >= th for s in tune); fp_o = sum(s >= th for v in others.values() for s in v); n_o = sum(len(v) for v in others.values())
    print(f"  {th:>4}   | {fp_t:>3}/{len(tune)} ({100*fp_t/len(tune):4.1f}%) | {fp_o:>3}/{n_o} ({100*fp_o/n_o:4.1f}%) | {sum(s>=th for s in pos)}/{len(pos)} ({100*sum(s>=th for s in pos)/len(pos):3.0f}%) | {sum(s>=th for s in neg)}/{len(neg)}")
