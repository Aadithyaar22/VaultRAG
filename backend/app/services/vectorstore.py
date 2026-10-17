"""Local vector store over the SQLite `chunks` table. Search is constrained to an explicit set of
document IDs computed from the authoritative DB *before* retrieval; callers must additionally
re-verify every candidate (a metadata filter alone is not trusted)."""
import json

from .. import db
import math

from .embeddings import _tokens, cosine, embed


def search(question: str, allowed: dict[str, dict], k: int, min_score: float) -> list[dict]:
    if not allowed:
        return []
    qv = embed([question])[0]
    ids = list(allowed)
    rows = db.q(
        "SELECT c.id, c.doc_id, c.doc_version, c.idx, c.text, c.vector, c.injection_score, c.quarantined "
        "FROM chunks c JOIN documents d ON d.id=c.doc_id AND d.version=c.doc_version "
        "WHERE c.doc_id IN (%s)" % ",".join("?" * len(ids)), tuple(ids))
    # Hybrid ranking: semantic-ish cosine (hashed uni+bigram TF) blended with BM25 keyword scoring. BM25's IDF stops
    # near-duplicate boilerplate chunks from outranking the one chunk that actually contains the rare answer terms.
    qtoks = list(dict.fromkeys(_tokens(question)))
    docs = [(r, _tokens(r["text"])) for r in rows]
    n = max(1, len(docs)); avgdl = sum(len(t) for _, t in docs) / n or 1.0
    df = {w: sum(1 for _, t in docs if w in set(t)) for w in qtoks}
    idf = {w: math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) for w in qtoks}
    cos_s, bm_s = [], []
    for r, toks in docs:
        vec = {int(i): v for i, v in json.loads(r["vector"]).items()}
        cos_s.append(cosine(qv, vec))
        tf = {}
        for w in toks:
            if w in idf:
                tf[w] = tf.get(w, 0) + 1
        bm = sum(idf[w] * (f * 2.2) / (f + 1.2 * (1 - 0.75 + 0.75 * len(toks) / avgdl)) for w, f in tf.items())
        bm_s.append(bm)
    cmax = max(cos_s, default=0) or 1.0; bmax = max(bm_s, default=0) or 1.0
    scored = []
    for (r, _), c, b in zip(docs, cos_s, bm_s):
        blended = 0.4 * (c / cmax) + 0.6 * (b / bmax)
        if c >= min_score:   # relevance gate unchanged: BM25 re-ranks, it never widens the candidate set
            scored.append((blended * max(cmax, 0.15), r))   # keep a similarity-like scale for the abstain threshold
    scored.sort(key=lambda x: -x[0])
    return [{"chunk_id": r["id"], "doc_id": r["doc_id"], "doc_version": r["doc_version"], "idx": r["idx"],
             "text": r["text"], "score": round(s, 4), "injection_score": r["injection_score"],
             "quarantined": bool(r["quarantined"])} for s, r in scored[:k]]
