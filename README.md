# Catalyst Platform

**Keep what an organization has learned, even when the AI underneath changes.**

Catalyst is a small, capability-first architecture for building and evolving AI work without tying organizational knowledge to one Agent, model, Harness, Runtime, provider, or framework.

The core idea is simple:

> **Preserve capability, not implementation privilege.**

An Agent may be replaced. A Runtime may be rebuilt. A better external Harness may arrive tomorrow. Catalyst is designed so the valuable part — what the organization knows how to do, why it trusts that ability, where its limits are, and what was learned from previous failures — does not have to disappear with the implementation.

> **Current state:** **Catalyst Minimum Operational V1 — accepted for controlled real use.**  
> Planned platform pre-development is stopped. New platform work should now come from real use or a concrete failure.

---

## Why Catalyst exists

AI systems are getting better very quickly. That is good news — but it creates a different problem for teams and organizations.

If every useful workflow is trapped inside a particular Agent, prompt, provider, framework, or project, then every technology change risks throwing away accumulated learning.

Catalyst treats the durable asset as the **Capability**, not the container that happened to implement it.

A useful capability may carry:

- a clear responsibility and observable promise;
- domain or enterprise meaning;
- evidence showing that it really works;
- benchmarks and evaluation knowledge;
- known limits and failure modes;
- compatibility and migration knowledge;
- the history of why one implementation was repaired, rebuilt, replaced, adopted, or retired.

That leads to three design rules:

> **Stable WHAT / Replaceable HOW.**  
> **Everything is replaceable. Nothing is casually replaceable.**  
> **Real use and evidence decide what deserves to survive.**

For the fuller design philosophy, read [`Catalyst Capability Harvest — Design Philosophy`](docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md).

---

## What Catalyst does today

Operational V1 provides a small, working capability lifecycle:

```text
REAL NEED
→ identify the responsibility / capability need
→ discover what the organization already knows
→ reuse / adapt / compose / reconstruct before building new
→ choose the simplest valid implementation
→ execute through the applicable boundary
→ preserve evidence
→ evaluate and attribute failures
→ repair / rebuild / replace / adopt / retire when justified
→ preserve useful learning
→ reuse it again
```

No single Engine owns this loop. The pieces remain independently replaceable.

Catalyst has already demonstrated this with:

- a real Platform Standard → Adapter → Runtime execution path;
- multiple capabilities without redesigning Runtime/Core;
- Extension-first enterprise semantics;
- real model and external-tool execution with evidence and evaluation;
- a professional Building Regulation capability pilot with fail-closed evidence discipline;
- two independent cases where capability value was preserved while implementation strategy changed;
- harvested knowledge that remains usable after the original Case/Agent is no longer part of the active platform.

Catalyst is **not** claiming to be a production-complete enterprise portal, a universal Agent framework, or a feature-complete replacement for Pi, Codex, DeepSeek Harness, LangGraph, or other execution systems.

Those systems can be knowledge sources or implementation candidates. Catalyst does not need to own every HOW.

---

## Five-minute mental model

Catalyst separates **organizational meaning** from **replaceable execution**.

```text
                  Application / Agent / Workflow
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
          Domain meaning             Enterprise meaning
                │                           │
                └─────────────┬─────────────┘
                              ▼
                     Platform Standard
                  stable coordination boundary
                              ▼
                        Runtime Adapter
                              ▼
                           Runtime
                    replaceable execution HOW
                              ▼
                        Infrastructure
```

A second view is the capability boundary:

```text
Capability / Responsibility
        ↓
public / shared Contract
        ↓
Binding / Adapter
        ↓
replaceable implementation
        ↓
Runtime / external machinery
```

The important part is not that every box must be Catalyst-owned. The important part is that the responsibility and evidence remain clear enough for implementations to change without losing organizational value.

---

## Try the accepted system

Python 3.12 is the current CI reference.

From the repository root:

```bash
python -m examples.run_minimal_loop
```

Run the current Operational V1 proof:

```bash
python -m examples.test_catalyst_operational_v1
```

Run the current Platform / Extension contract evidence:

```bash
python tests/test_platform_standard_core.py
python tests/test_capability_contract_conformance_pilot.py
python tests/test_enterprise_extension_pilot.py
```

The complete active regression gate is defined in:

```text
.github/workflows/ci.yml
```

This Quick Start verifies the accepted platform baseline. Catalyst is not yet a polished end-user application with a single universal task UI; controlled real use may currently be driven through a suitable coding/agent Harness or the repository's reference surfaces. The operator surface is intentionally not promoted into Core before repeated real-use evidence justifies it.

---

## How Catalyst decides what to build

Catalyst starts with responsibility, not with the easiest file to edit.

| Need | Default owner |
|---|---|
| execution lifecycle, timeout, recovery, reconciliation, certainty | **Runtime** |
| vendor / provider / API-specific difference | **Adapter** |
| concrete way a capability performs work | **Capability implementation** |
| portable invocation / result promise | **Platform Standard** |
| professional / industry meaning | **Domain** |
| organization-specific meaning | **Enterprise** |
| cross-capability process structure | **Workflow / Orchestration** |
| local semantic not owned by Core | **Extension first** |

A new idea does not enter Platform Core because it looks general or elegant. It earns a stable boundary only when repeated real evidence shows that the shared gap is real.

> **Extension First. Core Promotion Later.**

---

## How Catalyst handles failure

A failure does not automatically mean “repair the current code.”

Catalyst first asks:

```text
What failed?
Which responsibility owns it?
What capability / evidence / meaning must survive?
Is the responsibility wrong, the contract wrong, or only the implementation wrong?
Is there already a better internal or external mechanism?
```

Then the implementation may be:

```text
REPAIRED
LOCALLY REPLACED
REBUILT
RECOMPOSED
REPLACED AS A SUBSYSTEM
EXTERNALLY ADOPTED / ADAPTED
RETIRED
```

No action has automatic priority. The current implementation must earn the right to remain through evidence and total evolution cost.

The replaceable method is [`capability-optimization`](platform-harness/skills/capability-optimization/SKILL.md).

---

## Current operating methods

Catalyst deliberately keeps the formal method set small:

- [`agent-construction`](platform-harness/skills/agent-construction/SKILL.md) — understand the real need, search existing capability value first, choose the simplest justified solution form.
- [`capability-benchmark-design`](platform-harness/skills/capability-benchmark-design/SKILL.md) — design benchmarks that test the real user capability rather than implementation trivia.
- [`capability-evaluation`](platform-harness/skills/capability-evaluation/SKILL.md) — preserve evidence and attribute success/failure to the responsible boundary.
- [`capability-optimization`](platform-harness/skills/capability-optimization/SKILL.md) — compare implementation-evolution candidates without sacrificing durable capability value.

These are methods, not Engines or Platform services.

---

## Repository map

```text
Catalyst Platform
├── README.md                         human entry point
├── CATALYST_OPERATIONAL_BASELINE_V1.md
│                                     current-state authority
├── ARCHITECTURE.md                   purpose, layers, boundaries
├── PLATFORM_STANDARD_CORE_V0.1.md    accepted public contract slice
├── CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json
│                                     tiny capability-value navigation
├── platform_standard/                public coordination implementation
├── agent_runtime/                    one replaceable Runtime implementation
├── platform-harness/                 replaceable operating methods
├── enterprise_extensions/            current Extension evidence
├── assets/                           preserved organizational assets
├── evidence/                         accepted execution/evaluation evidence
├── examples/ + tests/                reference proofs and regressions
└── docs/                              philosophy, governance, history
```

`agent_runtime/**` keeps its historical package name because it is only one replaceable Runtime implementation. It is not the product identity.

---

## Where to read next

There is no single document that is authoritative for every question.

1. **What is Catalyst now? What is active?** → [`CATALYST_OPERATIONAL_BASELINE_V1.md`](CATALYST_OPERATIONAL_BASELINE_V1.md)
2. **Why does Catalyst exist? What owns what?** → [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. **Why preserve capability / Harvest?** → [`Capability Harvest Design Philosophy`](docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md)
4. **What stable governance constrains growth?** → [`Governing Baseline — Part A`](docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md)
5. **What does Platform Standard Core v0.1 promise?** → [`PLATFORM_STANDARD_CORE_V0.1.md`](PLATFORM_STANDARD_CORE_V0.1.md)
6. **How is repository work governed?** → [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md)
7. **Where is historical Case / Stage evidence?** → [`docs/history/README.md`](docs/history/README.md)

Accepted code truth remains GitHub `main` plus active tests and CI.

---

## Current operating rule

Catalyst has reached its planned pre-development stopping point.

> # **STOP PLANNED PLATFORM PRE-DEVELOPMENT**

The next source of change is real use:

```text
USE
→ OBSERVE
→ ATTRIBUTE
→ search existing internal / external capability knowledge
→ make the smallest justified change
→ evaluate against the same responsibility / evidence boundary
→ preserve useful learning
→ USE AGAIN
```

Do not add a Registry, graph, monitoring layer, Workflow Engine, memory platform, Authority/Policy system, second Runtime, or new Core concept simply to make the platform look more complete.

The goal is not to own the most AI machinery.

The goal is for an organization to keep what it has genuinely learned while the machinery keeps changing.
