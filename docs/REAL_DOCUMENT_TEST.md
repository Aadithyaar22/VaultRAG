# Testing VaultRAG on real documents (run 2026-10-17, live LinuxONE instance, real Groq model)

Why: our first tests used synthetic documents we wrote ourselves, which flatters any system. We then downloaded **six real public
documents**, uploaded them to the running app (IBM LinuxONE, s390x) with different role ACLs, and tested every feature as every user
with the real model (`openai/gpt-oss-120b` via Groq). **It found real bugs; all are fixed and covered by regression tests.**

## Documents used (not stored in the repo; `backend/scripts/real_docs/download_real_data.sh` fetches them)
| Role ACL | Document | Format | Size |
|---|---|---|---|
| HR | US Dept of Labor FMLA Fact Sheet #28 (copy hosted by U. Michigan) | PDF | 183 KB |
| HR | University of North Texas policy 05.069 *Leave of Absence without Pay* | PDF | 215 KB |
| Everyone | OSHA 3021 *Workers' Rights* (2011 edition, copy hosted by Vermont DOL) | PDF (custom fonts) | 164 KB |
| Finance | IRS Publication 463 *Travel, Gift, and Car Expenses* | PDF, 296k characters | 1.8 MB |
| Finance | Washington State DES *Travel Policies and Related Issues* | **DOCX with a table** | 17 KB |
| Legal | Apache License 2.0 | TXT | 11 KB |

## Bugs the real documents exposed (and the fixes)
| # | Problem found | Fix |
|---|---|---|
| 1 | **DOCX tables ignored**: the WA document extracted as 36 characters | Read tables, hyperlinks, content controls in order (4,888 chars now) |
| 2 | **Garbled PDF text indexed silently**: OSHA PDF's custom fonts made `pypdf` return gibberish | Text-quality score; fall back to `pdfminer.six`; never index unreadable chunks; reject mostly-unreadable files (422) |
| 3 | **Injection detector over-flagged real prose**: 28–34% of ordinary real-document chunks flagged by the ML classifier at its 0.5 cut-off | Added benign/regulatory training text; thresholds calibrated on the IRS publication and verified on four other documents: 10 of 667 chunks flagged (1.5%), 0 quarantined |
| 4 | Regex rule `system:` matched "Payment System: …" | Rule now requires line start / bracket |
| 5 | **Retrieval missed the answer** in a 558-chunk document (recall@4 = 8/12 on our real questions) | BM25 + similarity hybrid, 6 passages, 140-character chunk overlap so facts split across a boundary stay retrievable → **recall@6 = 12/12** |
| 6 | Correct answers **blocked** when the model's citation format varied (`【4】`, none) | Normalise citation styles; one citation-reminder retry before the gate; still blocked (not guessed) if uncited |
| 7 | Groq rate-limit/5xx errors surfaced as failures with no detail | Retry with back-off, HTTP status recorded; client errors (bad key) fail immediately |
| 8 | Quarantining a whole chunk **threw away legitimate text** next to an injected sentence | Sentence-level removal; only if nothing readable remains is the chunk quarantined |

## Results after the fixes
**Role × question matrix** (6 users × 6 questions, real model; each fact verified against the document text first):
authorized users got the correct, correctly-cited answer **15 / 15** (was 8 / 15 before the fixes); unauthorized attempts released nothing, named
no restricted document and leaked no content **21 / 21**.

**Lifecycle and security scenarios (live)** — all passed:
- Revocation while an answer is cached → cached answer not released; audit shows `permission_changed` + `cache_invalidated`; restoring access gives a fresh answer.
- Explicit per-user deny overrides a role grant (HR user blocked, other HR user unaffected).
- Document replacement → new version cited, old cached answer not served (verified with an edited real license text).
- Role change invalidates the user's cache.
- Authorization outage → every request including cached ones denied (fails closed); recovers.
- Revocation *during* generation (race) → answer discarded, then abstained; trace shows `revocation_detected_before_release`.
- PII on real phone numbers: non-exempt user sees `[REDACTED:phone]`, HR (exempt by policy) sees the number.
- 12 parallel requests from two users: no cross-user leakage; document lists match each user's ACL exactly; restricted passage and nonexistent document are indistinguishable (404).
- Administrator cannot read HR/Finance/Legal content; non-managers get 403 on upload/ACL; no or forged token → 401.
- Upload validation: unsupported type 415, empty 422, garbled 422, over 10 MB 413, invalid role 422. Hash-chain audit verified after ~300 entries.
- Injection inside a policy document: English topic-switch and paraphrased instructions were removed before the model saw them; the legitimate facts (Friday, ten holidays) were still answered; **the German instruction was not detected and did reach the model, which did not obey it**.

## Prompt-injection detection measured on an independent public benchmark
`deepset/prompt-injections` (Apache-2.0): we tuned on its **train** split and real documents only, then evaluated the **test** split once.
| Detector | Test recall (all / English / German) | False positives (56 benign prompts) |
|---|---|---|
| Regex rules only | 15% / 24% / 0% | 0 |
| **Ensemble (regex + ML), as shipped** | **20% / 32% / 0%** | **0** |
Our earlier 16/16 on our own hand-written cases was optimistic — those cases were written by us and the rules adjusted after seeing misses. **The detector is a
supplementary signal; it misses most real-world injections. The protection is architectural** (authorization before the model, evidence framed as untrusted data,
no tools, deterministic release gate), and in the test above the model did not follow the injected text it was shown.

## Other honest limitations
- Document **sensitivity** classifier is unreliable on real documents (department 6/6 correct but confidence only 0.28–0.73; sensitivity often wrong, e.g. the Apache license "restricted"); treat suggestions as hints.
- The anomaly detector scores everyone "high" under heavy automated test traffic (it is rate-based and trained on synthetic baselines).
- Retrieval is lexical (hashing embeddings + BM25), not a neural embedding model; 6 documents and 12 retrieval questions is a small sample.
- Model nondeterminism and Groq rate limits mean results can vary run to run; p95 latency in the run was ~8.8 s (back-off), p50 ~0.7 s.
- The OSHA copy is the 2011 edition; documents were public/government text, not confidential material.

## Reproduce
```bash
cd backend && REAL_DATA_DIR=./real_data bash scripts/real_docs/download_real_data.sh
export REAL_DATA_DIR=./real_data BASE_URL=http://<server>:8000          # server running with a real LLM key
python -I scripts/real_docs/extraction_report.py                         # extraction quality per document
python -I scripts/real_docs/retrieval_recall.py                          # retrieval recall@k
python -I scripts/real_docs/injection_benchmark.py test                  # independent injection benchmark
python scripts/real_docs/e2e_1_access_matrix.py && python scripts/real_docs/e2e_2_lifecycle.py && python scripts/real_docs/e2e_3_versions_deny_injection.py
```
(The end-to-end scripts reset the demo data on the target server and need the demo administrator login.)
