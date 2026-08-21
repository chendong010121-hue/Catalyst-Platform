# CASE 01-D — D1 ADMISSION ARCHITECTURE COMPATIBILITY V0.1
## STAGE SPEC — ARCHITECTURE REVIEW ONLY
### GOVERNED AGENT ADMISSION · EXECUTION BINDING · PLATFORM COMPATIBILITY · CASE ↔ PLATFORM CO-EVOLUTION

> **Project:** Catalyst  
> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)  
> **Branch:** `case-01`  
> **Parent Stage:** CASE 01-C — `EVIDENCE-BACKED PASS / CLOSED`  
> **CASE 01-C final closure commit:** `dd491a73a5dc59227a7c93c7962e9ba23ea04efa`  
> **CASE 01-D D0 implementation commit:** `75a23c53c9ed1913f0d7496b8ce29d523b3db82a`  
> **D0 external review:** `EVIDENCE-BACKED PASS / CLOSED AS CASE 01 METHOD PROOF`  
> **Catalyst accepted `main`:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **Architecture / Stage authority + external auditor:** ChatGPT  
> **Execution / analysis author:** DeepSeek  
> **Product / Release authority:** User  
> **D1 status:** **STAGE SPEC ACCEPTED / EXECUTION REQUIRES EXPLICIT USER AUTHORIZATION**  
> **D2 Local Admission / Binding Proof:** **NOT AUTHORIZED**  
> **CASE 01-E:** **NOT AUTHORIZED**  
> **Catalyst `main` mutation:** **FORBIDDEN**

---

# 0. Stage Thesis

CASE 01-D remains the accepted next mainline:

```text
01-A  UNDERSTAND LEGACY                         CLOSED
01-B  DEFINE GOVERNED AGENT                     CLOSED
01-C  GOVERNED LOCAL FORMATION                  CLOSED
01-D
  D0  BLIND AGENT UNDERSTANDING METHOD PROOF    CLOSED
  D1  ADMISSION ARCHITECTURE COMPATIBILITY      NEXT
  D2  LOCAL ADMISSION / BINDING PROOF           LATER
01-E  PROFESSIONAL AGENT COMPLETION             LATER
01-F  PROFESSIONAL VALIDATION / EVOLUTION       LATER
```

D1 is **not an implementation stage**.

Its job is to answer:

> **Can the already formation-proven BREA v0.1 Candidate enter Catalyst's governance + execution boundary using the current architecture without collapsing Agent into Capability, pushing Domain/Enterprise meaning into lower layers, or prematurely expanding Platform Core / Runtime?**

D1 must discover the minimum valid architecture before D2 writes any Admission / Binding code.

---

# 1. D0 Closure Is an Input, Not a New Mainline

The D0 external review accepted:

```text
D0 BLIND AGENT UNDERSTANDING PROOF
EVIDENCE-BACKED PASS

Reusable Catalyst Understanding service/API/Agent
NOT YET PROVEN

Cross-Agent/model portability
NOT YET PROVEN

D1
ELIGIBLE FOR NEXT AUTHORIZATION
```

D0 therefore remains:

```text
CASE 01 METHOD PROOF
LOCAL / CASE-EVIDENCED
NOT PLATFORM CORE
NOT A GENERIC SERVICE
```

Do not continue Agent Understanding work in D1.

Do not build:

```text
AgentUnderstandingService
Generic Agent Intake API
Repository Understanding Platform
```

unless a later independent Stage authorizes it.

---

# 2. D0 Findings That Must Carry Forward

D1 must preserve three external-audit findings.

## 2.1 Product intent is useful but not exhaustive

D0 recovered the core Legacy product intent, but UC-02 remains:

```text
PARTIAL
```

In particular, broad:

```text
local-first
+
network supplement
```

was recovered, but all fine-grained historical Web evidence UX / trust requirements were not proven exhaustive.

Therefore:

```text
RECOVERED_PRODUCT_INTENT_BASELINE
= useful evidence
!= exhaustive final product requirements
```

D1 must not use D0 product intent to retroactively redefine accepted BREA formation contracts.

## 2.2 Enterprise recovery remains partial

UC-06 remains:

```text
PARTIAL
```

Project attribution / isolation is clearly Enterprise-like.

But:

```text
local-first evidence strategy
network fallback
source trust
```

must not be automatically classified as Enterprise semantics.

They may belong to:

```text
Domain
Agent Behavior
Governance
Enterprise override / policy
```

depending on evidence.

D1 must classify by responsibility, not by where a rule happened to appear in Legacy files.

## 2.3 Blind benchmark procedure is good but not fully independently proven

UC-10 is:

```text
PROCEDURALLY SUPPORTED PASS
```

because blind and comparison artifacts were published in one commit.

This does not block D1.

For future second-Agent Understanding proof, the blind snapshot should be remotely committed before known-answer comparison.

Do not repair D0 in D1.

---

# 3. D1 Is an Architecture Compatibility Review

D1 must inspect the already accepted architecture and answer:

```text
What does BREA need in order to be admitted as a governed Agent version?

Which of those needs already have a valid owner?

Which existing Catalyst contracts / seams can be reused as-is?

Which needs can remain Case-local?

Which need an Extension?

Which belong to Adapter / Binding?

Which are true Platform gaps?

Does any requirement force Platform Core or Runtime change?

Can execution be attributed to an exact admitted Agent version?

Can this be done without Agent == Capability?
```

D1 must produce evidence-backed compatibility decisions.

No production architecture is to be predicted.

---

# 4. Hard Architectural Invariants

These are not hypotheses.

They are binding D1 rules.

## I-01 — Agent is the primary governed / delivery unit

```text
Whole Agent
= primary governed subject / delivery unit
```

Its internal:

```text
RAG
Memory
LLM
Tool
Skill
Retriever
Parser
Sub-agent
Component
```

may be independently designed, tested, versioned, replaced or governed where justified.

But internal modularity does not automatically make every component a Platform Resource.

## I-02 — Agent != Capability

BREA must not be collapsed into a `CapabilityDescriptor` merely because current Platform Standard is capability-centric.

Possible relationships may include:

```text
Agent exposes / uses / orchestrates Capability
Agent execution is adapted through existing capability-compatible mechanics
```

but:

```text
Agent identity
!= Capability identity
```

unless later evidence explicitly justifies a new accepted model.

## I-03 — Admission != Registry registration

```text
Registry.register()
!= governance admission
```

Admission must represent an evidence-backed decision about an exact governed Agent version.

## I-04 — Admission != runnable

A Candidate being executable does not prove it is admitted.

Formation proof, admission decision and execution ability are different facts.

## I-05 — Binding != Agent identity

```text
Agent identity / version
```

must survive replacement of implementation HOW when governance permits.

Binding connects an admitted governed subject to an execution implementation/path.

It does not define what the Agent means.

## I-06 — Domain and Enterprise remain first-class but separate

```text
Domain
= professional meaning

Enterprise
= organization-specific meaning
```

Neither may be silently pushed into:

```text
Platform Core
Runtime
```

## I-07 — Runtime stays execution infrastructure

Runtime must remain:

```text
domain-free
enterprise-free
replaceable
```

D1 may inspect Runtime, but may not assign Agent governance meaning to Runtime.

## I-08 — Extension First. Core Promotion Later.

A local governance need does not become Platform Standard merely because CASE 01 needs it.

Use the order:

```text
existing contract
→ Case-local
→ Extension
→ Adapter-local
→ Evidence
→ repeated cross-boundary gap?
→ Platform review
```

## I-09 — Small constitutional core

D1 must not design a thick future Agent object model.

Do not pre-build:

```text
Agent Catalog
Agent Control Plane
Generic Agent Registry
IAM
RBAC
Approval Engine
Policy Engine
Agent Marketplace
Universal Manifest Framework
```

## I-10 — Everything is replaceable. Nothing is casually replaceable.

Admission / Binding must preserve:

```text
identity
evidence
responsibility
observable obligations
migration / replacement trace
```

without granting permanent privilege to one implementation.

---

# 5. Governed Subject Under Review

D1 reviews the already accepted BREA Candidate.

Current governing references include:

```text
Agent:
Building Regulation Evidence Agent (BREA)

Candidate:
BREA v0.1-candidate

Professional purpose:
Provide reliable, applicable, traceable building-regulation evidence
for architectural / preliminary-design work and fail closed when
reliable evidence is unavailable.

Formation:
CASE 01-C — EVIDENCE-BACKED PASS / CLOSED

Functions:
FN-01..FN-11

Governed seams:
SEAM-01 Professional Project Facts
SEAM-02 Regulation Applicability
SEAM-03 Regulation Evidence

Obligations:
OBL-01..OBL-06
```

D1 may reference these accepted facts.

D1 may not redesign them.

If Admission cannot be modeled without changing:

```text
Agent identity
Professional purpose
FN-01..FN-11
SEAM-01..03
OBL-01..06
```

then:

```text
STOP
→ ARCHITECTURE / DESIGN BLOCKER
```

Do not repair CASE 01-B/C inside D1.

---

# 6. D1 Primary Architecture Questions

D1 must explicitly answer at least the following.

## Q-01 — What exact object is admitted?

Candidate hypotheses to evaluate:

```text
Agent identity
+
Agent version
+
accepted governed definition
+
formation evidence
+
bound implementation fingerprint
```

Do not assume the answer is a file, class, manifest or registry entry.

State the smallest evidence-backed governed subject.

## Q-02 — What is the minimum Agent Admission Record?

Evaluate which semantics are actually required for CASE 01.

Candidate fields may include — as hypotheses only:

```text
agent_id
agent_version
owner_ref
professional_purpose_ref
governed_definition_ref / SHA
formation_evidence_refs
obligations_ref
governed_seams_ref
implementation_fingerprint_ref
enterprise_context_ref
corpus / protected-input boundary ref
admission_status
admission_decision_ref
```

D1 must classify every field:

```text
REQUIRED NOW
REFERENCE ONLY
DERIVED
DEFER
REJECT
```

Do not freeze a universal schema.

## Q-03 — What evidence permits admission?

Determine the minimum admission evidence needed for BREA v0.1.

Likely evidence candidates include:

```text
accepted Governed Definition
exact Definition SHA
CASE 01-C formation closure
Builder → Candidate provenance
FN / SEAM / OBL conformance
whole-Agent formation tests
raw corpus boundary / admission reference
owner / acceptance authority
implementation fingerprint
```

D1 must separate:

```text
Formation Evidence
from
Admission Decision
```

Formation evidence informs admission.

It does not self-authorize admission.

## Q-04 — What is an implementation fingerprint?

D1 must determine the smallest deterministic way to identify the exact implementation being bound.

Candidate approaches may include:

```text
Git commit / tree SHA
candidate directory manifest SHA
artifact manifest hash
source bundle hash
```

Do not build a production signing / supply-chain system.

The requirement is only:

> An admitted Agent version must not silently bind to a different implementation.

## Q-05 — What is an Execution Binding?

Define the Case-level relationship:

```text
admitted governed Agent version
→ specific implementation identity
→ execution entry
→ existing Platform-compatible path
```

D1 must clarify what Binding owns and what it does not own.

Binding may own:

```text
compatibility / translation
implementation target
version relationship
execution entry reference
```

Binding must not own:

```text
professional Domain meaning
Enterprise policy
Agent product purpose
Runtime execution semantics
```

## Q-06 — Can current Platform Standard execute BREA without Agent == Capability?

Inspect the actual current executable boundary.

Determine whether D2 can reuse:

```text
Standard Invocation
Validator
Runtime Adapter
Runtime
Standard Result
ArtifactRef
Trace
Extension mechanism
```

while keeping:

```text
Agent identity
separate from
Capability identity
```

D1 must not manufacture a fake answer.

Possible verdicts:

```text
YES — existing path is sufficient
PARTIAL — Case-local wrapper / attribution is needed
NO — architecture gap
```

## Q-07 — How does exact Agent attribution travel through execution?

Evaluate the smallest non-Core mechanism capable of preserving:

```text
agent_id
agent_version
admission_ref
binding_ref
```

through the execution evidence path.

Candidate location to inspect first:

```text
governance.* Extension
```

But this is a hypothesis, not a pre-approved field model.

If existing Extension can carry the semantics without redefining Platform Core:

```text
PREFER EXTENSION
```

## Q-08 — What does Adapter need to know?

Determine whether the existing Runtime Adapter can stay generic.

Possible outcomes:

```text
REUSE AS-IS
CASE-LOCAL BINDING WRAPPER
CASE-LOCAL ADAPTER ADAPTATION
TRUE ADAPTER GAP
```

Do not turn Adapter into Agent Governance, Workflow, Policy or Enterprise owner.

## Q-09 — Does Runtime need any change?

Preferred result:

```text
NO
```

But D1 must prove this from the current execution path.

If Agent admission requires Runtime to understand:

```text
Domain meaning
Enterprise meaning
governance admission semantics
```

then the proposed architecture is suspect.

STOP before any Runtime change.

## Q-10 — What is the minimum Enterprise participation?

D1 must preserve Enterprise as a first-class semantic dimension while keeping the Pilot minimal.

Evaluate only current proven needs such as:

```text
organization_ref
owner / product-release authority
project_ref
evaluation / acceptance authority
Agent ownership
```

Do not implement:

```text
IAM
RBAC
approval workflow
source trust policy platform
network policy platform
retention platform
```

merely because they are foreseeable.

## Q-11 — What remains Domain-owned?

Professional meaning remains in Domain / Agent professional semantics.

D1 must confirm Admission / Binding does not become owner of:

```text
regulation applicability
professional facts
source authority meaning
numeric safety meaning
professional uncertainty
```

## Q-12 — What must D2 prove?

D1 must end with a precise D2 evidence boundary.

No vague:

```text
"implement admission"
```

D2 entry must identify:

```text
minimum local objects
exact current seams to reuse
required fail-closed tests
what may be written
what must remain untouched
what result proves admission + binding
```

---

# 7. Compatibility Classification Model

Every D1 need must be classified using exactly one primary disposition:

```text
REUSE-AS-IS
CASE-LOCAL
EXTENSION
ADAPTER-LOCAL
PLATFORM-GAP
RUNTIME-GAP
DEFER
REJECT
```

Definitions:

```text
REUSE-AS-IS
current accepted Catalyst mechanism already owns the need

CASE-LOCAL
needed for CASE 01 but not yet justified as reusable Platform semantics

EXTENSION
can be expressed through the existing extension boundary without Core change

ADAPTER-LOCAL
compatibility / translation / implementation binding belongs at a Case-local Adapter seam

PLATFORM-GAP
current stable Platform public boundary cannot express a necessary cross-boundary responsibility

RUNTIME-GAP
current Runtime execution semantics cannot provide a necessary execution behavior without redesign

DEFER
real but not required for D2

REJECT
predicted / misplaced / unnecessary concept
```

No field may be promoted to Platform merely because `CASE-LOCAL` feels inconvenient.

---

# 8. Required Admission Need Matrix

Create:

```text
ADMISSION_NEED_COMPATIBILITY_MATRIX_V0.1.md
```

At minimum include:

| Need | Governed meaning | Default owner | Current Catalyst evidence | Disposition | D2 required? | Gap? |
|---|---|---|---|---|---|---|
| Agent identity | exact governed Agent | Agent governance | inspect | classify | yes/no | yes/no |
| Agent version | exact version | Agent governance | inspect | classify | yes/no | yes/no |
| owner | accountability | Enterprise/Governance | inspect | classify | yes/no | yes/no |
| definition SHA | definition identity | Governance evidence | inspect | classify | yes/no | yes/no |
| formation evidence | formation proof | Governance evidence | inspect | classify | yes/no | yes/no |
| implementation fingerprint | bound implementation | Binding | inspect | classify | yes/no | yes/no |
| admission status | admission decision | Governance | inspect | classify | yes/no | yes/no |
| execution binding | version → implementation | Binding/Adapter | inspect | classify | yes/no | yes/no |
| Agent attribution | execution provenance | Governance/Extension | inspect | classify | yes/no | yes/no |
| Platform invocation | public execution path | Platform Standard | inspect | classify | yes/no | yes/no |
| Runtime execution | lifecycle / certainty | Runtime | inspect | classify | yes/no | yes/no |
| Enterprise attribution | organization context | Enterprise | inspect | classify | yes/no | yes/no |
| Domain semantics | professional meaning | Domain | inspect | classify | yes/no | yes/no |
| corpus boundary | protected input | Agent/Domain/Governance | inspect | classify | yes/no | yes/no |

Additional rows are allowed only when evidence shows a real D2 need.

---

# 9. Required Current-System Inspection

D1 must inspect current accepted `main` at:

```text
5874be1130e8867082880fcd63f659fc909d9efd
```

At minimum inspect the actual responsibility / behavior of:

```text
README.md
ARCHITECTURE.md
PLATFORM_STANDARD_CORE_V0.1.md
platform_standard/**
agent_runtime/**
enterprise_extensions/**
examples/platform_standard_reference.py
tests/test_platform_standard_core.py
tests/test_capability_contract_conformance_pilot.py
tests/test_enterprise_extension_pilot.py
current CI workflow
active Governing Baseline
```

Inspect only what is necessary to answer D1.

Do not modify them.

Record exact:

```text
file path
main SHA
relevant symbol / section
why it supports the D1 decision
```

---

# 10. Required CASE 01 Inputs

D1 must read accepted Case evidence as architecture inputs:

```text
CASE 01-B accepted Governed Agent Definition
CASE 01-B Builder-consumable Definition
CASE 01-C final formation outputs
CASE 01-C final closure / review evidence
CASE 01-D D0 outputs
D0 external-audit verdict / findings as provided by Stage authority
```

D0 outputs are only used for:

```text
context
product-mainline preservation
Domain / Enterprise caution
known future completion relevance
```

They are not authority to rewrite accepted BREA formation contracts.

---

# 11. D1 Required Output Package

Write only under:

```text
case-01/01-d-governed-agent-admission-binding/
d1-admission-architecture-compatibility/
```

Required outputs:

```text
D1_ARCHITECTURE_COMPATIBILITY_REVIEW_V0.1.md

ADMISSION_NEED_COMPATIBILITY_MATRIX_V0.1.md

MINIMUM_AGENT_ADMISSION_RECORD_CANDIDATE_V0.1.md

EXECUTION_BINDING_MODEL_CANDIDATE_V0.1.md

PLATFORM_EXECUTION_REUSE_MAP_V0.1.md

DOMAIN_ENTERPRISE_RESPONSIBILITY_CHECK_V0.1.md

PLATFORM_GAP_REGISTER_D1_V0.1.md

D1_EVIDENCE_INDEX_V0.1.md

CASE_01_D2_ENTRY_BOUNDARY_V0.1.md
```

Optional:

```text
diagrams / small static analysis notes
```

No implementation package is authorized.

---

# 12. Minimum Agent Admission Record Candidate — Required Analysis

`MINIMUM_AGENT_ADMISSION_RECORD_CANDIDATE_V0.1.md` must not pretend to be a Platform Standard.

It must contain:

```text
Candidate purpose
Candidate field list
Why each field exists
Owner of each field
Source of truth
Required / reference / derived / deferred status
What is intentionally excluded
What would invalidate the record
How version replacement would affect it
```

It must explicitly state:

```text
CASE-LOCAL CANDIDATE MODEL
NOT PLATFORM CORE
NOT GENERIC AGENT MANIFEST
```

No future-complete Agent object model.

---

# 13. Execution Binding Model Candidate — Required Analysis

`EXECUTION_BINDING_MODEL_CANDIDATE_V0.1.md` must answer:

```text
What is being bound?
What implementation is being bound?
How is implementation identity frozen?
What execution entry is used?
Which Platform seam is reused?
Which Adapter seam is reused?
How is Agent attribution preserved?
How does a mismatch fail closed?
What does Binding explicitly NOT own?
```

The model should support future replacement conceptually:

```text
Agent version / governed identity
        ↓
binding
        ↓
Implementation A

later, when separately governed:

Agent version / next version
        ↓
new binding
        ↓
Implementation B
```

Do not implement Candidate N+1 in D1.

---

# 14. Platform Execution Reuse Map

`PLATFORM_EXECUTION_REUSE_MAP_V0.1.md` must map:

```text
BREA whole-Agent execution need
```

against current:

```text
Capability Descriptor
Standard Invocation
Validator
Extension
Runtime Adapter
Runtime
Standard Result
ArtifactRef
Trace
```

For each, state:

```text
can reuse?
what meaning is carried?
what meaning must stay outside?
would reuse accidentally imply Agent == Capability?
D2 change required?
```

The goal is to maximize reuse while preserving correct responsibility.

---

# 15. Domain / Enterprise Responsibility Check

`DOMAIN_ENTERPRISE_RESPONSIBILITY_CHECK_V0.1.md` must include at least:

```text
Agent ownership
project attribution
organization attribution
acceptance authority

professional purpose
professional facts
applicability
evidence semantics
numeric safety

network fallback
source trust
human review
memory / retention
```

For each classify:

```text
DOMAIN
ENTERPRISE
AGENT BEHAVIOR
GOVERNANCE
IMPLEMENTATION HOW
COMPOSED / MULTI-OWNER
UNRESOLVED
```

Important:

D0 UC-06 is PARTIAL.

Therefore D1 must preserve uncertainty where current evidence cannot prove a single owner.

Do not force every item into exactly one semantic layer when composition is the accurate result.

---

# 16. Platform Gap Register

`PLATFORM_GAP_REGISTER_D1_V0.1.md` must distinguish:

```text
REAL D2 BLOCKER
CASE-LOCAL NEED
GENERALIZATION CANDIDATE
DEFERRED FUTURE NEED
REJECTED PREMATURE CONCEPT
```

For every gap record:

```text
gap_id
need
evidence
current owner
why current contract is insufficient
smallest local alternative
does D2 require it?
does it require Platform review?
```

A new gap does not authorize implementation.

---

# 17. D1 Preflight

Before analysis:

```text
P-D1-01 branch == case-01
P-D1-02 case-01 HEAD includes D0 commit 75a23c53...
P-D1-03 CASE 01-C closure remains present
P-D1-04 accepted main is still 5874be1130...
P-D1-05 main has no drift relative to accepted baseline
P-D1-06 D0 external verdict is PASS / CLOSED AS CASE 01 METHOD PROOF
P-D1-07 no unresolved local work would be overwritten
P-D1-08 no D1 implementation already exists
```

If unknown user work exists:

```text
STOP
do not auto-clean
```

---

# 18. D1 Execution Sequence

When separately authorized:

```text
D1-0   preflight
D1-1   freeze current Case / main SHAs in evidence index
D1-2   inventory current Admission needs from BREA formation evidence
D1-3   inspect current Platform Standard / Extension / Adapter / Runtime responsibility
D1-4   build Admission Need Compatibility Matrix
D1-5   define minimum Case-local Admission Record candidate
D1-6   define minimum Execution Binding candidate
D1-7   test Agent != Capability compatibility against current execution path
D1-8   test governance attribution via existing Extension / Trace mechanisms conceptually
D1-9   verify Adapter can remain compatibility owner rather than Agent governance owner
D1-10  verify Runtime can remain unchanged / semantic-free
D1-11  run Domain / Enterprise responsibility check
D1-12  classify gaps
D1-13  choose D1 verdict
D1-14  define exact D2 entry boundary
D1-15  contamination / unauthorized-change check
D1-16  one docs-only D1 commit + one push to case-01
D1-17  STOP
→ CHATGPT EXTERNAL REVIEW
```

No D2 implementation follows automatically.

---

# 19. D1 Evidence Requirements

D1 evidence must be sufficient for an external reviewer to verify:

```text
what current mechanism was inspected
what responsibility it currently owns
why D1 believes it can / cannot be reused
what Case-local meaning remains outside Core
where Agent attribution would travel
why Runtime does / does not need change
why Agent has not been collapsed into Capability
```

Assertions such as:

```text
"Extension can handle it"
"Adapter already supports it"
"Runtime does not need change"
```

without exact code / contract evidence are insufficient.

---

# 20. D1 Forbidden Actions

D1 may not modify implementation.

Forbidden:

```text
Catalyst main
Platform Core
Platform Standard code
Runtime
Runtime Adapter code
Enterprise extension code
BREA candidate implementation
CASE 01-B/C accepted artifacts
Legacy Agent 2.0
raw regulation corpus
tests
CI
```

D1 may not create:

```text
Agent Registry implementation
Admission service
Binding service
Agent manifest SDK
Agent catalog
Control Plane
IAM / RBAC
Policy / Approval engine
generic Agent framework
generic Agent Understanding service
```

D1 is architecture review only.

---

# 21. D1 STOP Conditions

STOP / report blocker if any occur:

```text
S-D1-01 Agent must be equated to Capability to use current Platform
S-D1-02 Admission requires Platform Registry to become governance authority
S-D1-03 Agent identity can only be preserved by adding Domain/Enterprise fields to Runtime
S-D1-04 Adapter must become owner of Agent professional/governance meaning
S-D1-05 current Platform public contract must be modified to make D2 possible
S-D1-06 Runtime semantics must be modified to make D2 possible
S-D1-07 D1 requires redesign of accepted FN / SEAM / OBL / professional purpose
S-D1-08 D0 partial product intent is treated as exhaustive normative BREA definition
S-D1-09 D0 partial Enterprise classification is silently promoted to final Enterprise ownership
S-D1-10 a thick generic Agent Object Model is being designed
S-D1-11 implementation starts before D1 external review
S-D1-12 unauthorized repo / workspace mutation occurs
```

On STOP:

```text
record evidence
record smallest blocking responsibility
do not repair
do not change Platform / Runtime
return for Architecture Review
```

---

# 22. D1 Verdict Model

D1 exits as exactly one:

## A — PASS / D2 ELIGIBLE

```text
Current architecture can support D2
with REUSE-AS-IS / CASE-LOCAL / EXTENSION / ADAPTER-LOCAL only.
No Platform Core or Runtime change required.
```

## B — PASS WITH NON-BLOCKING GAP CANDIDATES

```text
D2 can proceed locally,
but one or more recurring/generalizable gaps are recorded for later review.
```

No gap is implemented in D1.

## C — ARCHITECTURE REVIEW REQUIRED

```text
D2 cannot be performed without changing
Platform Core / Platform public contract / Runtime
or violating accepted responsibility boundaries.
```

STOP.

## D — INSUFFICIENT EVIDENCE

```text
Current repository / evidence does not allow a defensible compatibility decision.
```

STOP and request the smallest missing evidence.

---

# 23. D1 Acceptance Criteria

D1 can receive external PASS only if all are true:

```text
AC-D1-01 current main / Case SHAs are frozen and cited
AC-D1-02 all minimum admission needs are classified
AC-D1-03 exact governed subject is stated
AC-D1-04 minimum Admission Record candidate is bounded and Case-local
AC-D1-05 minimum Binding candidate is bounded and Case-local
AC-D1-06 Agent != Capability is preserved
AC-D1-07 Admission != Registry.register is preserved
AC-D1-08 Binding != identity is preserved
AC-D1-09 current Platform execution seams are mapped with evidence
AC-D1-10 Agent attribution path is identified or explicitly blocked
AC-D1-11 Domain ownership remains outside Platform/Runtime
AC-D1-12 Enterprise remains first-class and not collapsed into a few Core fields
AC-D1-13 Adapter remains compatibility / translation owner only
AC-D1-14 Runtime remains domain-free / enterprise-free
AC-D1-15 all real gaps are recorded rather than silently solved
AC-D1-16 no Platform / Runtime / BREA implementation changed
AC-D1-17 D0 partial findings remain correctly scoped
AC-D1-18 D2 entry boundary is explicit
AC-D1-19 product mainline remains preserved for CASE 01-E
AC-D1-20 external review can reproduce the architecture decision from committed evidence
```

---

# 24. Product Mainline Preservation

D1 is not the stage that completes the professional Building Regulation Agent.

The product line remains:

```text
Legacy Agent 2.0
→ Understand
→ Governed Definition
→ Governed Formation
→ Admission / Binding
→ Professional Completion
→ Professional Validation
→ Bounded Evolution
```

D0 recovered useful original product intent.

That product-intent evidence must remain visible for CASE 01-E.

D1 must not consume professional-completion scope such as:

```text
complete local-first retrieval
Web fallback
official / verified Web source rules
local-vs-Web evidence labeling
validated URL UX
LLM / RAG / Loop / Memory completion
multi-turn interaction
frontend / backend completion
broader regulation coverage
```

Those are future Case/product work when separately authorized.

This prevents governance work from replacing product delivery.

---

# 25. Enterprise Layer Preservation

Enterprise has not disappeared.

The accepted responsibility model remains:

```text
Agent / Workflow
      │
      ├──────────────┐
      ▼              ▼
    Domain       Enterprise
 professional   organization
   meaning        meaning
      └──────┬───────┘
             ▼
      Platform Standard
             ▼
          Adapter
             ▼
          Runtime
```

D1 must answer only the minimum Enterprise participation needed for current Admission.

Any future:

```text
source trust policy
network permission
human review policy
retention / memory policy
approved Agent policy
organizational workflow
```

remains architecturally legitimate but is not automatically required now.

Real need must pull it into a future Stage.

---

# 26. Platform Co-evolution Rule

D1 follows:

```text
Case Need
→ Responsibility
→ Existing Reference
→ Current Contract Compatibility
→ Local / Extension / Adapter candidate
→ Evidence
→ Generalization Gate
```

A Case gap does not automatically authorize Platform growth.

Only after repeated or structurally unavoidable evidence may a gap become:

```text
PLATFORM STANDARD REVIEW CANDIDATE
```

D1 is permitted to nominate candidates.

It is not permitted to promote them.

---

# 27. D2 Entry Boundary — Required Shape

`CASE_01_D2_ENTRY_BOUNDARY_V0.1.md` must state:

```text
D1 VERDICT
PASS / PASS WITH GAPS / BLOCKED

D2 PURPOSE
one sentence

GOVERNED SUBJECT
exact Agent + version

ADMISSION INPUTS
exact references

MINIMUM ADMISSION RECORD
fields / refs actually required

MINIMUM BINDING
what binds to what

PLATFORM SEAMS REUSED
exact current seams

CASE-LOCAL SEMANTICS
list

EXTENSIONS USED
list or NONE

ADAPTER-LOCAL WORK
list or NONE

PLATFORM CORE CHANGE
NONE or BLOCKER

RUNTIME CHANGE
NONE or BLOCKER

REQUIRED D2 TESTS
list

D2 ALLOWED WRITE PATHS
list

D2 FORBIDDEN PATHS
list

D2 STOP CONDITIONS
list

CASE 01-E
NOT AUTHORIZED
```

D1 does not authorize D2.

---

# 28. Publication Rule

Current state:

```text
D1 STAGE SPEC
ACCEPTED

D1 EXECUTION
NOT YET AUTHORIZED
```

After explicit user authorization, DeepSeek may perform D1 as a **docs / architecture-evidence-only** Stage.

Authorized publication after that explicit approval:

```text
one D1 analysis commit
+
one push to case-01
+
STOP
```

No intermediate pushes.

No D2 implementation.

No PR to `main`.

If post-push D1 repair is needed:

```text
STOP
→ new publication authorization required
```

---

# 29. Required D1 Final Report

When D1 is executed, DeepSeek must return:

```text
D1 STATUS
PASS / PASS WITH NON-BLOCKING GAPS / ARCHITECTURE REVIEW REQUIRED / INSUFFICIENT EVIDENCE

CASE-01 HEAD INPUT
<sha>

CATALYST MAIN
5874be1130e8867082880fcd63f659fc909d9efd

D0
EVIDENCE-BACKED PASS / CLOSED AS CASE 01 METHOD PROOF

GOVERNED SUBJECT
<exact statement>

ADMISSION NEEDS CLASSIFIED
N

REUSE-AS-IS
N

CASE-LOCAL
N

EXTENSION
N

ADAPTER-LOCAL
N

PLATFORM-GAP
N

RUNTIME-GAP
N

DEFER / REJECT
N

AGENT == CAPABILITY
NO

ADMISSION == REGISTRY REGISTER
NO

RUNTIME CHANGE REQUIRED
NO / YES + blocker

PLATFORM CORE CHANGE REQUIRED
NO / YES + blocker

AGENT ATTRIBUTION PATH
<summary>

ENTERPRISE PARTICIPATION
<summary>

DOMAIN PRESERVATION
PASS / FAIL

D2 ENTRY BOUNDARY
GENERATED / NOT GENERATED

D1 COMMIT
<sha or NONE>

MAIN
UNCHANGED / CHANGED

D2
NOT AUTHORIZED

CASE 01-E
NOT AUTHORIZED

FINAL
READY FOR D1 EXTERNAL REVIEW
or
ARCHITECTURE REVIEW REQUIRED
```

STOP.

---

# 30. Final Stage Authorization State

```text
CASE 01-D
ACTIVE

D0 AGENT UNDERSTANDING METHOD PROOF
EVIDENCE-BACKED PASS / CLOSED

D1 ADMISSION ARCHITECTURE COMPATIBILITY
STAGE SPEC ACCEPTED
EXECUTION REQUIRES EXPLICIT USER AUTHORIZATION

D2 LOCAL ADMISSION / BINDING PROOF
NOT AUTHORIZED

CASE 01-E PROFESSIONAL AGENT COMPLETION
NOT AUTHORIZED

CATALYST MAIN CHANGE
FORBIDDEN

PLATFORM CORE CHANGE
FORBIDDEN

RUNTIME CHANGE
FORBIDDEN
```

# **D1 SPEC VERDICT — ACCEPTED / READY FOR EXPLICIT EXECUTION AUTHORIZATION**
