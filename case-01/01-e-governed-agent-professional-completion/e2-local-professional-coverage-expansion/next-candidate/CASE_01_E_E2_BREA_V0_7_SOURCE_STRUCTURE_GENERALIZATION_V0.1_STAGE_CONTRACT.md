# CASE 01-E / E2 — BREA v0.7 Source Structure Generalization
## STAGE CONTRACT V0.1

> Baseline branch HEAD: `388d47a21c36efec94fce5b7910094a4c2d8be84`  
> Frozen predecessor: `case-01.brea @ 0.6-candidate`  
> Target: `case-01.brea @ 0.7-candidate`  
> Trigger: KR-002 Growth Gate `G-02 = SOURCE_STRUCTURE_GROWTH_DETECTED`  
> Knowledge for construction proof: `KR-002`  
> Professional Semantic Growth (G-03): OUT OF SCOPE  
> E2-C: NOT AUTHORIZED  
> Admission / Binding: NOT AUTHORIZED

## 1. Single Stage thesis

Repair only the source-structure boundary proven by KR-002 G-02.

The frozen v0.6 retrieval mechanism assumes that useful evidence is represented as `X.Y.Z` clauses and `表N.M...` tables. The Hangzhou source proved that a real regulation may instead use Chinese hierarchical headings, single-level ordinals, and native table labels such as `表（2-3）`.

v0.7 must generalize the evidence-unit abstraction without adding Hangzhou professional meaning.

```text
SOURCE STRUCTURE GROWTH
→ FN-09 PRIVATE HOW EXTENSION
→ source-native Evidence Units
```

No new Governed Seam, Obligation, Platform capability, Runtime responsibility, or professional planning contract is authorized.

---

## 2. Target retrieval relationship

Replace the effective dependency:

```text
Raw Source
→ X.Y.Z clause_index only
→ search_units
→ evidence retrieval
```

with:

```text
Raw Source
→ source-native structural segmentation
→ Evidence Units
→ exact / lexical retrieval
→ verbatim evidence
→ source-native locator
```

The mechanism may normalize an internal lookup key, but must not rewrite the source locator presented as evidence.

---

## 3. Minimum Evidence Unit

Use the smallest internal representation needed for retrieval and traceability. A unit should contain no more than necessary, for example:

```text
unit_id              # internal deterministic identity
kind                 # clause / item / section / table / other bounded structural kind
text                 # source-faithful evidence text
source_locator       # native locator, preserved as written
page                 # when available
structure_path       # only when needed to preserve parent context
```

This is PRIVATE HOW, not a new governed asset schema and not a persisted universal Regulation IR.

Do not create an ontology or general legal-document model.

---

## 4. Minimum observed source structures to support

v0.7 must support the structures already evidenced by the three current local sources, including at least:

```text
existing decimal clause:
  4.3.16
  3.1.3
  5.0.4

Chinese top-level heading:
  一、总则
  六、附则

Chinese parenthesized subsection:
  （一）
  （二）

single-level ordinal item:
  1.
  2.
  3.

parenthesized numeric item where present:
  （1）
  （2）

existing decimal table locator:
  表5.0.4

Hangzhou native table locator:
  表（2-3）
  表（3-2）
```

This is an observed-format contract, not a claim to support every Chinese regulation format.

Generic structure patterns are allowed. Source IDs, regulation titles, test questions, exact Hangzhou rule phrases, or per-source parser branches are not.

---

## 5. Section prose must remain retrievable

The parser must not require every useful rule to have a leaf-level clause number.

For example, source-faithful prose under a section heading such as the effective-date sentence in `六、附则` must be able to become retrievable evidence without inventing a fake `X.Y.Z` locator.

Allowed locator style:

```text
六、附则 / [page N]
```

or another source-faithful equivalent.

Forbidden:

```text
inventing 第6.1.1条
inventing normalized clause numbers presented as source locators
```

---

## 6. Table handling boundary

v0.7 must generalize table caption / locator recognition enough to preserve and retrieve both currently observed styles:

```text
表5.0.4...
表（2-3）...
```

Requirements:

```text
query locator may be normalized internally
native caption is preserved in evidence
native source locator is returned
bounded table region can be retrieved
numeric content must remain source-faithful
```

Do not implement P-01/P-02 planning row-selection semantics in this Stage.

Finding a table and professionally deciding which row applies are separate responsibilities.

---

## 7. Query-path boundary

Generalized retrieval may extend locator extraction and source-unit lookup only as needed for the observed source structures.

Keep the existing deterministic retrieval approach:

```text
exact locator
+
lexical/topic retrieval
+
source/alias resolution
```

Do not add:

```text
LLM
embeddings
Dense retrieval
Vector DB
reranker
Web
planner
```

If source-structure generalization cannot be achieved without one of these, STOP and report the blocker.

---

## 8. KR-002 boundary

Use the already-formed `KR-002` as the knowledge input for the Hangzhou source-structure proof.

Do not add to KR-002:

```text
Hangzhou professional routes
land_use_type
road_width_m
building_height / height-band planning facts
Q semantics
planning applicability rules
new professional test answers
```

KR-002 is evidence input for this Candidate, not a vehicle for solving G-03.

If the local derivative referenced by KR-002 is no longer present, the executor may recreate it locally from the same supplied PDF using the recorded extraction method, provided the resulting bytes match the recorded derivative SHA. If they do not match, STOP; do not mutate KR-002 during this Stage.

Raw PDF and normalized full text remain local and uncommitted.

---

## 9. Required new-source proof

Using `v0.7 + KR-002`, the same five G-02 probes must now be executed through the generalized evidence path:

```text
S-01 implementation/effective date
S-02 wall-height rule: 2.2m
S-03 underground pedestrian connection: 4m width / 2.5m clear height
S-04 表（2-3） residential FAR / building-density source evidence
S-05 explicit 表（2-3） locator / table-structure retrieval
```

For S-01..S-05, success requires as applicable:

```text
correct source resolution
real evidence returned
verbatim/source fidelity
usable native locator
source-backed numeric fidelity
no unsupported numeric fabrication
```

Professional project applicability is NOT required for these five probes.

---

## 10. Regression proof

v0.7 must preserve all already-proven behavior from v0.6/KR-001:

```text
E1 generalized local query
existing X.Y.Z clause resolution
existing 表5.0.4 table resolution
PC-01..PC-07
five professional forms
T-C01 / T-C02 / T-C03
source fidelity / provenance
Knowledge Revision binding + traceability
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
Platform-bound compatibility
```

v0.7 should be able to bind KR-001 and KR-002 through the same Knowledge Binding mechanism.

---

## 11. Anti-hardcode / anti-rewrite gate

The implementation must not contain source-specific behavioral branches such as:

```text
if source == CORPUS-03
if standard == HZ-PLANNING-TECH-2026
if title == 杭州市城市规划管理技术规定
if query contains 围墙 / 地下步行 / 容积率 then special result
```

The parser may contain generic structural grammars for the observed formats.

The source text must not be rewritten into fake decimal clauses or fake decimal table identifiers merely to satisfy old code.

---

## 12. Minimum construction checks

Keep the test surface small:

```text
S-01..S-05 Hangzhou source-structure probes

R-01 legacy X.Y.Z clause regression
R-02 legacy decimal table regression
R-03 E1 generalized query regression
R-04 PC-01..PC-07 / five-form professional regression
R-05 T-C01/T-C02/T-C03
R-06 KR-001 + KR-002 binding/trace regression
R-07 source-native locator fidelity
R-08 anti-hardcode / anti-source-rewrite
R-09 identity / lineage / fingerprint / protected boundaries
R-10 Platform-bound compatibility
```

Do not add near-duplicate tests merely to increase count.

---

## 13. Candidate / repository boundary

Preserve read-only:

```text
v0.1..v0.6
KR-001
KR-002
closed Growth Gate evidence
Platform Core
Runtime / RuntimeAdapter
Enterprise extensions
main
raw source files
```

Form a new Candidate tree only:

```text
candidate/brea-v0.7/**
```

No new planning professional route/fact is authorized.

---

## 14. Minimal artifact surface

After explicit authorization, long-lived output only:

```text
candidate/brea-v0.7/**
V0_7_RESULTS.json
V0_7_CANDIDATE_REVIEW.md
V0_7_FREEZE_RECORD.json
```

Use Git diff / test output / execution trace for supporting checks. No Evidence Index or duplicate conformance package by default.

---

## 15. Freeze / publication

After implementation:

```text
record v0.7 Candidate tree SHA
record implementation fingerprint
freeze v0.7
status = FROZEN / NOT ADMITTED / NOT BOUND
ONE implementation + evidence + freeze commit
ONE push to case-01
STOP
```

Specific E2-C benchmark cases must not be created.

After push:

```text
STOP
→ ChatGPT v0.7 Candidate Freeze External Review
```

---

## 16. Success boundary

A successful v0.7 may claim only:

```text
SOURCE-NATIVE EVIDENCE UNIT GENERALIZATION
CASE-PROVEN ACROSS CURRENT THREE SOURCES

KR-002 GENERALIZED EVIDENCE RETRIEVAL
PROVEN

KNOWLEDGE CONTENT GROWTH WITHOUT
SOURCE-SPECIFIC AGENT BRANCHES
PROVEN FOR THIS CASE
```

It may not claim:

```text
Hangzhou planning applicability supported
P-01/P-02 professionally solved
all Chinese regulations supported
generic PDF ingestion solved
LLM/RAG needed or solved
Platform-general ingestion capability
E2 complete
```

## 17. Next boundary after external PASS

Do not pre-authorize the next implementation.

If v0.7 passes, the already-confirmed G-03 evidence becomes the legitimate input for the next product slice: bounded planning professional semantic coverage, starting from the smallest useful family rather than implementing the whole Hangzhou regulation at once.

# VERDICT — READY FOR EXPLICIT v0.7 IMPLEMENTATION AUTHORIZATION
