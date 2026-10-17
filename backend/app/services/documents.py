"""Document + permission lifecycle. Every mutation bumps versions and invalidates dependent cache
entries inside the same transaction, then writes an audit record."""
import json
import re

from .. import db
from ..util import new_id, now, sha256
from . import audit, injection, pii, rseg
from .embeddings import embed
from .extract import chunk_text, extract_with_report, readable_chunks

ROLES = ["employee", "hr", "finance", "legal", "administrator"]
SENSITIVITIES = ["public", "internal", "confidential", "restricted"]


def _validate(sensitivity: str, roles: list[str]) -> None:
    if sensitivity not in SENSITIVITIES:
        raise ValueError(f"sensitivity must be one of {SENSITIVITIES}")
    bad = [r for r in roles if r not in ROLES]
    if bad or not roles:
        raise ValueError(f"allowed_roles must be a non-empty subset of {ROLES}")


def ingest(*, title: str, sensitivity: str, filename: str, data: bytes, allowed_roles: list[str],
           actor_id: str | None, doc_id: str | None = None) -> dict:
    _validate(sensitivity, allowed_roles)
    text, report = extract_with_report(filename, data)
    pieces, dropped = readable_chunks(chunk_text(text))
    if not pieces:
        raise ValueError("No readable text could be extracted (scanned images or unusual fonts?). Upload a text-based PDF, DOCX or TXT.")
    if dropped and dropped > len(pieces):
        raise ValueError(f"Most of this file's text is unreadable ({dropped} of {dropped + len(pieces)} sections). Upload a text-based version.")
    # Sentence-level neutralisation: drop only the instruction-like sentences, keep the legitimate text around them.
    # A chunk that is still quarantine-worthy afterwards (e.g. entirely injected) stays quarantined as a whole.
    orig_scans = [injection.scan(p) for p in pieces]
    removed_per_chunk: dict[int, int] = {}
    for i, (p, sc) in enumerate(zip(pieces, orig_scans)):
        if not sc["quarantine"]:
            continue
        sents = re.split(r"(?<=[.!?])\s+|\n+", p)
        kept = [x for x in sents if x.strip() and not injection.scan(x)["quarantine"]]
        if len(sents) > len(kept) and sum(len(x) for x in kept) >= 60:
            removed_per_chunk[i] = len([x for x in sents if x.strip()]) - len(kept)
            pieces[i] = " ".join(kept) + " [instruction-like text removed]"
    vectors = embed(pieces)
    scans = [injection.scan(p) for p in pieces]
    pii_total = sum(sum(pii.detect(p).values()) for p in pieces)
    ts = now()
    with db.tx() as c:
        existing = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone() if doc_id else None
        if doc_id and not existing:
            raise LookupError("document not found")
        if existing:
            version = existing["version"] + 1
            c.execute("UPDATE documents SET title=?, sensitivity=?, filename=?, version=?, status='active', "
                      "injection_flagged=?, pii_count=?, updated_at=? WHERE id=?",
                      (title, sensitivity, filename, version, int(any(s["flagged"] for s in orig_scans)),
                       pii_total, ts, doc_id))
            c.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        else:
            doc_id, version = new_id("doc"), 1
            c.execute("INSERT INTO documents(id,title,sensitivity,filename,version,acl_version,injection_flagged,"
                      "pii_count,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (doc_id, title, sensitivity, filename, 1, 1, int(any(s["flagged"] for s in orig_scans)),
                       pii_total, actor_id, ts, ts))
        _set_acl_rows(c, doc_id, allowed_roles, None)
        if existing:  # ACL version also moves: the evidence behind any cached answer has changed
            c.execute("UPDATE documents SET acl_version=acl_version+1 WHERE id=?", (doc_id,))
        for i, (p, v, s) in enumerate(zip(pieces, vectors, scans)):
            c.execute("INSERT INTO chunks(id,doc_id,doc_version,idx,text,vector,injection_score,quarantined) "
                      "VALUES(?,?,?,?,?,?,?,?)",
                      (f"{doc_id}:v{version}:c{i}", doc_id, version, i, p,
                       json.dumps({str(k): x for k, x in v.items()}), s["score"], int(s["quarantine"])))
        c.execute("INSERT OR REPLACE INTO document_versions VALUES(?,?,?,?,?,?)",
                  (doc_id, version, sha256(text), filename, len(pieces), ts))
        n_inv = rseg.invalidate_for_doc(doc_id, "document_replaced" if existing else "document_created")
        flagged = [i for i, s in enumerate(orig_scans) if s["flagged"]]
        audit.log("document_replaced" if existing else "document_uploaded", user_id=actor_id, outcome="ok",
                  doc_id=doc_id, version=version, chunks=len(pieces), dropped_unreadable=dropped, extraction=report.get("method"), roles=sorted(allowed_roles),
                  sensitivity=sensitivity, cache_invalidated=n_inv, pii_detected=pii_total)
        if flagged:
            audit.log("prompt_injection_detected_on_upload", user_id=actor_id, outcome="flagged", doc_id=doc_id,
                      chunks=flagged, rules=sorted({r for s in orig_scans for r in s["rules"]}), sentences_removed=removed_per_chunk,
                      quarantined=[i for i, s in enumerate(scans) if s["quarantine"]])
    meta = get_meta(doc_id)
    meta["extraction"] = {"method": report.get("method"), "quality": None if report.get("quality") is None else round(report["quality"], 2),
                          "unreadable_sections_dropped": dropped}
    return meta


def _set_acl_rows(c, doc_id: str, roles: list[str] | None, denied: list[str] | None) -> None:
    if roles is not None:
        c.execute("DELETE FROM document_acl WHERE doc_id=?", (doc_id,))
        c.executemany("INSERT INTO document_acl VALUES(?,?)", [(doc_id, r) for r in sorted(set(roles))])
    if denied is not None:
        c.execute("DELETE FROM document_user_deny WHERE doc_id=?", (doc_id,))
        c.executemany("INSERT INTO document_user_deny VALUES(?,?)", [(doc_id, u) for u in sorted(set(denied))])


def set_acl(doc_id: str, *, allowed_roles: list[str] | None, denied_users: list[str] | None,
            actor_id: str | None) -> dict:
    if allowed_roles is not None:
        _validate("internal", allowed_roles)
    with db.tx() as c:
        if not c.execute("SELECT 1 FROM documents WHERE id=? AND status='active'", (doc_id,)).fetchone():
            raise LookupError("document not found")
        _set_acl_rows(c, doc_id, allowed_roles, denied_users)
        c.execute("UPDATE documents SET acl_version=acl_version+1, updated_at=? WHERE id=?", (now(), doc_id))
        n = rseg.invalidate_for_doc(doc_id, "acl_changed")
        audit.log("permission_changed", user_id=actor_id, outcome="ok", doc_id=doc_id,
                  roles=allowed_roles, denied_users=denied_users, cache_invalidated=n)
    return get_meta(doc_id)


def remove(doc_id: str, actor_id: str | None) -> None:
    with db.tx() as c:
        if not c.execute("SELECT 1 FROM documents WHERE id=? AND status='active'", (doc_id,)).fetchone():
            raise LookupError("document not found")
        c.execute("UPDATE documents SET status='removed', acl_version=acl_version+1, updated_at=? WHERE id=?",
                  (now(), doc_id))
        c.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        n = rseg.invalidate_for_doc(doc_id, "document_removed")
        audit.log("document_removed", user_id=actor_id, outcome="ok", doc_id=doc_id, cache_invalidated=n)


def set_user_roles(user_id: str, roles: list[str], actor_id: str | None) -> None:
    _validate("internal", roles) if roles else None
    with db.tx() as c:
        if not c.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            raise LookupError("user not found")
        c.execute("DELETE FROM user_roles WHERE user_id=?", (user_id,))
        c.executemany("INSERT INTO user_roles VALUES(?,?)", [(user_id, r) for r in sorted(set(roles))])
        c.execute("UPDATE users SET authz_version=authz_version+1 WHERE id=?", (user_id,))
        n = rseg.invalidate_for_user(user_id, "roles_changed")
        audit.log("permission_changed", user_id=actor_id, outcome="ok", target_user=user_id,
                  roles=sorted(set(roles)), cache_invalidated=n)


def get_meta(doc_id: str) -> dict:
    d = db.q1("SELECT * FROM documents WHERE id=?", (doc_id,))
    acl = [r["role"] for r in db.q("SELECT role FROM document_acl WHERE doc_id=?", (doc_id,))]
    deny = [r["user_id"] for r in db.q("SELECT user_id FROM document_user_deny WHERE doc_id=?", (doc_id,))]
    vers = [dict(v) for v in db.q("SELECT version, content_sha256, filename, chunk_count, created_at "
                                  "FROM document_versions WHERE doc_id=? ORDER BY version", (doc_id,))]
    out = {k: d[k] for k in ("id", "title", "sensitivity", "filename", "version", "acl_version", "status",
                             "injection_flagged", "pii_count", "created_at", "updated_at")}
    out.update(allowed_roles=sorted(acl), denied_users=sorted(deny), versions=vers)
    return out
