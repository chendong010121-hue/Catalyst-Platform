# Catalyst Capability Harvest — Design Philosophy V0.1

- **Status:** **ACCEPTED / SEDIMENTED**
- **Type:** Non-Governing Design Philosophy
- **Authority:** Interpretive / explanatory only
- **Subordinate to:** `ARCHITECTURE.md` / `CATALYST_OPERATIONAL_BASELINE_V1.md` / active Governing Baseline / bounded user-approved Stage authorization / `docs/DEVELOPMENT_WORKFLOW.md`
- **Implementation Authorization:** NO
- **Architecture Change:** NO
- **Governing Baseline Change:** NO

## Purpose

This document preserves the accepted Catalyst design philosophy behind Capability preservation, Evidence, Evaluation, Harvest, external learning, and human–AI organizational learning.

It exists to prevent Catalyst from collapsing back into an Agent Builder, a Runtime, a Harness, an Evaluation product, or a collection of implementation features.

It does **not** add a Platform object, layer, service, ontology, pipeline, engine, registry, or implementation requirement.

---

## 1. Capability, not software

Catalyst is not primarily designed to preserve software. Catalyst is designed to preserve **Capability**.

Models, providers, Agents, Skills, Workflows, Harnesses, Runtimes, adapters, tools, frameworks, databases, prompts, and concrete source code may be replaced. What should survive, where sufficiently understood and evidenced, is the durable organizational value above them:

```text
Capability / Responsibility
Domain knowledge
Enterprise meaning
Contract / public obligations
Evidence
Evaluation / benchmark knowledge
Known limits
Workflow / method patterns
Compatibility / migration knowledge
Operational learning
Evolution lineage
```

The deeper rule is:

> **Short-cycle implementations may change quickly; proven organizational capability should remain as continuous and portable as reasonably possible.**

This is the explanatory meaning of:

> **Everything is replaceable. Nothing is casually replaceable.**
>
> **Stable WHAT / Replaceable HOW.**
>
> **Preserve capability, not implementation privilege.**

---

## 2. Capability may come from anywhere

Catalyst is not a closed ecosystem and does not require all useful Agents or mechanisms to be built by Catalyst.

Potential capability sources include:

```text
Catalyst-built Agent / Skill / Workflow
legacy enterprise Agent
third-party or open-source Agent
commercial AI system
external Harness / Runtime / tool
human expertise
human working method
human–AI collaboration
project experience
team practice
```

The aspiration is not:

> Only Catalyst-built systems are valid.

It is:

> **Catalyst should increasingly be able to understand an external source, decompose its responsibilities, evaluate what is real, and preserve only what is genuinely valuable.**

External systems are therefore legitimate knowledge sources and implementation candidates, but never automatic architecture authorities.

---

## 3. Understand before preserve

A system, Agent, workflow, method, or human practice must not be harvested merely because it looks useful.

Understanding should distinguish at least:

```text
what problem is actually solved?
what responsibilities exist?
what is durable capability?
what is accidental implementation HOW?
what belongs to Domain meaning?
what belongs to Enterprise meaning?
what is actually implemented?
what is only intended or claimed?
what evidence exists?
what remains unknown or contradicted?
```

Useful review states may include:

```text
IMPLEMENTED
PARTIAL
INTENDED_NOT_IMPLEMENTED
UNKNOWN
CONTRADICTED
```

The goal of Understanding is not more documentation. The goal is to identify value that can be independently judged, evolved, and potentially reused.

---

## 4. Evaluation exists to establish evidence

Evaluation is not primarily a leaderboard or a numerical score. Its main job is to establish what has actually been proven:

```text
does this capability really exist?
under what conditions?
where are its limits?
why did it fail?
how reliable is the evidence?
is the benchmark itself valid?
is the capability mature enough to preserve?
```

`UNDERSTAND` is not `HARVEST`. Evidence and Evaluation sit between them.

Evaluation may use, when appropriate:

```text
structural evidence
controlled benchmark
regression
real-use evidence
human professional review
world-state verification
trace / execution evidence
reliability evidence
```

### Real use remains above benchmark

Benchmark is a **reality probe**, not the destination of the system.

The higher-order loop is:

```text
REAL USER NEED
→ REAL TASK
→ REAL RESULT / SIDE EFFECT
→ USER ACCEPTS / CORRECTS / RETRIES / ABANDONS
→ EVIDENCE
→ UNDERSTAND
→ EVALUATE
→ EVOLVE
→ REAL USE AGAIN
```

A controlled benchmark is useful when reality is ambiguous, a failure needs reproduction, or alternatives need comparison. Catalyst must not become a system that optimizes only for its own benchmark.

### Observation is not certification

Components may report bounded facts about themselves, but self-observation does not equal self-certification. Independent Evaluation owns judgment and failure attribution.

---

## 5. Harvest is a lifecycle verb

`HARVEST` means preserving a sufficiently understood, evidence-backed, repeatedly useful capability from a temporary Agent, implementation, project, method, external system, or human–AI collaboration as reusable organizational value.

> **Harvest is a lifecycle verb, not a Platform object.**

There is no implied:

```text
Harvest Engine
Harvest Service
Harvest Registry
Harvest Manager
Harvest Platform
Harvest Object Model
```

A useful maturation pattern is:

```text
REAL USE
→ OBSERVE
→ UNDERSTAND
→ DECOMPOSE
→ EVIDENCE
→ EVALUATE
→ REPEATED USEFULNESS
→ SUFFICIENT CONFIDENCE
→ HARVEST
```

If that threshold is not met:

> **DO NOT HARVEST YET.**

Harvested does not mean permanent. A harvested capability may later be reused, recomposed, rebound, updated, superseded, replaced, or reevaluated.

---

## 6. One capability should accumulate learning, not multiply identities

Understanding, Evaluation, Harvest, and later real use should enrich the same underlying Capability / Responsibility where that identity is genuinely stable.

Conceptually:

```text
UNDERSTANDING
→ adds structural evidence

EVALUATION
→ adds behavioral evidence, reliability, limits, failure attribution

HARVEST
→ adds reuse / reconstruction evidence

REAL USE
→ adds operational evidence
```

The default should **not** be to create separate `analysis-*`, `eval-*`, and `harvest-*` capabilities for the same responsibility.

> **Analysis, Evaluation, preservation, and reuse should converge on the same Capability / Responsibility meaning when the evidence supports one stable identity.**

A Capability Library is therefore not merely a pile of prompts, code, Skills, or Agents. It is the accumulated result of governed capability identity, responsibility, evidence, lineage, reuse history, Evaluation, and known limitations.

---

## 7. Humans and human–AI collaboration are capability sources

People are not outside the model. Human expertise, working methods, review habits, tacit domain knowledge, and human–AI collaboration may all produce valuable capability.

But experience is not automatically organizational property or reusable capability.

A selective, governed path is:

```text
REAL WORK
→ EXPRESSION / OBSERVATION
→ UNDERSTANDING
→ EVIDENCE
→ REPEATED USEFULNESS
→ EVALUATION
→ HARVEST
```

This is **not** surveillance, automatic employee extraction, or automatic ownership assignment. Human contribution requires appropriate consent, attribution, governance, privacy, and evidence.

---

## 8. Harness is an evidence-producing aid, not the product identity

A Harness becomes valuable to Catalyst when it helps AI production become bounded, inspectable, reproducible where necessary, and evidence-producing:

```text
AI CREATION
→ GOVERNED PRODUCTION
→ BOUNDED / INSPECTABLE RESULT
→ EVIDENCE
→ EVALUATION
→ POSSIBLE HARVEST
```

Useful Harness responsibilities may include scope boundaries, execution boundaries, evidence preservation, verification, version identity, rollback, and traceability.

But the Harness remains replaceable. Catalyst has no architectural reason to permanently bind itself to one Harness implementation.

---

## 9. Catalyst should learn from the external world

Catalyst should not reimplement mechanisms simply to claim ownership.

A healthy external-learning sequence is:

```text
EXTERNAL SYSTEM
→ UNDERSTAND
→ DECOMPOSE
→ IDENTIFY RESPONSIBILITY
→ IDENTIFY VALUABLE MECHANISM
→ REMOVE PRODUCT-SPECIFIC ASSUMPTIONS
→ COMPARE WITH EXISTING CATALYST VALUE
→ REUSE / ADAPT / RECONSTRUCT / EXTERNAL ADOPT WHEN JUSTIFIED
→ EVALUATE IN THE REAL RESPONSIBILITY BOUNDARY
→ HARVEST ONLY DURABLE VALUE
```

The external product may later disappear. The organizational learning should not have to disappear with it.

External adoption is first-class, but never automatic.

---

## 10. Minimal architecture is a discipline

Catalyst should prefer a few strong, composable responsibilities over a growing catalog of platform objects.

A new Registry, Engine, Service, graph, Manager, ontology, Control Plane, Workflow system, or monitoring layer is not evidence of maturity.

Before creating a new Platform object, ask:

```text
what stable responsibility does it own?
is that responsibility already owned elsewhere?
is this a repeated real gap or a one-case convenience?
can an existing seam or external mechanism satisfy it?
what evidence proves the new object earns permanent architectural cost?
```

If the answer is unclear:

> **DO NOT BUILD IT YET.**

This is how Catalyst remains a small constitutional architecture while still allowing rich external execution ecosystems.

---

## 11. Real use drives evolution

The long-term operating loop is not endless platform design.

It is:

```text
REAL USE
→ OBSERVE
→ ATTRIBUTE
→ UNDERSTAND
→ EVALUATE
→ PRESERVE WHAT MUST SURVIVE
→ REPAIR / REBUILD / REPLACE / RECOMPOSE / ADOPT / RETIRE AS EVIDENCE JUSTIFIES
→ HARVEST DURABLE VALUE
→ REAL USE AGAIN
```

No implementation action has automatic priority. Repair is not the default; replacement is not the default. Evidence-governed Evolution Decision is the default.

---

## 12. Metaphor, not ontology

The Catalyst / Harvest language is explicitly:

> **METAPHOR, NOT ONTOLOGY.**

It gives the project a useful language for selective preservation and evolution. It does not introduce Seed, Crop, Growth, Harvest, or Evolution managers, objects, layers, or registries.

---

## Closing principle

Catalyst should make it increasingly possible for an organization to answer:

```text
What have we learned to do?
Why do we believe we can do it?
Under what limits?
What implementation is currently doing it?
What may be replaced without losing the capability?
What did previous failures teach us?
Can the next person, team, Agent, or system reuse that learning?
```

The strongest possible Catalyst is not the one that owns the most AI machinery.

It is the one that allows technology to change while the organization keeps what it has genuinely learned.
