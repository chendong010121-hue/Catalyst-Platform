# Minimum Architectural Framework — Governing Baseline v1.1
## Activation / Authority Index

> **Repository:** `chendong010121-hue/Catalyst-Platform`  
> **Architecture authority:** `ARCHITECTURE.md` v2.5 — Capability-Preserving Operational Architecture  
> **Current whole-platform state:** `CATALYST_OPERATIONAL_BASELINE_V1.md`  
> **Baseline status:** **ACTIVATED / ACCEPTED**  
> **Role:** stable governing principles preserved from Minimum Architectural Framework v1; not current-stage metadata

This repository packages Governing Baseline v1.1 as two files for maintainability. The split is packaging, not a second governance layer.

1. [`MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md`](./MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md) — **Stable Governing Core**. Its durable governance disciplines remain active unless superseded by an explicitly accepted governance/architecture change.
2. [`MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_B.md`](./MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_B.md) — **Historical v1 Decision Snapshot**. Its old `current`, Stage, and Risk Queue wording records the v1 closure moment and is not current-state authority.

## Activation history

The original merge of this bundle activated Governing Baseline v1.1 and closed Minimum Architectural Framework v1 for its declared evidence scope:

```text
Minimum Architectural Framework v1
= PROVEN / ACCEPTED

Default after closure
= STOP
```

That historical activation remains valid.

## Current interpretation rule

The governing principles that remain durable include, among others:

```text
real need before implementation
responsibility before file choice
Architecturally Exists != implementation required
Evidence-backed claims require evidence
minimum sufficient implementation
Extension First / avoid premature Core growth
Everything is replaceable; nothing is casually replaceable
explicit Stop Condition
Risk Queue != roadmap
```

### North Star terminology

Part A was activated when the project still used **Enterprise Agent Operating Model** as its long-term framing. The accepted Design Philosophy and Architecture later generalized that framing.

For current long-term product meaning, the authoritative term is now:

> **Organization–AI Capability Operating Model**

as defined by `ARCHITECTURE.md` v2.5 and explained by `docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md`.

This supersedes the old **name / framing**, not the durable Part A discipline that long-term architecture is a responsibility map rather than a feature backlog, that Production Exists is not implied, and that implementation requires evidence.

### Historical status wording

Where Part A or Part B uses old phrases such as `current project goal`, `current stage`, `current risk queue`, old repository names, old Architecture version references, or old implementation baselines, interpret those as the v1 governance context in which this baseline was activated.

For **current state and current operating mode**, use:

```text
CATALYST_OPERATIONAL_BASELINE_V1.md
GitHub main
active tests / CI
explicit bounded user-approved Stage / task when one is active
```

For **durable architecture meaning**, use `ARCHITECTURE.md`.

No PARK / WATCH item becomes automatically authorized merely because it appears in this historical baseline. After Operational V1, real use or a concrete finding must justify new bounded work.
