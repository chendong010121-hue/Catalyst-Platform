# CASE 01-D — D2 LOCAL ADMISSION & BINDING PROOF V0.1
## STAGE SPEC — IMPLEMENTATION NOT YET AUTHORIZED
### AGENT ADMISSION · EXECUTION BINDING · ATTRIBUTION · PROVENANCE · CASE ↔ PLATFORM CO-EVOLUTION

> **Project:** Catalyst  
> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)  
> **Branch:** `case-01`  
> **Parent:** CASE 01-D / D1 — `EVIDENCE-BACKED PASS / CLOSED`  
> **D1 implementation/evidence commit:** `747317afd0d2f8ca3a09394b4d5de1a22405eec2`  
> **Catalyst accepted `main`:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **CASE 01-C final formation closure:** `dd491a73a5dc59227a7c93c7962e9ba23ea04efa`  
> **D0 method proof:** `EVIDENCE-BACKED PASS / CLOSED AS CASE 01 METHOD PROOF`  
> **Architecture / Stage authority + external auditor:** ChatGPT  
> **Implementation author:** DeepSeek  
> **Product / Release / Stage authority:** User  
> **D2 Stage Spec:** **ACCEPTED**  
> **D2 execution:** **REQUIRES EXPLICIT USER AUTHORIZATION**  
> **CASE 01-E:** **NOT AUTHORIZED**  
> **Catalyst `main` mutation:** **FORBIDDEN**

---

# 0. Stage Thesis

CASE 01-D now stands at:

```text
01-D / D0  BLIND AGENT UNDERSTANDING METHOD PROOF      CLOSED
01-D / D1  ADMISSION ARCHITECTURE COMPATIBILITY        CLOSED
01-D / D2  LOCAL ADMISSION & BINDING PROOF              NEXT
```

D2 is the first implementation proof that an already formation-proven Governed Agent can enter Catalyst's local governance + execution boundary as an **exact admitted Agent version**, bind to an **exact implementation**, execute through the **existing Platform-compatible path**, and return evidence that can be traced back to that exact admitted version.

D2 must prove:

```text
Governed Agent identity
        !=
Platform execution routing identity

Formation Evidence
        !=
Admission Decision

Admission
        !=
Registry registration

Binding
        !=
Agent identity

Agent governance attribution
        travels around / through execution evidence
        without becoming Runtime meaning
```

The preferred architecture remains:

```text
BREA v0.1-candidate
        ↓
Case-local Admission Record
        ↓
Case-local Execution Binding
        ↓
Case-local governance.agent attribution helper
        ↓
Existing Platform Invocation / Validator / RuntimeAdapter
        ↓
Existing Runtime
        ↓
Result / ArtifactRef / Trace
        ↓
Case-local provenance verification
```

No Platform Core or Runtime change is expected or authorized.

---

# 1. D1 Accepted Architecture Inputs

D2 inherits these D1 conclusions as accepted inputs:

```text
Agent != Capability
PASS

Admission != Registry.register()
PASS

Admission != runnable
PASS

Binding != Agent identity
PASS

Platform execution path
REUSABLE

Platform Core change
NOT REQUIRED

Runtime change
NOT REQUIRED

Agent-level identity/version/admission
CASE-LOCAL

Agent execution attribution
governance.agent Extension candidate

Execution binding
CASE-LOCAL / ADAPTER-LOCAL
```

D2 may implement these Case-local candidates.

D2 may not reinterpret D1 into a generic Platform proposal.

---

# 2. Three Mandatory External-Audit Preconditions

These are hard D2 rules.

## P-D2-01 — Canonical Agent Attribution Location

D2 must use exactly one canonical Agent attribution source on Invocation:

```text
Invocation.extensions["governance.agent"]
```

The existing Platform contract still requires:

```text
Invocation.context["extensions"]
```

to exist structurally.

For D2:

```text
Invocation.context.extensions
MUST NOT contain governance.agent
```

If `governance.agent` appears in `context.extensions`:

```text
FAIL CLOSED
AMBIGUOUS ATTRIBUTION AUTHORITY
```

Do not use:

```text
Invocation.extensions and/or Invocation.context.extensions
```

as two possible authorities.

A Case-local attribution helper must perform:

```text
validate Invocation
→ parse + validate Invocation.extensions["governance.agent"]
→ verify it matches Admission + Binding
→ execute through unchanged RuntimeAdapter
→ retrieve trace events
→ attach the exact same governance.agent value to TraceEvent.extensions
→ fail closed on any conflicting existing attribution
→ return Result + attributed Trace
```

The generic RuntimeAdapter is not responsible for understanding or propagating Agent governance semantics.

## P-D2-02 — Governed Agent Identity and Execution Capability Identity Must Be Explicitly Separate

D2 must define two different semantic identities.

Required Case-local Agent identity:

```text
agent_id = "case-01.brea"
agent_version = "0.1-candidate"
```

Required execution-routing identity:

```text
execution_capability_id = "case-01.brea.execute"
execution_capability_version = "0.1"
```

The strings must remain distinct:

```text
agent_id != execution_capability_id
agent_version != execution_capability_version
```

The meaning is:

```text
agent_id / agent_version
→ governed subject identity

execution_capability_id / execution_capability_version
→ Platform / Runtime routing identity only
```

The Platform `CapabilityDescriptor.id` must never become the source of truth for Agent identity.

D2 positive evidence must show the mapping explicitly.

## P-D2-03 — Admission Decision Authority Must Be Explicit

DeepSeek, Registry and test results are not admission authorities.

D2 execution authorization, when explicitly granted by the User, means:

> **The User authorizes CASE 01 to attempt a local BREA v0.1 admission under the accepted D2 gates. If and only if all mandatory gates pass, the D2 mechanism may write the final Case-local Admission Record as `ADMITTED`, referencing that explicit User authorization as the decision authority.**

Authority chain:

```text
User explicit D2 authorization
→ authority to attempt conditional Case-local admission

D2 implementation / DeepSeek
→ evaluates required evidence
→ writes record according to deterministic rules
→ cannot override failed gates

Platform Registry
→ descriptor storage / execution lookup only
→ NOT governance authority

ChatGPT external audit
→ verifies D2 evidence and Stage closure
→ does not retroactively invent admission authority
```

If explicit D2 authorization is absent:

```text
DO NOT EXECUTE
DO NOT WRITE ADMITTED
```

---

# 3. Governed Subject

The D2 governed subject is fixed:

```text
Agent:
BREA — Building Regulation Evidence Agent

agent_id:
case-01.brea

agent_version:
0.1-candidate

accepted Governed Definition SHA:
6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4

formation closure:
dd491a73a5dc59227a7c93c7962e9ba23ea04efa
```

Professional purpose, FN-01..FN-11, SEAM-01..03 and OBL-01..06 remain frozen from accepted 01-B/C evidence.

D2 may not redesign BREA.

If D2 cannot proceed without changing them:

```text
STOP
→ ARCHITECTURE / DESIGN REVIEW
```

---

# 4. D2 Execution Identity

D2 must introduce a **Case-local execution-routing identity** separate from Agent identity:

```text
execution_capability_id:
case-01.brea.execute

execution_capability_version:
0.1
```

This Capability identity exists only to reuse the current executable Platform / Runtime path.

It does not mean:

```text
BREA Agent == Capability
```

The mapping must be explicit in the Binding Record:

```text
case-01.brea @ 0.1-candidate
        ↓ binding
case-01.brea.execute @ 0.1
        ↓
BREA runner implementation
```

---

# 5. Minimum Admission Gates

D2 may write:

```text
admission_status = ADMITTED
```

only if every mandatory gate passes.

## G-A01 — Exact Governed Definition

Verify the accepted Builder-consumable Governed Definition SHA exactly equals:

```text
6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4
```

Mismatch:

```text
REJECT
```

## G-A02 — Formation Closure Exists

Verify CASE 01-C final closure/evidence is present and references the accepted Candidate.

At minimum resolve:

```text
01-C final closure
Builder → Candidate provenance
FN / SEAM / OBL conformance evidence
15/15 Candidate self-check evidence
T-C01 / T-C02 / T-C03 evidence
```

Missing required formation evidence:

```text
REJECT
```

## G-A03 — Candidate Has Not Mutated

The 01-C Candidate is read-only in D2.

Recompute deterministic implementation fingerprint from the exact Candidate files declared by the accepted 01-C Builder Output Manifest.

Recommended deterministic method:

```text
for each declared Candidate file:
    relative_path
    SHA256(file bytes)

sort by relative_path
canonicalize the path/hash list
aggregate SHA256(canonical list)

also compute:
SHA256(BUILDER_OUTPUT_MANIFEST_V0.1.json)
```

Binding fingerprint must contain both:

```text
candidate_tree_sha256
builder_output_manifest_sha256
```

Do not include:

```text
__pycache__
transient logs
runtime temp files
raw corpus
```

unless the accepted manifest declares them as Candidate implementation files.

## G-A04 — Corpus Boundary Intact

Verify the admitted local corpus reference remains the accepted read-only reference boundary.

Raw corpus must not be copied into GitHub.

Any raw-corpus upstream contamination:

```text
REJECT
STOP
```

## G-A05 — Owner / Acceptance Authority Exists

Resolve the existing Case 01 minimum governance context:

```text
owner / Product-Release Authority
User / CASE 01 Product-Release Authority

evaluation / acceptance authority
User / CASE 01 Acceptance Authority
```

D2 final Admission Record must reference the explicit D2 authorization record created after User authorization.

## G-A06 — Candidate Regression Still Passes

Without modifying 01-C Candidate, rerun the accepted Candidate test/self-check surface.

Required:

```text
Candidate tests / self-check
15 / 15 PASS

T-C01
PASS

T-C02
PASS

T-C03
PASS
```

Regression failure:

```text
DO NOT ADMIT
```

## G-A07 — No Unauthorized Architecture Mutation

Verify:

```text
Platform Core unchanged
Platform Standard code unchanged
Runtime unchanged
Runtime Adapter unchanged
enterprise_extensions unchanged
01-C Candidate unchanged
main unchanged
```

Any prohibited mutation:

```text
STOP
```

---

# 6. Minimum Case-Local Admission Record

Create a machine-readable Case-local record only after validating gates.

Required final artifact:

```text
admission/BREA_V0_1_ADMISSION_RECORD.json
```

Minimum fields:

```text
record_kind
record_version
agent_id
agent_version
professional_purpose_ref
governed_definition_ref
governed_definition_sha256
formation_evidence_refs[]
obligations_ref
governed_seams_ref
implementation_fingerprint_ref
enterprise_context_ref
corpus_boundary_ref
owner_ref
acceptance_authority_ref
d2_authorization_ref
admission_status
admission_decision_reason
decided_at
```

Allowed final status:

```text
ADMITTED
or
REJECTED
```

`PENDING` may exist only as temporary in-memory/local working state and must not be published as successful D2 evidence.

If any mandatory admission gate fails:

```text
admission_status = REJECTED
NO Binding Record marked BOUND
NO normal positive execution proof
STOP after failure evidence/report
```

This record is:

```text
CASE-LOCAL
NOT PLATFORM CORE
NOT GENERIC AGENT MANIFEST
NOT REGISTRY ENTRY
```

---

# 7. Minimum Case-Local Execution Binding Record

Only an `ADMITTED` Agent may receive a successful binding.

Required artifact:

```text
binding/BREA_V0_1_EXECUTION_BINDING.json
```

Minimum fields:

```text
binding_id
binding_version
agent_id
agent_version
admission_ref
implementation_fingerprint
execution_capability_id
execution_capability_version
execution_entry_ref
platform_standard_version
binding_status
created_under_authorization_ref
```

Successful status:

```text
BOUND
```

Binding validation must verify:

```text
Agent identity matches Admission Record
Agent version matches Admission Record
Admission status == ADMITTED
Implementation fingerprint matches admitted fingerprint
execution_capability_id == case-01.brea.execute
execution_capability_version == 0.1
execution entry resolves to the read-only BREA Candidate runner
```

Mismatch:

```text
FAIL CLOSED
DO NOT BIND
```

Binding must not own:

```text
professional Domain meaning
Enterprise policy
Agent product purpose
Runtime execution semantics
```

---

# 8. Case-Local `governance.agent` Semantic

D2 may implement one Case-local interpreter for:

```text
governance.agent
```

Canonical Extension shape:

```json
{
  "version": "0.1",
  "required": false,
  "payload": {
    "agent_id": "case-01.brea",
    "agent_version": "0.1-candidate",
    "admission_ref": "...",
    "binding_ref": "..."
  }
}
```

Required parser behavior:

```text
extension absent
→ fail closed for D2 governed execution

unsupported version
→ fail closed

required != false
→ fail closed under current Core v0.1

payload not object
→ fail closed

missing / empty field
→ fail closed

agent_id/version mismatch Admission Record
→ fail closed

admission_ref mismatch
→ fail closed

binding_ref mismatch
→ fail closed
```

Invocation authority:

```text
Invocation.extensions["governance.agent"]
```

Trace attribution:

```text
TraceEvent.extensions["governance.agent"]
```

Conflict rule:

```text
no existing trace attribution
→ attach

identical existing attribution
→ preserve

conflicting existing attribution
→ fail closed
```

Do not modify generic `platform_standard/extensions.py`.

---

# 9. Enterprise Attribution

D2 may reuse existing:

```text
enterprise.identity
```

for minimum organization / user / project attribution.

The existing Case 01 minimum enterprise context remains sufficient.

For D2 positive execution, use a deterministic Enterprise identity consistent with the admitted Case context.

If `enterprise.identity` is supplied, the Case-local orchestration layer must verify it is compatible with the Admission Record enterprise context.

Mismatch:

```text
FAIL CLOSED
```

Do not implement:

```text
IAM
Authentication
RBAC
Approval workflow
Enterprise policy engine
```

Enterprise identity remains attribution, not authorization.

---

# 10. Case-Local Platform Compatibility Wrapper

D2 may add the minimum local code needed to adapt BREA to the existing execution path.

Permitted responsibilities:

```text
BREA runner → Runtime Capability protocol adapter
Platform Capability Descriptor for execution routing only
Case-local artifact mapper
Admission gate validation
Binding validation
governance.agent parser / attribution helper
provenance verification
```

The execution Capability Descriptor must use:

```text
id = case-01.brea.execute
capability_version = 0.1
```

It may describe the already accepted BREA request/result shape for Platform direct-binding conformance.

Do not modify BREA professional behavior to satisfy Platform routing.

If direct binding cannot be achieved without changing BREA FN/SEAM/OBL semantics:

```text
STOP
→ ARCHITECTURE REVIEW
```

---

# 11. Required Provenance Chain

D2 must produce one machine/verifier-readable proof chain connecting:

```text
Admission Record
        ↓
Binding Record
        ↓
Invocation.extensions["governance.agent"]
        ↓
Platform Invocation
        ↓
execution capability routing identity
        ↓
RuntimeAdapter / Runtime
        ↓
Result.invocation_id
        ↓
TraceEvent.trace_id + subject_id
        ↓
TraceEvent.extensions["governance.agent"]
        ↓
ArtifactRef.producer.invocation_id
```

The verifier must assert that all identifiers resolve back to:

```text
agent_id = case-01.brea
agent_version = 0.1-candidate
exact admission_ref
exact binding_ref
exact implementation fingerprint
```

Required artifact:

```text
evidence/D2_PROVENANCE_CHAIN_V0.1.json
```

and human-readable:

```text
evidence/D2_PROVENANCE_CHAIN_V0.1.md
```

A result that runs successfully but cannot establish this chain:

```text
D2 FAIL
```

---

# 12. Required D2 Tests

Create D2-local tests only.

Do not modify root / accepted Platform tests.

At minimum prove:

```text
D2-T01 valid gates → Admission Record ADMITTED

D2-T02 wrong Governed Definition SHA → REJECTED

D2-T03 missing required Formation Evidence → REJECTED

D2-T04 implementation fingerprint mismatch → binding rejected

D2-T05 unknown Agent version → no binding / fail closed

D2-T06 missing governance.agent on governed execution → fail closed

D2-T07 governance.agent payload mismatches Admission/Binding → fail closed

D2-T08 governance.agent appears in Invocation.context.extensions → fail closed as ambiguous authority

D2-T09 agent_id != execution_capability_id and semantic mapping is explicit

D2-T10 wrong execution capability binding → fail closed

D2-T11 conflicting TraceEvent governance.agent attribution → fail closed

D2-T12 result / trace / artifact provenance cannot be linked → fail closed

D2-T13 enterprise.identity conflicts with admitted enterprise context → fail closed

D2-T14 Platform-bound T-C01 direct clause → professional behavior preserved + exact Agent attribution

D2-T15 Platform-bound T-C02 conditional table → professional behavior preserved + exact Agent attribution

D2-T16 Platform-bound T-C03 insufficient-context fail closed → fail-closed behavior preserved + exact Agent attribution
```

D2-T14..16 must invoke the **whole BREA Agent through the D2 Platform-compatible binding path**, not call isolated functions directly.

---

# 13. Evidence Output Package

Write only under:

```text
case-01/01-d-governed-agent-admission-binding/d2-local-admission-binding/
```

Expected package:

```text
admission/
  BREA_V0_1_ADMISSION_RECORD.json

binding/
  BREA_V0_1_EXECUTION_BINDING.json

implementation/
  <minimum Case-local admission / binding / attribution / adapter code>

scripts/
  <deterministic fingerprint / provenance verification helpers if needed>

tests/
  <D2-local tests>

evidence/
  D2_TEST_RESULTS.log
  D2_CANDIDATE_REGRESSION_RESULTS.log
  D2_PLATFORM_BOUND_CASE_RESULTS.log
  D2_PROVENANCE_CHAIN_V0.1.json
  D2_PROVENANCE_CHAIN_V0.1.md
  D2_EVIDENCE_INDEX_V0.1.md
  D2_REPOSITORY_INTEGRITY_V0.1.md
  PLATFORM_GAP_UPDATE_D2_V0.1.md

review/
  CASE_01_D_D2_EXECUTION_REPORT_V0.1.md
  CASE_01_E_ENTRY_BOUNDARY_V0.1.md
```

Equivalent minimal structure is allowed if all required semantics/evidence remain explicit.

Do not create a generic reusable package merely for neatness.

---

# 14. Platform Gap Update

D2 must update evidence for D1 gaps without auto-promoting them.

Track at least:

```text
G-D1-01 Agent identity/version/admission representation
G-D1-02 Agent execution attribution
G-D1-03 whole-Agent execution through capability-centric mechanics
G-D1-04 implementation fingerprint
G-D1-05 admission status / decision record
```

Allowed D2 dispositions:

```text
CASE-PROVEN
CASE-PROVEN / GENERALIZATION CANDIDATE
STILL OPEN
BLOCKED
```

D2 may not declare:

```text
PLATFORM CORE ADOPTED
GENERIC CATALYST CAPABILITY
```

Only one Agent / one Case has been proven.

---

# 15. D2 Allowed Writes

After explicit D2 authorization, DeepSeek may write only under:

```text
case-01/01-d-governed-agent-admission-binding/d2-local-admission-binding/**
```

Read-only inputs may include:

```text
case-01/01-b-governed-agent-definition/**
case-01/01-c-governed-local-formation/**
case-01/01-d-governed-agent-admission-binding/d0-agent-understanding/**
case-01/01-d-governed-agent-admission-binding/d1-admission-architecture-compatibility/**
Platform Standard / Runtime / Enterprise extension source at accepted main
local admitted regulation corpus through existing read-only reference
```

Raw corpus remains local and must not be copied into GitHub.

---

# 16. Forbidden Writes / Changes

D2 may not modify:

```text
Catalyst main
README / ARCHITECTURE / Governing Baseline
platform_standard/**
agent_runtime/**
enterprise_extensions/**
examples/**
root tests/**
CI
CASE 01-B accepted artifacts
CASE 01-C Candidate implementation / accepted evidence
Legacy Agent 2.0 workspace
raw regulation corpus
```

D2 may not implement:

```text
Generic Agent Registry
Generic Admission Service
Generic Binding Service
Generic Agent Manifest SDK
Control Plane
IAM / RBAC
Approval Engine
Policy Engine
Generic Agent Understanding Service
Generic Builder Platform
```

---

# 17. D2 Preflight

Before execution:

```text
P-D2-00 explicit User D2 execution authorization exists
P-D2-01 branch == case-01
P-D2-02 case-01 includes D1 commit 747317afd0d2f8ca3a09394b4d5de1a22405eec2
P-D2-03 accepted main == 5874be1130e8867082880fcd63f659fc909d9efd
P-D2-04 CASE 01-C closure remains present
P-D2-05 D1 external verdict == EVIDENCE-BACKED PASS / CLOSED
P-D2-06 no unauthorized local work would be overwritten
P-D2-07 01-C Candidate is unchanged before D2
P-D2-08 raw corpus remains outside GitHub
P-D2-09 D2 directory contains Stage Spec / authorization only before implementation
```

Unknown user work:

```text
STOP
DO NOT CLEAN OR OVERWRITE
```

---

# 18. D2 Execution Sequence

Once separately authorized:

```text
D2-0   preflight + freeze SHAs
D2-1   resolve explicit D2 authorization authority ref
D2-2   validate Governed Definition SHA
D2-3   resolve Formation Evidence
D2-4   recompute Candidate implementation fingerprint
D2-5   verify corpus boundary / no raw corpus upstream
D2-6   rerun Candidate 15/15 + T-C01/02/03 regression
D2-7   evaluate Admission gates
D2-8   if any admission gate fails → write REJECTED evidence → STOP
D2-9   write Case-local ADMITTED Admission Record
D2-10  create + validate Execution Binding Record
D2-11  create execution Capability routing descriptor / BREA adapter-local wrapper
D2-12  implement Case-local governance.agent parser + attribution helper
D2-13  compose existing Platform Validator / RuntimeAdapter / Runtime path
D2-14  run D2-T01..D2-T16
D2-15  run Platform-bound T-C01 / T-C02 / T-C03
D2-16  generate machine-readable provenance chain
D2-17  independently verify provenance chain
D2-18  update D1 gap evidence
D2-19  repository contamination / main integrity check
D2-20  generate CASE 01-E entry boundary
D2-21  one D2 implementation/evidence commit + one push to case-01
D2-22  STOP
→ CHATGPT EXTERNAL REVIEW
```

DeepSeek must not start CASE 01-E.

---

# 19. D2 STOP Conditions

STOP immediately if:

```text
S-D2-01 D2 explicit authorization missing
S-D2-02 Agent must equal Capability for execution to work
S-D2-03 Platform Registry must become admission authority
S-D2-04 Platform Core / public contract change is required
S-D2-05 Runtime change is required
S-D2-06 Runtime Adapter code change is required
S-D2-07 Enterprise extension code change is required
S-D2-08 BREA professional behavior / FN / SEAM / OBL must be redesigned
S-D2-09 governance.agent requires two competing Invocation authority locations
S-D2-10 Agent identity cannot remain separate from execution capability identity
S-D2-11 Admission status would be self-authorized by DeepSeek/tests/Registry
S-D2-12 implementation fingerprint cannot deterministically identify bound Candidate
S-D2-13 Formation Evidence cannot be resolved
S-D2-14 Candidate regression fails
S-D2-15 provenance chain cannot link exact admitted Agent/version/binding to execution evidence
S-D2-16 raw corpus would need to be committed
S-D2-17 unauthorized path mutation occurs
S-D2-18 main drift occurs
```

On architecture blocker:

```text
record smallest blocker
DO NOT PATCH CORE
DO NOT PATCH RUNTIME
STOP → ARCHITECTURE REVIEW
```

---

# 20. D2 Acceptance Criteria

External D2 PASS requires all:

```text
AC-D2-01 explicit User authorization exists and is referenced
AC-D2-02 exact Agent identity/version are frozen
AC-D2-03 execution capability identity/version are separate and frozen
AC-D2-04 Governed Definition SHA exact
AC-D2-05 Formation Evidence exact and resolvable
AC-D2-06 deterministic implementation fingerprint recorded
AC-D2-07 Candidate unchanged / regression 15/15
AC-D2-08 T-C01 / T-C02 / T-C03 baseline still pass
AC-D2-09 Admission Record is Case-local and evidence-backed
AC-D2-10 Admission != Registry.register preserved
AC-D2-11 successful Binding exists only for ADMITTED Agent
AC-D2-12 governance.agent canonical source = Invocation.extensions only
AC-D2-13 context.extensions does not duplicate governance.agent
AC-D2-14 governance.agent is validated against Admission + Binding
AC-D2-15 conflicting Trace attribution fails closed
AC-D2-16 existing Platform Validator / RuntimeAdapter / Runtime are reused unchanged
AC-D2-17 Platform-bound T-C01 passes with exact Agent attribution
AC-D2-18 Platform-bound T-C02 passes with exact Agent attribution
AC-D2-19 Platform-bound T-C03 preserves professional fail-closed behavior + exact attribution
AC-D2-20 Result / Trace / Artifact provenance resolves to exact admitted Agent + binding
AC-D2-21 Domain meaning remains outside Platform / Runtime
AC-D2-22 Enterprise remains attribution/context, not Runtime meaning
AC-D2-23 raw corpus not committed
AC-D2-24 Platform Core unchanged
AC-D2-25 Runtime / Runtime Adapter unchanged
AC-D2-26 main unchanged
AC-D2-27 no generic Agent Platform capability claimed
AC-D2-28 CASE 01-E not started
```

---

# 21. D2 Verdict Model

DeepSeek does not close D2.

It reports one:

```text
READY FOR D2 EXTERNAL REVIEW

ADMISSION REJECTED — EVIDENCE/GATE FAILURE

ARCHITECTURE REVIEW REQUIRED

IMPLEMENTATION FAILURE / TARGETED REPAIR CANDIDATE
```

ChatGPT external review then decides:

```text
A. EVIDENCE-BACKED PASS / CLOSED
B. TARGETED REPAIR
C. ARCHITECTURE REVIEW REQUIRED
D. FAIL
```

---

# 22. Publication Rule

Current authorization state:

```text
D2 STAGE SPEC
ACCEPTED

D2 EXECUTION
NOT AUTHORIZED YET
```

After explicit User authorization, DeepSeek may publish:

```text
ONE D2 implementation + evidence commit
+
ONE push to case-01
+
STOP
```

No intermediate push.

No PR to main.

No post-push repair without new authorization.

The Stage Spec / authorization governance commits authored by Stage authority are separate from DeepSeek's one authorized D2 implementation publication.

---

# 23. Product Mainline Preservation

D2 is not professional completion.

After D2, BREA is expected to become:

```text
FORMATION-PROVEN
+
LOCALLY ADMITTED
+
EXECUTION-BOUND
+
TRACEABLE THROUGH CATALYST
```

This still does not mean:

```text
complete production-ready Building Regulation Agent
```

CASE 01-E remains responsible for continuing the real product mainline, including only when separately authorized and evidence-driven:

```text
broader local regulation retrieval
Web fallback
verified / official source strategy
local-vs-Web evidence labeling
validated URLs
RAG / LLM / Loop / Memory where justified
multi-turn interaction
frontend / backend completion
broader professional coverage
real professional evaluation
```

D0 recovered product intent remains useful but not exhaustive.

---

# 24. CASE 01-E Entry Boundary Requirement

D2 must generate:

```text
review/CASE_01_E_ENTRY_BOUNDARY_V0.1.md
```

It must state at minimum:

```text
D2 final local Agent maturity
admission/binding/provenance evidence produced
what current BREA can actually do
what product capabilities remain partial / missing
which D0 recovered intent remains relevant
which Domain / Enterprise issues remain unresolved
what Platform gaps gained new Case evidence
what must NOT be generalized yet
recommended 01-E first professional-completion slice
CASE 01-E authorization = NO
```

D2 may recommend the next slice.

It may not start it.

---

# 25. Required D2 Final Report

DeepSeek must return:

```text
D2 STATUS
READY FOR EXTERNAL REVIEW / REJECTED / ARCHITECTURE REVIEW REQUIRED / IMPLEMENTATION FAILURE

CASE-01 HEAD INPUT
<sha>

CATALYST MAIN
5874be1130e8867082880fcd63f659fc909d9efd

D2 AUTHORIZATION REF
<file / commit>

GOVERNED AGENT
case-01.brea @ 0.1-candidate

EXECUTION CAPABILITY
case-01.brea.execute @ 0.1

AGENT == CAPABILITY
NO

DEFINITION SHA
PASS / FAIL

FORMATION EVIDENCE
PASS / FAIL

IMPLEMENTATION FINGERPRINT
<candidate_tree_sha256>
<builder_output_manifest_sha256>

CANDIDATE REGRESSION
15/15 PASS / FAIL

T-C01 BASELINE
PASS / FAIL

T-C02 BASELINE
PASS / FAIL

T-C03 BASELINE
PASS / FAIL

ADMISSION STATUS
ADMITTED / REJECTED

ADMISSION AUTHORITY
User explicit D2 authorization ref

BINDING STATUS
BOUND / NOT BOUND

governance.agent CANONICAL LOCATION
Invocation.extensions

D2 TESTS
N/N PASS

PLATFORM-BOUND T-C01
PASS / FAIL

PLATFORM-BOUND T-C02
PASS / FAIL

PLATFORM-BOUND T-C03
PASS / FAIL

PROVENANCE CHAIN
PASS / FAIL

RAW CORPUS COMMITTED
NO / YES

UNAUTHORIZED PATH CHANGES
0 / N

PLATFORM CORE CHANGE
NO / YES

RUNTIME / ADAPTER CHANGE
NO / YES

MAIN
UNCHANGED / CHANGED

PLATFORM GAP UPDATE
summary

CASE 01-E ENTRY BOUNDARY
GENERATED / NOT GENERATED

D2 COMMIT
<sha or NONE>

CASE 01-E
NOT AUTHORIZED

FINAL
READY FOR D2 EXTERNAL REVIEW
```

STOP.

---

# 26. Final Authorization State

```text
CASE 01-D / D0
EVIDENCE-BACKED PASS / CLOSED

CASE 01-D / D1
EVIDENCE-BACKED PASS / CLOSED

CASE 01-D / D2
STAGE SPEC ACCEPTED
EXECUTION REQUIRES EXPLICIT USER AUTHORIZATION

CASE 01-E
NOT AUTHORIZED

PLATFORM CORE CHANGE
FORBIDDEN

RUNTIME / RUNTIME ADAPTER CHANGE
FORBIDDEN

CATALYST MAIN CHANGE
FORBIDDEN
```

# **D2 SPEC VERDICT — ACCEPTED / READY FOR EXPLICIT EXECUTION AUTHORIZATION**
