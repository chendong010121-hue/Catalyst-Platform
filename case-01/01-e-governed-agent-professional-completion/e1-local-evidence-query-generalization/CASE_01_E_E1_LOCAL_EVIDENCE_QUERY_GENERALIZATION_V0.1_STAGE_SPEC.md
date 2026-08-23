# CASE 01-E — E1 LOCAL EVIDENCE QUERY GENERALIZATION V0.1
## STAGE SPEC — PROFESSIONAL COMPLETION SLICE
### PRODUCT CHANGE · GOVERNED CHANGE IMPACT · BUILDER-ASSISTED CANDIDATE N+1 · LOCAL QUERY GENERALIZATION

> **Project:** Catalyst  
> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)  
> **Branch:** `case-01`  
> **Parent stage:** CASE 01-D — `EVIDENCE-BACKED PASS / CLOSED`  
> **Current case-01 baseline before E1 planning:** `b08095913f984b742d9dd44cc1ad712a19d28b76`  
> **Accepted Catalyst main:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **Current admitted Agent:** `case-01.brea @ 0.1-candidate`  
> **E1 Professional Change Request:** `E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md`  
> **Change Request commit:** `9ca6bbdd76ae20633a210403f6a99e0248ed6e01`  
> **Architecture / Stage authority + external auditor:** ChatGPT  
> **Implementation executor:** DeepSeek  
> **Product / Release / Stage authority:** User  
> **E1 Stage Spec:** **ACCEPTED**  
> **E1 execution:** **REQUIRES EXPLICIT USER AUTHORIZATION**  
> **E2:** **NOT AUTHORIZED**  
> **Catalyst main mutation:** **FORBIDDEN**

---

# 0. Stage Thesis

CASE 01-E is the point where the mainline deliberately shifts back toward the actual product.

The current BREA is already:

```text
FORMATION-PROVEN
+ LOCALLY ADMITTED
+ EXECUTION-BOUND
+ TRACEABLE THROUGH CATALYST
```

but its professional behavior remains narrow and strongly tied to the original formation cases.

E1 therefore asks:

> **Can Catalyst drive a governed professional change that turns BREA from a fixture-oriented local evidence Agent into an Agent that can perform general local regulation evidence queries over the already admitted corpus, without mutating the admitted v0.1 baseline and without using LLM/RAG/Web as a shortcut?**

The desired progression is:

```text
BREA v0.1-candidate
ADMITTED / BOUND / READ-ONLY BASELINE
        ↓
Professional Change Request
        ↓
Governed Change Impact
        ↓
Builder / Agent-development mechanism
        ↓
BREA v0.2-candidate
        ↓
Generalized local evidence-query proof
        ↓
Professional evidence
        ↓
External review
```

E1 is a product-completion slice and simultaneously a real test of Catalyst's Agent Development Capability.

---

# 1. Fixed Product Change Request

The authoritative E1 request is:

> **让 BREA 能够对已经接入的本地建筑规范进行一般化查询，而不是只能回答预设测试题；回答必须继续提供原文证据、条款/表格定位和数值来源，找不到可靠证据时不能编造。**

The Stage may refine this into governed technical requirements.

The Stage may not replace it with a different product goal.

---

# 2. Existing BREA v0.1 Is Immutable

The following currently admitted subject is an evidence baseline:

```text
agent_id:
case-01.brea

agent_version:
0.1-candidate

admission_ref:
admission-case-01-brea-v0.1-001

binding_ref:
binding-case-01-brea-v0.1-001
```

E1 may read but may not modify:

```text
case-01/01-c-governed-local-formation/candidate/brea-v0.1/**
```

The D2 implementation fingerprint must remain valid.

If E1 modifies v0.1 in place:

```text
E1 FAIL
STOP
```

---

# 3. E1 Candidate Version

The new Candidate identity is fixed for this Stage as:

```text
agent_id:
case-01.brea

candidate_version:
0.2-candidate
```

Meaning:

```text
same governed Agent lineage
+
new professional implementation Candidate
```

E1 does **not** automatically admit or bind v0.2.

The outcome is a Candidate and professional evidence only.

A later admission / re-binding decision requires separate governance review.

---

# 4. Hard Product Anti-Fixture Rule

E1 must not satisfy the Change Request by adding more branches such as:

```text
if "防火分区" in question:
    clause = "x.x.x"

if "疏散距离" in question:
    clause = "y.y.y"
```

or by adding one dedicated code path per benchmark query.

The core E1 criterion is:

> **New benchmark queries must be answerable because a reusable query/evidence mechanism exists, not because those exact questions were individually encoded.**

The external audit may inspect source code for benchmark-specific clauses / table ids / question literals.

Evidence of benchmark-specific implementation may cause:

```text
REQUEST REPAIR
or
FAIL
```

---

# 5. Current Professional Limitation — Accepted Starting Evidence

Current v0.1 evidence shows:

```text
Question contains 防火间距
→ GB55037-2022
→ fixed Clause 3.1.3 path

Question contains 停车位 / 配建
→ DBJ33T1021-2023
→ fixed Table 5.0.1 + Table 5.0.4 path

Other query intent
→ generally unresolved / fail closed
```

The lower-level corpus / evidence layer already contains reusable primitives such as:

```text
manifest-driven corpus loading
SHA fail-closed verification
clause extraction
basic table extraction
verbatim evidence assertion
locator / page / line construction
```

E1 should evolve the whole-Agent query path rather than discard these proven primitives.

---

# 6. Governed Change Impact Review — Required Before Implementation

Before generating v0.2, DeepSeek must create:

```text
E1_CHANGE_IMPACT_REVIEW_V0.1.md
```

It must classify each existing responsibility as:

```text
UNCHANGED
EXTENDED
IMPLEMENTATION-ONLY CHANGE
REQUIRES DESIGN REVIEW
```

At minimum review:

```text
FN-01 Question & Context Intake
FN-02 Professional Fact Normalization
FN-03 Regulation Applicability Resolution
FN-04 Evidence Locating & Extraction
FN-05 Evidence Binding & Numeric Safety
FN-06 Uncertainty & Fail-Closed Decision
FN-07 Result Composition & Attribution
FN-08 Artifact & Provenance Preservation
FN-09 Corpus Access & Parsing
FN-10 Provider & Execution Plumbing
FN-11 Local Runner / Service Shell

SEAM-01 Professional Project Facts
SEAM-02 Regulation Applicability
SEAM-03 Regulation Evidence

OBL-01..OBL-06
```

Expected default hypothesis:

```text
Professional purpose
UNCHANGED

OBL-01..OBL-06
UNCHANGED

SEAM-01
UNCHANGED unless evidence proves new facts are needed

SEAM-02
EXTENDED

SEAM-03
EXTENDED

FN-04/FN-05/FN-09
major implementation completion
```

If the Stage discovers that the professional purpose or obligations materially need to change:

```text
STOP
→ GOVERNED DESIGN REVIEW
```

Do not silently rewrite 01-B.

---

# 7. Required Development Mechanism

E1 must deliberately test Catalyst's Agent Development Capability.

DeepSeek may not simply hand-edit a copy of v0.1 and call the task complete without preserving a governed development trace.

Required chain:

```text
Professional Change Request
        ↓
Change Impact Review
        ↓
Builder / change-formation input
        ↓
Candidate N+1 workspace
        ↓
Candidate mapping / evidence
```

The existing Case-scoped Builder may be reused / minimally extended.

If the current Builder can only create initial Candidates and cannot consume a governed professional change:

```text
record BUILDER GAP
```

Then E1 may implement the smallest **Case-local Builder change mechanism** needed to:

```text
read accepted baseline definition
read Professional Change Request
read Change Impact Review
copy / form a new Candidate workspace
apply only authorized changed responsibilities
preserve unchanged contracts
produce change provenance
```

This is a Case-local development mechanism, not a generic Builder Platform.

---

# 8. New Candidate Workspace

All v0.2 Candidate files must live under:

```text
case-01/01-e-governed-agent-professional-completion/
e1-local-evidence-query-generalization/
candidate/brea-v0.2/**
```

Do not reuse the admitted v0.1 directory as the target.

The Candidate must preserve the same overall functional decomposition unless Change Impact explicitly proves an allowed change.

---

# 9. E1 Local Query Capability — Minimum Functional Scope

E1 must implement reusable deterministic local evidence-query behavior across the two already admitted regulations.

At minimum support the following query modes.

## QMODE-01 — Explicit Standard + Clause Locator

Examples of input shape:

```text
“GB55037-2022 第3.1.3条怎么规定？”
“查一下 GB 55037 的 3.1.3 条原文。”
```

Required behavior:

```text
resolve standard
resolve clause locator
extract verbatim clause
return source + locator + evidence
```

No special code branch for Clause 3.1.3 is allowed.

## QMODE-02 — Explicit Standard + Unknown / Missing Clause

Example:

```text
“GB55037-2022 第99.9.9条怎么规定？”
```

Required:

```text
no_reliable_evidence
no invented clause
```

## QMODE-03 — Local Topic Evidence Search

Examples:

```text
“GB55037 里哪里提到人员密集场所？”
“这份防火规范里关于汽车库的条文有哪些相关内容？”
```

Required:

```text
search admitted local text
rank / select bounded evidence candidates
return source-backed evidence excerpts / locators
```

The mechanism may use deterministic token / phrase / normalized-text retrieval.

It must not require LLM/RAG/vector database in E1.

## QMODE-04 — Explicit Table / Table-region Query

Where a table can be reliably parsed from the current OCR corpus, E1 should support:

```text
resolve table caption / number
return table region or selected row evidence
```

Do not claim generalized arbitrary table understanding if the parser cannot prove it.

## QMODE-05 — Existing Professional Applicability Cases

Existing T-C01 / T-C02 / T-C03 behavior must remain valid.

E1 generalized query support does not replace professional applicability logic.

---

# 10. Search / Retrieval Semantics

E1 may choose deterministic local retrieval implementation under the existing PRIVATE implementation freedom.

Allowed examples:

```text
exact locator extraction
normalized phrase search
keyword / token scoring
section-window search
bounded candidate ranking
simple lexical scoring
```

Forbidden as necessary dependencies for E1:

```text
external Web
LLM
embedding service
vector DB
remote provider
```

If DeepSeek chooses an optional local dependency, it must justify why stdlib / existing implementation is insufficient.

The preferred result remains simple and inspectable.

---

# 11. Evidence Contract Must Remain Stable

The current Result contract should remain compatible:

```text
request_id
status
conclusion
evidence_items
artifacts
uncertainty
implementation_metadata
```

E1 may extend Case-local metadata only if backward-compatible and evidence-justified.

Every accepted professional answer must continue to provide:

```text
source_identity
source_title
source_version_or_date
locator
evidence_type
evidence_content
claim_relation
```

OBL-01 / OBL-05 remain mandatory.

---

# 12. Numeric Safety

E1 must preserve:

```text
NO normative numeric claim without source evidence
```

Any conclusion containing a normative numeric value must have source evidence that includes / resolves that value.

Generalized retrieval must not turn numeric text matches into normative conclusions without applicability / binding logic.

For generic topic retrieval:

```text
evidence excerpt
!= automatically accepted normative conclusion
```

When the Agent cannot safely bind a professional numeric conclusion:

```text
return evidence / uncertainty
or
fail closed
```

rather than fabricate meaning.

---

# 13. Applicability Boundary

E1 must distinguish:

```text
Evidence Retrieval
from
Professional Applicability Decision
```

An explicit clause lookup can return clause evidence even if the project facts are insufficient to claim that the clause applies to the user's project.

The Result must make this distinction observable.

Example:

```text
“查 3.1.3 原文”
→ evidence query can succeed

“我的项目是否适用 3.1.3？”
→ requires professional facts / applicability
```

Do not let generalized retrieval bypass SEAM-02.

---

# 14. Required E1 Benchmark Design

E1 must create a benchmark set that was **not the implementation source list**.

Minimum benchmark classes:

```text
B-E1-01 explicit clause lookup — existing known clause
B-E1-02 same clause — alternate natural-language wording
B-E1-03 explicit clause lookup — different real clause from admitted corpus
B-E1-04 nonexistent clause — fail closed
B-E1-05 local topic search — GB corpus
B-E1-06 local topic search — DBJ corpus
B-E1-07 explicit table-region query
B-E1-08 table / row query with insufficient facts
B-E1-09 local corpus does not support question — no_reliable_evidence
B-E1-10 normative numeric question without sufficient applicability — no unsupported numeric conclusion
B-E1-11 existing T-C01 regression
B-E1-12 existing T-C02 regression
B-E1-13 existing T-C03 regression
```

At least **three successful queries** must involve a locator / topic / phrase that was not individually hardcoded into Candidate runtime code.

The benchmark artifact must record:

```text
question
expected class of behavior
expected source / locator constraints
whether professional applicability is required
numeric safety expectation
```

Do not encode full expected answer text into runtime code.

---

# 15. Anti-Hardcode Inspection

Create:

```text
E1_ANTI_HARDCODE_REVIEW_V0.1.md
```

It must inspect the Candidate source and answer:

```text
Are benchmark questions copied into runtime code?
Are benchmark-specific clause ids copied into dedicated branches?
Are benchmark-specific conclusions hardcoded?
Does a reusable locator / retrieval path exist?
Can at least 3 previously unencoded local queries succeed?
```

Allowed:

```text
standard metadata
known parser patterns
table structure knowledge where general to that source format
professional applicability rules
```

Not allowed as evidence of generalization:

```text
one branch per benchmark
one conclusion string per benchmark
one dedicated handler per test question
```

---

# 16. v0.1 Regression Requirement

The admitted v0.1 baseline must remain unchanged and must still pass its existing self-check.

The v0.2 Candidate must also preserve the historical professional behavior:

```text
T-C01 PASS
T-C02 PASS
T-C03 PASS
```

Any regression in OBL-01..06 is blocking.

---

# 17. D2 / Platform Compatibility in E1

E1 is **not** an admission stage.

Therefore E1 does not need to create a new official Admission / Binding Record for v0.2.

However, it must answer:

> Can the v0.2 Candidate still satisfy the existing D2 execution adapter shape without requiring Platform Core / Runtime changes?

Required evidence:

```text
E1_PLATFORM_COMPATIBILITY_CHECK_V0.1.md
```

Preferred result:

```text
request/result contract compatible
Platform Core change NONE
Runtime change NONE
D2 Case-local binding mechanism conceptually reusable later
```

If v0.2 requires Platform Core / Runtime modification:

```text
STOP
→ ARCHITECTURE REVIEW
```

---

# 18. Enterprise Boundary

E1 should not add Enterprise product scope unless the generalized local-query capability genuinely requires it.

Minimum Enterprise context remains:

```text
organization_id
user_id
optional project_id
```

Do not implement:

```text
source trust policy
network permission
IAM
RBAC
human review workflow
```

Those are likely relevant in later Web / organizational stages, not E1 local-only retrieval.

---

# 19. Corpus Boundary

E1 must use exactly the currently admitted two local corpus references.

Do not add a third regulation in E1.

This is intentional.

The proof must demonstrate:

> More general behavior came from a better Agent mechanism, not a larger corpus.

Raw corpus remains:

```text
local
read-only
not committed
```

---

# 20. Builder / Development Evidence

E1 must create:

```text
E1_AGENT_DEVELOPMENT_TRACE_V0.1.md
```

It must show:

```text
Professional Change Request
→ impacted responsibilities
→ unchanged responsibilities
→ Builder / change mechanism input
→ files created / changed in v0.2 Candidate
→ reason for each changed module
→ tests / benchmark
→ Candidate output
```

If DeepSeek manually changes code outside this trace, external review may reject the Stage as failing to test the intended Catalyst development capability.

---

# 21. Required Output Package

Write only under:

```text
case-01/01-e-governed-agent-professional-completion/
e1-local-evidence-query-generalization/**
```

Expected outputs:

```text
E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md
CASE_01_E_E1_LOCAL_EVIDENCE_QUERY_GENERALIZATION_V0.1_STAGE_SPEC.md

change/
  E1_CHANGE_IMPACT_REVIEW_V0.1.md
  E1_AGENT_DEVELOPMENT_TRACE_V0.1.md

builder/
  <minimum Case-local change / Candidate formation mechanism if needed>
  E1_BUILDER_RUN_REPORT_V0.1.md

candidate/
  brea-v0.2/**

tests/
  <E1-local benchmark / test runner>

evidence/
  E1_TEST_RESULTS.log.txt
  E1_BENCHMARK_RESULTS_V0.1.json
  E1_ANTI_HARDCODE_REVIEW_V0.1.md
  E1_V01_BASELINE_INTEGRITY_V0.1.md
  E1_V02_FUNCTION_SEAM_OBLIGATION_CONFORMANCE_V0.1.md
  E1_PLATFORM_COMPATIBILITY_CHECK_V0.1.md
  E1_REPOSITORY_INTEGRITY_V0.1.md
  PLATFORM_GAP_UPDATE_E1_V0.1.md
  E1_EVIDENCE_INDEX_V0.1.md

review/
  CASE_01_E_E1_EXECUTION_REPORT_V0.1.md
  CASE_01_E_E2_ENTRY_BOUNDARY_V0.1.md
```

Equivalent minimal organization is allowed only if all evidence remains explicit.

---

# 22. E1 Allowed Writes

After explicit authorization, DeepSeek may write only under:

```text
case-01/01-e-governed-agent-professional-completion/
e1-local-evidence-query-generalization/**
```

Read-only inputs may include:

```text
01-A / 01-B / 01-C / 01-D artifacts
admitted BREA v0.1
current Platform / Runtime source
local admitted corpus
```

---

# 23. Forbidden Writes

Do not modify:

```text
case-01/01-c-governed-local-formation/candidate/brea-v0.1/**
case-01/01-d-governed-agent-admission-binding/** accepted D2 evidence
platform_standard/**
agent_runtime/**
enterprise_extensions/**
root tests/**
CI
Catalyst README / Architecture / Governing Baseline
main
raw corpus
Legacy Agent 2.0
```

Do not implement in E1:

```text
Web fallback
RAG
LLM
Memory
Agent loop
frontend
backend service platform
Generic Builder Platform
Generic Admission Platform
Generic Agent Registry
```

---

# 24. Preflight

Before E1 execution:

```text
P-E1-01 explicit User E1 authorization exists
P-E1-02 branch == case-01
P-E1-03 case-01 contains E1 Change Request + Stage Spec
P-E1-04 admitted v0.1 fingerprint still matches D2
P-E1-05 accepted main == 5874be1130e8867082880fcd63f659fc909d9efd
P-E1-06 raw corpus remains outside repo
P-E1-07 no unknown user work would be overwritten
P-E1-08 v0.2 Candidate does not already exist unless created by this authorized run
```

Unknown work:

```text
STOP
DO NOT CLEAN
```

---

# 25. Execution Sequence

After explicit authorization:

```text
E1-0  preflight
E1-1  freeze v0.1 / main / corpus evidence
E1-2  perform Change Impact Review
E1-3  confirm professional purpose + OBL-01..06 remain valid
E1-4  define generalized local-query behavior
E1-5  prepare Builder / Candidate-change input
E1-6  form brea-v0.2 Candidate in clean target
E1-7  implement reusable local locator / topic evidence-query mechanism
E1-8  preserve / extend applicability separation
E1-9  preserve numeric safety + evidence contract
E1-10 design benchmark without adding benchmark-specific runtime branches
E1-11 run historical T-C01/02/03 regression
E1-12 run E1 benchmark classes
E1-13 run anti-hardcode review
E1-14 run FN/SEAM/OBL conformance review
E1-15 run Platform compatibility check
E1-16 verify admitted v0.1 unchanged
E1-17 verify no Platform / Runtime / main / raw-corpus contamination
E1-18 update Platform / Builder gap evidence
E1-19 generate E2 entry boundary
E1-20 one implementation+evidence commit + one push to case-01
E1-21 STOP for external review
```

E2 must not start automatically.

---

# 26. Stop Conditions

STOP and report if:

```text
S-E1-01 v0.1 must be mutated to implement change
S-E1-02 professional purpose materially changes
S-E1-03 OBL-01..06 are insufficient and new obligations are required
S-E1-04 generalized query can only be achieved by benchmark-specific hardcode
S-E1-05 query generalization bypasses professional applicability boundary
S-E1-06 numeric conclusions can be generated without bound source evidence
S-E1-07 raw corpus must be copied to GitHub
S-E1-08 Platform Core change required
S-E1-09 Runtime / RuntimeAdapter change required
S-E1-10 Enterprise semantics must be pushed into Runtime
S-E1-11 existing admitted v0.1 fingerprint changes
S-E1-12 E1 requires Web / LLM / RAG / Memory as mandatory dependency
S-E1-13 implementation occurs outside E1 write path
S-E1-14 main drifts
```

---

# 27. Acceptance Criteria

External E1 PASS requires all:

```text
AC-E1-01 v0.1 remains byte / fingerprint unchanged
AC-E1-02 v0.2 Candidate exists as separate workspace
AC-E1-03 Professional Change Request is traceable to implementation
AC-E1-04 Change Impact Review is complete
AC-E1-05 professional purpose remains stable or Stage stops for design review
AC-E1-06 OBL-01..06 remain satisfied
AC-E1-07 reusable explicit-clause query exists
AC-E1-08 nonexistent clause fails closed
AC-E1-09 reusable topic evidence retrieval exists
AC-E1-10 at least one bounded table query path exists or is explicitly evidence-deferred
AC-E1-11 evidence / locator / source contract preserved
AC-E1-12 applicability remains separate from mere retrieval
AC-E1-13 no unsupported normative numeric conclusions
AC-E1-14 T-C01 PASS
AC-E1-15 T-C02 PASS
AC-E1-16 T-C03 PASS
AC-E1-17 at least 3 successful queries were not individually hardcoded into runtime code
AC-E1-18 anti-hardcode review PASS
AC-E1-19 FN/SEAM/OBL mapping remains valid
AC-E1-20 Platform / Runtime unchanged
AC-E1-21 current D2 admitted/bound v0.1 evidence remains valid
AC-E1-22 raw corpus not committed
AC-E1-23 main unchanged
AC-E1-24 E2 not started
```

---

# 28. E1 Verdict Model

DeepSeek returns one:

```text
READY FOR E1 EXTERNAL REVIEW

GOVERNED DESIGN REVIEW REQUIRED

IMPLEMENTATION FAILURE / TARGETED REPAIR CANDIDATE

PRODUCT CHANGE NOT PROVEN
```

ChatGPT external review decides:

```text
A. EVIDENCE-BACKED PASS / CLOSED
B. TARGETED REPAIR
C. DESIGN / ARCHITECTURE REVIEW REQUIRED
D. FAIL
```

---

# 29. Publication Rule

Current state:

```text
E1 CHANGE REQUEST
RECORDED

E1 STAGE SPEC
ACCEPTED

E1 EXECUTION
NOT AUTHORIZED
```

After explicit User authorization, DeepSeek may publish:

```text
ONE E1 implementation + evidence commit
+
ONE push to case-01
+
STOP
```

No intermediate push.

No main PR.

No post-push repair without a new authorization.

---

# 30. Platform Co-evolution Questions E1 Must Answer

E1 must collect evidence for:

```text
Can the existing Builder support governed professional changes?

If not, what minimum Case-local Builder-change mechanism was needed?

Does Candidate N+1 formation preserve Agent identity while changing implementation?

Which query semantics belong to Domain vs Private implementation?

Does generalized retrieval require a new governed seam?

Can existing Admission / Binding mechanics conceptually accept a future v0.2 without Core change?
```

No answer automatically authorizes generalization.

---

# 31. E2 Entry Boundary

E1 must generate:

```text
review/CASE_01_E_E2_ENTRY_BOUNDARY_V0.1.md
```

It must state:

```text
v0.2 Candidate maturity
local-query behaviors proven
benchmark coverage
remaining hardcoded / parser limitations
current product gaps
Builder-development evidence
Domain / Enterprise issues exposed
Platform gaps exposed
recommended next professional-completion slice
E2 authorization = NO
```

Expected likely next slice:

```text
E2 — Local Professional Coverage Expansion
```

but E1 may recommend a different bounded slice if evidence shows a more important bottleneck.

---

# 32. Final Authorization State

```text
CASE 01-D
EVIDENCE-BACKED PASS / CLOSED

CASE 01-E / E1
CHANGE REQUEST RECORDED
STAGE SPEC ACCEPTED
EXECUTION REQUIRES EXPLICIT USER AUTHORIZATION

BREA v0.1-candidate
ADMITTED / BOUND / READ-ONLY

BREA v0.2-candidate
NOT YET FORMED

E2
NOT AUTHORIZED

PLATFORM CORE CHANGE
FORBIDDEN

RUNTIME CHANGE
FORBIDDEN

MAIN CHANGE
FORBIDDEN
```

# **E1 SPEC VERDICT — ACCEPTED / READY FOR EXPLICIT EXECUTION AUTHORIZATION**
