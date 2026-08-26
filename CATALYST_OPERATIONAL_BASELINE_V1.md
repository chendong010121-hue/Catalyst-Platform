# Catalyst Platform — Operational Baseline V1

> **Baseline type:** current-state / operational release baseline  
> **Target state:** **CATALYST MINIMUM OPERATIONAL V1**  
> **Valid when:** this baseline is present on accepted GitHub `main` and the active Catalyst Platform CI for that commit is green  
> **Platform pre-development after activation:** **STOP**  
> **Next operating mode:** controlled real use → evidence-driven evolution

This file is the **single current-state front door** for Catalyst Platform. It does not replace `ARCHITECTURE.md`, Platform Standard contracts, Evaluation evidence, or governance authority. It answers one question:

> **What is Catalyst now, what is currently usable, where is the authority/evidence, and when must platform-building stop?**

---

## 1. Product identity

The product is:

# **Catalyst Platform**

The directory/package:

```text
agent_runtime/**
```

is one replaceable Runtime implementation inside Catalyst Platform. It is intentionally **not** renamed as part of product naming because Runtime remains a replaceable HOW.

The historical GitHub slug `agent-runtime` is administrative metadata, not architectural identity. The repository naming target is `catalyst-platform`; changing the slug must not trigger a Runtime, contract, or package redesign.

---

## 2. What has been proven before Operational V1

Catalyst enters Operational V1 with the following evidence chain already accepted:

```text
Minimum Architectural Framework v1
→ PROVEN / ACCEPTED

Platform Integration V0.1
→ minimal Capability visibility
→ Capability-first Construction
→ Construction responsibility/evidence handoff
→ cross-component execution/attribution proof
→ COMPLETE / STOPPED

Catalyst Minimum Usable V0.2
→ real model API
→ real external API/tool
→ benchmark + raw evidence + evaluation
→ bounded Candidate + same-benchmark re-evaluation
→ accept / rollback
→ PASS / MERGED

Phase 2 — Governed Capability Adoption
→ real Building Regulation Evidence Capability local pilot
→ Domain × Enterprise separation
→ replaceable implementation
→ real professional evidence / fail closed
→ Post-Pilot Architecture Review
→ post-close evidence recertification
→ COMPLETE — PASS

Capability-Preserving Evolution
→ evidence-backed stable architecture principle
→ capability-optimization v2 as replaceable method
→ MERGED
```

The formal Phase 2 closure evidence remains at:

```text
docs/governance/CATALYST_PHASE_2_CLOSURE_REVIEW_V0.1.md
```

Its accepted post-close recertification manifest identity is:

```text
cd8c28b58a563ea7d16e8711eb44076f70fde4d146f742c0be6bd6cc9bd06759
```

---

## 3. Operational V1 thesis

Catalyst is ready for controlled real use when the existing pieces can be treated as one small capability lifecycle rather than as a roadmap for more platform objects:

```text
REAL NEED
  ↓
RESPONSIBILITY / CAPABILITY NEED
  ↓
DISCOVER EXISTING ORGANIZATIONAL VALUE
  ↓
REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD ONLY THE GAP
  ↓
SELECT SIMPLEST VALID SOLUTION FORM
  ↓
BIND / EXECUTE WHEN APPLICABLE
  ↓
RAW EVIDENCE
  ↓
EVALUATE / ATTRIBUTE
  ↓
PRESERVE WHAT MUST SURVIVE
  ↓
REPAIR / REBUILD / REPLACE / RECOMPOSE / ADOPT / RETIRE AS JUSTIFIED
  ↓
SAME RESPONSIBILITY / BENCHMARK / EVIDENCE BOUNDARY
  ↓
ACCEPT OR ROLLBACK
  ↓
HARVEST DURABLE VALUE
  ↓
FUTURE REUSE
```

No single Engine owns this lifecycle. The lifecycle is a composition of independent, replaceable responsibilities.

---

## 4. Current authority map

| Question | Current authority |
|---|---|
| What is Catalyst right now? What should a contributor use first? | **this file** |
| Why does Catalyst exist? What are the layers, boundaries and replacement rules? | `ARCHITECTURE.md` |
| What stable governance principles constrain growth? | `docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md` |
| What does Platform Standard Core v0.1 promise? | `PLATFORM_STANDARD_CORE_V0.1.md` |
| What code is accepted? | GitHub `main` |
| What execution behavior is currently implemented? | `agent_runtime/**` + active tests |
| What is the current public coordination implementation? | `platform_standard/**` + Platform tests |
| How are real needs turned into solution decisions? | `platform-harness/skills/agent-construction/SKILL.md` |
| How are capability benchmarks designed? | `platform-harness/skills/capability-benchmark-design/SKILL.md` |
| How is capability behavior evaluated? | `platform-harness/skills/capability-evaluation/SKILL.md` |
| How are implementations evolved after evidence exists? | `platform-harness/skills/capability-optimization/SKILL.md` |
| Where can current reusable organizational value be rediscovered? | `CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json` |
| Who may implement/publish/merge and how? | `docs/DEVELOPMENT_WORKFLOW.md` |
| Where are old Stages/Cases/pre-Operational artifacts? | `docs/history/README.md` + Git history / archive refs |

### Current-state supersession rule

Older architecture/governance documents may contain embedded `current stage`, `accepted baseline`, or readiness lines that were correct when written. For **current-state questions only**, those snapshot lines are superseded by this Operational Baseline. Their durable architecture/governance meaning remains authoritative within their responsibility.

This prevents historical status metadata from becoming a second current-state authority.

---

## 5. Current minimal platform surface

Operational V1 intentionally keeps the active surface small:

```text
CURRENT CONSTITUTION / CONTRACT
  README.md
  ARCHITECTURE.md
  CATALYST_OPERATIONAL_BASELINE_V1.md
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

CURRENT EVIDENCE
  evidence/**
  active tests / CI
  accepted closure/evaluation records referenced from the current assets
```

Anything outside this current surface is not automatically active just because it exists in history.

---

## 6. Capability / organizational asset state

The Capability Visibility Index remains deliberately tiny and reference-based. It is **not** a Registry, Capability contract, health model, dependency graph, or source of truth.

Operational V1 keeps three representative organizational states discoverable:

1. `compose_report@1.0.0` — formal Platform Capability.
2. Retrieval-gated memory query selection — governed harvested mechanism knowledge, separated from the disposable source Agent.
3. Bounded fail-closed numeric safety — evidence-backed safety knowledge with explicit scope/limits.

The latter two are stored as current Catalyst organizational assets under `assets/knowledge/`; their source Case/external systems remain lineage/evidence, not current authority.

---

## 7. Case01 / Case02 disposition

Raw Case work is **not part of the Operational V1 mainline tree**.

Historical refs are frozen as:

```text
Case01
branch: case-01
head:   232d6837647c68670fba3f3b2faf7ec1fac73f0a
role:   historical product/evaluation/evolution evidence

Case02
branch: case-02
head:   336f8e6f28c1569e5c53f245daaa3ee8a197f33d
role:   historical external-Agent decomposition / harvested-knowledge evidence
```

Operational V1 must not require those branches to execute the current Platform. Useful knowledge that earned preservation is re-expressed as a small current organizational asset with explicit lineage; the raw Case remains historical evidence.

This is the practical meaning of:

> **Preserve capability, not the historical solution container.**

---

## 8. Historical asset disposition

The complete pre-consolidation repository tree is preserved at:

```text
archive/pre-operational-v1
3986236db1dc66ee0bc78ac2a4264792d4a8f5fb
```

Closed Stage Specs, old Handoffs, pre-merge campaigns, runtime implementation notes, research audits, and Case-specific proof fixtures are removed from the Operational V1 root rather than copied into a second active authority surface.

Use `docs/history/README.md` to navigate historical evidence.

Git history / frozen refs are the preservation mechanism; **the active root is not an archive**.

---

## 9. Root cleanliness contract

The repository root is intentionally restricted to the smallest current front-door set plus implementation directories.

Current root documents should remain approximately:

```text
README.md
ARCHITECTURE.md
CATALYST_OPERATIONAL_BASELINE_V1.md
CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json
PLATFORM_STANDARD_CORE_V0.1.md
```

Do not reintroduce new root-level Stage Specs, Handoffs, audit reports, one-off decision fixtures, or Case reports.

New historical records belong behind a clearly bounded Stage/evidence location or Git ref. New current authority belongs only where its responsibility genuinely lives.

---

## 10. What Operational V1 does NOT claim

Operational V1 is **not** a claim of Production Exists.

It does not claim:

```text
production Registry / Capability DB
organization-wide UI / portal
continuous monitoring / alerting
online Evaluation platform
automatic self-repair or replacement
Workflow Engine
Control Plane
full Authority / Policy / Approval system
production IAM / tenant isolation
universal Domain SDK
universal Enterprise Profile
second Runtime
Pi / LangGraph / external Harness dependency
complete building-regulation product
```

These remain absent unless future real use provides enough evidence to justify a bounded Stage.

---

## 11. External systems policy

Pi, Codex, DeepSeek, LangGraph, Inspect, OpenTelemetry, MCP, Backstage, and future systems are legitimate:

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
→ compare against existing Catalyst assets
→ reuse / adapt / externally adopt only when justified
→ evaluate in the real responsibility boundary
→ harvest only durable value
```

External adoption is a candidate, not the default outcome of learning.

---

## 12. Operational release gate

Minimum Operational V1 is active only when all are true:

```text
O-1  accepted main contains this consolidated current-state surface
O-2  current Catalyst Platform CI is green
O-3  root historical clutter is removed
O-4  current Capability navigation resolves current assets without raw Case authority
O-5  current operational proof executes the existing Platform/Adapter/Runtime path
O-6  Capability Construction / Benchmark / Evaluation / Optimization methods remain available
O-7  Phase 2 closure remains traceable
O-8  Runtime/Core remain free of Case/Domain/Enterprise-specific expansion
O-9  no new Registry/Engine/Service/ontology was introduced for consolidation
```

If one fails, repair only the owning boundary; do not expand the Platform to compensate.

---

## 13. STOP condition

When the Operational release gate passes:

# **STOP PLANNED PLATFORM PRE-DEVELOPMENT**

There is no automatic Phase 4.

The next mainline is real use:

```text
REAL USE
→ real finding
→ observe / attribute
→ existing Capability search
→ internal/external alternative search
→ smallest justified evolution candidate
→ evaluation
→ accept / rollback
→ harvest
→ real use again
```

A future bounded Stage exists only when a real finding cannot be responsibly handled inside current accepted boundaries.

---

## 14. Post-release governance review

Operational V1 intentionally does not use consolidation as an excuse to redesign governance. After the platform is frozen and used, governance documents may be reviewed for stale role/status wording as a separate bounded documentation/governance task.

That review must not reopen closed platform feature work without new evidence.
