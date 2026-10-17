"""Heuristic prompt-injection detector for UNTRUSTED retrieved/uploaded text.

This is a defence-in-depth signal, not a guarantee: it is measured against a labelled test suite
(see scripts/benchmark.py) and the real boundary is architectural (authz before the LLM, evidence
delimited as data, no tools/actions, deterministic release gate)."""
import re

_RULES: list[tuple[str, float, re.Pattern]] = [
    ("override_instructions", 0.9, re.compile(r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(previous|prior|above|earlier|all|any|the|your)\b.{0,40}\b(instruction|rule|prompt|polic|guideline|restriction|security|access)", re.I | re.S)),
    ("override_security", 0.8, re.compile(r"\b(ignore|disregard|bypass|override|disable)\b.{0,30}\b(security|access)\b.{0,20}(restriction|rule|polic|control|check)", re.I | re.S)),
    ("reveal_system_prompt", 0.9, re.compile(r"\b(reveal|show|print|output|repeat|leak|disclose)\b.{0,40}\b(system prompt|hidden prompt|initial prompt|instructions|api key|secret|credential|password)", re.I | re.S)),
    ("role_hijack", 0.7, re.compile(r"\b(you are now|act as|pretend (to be|you are)|from now on you|new instructions?:|system:|assistant:|\[system\]|<\|?system\|?>)", re.I)),
    ("auth_escalation", 0.9, re.compile(r"\b(grant|give|treat)\b.{0,30}\b(me|the user|user)\b.{0,30}\b(admin|administrator|full access|all access|unrestricted)|\b(user|requester) (is|has been) (authori[sz]ed|an? admin)|access control(s)? (is|are) (disabled|suspended|waived)|\b(treat|consider|regard)\b.{0,40}\bas\b.{0,20}\b(admin|administrator)\b|\bgrant\b.{0,20}\b(full|unrestricted|all)\b.{0,10}\baccess", re.I | re.S)),
    ("exfiltration", 0.8, re.compile(r"\b(send|post|email|forward|upload|exfiltrate|transmit)\b.{0,50}(https?://|@[a-z0-9.-]+\.[a-z]{2,}|to the following (address|url))", re.I | re.S)),
    ("command_execution", 0.7, re.compile(r"\b(execute|run|invoke|call)\b.{0,30}\b(command|script|shell|tool|function|code|curl|rm -rf)\b", re.I | re.S)),
    ("confidentiality_override", 0.6, re.compile(r"\b(do not|don't|never)\b.{0,30}\b(mention|tell|warn|cite|redact|filter)\b.{0,40}\b(user|security|policy|restriction|redaction)", re.I | re.S)),
]

QUARANTINE_THRESHOLD = 0.7


def scan(text: str) -> dict:
    hits = [(name, w) for name, w, rx in _RULES if rx.search(text)]
    score = min(1.0, max((w for _, w in hits), default=0.0) + 0.05 * max(0, len(hits) - 1))
    return {"score": round(score, 2), "rules": [n for n, _ in hits], "flagged": bool(hits),
            "quarantine": score >= QUARANTINE_THRESHOLD}
