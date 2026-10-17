"""On-server predictive ML (scikit-learn). Models are TRAINED AT STARTUP from synthetic generated data, on whatever
machine runs the app (we run it on IBM LinuxONE / s390x) -- no pickled models are shipped because pickles are not
portable across scikit-learn versions or byte order.

  1. department + sensitivity classifier  -> suggests an ACL for an uploaded document, warns on over-exposure
  2. prompt-injection classifier          -> second opinion next to the regex rules (ensemble in injection.py)
  3. behavioural anomaly detector         -> IsolationForest over per-user audit-log windows -> risk score

Optional: if scikit-learn is unavailable everything degrades gracefully to the rule-based controls."""
import json
import platform
import random
import re
import sys
import threading
import time

from .. import db
from . import ml_data, ml_eval

try:
    import numpy as np
    import sklearn
    from sklearn.ensemble import IsolationForest
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline
    AVAILABLE = True
except Exception:  # pragma: no cover
    AVAILABLE = False

ROLES_FOR_DEPT = {"hr": ["hr"], "finance": ["finance"], "legal": ["legal"],
                  "general": ["employee", "hr", "finance", "legal", "administrator"]}
_lock = threading.Lock()
_models: dict = {}
_meta: dict = {}


def _text_clf(C: float, char: bool = False):
    if char:
        feats = FeatureUnion([("w", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)),
                              ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True))])
    else:
        feats = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
    return Pipeline([("f", feats), ("m", LogisticRegression(C=C, max_iter=2000, class_weight="balanced"))])


def _normal_windows(n=600, seed=5):
    rng = np.random.default_rng(seed)
    q = rng.poisson(3, n)
    denied = np.minimum(q, rng.binomial(np.maximum(q, 1), 0.12))
    inj = rng.poisson(0.03, n)
    return np.column_stack([q, denied, np.where(q > 0, denied / np.maximum(q, 1), 0), inj, q / 10.0])


def train() -> dict:
    """(Re)train everything; returns timing/size info. Safe to call repeatedly."""
    if not AVAILABLE:
        return {"available": False}
    t0 = time.perf_counter()
    with _lock:
        Xd, yd = ml_data.dept_dataset(); dept = _text_clf(8.0).fit(Xd, yd)
        Xs, ys = ml_data.sens_dataset(); sens = _text_clf(8.0).fit(Xs, ys)
        Xi, yi = ml_data.injection_dataset_v2(); inj = _text_clf(6.0, char=True).fit(Xi, yi)
        W = _normal_windows(); forest = IsolationForest(n_estimators=200, random_state=0).fit(W)
        _models.update(dept=dept, sens=sens, inj=inj, forest=forest, ref=np.sort(forest.score_samples(W)))
        _meta.clear()
        _meta.update(trained_at=time.strftime("%Y-%m-%dT%H:%M:%S"), train_seconds=round(time.perf_counter() - t0, 2),
                     sizes={"department": len(Xd), "sensitivity": len(Xs), "injection": len(Xi), "anomaly_windows": len(W)})
    return {"available": True, **_meta}


def ensure() -> bool:
    if not AVAILABLE:
        return False
    if not _models:
        train()
    return True


# ---------- 1. document classification ----------
def classify_document(text: str) -> dict | None:
    if not ensure():
        return None
    t = text[:4000]
    dp = _models["dept"].predict_proba([t])[0]; sp = _models["sens"].predict_proba([t])[0]
    di, si = int(dp.argmax()), int(sp.argmax())
    dept, sens = _models["dept"].classes_[di], _models["sens"].classes_[si]
    return {"department": dept, "department_confidence": round(float(dp[di]), 3),
            "sensitivity": sens, "sensitivity_confidence": round(float(sp[si]), 3),
            "suggested_roles": ROLES_FOR_DEPT[dept],
            "model": f"tfidf+logreg (scikit-learn {sklearn.__version__}) on {platform.machine()}"}


def overexposure(prediction: dict | None, chosen_roles: list[str], chosen_sensitivity: str) -> dict | None:
    """Warn when a document that looks departmental/sensitive is being shared more widely than predicted."""
    if not prediction or prediction["department_confidence"] < 0.6:
        return None
    extra = sorted(set(chosen_roles) - set(prediction["suggested_roles"]))
    order = ["public", "internal", "confidential", "restricted"]
    too_open = (prediction["department"] != "general" and extra)
    too_low = order.index(chosen_sensitivity) < order.index(prediction["sensitivity"]) - 1 \
        and prediction["sensitivity_confidence"] >= 0.6
    if not (too_open or too_low):
        return None
    why = []
    if too_open:
        why.append(f"looks like {prediction['department'].upper()} content but is shared with: {', '.join(extra)}")
    if too_low:
        why.append(f"labelled '{chosen_sensitivity}' but content looks '{prediction['sensitivity']}'")
    return {"warning": "possible over-exposure: " + "; ".join(why), "prediction": prediction}


# ---------- 2. injection classifier ----------
def injection_prob(text: str) -> float | None:
    """Max over sentences (an injected instruction is usually one sentence inside a longer chunk)."""
    if not ensure():
        return None
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 8] or [text]
    return float(_models["inj"].predict_proba(sents)[:, 1].max())


# ---------- 3. behavioural anomaly detection ----------
def _features_from_audit(window_minutes: int) -> dict[str, dict]:
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - window_minutes * 60))
    users: dict[str, dict] = {}
    for r in db.q("SELECT user_id, event_type FROM audit_log WHERE user_id IS NOT NULL AND ts >= ?", (cutoff,)):
        u = users.setdefault(r["user_id"], {"queries": 0, "denied": 0, "injection": 0})
        if r["event_type"] == "query_received":
            u["queries"] += 1
        elif r["event_type"] in ("response_blocked", "response_abstained", "stale_cache_rejected"):
            u["denied"] += 1
        elif r["event_type"].startswith("prompt_injection"):
            u["injection"] += 1
    return users


def risk_scores(window_minutes: int = 10) -> list[dict]:
    if not ensure():
        return []
    out = []
    for uid, f in _features_from_audit(window_minutes).items():
        q, d = f["queries"], f["denied"]
        row = np.array([[q, d, d / q if q else 0.0, f["injection"], q / 10.0]])
        s = float(_models["forest"].score_samples(row)[0])
        risk = round(100.0 * float(np.mean(_models["ref"] > s)), 1)  # share of normal windows that look MORE normal
        level = "high" if risk >= 99 else "elevated" if risk >= 90 else "normal"
        out.append({"user_id": uid, "window_minutes": window_minutes, "queries": q, "denied_or_abstained": d,
                    "denial_ratio": round(d / q, 2) if q else 0.0, "injection_events": f["injection"],
                    "risk": risk, "level": level})
    return sorted(out, key=lambda r: -r["risk"])


# ---------- status / held-out evaluation ----------
_eval_cache: dict = {}


def status() -> dict:
    base = {"available": AVAILABLE, "platform": platform.machine(), "byteorder": sys.byteorder,
            "python": platform.python_version()}
    if not ensure():
        return base
    if not _eval_cache:
        from .. import seed
        from . import injection
        mal, ben = ml_eval.MALICIOUS, ml_eval.BENIGN

        def rates(fn):
            tp = sum(bool(fn(t)) for t in mal); fp = sum(bool(fn(t)) for t in ben)
            return {"recall": f"{tp}/{len(mal)}", "false_positives": f"{fp}/{len(ben)}"}
        docs = {k: (t, s) for k, _title, s, _r, _d, t in seed.DOCS}
        dok = sok = 0
        for k, (text, sens) in docs.items():
            p = classify_document(text)
            dok += p["department"] == ml_eval.SEED_DEPT[k]; sok += p["sensitivity"] == sens
        _eval_cache.update(
            injection={"regex_only": rates(lambda t: injection.scan_regex(t)["flagged"]),
                       "ml_only": rates(lambda t: injection_prob(t) >= injection.ML_FLAG),
                       "ensemble": rates(lambda t: injection.scan(t)["flagged"]),
                       "note": "Own 30-sample suite: optimistic (we wrote it and tuned regex rules after seeing misses). On the independent deepset benchmark test split the shipped ensemble caught 20% overall / 32% English / 0% German with 0 false positives (docs/REAL_DOCUMENT_TEST.md)."},
            document_classifier={"department_correct": f"{dok}/{len(docs)}", "sensitivity_correct": f"{sok}/{len(docs)}",
                                 "note": "evaluated on the 9 seed documents (not in training data; vocabulary overlaps the phrase banks)"})
    return {**base, "sklearn": sklearn.__version__, **_meta, "evaluation": _eval_cache}
