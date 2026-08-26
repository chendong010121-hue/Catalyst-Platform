---
name: capability-optimization
description: Improve a solution from frozen benchmark evidence using bounded hypotheses, replaceable candidates, re-evaluation, and accept-or-rollback decisions without changing Catalyst architecture authority.
short_description: Evidence-driven capability improvement.
short_description_zh: 基于评测证据进行能力改进与回滚。
version: 1
updated: 2026-08-26T17:20:00+08:00
---

# Capability Optimization

This is a replaceable Harness-side improvement method. It does not own Platform Capability admission, architecture authority, or Runtime semantics.

## Core rule

> Evidence → hypothesis → bounded candidate → same benchmark → accept or rollback.

Do not optimize from intuition alone and do not redesign the architecture because one case failed.

## 1. Establish the Reference

Freeze:

```text
solution revision
benchmark revision
provider/model or other execution runtime
knowledge/source revision
accepted evidence from the reference run
```

The candidate must be compared against the same capability target. If the benchmark or runtime changes materially, treat it as a new comparison context.

## 2. Diagnose by responsibility

For every lost point or critical failure, identify the owning gap:

```text
understanding / clarification
knowledge/source coverage
retrieval / evidence binding
reasoning / decision policy
tool/API use
solution-form / orchestration
Runtime / provider / infrastructure
answer composition / UX
benchmark/evaluator defect
```

Do not modify an Agent prompt to hide a missing knowledge source. Do not change Runtime to fix a product-answer mistake.

## 3. State one bounded hypothesis

A useful hypothesis predicts an observable behavior change, for example:

```text
If the solution checks local evidence sufficiency before answering,
then unsupported cases will stop guessing and invoke the approved external source or fail closed.
```

Avoid vague candidates such as `think harder`, `be more careful`, or broad rewrites with no falsifiable prediction.

## 4. Choose the smallest replaceable candidate

A candidate may change whichever layer owns the gap:

- Skill / instructions;
- deterministic implementation;
- Workflow structure;
- Agent policy/prompt/state;
- retrieval configuration;
- tool adapter;
- provider choice when the provider itself is the tested variable.

Do not assume every improvement is an Agent-State edit.

Keep the candidate independently revertible.

## 5. Re-evaluate

Run every materially affected benchmark case using `capability-evaluation` and the frozen comparison conditions.

For nondeterministic model behavior, use repeated runs only when variance is material to the decision. Do not pretend one lucky run proves stable quality.

## 6. Accept or rollback

Accept only when:

```text
critical gates remain satisfied
+
capability evidence improves on the intended dimensions
+
no newly introduced regression invalidates the user outcome
```

Otherwise restore the Reference. Preserve rejected-candidate evidence when it teaches a reusable failure/compatibility lesson, but do not treat rejected implementation state as current truth.

## 7. What may be harvested

After sufficient evidence, reusable value may include:

```text
Capability boundary
Skill/procedure
Workflow pattern
implementation mechanism
evaluation pattern
source/knowledge handling rule
migration/replacement knowledge
```

The original Agent/Workflow/implementation may still be discarded.

## 8. STOP

Stop when the current user capability meets the accepted benchmark boundary or when the next improvement requires a new architecture/product decision. Do not convert optimization into an endless self-modifying service in V0.2.
