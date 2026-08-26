# Catalyst Platform — System Architecture
## v2.5 · Capability-Preserving Operational Architecture

> **Role of this file:** durable system purpose, layer meaning, responsibility, boundaries, replacement rules, and architecture-level evolution principles.  
> **Current whole-platform state:** [`CATALYST_OPERATIONAL_BASELINE_V1.md`](CATALYST_OPERATIONAL_BASELINE_V1.md).  
> **Guiding thesis:** **Everything is replaceable. Nothing is casually replaceable.**

This file intentionally does **not** pin the current `main` SHA, active Stage, or release status. Those are current-state facts owned by the Operational Baseline, GitHub `main`, tests, CI, and any explicitly active bounded Stage.

---

# 1. Purpose

Catalyst is not primarily an Agent framework, Runtime, Harness, or collection of AI features.

Its long-term direction is an **Organization–AI Capability Operating Model**: an architecture in which people and AI systems can create useful capability while the organization keeps the value that should survive model, provider, Agent, Harness, Runtime, framework, and implementation change.

Catalyst therefore optimizes for:

```text
clear responsibility
stable public obligations
replaceable implementation
portable organizational capability
Domain / Enterprise separation
Evidence and independent Evaluation
Extension-first growth
capability-preserving evolution
real-use-driven architecture change
```

The strongest Catalyst is not the one that owns the most AI machinery. It is the one that allows machinery to change without forcing the organization to relearn what it already proved.

---

# 2. Core architecture principles

> **Stable WHAT / Replaceable HOW.**

> **Preserve capability, not implementation privilege.**

> **Extension First. Core Promotion Later.**

> **Repair is not the default. Evolution decision comes first.**

> **A component may report facts about itself; it does not certify itself.**

> **The Standard grows from evidence, not from predicting every future need.**

Meaning:

- no implementation has permanent privilege;
- replacement is legitimate only when required obligations survive or have an explicit migration path;
- repair, rebuild, replacement, recomposition, external adoption, and retirement are implementation choices, not architecture defaults;
- real use and evidence determine whether a new shared concept deserves architectural cost;
- the more durable organizational value depends on a boundary, the more carefully that boundary must evolve.

---

# 3. Layer model

`Domain` and `Enterprise` are different semantic dimensions that compose; neither is a strict parent of the other.

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

Semantic relation:

```text
one Enterprise may use multiple Domains
one Domain may be used by multiple Enterprises
```

Do not over-model this relationship until real use requires more structure.

---

# 4. Responsibility model

Catalyst asks first:

> **Which responsibility owns this problem?**

not:

> Which file is easiest to edit?

| Problem / change | Default owner |
|---|---|
| execution lifecycle, cancellation, timeout, recovery, reconciliation, execution certainty | **Runtime** |
| vendor / provider / API-specific integration difference | **Adapter** |
| concrete way a capability performs work | **Capability implementation** |
| portable invocation / result / shared public promise | **Platform Standard** |
| professional / industry meaning | **Domain** |
| organization-specific meaning, vocabulary, policy, approval, risk preference | **Enterprise** |
| local semantic needed by limited contexts | **Extension first** |
| cross-capability sequencing / conditional / parallel / long-running process structure | **Workflow / Orchestration** |
| repeated cross-boundary semantic gap harming interoperability / replaceability / portability | **Platform Standard review candidate** |
| current Runtime cannot satisfy required execution obligations | **Runtime evolution candidate** |
| Runtime must understand Domain or Enterprise meaning | **architecture boundary failure candidate** |

> **Change where the responsibility lives.**

A local implementation problem is not evidence that Platform Core should grow.

---

# 5. Capability — the stable WHAT

Capability means **what the system can reliably do**, not the current code object that happens to implement it.

A durable Capability may carry:

```text
responsibility / semantic intent
public or shared Contract obligations
version / identity relationship
Domain meaning
Enterprise meaning
Evidence
Evaluation / benchmark knowledge
known limits
compatibility / migration knowledge
Evolution Lineage
```

A Capability is not identical to:

```text
Python class
prompt
tool function
Agent
Skill implementation
Workflow implementation
provider SDK
Runtime object
framework
```

Those are possible HOWs.

Understanding, Evaluation, Harvest, and real use should enrich the same Capability / Responsibility identity when evidence supports one stable meaning rather than multiplying artificial `analysis-*`, `eval-*`, and `harvest-*` identities.

For the accepted explanatory philosophy, see [`docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md`](docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md).

---

# 6. Platform Standard

Platform Standard is the stable, evolvable coordination boundary between independently evolving organizational assets and replaceable execution implementations.

It has three durable responsibilities.

## 6.1 Coordination

Allow independently implemented components to cooperate through shared contracts.

## 6.2 Isolation

Prevent change from spreading into unrelated layers:

```text
enterprise rule change       != Runtime rewrite
domain terminology change    != Platform Core rewrite
Runtime replacement          != rewriting all Domain / Enterprise assets
vendor API difference        != new shared semantic by default
```

## 6.3 Evolution

Provide enough extension, compatibility, versioning, and migration semantics for the system to evolve without repeatedly collapsing into a new monolith.

> **Platform Standard is valuable when it removes unnecessary coupling while preserving necessary variation.**

The accepted executable contract slice is `PLATFORM_STANDARD_CORE_V0.1.md`. It is a proven minimum, not a claim that the final Standard is completely known.

---

# 7. Extension-first growth

> **Extension First. Core Promotion Later.**

Conceptual lifecycle:

```text
Observed Need
→ Local Solution / Extension
→ Real Usage
→ Evidence
→ repeated cross-boundary common gap?
   ├─ NO  → remain local / Domain / Enterprise / Adapter / Extension
   └─ YES → Platform Standard review candidate
→ compatibility / portability review
→ promote / reject / remain extension
→ migration when required
```

Repeated usage alone does **not** justify Core promotion.

A Domain Extension, Enterprise Extension, Adapter/Vendor Extension, or Experimental Extension may remain outside Core permanently.

Platform Standard deserves review only when evidence repeatedly shows a shared semantic gap across independent contexts and promotion would reduce total system coupling more than it increases Core complexity.

A concept does not enter Core because it is elegant.

---

# 8. Runtime

Runtime answers:

> **How does accepted execution run reliably?**

The current Runtime implementation owns execution concerns such as:

```text
Agent / reasoning execution mechanics
Capability execution
Session / state lifecycle
PendingExecution
execution identity and certainty
cancellation / timeout
recovery
reconciliation
runtime-local execution control
```

Accepted fail-closed semantics include:

```text
exception != proof of non-execution
timeout != failure
unresolved execution never auto-replays
reconciliation is explicit
```

Runtime must remain free of Domain and Enterprise meaning.

Runtime does **not** own:

```text
company organization
professional ontology
domain vocabulary
role meaning
approval meaning
enterprise policy meaning
```

## 8.1 Runtime replacement boundary

A replacement Runtime does not need the same classes, APIs, Agent Loop, framework, or source structure.

It must preserve or explicitly migrate the required obligations at the accepted boundary, for example:

```text
execution certainty semantics
required lifecycle guarantees
standard invocation / result usability
necessary context preservation
required evidence availability
no forced rewrite of stable upper-layer contracts
```

Runtime replaceability is an architecture commitment, not an instruction to build a second Runtime without evidence.

---

# 9. Domain and Enterprise

- **Domain** carries professional / industry meaning.
- **Enterprise** carries organization-specific meaning.

They compose and should remain outside Runtime and generic Platform Core unless repeated cross-boundary evidence proves a genuinely shared coordination semantic.

Current architecture may recognize future responsibilities such as Domain packages, Enterprise profiles, policy, approval, or Workflow without requiring their production implementation.

> **Architecturally Exists does not mean implementation required.**

---

# 10. Workflow / Orchestration

Workflow / Orchestration owns process structure across capabilities:

```text
sequence
parallelism
branching / conditions
long-running process structure
cross-capability coordination
```

Domain may provide professional workflow patterns. Enterprise may configure organization-specific process meaning. Workflow execution must not turn Runtime into a Domain or Enterprise semantic owner.

No Workflow Engine is required merely because this responsibility exists architecturally.

---

# 11. Evidence, observation, and independent Evaluation

Replaceability requires enough evidence to know where failure occurred.

A useful separation is:

```text
Provider / external system
→ reports provider facts

Harness / interaction layer
→ reports protocol / interaction facts

Runtime
→ reports execution / certainty facts

Capability implementation
→ reports invocation / observation facts

Independent Evaluation
→ judges tested capability behavior and attributes failure
```

> **Self-observation is not self-certification.**

Evaluation is not primarily a leaderboard. It establishes what is proven, under what conditions, with what limits, and what responsibility owns a failure.

Benchmark is one evidence mechanism. Real-use evidence remains higher-order reality.

---

# 12. Capability-preserving implementation evolution

When an implementation fails or becomes expensive to maintain, first identify:

```text
what failed?
which responsibility owns it?
what capability / obligation must survive?
is the responsibility wrong?
is the Contract wrong?
is the implementation wrong?
is an assumption obsolete?
what internal or external alternatives exist?
```

Only then choose a bounded implementation path.

Possible method-level candidates include:

```text
REPAIR / PATCH
LOCAL REPLACE
REBUILD
RECOMPOSE
REPLACE SUBSYSTEM
EXTERNAL ADOPT / ADAPT
RETIRE / REMOVE
```

These actions are **not Platform ontology** and have no automatic priority.

The detailed, replaceable method lives in:

`platform-harness/skills/capability-optimization/SKILL.md`

## 12.1 Total evolution cost

Do not equate smallest diff with cheapest solution.

Material cost may include:

```text
implementation effort
legacy-understanding cost
maintenance burden
compatibility debt
regression / migration risk
rollback difficulty
hidden coupling
pressure to pollute Runtime / Core
future replaceability cost
loss of evidence / semantics
opportunity cost versus mature external alternatives
```

## 12.2 Evolution Lineage

Material implementation change should preserve enough lineage to reconstruct:

```text
Reference
triggering evidence
owning responsibility
preserved obligations
considered candidates
accept / reject rationale
benchmark / evidence identity
migration / rollback implications
remaining known limits
resulting implementation
```

This does not require a Lineage Service or universal schema. Git history, PRs, evidence artifacts, review records, and bounded Stage records may carry the lineage.

---

# 13. External systems are first-class HOW candidates

Catalyst does not need to own source code for every mechanism.

Pi, Codex, DeepSeek Harness, LangGraph, MCP implementations, retrieval systems, external Runtimes, model providers, or future systems may be:

```text
knowledge sources
mechanism references
implementation candidates
```

Adopt external machinery when it satisfies the required responsibility, evidence, and replacement obligations through a clean seam with lower justified total cost.

Do not clone mature machinery merely so Catalyst can claim authorship.

External systems never become Catalyst identity or architecture authority merely because they are powerful.

---

# 14. Capability preservation and Harvest

Short-lived implementation change should not unnecessarily destroy long-lived organizational learning.

Likely durable assets include:

```text
Capability / Responsibility
public Contract obligations
Domain knowledge
Enterprise mappings
workflow / method patterns
Evaluation / benchmark knowledge
operational evidence
known limits
compatibility / migration knowledge
Evolution Lineage
```

`HARVEST` is a lifecycle verb describing selective preservation of sufficiently understood, evidence-backed, repeatedly useful capability.

It does not create a Harvest Engine, Registry, Service, Manager, or Platform layer.

Human expertise and human–AI collaboration can also be capability sources, subject to appropriate consent, attribution, privacy, governance, and evidence.

---

# 15. Architecture failure signals

Treat these as review signals, not automatic Core-change authorization.

```text
Runtime changes because one enterprise changed a business rule
→ possible Enterprise / Runtime boundary failure

Domain implementation must be rewritten for every Runtime
→ possible missing stable coordination boundary

many Extensions duplicate the same cross-system meaning
→ possible Platform Standard review candidate

one vendor limitation forces a new Core concept
→ likely Adapter / implementation problem promoted upward

obsolete assumptions survive through repeated compatibility patches because repair is treated as mandatory
→ implementation-evolution failure candidate

replacement destroys Capability evidence, Domain/Enterprise meaning, benchmark knowledge, or public obligations that should be portable
→ missing preservation / migration boundary candidate
```

---

# 16. Source authority by question

There is no single globally highest Source of Truth.

| Question | Authority |
|---|---|
| What is Catalyst now? What is active? | `CATALYST_OPERATIONAL_BASELINE_V1.md` |
| What code is accepted? | GitHub `main` |
| What are system purpose, layers, responsibilities, and replacement rules? | `ARCHITECTURE.md` |
| What stable governance principles constrain growth? | Governing Baseline Part A |
| What does Platform Standard Core v0.1 promise? | `PLATFORM_STANDARD_CORE_V0.1.md` |
| What execution behavior exists? | `agent_runtime/**` + active tests / CI |
| How are needs constructed into solutions? | `agent-construction` Skill |
| How are benchmarks designed? | `capability-benchmark-design` Skill |
| How is behavior judged? | `capability-evaluation` Skill |
| How is implementation evolution decided? | `capability-optimization` Skill |
| Where is reusable organizational value discoverable? | Capability Visibility Index + referenced authority |
| How are repository changes governed? | `docs/DEVELOPMENT_WORKFLOW.md` |
| What historical decision produced the current state? | Git history, closed PRs, evidence, `docs/history/README.md` |
| What implementation work is currently authorized? | explicit bounded user-approved task / Stage when active |

Historical status lines do not redefine current state.

Implementation success does not automatically redefine Architecture or Contract.

---

# 17. Current validated architecture evidence

Current accepted history has demonstrated, at its declared evidence scopes:

```text
reliable Runtime execution certainty / reconciliation semantics
Platform Standard Core v0.1 executable boundary
second Capability portability without Core/Runtime redesign
Extension-first enterprise semantics
Capability Contract conformance on the reference direct-binding path
real model + external tool/API execution with evidence
native-tools v1 → v2 capability-preserving evolution
real Building Regulation professional Capability adoption without Runtime/Core pollution
Domain × Enterprise separation in the Phase 2 pilot
post-close evidence recertification and Phase 2 closure
Capability-Preserving Evolution promotion
Minimum Operational V1 current surface and CI release gate
```

These facts do **not** prove Production Enterprise completeness.

---

# 18. Explicit non-goals without new evidence

Do not build these merely to make Catalyst look more complete:

```text
production Capability Registry / DB
dependency graph
monitoring platform
self-healing / autonomous evolution engine
Repair / Replacement Service
universal Lineage Service
Workflow Engine
Control Plane
full Authority / Policy / Approval system
production IAM / tenant platform
universal Domain SDK
universal Enterprise Profile
second Runtime purely to prove replaceability
Pi / Codex / DeepSeek dependency as product identity
```

They may become legitimate bounded work only when real use produces sufficient evidence.

---

# 19. Operational architecture rule

Catalyst Minimum Operational V1 marks the end of planned platform pre-development.

The default operating loop is now:

```text
REAL USE
→ OBSERVE
→ ATTRIBUTE
→ search existing internal / external capability knowledge
→ smallest justified bounded change
→ EVALUATE
→ ACCEPT / ROLLBACK
→ HARVEST durable value when earned
→ REAL USE AGAIN
```

There is no automatic next Phase.

A new Stage exists only when a real finding cannot be responsibly handled inside current accepted boundaries.

---

# 20. Final statement

> **Catalyst is an Organization–AI Capability Operating Model, not a larger Runtime.**
>
> **Capability is the durable WHAT; implementation is replaceable HOW.**
>
> **Platform Standard protects coordination and portability without absorbing every semantic.**
>
> **Runtime owns reliable execution, not Domain or Enterprise meaning.**
>
> **Extensions preserve variation; Core promotion requires repeated cross-boundary evidence.**
>
> **Evaluation judges evidence independently; components do not certify themselves.**
>
> **Repair is not the default; implementation evolution is evidence-governed.**
>
> **External systems are legitimate HOW candidates and knowledge sources.**
>
> **Real use, not architecture imagination, decides what grows next.**
>
> **Everything is replaceable. Nothing is casually replaceable.**
