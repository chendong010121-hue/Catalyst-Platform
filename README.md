# Catalyst Platform

**An operating model for preserving and growing organizational capability in the AI era.**

Models, Agents, tools, providers, and frameworks will keep changing. The harder organizational problem is continuity: **how do you keep what people and AI have genuinely learned to do through real work when the machinery underneath changes?**

Catalyst is designed for that problem.

It provides a small architecture for making useful capability understandable, evidenced, reusable, and evolvable without making any one Agent, Runtime, Harness, provider, framework, or codebase permanent.

In architecture terms, Catalyst is an **Organization–AI Capability Operating Model**.

> **Current state:** Catalyst Minimum Operational V1 is accepted for controlled real use. Planned platform pre-development is stopped; new platform work should come from real use or a concrete failure. See [`CATALYST_OPERATIONAL_BASELINE_V1.md`](CATALYST_OPERATIONAL_BASELINE_V1.md) for the current whole-platform state.

### Repository status and evidence roles

| Identity | Current meaning |
|---|---|
| **Current state** | `CATALYST_OPERATIONAL_BASELINE_V1.md` + accepted GitHub `main` |
| **Current architecture / contract** | `ARCHITECTURE.md` + `PLATFORM_STANDARD_CORE_V0.1.md` |
| **Current deterministic verification** | active tests + `.github/workflows/ci.yml` (`catalyst-platform-ci`) |
| **Historical evidence** | `evidence/v0.2/**`, historical Case / Stage records, and frozen refs |

The public `main` branch is PR-gated, deletion-protected, and non-fast-forward / force-push protected. **Catalyst CI is currently not configured as a GitHub-required merge status check**, so repository text must not imply that GitHub blocks every merge unless CI is green.

The visible `live-capability-eval.yml` workflow and `platform-harness/live_eval/**` belong to the **historical Catalyst Minimum Usable V0.2 live-model evidence lineage**. They remain legitimate historical proof at their tested identities, but they are not current Operational V1 continuous recertification. Registered historical evidence is preserved evidence; it is not automatically rerun or written back on every current commit.

No reuse license has yet been granted for this public repository.

---

## Why Catalyst exists

Organizations do not learn only through software.

Useful capability may emerge from:

- a person’s professional judgment or working method;
- a team process that repeatedly produces a good result;
- a human–AI collaboration pattern;
- an Agent, Skill, Workflow, service, or tool;
- an external product or open-source mechanism;
- a project that exposes a better way to work;
- an evaluation or failure that clarifies what really matters.

The problem is that this learning is often trapped inside temporary containers: one project, one prompt, one Agent, one provider, one team member, or one implementation.

When the container changes, the organization can end up relearning the same thing.

Catalyst tries to separate the **durable value** from the **temporary machinery**.

The goal is not to freeze technology. It is to make technology easier to replace **without forcing the organization to forget what it already proved**.

---

## What Catalyst means by Capability

A **Capability** is what the system, person, team, or human–AI combination can reliably do — together with enough meaning and evidence to understand what that claim actually covers.

A durable Capability may include:

```text
responsibility / semantic intent
public or shared obligations
Domain meaning
Enterprise meaning
Evidence
Evaluation / benchmark knowledge
known limits and failure modes
compatibility / migration knowledge
Evolution Lineage
```

A Capability is not the same thing as the implementation currently carrying it.

```text
Capability / Responsibility    = durable WHAT
Agent / Skill / Workflow       = possible HOW
Runtime / Harness / provider   = possible HOW
framework / prompt / code      = possible HOW
```

For example, a building-regulation capability is not simply “the Agent that answers regulation questions.” The durable value is the ability to answer within a defined professional responsibility: use the right sources, preserve locators, check applicability, fail closed when context is insufficient, expose known limits, and retain evidence about what was proven. The retrieval stack, model, Agent shape, or Runtime may later change without erasing that capability.

That distinction is the center of Catalyst.

---

## How capability grows

Catalyst is built around real work rather than endless platform design.

```text
REAL WORK
   ↓
UNDERSTAND
what problem is actually being solved?
what responsibility exists?
   ↓
EVIDENCE
what happened, under what conditions?
   ↓
EVALUATE
what is actually proven, limited, or failing?
   ↓
HARVEST
preserve only durable value that has earned it
   ↓
REUSE / ADAPT / RECONSTRUCT / COMPOSE
use what the organization already knows
   ↓
EVOLVE
repair, rebuild, replace, adopt, or retire when justified
   ↓
REAL WORK AGAIN
```

`HARVEST` is a lifecycle verb, not a Platform object. Catalyst does not create a Harvest Engine, Harvest Service, or universal Harvest Registry. The point is selective preservation: keep what is sufficiently understood, evidenced, and useful; leave the rest local, provisional, or disposable.

Benchmarking is part of this loop, but it is not the destination. **Real use remains the higher-order reality.** A benchmark is valuable when it helps reproduce a failure, compare alternatives, or clarify whether a capability is actually present.

The accepted explanatory philosophy is documented in [`Catalyst Capability Harvest — Design Philosophy`](docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md).

---

## Design principles

Catalyst keeps the formal architecture small. A few principles do most of the work.

### Stable WHAT / Replaceable HOW

The responsibility and public obligation should be more stable than the current implementation. Agents, providers, Harnesses, Runtimes, frameworks, and internal mechanisms remain replaceable where the required obligations can be preserved or explicitly migrated.

### Preserve capability, not implementation privilege

The current implementation has no automatic right to survive because it already exists. What deserves preservation is the capability, evidence, meaning, and learning that should remain valuable after the implementation changes.

### Everything is replaceable. Nothing is casually replaceable.

Replaceability is not churn. A replacement must respect the obligations, evidence, migration cost, and organizational value attached to the boundary being changed.

### Extension First. Core Promotion Later.

A useful idea does not enter Platform Core because it looks elegant or general. Local needs stay local until repeated evidence shows a shared cross-boundary responsibility that is worth the permanent architectural cost.

### Observation is not certification

A component may report facts about itself. It does not certify itself. Independent Evaluation owns judgment and failure attribution.

### Repair is not the default

When an implementation fails, Catalyst first asks what responsibility failed and what must survive. Repair, local replacement, rebuild, recomposition, subsystem replacement, external adoption, and retirement are all legitimate implementation choices. No action has automatic priority.

### The Standard grows from evidence

Platform Standard should stabilize only what repeated real use proves needs a shared coordination boundary. Architecturally imaginable does not mean implementation required.

---

## Architecture in one view

Catalyst separates organizational meaning from replaceable execution.

```text
                    Application Surfaces
                            │
                            ▼
                  Agent / Workflow Layer
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
        Domain Semantics          Enterprise Semantics
      professional meaning      organization-specific meaning
              │                           │
              └─────────────┬─────────────┘
                            ▼
                   Platform Standard
              stable coordination boundary
                            │
                            ▼
                      Runtime Adapter
                            │
                            ▼
                         Runtime
                 replaceable execution HOW
                            │
                            ▼
                     Infrastructure
```

`Domain` and `Enterprise` are different semantic dimensions that compose. Runtime remains execution infrastructure and should not learn professional or organization-specific meaning merely to make one feature convenient.

A second useful view is the capability boundary:

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

The important point is not that every box must be implemented by Catalyst. External systems may be better at particular mechanisms. Catalyst can learn from them, adopt them, or use them as replaceable HOW candidates without turning them into Catalyst’s identity or architecture authority.

For the complete responsibility and replacement model, read [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## What Operational V1 has actually proven

Catalyst is intentionally not presented as production-complete enterprise software. Operational V1 is a **minimum operational architecture**: enough real implementation and evidence to begin controlled use without pretending that every future Platform responsibility is already known.

Accepted history has demonstrated, within its declared scopes:

- Runtime execution certainty, recovery, reconciliation, cancellation, and timeout semantics;
- a working Platform Standard → Adapter → Runtime → Result path;
- more than one Capability passing through the accepted boundary without redesigning Runtime/Core;
- Extension-first enterprise semantics without teaching generic Runtime enterprise meaning;
- real model and external-tool execution with preserved evidence and failure attribution;
- capability-preserving implementation evolution from a failed tool-interaction assumption to a rebuilt candidate;
- a real Building Regulation professional Capability pilot with evidence discipline and fail-closed behavior;
- Domain × Enterprise separation in real capability adoption;
- harvested mechanism knowledge that remains useful after the original Case or source Agent leaves the active platform;
- a consolidated Operational V1 repository surface with an accepted CI release gate.

These facts prove that the architecture can operate. They do not prove universal Domain coverage, a production Capability Registry, a finished end-user portal, or a complete enterprise operating system.

---

## How to use Catalyst today

Catalyst today is an operating model and governed repository, not a single universal chat or task UI.

A controlled real-use task should begin with a real need, not with a request to add a Platform feature.

```text
real need
→ identify the responsibility / capability need
→ search existing Catalyst capability value
→ reuse / adapt / compose / reconstruct where possible
→ use the simplest justified implementation
→ execute through an appropriate Runtime / Harness / external system
→ preserve evidence
→ evaluate the result and attribute failure correctly
→ evolve only where evidence justifies change
→ preserve durable learning
```

The operator surface is intentionally replaceable. A suitable external coding or Agent Harness may be used to perform work without becoming Catalyst Core. Catalyst owns the responsibility, evidence, and governance boundaries that must remain stable; it does not need to own every execution interface.

The four current operating methods are:

- [`agent-construction`](platform-harness/skills/agent-construction/SKILL.md) — understand the real need, search existing capability value first, and choose the simplest justified solution form;
- [`capability-benchmark-design`](platform-harness/skills/capability-benchmark-design/SKILL.md) — design benchmarks around real user capability rather than implementation trivia;
- [`capability-evaluation`](platform-harness/skills/capability-evaluation/SKILL.md) — preserve evidence and attribute success or failure to the responsible boundary;
- [`capability-optimization`](platform-harness/skills/capability-optimization/SKILL.md) — compare implementation-evolution candidates while preserving durable capability value.

These are methods, not Engines or Platform services.

---

## Verify the accepted system

Python 3.12 is the current CI reference.

From the repository root:

```bash
python -m examples.run_minimal_loop
```

Run the Operational V1 proof:

```bash
python -m examples.test_catalyst_operational_v1
```

Run the current Platform / Extension contract evidence:

```bash
python tests/test_platform_standard_core.py
python tests/test_capability_contract_conformance_pilot.py
python tests/test_enterprise_extension_pilot.py
```

The complete active regression gate is defined in `.github/workflows/ci.yml`.

These commands verify the accepted platform baseline. They are not intended to pretend that Catalyst already has a polished universal end-user application.

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
│                                     thin capability-value navigation
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

## Where authority lives

There is no single document that is authoritative for every question.

| Question | Authority |
|---|---|
| What is Catalyst now? What is active? | [`CATALYST_OPERATIONAL_BASELINE_V1.md`](CATALYST_OPERATIONAL_BASELINE_V1.md) |
| Why does Catalyst exist? What owns what? | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Why preserve capability / Harvest? | [`Capability Harvest Design Philosophy`](docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md) |
| What stable governance constrains growth? | [`Governing Baseline — Part A`](docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md) — stable governing core; current product/architecture identity is supplied by Operational V1 + `ARCHITECTURE.md` |
| What does Platform Standard Core v0.1 promise? | [`PLATFORM_STANDARD_CORE_V0.1.md`](PLATFORM_STANDARD_CORE_V0.1.md) |
| How is repository work governed? | [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md) |
| Where is historical Case / Stage evidence? | [`docs/history/README.md`](docs/history/README.md) |
| What code is accepted? | GitHub `main` + active tests / CI |

Historical status lines, branch names, old Stage files, and historical evidence do not redefine current authority.

---

## Current operating rule

Catalyst has reached its planned pre-development stopping point.

The next source of architectural change is **real use**.

```text
USE
→ OBSERVE
→ ATTRIBUTE
→ search existing internal / external capability knowledge
→ make the smallest justified change
→ EVALUATE
→ ACCEPT / ROLLBACK
→ HARVEST durable value when earned
→ USE AGAIN
```

Do not add a Registry, graph, monitoring layer, Workflow Engine, memory platform, Authority/Policy system, second Runtime, or new Core concept simply to make the repository look more complete.

Catalyst does not become stronger by owning more AI machinery.

It becomes stronger when people, teams, and AI systems can keep building on what the organization has genuinely learned while the machinery continues to change.
