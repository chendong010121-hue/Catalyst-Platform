# CASE 01 / E2 — BREA PRODUCT CAPABILITY EVALUATION EXECUTION V0.1

> **Status:** STAGE SPEC
> **Execution Authorization:** **NO**
> **Implementation Authorization:** **NO**
> **Candidate mutation:** **NO**
> **E2-C:** **NOT AUTHORIZED**
> **Admission / Binding:** **NOT AUTHORIZED**
> **Baseline before this Stage:** `8a6505992a784c5e525c2cdd96c84966b434b905`
> **Frozen evaluation target:** `case-01.brea @ 0.9-candidate`
> **Candidate freeze commit:** `c6393d4210708400b492ad9e531002e29fe3635e`
> **Evaluation Contract:** `CASE_01_E2_BREA_PRODUCT_CAPABILITY_EVALUATION_V0.1.md`

---

# 0. Stage thesis

Run evaluation before any further BREA development.

This Stage does not create a second analysis system beside the existing Catalyst understanding/decomposition method.

The governing lifecycle is one system:

```text
UNDERSTAND
→ DECOMPOSE BY RESPONSIBILITY
→ CLASSIFY RESPONSIBILITY / OWNERSHIP
→ ASSETIZE WHERE USEFUL
→ EVALUATE THE SAME RESPONSIBILITIES
→ ATTRIBUTE FAILURE
→ HARVEST / REUSE / REPAIR ONLY IF EVIDENCE REQUIRES IT
```

The objects discovered during understanding and decomposition are the same objects later evaluated.

Therefore:

```text
ANALYSIS MODEL
=
EVALUATION MODEL
=
CAPABILITY / RESPONSIBILITY MODEL
```

They are different operations over the same evidence-backed representation, not separate Platform capabilities.

This Stage is Case-local evidence for that unification. It does NOT authorize a Platform-wide Agent Analysis Service, Eval Service, or Capability Service.

---

# 1. Evaluation question

The Stage answers exactly:

> Is frozen BREA v0.9 sufficiently complete for its currently declared product envelope to enter E2-C independent evaluation, and if not, what is the single next material product gap?

It does NOT ask:

```text
What could an ideal universal regulation Agent eventually do?
```

---

# 2. Frozen declared product envelope

Use the accepted Case 01 product definition as authority:

```text
DOMAIN
Building Regulation / Engineering Construction Standards

WORK CONTEXT
architecture_pre_design

PURPOSE
reliable + applicable + traceable regulation evidence from project context

SAFETY
numeric claims must be supported
applicability must be bounded
uncertainty must be explicit / fail closed
source fidelity and provenance required
minimum enterprise attribution preserved
```

Current Knowledge Revision is `KR-003` with three bound source records and four declarative professional routes.

The Stage must evaluate this real envelope, not penalize BREA for absent features that have not been proven required.

---

# 3. Reuse the existing responsibility model

The Evaluation Contract PR-01..PR-18 is the working responsibility map.

Do NOT create a second set of near-duplicate concepts such as:

```text
analysis_dimensions
assessment_dimensions
audit_capabilities
eval_capabilities
```

If the Stage discovers that one PR is incorrectly scoped or actually combines two independent responsibilities, it may propose a responsibility-map repair in the final report, but must not silently create a parallel ontology.

Existing FN-01..FN-11 / SEAM-01..SEAM-03 / OBL-01..OBL-06 remain evidence anchors and responsibility ownership references.

---

# 4. Execution phases

## Phase A — Evidence projection

Map existing evidence onto PR-01..PR-18 before inventing any new benchmark.

For every PR record:

```text
requirement_status
capability_state
current evidence
coverage
known limitation
value / redundancy state if relevant
confidence
```

Allowed requirement states:

```text
REQUIRED
NOT_REQUIRED_NOW
UNKNOWN
```

Allowed capability states:

```text
PROVEN
PARTIAL
EXISTS_NOT_PROVEN
INTENDED
MISSING
UNKNOWN
NOT_REQUIRED_NOW
```

Do not create a new test for a responsibility already adequately proven unless it is needed as a regression anchor.

## Phase B — Gap-to-benchmark decision

Only PRs that are:

```text
REQUIRED
+
not adequately PROVEN
```

may generate new Capability Boundary / Critical Gate / End-to-End benchmark Cases.

Likely audit candidates that MUST NOT be pre-judged as missing include:

```text
PR-05 jurisdiction / regulatory scope resolution
PR-06 source edition / effective-status selection
PR-11 cross-rule / cross-source composition
PR-13 clarification / missing-fact interaction
PR-18 governed external supplementation
```

The Stage must first prove whether each is required for the current declared product envelope.

## Phase C — Freeze minimum benchmark

Create only enough new Cases to make the E2 readiness decision credible.

Target:

```text
normally 4–10 new Cases
```

This is a target, not a quota.

Each Case requires:

```text
case_id
suite
PR ids tested
public task statement
provided project context
provided regulation context
available source scope
private expected observable outcome
private rubric / deterministic checks
critical-gate conditions
acceptable partial credit if any
forbidden shortcut
failure attribution hints
```

Public task and private rubric must be separated.

## Phase D — Run evaluation

Run:

```text
1. inherited v0.9 deterministic Regression Suite
2. new minimum Capability Boundary Cases
3. new minimum Critical Safety / Fail-Closed Cases
4. small realistic End-to-End Product set
```

BREA v0.9 is currently deterministic. Do NOT add an LLM simply because the Evaluation Contract supports model graders.

Use deterministic graders wherever the result can be checked structurally.

Model judge is permitted only if a qualitative judgment cannot be made credibly otherwise and must be separately identified.

## Phase E — Failure attribution

Every material failure must be attributed to one primary category or explicitly remain unresolved:

```text
AGENT_CAPABILITY_GAP
KNOWLEDGE_COVERAGE_GAP
KNOWLEDGE_QUALITY_GAP
RUNTIME_ADAPTER_GAP
MODEL_PROVIDER_LIMITATION
HARNESS_CAPABILITY_GAP
ENVIRONMENT_FAILURE
EVALUATION_INFRASTRUCTURE_FAILURE
BENCHMARK_DEFECT
GRADER_UNCERTAIN
PRODUCT_SCOPE_NOT_REQUIRED
```

Important:

BREA product execution does not normally include Catalyst development Harness.
Do not blame Harness for a BREA product failure merely because Harness previously helped build BREA.

## Phase F — Human Product / Professional Review

After machine evidence is frozen, present a small representative subset of End-to-End outputs for human review.

Human review must assess:

```text
professional source choice
applicability sense
fact sufficiency
unsafe overclaiming
citation usefulness
clarity of uncertainty / next action
actual usefulness for architecture pre-design
```

Human Professional Review remains `PENDING` until explicitly reviewed; automated PASS must not silently fill it in.

---

# 5. Regression floor

The complete inherited v0.9 regression surface remains mandatory:

```text
python tests/run_all.py
python tests/test_v07_source_structure.py
python tests/test_v08_residential_slice.py
python tests/test_v09_knowledge_identity.py
```

Existing evidence includes:

```text
P-01..P-09
PC-01..PC-07
S-01..S-05
T-C01 / T-C02 / T-C03
legacy clause/table behavior
E1 generalized local query
five professional forms
canonical KR-001 / KR-002 / KR-003 binding
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
source SHA fail-closed
```

Any regression failure is a blocker unless the evaluation infrastructure itself is invalid.

---

# 6. Critical gates

At minimum preserve the Evaluation Contract gates:

```text
GATE-01 unsupported normative numeric claim
GATE-02 fabricated / mismatched evidence
GATE-03 applicability overclaim
GATE-04 fail-closed bypass
GATE-05 source fidelity failure
GATE-06 required attribution loss
```

A high average score cannot compensate for a failed critical gate.

The Stage may propose an additional gate only if current product-scope analysis proves that responsibility is required.

---

# 7. Precision rules for benchmark design

## 7.1 Source-bounded honesty

If a user asks about a regulation/source outside `KR-003`, the benchmark must distinguish:

```text
correct fail-closed / limitation
from
incorrect hallucinated answer
```

It must not score “cannot answer because source is not bound” as an Agent defect if the current declared product envelope permits source-bounded operation.

## 7.2 Jurisdiction

Do not assume full national/local hierarchy resolution is already a required product capability.

Evaluate whether BREA correctly avoids applying Hangzhou-specific rules to clearly non-Hangzhou context and whether the declared product scope requires more than that.

## 7.3 Clarification

Do not assume multi-turn clarification UI is required.

First determine whether structured `insufficient_context` plus explicit missing facts and next action already closes the current product responsibility.

## 7.4 Cross-source reasoning

Do not create an artificial multi-source question merely to force composition.

Only test cross-source composition if a realistic task inside the frozen declared scope genuinely requires it.

## 7.5 External web supplementation

Do not score absence of web access as MISSING by default.

Only classify PR-18 as product-critical if the current declared product promise cannot be credibly fulfilled with explicitly bound local authoritative sources + fail closed.

---

# 8. No Candidate mutation

The frozen v0.9 tree is read-only during this Stage.

Forbidden writes:

```text
candidate/brea-v0.9/**
knowledge/KR-001.json
knowledge/KR-002.json
knowledge/KR-003.json
Runtime
RuntimeAdapter
Platform Standard
platform-harness
main
```

Evaluation scripts / benchmark fixtures / results may be created only inside the later explicitly authorized evaluation workspace path.

No product repair is allowed in the same Stage.

---

# 9. Minimum persistent evaluation surface

When later authorized, keep artifacts minimal under one evaluation directory, for example:

```text
evaluation-v0.1/
  benchmark/
  run_evaluation.py
  results.json
  PRODUCT_CAPABILITY_EVALUATION_REPORT.md
```

Private rubric/gold material may live under `benchmark/private/**`; public tasks under `benchmark/public/**`.

Do not create separate documents for:

```text
Capability Audit
Gap Analysis
Benchmark Analysis
Failure Analysis
Professional Review Summary
```

unless one of them has independent decision value that cannot live in the primary report.

The primary report is the unified understanding/decomposition/evaluation output.

---

# 10. Required primary report

The final report must contain:

```text
frozen target identity
frozen declared product envelope
PR-01..PR-18 map
requirement state per PR
capability state per PR
evidence / coverage / limitations
value / redundancy findings
regression results
new benchmark results
critical-gate results
failure attribution per material failure
evaluation validity review
Human Product Review status
Human Professional Review status
final E2 readiness decision
```

If a gap remains, report exactly one:

```text
NEXT MATERIAL GAP
```

No feature backlog.

---

# 11. Valid final machine-stage conclusions

Before explicit Human Professional Review, machine execution may conclude only:

```text
MACHINE_EVALUATION_SUPPORTS_READY_FOR_HUMAN_REVIEW
PRODUCT_CRITICAL_GAP_REMAINS
EVALUATION_NOT_YET_VALID
```

After Human Product + Professional Review, the integrated Case decision may become:

```text
READY_FOR_E2_C
PRODUCT_CRITICAL_GAP_REMAINS
EVALUATION_NOT_YET_VALID
```

`READY_FOR_E2_C` still requires a later explicit E2-C authorization.

---

# 12. Unified-system implication

This Stage intentionally treats:

```text
understanding evidence
functional decomposition
capability records
test evidence
evaluation evidence
failure attribution
harvest / repair decisions
```

as a single accumulating evidence system around the same responsibilities.

No separate “analysis result” and “evaluation result” should drift into conflicting capability identities.

A capability/responsibility discovered in Understanding must be evaluated under that same identity or explicitly revised with lineage.

A capability found during Evaluation becomes new understanding evidence for future decomposition / harvesting.

Thus the loop is:

```text
UNDERSTAND
↔ DECOMPOSE
↔ EVALUATE
↔ LEARN
→ only then CHANGE
```

This is a Case-local method principle until repeated evidence justifies broader promotion.

---

# 13. STOP

```text
STAGE SPEC = FORMED
BENCHMARK = NOT YET FROZEN
EVALUATION EXECUTION = NOT AUTHORIZED
BREA v0.9 MUTATION = NO
E2-C = NO
ADMISSION / BINDING = NO
```
