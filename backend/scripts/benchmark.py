"""Evaluation harness: VaultRAG vs two baselines on a defined, synthetic test suite.

Conditions (all stated in the output): in-memory SQLite, synthetic seed data, `extractive` offline
"LLM" (deterministic, non-generative -> measures the *pipeline's* authorization behaviour, NOT model
answer quality), hashing embeddings, single process, no network. Baselines share retrieval, chunking,
injection quarantine and PII policy with VaultRAG; they differ ONLY in the authorization controls:
  conventional : no document-level authorization, naive cache
  filtered     : permission-filtered retrieval, naive cache, no final gate
  vaultrag     : filtered + candidate re-verification + revalidated cache + RSEG final gate
Run:  python -m scripts.benchmark [--out ../docs/BENCHMARK.md]
"""
import argparse
import json
import statistics
import time

from app import db, seed
from app.config import get_settings
from app.services import authz, documents, rag

MODES = ["conventional", "filtered", "vaultrag"]

LEGIT = [  # user, question, expected substring
    ("hannah", "What is the Level 5 salary band?", "92,000"),
    ("hannah", "How many weeks of paid parental leave do primary caregivers receive?", "16 weeks"),
    ("hannah", "How long must disciplinary investigations take to complete?", "30 days"),
    ("hannah", "How many roles in the Dallas office may be eliminated?", "40 roles"),
    ("frank", "What is the Q3 marketing budget?", "1.8 million"),
    ("frank", "Which expenses require director approval?", "500 USD"),
    ("leo", "What is the termination notice period for the Acme agreement?", "90 days"),
    ("leo", "What is the litigation reserve for the Northwind dispute?", "750,000"),
    ("alice", "How many days of paid annual leave do employees receive?", "24 days"),
    ("alice", "How many days per week can employees work remotely?", "three days"),
]
# (question, secret, doc key holding the secret)
SECRETS = [
    ("What is the Level 5 salary band?", "92,000", "hr_comp"),
    ("How many weeks of paid parental leave do primary caregivers receive?", "16 weeks", "hr_leave"),
    ("How many roles in the Dallas office may be eliminated?", "40 roles", "restructuring"),
    ("What is the Q3 marketing budget?", "1.8 million", "fin_budget"),
    ("What is the termination notice period for the Acme agreement?", "90 days", "legal_acme"),
    ("What is the litigation reserve for the Northwind dispute?", "750,000", "legal_memo"),
]
ATTACKERS = ["alice", "frank", "leo", "adam", "maya"]


def fresh():
    db.init_db(":memory:")
    authz.set_available(True)
    rag.reset_naive_cache()
    ids = seed.seed_all()
    users = {}
    for uid, uname, _, _ in seed.USERS:
        roles = [r["role"] for r in db.q("SELECT role FROM user_roles WHERE user_id=?", (uid,))]
        users[uname] = {"id": uid, "username": uname, "roles": roles}
    return ids, users


def leaked(res, secret):
    return secret in json.dumps({"a": res["answer"], "c": res["citations"]})


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def run_mode(mode: str) -> dict:
    out = {}
    # 1. unauthorized disclosure (fresh cache per probe)
    ids, users = fresh()
    n = leaks = 0
    for uname in ATTACKERS:
        for q, secret, key in SECRETS:
            if ids[key] in authz.accessible_docs(users[uname]["id"]):
                continue
            n += 1
            leaks += leaked(rag.run(users[uname], q, mode), secret)
    out["unauth_probes"], out["unauth_disclosures"] = n, leaks

    # 2. revocation after caching
    ids, users = fresh()
    cases = [(q, s, k) for q, s, k in SECRETS if k in ("hr_comp", "hr_leave")]
    n = leaks = 0
    lat = []
    for q, secret, key in cases:
        rag.run(users["hannah"], q, mode)  # populate cache
        documents.set_acl(ids[key], allowed_roles=None, denied_users=["u_hannah"], actor_id="u_adam")
        t = time.perf_counter()
        r = rag.run(users["hannah"], q, mode)
        lat.append((time.perf_counter() - t) * 1000)
        n += 1
        leaks += leaked(r, secret)
    out["revoke_cache_probes"], out["revoke_cache_leaks"] = n, leaks
    out["revocation_enforcement_ms_p50"] = round(statistics.median(lat), 2)

    # 3. permission change during generation
    ids, users = fresh()
    n = leaks = 0
    for q, secret, key in cases:
        def revoke(ctx, key=key):
            documents.set_acl(ids[key], allowed_roles=None, denied_users=["u_hannah"], actor_id="u_adam")
        n += 1
        leaks += leaked(rag.run(users["hannah"], q, mode, hooks={"before_gate": revoke}), secret)
        db.conn().execute("DELETE FROM document_user_deny")  # restore for next probe
        db.conn().execute("UPDATE documents SET acl_version=acl_version+1")
    out["race_probes"], out["race_leaks"] = n, leaks

    # 4. legitimate quality / false refusal
    ids, users = fresh()
    ok = refused = 0
    for uname, q, exp in LEGIT:
        r = rag.run(users[uname], q, mode)
        ok += (r["status"] == "answered" and exp in r["answer"])
        refused += (r["status"] != "answered")
    out["legit_total"], out["legit_correct"], out["false_refusals"] = len(LEGIT), ok, refused

    # 5. cache correctness after document replacement
    ids, users = fresh()
    q = "How many weeks of paid parental leave do primary caregivers receive?"
    rag.run(users["hannah"], q, mode)
    documents.ingest(title="HR Parental Leave Policy", sensitivity="confidential", filename="x.txt",
                     data=b"Parental leave: primary caregivers receive 20 weeks of paid parental leave.",
                     allowed_roles=["hr"], actor_id="u_adam", doc_id=ids["hr_leave"])
    r = rag.run(users["hannah"], q, mode)
    out["cache_correct_after_replace"] = "20 weeks" in r["answer"] and "16 weeks" not in r["answer"]

    # 6. latency (cold = cache off, warm = cache hit)
    s = get_settings()
    ids, users = fresh()
    s.cache_enabled = False
    cold = []
    for _ in range(5):
        for uname, qq, _e in LEGIT:
            t = time.perf_counter()
            rag.run(users[uname], qq, mode)
            cold.append((time.perf_counter() - t) * 1000)
    s.cache_enabled = True
    for uname, qq, _e in LEGIT:
        rag.run(users[uname], qq, mode)
    warm = []
    for _ in range(5):
        for uname, qq, _e in LEGIT:
            t = time.perf_counter()
            rag.run(users[uname], qq, mode)
            warm.append((time.perf_counter() - t) * 1000)
    out.update(cold_p50=round(pct(cold, 50), 2), cold_p95=round(pct(cold, 95), 2),
               warm_p50=round(pct(warm, 50), 2), warm_p95=round(pct(warm, 95), 2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../docs/BENCHMARK.md")
    a = ap.parse_args()
    s = get_settings()
    s.llm_provider, s.embedding_provider, s.cache_enabled = "extractive", "hashing", True
    res = {m: run_mode(m) for m in MODES}
    rows = [
        ("Unauthorized disclosures / probes", lambda r: f"{r['unauth_disclosures']} / {r['unauth_probes']}"),
        ("Leaks after revocation (cached) / probes", lambda r: f"{r['revoke_cache_leaks']} / {r['revoke_cache_probes']}"),
        ("Leaks when revoked mid-generation / probes", lambda r: f"{r['race_leaks']} / {r['race_probes']}"),
        ("Revocation-enforcement latency, first post-revoke query (p50 ms)", lambda r: r["revocation_enforcement_ms_p50"]),
        ("Legitimate answers correct / total", lambda r: f"{r['legit_correct']} / {r['legit_total']}"),
        ("False refusals / legitimate queries", lambda r: f"{r['false_refusals']} / {r['legit_total']}"),
        ("Cache correct after document replacement", lambda r: "yes" if r["cache_correct_after_replace"] else "NO (stale)"),
        ("Latency, cold pipeline p50 / p95 (ms)", lambda r: f"{r['cold_p50']} / {r['cold_p95']}"),
        ("Latency, cache-hit p50 / p95 (ms)", lambda r: f"{r['warm_p50']} / {r['warm_p95']}"),
    ]
    md = ["# VaultRAG benchmark (generated by `scripts/benchmark.py`)", "",
          "**Test conditions:** in-memory SQLite; synthetic seed data (9 documents, 6 users); `extractive` "
          "offline model (deterministic, non-generative) so results measure the *authorization pipeline*, not "
          "LLM answer quality; hashing embeddings; single process on one machine; tiny suite "
          f"({len(SECRETS)} secrets x {len(ATTACKERS)} users, {len(LEGIT)} legitimate queries). "
          "Latencies are indicative only. Zero observed leaks in this suite is **not** a proof of zero leakage.",
          "", "| Metric | Conventional RAG | Permission-filtered RAG | VaultRAG (RSEG) |", "|---|---|---|---|"]
    for name, f in rows:
        md.append(f"| {name} | " + " | ".join(str(f(res[m])) for m in MODES) + " |")
    text = "\n".join(md) + "\n"
    print(text)
    open(a.out, "w").write(text)
    json.dump(res, open(a.out.replace(".md", ".json"), "w"), indent=2)


if __name__ == "__main__":
    main()
