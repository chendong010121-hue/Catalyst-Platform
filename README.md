# Catalyst

**Governed capability architecture for evolving enterprise agent systems.**

Catalyst is designed around one idea:

> **Rich ecosystem, small constitutional core.**

Execution technologies should be free to evolve. Runtimes, providers, agents, adapters, and implementations may be replaced. The organizational assets above them — capability contracts, domain meaning, enterprise meaning, artifacts, evidence, and governance history — should not have to be rebuilt every time the execution stack changes.

> [!IMPORTANT]
> **Current evidence state:** Minimum Architectural Framework v1 is **PROVEN / ACCEPTED**.
>
> This repository proves a minimum set of architectural boundaries. It is **not** a production-complete enterprise Agent platform.
>
> For the accepted v1 closure and PARK / WATCH snapshot, read the active [Governing Baseline snapshot](docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_B.md).
>
> For current implementation authorization, read the **current user-approved Stage Spec**.

## 1. What Catalyst Is / Is Not

Catalyst is moving toward an **Enterprise Agent Operating Model** in which teams can build useful AI capabilities without forcing every new tool, model, workflow, or enterprise rule into one permanent Runtime or Platform Core.

Use this repository when you care about:

- stable public capability contracts;
- replaceable execution implementations;
- clear responsibility between Platform, Adapter, Runtime, Domain, and Enterprise semantics;
- evidence-backed architectural evolution;
- traceable governance and migration instead of silent coupling.

Catalyst is **not**:

- a production-complete enterprise platform;
- a fixed Agent Runtime that every capability must depend on forever;
- a feature race to own every RAG, MCP, Multi-Agent, Workflow, Policy, or Control Plane implementation;
- a promise that every box in the long-term architecture already exists in code.

The current project goal is deliberately smaller:

> **Use the minimum real implementation needed to prove the most important architecture boundaries.**

## 2. What Is Proven Now

> This section is a convenience summary of the current proven state. GitHub `main` and accepted governance evidence remain authoritative.

The accepted repository has evidence for the following claims:

| Proven boundary | What it means |
|---|---|
| **Runtime execution semantics** | timeout / exception do not silently imply non-execution; unresolved execution is explicit |
| **Platform executable boundary** | Capability Descriptor → Invocation → Validator → Adapter → Runtime → Result is real and runnable |
| **Capability portability** | a meaningfully different Capability can be added without redesigning Platform Core or Runtime |
| **Extension-first growth** | `enterprise.identity` can add enterprise semantics without putting them into Platform Core or `agent_runtime/**` |
| **Platform Contract Authority** | a Platform Capability Contract is a versioned public promise, not implementation metadata |
| **Direct-binding conformance** | a clearly incompatible declared implementation fails closed before normal execution |
| **Minimum Architectural Framework v1** | the deliberately selected v1 Evidence Scope is PROVEN / ACCEPTED |

This does **not** mean Workflow, Authority, Policy, Approval, Domain Packages, Enterprise Profiles, Control Plane, or a second Runtime are already production implementations.

## 3. Quick Start

The current reference system is intentionally small and can be verified locally without deploying a service.

CI currently runs on Python 3.12.

From the repository root:

```bash
python -m examples.run_minimal_loop
```

Run the current Platform Standard evidence:

```bash
python tests/test_platform_standard_core.py
```

Run Capability Contract Conformance evidence:

```bash
python tests/test_capability_contract_conformance_pilot.py
```

Run the Enterprise Extension evidence:

```bash
python tests/test_enterprise_extension_pilot.py
```

The CI workflow is the best source for the complete active regression set:

```text
.github/workflows/ci.yml
```

Before changing architecture, first make sure the accepted system still runs.

## 4. Five-Minute Architecture

Catalyst separates **organizational meaning** from **replaceable execution**.

```text
                 Application / Agent / Workflow
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
        Domain Packages            Enterprise Semantics
     professional meaning        organization meaning
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
                   Platform Standard
              stable public contracts
                            │
                            ▼
                     Runtime Adapter
              compatibility / translation
                            │
                            ▼
                         Runtime
                 reliable execution
                            │
                            ▼
                     Infrastructure
```

A second useful view is the Capability boundary:

```text
Semantic / Capability meaning
        ↓
Platform Capability Contract
versioned observable promise
        ↓
Binding / Adapter
compatibility / translation
        ↓
Capability Implementation
how the work is done
        ↓
Runtime
how execution runs reliably
```

**Everything is replaceable. Nothing is casually replaceable.**

Replacement is allowed when the architectural obligations at the stable boundary are preserved or explicitly migrated.

## 5. Where Does My Change Belong?

Start with responsibility, not the easiest file to edit.

| Need / change | Default owner |
|---|---|
| execution lifecycle, cancellation, timeout, recovery, reconciliation | **Runtime** |
| vendor / provider / API-specific difference | **Adapter** |
| concrete way a capability performs work | **Capability implementation** |
| portable public invocation / result promise | **Platform Standard** |
| professional / industry meaning | **Domain** |
| organization-specific meaning, vocabulary, policy, approval semantics | **Enterprise** |
| cross-capability sequencing / parallel / conditional process structure | **Workflow / Orchestration** |
| new local semantic that current Core does not own | **Extension first** |

The permanent default rule is:

```text
Real Need
    ↓
Who owns the problem?
    ↓
Can existing contracts express it?
    │
 ┌──┴──┐
YES    NO
 │      │
 ▼      ▼
Implement at owner
        ↓
local / Adapter / Domain / Enterprise / Extension first
        ↓
collect real evidence
        ↓
repeated cross-boundary gap?
        │
   ┌────┴────┐
   NO       YES
   │          │
remain local  Platform Standard review
```

> [!CAUTION]
> **DO NOT CHANGE PLATFORM CORE FIRST.**
>
> If the responsible layer, evidence, or implementation authorization is unclear: **STOP**.

## 6. Existing Integration Seams

Only currently real seams are listed here.

### Capability implementation

Reference implementations:

```text
examples/platform_standard_reference.py
```

`ComposeReportCapability` and `CountWordsCapability` show that implementation HOW is separate from the Platform Capability Contract.

### Platform Capability contract

Reference descriptors:

```text
examples/platform_standard_reference.py
```

The normative v0.1 contract is defined in:

```text
PLATFORM_STANDARD_CORE_V0.1.md
```

Do not let an implementation silently redefine the Platform public promise.

### Runtime Adapter / binding

Current reference boundary:

```text
platform_standard/runtime_adapter.py
```

The Adapter owns current binding / translation responsibilities. It must not become a Workflow Engine, Policy Engine, enterprise semantic owner, or replacement Runtime.

### Extensions

Generic extension contract:

```text
platform_standard/extensions.py
```

Current enterprise evidence:

```text
enterprise_extensions/identity.py
```

New Domain / Enterprise needs should not become new Core fields merely because one project needs them.

### Runtime composition

The reference stack is assembled through:

```text
examples/platform_standard_reference.py
```

The Runtime remains replaceable execution infrastructure and must stay domain-free and enterprise-free.

Future architecture may include Domain Packages, Enterprise Profiles, Workflow / Orchestration, additional Runtimes, or other execution services. Their existence in the architecture does **not** mean there is a current implementation tutorial or authorization for them.

## 7. Source of Truth / Reading Order

Catalyst does **not** have one globally highest Source of Truth. Authority depends on the question.

| Question | Authority |
|---|---|
| Why does the system exist? What are the layers and boundaries? | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| How may the architecture evolve? When should we STOP or avoid Core changes? | [`Governing Baseline — PART A`](docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md) |
| What is the accepted v1 closure / PARK / WATCH snapshot? | [`Governing Baseline — PART B`](docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_B.md)（快照，非 implementation authorization） |
| What work is currently authorized? | Current user-approved Stage Spec |
| What does Platform Standard Core v0.1 normatively define? | [`PLATFORM_STANDARD_CORE_V0.1.md`](PLATFORM_STANDARD_CORE_V0.1.md) |
| Who designs, implements, audits, publishes, and merges? | [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md) |
| What code and tests are actually accepted now? | **GitHub `main` + active tests + CI** |

Recommended reading order:

```text
README.md
→ ARCHITECTURE.md
→ Governing Baseline PART A
→ Governing Baseline PART B
→ PLATFORM_STANDARD_CORE_V0.1.md
→ docs/DEVELOPMENT_WORKFLOW.md
→ code / tests for implementation detail
```

A stale status line in an older document does not automatically redefine the current accepted repository state.

### README authority protection

> README is an onboarding summary, not an architecture, governance, contract, or implementation authority. If this README conflicts with an authoritative source for a given question, the authority for that question wins.

### Current implementation authorization

> Current governance may establish the default state, constraints, decision protocol, or eligibility for future work.
>
> Current implementation authorization must be **explicitly identified** for the current task by a user-approved Stage Spec or equivalent explicit user authorization.
>
> If no current authorization is explicitly identified: **STOP**.
>
> Do **not** infer current authorization from an older Stage Spec based on filename, numbering, modification time, recency, similarity, sequence, architectural relevance, or "looks like the latest one".

## 8. Development Workflow

Catalyst separates architecture, implementation, evidence, audit, and release authority.

The authoritative repository development workflow is defined in:

[`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md)

This README does not independently define development roles or implementation authorization; it only navigates to the workflow authority.

Architecture findings are **not** automatic authorization to modify code.

## 9. For AI Coding Agents

Using Codex, DeepSeek, Claude Code, or another coding agent?

Before editing, first read:

```text
README.md
ARCHITECTURE.md
docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md
docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_B.md
docs/DEVELOPMENT_WORKFLOW.md
Current user-approved Stage Spec / task handoff
```

Then be able to state:

```text
1. What is the current accepted code baseline?
2. What work is currently authorized?
3. Which architecture layer owns the requested change?
4. Which files are allowed to change?
5. What is the Stage stop condition?
```

Guardrails:

1. **Do not infer implementation authorization from an architecture diagram.**
2. **Do not change Platform Core first.**
3. **Do not put Domain or Enterprise meaning into Runtime.**
4. **Do not treat a vendor API, Agent framework, Workflow engine, or provider schema as the Catalyst Standard.**
5. **Do not silently expand a Stage when the existing contract is insufficient.**
6. **STOP and report an Architecture Finding when responsibility or authority is unclear.**
7. **Preserve exact evidence: branch, SHA, tests, CI, and candidate diff.**
8. **Implementation author is not the final architecture auditor whenever practical.**
9. **GitHub `main` is accepted code truth; a local working copy is not.**
10. **A successful implementation does not automatically redefine the Platform Contract.**
11. **Do not infer current authorization from an older Stage Spec** (filename, recency, similarity, sequence, or architectural relevance); if no user-approved Stage Spec / equivalent explicit authorization identifies the current task, STOP.

The goal is not to make every change possible.

The goal is to let the system grow **without destroying the boundaries that preserve long-term organizational assets**.
