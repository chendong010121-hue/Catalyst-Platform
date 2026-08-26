---
name: capability-optimization
description: Evolve a capability solution from frozen evidence by attributing the owning gap, preserving durable organizational value, comparing repair/rebuild/replace/adopt candidates, and accepting or rolling back a bounded candidate against the same benchmark.
short_description: Evidence-governed capability evolution.
short_description_zh: 基于证据进行能力实现的修复、重建、替换与回滚决策。
version: 2
updated: 2026-08-26T21:50:00+08:00
---

# Capability Optimization

This is a replaceable Harness-side evolution method. It does not own Platform Capability admission, Architecture authority, Platform Standard evolution, or Runtime semantics.

It is NOT an Evolution Engine, Repair Engine, Replacement Service, lifecycle controller, self-modifying daemon, or Platform object.

## Core rule

> **Repair is not the default. First decide how the implementation should evolve while preserving the capability value that must survive.**

Operationally:

```text
Evidence
→ Attribute
→ Preserve
→ Diagnose
→ Search alternatives
→ Generate candidates
→ Compare
→ Bounded candidate
→ Same benchmark / evidence boundary
→ Accept or rollback
→ Record lineage
```

Do not optimize from intuition alone. Do not redesign architecture because one case failed. Do not preserve code merely because Catalyst or a previous team wrote it.

## 1. Establish the Reference

Freeze enough identity to make the comparison meaningful:

```text
capability / responsibility target
solution revision
benchmark revision
provider/model or other execution runtime when material
knowledge/source revision when material
accepted evidence from the reference run
known limits / unproven boundaries when material
```

The candidate must be compared against the same capability target. If the benchmark, responsibility, provider/runtime, or knowledge boundary changes materially, record a new comparison context instead of pretending it is the same experiment.

## 2. Attribute the observed failure or limitation

Before proposing a fix, identify where the evidence says the gap is owned.

Typical owners include:

```text
understanding / clarification
knowledge/source coverage
retrieval / evidence binding
reasoning / decision policy
tool/API interaction
solution-form / orchestration
Capability implementation
Adapter / provider integration
Runtime execution certainty / lifecycle
answer composition / UX
benchmark/evaluator defect
Architecture / responsibility boundary
```

Preserve observable facts separately from judgment. A component may report facts about itself; independent Evaluation owns the judgment that those facts satisfy or violate the tested capability.

Do not modify an Agent prompt to hide a missing knowledge source. Do not change Runtime to fix a product-answer mistake. Do not promote a vendor limitation into Platform Core merely because the current mechanism is inconvenient.

## 3. Identify what must be preserved

Before changing implementation, name the durable organizational value that should survive where applicable:

```text
responsibility / semantic WHAT
public or shared Contract obligations
Capability identity / version relationship
Domain meaning
Enterprise meaning
accepted evidence and benchmark knowledge
compatibility / migration knowledge
known limits
lineage / decision rationale
```

The implementation itself is not automatically part of the preserved set.

> **Preserve capability, not implementation.**

This method does not redefine the Platform Capability contract or Harvest philosophy. It only uses the existing Catalyst distinction between durable capability value and replaceable HOW.

## 4. Diagnose the kind of problem

Ask explicitly:

```text
Is the responsibility itself wrong or misplaced?
Is the Contract / required obligation wrong or insufficient?
Is the implementation locally defective?
Is the implementation built on an obsolete assumption?
Is the failure caused by composition rather than one component?
Is a mature internal or external mechanism already available?
Is the implementation still worth maintaining at all?
```

If responsibility or Architecture ownership itself must change, STOP and route to the appropriate architecture/product decision. This Skill does not silently rewrite Architecture.

## 5. Search before rebuilding

Before inventing a candidate, inspect in this order when relevant:

```text
current authoritative Catalyst capability/evidence references
→ existing Catalyst implementation/mechanism alternatives
→ accepted local governed assets
→ trusted mature external mechanisms / complete solutions
→ only then new implementation work
```

External machinery is a first-class candidate when it can satisfy Catalyst's required obligations through a clean boundary. Do not rebuild an inferior Catalyst-owned clone merely for ownership symmetry.

## 6. Generate multiple evolution candidates

Candidate actions are method vocabulary, not Platform ontology and not mandatory enum values.

Consider the smallest relevant set from:

```text
REPAIR / PATCH
  correct a local defect while the responsibility, Contract, and basic assumptions remain valid

LOCAL REPLACE / REPLACE COMPONENT
  preserve the surrounding boundary and replace one Adapter, Provider, Retriever, Tool Loop, policy module, or other localized mechanism

REBUILD COMPONENT
  preserve the responsibility/Contract but create a clean implementation because the old implementation is shaped by obsolete assumptions or compatibility debt

RECOMPOSE
  preserve useful components but change their composition because the failure belongs to the arrangement rather than each component

REPLACE SUBSYSTEM
  replace the larger Harness, Runtime, retrieval stack, Agent implementation, Service, or other subsystem when multiple internal assumptions are no longer worth maintaining

EXTERNAL ADOPT / ADAPT
  use a mature external mechanism or complete solution when it satisfies the required boundary with lower total cost and acceptable coupling

RETIRE / REMOVE
  stop carrying an implementation or mechanism whose responsibility is obsolete, duplicated, or no longer justified
```

No action has automatic priority. **Repair current implementation is only one candidate.**

## 7. Compare Total Evolution Cost, not diff size

Do not choose a candidate merely because it changes the fewest lines today.

Compare material costs such as:

```text
immediate implementation effort
cost of understanding legacy behavior
future maintenance burden
compatibility-patch debt
regression risk
migration risk
rollback difficulty
hidden coupling introduced
pressure to pollute Runtime / Platform Core
future replaceability cost
loss of already-proven semantics or evidence
opportunity cost versus mature external alternatives
```

A clean rewrite with more lines may be cheaper than a small patch that keeps an invalid assumption alive.

Prefer the candidate that satisfies the preserved obligations with the lowest justified total cost, risk, hidden coupling, and long-term maintenance burden — not simply the smallest diff.

## 8. State a bounded hypothesis

The selected candidate must have a falsifiable prediction tied to the attributed gap.

Example:

```text
If native tool interaction is rebuilt around one model turn → 0..N tool calls
while reusing the existing per-execution certainty lifecycle,
then multi-call model responses should execute without losing execution identity
and the accepted single-execution certainty guarantees should remain green.
```

Avoid vague candidates such as `think harder`, `be more careful`, or broad rewrites with no observable prediction.

## 9. Keep the candidate bounded and reversible

The candidate should change only the responsible implementation boundary unless evidence explicitly authorizes a wider change.

Preserve the Reference as a rollback target when practical. New and old implementations may temporarily coexist when that makes comparison, migration, or rollback safer.

Do not mutate an accepted implementation beyond recognition while keeping its old identity solely to avoid admitting that a rebuild or replacement occurred.

## 10. Re-evaluate on the same proof boundary

Run every materially affected benchmark case using `capability-evaluation` and the frozen comparison conditions.

Where applicable preserve:

```text
same capability responsibility / Contract
same benchmark / rubric revision
same evidence requirements
same provider/runtime/knowledge context unless that variable is deliberately under test
Reference identity
Candidate identity
raw execution evidence
```

For nondeterministic model behavior, use repeated runs only when variance is material to the decision. Do not pretend one lucky run proves stable quality.

## 11. Accept or rollback

Accept only when:

```text
critical gates remain satisfied
+
the attributed gap is materially improved or removed
+
required preserved obligations remain satisfied
+
no newly introduced regression invalidates the user outcome
+
new coupling / maintenance cost is justified by the gain
```

Otherwise restore or retain the Reference.

A rejected candidate may still produce valuable compatibility or failure knowledge. Rejected implementation state is not current truth.

## 12. Record Evolution Lineage

A replacement that erases why the system changed is software churn, not organizational learning.

Preserve enough lineage to answer, when material:

```text
what implementation/revision was the Reference?
what failure or limitation triggered review?
which responsibility owned it?
what value/obligations had to survive?
which candidates were considered?
why was the chosen candidate accepted or rejected?
which benchmark/evidence supported the decision?
what migration/rollback implications remain?
what known limits remain unproven?
what implementation/revision is current now?
```

Lineage may live in Git history, review/evidence artifacts, Stage records, or other authoritative references. This Skill does not create a Lineage Service or universal schema.

## 13. What may be harvested

After sufficient evidence, reusable value may include:

```text
Capability boundary
Skill/procedure
Workflow pattern
implementation mechanism
evaluation pattern
source/knowledge handling rule
failure-attribution lesson
compatibility/migration rule
repair/rebuild/replacement decision knowledge
external-adapter knowledge
```

The original Agent, Workflow, Harness, Runtime, or implementation may still be discarded.

## 14. Boundary with Construction / Evaluation / Architecture

```text
Construction
→ understands a need, searches reusable value, selects the simplest justified solution form

Evaluation
→ observes behavior, preserves evidence, attributes failure to the responsible boundary

Capability Optimization / this Skill
→ compares implementation-evolution candidates and accepts/rolls back evidence-backed changes

Architecture / Governance
→ owns stable responsibility, boundary, authority, and Platform evolution rules
```

Do not duplicate these responsibilities into one giant Harness.

## 15. STOP

Stop when:

```text
the accepted capability boundary is satisfied
or
no candidate is justified by current evidence
or
the next change requires a new Architecture / Platform / product decision
```

Do not convert this method into an endless self-repairing or self-modifying service.
