# BREA — Building Regulation Evidence Agent · v0.10-candidate

`case-01.brea @ 0.10-candidate` is a targeted Candidate N+1 from frozen
`case-01.brea @ 0.9-candidate`. It repairs generic professional-intent routing,
declarative route resolution, and existing source-native evidence binding without
changing Knowledge meaning.
The Agent binds an explicit Case-local Knowledge Revision; the knowledge contents are not
owned by the Agent Candidate.

KR-003 is unchanged. Its canonical Knowledge Revision identity is stable across
serialization-only differences and machine-local `sources[].local_reference` relocation;
knowledge-bearing changes still change the identity, and source-content SHA verification
remains independent.

KR-003 inherits the KR-002 source revisions, metadata/SHA, aliases, declarative
routes, and fact descriptors and adds only the bounded table route and three
authorized facts. Raw regulation content remains
external, local, read-only, and uncommitted.

Source-native structural segmentation produces ephemeral Evidence Units with native
locators, page provenance, and structure paths. The bounded professional route uses
a declarative numeric-banded table selector; values are extracted from the selected
source row and remain bound to verbatim table evidence.

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

Status after the bounded build: `CANDIDATE N+1`, `NOT ADMITTED`, `NOT BOUND`.
