import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
import sys, glob, os, time, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app.services import extract
root = DATA + "/realdocs"
print(f"{'file':40s} {'method':9s} {'quality':>7s} {'chars':>8s} {'chunks':>6s} {'dropped':>7s} {'secs':>5s}")
for f in sorted(glob.glob(root + "/*/*")):
    n = os.path.basename(f); t0 = time.time()
    text, rep = extract.extract_with_report(n, open(f, "rb").read())
    kept, dropped = extract.readable_chunks(extract.chunk_text(text))
    q = rep.get("quality")
    print(f"{n:40s} {rep['method']:9s} {('%.2f' % q) if q is not None else '  n/a':>7s} {len(text):8,d} {len(kept):6d} {dropped:7d} {time.time()-t0:5.1f}")
