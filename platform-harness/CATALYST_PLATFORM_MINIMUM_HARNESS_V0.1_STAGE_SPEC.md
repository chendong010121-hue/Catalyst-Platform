# CATALYST PLATFORM — MINIMUM HARNESS V0.1 STAGE SPEC

> **Stage Spec Version:** **V0.2**
> **Status:** STAGE SPEC — TARGETED STRUCTURAL REPAIR COMPLETE
> **Supersedes:** Stage Spec V0.1 at commit `6c9d4ef0fee74c91220db5b5f3018afd1b4058a7`
> **Implementation Authorization:** **NO**
> **Platform Integration Authorization:** **NO**
> **Branch:** `platform-harness`
> **Architecture Review:** `platform-harness/PLATFORM_HARNESS_CAPABILITY_ARCHITECTURE_REVIEW_V0.1.md`
> **Implementation Base:** must be the exact Stage-Spec commit named by a later Authorization Record
> **Purpose:** prove the smallest Catalyst-controlled Harness execution loop needed to perform one already-authorized bounded software-development task inside an isolated Workspace, using a replaceable model boundary, minimal development tools, approval and auditable evidence without duplicating or redefining the accepted Agent Runtime.

---

# 0. Stage Question

This Stage answers exactly one question:

> Can Catalyst Platform control a replaceable development Harness Session that reads an authorized task, operates only inside an isolated Workspace, uses a replaceable LLM boundary plus a minimal development-tool environment, makes one bounded code change, runs deterministic verification, records execution evidence, and returns a reviewable result without inheriting governance authority or re-implementing the accepted Agent Runtime?

This Stage does **not** attempt to prove:

```text
full Agent Builder
full Skill Builder
one-sentence Agent generation
multi-agent orchestration
self-improving Harness
Capability Registry
automatic capability replacement
Platform integration
production deployment
```

---

# 1. Architectural Position

Catalyst remains the Platform.

Harness is one replaceable Platform capability for **development / inspection / controlled evolution work**.

The accepted Runtime remains the replaceable execution infrastructure for already-formed Agent execution.

```text
CATALYST PLATFORM
        │
        ├── Governed Development Path
        │       ↓
        │   Harness Responsibility Contract
        │       ↓
        │   Harness V0.1 Candidate
        │
        └── Agent Execution Path
                ↓
            Runtime Adapter
                ↓
            Accepted Runtime
```

The Harness may reuse compatible lower-level neutral contracts or adapters where evidence supports reuse.
It must not become a second Agent Runtime by casually duplicating existing Runtime responsibilities.

The Stage must preserve:

```text
Catalyst authority > Harness execution
```

The Harness may execute an authorized task.
It may not create its own Stage, expand scope, admit a Candidate, merge branches, promote a Capability, or redefine Domain / Enterprise meaning.

---

# 2. Evidence Basis

The Stage is justified by repeated external-Harness work observed in:

```text
CASE 01
→ governed Agent construction / modification / deterministic verification / freeze evidence

CASE 02
→ external Agent inspection / decomposition / asset discovery / Catalyst-native reconstruction
```

PenguinHarness is a mechanism reference for:

```text
Session
Workspace
LLM boundary
Environment / tool boundary
approval callback
trace
small tool surface
```

Pinned research reference used by the Architecture Review:

```text
Prism-Shadow/penguin-harness
11d6d16efccd889557236b0f951683d8b350cd91
```

Penguin remains research evidence only and is not an implementation dependency or architecture authority.

## 2.1 Accepted Runtime evidence that constrains this Stage

Current Catalyst Runtime already owns:

```text
Agent Loop
Reasoner
ModelProvider seam
Capability execution
Session / state lifecycle
PendingExecution
execution certainty
reconciliation
cancellation / timeout
Runtime-local execution control
```

Its neutral contracts already include a provider-independent `ModelProvider` boundary.
Its `Capability` contract explicitly states that filesystem / sandbox / HTTP transport / credential store / LLM provider / telemetry infrastructure should not be forced into the Agent-facing Capability interface.

Therefore V0.1 must consciously distinguish:

```text
REUSE COMPATIBLE NEUTRAL CONTRACT
vs
NEW HARNESS-SPECIFIC RESPONSIBILITY
vs
ACCIDENTAL RUNTIME DUPLICATION
```

---

# 3. Mandatory Pre-Implementation Boundary Gate — H-00

Before writing the Harness execution loop, implementation must record one concise responsibility mapping for every overlapping concept below.

| Concept | Existing Runtime meaning | Harness V0.1 rule |
|---|---|---|
| Model provider | provider-neutral model request / response | **reuse first**; no parallel provider abstraction unless incompatibility is explicitly demonstrated |
| Reasoner / Agent loop | Agent decision lifecycle over Agent-facing Capabilities | **do not copy by default**; Harness development loop has a different task boundary |
| Runtime Session | durable Agent execution lifecycle / recovery identity | Harness Session is a distinct development-execution identity; do not silently alias semantics |
| Capability | Agent-facing executable ability | file / shell / test tools remain Harness Environment infrastructure; do not force them into Capability merely to reuse Runtime |
| Policy | pure Runtime action guardrail | Harness approval is an execution-authority callback / policy; do not claim it is the same semantic without evidence |
| Trace / history | Runtime Agent execution evidence | Harness trace is Stage-local development evidence; no generic Platform Trace standard is created |
| timeout / failure | Runtime execution-certainty semantics | reuse principles where applicable, but do not claim semantic equivalence without evidence |

Allowed experimental reuse in V0.1:

```text
existing neutral ModelProvider contract
existing provider adapter if compatible
small shared value types if genuinely neutral
```

Forbidden shortcut:

```text
wrapping the entire existing Runtime / AgentCore / CapabilityExecutor
and calling that the Harness without proving the responsibility fit
```

H-00 is an acceptance proof, not a request for a new architecture document.
It belongs in the integrated V0.1 Review / Results.

---

# 4. Stage Scope

V0.1 must implement only the minimum responsibilities required for the proof.

## 4.1 Required responsibilities

```text
HARNESS SESSION
- one development-execution identity
- one authorized task
- one bounded lifecycle
- explicitly distinct from Runtime Session semantics

WORKSPACE BOUNDARY
- explicit root
- read/write limited to authorized Workspace
- reject traversal / escape

MODEL ACCESS
- provider-neutral boundary
- existing ModelProvider is the first reuse candidate
- one concrete live adapter must prove the boundary can actually drive the Harness
- fake/scripted model is allowed for deterministic structural tests only

CONTEXT ASSEMBLY
- Stage/task instruction
- authorized Workspace state
- minimal tool descriptions
- no automatic ingestion of unrelated repository history

HARNESS ENVIRONMENT TOOLS
- bounded text read
- bounded Workspace-local write/edit
- bounded command execution
- deterministic test execution via command execution or thin wrapper
- these are development infrastructure, not automatically Agent Capabilities

APPROVAL BOUNDARY
- mutating / command actions require an approval policy supplied to the Session
- model cannot self-approve

EXECUTION TRACE
- model implementation identity
- tool call identity
- tool type
- target path / command summary
- approval decision
- result status
- test result
- final Stage result

RESULT / FAILURE
- explicit PASS / FAIL / BLOCKED semantics
- no silent success on missing verification
```

## 4.2 Optional only if implementation simplicity requires it

```text
small Harness-local message/event type
small tool registry
thin compatibility adapter around existing ModelProvider
```

These remain private HOW unless later evidence proves an independently stable seam.

---

# 5. Explicit Non-Scope

Do not implement in this Stage:

```text
Git commit
Git push
GitHub mutation
branch creation
PR creation
Agent admission
Skill marketplace
Capability database
Capability vector search
Capability comparison engine
Capability replacement engine
Domain engine
Enterprise policy engine
Runtime replacement
Runtime modification
Runtime Adapter modification
multi-user server
Web UI
Desktop UI
MCP framework
browser automation
subagent spawning
multi-agent planning
self-optimization
benchmark generation
automatic Stage generation
```

Git diff may be inspected by the external reviewer after the proof, but Harness V0.1 does not need to own Git mutation.

---

# 6. Construction Principle

V0.1 is not an Agent Builder.

It is a **governed development executor proof**.

The Harness receives a task already defined and authorized outside the Harness.

```text
AUTHORIZED TASK
        ↓
Harness Session
        ↓
inspect authorized files
        ↓
propose bounded change
        ↓
approval
        ↓
apply bounded change
        ↓
run deterministic verification
        ↓
if verification fails, one bounded repair may occur
        ↓
rerun verification
        ↓
record trace + final result
        ↓
STOP
```

The Harness must not decide what the next Stage should be.

---

# 7. Proof Fixture

The first proof should use a tiny Catalyst-relevant local fixture, not a generic Hello World and not a live Case 01 mutation.

Reason:

- a pure Hello World does not test governed development behavior;
- directly mutating active Case 01 before Harness isolation is proven creates unnecessary product risk.

## 7.1 Required fixture properties

The fixture must contain:

```text
one small implementation file
one deterministic test file
one explicit task instruction
one intentionally missing / incorrect bounded behavior
```

The authorized task should require a change small enough that the proof evaluates Harness mechanics rather than coding sophistication.

Example class of task:

```text
"Change a bounded function so a declared invalid input fails closed,
then run the supplied deterministic test. Do not modify any other behavior."
```

Do not encode building-regulation Domain semantics into the fixture.
Do not reuse Case 01 implementation code unless separately authorized later.

---

# 8. Required Proofs

## H-00 — Runtime / Harness Responsibility Separation

PASS requires the integrated result to show that V0.1 consciously reused, separated or rejected each overlapping Runtime concept in Section 3.

No accidental second Runtime may be presented as Harness architecture.

## H-01 — Session Identity

One run has a stable Harness Session id and records:

```text
session_id
task_id
workspace_root
model implementation identity
start / finish status
```

PASS requires the final result and trace to bind to the same Session.

## H-02 — Workspace Isolation

The Harness may read/write only inside the authorized Workspace.

Required negative checks:

```text
../ traversal rejected
absolute path outside Workspace rejected
symlink escape rejected where applicable to implementation
```

PASS requires no protected repository mutation outside the fixture.

## H-03 — Replaceable Model Boundary + Live Invocation

Harness task logic must depend on a provider-neutral model boundary rather than vendor SDK behavior.

Rules:

```text
existing Catalyst ModelProvider contract = first reuse candidate
scripted/fake model = allowed for deterministic unit / boundary tests
at least one live LLM invocation = required for final Stage PASS
```

The live proof may use one concrete configured provider, but:

```text
provider identity must be observable
provider-specific code must remain adapter-local
no provider receives architectural authority
```

If credentials / external configuration are unavailable, the Stage may reach structural success but final verdict must remain `TARGETED_REPAIR` / `BLOCKED`, not `PASS`.

## H-04 — Minimal Tool Boundary

Only the development tools required for the proof are exposed.

Expected minimum:

```text
read
write/edit
command/test
```

PASS requires:

```text
tools are Workspace-bound
file/shell/test are not mislabeled as Agent Capabilities merely for reuse
model does not gain arbitrary repository or host mutation authority
```

## H-05 — Approval Enforcement

At least one mutating action must prove:

```text
model proposes action
→ Harness asks supplied approval policy
→ action executes only after ALLOW
```

At least one negative test must prove DENY prevents execution.

Approval decision must appear in Trace.

## H-06 — Deterministic Verification

The task is not successful because the model says it is done.

PASS requires:

```text
supplied deterministic test command executed
exit / test status captured
final PASS only when test passes
```

Missing, timed-out, denied or failed verification cannot become PASS.

## H-07 — Bounded Repair Loop

The proof must support at most one repair cycle:

```text
initial change
→ test
→ if FAIL
→ return failure evidence to model
→ one repair attempt
→ rerun test
→ final result
```

This Stage intentionally does not authorize an open-ended autonomous coding loop.

A run that succeeds on the first change is valid, but tests must independently exercise the one-repair bound so the loop cannot become unbounded by accident.

## H-08 — Execution Trace

Trace must be sufficient to reconstruct the observable sequence:

```text
task start
model turn
read action(s)
proposed mutation
approval
mutation result
verification command
verification result
optional repair
final result
```

Trace may be JSON / JSONL or another small machine-readable Stage-local format.

Do not create a general Platform Trace standard in this Stage.

## H-09 — Governance Non-Inheritance

The Harness must demonstrate that it cannot self-authorize:

```text
scope expansion
outside-Workspace write
Platform Core change
Case 01 change
Case 02 change
Git commit / push
admission / promotion
```

PASS requires these to remain outside the Harness task contract.

## H-10 — Replaceability Statement

The integrated review must identify which parts are:

```text
REUSED EXISTING NEUTRAL CONTRACT
HARNESS RESPONSIBILITY
PRIVATE IMPLEMENTATION HOW
MODEL-SPECIFIC ADAPTER
TOOL-SPECIFIC IMPLEMENTATION
```

No provider, shell, message schema or concrete tool class may be declared permanent Platform identity based on this single proof.

---

# 9. Failure Semantics

The Stage must distinguish at least:

```text
TASK_INVALID
WORKSPACE_VIOLATION
APPROVAL_DENIED
MODEL_FAILED
TOOL_FAILED
COMMAND_TIMEOUT
VERIFICATION_FAILED
REPAIR_EXHAUSTED
TRACE_INCOMPLETE
```

Exact internal enum names may differ, but externally observable failure classes must remain distinguishable enough for review.

Do not claim that these Stage-local names replace or redefine accepted Runtime execution-certainty semantics.

No generic `success: false` blob is sufficient if it hides the reason the Stage cannot continue.

---

# 10. Minimal Artifact Set

Use the minimum artifact set capable of supporting the architecture decision.

Preferred output paths:

```text
platform-harness/minimum-harness-v0.1/
  harness/**                    # minimal Harness implementation
  fixture/**                    # bounded proof fixture
  tests/**                      # Harness boundary / proof tests
  V0_1_RESULTS.json             # machine-readable proof summary
  V0_1_REVIEW.md                # integrated H-00..H-10 interpretation + boundaries
```

Do NOT create by default:

```text
Evidence Index
separate report for every H-check
new Architecture document
Capability Registry
Agent Manifest standard
Plugin framework
provider catalog
Web UI docs
```

Trace output generated during tests may remain test artifact / temporary output if `V0_1_RESULTS.json` records the evidence needed for review. Persist a representative trace only when needed to independently verify H-08.

---

# 11. Implementation Constraints

The implementation should prefer the simplest technology already compatible with the repository.

Do not choose a framework merely because Penguin / Codex / DeepSeek uses it.

Rules:

```text
stdlib / existing dependencies preferred
no new large framework without evidence
no Penguin dependency
no Waku dependency
no Case 01 implementation dependency
no Case 02 implementation dependency
no vendor lock-in in Harness task semantics
reuse existing neutral Catalyst contracts before inventing duplicates
```

Allowed without changing accepted Runtime behavior:

```text
import / adapt a compatible neutral ModelProvider contract
reuse an existing provider adapter if it satisfies the proof
```

Not authorized:

```text
modify agent_runtime/**
change Runtime contracts
change Runtime lifecycle
change Runtime failure / execution-certainty semantics
```

---

# 12. Protected Boundaries

This Stage must not modify:

```text
main
case-01 branch / Case 01 files
case-02 branch / Case 02 files
agent_runtime/**
accepted Runtime behavior
Platform Core contracts
Runtime Adapter contracts
ARCHITECTURE.md
accepted governance baselines
external Penguin repository
external Waku repository
```

All new implementation must remain under:

```text
platform-harness/minimum-harness-v0.1/**
```

on branch:

```text
platform-harness
```

until a later explicit Platform Integration Stage is authorized.

---

# 13. Acceptance Criteria

The V0.1 Candidate may receive a Stage PASS only when:

```text
H-00 PASS
H-01 PASS
H-02 PASS
H-03 PASS INCLUDING ONE LIVE LLM INVOCATION
H-04 PASS
H-05 PASS
H-06 PASS
H-07 PASS
H-08 PASS
H-09 PASS
H-10 PASS
```

and:

```text
one bounded fixture task completes under Harness control
no protected boundary changes
no Runtime duplication presented as architecture
no Platform integration
no unauthorized Git mutation
no hidden dependence on Penguin / Waku / Case 01 / Case 02
no claim of full Agent Builder capability
```

Passing this Stage proves only:

> **Catalyst has a Case-evidenced minimum governed development Harness mechanism, with a real replaceable LLM adapter proof, on the isolated `platform-harness` branch.**

It does not prove:

```text
production readiness
full Agent construction
full Skill construction
portability across multiple live LLM providers
enterprise deployment
Platform admission / integration
```

---

# 14. Expected Stage Verdict Vocabulary

Final integrated review should end with exactly one of:

```text
MINIMUM_HARNESS_V0_1_PASS
MINIMUM_HARNESS_V0_1_TARGETED_REPAIR
MINIMUM_HARNESS_V0_1_FAIL
```

A PASS does not authorize Platform integration.

---

# 15. Next Decision After PASS

If V0.1 passes, the preferred next proof is:

```text
one real low-risk Case 01 development task
using the frozen V0.1 Harness
under a separate Case 01 authorization
```

This would test whether the isolated Harness mechanism can actually reduce the external-Harness glue observed in real product development.

Possible alternatives only if new evidence requires them:

```text
repair an evidenced Harness boundary
prove a second live ModelProvider implementation
gather more research before Case use
```

Do not automatically start V0.2, Agent Builder, Skill Builder, Capability Registry or Platform integration.

---

# 16. STOP / Authorization Boundary

This file defines the Stage only.

```text
STAGE SPEC V0.2
→ EXTERNAL / HUMAN REVIEW
→ explicit Authorization Record required
→ only then implementation may begin
```

Until Authorization exists:

```text
NO Harness code
NO fixture code
NO dependency change
NO test implementation
NO Platform integration
NO Case mutation
```
