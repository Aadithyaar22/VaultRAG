import os
DATA = os.environ.get("REAL_DATA_DIR", "./real_data")   # filled by download_real_data.sh
BASE = os.environ.get("BASE_URL", "http://localhost:8000") + "/api"
IDS_FILE = os.environ.get("E2E_IDS", "/tmp/e2e_ids.json")
import sys, glob, time, os, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app.services import extract, pii, injection, ml
root = DATA + "/realdocs"
for f in sorted(glob.glob(root + "/*/*")):
    name = os.path.basename(f); data = open(f, "rb").read()
    t0 = time.time(); text = extract.extract_text(name, data); dt = time.time() - t0
    chunks = extract.chunk_text(text)
    inj = [injection.scan(c) for c in chunks]
    flagged = [i for i, s in enumerate(inj) if s["flagged"]]
    p = ml.classify_document(text)
    print("=" * 78); print(name, "|", len(data), "bytes")
    print(f"  extracted {len(text):,} chars in {dt:.2f}s -> {len(chunks)} chunks (avg {len(text)//max(1,len(chunks))} chars)")
    print("  sample:", " ".join(text[:160].split()))
    print("  PII found:", pii.detect(text), "| injection-flagged chunks:", len(flagged), flagged[:5])
    print(f"  ML: dept={p['department']} ({p['department_confidence']}) sens={p['sensitivity']} ({p['sensitivity_confidence']}) roles={p['suggested_roles']}")
