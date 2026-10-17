"""Local vector store over the SQLite `chunks` table. Search is constrained to an explicit set of
document IDs computed from the authoritative DB *before* retrieval; callers must additionally
re-verify every candidate (a metadata filter alone is not trusted)."""
import json

from .. import db
from .embeddings import cosine, embed


def search(question: str, allowed: dict[str, dict], k: int, min_score: float) -> list[dict]:
    if not allowed:
        return []
    qv = embed([question])[0]
    ids = list(allowed)
    rows = db.q(
        "SELECT c.id, c.doc_id, c.doc_version, c.idx, c.text, c.vector, c.injection_score, c.quarantined "
        "FROM chunks c JOIN documents d ON d.id=c.doc_id AND d.version=c.doc_version "
        "WHERE c.doc_id IN (%s)" % ",".join("?" * len(ids)), tuple(ids))
    scored = []
    for r in rows:
        vec = {int(i): v for i, v in json.loads(r["vector"]).items()}
        s = cosine(qv, vec)
        if s >= min_score:
            scored.append((s, r))
    scored.sort(key=lambda x: -x[0])
    return [{"chunk_id": r["id"], "doc_id": r["doc_id"], "doc_version": r["doc_version"], "idx": r["idx"],
             "text": r["text"], "score": round(s, 4), "injection_score": r["injection_score"],
             "quarantined": bool(r["quarantined"])} for s, r in scored[:k]]
