"""Revocation-Safe Evidence Gate (RSEG).

Evidence dependency = (doc_id, doc_version, acl_version, chunk_ids). A cached or freshly generated
answer may be released only if, at release time and in ONE consistent DB read:
  * every supporting document is still active, at the same version and the same ACL version,
  * the user is still active, with the same authz_version,
  * the user can *currently* read every supporting document (re-derived from the DB, not the cache).
Anything else -> not releasable. Any exception/unavailability -> not releasable (fail closed).
"""
import json

from .. import db
from ..util import canonical, new_id, now, sha256, norm_question
from . import authz


def cache_key(user_id: str, question: str) -> str:
    return sha256(f"{user_id}|{norm_question(question)}")


def validate_release(user_id: str, user_authz_version: int, evidence: list[dict]) -> tuple[bool, list[str]]:
    """Returns (ok, reasons). Raises authz.AuthzUnavailable if the check cannot be completed."""
    if not evidence:
        return False, ["no_evidence"]
    with db._lock:  # one consistent snapshot relative to writers (which hold the same lock)
        snap = authz.user_snapshot(user_id)
        if not snap:
            return False, ["user_inactive_or_missing"]
        reasons = []
        if snap["authz_version"] != user_authz_version:
            reasons.append("user_authz_version_changed")
        readable = authz.accessible_docs(user_id)
        for ev in evidence:
            cur = readable.get(ev["doc_id"])
            d = db.q1("SELECT version, acl_version, status FROM documents WHERE id=?", (ev["doc_id"],))
            if not d or d["status"] != "active":
                reasons.append("document_removed")
            elif d["version"] != ev["doc_version"]:
                reasons.append("document_version_changed")
            elif d["acl_version"] != ev["acl_version"]:
                reasons.append("acl_version_changed")
            if cur is None:
                reasons.append("access_revoked")
        return (not reasons), sorted(set(reasons))


def cache_get(user_id: str, question: str) -> dict | None:
    row = db.q1("SELECT * FROM answer_cache WHERE key=?", (cache_key(user_id, question),))
    if not row:
        return None
    deps = [{"doc_id": d["doc_id"], "doc_version": d["doc_version"], "acl_version": d["acl_version"],
             "chunk_ids": json.loads(d["chunk_ids"])}
            for d in db.q("SELECT * FROM cache_deps WHERE cache_key=?", (row["key"],))]
    return {"key": row["key"], "user_authz_version": row["user_authz_version"],
            "answer": json.loads(row["answer_json"]), "evidence": deps}


def cache_put(user_id: str, question: str, user_authz_version: int, answer: dict, evidence: list[dict]) -> None:
    key = cache_key(user_id, question)
    with db.tx() as c:
        c.execute("DELETE FROM cache_deps WHERE cache_key=?", (key,))
        c.execute("INSERT OR REPLACE INTO answer_cache VALUES(?,?,?,?,?,?)",
                  (key, user_id, sha256(norm_question(question)), user_authz_version,
                   json.dumps(answer), now()))
        for ev in evidence:
            c.execute("INSERT INTO cache_deps VALUES(?,?,?,?,?)",
                      (key, ev["doc_id"], ev["doc_version"], ev["acl_version"], json.dumps(ev["chunk_ids"])))


def drop_entry(key: str) -> None:
    db.conn().execute("DELETE FROM cache_deps WHERE cache_key=?", (key,))
    db.conn().execute("DELETE FROM answer_cache WHERE key=?", (key,))


def invalidate_for_doc(doc_id: str, reason: str) -> int:
    from . import audit
    keys = [r["cache_key"] for r in db.q("SELECT DISTINCT cache_key FROM cache_deps WHERE doc_id=?", (doc_id,))]
    for k in keys:
        drop_entry(k)
    if keys:
        audit.log("cache_invalidated", outcome="ok", reason=reason, doc_id=doc_id, entries=len(keys))
    return len(keys)


def invalidate_for_user(user_id: str, reason: str) -> int:
    from . import audit
    keys = [r["key"] for r in db.q("SELECT key FROM answer_cache WHERE user_id=?", (user_id,))]
    for k in keys:
        drop_entry(k)
    if keys:
        audit.log("cache_invalidated", outcome="ok", reason=reason, user_id=user_id, entries=len(keys))
    return len(keys)
