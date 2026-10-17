"""Heuristic prompt-injection detector for UNTRUSTED retrieved/uploaded text.

This is a defence-in-depth signal, not a guarantee: it is measured against a labelled test suite
(see scripts/benchmark.py) and the real boundary is architectural (authz before the LLM, evidence
delimited as data, no tools/actions, deterministic release gate)."""
import re

_RULES: list[tuple[str, float, re.Pattern]] = [
    ("override_instructions", 0.9, re.compile(r"\b(ignore|disregard|forget|override|bypass|discard|set aside)\b.{0,40}\b(previous|prior|preceding|above|earlier|all|any|the|your|every)\b.{0,40}\b(instruction|rule|prompt|polic|guideline|restriction|security|access|order|command|directive|task|request)", re.I | re.S)),
    ("topic_switch", 0.8, re.compile(r"\b(forget|ignore|disregard)\b.{0,20}\b(everything|all|anything)\b.{0,30}\b(before|previous|preceding|above|said|know)|\bnew (tasks?|orders?|assignment)s?\b.{0,12}\b(follow|:)|\bnow forget\b|\bstart over with a new\b", re.I | re.S)),
    ("output_only_hijack", 0.7, re.compile(r"\b(just|only) (say|output|print|reply with|respond with|write)\b.{0,40}[\"'“]|\b(do not|don't) (look|read|use)\b.{0,25}\b(documents?|context|sources?)\b|\bignore the documents?\b", re.I | re.S)),
    ("override_security", 0.8, re.compile(r"\b(ignore|disregard|bypass|override|disable)\b.{0,30}\b(security|access)\b.{0,20}(restriction|rule|polic|control|check)", re.I | re.S)),
    ("reveal_system_prompt", 0.9, re.compile(r"\b(reveal|show|print|output|repeat|leak|disclose)\b.{0,40}\b(system prompt|hidden prompt|initial prompt|instructions|api key|secret|credential|password)", re.I | re.S)),
    ("role_hijack", 0.7, re.compile(r"\b(you are now|act as|pretend (to be|you are)|from now on you|new instructions?:|(?:^|\n|\[)\s*(?:system|assistant)\s*:|\[system\]|<\|?system\|?>)", re.I)),
    ("auth_escalation", 0.9, re.compile(r"\b(grant|give|treat)\b.{0,30}\b(me|the user|user)\b.{0,30}\b(admin|administrator|full access|all access|unrestricted)|\b(user|requester) (is|has been) (authori[sz]ed|an? admin)|access control(s)? (is|are) (disabled|suspended|waived)|\b(treat|consider|regard)\b.{0,40}\bas\b.{0,20}\b(admin|administrator)\b|\bgrant\b.{0,20}\b(full|unrestricted|all)\b.{0,10}\baccess", re.I | re.S)),
    ("exfiltration", 0.8, re.compile(r"\b(send|post|email|forward|upload|exfiltrate|transmit)\b.{0,50}(https?://|@[a-z0-9.-]+\.[a-z]{2,}|to the following (address|url))", re.I | re.S)),
    ("command_execution", 0.7, re.compile(r"\b(execute|run|invoke|call)\b.{0,30}\b(command|script|shell|tool|function|code|curl|rm -rf)\b", re.I | re.S)),
    ("confidentiality_override", 0.6, re.compile(r"\b(do not|don't|never)\b.{0,30}\b(mention|tell|warn|cite|redact|filter)\b.{0,40}\b(user|security|policy|restriction|redaction)", re.I | re.S)),
]

QUARANTINE_THRESHOLD = 0.7


def scan_regex(text: str) -> dict:
    hits = [(name, w) for name, w, rx in _RULES if rx.search(text)]
    score = min(1.0, max((w for _, w in hits), default=0.0) + 0.05 * max(0, len(hits) - 1))
    return {"score": round(score, 2), "rules": [n for n, _ in hits], "flagged": bool(hits),
            "quarantine": score >= QUARANTINE_THRESHOLD}


# Calibrated on real documents + a public benchmark (see docs/REAL_DOCUMENT_TEST.md): at 0.5 the classifier flagged ~30%
# of ordinary real-document chunks; at 0.85 / 0.90 it flagged ~0-2%.
ML_FLAG = 0.85
ML_QUARANTINE = 0.90


def scan(text: str) -> dict:
    """Ensemble: regex rules OR the on-server ML classifier (when scikit-learn is available)."""
    from . import ml
    r = scan_regex(text)
    p = ml.injection_prob(text) if ml.AVAILABLE else None
    r["ml_score"] = None if p is None else round(p, 3)
    if p is not None:
        if p >= ML_FLAG and not r["flagged"]:
            r["rules"] = r["rules"] + ["ml_classifier"]
        r["flagged"] = r["flagged"] or p >= ML_FLAG
        r["quarantine"] = r["quarantine"] or p >= ML_QUARANTINE
        r["score"] = round(max(r["score"], p), 2)
    return r
