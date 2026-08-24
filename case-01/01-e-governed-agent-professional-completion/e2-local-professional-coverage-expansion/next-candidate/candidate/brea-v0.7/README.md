# BREA — Building Regulation Evidence Agent · v0.7-candidate

`case-01.brea @ 0.7-candidate` is the bounded Source Structure Generalization
Candidate formed from frozen v0.6 behavior. The Agent binds an explicit Case-local
Knowledge Revision; the knowledge contents are not owned by the Agent Candidate.

KR-001 and KR-002 contain source revisions, metadata/SHA, aliases, declarative
routes, and fact descriptors. Raw regulation content remains
external, local, read-only, and uncommitted.

Source-native structural segmentation produces ephemeral Evidence Units with native
locators, page provenance, and structure paths. Retrieval supports clauses, headings,
numbered items, and both decimal and parenthesized table locators without rewriting
source structure.

## Main path

```text
Question
→ Fact Normalization
→ Local Evidence Retrieval
→ G-BASE Evidence Unit
→ Generic Semantic Derivation
→ Ephemeral Semantic View
→ SEAM-02 Applicability
→ Deterministic Verification
→ Evidence-bound Answer / Fail Closed
```

The semantic view is private, ephemeral, and derived from retrieved evidence plus
the local professional fact descriptors. It is not a persisted typed RegulationUnit.
Numeric conclusions preserve source operand/modifier evidence and runtime formula
and result. Table conclusions preserve the source row values used for the answer.

E1 generalized local-query behavior and T-C01/T-C02/T-C03 remain available. No LLM, dense retrieval, embeddings,
vector database, web fallback, new seam, new obligation, or platform/runtime change
is introduced.

Status after the bounded build: `FORMED`, `FROZEN`, `NOT ADMITTED`, `NOT BOUND`.
