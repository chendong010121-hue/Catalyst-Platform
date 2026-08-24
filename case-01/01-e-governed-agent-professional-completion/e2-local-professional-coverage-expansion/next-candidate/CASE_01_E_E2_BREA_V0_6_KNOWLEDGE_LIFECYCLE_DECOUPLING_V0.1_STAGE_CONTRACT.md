# CASE 01-E / E2 — BREA v0.6 Knowledge Lifecycle Decoupling
## STAGE CONTRACT V0.1

> Baseline: `7417f75a2ee207aa69c4b6f89513c186f28584c3`  
> Frozen predecessor: `case-01.brea @ 0.5-candidate`  
> Target: `case-01.brea @ 0.6-candidate`  
> Trigger: Growth Gate G-01 = `STRUCTURAL_GROWTH_DETECTED`  
> Purpose: decouple Knowledge Revision lifecycle from Agent Candidate lifecycle  
> Platform / Runtime change: FORBIDDEN  
> E2-C: NOT AUTHORIZED  
> Admission / Binding: NOT AUTHORIZED

## 1. Single Stage thesis

Fix only the structural defect already proven by G-01:

```text
Knowledge Revision
must not require mutation of a frozen Agent Candidate.
```

Do not implement Hangzhou professional rules yet.
Do not expand Fact Vocabulary yet.
Do not repair unseen source-format gaps yet.

## 2. Required target relationship

Replace the current implicit ownership:

```text
Agent Candidate
├── fixed historical corpus manifest path
└── candidate-local professional_data.json
```

with an explicit Case-local binding:

```text
BREA Agent Version
        │
        │ binds
        ▼
BREA Knowledge Revision
```

Agent behavior code must not own the mutable knowledge contents.

## 3. Minimal Case-local Knowledge Revision

Create one minimum Case-local BREA Knowledge Revision asset.

Preferred minimum representation: one JSON document plus local raw-source references.

It must contain only what is needed to replace the current coupled assets:

```text
knowledge_revision_id
schema_version
sources[]
  source_id
  file_name / local reference
  sha256
  authority
  title
  version / effective status
standards
  metadata
  aliases
routes
fact_descriptors
```

Raw regulation content remains LOCAL / READ-ONLY / NOT COMMITTED.

Do not create a generic Catalyst Knowledge Platform, registry service, database, or multi-file ontology.

## 4. Explicit Knowledge Binding

v0.6 must receive the selected Knowledge Revision through one explicit Case-local binding mechanism.

Allowed implementation forms include a small runner/config/adapter binding.

The exact mechanism is implementation HOW, but it must satisfy:

```text
Agent source does not hardcode a historical manifest path.
Agent source does not require professional_data.json beside Python modules.
Knowledge Revision selection is not controlled by user question text.
Missing / invalid binding fails closed.
Knowledge Revision identity is observable in execution trace/result.
```

Do not introduce Platform or Runtime responsibility to achieve this.

## 5. Trace / provenance minimum

Every result produced through v0.6 must preserve the existing source evidence/provenance and additionally expose:

```text
knowledge_revision_id
knowledge_revision_sha256
```

so an execution can be reconstructed as:

```text
Agent Version
+
Knowledge Revision
+
Source SHA
+
Evidence Locator
```

## 6. KR-001 baseline

Form the first knowledge revision from the currently accepted v0.5 knowledge only:

```text
GB55037-2022
DBJ33T1021-2023
existing standard metadata / aliases
existing declarative routes
existing fact descriptors
```

KR-001 must preserve existing v0.5 behavior.

Do not add the Hangzhou 2026 regulation to KR-001.

## 7. Candidate behavior preservation

v0.6 must preserve without regression:

```text
v0.5 generic professional path
PC-01..PC-07
five supported professional forms
E1 generalized local query
T-C01 / T-C02 / T-C03
source fidelity / provenance
SEAM-02 ownership
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
Platform-bound compatibility
```

No new Governed Seam or Obligation is authorized.

## 8. What is explicitly NOT part of v0.6

Do NOT in this Candidate:

```text
add Hangzhou professional routes
add road_width / building_height / land_use / Q or other new Domain facts
support new planning formulas
expand source-format parser for Chinese hierarchical numbering unless needed merely to preserve current KR-001 behavior
add BM25 / Dense / embeddings / Vector DB
add LLM / Web / Memory / Multi-Agent
create Platform / Runtime / Enterprise capability
perform E2-C
```

If one of these appears necessary to complete the lifecycle decoupling itself, STOP and report the smallest blocker.

## 9. Minimum checks

Use only the checks needed to prove this Stage:

```text
K-01 v0.6 loads KR-001 through explicit binding
K-02 no historical manifest path is hardcoded in Agent behavior code
K-03 no candidate-local professional_data ownership is required
K-04 missing/invalid Knowledge binding fails closed
K-05 result/trace records Knowledge Revision identity + SHA
K-06 v0.5 professional regression PASS
K-07 E1 + T-C01/T-C02/T-C03 regression PASS
K-08 identity / lineage / fingerprint / protected boundaries PASS
K-09 Platform-bound compatibility PASS
```

Do not add near-duplicate tests.

## 10. Minimal artifact surface

Long-lived output after authorization:

```text
next-candidate/
  knowledge/
    KR-001.json

  candidate/
    brea-v0.6/**

  V0_6_RESULTS.json
  V0_6_CANDIDATE_REVIEW.md
  V0_6_FREEZE_RECORD.json
```

Do not create separate Evidence Index / conformance / repository-integrity reports unless a new independent decision requires them.

## 11. Freeze and next Gate

After successful construction:

```text
v0.6 = FROZEN / NOT ADMITTED / NOT BOUND
KR-001 identity + SHA recorded
Candidate tree SHA recorded
ONE implementation+evidence+freeze commit
ONE push to case-01
STOP
```

After external v0.6 Freeze Review PASS, the next action is NOT E2-C yet.

The next action is:

```text
KR-001 → KR-002
using the already supplied
《杭州市城市规划管理技术规定》

while v0.6 Agent tree remains byte-identical.
```

That follow-up Gate may then expose, separately:

```text
Knowledge Content Growth
Source Format Growth
Professional Semantic Growth
```

Do not pre-fix those future gaps in v0.6.

## 12. Success boundary

A successful v0.6 may claim only:

```text
CASE-LOCAL KNOWLEDGE LIFECYCLE DECOUPLING
PROVEN FOR KR-001

Agent Version != Knowledge Revision
at the binding/lifecycle level
```

It may not yet claim:

```text
Hangzhou source ingestion proven
normal knowledge growth proven
new source format proven
new planning professional coverage proven
Platform-general knowledge capability
E2 complete
```

# VERDICT — READY FOR EXPLICIT v0.6 IMPLEMENTATION AUTHORIZATION
