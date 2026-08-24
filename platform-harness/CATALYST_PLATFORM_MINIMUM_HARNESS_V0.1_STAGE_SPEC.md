# CATALYST PLATFORM — MINIMUM HARNESS V0.1 STAGE SPEC

> **Status:** STAGE SPEC
> **Implementation Authorization:** **NO**
> **Platform Integration Authorization:** **NO**
> **Branch:** `platform-harness`
> **Expected Base:** `888214d9aaa5ac8d478e07a88c941d09bea305ac`
> **Architecture Review:** `platform-harness/PLATFORM_HARNESS_CAPABILITY_ARCHITECTURE_REVIEW_V0.1.md`
> **Purpose:** prove the smallest Catalyst-controlled Harness execution loop needed to perform one already-authorized bounded software-development task inside an isolated Workspace with replaceable model/tool execution and auditable evidence.

---

# 0. Stage Question

This Stage answers exactly one question:

> Can Catalyst Platform control a replaceable Harness Session that reads an authorized task, operates only inside an isolated Workspace, invokes an LLM plus a minimal tool surface, makes one bounded code change, runs deterministic verification, records execution evidence, and returns a reviewable result without gaining governance authority?

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

Harness is one replaceable Platform capability.

```text
CATALYST PLATFORM
        ↓
Harness Responsibility Contract
        ↓
Harness V0.1 Candidate Implementation
        ↓
Replaceable Model + Replaceable Tools
```

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

---

# 3. Stage Scope

V0.1 must implement only the minimum responsibilities required for the proof.

## 3.1 Required responsibilities

```text
HARNESS SESSION
- one execution identity
- one authorized task
- one bounded lifecycle

WORKSPACE BOUNDARY
- explicit root
- read/write limited to authorized Workspace
- reject traversal / escape

MODEL GATEWAY
- one replaceable model interface
- implementation may use one concrete provider for the proof
- provider-specific behavior must remain outside core task semantics

CONTEXT ASSEMBLY
- Stage/task instruction
- authorized Workspace state
- minimal tool descriptions
- no automatic ingestion of unrelated repository history

READ FILE
- bounded text read

WRITE / EDIT FILE
- bounded Workspace-local mutation

COMMAND EXECUTION
- bounded command execution in Workspace
- timeout / exit status observable

TEST EXECUTION
- deterministic test command is a specialization of command execution or a very thin wrapper

APPROVAL BOUNDARY
- write / command actions require authorization policy supplied to the Session
- model cannot self-approve

EXECUTION TRACE
- model request/result identity sufficient for review
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

## 3.2 Optional only if implementation simplicity requires it

```text
small internal message/event type
small provider adapter
small tool registry
```

These remain private HOW unless evidence proves an independently stable seam.

---

# 4. Explicit Non-Scope

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
Runtime integration
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

# 5. Construction Principle

V0.1 is not an Agent Builder.

It is a **governed development executor proof**.

The Harness receives a task that has already been defined and authorized outside the Harness.

```text
AUTHORIZED TASK
        ↓
Harness Session
        ↓
inspect authorized files
        ↓
make bounded change
        ↓
run deterministic verification
        ↓
if verification fails, bounded repair may occur
        ↓
rerun verification
        ↓
record trace + final result
        ↓
STOP
```

The Harness must not decide what the next Stage should be.

---

# 6. Proof Fixture

The first proof should use a tiny Catalyst-relevant local fixture, not a generic Hello World and not a live Case 01 mutation.

Reason:

- a pure Hello World does not test governed development behavior;
- directly mutating active Case 01 before Harness isolation is proven creates unnecessary product risk.

## 6.1 Required fixture properties

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

# 7. Required Proofs

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

## H-03 — Replaceable Model Boundary

Harness task logic must depend on a small model interface rather than a provider SDK throughout the implementation.

For the proof, at least one of the following is acceptable:

```text
A. deterministic scripted/fake model implementation
B. one live model adapter behind the interface
```

A live credential is not required to prove architecture.

If a fake model is used, it must still exercise the same tool-call / response path used by a live adapter.

## H-04 — Minimal Tool Boundary

Only the tools required for the proof are exposed.

Expected minimum:

```text
read
write/edit
command/test
```

PASS requires the model not to gain arbitrary repository or host mutation authority outside Workspace policy.

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

Trace may be JSON / JSONL or another small machine-readable Case-local format.

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

The review must identify which parts are:

```text
HARNESS RESPONSIBILITY
PRIVATE IMPLEMENTATION HOW
MODEL-SPECIFIC ADAPTER
TOOL-SPECIFIC IMPLEMENTATION
```

No provider, shell, message schema or concrete tool class may be declared permanent Platform identity based on this single proof.

---

# 8. Failure Semantics

The Stage must fail explicitly when any of these occur:

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

No generic `success: false` blob is sufficient if it hides the reason the Stage cannot continue.

---

# 9. Minimal Artifact Set

Use the minimum artifact set capable of supporting the architecture decision.

Preferred output paths:

```text
platform-harness/minimum-harness-v0.1/
  harness/**                    # minimal implementation
  fixture/**                    # bounded proof fixture
  tests/**                      # Harness boundary / proof tests
  V0_1_RESULTS.json             # machine-readable proof summary
  V0_1_REVIEW.md                # integrated interpretation + boundaries
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

# 10. Implementation Constraints

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
no vendor lock-in in core task semantics
```

If one provider adapter is needed for a later live proof, keep it replaceable and outside the core Harness responsibility model.

---

# 11. Protected Boundaries

This Stage must not modify:

```text
main
case-01 branch / Case 01 files
case-02 branch / Case 02 files
accepted Runtime behavior
Platform Core contracts
Runtime Adapter contracts
ARCHITECTURE.md
accepted governance baselines
external Penguin repository
external Waku repository
```

All implementation must remain on:

```text
platform-harness
```

until a later explicit Platform Integration Stage is authorized.

---

# 12. Acceptance Criteria

The V0.1 Candidate may receive a Stage PASS only when:

```text
H-01 PASS
H-02 PASS
H-03 PASS
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
no Platform integration
no unauthorized Git mutation
no hidden dependence on Penguin / Waku / Case 01 / Case 02
no claim of full Agent Builder capability
```

Passing this Stage proves only:

> **Catalyst has a Case-evidenced minimum governed development execution mechanism on the isolated `platform-harness` branch.**

It does not prove:

```text
production readiness
full Agent construction
full Skill construction
executor portability across multiple real LLMs
enterprise deployment
Platform admission
```

---

# 13. Expected Stage Verdict Vocabulary

Final integrated review should end with exactly one of:

```text
MINIMUM_HARNESS_V0_1_PASS
MINIMUM_HARNESS_V0_1_TARGETED_REPAIR
MINIMUM_HARNESS_V0_1_FAIL
```

A PASS does not authorize Platform integration.

---

# 14. Next Decision After PASS

If V0.1 passes, the next decision is **not automatically V0.2**.

External review should choose among:

```text
A. use V0.1 to execute one real low-risk Case 01 task
B. repair an evidenced Harness boundary
C. test one real replaceable model adapter
D. stop because the current proof is sufficient
```

Only real evidence determines which path is next.

A future Case 01 trial must have its own Case-local authorization and must not be implied by this Stage.

---

# 15. STOP / Authorization Boundary

This file defines the Stage only.

```text
STAGE SPEC CREATED
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
