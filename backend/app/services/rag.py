"""Permission-aware RAG pipeline with the RSEG final gate.

modes:
  vaultrag     authz-before-retrieval + candidate re-verification + injection quarantine
               + revalidated cache + final release gate + regenerate/deny + fail closed
  filtered     BASELINE 2: permission-filtered retrieval only; naive cache; no final gate
  conventional BASELINE 1: no document-level authorization at all; naive cache
Baselines exist only for evaluation (scripts/benchmark.py); the API always uses `vaultrag`.
"""
import time
from typing import Callable

from ..config import get_settings
from ..util import new_id, sha256, norm_question
from . import audit, authz, llm, pii, rseg, vectorstore
from .authz import AuthzUnavailable

_NAIVE_CACHE: dict[tuple, dict] = {}  # baselines' cache: keyed (mode,user,question), never revalidated


def reset_naive_cache() -> None:
    _NAIVE_CACHE.clear()


def _result(rid, status, t0, *, answer="", citations=None, reason=None, cache="miss", security=None,
            llm_info=None):
    return {"request_id": rid, "status": status, "answer": answer, "citations": citations or [],
            "reason": reason, "cache": cache, "security": security or {},
            "llm": llm_info, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}


def _deny(rid, t0, user_id, reason, **extra):
    audit.log("response_blocked", request_id=rid, user_id=user_id, outcome="blocked", reason=reason, **extra)
    return _result(rid, "denied", t0, reason=reason, security={"released": False, "reason": reason, **extra})


def _doc_titles(doc_ids: list[str]) -> dict[str, str]:
    from .. import db
    if not doc_ids:
        return {}
    rows = db.q("SELECT id,title FROM documents WHERE id IN (%s)" % ",".join("?" * len(doc_ids)), tuple(doc_ids))
    return {r["id"]: r["title"] for r in rows}


def _build_evidence(candidates: list[dict], allowed: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Returns (llm_chunks, dependency_records). Only chunks of re-verified documents get here."""
    chunks = [c for c in candidates if not c["quarantined"] and c["doc_id"] in allowed
              and allowed[c["doc_id"]]["version"] == c["doc_version"]]
    deps: dict[str, dict] = {}
    for c in chunks:
        d = deps.setdefault(c["doc_id"], {"doc_id": c["doc_id"], "doc_version": c["doc_version"],
                                          "acl_version": allowed[c["doc_id"]]["acl_version"], "chunk_ids": []})
        d["chunk_ids"].append(c["chunk_id"])
    return chunks, list(deps.values())


def _finalize(question, user, chunks, raw) -> tuple[str, list[dict], dict]:
    """Deterministic post-processing: citation validation, canary check, PII policy."""
    import re
    # normalise citation styles models emit: 【1】, [1, 2], (1) -> [1][2]
    raw = re.sub(r"[【\[]\s*(\d+(?:\s*[,;]\s*\d+)*)\s*[】\]]",
                 lambda m: "".join(f"[{n}]" for n in re.findall(r"\d+", m.group(1))), raw)
    n_ev = len(chunks)
    cited = sorted({int(m) for m in re.findall(r"\[(\d+)\]", raw) if 1 <= int(m) <= n_ev})
    text = re.sub(r"\[(\d+)\]", lambda m: m.group(0) if 1 <= int(m.group(1)) <= n_ev else "", raw)
    if not cited:  # grounded answers must cite at least one authorised passage
        return "", [], {"blocked": "uncited_answer"}
    if llm.SYSTEM_PROMPT[:60].lower() in text.lower():
        return "", [], {"blocked": "system_prompt_leak"}
    text, found, action = pii.apply_policy(text, user["roles"])
    if action == "block":
        return "", [], {"blocked": "pii_policy", "pii": found}
    titles = _doc_titles(sorted({chunks[n - 1]["doc_id"] for n in cited}))
    cites = [{"n": n, "doc_id": chunks[n - 1]["doc_id"], "title": titles.get(chunks[n - 1]["doc_id"]),
              "doc_version": chunks[n - 1]["doc_version"], "chunk_id": chunks[n - 1]["chunk_id"],
              "passage": pii.apply_policy(chunks[n - 1]["text"], user["roles"])[0]} for n in cited]
    return text, cites, {"pii": found, "pii_action": action}


def run(user: dict, question: str, mode: str = "vaultrag",
        hooks: dict[str, Callable] | None = None, use_cache: bool = True) -> dict:
    s, hooks = get_settings(), hooks or {}
    rid, t0, uid = new_id("req"), time.perf_counter(), user["id"]
    qh = {"question_sha256": sha256(norm_question(question))[:16], "question_len": len(question)}
    audit.log("query_received", request_id=rid, user_id=uid, outcome="info", mode=mode, **qh)
    try:
        if mode != "vaultrag":
            return _run_baseline(rid, t0, user, question, mode, hooks)
        snap = authz.user_snapshot(uid)  # fail closed if authz is down
        if not snap:
            return _deny(rid, t0, uid, "user_inactive")
        if s.cache_enabled and use_cache:
            hit = rseg.cache_get(uid, question)
            if hit:
                ok, reasons = rseg.validate_release(uid, snap["authz_version"], hit["evidence"])
                if ok and hit["user_authz_version"] == snap["authz_version"]:
                    audit.log("cache_hit_revalidated", request_id=rid, user_id=uid, outcome="released",
                              docs=[e["doc_id"] for e in hit["evidence"]])
                    r = _result(rid, "answered", t0, cache="hit_revalidated", **hit["answer"])
                    r["security"] = {**r["security"], "released": True, "gate": "revalidated_cache"}
                    return r
                rseg.drop_entry(hit["key"])
                audit.log("stale_cache_rejected", request_id=rid, user_id=uid, outcome="blocked", reasons=reasons)
        attempts = 0
        while True:
            snap = authz.user_snapshot(uid)
            if not snap:
                return _deny(rid, t0, uid, "user_inactive")
            allowed = authz.accessible_docs(uid)                       # 1. authz BEFORE retrieval
            cands = vectorstore.search(question, allowed, s.retrieval_top_k, s.retrieval_min_score)
            verified = authz.accessible_docs(uid)                      # 2. independent re-verification
            cands = [c for c in cands if c["doc_id"] in verified]
            quarantined = [c for c in cands if c["quarantined"]]
            for c in quarantined:
                audit.log("prompt_injection_quarantined", request_id=rid, user_id=uid, outcome="flagged",
                          doc_id=c["doc_id"], chunk_id=c["chunk_id"], score=c["injection_score"])
            chunks, deps = _build_evidence(cands, verified)
            audit.log("retrieval", request_id=rid, user_id=uid, outcome="ok", attempt=attempts,
                      candidates=len(cands), used=[c["chunk_id"] for c in chunks],
                      authz_versions={d["doc_id"]: d["acl_version"] for d in deps})
            if not chunks:
                audit.log("response_abstained", request_id=rid, user_id=uid, outcome="abstained",
                          reason="no_authorized_evidence")
                return _result(rid, "abstained", t0, reason="no_authorized_evidence",
                               answer="I couldn't find information I'm permitted to share that answers this.",
                               security={"released": True, "gate": "no_evidence", "quarantined": len(quarantined)})
            if "after_retrieval" in hooks:
                hooks["after_retrieval"]({"user": user, "chunks": chunks, "attempt": attempts})
            res = llm.generate(question, chunks)                       # 3. generate (never streamed)
            if "before_gate" in hooks:
                hooks["before_gate"]({"user": user, "chunks": chunks, "attempt": attempts})
            ok, reasons = rseg.validate_release(uid, snap["authz_version"], deps)   # 4. final gate
            if not ok:
                audit.log("revocation_detected_before_release", request_id=rid, user_id=uid, outcome="discarded",
                          reasons=reasons, attempt=attempts, docs=[d["doc_id"] for d in deps])
                if attempts < s.rseg_max_regenerations:
                    attempts += 1
                    continue                                            # regenerate from current evidence
                return _deny(rid, t0, uid, "authorization_changed_during_generation", reasons=reasons)
            if res.text.strip().startswith("INSUFFICIENT_EVIDENCE"):
                audit.log("response_abstained", request_id=rid, user_id=uid, outcome="abstained",
                          reason="insufficient_evidence")
                return _result(rid, "abstained", t0, reason="insufficient_evidence",
                               answer="The documents I can access don't contain enough information to answer.",
                               security={"released": True, "gate": "passed"},
                               llm_info={"provider": res.provider, "generative": res.generative})
            text, cites, meta = _finalize(question, user, chunks, res.text)
            if "blocked" in meta:
                audit.log("pii_blocked" if meta["blocked"] == "pii_policy" else "output_blocked",
                          request_id=rid, user_id=uid, outcome="blocked", **{k: v for k, v in meta.items()})
                return _deny(rid, t0, uid, meta["blocked"])
            if meta.get("pii"):
                audit.log("pii_detected_in_response", request_id=rid, user_id=uid, outcome=meta["pii_action"],
                          pii=meta["pii"])
            payload = {"answer": text, "citations": cites,
                       "security": {"released": True, "gate": "passed", "attempts": attempts + 1,
                                    "auth_versions": {d["doc_id"]: d["acl_version"] for d in deps},
                                    "quarantined": len(quarantined), **{k: v for k, v in meta.items()}},
                       "llm_info": {"provider": res.provider, "generative": res.generative}}
            audit.log("response_released", request_id=rid, user_id=uid, outcome="released",
                      docs=[(d["doc_id"], d["doc_version"], d["acl_version"]) for d in deps], attempts=attempts + 1)
            if s.cache_enabled:
                rseg.cache_put(uid, question, snap["authz_version"],
                               {"answer": text, "citations": cites,
                                "security": payload["security"], "llm_info": payload["llm_info"]}, deps)
            return _result(rid, "answered", t0, **payload)
    except AuthzUnavailable:
        return _deny(rid, t0, uid, "authorization_service_unavailable")      # fail closed
    except llm.LLMNotConfigured as e:
        audit.log("llm_not_configured", request_id=rid, user_id=uid, outcome="error", error=str(e))
        return _result(rid, "error", t0, reason="model_not_configured", answer=str(e))
    except llm.LLMError as e:
        audit.log("llm_error", request_id=rid, user_id=uid, outcome="error", error=str(e))
        return _result(rid, "error", t0, reason="model_error", answer=str(e))
    except Exception as e:  # any unexpected failure while validating -> fail closed
        return _deny(rid, t0, uid, "internal_error_fail_closed", error=type(e).__name__)


def _run_baseline(rid, t0, user, question, mode, hooks) -> dict:
    s, uid = get_settings(), user["id"]
    ck = (mode, uid, norm_question(question))
    if s.cache_enabled and ck in _NAIVE_CACHE:
        return {**_NAIVE_CACHE[ck], "request_id": rid, "cache": "hit_unvalidated",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    allowed = authz.all_active_docs() if mode == "conventional" else authz.accessible_docs(uid)
    cands = vectorstore.search(question, allowed, s.retrieval_top_k, s.retrieval_min_score)
    chunks, deps = _build_evidence(cands, allowed)
    if not chunks:
        return _result(rid, "abstained", t0, reason="no_evidence", answer="No relevant information found.")
    if "after_retrieval" in hooks:
        hooks["after_retrieval"]({"user": user, "chunks": chunks, "attempt": 0})
    res = llm.generate(question, chunks)
    if "before_gate" in hooks:
        hooks["before_gate"]({"user": user, "chunks": chunks, "attempt": 0})
    if res.text.startswith("INSUFFICIENT_EVIDENCE"):
        return _result(rid, "abstained", t0, reason="insufficient_evidence", answer="Not enough information.")
    text, cites, meta = _finalize(question, user, chunks, res.text)
    out = _result(rid, "answered", t0, answer=text, citations=cites,
                  security={"released": True, "gate": "none"}, llm_info={"provider": res.provider})
    if s.cache_enabled:
        _NAIVE_CACHE[ck] = out
    return out
