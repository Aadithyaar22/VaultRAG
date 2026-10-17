import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
import sys, glob, json, re, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app.services import injection, ml
D = DATA + "/deepset"
def load(split):
    rows = []
    for f in sorted(glob.glob(f"{D}/rows_{split}_*.json")): rows += [r["row"] for r in json.load(open(f))["rows"]]
    return rows
DE = re.compile(r"\b(der|die|das|und|ist|nicht|ich|sie|wie|was|eine|einen|zu|mit|für|auf|dem|den|von|sind|werden|bitte|Sie)\b", re.I)
def lang(t): return "de" if len(DE.findall(t)) >= 2 or re.search(r"[äöüß]", t) else "en"
def rates(rows, fn, name):
    out = []
    for lg in ("all", "en", "de"):
        r = [x for x in rows if lg == "all" or lang(x["text"]) == lg]
        pos = [x for x in r if x["label"] == 1]; neg = [x for x in r if x["label"] == 0]
        tp = sum(bool(fn(x["text"])) for x in pos); fp = sum(bool(fn(x["text"])) for x in neg)
        out.append(f"{lg}: recall {tp}/{len(pos)} ({100*tp/max(1,len(pos)):.0f}%) FP {fp}/{len(neg)} ({100*fp/max(1,len(neg)):.0f}%)")
    print(f"{name:26s}", " | ".join(out))
for split in (sys.argv[1:] or ["train"]):
    rows = load(split); print(f"\n== deepset/prompt-injections {split} ({len(rows)} rows; {sum(r['label'] for r in rows)} injections) ==")
    rates(rows, lambda t: injection.scan_regex(t)["flagged"], "regex only")
    for th in (0.5, 0.7, 0.85, 0.95):
        rates(rows, lambda t, th=th: ml.injection_prob(t) >= th, f"ML only  >= {th}")
    rates(rows, lambda t: injection.scan(t)["flagged"], "ensemble (current)")
    rates(rows, lambda t: injection.scan(t)["quarantine"], "ensemble QUARANTINE")
