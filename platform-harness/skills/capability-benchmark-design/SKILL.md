---
name: capability-benchmark-design
description: Turn a real user capability into a multi-case benchmark that separates desired behavior from plausible shortcuts, with public task statements and private scoring criteria.
short_description: Design real-user capability benchmarks.
short_description_zh: 设计面向真实用户能力的多案例评测。
version: 1
updated: 2026-08-26T17:20:00+08:00
---

# Capability Benchmark Design

This is a replaceable Harness-side method. It is not Platform Standard and does not define Capability identity.

## Core rule

> Test what a user actually needs the system to do, not the architecture words used to describe it.

## 1. Start from the full user capability

Expand a short requirement into the observable behavior space that materially affects use. Typical dimensions include:

- natural-language variation and ambiguity;
- required context and missing facts;
- source/authority hierarchy;
- local knowledge vs external retrieval;
- version/change handling;
- tool/API use;
- multi-turn clarification;
- output form, provenance and uncertainty;
- failure/fail-closed behavior;
- domain or enterprise constraints when material.

Do not stop at labels such as `reliable`, `traceable`, `applicable`, `helpful`, or `safe`. Convert them into decisions and artifacts a benchmark can distinguish.

## 2. Write a Capability Contract for evaluation

Before writing cases, state:

```text
USER OUTCOME
OBSERVABLE RESPONSIBILITIES
AVAILABLE PUBLIC EVIDENCE
AUTHORITY / SOURCE RULES
MATERIAL SHORTCUTS OR WEAKER BEHAVIORS
REQUIRED ARTIFACTS / ANSWERS
FAIL-CLOSED CONDITIONS
CAPABILITY BOUNDARY NOT BEING CLAIMED
```

The contract belongs to the benchmark/evaluation method, not Platform Core.

## 3. Design multiple cases

A useful benchmark must contain materially different cases, not paraphrases of one happy path.

Prefer a set containing at least:

```text
positive / ordinary
missing-information
source-conflict or authority-selection
local-evidence available
external fallback required
unsupported-claim / fail-closed
knowledge/version change when relevant
```

Only include dimensions the target capability truly owns.

## 4. Separate public task and private rubric

Each case has:

```text
PUBLIC
- user-like statement
- supplied facts/materials
- allowed tools/sources
- requested output

PRIVATE
- required observable behavior
- critical gates
- scoring items
- accepted alternatives
- failure attribution hints
```

Never expose the private rubric to the tested solution.

## 5. Design against shortcuts

For every case, privately answer:

```text
What would a superficially strong solution do?
What would the desired capability do differently?
Which observable answer/tool call/artifact separates them?
```

If both strategies get the same score, the case is weak and should be redesigned.

## 6. Real execution requirement

A benchmark design alone is never evidence that a capability works.

For a live-use claim, require at least one execution campaign using the real solution and real external dependencies owned by the capability. Fake providers may calibrate deterministic plumbing only.

## 7. Freeze before formal comparison

Once a case revision is ready for evaluation, freeze:

- public statement;
- private rubric;
- target solution revision;
- provider/model for that campaign;
- available source/knowledge revision.

Do not move Gold or scoring requirements after seeing the tested answer. If a benchmark defect is found, repair it as a new revision and rerun affected cases.

## 8. Output

Return or write a benchmark package containing:

```text
capability_contract
public_cases
private_rubric
target_identity
source/knowledge identity if material
evaluation runtime requirements
explicit unproven boundaries
```

STOP when the benchmark can distinguish the capability boundary. Do not create an Evaluation Service, scoreboard backend, UI, registry, or new Core object merely to store it.
