"""Configurable PII detection + response policy. Redaction is a *second* control; it never
replaces authorization checks."""
import json
import re

from .. import db

_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<!\w)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{3}\)?[ -]?)\d{3}[ -]?\d{4}(?!\w)"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "employee_id": re.compile(r"\bEMP-\d{4,6}\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
}
DEFAULT_POLICY = {"mode": "redact", "types": list(_PATTERNS), "exempt_roles": ["hr"]}


def get_policy() -> dict:
    row = db.q1("SELECT value FROM settings WHERE key='pii_policy'")
    return json.loads(row["value"]) if row else dict(DEFAULT_POLICY)


def set_policy(policy: dict) -> dict:
    mode = policy.get("mode", "redact")
    if mode not in ("redact", "block", "off"):
        raise ValueError("mode must be redact|block|off")
    types = [t for t in policy.get("types", list(_PATTERNS)) if t in _PATTERNS]
    clean = {"mode": mode, "types": types, "exempt_roles": list(policy.get("exempt_roles", []))}
    db.conn().execute("INSERT INTO settings(key,value) VALUES('pii_policy',?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(clean),))
    return clean


def detect(text: str, types: list[str] | None = None) -> dict[str, int]:
    found = {}
    for t in types or _PATTERNS:
        n = len(_PATTERNS[t].findall(text))
        if n:
            found[t] = n
    return found


def apply_policy(text: str, roles: list[str]) -> tuple[str, dict, str]:
    """Returns (text, detections, action) where action is allow|redact|block."""
    pol = get_policy()
    found = detect(text, pol["types"])
    if pol["mode"] == "off" or not found or set(roles) & set(pol["exempt_roles"]):
        return text, found, "allow"
    if pol["mode"] == "block":
        return "", found, "block"
    for t in pol["types"]:
        text = _PATTERNS[t].sub(f"[REDACTED:{t}]", text)
    return text, found, "redact"
