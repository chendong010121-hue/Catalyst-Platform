# Catalyst Platform — Operational Baseline V1

> **Baseline type:** current-state / operational release baseline  
> **Product state:** **CATALYST MINIMUM OPERATIONAL V1**  
> **Repository:** `chendong010121-hue/Catalyst-Platform`  
> **Valid when:** this baseline is present on accepted GitHub `main` and the active Catalyst Platform CI for that commit is green  
> **Platform pre-development:** **STOP**  
> **Operating mode:** controlled real use → evidence-driven evolution

This file is the **single current-state front door** for Catalyst Platform. It does not replace Architecture, Platform Standard contracts, governing principles, Evaluation evidence, or accepted code truth.

It answers:

> **What is Catalyst now, what is active, where is the authority/evidence, and when must platform-building stop?**

---

## 1. Product identity

The product and repository identity is:

# **Catalyst Platform**

The package:

```text
agent_runtime/**
```

is one replaceable Runtime implementation inside Catalyst. It intentionally keeps its implementation name because Runtime is a replaceable HOW, not the product identity.

The historical repository name `agent-runtime` remains only in historical Git objects, old evidence, and closed references where changing it would rewrite history.

---

## 2. Accepted evidence chain

Catalyst enters controlled real use with the following accepted chain:

```text
Minimum Architectural Framework v1
→ PROVEN / ACCEPTED

Platform Standard Core v0.1
→ executable Standard / Adapter / Runtime boundary
→ second Capability portability
→ Extension support
→ ACCEPTED / CLOSED

Platform Integration V0.1
→ minimal Capability visibility
→ Capability-first Construction
→ Construction / Evaluation evidence handoff
→ cross-component execution / attribution proof
→ COMPLETE / STOPPED

Catalyst Minimum Usable V0.2
→ real model API
→ real external API / tool
→ benchmark + raw evidence + Evaluation
→ frozen Reference
→ bounded Candidate + same-benchmark re-evaluation
→ accept / rollback
→ PASS / MERGED

Phase 2 — Governed Capability Adoption
→ real Building Regulation Evidence Capability local pilot
→ Domain × Enterprise separation
→ replaceable implementation
→ professional evidence / fail closed
→ Post-Pilot Architecture Review
→ post-close evidence recertification
→ COMPLETE — PASS

Capability-Preserving Evolution
→ stable Architecture principle
→ capability-optimization v2 as replaceable method
→ MERGED

Minimum Operational V1
→ current surface consolidated
→ historical Case / Stage clutter removed from active root
→ active Operational proof
→ Catalyst Platform CI release gate
→ PASS
```

The Phase 2 closure record remains:

```text
docs/governance/CATALYST_PHASE_2_CLOSURE_REVIEW_V0.1.md
```

Accepted post-close recertification manifest identity:

```text
cd8c28b58a563ea7d16e8711eb44076f70fde4d146f742c0be6bd6cc9bd06759
```

Operational V1 activation was proven on accepted `main` with the Catalyst Platform CI release gate; later documentation/governance hygiene must not silently redefine runtime or contract behavior.

---

## 3. Operational thesis

Catalyst is usable when the existing pieces compose into a small capability lifecycle rather than a roadmap for more Platform objects:

```text
REAL NEED
→ RESPONSIBILITY / CAPABILITY NEED
→ DISCOVER EXISTING ORGANIZATIONAL VALUE
→ REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD ONLY THE GAP
→ SELECT SIMPLEST VALID SOLUTION FORM
→ BIND / EXECUTE WHEN APPLICABLE
→ RAW EVIDENCE
→ EVALUATE / ATTRIBUTE
→ PRESERVE WHAT MUST SURVIVE
→ REPAIR / REBUILD / REPLACE / RECOMPOSE / ADOPT / RETIRE AS JUSTIFIED
→ SAME RESPONSIBILITY / BENCHMARK / EVIDENCE BOUNDARY
→ ACCEPT OR ROLLBACK
→ HARVEST DURABLE VALUE WHEN EARNED
→ FUTURE REUSE
```

No single Engine owns this lifecycle. It is a composition of independent, replaceable responsibilities.

---

## 4. Current authority map

| Question | Current authority |
|---|---|
| What is Catalyst right now? What is active? | **this file** |
| What code is accepted? | GitHub `main` |
| Why does Catalyst exist? What are the layers, boundaries, and replacement rules? | `ARCHITECTURE.md` |
| What stable governance principles constrain growth? | `docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md` |
| What does Platform Standard Core v0.1 promise? | `PLATFORM_STANDARD_CORE_V0.1.md` |
| What execution behavior currently exists? | `agent_runtime/**` + active tests / CI |
| What is the current public coordination implementation? | `platform_standard/**` + active tests |
| How are real needs turned into solution decisions? | `platform-harness/skills/agent-construction/SKILL.md` |
| How are capability benchmarks designed? | `platform-harness/skills/capability-benchmark-design/SKILL.md` |
| How is capability behavior evaluated? | `platform-harness/skills/capability-evaluation/SKILL.md` |
| How are implementations evolved after evidence exists? | `platform-harness/skills/capability-optimization/SKILL.md` |
| Where is current reusable organizational value rediscovered? | `CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json` + referenced authority |
| Why preserve capability / Harvest? | `docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md` |
| How are repository changes governed? | `docs/DEVELOPMENT_WORKFLOW.md` |
| Where is historical Stage / Case / audit evidence? | `docs/history/README.md` + Git history / closed PRs / frozen refs |
| What implementation work is authorized now? | explicit bounded user-approved task / Stage, when one is active |

### Current-state supersession rule

Historical Architecture, governance, Stage, Handoff, audit, or PR records may contain `current stage`, baseline, readiness, or repository-name lines that were correct when written.

For **current-state questions only**, those old snapshot lines are superseded by this Operational Baseline and GitHub `main`.

Their durable evidence and decision history remain historical truth.

### Verification and evidence identities

The repository deliberately separates four different identities:

| Identity | Meaning |
|---|---|
| **Current state** | this Operational Baseline + accepted GitHub `main` |
| **Current contract / architecture** | `PLATFORM_STANDARD_CORE_V0.1.md` + `ARCHITECTURE.md` |
| **Current deterministic verification** | active tests + `.github/workflows/ci.yml` (`catalyst-platform-ci`) |
| **Historical evidence** | preserved V0.2 live campaigns, older Case / Stage evidence, frozen refs, and other immutable historical records |

The active `Protect main` repository ruleset targets the default branch and currently enforces PR-based changes, deletion protection, and non-fast-forward protection. **Catalyst CI is not currently configured as a GitHub-required status check**, so “current main is green” must not be read as “GitHub blocks every merge unless CI is green.”

The visible `.github/workflows/live-capability-eval.yml` and `platform-harness/live_eval/**` belong to the **historical Catalyst Minimum Usable V0.2 live-model evidence lineage**. They remain legitimate historical evidence at their tested identities, but they are not the current Operational V1 deterministic gate and do not provide continuous current recertification.

Likewise, `evidence/v0.2/**` contains registered immutable historical evidence. Registration preserves the accepted evidence chain; it does **not** mean the campaigns are automatically rerun, rewritten, or continuously recertified on current commits.

Current platform health should therefore be read from the current accepted `main` plus the current active deterministic CI for that commit. Historical failed or superseded runs remain legitimate development history and must not be rewritten as current release state.

---

## 5. Active platform surface

Operational V1 intentionally keeps the current surface small:

```text
CURRENT FRONT DOORS / CONTRACT
  README.md
  CATALYST_OPERATIONAL_BASELINE_V1.md
  ARCHITECTURE.md
  PLATFORM_STANDARD_CORE_V0.1.md

CURRENT NAVIGATION
  CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json

CURRENT EXECUTION / COORDINATION
  agent_runtime/**
  platform_standard/**
  enterprise_extensions/**

CURRENT METHODS
  platform-harness/skills/agent-construction
  platform-harness/skills/capability-benchmark-design
  platform-harness/skills/capability-evaluation
  platform-harness/skills/capability-optimization

CURRENT ORGANIZATIONAL ASSETS
  assets/**

CURRENT EVIDENCE / VERIFICATION
  active tests / current deterministic CI
  accepted closure/evaluation records referenced by current assets

HISTORICAL EVIDENCE
  evidence/v0.2/**
  historical live-model campaigns / evaluator infrastructure
  closed Case / Stage records and frozen refs

CURRENT PHILOSOPHY / GOVERNANCE
  docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md
  docs/governance/**
  docs/DEVELOPMENT_WORKFLOW.md
```

Anything outside this current surface is not active merely because it exists in Git history or another branch.

---

## 6. Capability / organizational asset state

The Capability Visibility Index remains deliberately tiny and reference-based. It is **not** a Registry, Capability contract, health model, dependency graph, or source of truth.

Operational V1 currently keeps three representative organizational values discoverable:

1. `compose_report@1.0.0` — formal Platform Capability.
2. Retrieval-gated memory query selection — harvested mechanism knowledge separated from the disposable source Agent.
3. Bounded fail-closed numeric safety — evidence-backed safety knowledge with explicit scope and limits.

The latter two live under `assets/knowledge/`. Their source Cases / external systems remain lineage and evidence, not current authority.

---

## 7. Case01 / Case02 disposition

Raw Case work is **not part of the Operational V1 `main` tree** and is not required to execute the current Platform.

Historical frozen refs:

```text
Case01
branch: case-01
head:   232d6837647c68670fba3f3b2faf7ec1fac73f0a
role:   historical product / Evaluation / evolution evidence

Case02
branch: case-02
head:   336f8e6f28c1569e5c53f245daaa3ee8a197f33d
role:   historical external-Agent decomposition / harvested-knowledge evidence
```

Useful value that earned preservation is represented in current organizational assets with explicit lineage.

> **Preserve capability, not the historical solution container.**

---

## 8. Historical asset disposition

The complete pre-Operational V1 repository state is preserved at:

```text
archive/pre-operational-v1
3986236db1dc66ee0bc78ac2a4264792d4a8f5fb
```

Closed Stage Specs, old Handoffs, pre-merge campaigns, Runtime implementation notes, research audits, and Case-specific proof fixtures do not belong in the current root.

Use `docs/history/README.md` to navigate historical evidence.

Git history, closed PRs, and frozen refs are preservation mechanisms. **The active root is not an archive.**

---

## 9. Root cleanliness contract

The repository root should remain approximately:

```text
README.md
ARCHITECTURE.md
CATALYST_OPERATIONAL_BASELINE_V1.md
CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json
PLATFORM_STANDARD_CORE_V0.1.md
```

plus implementation directories and normal repository configuration.

Do not reintroduce root-level Stage Specs, Handoffs, audit reports, one-off decision fixtures, or Case reports.

Current authority belongs only where its responsibility genuinely lives.

---

## 10. What Operational V1 does NOT claim

Operational V1 is **not** Production Exists.

It does not claim:

```text
production Capability Registry / DB
organization-wide UI / portal
continuous monitoring platform
online Evaluation service
automatic self-repair / replacement
Workflow Engine
Control Plane
full Authority / Policy / Approval system
production IAM / tenant isolation
universal Domain SDK
universal Enterprise Profile
second Runtime
Pi / Codex / DeepSeek / LangGraph dependency as platform identity
complete Building Regulation product
```

These remain absent unless future real use provides enough evidence for a bounded Stage.

---

## 11. External systems policy

Pi, Codex, DeepSeek Harness, LangGraph, Inspect, OpenTelemetry, MCP, Backstage, and future systems are legitimate:

```text
knowledge sources
mechanism references
implementation candidates
```

They are not Catalyst identity or architecture authority.

Default external-learning sequence:

```text
observe what works
→ identify the stable responsibility
→ remove product-specific assumptions
→ preserve provenance
→ compare with existing Catalyst value
→ reuse / adapt / externally adopt only when justified
→ evaluate in the real responsibility boundary
→ harvest only durable value
```

External adoption is first-class, not automatic.

---

## 12. Operational release gate

Minimum Operational V1 is active only when all are true:

```text
O-1  accepted main contains the consolidated current-state surface
O-2  current Catalyst Platform CI is green
O-3  root historical clutter is absent
O-4  Capability navigation resolves current assets without raw Case authority
O-5  current operational proof executes the Platform / Adapter / Runtime path
O-6  Construction / Benchmark / Evaluation / Optimization methods remain available
O-7  Phase 2 closure remains traceable
O-8  Runtime / Core remain free of Case / Domain / Enterprise-specific pollution
O-9  consolidation introduces no new Registry / Engine / Service / ontology
```

This is the accepted Catalyst release criterion. It does not imply that GitHub's branch ruleset currently enforces `catalyst-platform-ci` as a required merge status check.

If one fails, repair only the owning boundary. Do not expand the Platform to compensate.

---

## 13. STOP condition

When the Operational gate passes:

# **STOP PLANNED PLATFORM PRE-DEVELOPMENT**

There is no automatic Phase 4.

The main operating loop is:

```text
REAL USE
→ REAL FINDING
→ OBSERVE / ATTRIBUTE
→ EXISTING CAPABILITY SEARCH
→ INTERNAL / EXTERNAL ALTERNATIVE SEARCH
→ SMALLEST JUSTIFIED EVOLUTION CANDIDATE
→ EVALUATION
→ ACCEPT / ROLLBACK
→ HARVEST WHEN EARNED
→ REAL USE AGAIN
```

A future bounded Stage exists only when a real finding cannot be responsibly handled inside current accepted boundaries.

---

## 14. Documentation / governance hygiene rule

Documentation or governance hygiene may repair stale product names, role wording, status metadata, navigation references, and historical/current classification.

It must **not** use cleanup as an excuse to:

```text
redesign Runtime
expand Platform Core
add new functional layers
reopen closed Stages
rewrite historical evidence to look cleaner
```

Historical mistakes or superseded decisions should remain recoverable as history; current authority should simply classify them correctly.
