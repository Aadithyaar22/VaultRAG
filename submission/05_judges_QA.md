# 05 · Questions judges may ask — and honest answers

Keep answers short and true. Where we have a weakness, say it first.

**1. How is this different from normal role-based access in a vector database?**
Filtering at search time is not enough: a saved answer, or an answer still being written, can outlive a permission change. We attach every answer to the exact document and permission versions it used and re-check them at release time. The database — not the vector store’s filter — decides.

**2. Is it novel?**
We did not do a prior-art review, so we do not claim novelty. We built and tested a specific combination of known ideas — permission-first retrieval, versioned evidence, release-time re-validation, fail-closed behaviour — and measured it.

**3. What stops a poisoned document from hijacking the AI?**
Mainly the design: the AI has no tools, sees only documents the user may read, treats them as data, and cannot read other documents anyway. On top of that we remove attack-like sentences. The detector itself is weak (about 20% on a public benchmark, 0% for German) — we say so.

**4. Does any data leave the server?**
Yes. The passages a user is allowed to read go to the Groq AI service to write the answer. Passages the user may not read never do. A model on the server (IBM Granite) is the planned fix and the code already supports switching the provider.

**5. How do you use IBM Z?**
The app, the 42 tests, and our ML models run on an IBM LinuxONE z17 (s390x). We completed IBM’s Jupyter AI/ML lab there. The Z AI accelerator and hardware encryption are planned, not used.

**6. Quantum-safe?**
Not implemented. It is on the roadmap.

**7. What if the AI makes things up?**
It must cite numbered evidence; answers without a valid citation are blocked; if the evidence does not answer, it must say so and we show “nothing I may share”. We cannot guarantee the wording is always right.

**8. What if the permission check fails or is down?**
The answer is blocked — even saved ones. There is a demo button and a test for this.

**9. How did you test it?**
42 automated tests; a benchmark against two baselines; a live test with six real public documents across six roles using the real model; an independent public injection benchmark. All reports, including the failures we found, are in the repository.

**10. What did the real documents teach you?**
They exposed eight bugs our own test files hid: DOCX tables unread, garbled PDF fonts, over-flagging of normal text, weak retrieval, citation-format blocking, rate-limit handling, and over-quarantining. All fixed with tests. Authorized answers went from 8/15 correct to 15/15.

**11. Will it scale?**
Not as built: one server and one SQLite file. The permission logic does not depend on that; storage would move to a replicated database and a separate authorization service.

**12. Why does the administrator not see everything?**
Managing documents and reading them are different powers. Separating them reduces insider risk. An admin can change who may read a file but cannot read it unless the file’s list names that role.

**13. Why SQLite and plain-Python search?**
They install on s390x with no native-library surprises, and they are enough for a prototype. A real deployment would use a replicated database and an embeddings model.

**14. What are the biggest weaknesses?**
(1) The injection detector is weak. (2) Allowed text goes to an outside AI service. (3) Quantum-safe security and the Z accelerator are not used. (4) One node, no SSO/MFA, demo accounts. (5) Small tests on public documents, not confidential data.

**15. Where is the code and how do we run it?**
https://github.com/Aadithyaar22/VaultRAG — README has the quick start; `docs/PROJECT_GUIDE.pdf` explains everything; the live demo is at http://148.100.99.19:8000.
