"""Hash-linked (tamper-evident, not immutable) audit trail.

Each entry's hash covers the previous entry's hash, so editing/deleting a row breaks verification
from that point on. Anyone with write access to the DB file could rewrite the whole chain; ship the
head hash externally for stronger guarantees. Details never contain credentials or raw document
text: questions are stored as a hash + length only.
"""
import json

from .. import db
from ..util import canonical, now, sha256

GENESIS = "0" * 64
_FORBIDDEN_KEYS = {"password", "api_key", "token", "secret", "text", "content"}


def _scrub(detail: dict) -> dict:
    return {k: v for k, v in (detail or {}).items() if k.lower() not in _FORBIDDEN_KEYS}


def log(event_type: str, *, request_id: str | None = None, user_id: str | None = None,
        outcome: str = "info", **detail) -> None:
    detail = _scrub(detail)
    with db._lock:  # chain head read + insert must be atomic
        row = db.conn().execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else GENESIS
        ts = now()
        body = canonical([ts, event_type, request_id, user_id, outcome, detail])
        h = sha256(prev + body)
        db.conn().execute(
            "INSERT INTO audit_log(ts,event_type,request_id,user_id,outcome,detail,prev_hash,hash)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (ts, event_type, request_id, user_id, outcome, json.dumps(detail, sort_keys=True), prev, h))


def verify_chain() -> dict:
    prev, n = GENESIS, 0
    for r in db.q("SELECT * FROM audit_log ORDER BY seq"):
        detail = json.loads(r["detail"])
        body = canonical([r["ts"], r["event_type"], r["request_id"], r["user_id"], r["outcome"], detail])
        if r["prev_hash"] != prev or sha256(prev + body) != r["hash"]:
            return {"valid": False, "first_bad_seq": r["seq"], "entries": n, "head": prev}
        prev, n = r["hash"], n + 1
    return {"valid": True, "entries": n, "head": prev}


def recent(limit: int = 100, event_types: list[str] | None = None, request_id: str | None = None):
    sql, params = "SELECT * FROM audit_log", []
    where = []
    if event_types:
        where.append("event_type IN (%s)" % ",".join("?" * len(event_types)))
        params += event_types
    if request_id:
        where.append("request_id=?")
        params.append(request_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY seq DESC LIMIT ?"
    params.append(limit)
    out = []
    for r in db.q(sql, tuple(params)):
        d = dict(r)
        d["detail"] = json.loads(d["detail"])
        out.append(d)
    return out
