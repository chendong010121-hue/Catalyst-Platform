# CASE 01 / E2 — BREA PRODUCT CAPABILITY EVALUATION V0.1

> **Status:** EVALUATION CONTRACT / AUDIT DESIGN
> **Execution Authorization:** **NO**
> **Implementation Authorization:** **NO**
> **Admission / Binding:** **NO**
> **E2-C:** **NOT YET AUTHORIZED**
> **Case branch baseline before this contract:** `5cb440d13ae09a2a33dcc70f59c046aaa88b62b0`
> **Frozen Candidate under evaluation:** `case-01.brea @ 0.9-candidate`
> **Candidate freeze commit:** `c6393d4210708400b492ad9e531002e29fe3635e`
> **Candidate tree SHA256:** `d68bd70cc8edd9900ff385f1cdc5a31f3b6f48b2003a442ccdb3c458c6af9eb0`
> **Knowledge Revision:** `KR-003`
> **Knowledge Revision canonical SHA256:** `4049f7f00e709fd0d97fb30df2a5f59e3073448ad06ad4afa471babbe45a21d2`
> **Purpose:** determine, with evidence and explicit failure attribution, whether the current declared BREA product scope is sufficiently complete to enter independent E2-C evaluation, and identify exactly one product-critical next gap if it is not.

---

# 0. Executive decision

The next Case 01 step is evaluation before further product development.

The question is NOT:

```text
What features could an ideal building-regulation Agent eventually have?
```

The question is:

```text
For the product BREA currently declares itself to be,
what responsibilities are required,
which are actually proven,
where is the evidence boundary,
and what — if anything — still blocks a credible product loop?
```

The evaluation must be accurate enough to distinguish:

```text
AGENT CAPABILITY GAP
KNOWLEDGE GAP
RUNTIME / ADAPTER GAP
MODEL / PROVIDER LIMITATION
HARNESS CAPABILITY GAP
ENVIRONMENT FAILURE
EVALUATION INFRASTRUCTURE FAILURE
BENCHMARK DEFECT
GRADER UNCERTAINTY
PRODUCT-SCOPE NON-REQUIREMENT
```

A failed task without credible attribution is not yet a useful Catalyst growth signal.

Therefore:

```text
SCORE
!=
ROOT CAUSE

PASS
!=
PRODUCT COMPLETE

FAIL
!=
AGENT DEFECT
```

This Evaluation Contract intentionally combines:

```text
Product Capability Completeness Audit
+
Capability / Regression Evaluation
+
Critical Professional Gates
+
Failure Attribution
+
Human Professional Review
```

into one Case-local evaluation method.

No Catalyst-wide Eval Platform is authorized.

---

# 1. Evaluation authority and evidence sources

## 1.1 Catalyst-owned product authority

BREA's accepted professional purpose remains:

> Use project context to provide reliable, applicable, traceable building-regulation evidence for architectural / preliminary design work, and explicitly return uncertainty or fail closed when reliable evidence is unavailable.

The accepted governed obligations remain:

```text
OBL-01 Verbatim evidence traceability
OBL-02 Applicability determination
OBL-03 Numeric safety — zero unsupported normative numeric claims
OBL-04 Fail-closed uncertainty
OBL-05 Source fidelity / provenance
OBL-06 Minimum enterprise attribution
```

The accepted functional decomposition remains FN-01..FN-11 with governed seams SEAM-01..SEAM-03.

These Catalyst Case definitions determine what BREA means.

## 1.2 Current Candidate evidence

v0.9 is frozen / evidence-backed / not admitted / not bound.

Current regression evidence proves the existing bounded implementation, including:

```text
P-01..P-09
PC-01..PC-07
S-01..S-05
T-C01 / T-C02 / T-C03
legacy clause/table behavior
E1 generalized local query
five professional forms
canonical KR-001 / KR-002 / KR-003 binding
FN-01..FN-11 identity preservation
SEAM-01..SEAM-03
OBL-01..OBL-06
Platform-bound compatibility
anti-hardcode checks
source-SHA fail-closed behavior
```

These are evidence anchors, not automatic proof of full product completeness.

## 1.3 External evaluation mechanism donors

External systems and public evaluation methods may inform HOW this Case evaluates the Agent, but they do not define Catalyst product authority.

Relevant mechanism lessons include:

```text
PenguinHarness
→ capability contract before benchmark
→ case-visible task separated from private rubric
→ isolated evaluation
→ score + trace linked to a fixed Candidate
→ frozen benchmark for N+1 comparison

Anthropic agent eval practice
→ capability eval != regression eval
→ code-based + model-based + human graders
→ repeated trials / reliability
→ inspect transcripts when failures occur

LangSmith trajectory evaluation
→ evaluate observable trajectory / tool responsibility path
→ strict / unordered / subset / superset matching where appropriate

DeepSeek Harness testing
→ no-key proof != real-provider proof
→ verify the world, not the Agent's self-report
→ untouched files / external state should be independently verified

OpenAI Agents SDK testing / tracing
→ deterministic provider-neutral tests for owned orchestration
→ real integration tests for externally owned model/provider behavior
→ trace observable workflow events rather than relying only on final output
```

These are reference mechanisms only.

---

# 2. The declared product envelope must be frozen before scoring

BREA must not be evaluated against an imaginary universal regulatory super-agent.

The current declared scope is:

```text
DOMAIN
Building Regulation / Engineering Construction Standards

WORK CONTEXT
architecture_pre_design

PRIMARY USER VALUE
reliable + applicable + traceable building-regulation evidence

INPUT BASIS
question
+ project context
+ regulation context
+ enterprise attribution

CURRENT KNOWLEDGE MODEL
explicit Case-local Knowledge Revision
+ local read-only source corpus

CURRENT PROFESSIONAL SAFETY
applicability determination
+ evidence binding
+ numeric safety
+ uncertainty / fail closed

CURRENT OUTPUT INTENT
evidence-backed conclusion
+ evidence / locator / provenance
+ explicit uncertainty where evidence is insufficient
```

The current v0.9 README explicitly does NOT introduce:

```text
LLM dependency
dense retrieval
embeddings
vector database
web fallback
new governed seam
new obligation
```

Therefore those capabilities must NOT be pre-labeled as missing merely because mature Agents elsewhere may have them.

They enter this Audit first as:

```text
AUDIT CANDIDATE
```

and may ultimately be classified:

```text
REQUIRED
PARTIAL
NOT_REQUIRED_NOW
UNKNOWN
```

The evaluation must prove necessity before converting a possible future feature into a current product-critical gap.

---

# 3. Evaluation target identity

Every evaluation run must identify exactly what system is being evaluated.

Minimum target identity:

```text
agent_id
candidate_version
candidate_tree_sha256
implementation_fingerprint
knowledge_revision_id
knowledge_revision_sha256
source identities + source SHA values
runtime / adapter identity if the run uses them
provider / model identity if the run uses them
benchmark revision
grader revision
environment identity sufficient for reproducibility
```

For the initial v0.9 product evaluation:

```text
Agent = case-01.brea@0.9-candidate
Knowledge = KR-003
Candidate tree SHA = d68bd70...
Implementation fingerprint = cf5ede8...
```

A result without frozen target identity is not valid evidence for Candidate comparison.

---

# 4. Evaluation object separation

The evaluation must distinguish at least five objects.

## 4.1 Product responsibility

What the user needs the Agent to do.

Examples:

```text
identify relevant regulation evidence
judge applicability
avoid unsupported normative numbers
explain uncertainty
```

## 4.2 Agent implementation

How the current BREA Candidate performs those responsibilities.

## 4.3 Knowledge / source state

What authoritative material is actually available to the Agent.

## 4.4 Execution infrastructure

Runtime / Adapter / environment / provider path used to execute the Agent.

## 4.5 Evaluation infrastructure

Benchmark statement, hidden rubric, evaluator code, model judge, human rubric and run orchestration.

A defect in one object must not be silently scored as a defect in another.

---

# 5. Product responsibility map — audit dimensions

The Audit must decompose BREA by user responsibility, not by repository files.

The following is the initial responsibility map to evaluate. It is NOT a declaration that every item is currently required or missing.

| ID | Product responsibility | Existing Catalyst anchor | Audit question |
|---|---|---|---|
| PR-01 | Question / intent and context intake | FN-01 | Does BREA correctly identify what the user is asking within its declared scope? |
| PR-02 | Project fact normalization | FN-02 / SEAM-01 | Can relevant project facts be normalized without inventing values? |
| PR-03 | Project-fact completeness judgment | FN-02 / FN-06 | Does the Agent know when facts are insufficient for a professional conclusion? |
| PR-04 | Regulation applicability resolution | FN-03 / SEAM-02 | Does the selected evidence actually apply to the supplied project context? |
| PR-05 | Jurisdiction / regulatory scope resolution | FN-03 candidate responsibility | Is current jurisdiction handling sufficient for declared product scope, and if not, what exact case breaks it? |
| PR-06 | Source / edition / effective-status selection | FN-03 / FN-09 candidate responsibility | Does the Agent select the correct available source/version when alternatives exist? |
| PR-07 | Local corpus retrieval | FN-04 / FN-09 | Can relevant evidence be found in the currently bound local corpus without hardcoded answer leakage? |
| PR-08 | Clause / table / note / native-structure retrieval | FN-04 / SEAM-03 | Can source-native evidence units and locators be correctly recovered? |
| PR-09 | Applicability conditions / modifiers / exceptions | FN-03 / FN-05 | Are conditions and exceptions correctly bound to project facts and evidence? |
| PR-10 | Numeric / banded / derived-rule safety | FN-05 / OBL-03 | Are all normative numeric conclusions directly or deterministically evidence-backed? |
| PR-11 | Cross-rule / cross-source composition | candidate product responsibility | Is composition required for the current declared product envelope, and what level is already proven? |
| PR-12 | Evidence sufficiency decision | FN-05 / FN-06 | Does BREA distinguish enough evidence from insufficient evidence? |
| PR-13 | Clarification / missing-fact interaction | FN-01 / FN-06 candidate responsibility | When a result requires missing project facts, is current fail-closed behavior enough, or is an explicit clarification turn product-critical? |
| PR-14 | Professional conclusion composition | FN-07 | Is the conclusion accurate, bounded, useful and non-overclaiming? |
| PR-15 | Citation / locator / provenance | FN-08 / SEAM-03 / OBL-01 / OBL-05 | Can every material professional claim be traced to the right source and locator? |
| PR-16 | Uncertainty / next-action communication | FN-06 / FN-07 | Does the user understand what is unknown and what would be needed next? |
| PR-17 | Enterprise attribution | OBL-06 | Is minimum organization/user/project attribution preserved correctly? |
| PR-18 | Governed external supplementation | currently absent by design | Is web/external supplementation actually required for the current product envelope, or NOT_REQUIRED_NOW? |

No PR item receives a final status merely because a similarly named field/module exists.

---

# 6. Supporting integrity guarantees — separate from product capability

Some capabilities are necessary for governed trust but are not direct user-facing product responsibilities.

Evaluate them separately so they do not inflate apparent product completeness.

```text
SG-01 Candidate identity / lineage
SG-02 Knowledge Revision identity
SG-03 source SHA integrity
SG-04 deterministic regression reproducibility
SG-05 protected-boundary preservation
SG-06 Platform / Runtime compatibility where explicitly required
SG-07 trace / artifact provenance sufficient for audit
```

v0.9 already has strong evidence for several SG items.

A strong SG profile does not substitute for weak user-facing product capability.

---

# 7. Capability-state vocabulary

Each Product Responsibility receives one current-state classification.

```text
PROVEN
```

Meaning:

```text
clear responsibility contract
+ adequate direct evidence
+ coverage sufficient for current declared scope
```

```text
PARTIAL
```

Meaning:

```text
real capability exists
but evidence shows product-relevant coverage gaps
```

```text
EXISTS_NOT_PROVEN
```

Meaning:

```text
code / mechanism appears present
but current evidence cannot justify a capability claim
```

```text
INTENDED
```

Meaning:

```text
accepted product definition implies the responsibility
but no working capability has yet been formed
```

```text
MISSING
```

Meaning:

```text
current declared product loop genuinely requires the responsibility
and it is absent
```

```text
UNKNOWN
```

Meaning:

```text
available evidence is insufficient to determine requirement or capability state
```

```text
NOT_REQUIRED_NOW
```

Meaning:

```text
possible mature-product capability
but not required to close the current declared BREA product loop
```

The difference between `MISSING` and `NOT_REQUIRED_NOW` is a core anti-feature-wishlist control.

---

# 8. Value / redundancy review

Completeness Audit must also review whether existing responsibilities or mechanisms remain valuable.

Each meaningful current mechanism may receive one value classification:

```text
REQUIRED
USEFUL_IMPLEMENTATION_SPECIFIC
REDUNDANT
HISTORICAL
PREMATURE
UNKNOWN_VALUE
```

Required questions:

```text
What real user / governance problem does this solve?
What evidence would be lost if it were removed?
Is this product responsibility or implementation HOW?
Is it duplicated elsewhere?
Has another mechanism replaced it?
Is it historical evidence that should remain but not stay active?
```

The Audit is allowed to discover that Catalyst should carry LESS, not only MORE.

---

# 9. Evaluation suite separation

BREA evaluation must not collapse all tasks into one undifferentiated benchmark.

## 9.1 REGRESSION SUITE

Question:

```text
Can BREA still do what it already proved?
```

Expected pass rate:

```text
near 100%
```

Initial anchors include existing deterministic v0.9 regressions.

A regression failure is a release blocker unless the previous capability is explicitly deprecated under separate authority.

## 9.2 CAPABILITY BOUNDARY SUITE

Question:

```text
Where does the current BREA capability envelope actually end?
```

Tasks should include realistic difficulty near current boundaries.

This suite is allowed to have failures. Its purpose is discovery, not cosmetic green status.

A saturated 100% capability suite should later be expanded or graduated into Regression.

## 9.3 CRITICAL SAFETY / FAIL-CLOSED SUITE

Question:

```text
Does BREA refuse unsafe professional conclusions when required evidence / facts / applicability are insufficient?
```

This suite contains hard gates and adversarial boundary cases.

## 9.4 END-TO-END PRODUCT SUITE

Question:

```text
Can an architectural / preliminary-design user complete a meaningful real task through BREA's current product interface?
```

This suite evaluates the combined user loop, not isolated functions.

## 9.5 HUMAN PROFESSIONAL SUITE

Question:

```text
Would a qualified professional accept the Agent's evidence path, scope judgment and conclusion as genuinely usable within the declared product envelope?
```

This suite cannot be replaced by automated scoring alone.

---

# 10. Benchmark case contract

Every non-regression evaluation Case must have a frozen Case Contract before execution.

Minimum Case fields:

```text
case_id
suite
product_responsibilities_tested
public_task_statement
provided_project_context
provided_regulation_context
available_source_scope
expected_observable_outcome
hidden_rubric
critical_gate_conditions
acceptable_partial_credit
forbidden_shortcuts
required_evidence_properties
trajectory_constraints_if_any
failure_attribution_hints
```

The Agent sees the task and normal user context.

The Agent must NOT see the hidden rubric / gold rationale / grader prompt.

Benchmark revision must be frozen and recorded with the evaluation result.

Do not rewrite a failed benchmark after seeing the Agent answer without incrementing Benchmark Revision.

---

# 11. Grader strategy

No single grader is trusted for every dimension.

## 11.1 Code-based deterministic graders

Prefer for:

```text
status values
exact evidence source identity
source SHA / revision identity
locator presence / correctness
required numeric operands
forbidden unsupported numeric claims
fail-closed status
required / forbidden observable actions
regression behavior
external file / world-state verification where applicable
```

For facts that can be deterministically checked, deterministic grading has priority over model judgment.

## 11.2 Model-based graders

May be used for bounded qualitative dimensions such as:

```text
answer completeness
scope discipline
clarity
professional explanation quality
whether uncertainty is communicated coherently
observable trajectory appropriateness when deterministic matching is insufficient
```

Rules:

```text
model judge is not sole authority for professional correctness
judge model/version/prompt must be recorded
judge output must include rationale + confidence
judge must be calibrated against human-reviewed examples
```

## 11.3 Human professional grader

Required for product completion judgment.

Human review focuses on questions such as:

```text
Did the Agent select the right regulatory source for the task?
Does the applicability judgment make professional sense?
Was any more authoritative / more specific source obviously omitted within the provided source scope?
Are project facts sufficient?
Did the Agent overclaim when facts/evidence were missing?
Are citations and locators professionally usable?
Would an architect actually rely on this answer for the stated pre-design task?
```

Human judgment does NOT automatically rewrite deterministic evidence. Disagreement becomes an explicit review item.

---

# 12. Critical gates — no total score can compensate

BREA must not be admitted based on a high weighted average if a core professional safety gate fails.

The initial critical gates are derived from existing obligations.

```text
GATE-01 UNSUPPORTED_NORMATIVE_NUMERIC_CLAIM
Any accepted professional conclusion contains a material normative number not supported by bound evidence / deterministic derivation.
→ FAIL

GATE-02 EVIDENCE_FABRICATION_OR_MISMATCH
Claimed source / locator / evidence content is fabricated or does not support the conclusion.
→ FAIL

GATE-03 APPLICABILITY_OVERCLAIM
Agent returns an accepted project-specific professional conclusion when the supplied facts/evidence do not justify applicability.
→ FAIL

GATE-04 FAIL_CLOSED_BYPASS
Critical project facts or reliable evidence are missing, but the Agent guesses a professional answer instead of expressing uncertainty / refusing.
→ FAIL

GATE-05 SOURCE_FIDELITY_FAILURE
Agent materially changes authoritative source content while presenting it as evidence.
→ FAIL

GATE-06 ATTRIBUTION_LOSS
Required minimum enterprise attribution is silently lost on an accepted result.
→ FAIL where OBL-06 applies
```

Future Audit may identify an additional critical gate such as jurisdiction/edition authority, but it must first prove that the responsibility belongs inside current declared product scope.

A critical-gate failure cannot be offset by good writing, speed or high scores elsewhere.

---

# 13. Evaluation Profile — no single admission score

The primary output is a profile, not one number.

Example dimensions:

```text
Declared Product Scope Coverage
Question / Context Handling
Project Fact Completeness
Applicability
Retrieval
Source-native Evidence Recovery
Numeric / Conditional Reasoning
Evidence Grounding
Fail-Closed Safety
Conclusion Usefulness
Citation / Provenance
Reliability
Regression Integrity
Human Professional Acceptance
```

Some dimensions may use scores for comparison / optimization.

Admission decisions remain gate- and evidence-based.

```text
TOTAL SCORE = 92
```

must never imply:

```text
ADMISSION READY
```

if a critical gate fails.

---

# 14. Reliability / repeated trials

A one-off success does not always prove reliable Agent capability.

Where execution is non-deterministic because of model/provider behavior, the evaluation should report at minimum:

```text
pass@1
per-case success rate
pass^k or equivalent consistency metric for repeated trials
```

For professional customer-facing behavior, consistency is more important than “one lucky success in k attempts.”

Initial policy:

```text
deterministic BREA paths
→ one deterministic run + reproducibility check may be sufficient

model-dependent / non-deterministic paths
→ repeat critical cases, normally k >= 3 unless cost/evidence justifies another value
```

Do not multiply deterministic runs merely to create impressive sample counts.

---

# 15. Observable trajectory evaluation

Catalyst must not require private chain-of-thought as evaluation evidence.

Trajectory evaluation means observable responsibility / tool / evidence behavior.

Possible constraints:

```text
REQUIRED ACTION
critical evidence source must be consulted / bound

FORBIDDEN ACTION
unapproved source / tool / write must not be used

SUBSET-LIKE CONSTRAINT
Agent may use only the allowed action/tool set

SUPERSET-LIKE CONSTRAINT
Agent must perform at least the minimum required observable actions

STRICT ORDER
use only where professional or safety order is itself required
```

Do not overfit a single exact path when multiple valid professional paths exist.

Trajectory efficiency may be measured, but correctness and safety dominate.

---

# 16. Verify the world, not the self-report

Evaluation evidence must independently inspect observable results wherever possible.

Examples:

```text
Agent says source was cited
→ evaluator inspects evidence_items / locator / source identity

Agent says uncertainty exists
→ evaluator inspects structured result status / uncertainty fields

Agent says no unsupported number was used
→ evaluator checks conclusion against evidence operands / allowed derivation

Harness says one file changed
→ repository diff independently verifies it
```

Agent/Harness narrative claims are not sufficient evidence by themselves.

---

# 17. Failure attribution taxonomy

Every failed evaluation Case must receive a primary attribution or remain explicitly unresolved.

## 17.1 Product / Agent-side categories

```text
AGENT_CAPABILITY_GAP
The required responsibility belongs to current product scope and the Agent implementation fails it.

KNOWLEDGE_COVERAGE_GAP
The task is in current product scope, but required authoritative knowledge/source content is absent from the bound Knowledge Revision/source set.

KNOWLEDGE_QUALITY_GAP
The required source exists but its parsed/structured/metadata form is insufficient or wrong.

RUNTIME_ADAPTER_GAP
Agent logic is adequate but the accepted execution path prevents correct execution.

MODEL_PROVIDER_LIMITATION
Failure is attributable to non-deterministic/model/provider behavior rather than the deterministic Agent responsibility itself.
```

## 17.2 Harness category

```text
HARNESS_CAPABILITY_GAP
```

Use ONLY when the evaluation target includes the Catalyst development Harness or when a required governed development task fails because of Harness responsibility.

Important:

```text
BREA product execution
normally does NOT include Catalyst development Harness
```

Therefore a BREA user-task failure must not be assigned to Harness merely because Harness helped build BREA.

## 17.3 Environment / evaluation categories

```text
ENVIRONMENT_FAILURE
Filesystem / executable / credential / network / runtime environment failure outside target capability.

EVALUATION_INFRASTRUCTURE_FAILURE
Runner / trace binding / evaluator implementation / case isolation failure.

BENCHMARK_DEFECT
Task statement, expected outcome, hidden rubric or supplied context/source scope is invalid or ambiguous.

GRADER_UNCERTAIN
Graders disagree or evidence cannot support a fair judgment.

PRODUCT_SCOPE_NOT_REQUIRED
The observed missing capability is not required to close the current declared product envelope.
```

A Benchmark or Evaluation Infrastructure failure is NOT scored as Agent failure.

---

# 18. Attribution record

Each failed Case should record:

```text
case_id
observed_failure
primary_attribution
contributing_factors
attribution_confidence
supporting_trace_or_evidence
counterfactual_check
```

Counterfactual examples:

```text
If the authoritative source is manually supplied, does the Agent then succeed?
→ helps separate Knowledge Coverage from Agent reasoning.

If the same Agent logic is executed without Runtime Adapter, does behavior change?
→ helps separate Agent from Runtime.

If deterministic scripted model output is used, does orchestration work?
→ helps separate Harness/Runtime plumbing from model behavior.
```

Do not perform unlimited diagnostic experiments. Use the smallest counterfactual that can materially distinguish causes.

---

# 19. Agent Evaluation vs Harness Evaluation

Catalyst may reuse one evaluation philosophy across Agents and Harnesses, but the evaluation suites are different.

## BREA Agent Product Evaluation

Primary concerns:

```text
professional task success
source/evidence correctness
applicability
numeric safety
fail-closed behavior
product usefulness
provenance
reliability
```

## Catalyst Harness Evaluation

Primary concerns:

```text
authorized development-task completion
Workspace boundary
read/write/tool boundary
ExecutionPolicy
ApprovalPolicy
credential/provider separation
tool-environment sanitization
trace completeness
repair/retry behavior
failure classification
reproducibility
real Case execution ability
```

The Harness Trial 01 evidence already proves one bounded real Case task.

This Evaluation Contract does NOT reopen Harness feature development.

If future BREA/product work exposes a genuine Harness blocker, that failure becomes evidence for a separate Harness-targeted evaluation/repair Stage.

---

# 20. Human Professional Acceptance Gate

Machine evaluation prepares the evidence.

It does not alone declare a high-professional-risk Agent product complete.

The final product review path is:

```text
MACHINE CAPABILITY AUDIT
        ↓
EVIDENCE-BACKED CAPABILITY MAP
        ↓
BENCHMARK / REGRESSION RESULTS
        ↓
FAILURE ATTRIBUTION
        ↓
HUMAN PRODUCT REVIEW
        ↓
HUMAN PROFESSIONAL REVIEW
        ↓
PRODUCT COMPLETENESS JUDGMENT
```

The human review should use realistic architecture/pre-design scenarios rather than only unit-test phrasing.

Possible scenario types to consider during benchmark design — not automatically all required:

```text
known-source clause lookup
known-source table lookup
project-specific applicability
missing project fact
wrong land-use / out-of-scope case
multiple plausible regulation sources
version / effective-status conflict
cross-rule combination
source absent from current local Knowledge
possible need for external source supplementation
```

Which scenarios enter the current required suite must be decided from the declared product envelope.

---

# 21. Product completeness decision rule

The final Evaluation may produce only one of three top-level conclusions.

## 21.1 READY_FOR_E2_C

Requires:

```text
Declared product responsibilities sufficiently complete
+
all critical gates PASS
+
Regression Suite PASS
+
Capability gaps remaining are enhancement / NOT_REQUIRED_NOW rather than product-critical
+
Evaluation itself judged valid
+
Human Product Review PASS
+
Human Professional Review PASS
```

This authorizes consideration of E2-C only through a separate explicit authorization.

It does NOT itself admit/bind BREA.

## 21.2 PRODUCT_CRITICAL_GAP_REMAINS

Requires the Audit to identify:

```text
exact responsibility
why it is required for current product scope
evidence that current implementation is insufficient
primary failure attribution
minimum proof needed to close it
```

Then select exactly one:

```text
NEXT MATERIAL GAP
```

Do NOT automatically produce a full implementation backlog.

## 21.3 EVALUATION_NOT_YET_VALID

Use when:

```text
Benchmark defect
Evaluation infrastructure failure
Grader disagreement too large
Product scope remains too ambiguous to score fairly
```

In this state, do not modify BREA merely to satisfy an invalid evaluation.

---

# 22. Minimum first execution surface

The first real evaluation should remain small enough to inspect manually.

Do NOT begin with 100+ benchmark tasks.

Minimum V0.1 execution should combine:

```text
A. existing v0.9 Regression Suite
   → reuse current deterministic regression evidence / rerun where required

B. a small frozen Capability Boundary set
   → selected to probe responsibility edges not already proven

C. a small Critical Gate / Fail-Closed set
   → designed around OBL-01..OBL-06 and current declared scope

D. a small Human Professional end-to-end set
   → realistic architecture/pre-design questions
```

The exact number of new Cases is not fixed by this Contract.

Benchmark design must stop when there is enough coverage to make the E2 decision credible; task count is not a maturity metric.

---

# 23. Required Evaluation output

The completed Evaluation should produce one primary report containing:

```text
1. Frozen evaluation target identity
2. Declared product envelope
3. Product Responsibility Map PR-01..PR-18
4. Status per responsibility
5. Evidence reference per responsibility
6. Coverage / limitations
7. Value / redundancy classification where relevant
8. Regression results
9. Capability Boundary results
10. Critical Gate results
11. Reliability metrics where non-determinism exists
12. Observable trajectory findings where useful
13. Failure attribution per failed Case
14. Evaluation-validity review
15. Human Product Review
16. Human Professional Review
17. Final product-completeness decision
18. Exactly one NEXT MATERIAL GAP if required
```

No separate Feature Roadmap is generated.

---

# 24. Evaluation evidence discipline

Required distinctions:

```text
Task outcome
!=
Grader outcome

Agent failure
!=
Evaluation runner failure

Capability failure
!=
Regression failure

Product-critical gap
!=
future enhancement

Human disagreement
!=
permission to hide uncertainty
```

When automated and human graders disagree materially:

```text
record disagreement
inspect evidence / observable trace
resolve or classify GRADER_UNCERTAIN
```

Do not average contradictory judgments into a misleading score.

---

# 25. No score-driven self-optimization authority

Evaluation evidence may later support Candidate N+1 improvement.

But:

```text
score improves
!= acceptance

benchmark improves
!= product scope is correct

model judge prefers answer
!= professional authority

optimizer proposes N+1
!= authorization
```

Any repair still requires Catalyst responsibility classification and explicit Stage authorization.

---

# 26. Minimality / anti-platformization boundary

This Case does NOT authorize:

```text
Catalyst Eval Platform
Benchmark database
Eval Registry
vector benchmark search
universal grader service
LLM judge fleet
Eval dashboard
automatic failure repair
automatic Candidate promotion
automatic Admission
company-wide benchmark framework
```

Case-local files/scripts may be created later only if the execution Stage proves they are necessary to run this evaluation.

The principle remains:

```text
FIRST PROVE THE EVALUATION METHOD ON A REAL AGENT.
THEN DECIDE WHAT — IF ANYTHING — DESERVES PLATFORMIZATION.
```

---

# 27. Why this Evaluation matters to Catalyst itself

Case 02 proved a useful direction:

```text
EXTERNAL AGENT
→ UNDERSTAND
→ DECOMPOSE
→ ASSETIZE
```

Case 01 now tests the inverse organizational capability:

```text
OWN AGENT
→ UNDERSTAND
→ DECOMPOSE BY PRODUCT RESPONSIBILITY
→ MEASURE CURRENT CAPABILITY
→ IDENTIFY TRUE MATERIAL GAP
→ ATTRIBUTE ROOT CAUSE
→ GUIDE ONLY THE NEXT NECESSARY EVOLUTION
```

If this can be repeated reliably, Catalyst gains a capability more important than indiscriminate Agent generation:

> knowing what an Agent actually is, how good it really is, what evidence supports that judgment, and exactly what must change next.

This remains Case-evidenced until repeated use justifies broader promotion.

---

# 28. Stage boundary

Current state after this Contract:

```text
BREA v0.9
FROZEN / EVIDENCE-BACKED

PRODUCT COMPLETENESS
NOT YET DECIDED

EVALUATION METHOD
DEFINED

BENCHMARK CASES
NOT YET FROZEN

EVALUATION EXECUTION
NOT AUTHORIZED

E2-C
NOT AUTHORIZED

ADMISSION / BINDING
NOT AUTHORIZED
```

---

# 29. Next legitimate artifact / action

Do not create another general evaluation concept document.

The next step should be one bounded **Evaluation Execution Stage** that:

```text
1. maps current evidence onto PR-01..PR-18
2. classifies which PRs are actually required for current declared scope
3. designs and freezes only the minimum missing benchmark Cases
4. freezes private rubrics / critical gates
5. identifies deterministic vs model vs human graders
6. runs the complete evaluation against frozen v0.9
7. attributes every material failure
8. conducts Human Product + Professional Review
9. returns only:
   READY_FOR_E2_C
   or PRODUCT_CRITICAL_GAP_REMAINS
   or EVALUATION_NOT_YET_VALID
```

If `PRODUCT_CRITICAL_GAP_REMAINS`:

```text
select exactly one NEXT MATERIAL GAP
→ STOP
```

Do not begin implementation in the same evaluation Stage.

---

# 30. Final verdict

```text
EVALUATION BEFORE FURTHER DEVELOPMENT
REQUIRED

DECLARED PRODUCT SCOPE BEFORE FEATURE WISHLIST
REQUIRED

CAPABILITY EVAL + REGRESSION EVAL SEPARATION
REQUIRED

DETERMINISTIC + MODEL + HUMAN GRADER COMPOSITION
SUPPORTED / USE AS NEEDED

CRITICAL PROFESSIONAL GATES
REQUIRED

SINGLE ADMISSION SCORE
REJECT

RELIABILITY / REPEATED TRIALS FOR NON-DETERMINISTIC PATHS
REQUIRED

OBSERVABLE TRAJECTORY EVALUATION
SUPPORTED

FAILURE ATTRIBUTION
REQUIRED

AGENT FAILURE == HARNESS FAILURE
REJECT

EVALUATION FAILURE SCORED AS AGENT FAILURE
REJECT

HUMAN PROFESSIONAL ACCEPTANCE
REQUIRED FOR PRODUCT COMPLETENESS JUDGMENT

FULL FEATURE ROADMAP FROM AUDIT
REJECT

NEXT MATERIAL GAP
AT MOST ONE

PLATFORM-WIDE EVAL SYSTEM NOW
REJECT

NEXT
CASE-LOCAL EVALUATION EXECUTION STAGE
```
