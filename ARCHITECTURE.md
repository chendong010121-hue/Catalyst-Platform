# Agent Runtime + Platform Standard — System Architecture
## v2.2 FINAL · Minimal Platform Transition

> **Accepted Runtime baseline:** `main @ 9b88c26eef8faf2569cce8ffcb1cb3407e27b980`  
> **Current stage:** Platform Standard Core v0.1 — **IMPLEMENTED / LOCAL VERIFIED / CI VERIFIED / PR #4 UNDER EXTERNAL REVIEW / NOT YET ACCEPTED INTO MAIN**  
> **Role of this file:** define architecture and boundaries. It does **not** authorize future features.

---

# 1. What exists now

A small provider-neutral Agent Runtime already exists.

It owns:

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

It can already execute registered Capabilities while preserving the important rule:

```text
exception != proof of non-execution
timeout != failure
unresolved execution never auto-replays
```

The Runtime baseline is therefore considered **closed** for the current stage.

The next task is not to enlarge Runtime. It is to place the first stable platform contract above it.

---

# 2. Long-term direction

The final product is not merely an Agent ↔ Tool framework.

The long-term direction is:

```text
Enterprise Agent Operating Model
        +
Platform Standard
        +
Domain Packages
        +
Enterprise Mapping
        +
Governed Runtime Ecosystem
```

The strategic assets are expected to accumulate mainly in:

```text
Platform Standard
Enterprise Mapping
Domain Packages
Workflow Patterns
Governance semantics
Evaluation / Feedback
Capability ecosystem
```

Runtime remains essential infrastructure, but should stay replaceable.

---

# 3. Architecture boundaries

```text
Application Surfaces
        ↓
Enterprise Mapping          [FUTURE]
        ↓
Domain Layer                [FUTURE]
        ↓
Agent / Workflow Layer
        ↓
Platform Standard
        ↓
Runtime Adapter
        ↓
Agent Runtime
        ↓
Infrastructure
```

A future Control Plane may govern Registry, IAM, Policy, Approval, Audit, Evaluation and configuration, but it is **not** Runtime.

## Runtime

Answers:

> How does execution run?

Runtime MUST remain enterprise-free and domain-free.

## Platform Standard

Answers:

> What common language must capabilities, invocations, results, artifacts and future governance layers use?

Core v0.1 contains only:

```text
Object Envelope
Extension
Capability
Invocation
Result
ArtifactRef
Minimal Trace
```

## Domain Layer

Answers:

> What does this industry mean?

Future content may include ontology, domain roles, evidence rules, artifact types, task/risk taxonomy and evaluation rules.

## Enterprise Mapping

Answers:

> How does this specific enterprise operate?

Future content may include organization, roles, delegation, approval matrix, risk appetite, data classification and enterprise vocabulary.

---

# 4. Platform Standard Core v0.1

The immediate executable path is only:

```text
Standard Capability
      ↓
Standard Invocation
      ↓
Validator
      ↓
InMemory Descriptor Registry
      ↓
Runtime Adapter
      ↓
Existing Runtime
      ↓
Standard Result
  + optional ArtifactRef
  + Minimal Trace
```

Core v0.1 MUST be implemented outside AgentCore.

The reference Adapter may keep a simple internal binding:

```text
(capability_id, capability_version)
        ↓
existing Runtime Capability implementation
```

This binding is an implementation detail, not another platform object.

---

# 5. Stable Core, adjustable enterprise

This is a permanent design principle:

> **The standard must be stable without becoming rigid.**

The following should change slowly:

```text
object envelope
invocation/result semantics
extension semantics
artifact reference semantics
minimum trace semantics
```

The following are expected to vary across companies and domains:

```text
organization
roles
delegation
approval chains
risk thresholds
capability availability
data classification
domain vocabulary
workflow patterns
evaluation rules
```

These variations MUST NOT require rewriting Runtime.

They SHOULD NOT require modifying Core.

Preferred mechanisms:

```text
Extension
Enterprise Profile          [FUTURE]
Domain Package              [FUTURE]
versioned policy/workflow   [FUTURE]
```

Default evolution rule:

> **Extension First. Core Promotion Later.**

A concept enters Core only after there is evidence that it is stable across industries, enterprises and Runtime implementations.

---

# 6. Future Authority Chain

A mature enterprise action should eventually be explainable as:

```text
User
 ↓
Organization
 ↓
Role / Project Role
 ↓
Delegation / Principal
 ↓
Agent / Actor
 ↓
Capability
 ↓
Resource
 ↓
Policy Decision
 ↓
Approval if required
 ↓
External Side Effect
 ↓
Artifact / Evidence / Audit
 ↓
Responsibility
```

Core v0.1 does not implement this.

Its only obligation is:

> Do not introduce assumptions that make this chain impossible to add later.

---

# 7. Current non-goals

Platform Core v0.1 does **not** implement:

```text
authentication / IAM
RBAC / ABAC
tenant isolation
approval
policy engine
workflow engine
full audit platform
Enterprise Profile
Domain Package
Control Plane
MCP
A2A
OpenTelemetry integration
multi-agent
plugin marketplace
new Runtime
new Agent Loop
```

These are future architecture, not current work.

---

# 8. Source of truth

```text
GitHub main
= accepted code reality

ARCHITECTURE.md
= system meaning and boundaries

PLATFORM_STANDARD_CORE_V0.1.md
= current engineering contract

approved Stage Spec
= what is authorized to build next

research documents
= evidence and vision only
```

No future box in this architecture automatically authorizes implementation.

---

# 9. Current completion test

Platform Standard Core v0.1 is complete when:

```text
1. one Standard Capability runs end-to-end through the existing Runtime
2. Result / ArtifactRef / Trace are returned through Standard contracts
3. AgentCore remains unchanged
4. uncertain Runtime execution remains Standard "unresolved"
5. a second different Capability can be added without changing Core schemas or Runtime
```

Then stop and review.

Do not automatically proceed into enterprise governance or domain modeling.

### v0.1 implementation status (PR #4 — NOT YET ACCEPTED INTO MAIN)

```text
Platform Standard Core v0.1           IMPLEMENTED / LOCAL VERIFIED / CI VERIFIED
status                                PR #4 UNDER EXTERNAL REVIEW — NOT YET ACCEPTED INTO MAIN
new package                           platform_standard/  (models, extensions, validation, registry, runtime_adapter)
reference vertical slice              examples/run_platform_standard_vertical_slice.py  (compose_report)  PASS
reference implementation              examples/platform_standard_reference.py
acceptance tests                      tests/test_platform_standard_core.py  PS-1..PS-14 + AR-1..AR-7  PASS
second capability (count_words)       added with NO Core schema / Validator / Runtime / AgentCore change  PASS
same-ID multi-version routing         Adapter-local wrapper (V1 vs V2)  PASS
Adapter seam                          RuntimeAdapter -> DirectedReasoner -> Runtime.start(goal) (existing Agent Loop)
AgentCore unchanged                   verified (agent_runtime/** zero diff on main @ 9b88c26)
existing regression                   22/22 examples test modules PASS
```

Completion test verdict: 1-5 all PASS locally + CI. **STOP** per release gate — no Identity/Policy/Approval/Domain/Workflow/MCP/A2A/Control Plane work started.

---

# 10. Final statement

> **Runtime is the execution heart.**

> **Platform Standard is the stable shared language.**

> **Extensions preserve adjustability.**

> **Domain Layer carries industry meaning.**

> **Enterprise Mapping carries organization-specific meaning.**

> **The long-term product is an Organization-AI Operating Model, not a larger Runtime.**

The immediate engineering task is intentionally small:

> **Run one complete Standard → Adapter → Runtime → Result path, prove the second Capability does not change Core, then stop.**
---

# 11. Current Implementation Authorization

This section is normative for the current engineering stage.

The architecture above describes both current and future system meaning. It does **not** authorize implementation of every future layer.

For the current stage, the only authorized engineering target is:

```text
Platform Standard Core v0.1
```

The implementation MUST be limited to the executable path:

```text
Capability Descriptor
      ↓
InMemory Descriptor Registry
      ↓
Standard Invocation
      ↓
Platform Validator
      ↓
Runtime Adapter
      ↓
Existing Agent Runtime
      ↓
Standard Result
  + ArtifactRef(s)
  + Minimal Trace
```

The implementation MAY add only the minimum adapter-local binding required to connect:

```text
(capability_id, capability_version)
        ↓
existing Runtime Capability implementation
```

This binding is not a new Platform object and must not become a plugin framework or Control Plane.

## Explicitly authorized work

```text
Common Object Envelope
Extension Contract
Capability Contract
Invocation Contract
Result Contract
ArtifactRef Contract
Minimal Trace Event
Validator
InMemory Descriptor Registry
Runtime Adapter
one reference Capability
one end-to-end vertical slice
one second-Capability portability test
required tests and handoff documentation
```

## Explicitly unauthorized in this stage

```text
Identity / IAM
RBAC / ABAC
Delegation
Policy engine
Approval system
Enterprise Profile implementation
Domain Package implementation
Workflow engine
Control Plane service
MCP
A2A
OpenTelemetry integration
Multi-Agent
Plugin framework / marketplace
Production Registry Service
New Runtime
New Agent Loop
AgentCore redesign
```

If any of these appear necessary to complete Core v0.1, implementation MUST stop and report the blocking reason instead of silently expanding scope.

## Current release gate

The stage is complete only when:

```text
1. the reference vertical slice passes end-to-end
2. uncertain Runtime execution maps to Standard `unresolved`
3. AgentCore remains unchanged
4. the second Capability is added without Core schema / Runtime / AgentCore changes
5. all Core v0.1 acceptance tests pass
```

After this gate passes:

> **STOP. Do not automatically begin Identity, Policy, Domain, Workflow, MCP, A2A or Control Plane work.**

The next stage requires a separate architecture decision based on evidence from this implementation.
