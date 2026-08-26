---
name: capability-assimilation
description: Study an external system or implementation, extract the stable responsibility and evidence-backed method value, and preserve it as Catalyst-owned capability/method knowledge without making the source product architecture authority.
short_description: Harvest external capability knowledge without importing product identity.
short_description_zh: 从外部系统吸收“怎么把事情做好”的能力，而不是把外部产品变成 Catalyst 的主人。
version: 1
updated: 2026-08-26T23:20:00+08:00
---

# Capability Assimilation

## Status and authority

This is a replaceable Harness-side / research method.

It is NOT:

- Catalyst Architecture authority;
- Platform Standard;
- a new Capability Registry;
- an external dependency manager;
- a package installation method;
- an instruction to migrate Catalyst onto the studied system;
- an automatic promotion path into Runtime/Core.

Core rule:

> **Assimilate capability knowledge first. Adopt external implementation only when later evidence separately justifies it.**

External systems contribute mechanism evidence, implementation examples, and observed trade-offs. Catalyst retains authority over responsibility, capability meaning, evidence interpretation, organizational lineage, and evolution decisions.

---

## 1. Accepted sources

The source may be:

```text
open-source Harness / Agent / framework
commercial or internal system
Skill / Workflow / Service
paper / design note / implementation specification
mature team procedure
historical enterprise process
```

Examples include Pi, Codex, Waku, LangGraph, DeepSeek Harness, and future systems.

Do not assume a famous or mature system is correct for Catalyst. Study what is actually evidenced.

---

## 2. Step 1 — Define the learning question

Do not begin with “what features does it have?”

Begin with:

```text
What does this system reliably do better or more completely?
What stable responsibility appears to explain that value?
What evidence shows the mechanism works?
Why might that responsibility matter to Catalyst capability preservation or reuse?
```

Reject feature-tour research that has no capability question.

---

## 3. Step 2 — Observe the source implementation

Inspect enough primary material to understand the mechanism:

```text
public contract / docs
implementation where necessary
failure / recovery behavior
Evaluation or tests
extension seams
telemetry / evidence surfaces
known non-goals / limits
```

Record source identity and immutable ref/version when practical.

Do not copy code merely because it is available.

---

## 4. Step 3 — Decompose source-specific HOW

Separate:

```text
SOURCE PRODUCT STRUCTURE
from
STABLE RESPONSIBILITY
from
IMPLEMENTATION MECHANISM
```

Examples:

```text
Pi AgentHarness / registers / lanes
!=
reliable external-effect execution responsibility

Pi vitest-evals adapter
!=
comparative candidate evaluation responsibility

Pi hook/event APIs
!=
observation-vs-intervention boundary
```

Remove product names, class names, framework APIs, and file layouts from the stable statement unless they are themselves the evidence being referenced.

---

## 5. Step 4 — Extract obligations

Describe the minimum observable obligations that make the responsibility credible.

Example — reliable external effect execution:

```text
stable effect identity
intent preserved before uncertain effect
settlement preserved after effect
uncertainty explicit when crash window cannot be known
replay policy explicit when material
recovery based on durable facts rather than guesswork
result correlation preserved
```

Example — comparative evaluation:

```text
frozen task / requirement
stable baseline identity
stable candidate identity
same evaluation conditions where material
repeated trials when stochastic behavior matters
independent / deterministic judge evidence
native execution evidence retained
quality separate from tokens / latency / cost
accept / rollback based on declared criteria
```

Example — observation vs intervention:

```text
passive events report facts
intercepting hooks may alter execution
permissions are not granted merely for visibility
extension seams remain bounded
```

Do not turn every implementation detail into an obligation.

---

## 6. Step 5 — Compare with existing Catalyst value

Search Catalyst before creating a new method candidate.

Classify each extracted responsibility as:

```text
ALREADY EXISTS
PARTIALLY EXISTS
NEW EVIDENCE FOR EXISTING PRINCIPLE
MATERIAL GAP
NOT RELEVANT NOW
```

Prefer strengthening evidence/known limits of an existing Catalyst capability or method over minting a duplicate concept.

---

## 7. Step 6 — Decide what is preserved

Allowed outcomes:

### REFERENCE ONLY
Useful external evidence; no Catalyst method change.

### EVIDENCE ADDITION
Adds evidence, known alternatives, or known limits to an existing Catalyst capability/method.

### METHOD CANDIDATE
A source-neutral, replaceable Catalyst method candidate is justified.

### IMPLEMENTATION CANDIDATE
The external implementation itself may later be compared as HOW.

### NO ACTION
No meaningful Catalyst value demonstrated.

Do not jump from METHOD CANDIDATE to IMPLEMENTATION ADOPTION.

---

## 8. Step 7 — Preserve lineage without transferring authority

A harvested record should preserve:

```text
source system
source version / commit / article
what was observed
stable responsibility
extracted obligations
Catalyst assets compared
what evidence was added
known alternatives
known limits
assimilation outcome
```

External source identity remains visible as lineage/evidence.

The resulting stable responsibility/method wording should remain meaningful if the external source disappears.

---

## 9. Pi Pilot scope

For Minimum Operational V1, Pi research is restricted to three topics:

### PI-01 Comparative Evaluation

Question:

> What minimum obligations make baseline/candidate comparison trustworthy enough to support Catalyst Repair/Rebuild/Replace/External-Adopt decisions?

### PI-02 Durable Effect / Recovery

Question:

> Which source-neutral execution obligations are evidenced by Pi's intent/effect/settlement and recovery design, and how do they compare with current Catalyst Runtime obligations?

Research only. This does not authorize Runtime changes.

### PI-03 Observation vs Intervention

Question:

> What minimum extension-boundary rule keeps passive observability separate from execution-changing control?

Research only. This does not authorize a new Extension Framework.

Explicitly not in this Pilot:

```text
Pi migration
Pi adapter
Pi as Catalyst primary Harness
SessionTree adoption
lanes
compaction implementation
TUI
provider ecosystem
package ecosystem
```

---

## 10. Assimilation output

Return one compact record:

```text
SOURCE
  system
  immutable_source_refs[]

LEARNING QUESTION

OBSERVED MECHANISM
  concise source-specific description

STABLE RESPONSIBILITY

OBLIGATIONS[]

CATALYST COMPARISON
  existing_refs[]
  classification

EVIDENCE / LINEAGE[]

KNOWN LIMITS[]

OUTCOME
  REFERENCE ONLY | EVIDENCE ADDITION | METHOD CANDIDATE | IMPLEMENTATION CANDIDATE | NO ACTION

STOP CONDITION
```

Do not include copied source code unless a tiny excerpt is necessary as evidence and licensing/copyright rules permit it.

---

## 11. Minimality test

Before preserving anything new, ask:

```text
Can this value be expressed as a reference/evidence addition to something Catalyst already knows?
Can the stable responsibility be stated without the source product name?
Would the value survive replacement of the source implementation?
Does this reduce future re-learning or re-building?
```

If the answer is no, do not add a new Catalyst concept.

---

## 12. Relationship to future adoption

If later real use suggests the external implementation itself is valuable:

```text
Capability / responsibility already stable
↓
external implementation becomes one Candidate HOW
↓
same benchmark / evidence requirements
↓
compare with current / other candidates
↓
accept or rollback
```

That later comparison is a separate evolution decision.

> **Catalyst learns from Pi before it ever depends on Pi.**
