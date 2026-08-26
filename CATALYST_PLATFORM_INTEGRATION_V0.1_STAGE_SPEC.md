# CATALYST PLATFORM INTEGRATION V0.1 — STAGE SPEC

> **Status:** AUTHORIZED INTEGRATION STAGE — CONSOLIDATION FIRST
> **Implementation scope:** asset consolidation, responsibility/evidence handoff, Harness construction-method integration, cross-component proof
> **Case01:** PAUSED
> **Case02:** PAUSED
> **Platform Core functional expansion:** FORBIDDEN
> **Runtime functional change:** FORBIDDEN
> **Generic Registry / DB / Control Plane:** FORBIDDEN
> **Goal:** turn the already-proven Catalyst parts into one connected, replaceable system before further Agent development.

---

## 0. Project identity

The product/repository system identity is:

# **Catalyst Platform**

`agent_runtime/**` is one replaceable Runtime implementation inside Catalyst Platform. It is not the identity of the Platform.

The GitHub repository slug may still temporarily remain `agent-runtime`; repository naming is an administrative migration and does not redefine architectural ownership.

---

## 1. Why this integration stage exists

Catalyst already has valuable pieces distributed across `main`, `platform-harness`, Case01, Case02 and evaluation artifacts:

- Runtime execution semantics;
- Platform Standard Core v0.1;
- Capability identity/version/public contracts;
- Adapter and direct-binding conformance evidence;
- Extension-first governance;
- Harness execution substrate;
- Harness architecture and construction-method candidate;
- Case-local Evaluation with failure attribution and Harvest-oriented findings;
- Capability decomposition / reconstruction / lineage evidence;
- governance, Stage authorization, audit and exact-SHA evidence.

The current risk is no longer absence of mechanisms. The risk is fragmentation:

```text
existing value is hard to rediscover
→ a new Stage re-analyzes the same problem
→ another local abstraction is created
→ Harness / Runtime / Evaluation / Harvest each develops its own language
→ replaceability remains theoretical but the system loses coherence
```

This Stage therefore prioritizes **consolidation before expansion**.

---

## 2. Stable model that MUST be preserved

### 2.1 Agent and Capability are complementary

```text
AGENT
= primary governed operational / delivery / admission unit

CAPABILITY
= reusable, composable, replaceable semantic asset unit
```

Agent governance MUST NOT be replaced by Capability-first thinking.
Capability search MUST NOT collapse into Skill search.

### 2.2 Shared semantic spine

Harness, Runtime, Evaluation and Harvest remain separate responsibilities but MUST connect through shared identities and evidence:

```text
REAL NEED
  ↓
UNDERSTAND / TARGETED CLARIFICATION
  ↓
AGENT RESPONSIBILITY
  ↓
CAPABILITY SEARCH
  ↓
REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD
  ↓
HARNESS CONSTRUCTION
  ↓
CATALYST CONFORMANCE
  ↓
RUNTIME EXECUTION
  ↓
RAW EVIDENCE
  ↓
EVALUATION / ATTRIBUTION
  ↓
EVALUATED EVIDENCE
  ↓
HARVEST / PRESERVE / REPLACE / DO NOT HARVEST
  ↓
FUTURE REUSE
```

The shared spine is:

```text
Agent identity
Responsibility
Capability identity/version
Evidence
Lineage
Bindings
Known limits
Replacement knowledge
```

Do NOT create separate Understanding / Construction / Evaluation / Harvest analyzers for the same responsibility.

---

## 3. Current capability-recording truth

Current Catalyst already proves:

- stable Capability identity and version;
- versioned public input/output/execution contract;
- Standard descriptor registration and lookup;
- same-ID multi-version routing;
- implementation Binding / Conformance checks;
- invocation / result / artifact / trace attribution;
- evidence-backed replacement principles;
- Case-local evaluation evidence and Harvest findings.

Current Catalyst DOES NOT yet prove:

- a persistent organization-wide Capability asset ledger;
- discovery of every Capability asset form across all branches / Cases;
- a dependency / impact graph;
- automatic continuous health monitoring;
- automatic replacement;
- production Registry / Capability DB.

Therefore the current state is:

```text
CAPABILITY IDENTITY / CONTRACT / REPLACEABILITY BOUNDARY
= EVIDENCE-BACKED

ORGANIZATION-WIDE CAPABILITY ASSET VISIBILITY
= INTEGRATION GAP

PROACTIVE AUTOMATIC CAPABILITY HEALTH MONITORING
= NOT YET IMPLEMENTED
```

This Stage must close the visibility/handoff gap with the smallest evidence-backed mechanism. It MUST NOT jump directly to a production Registry service.

---

## 4. Capability visibility and issue propagation target

The integration target is that any admitted/used Capability can be traced to a single semantic identity and its current evidence, regardless of where the implementation lives.

Minimum information that must be recoverable:

```text
capability identity + version
problem / semantic intent
responsibility boundary
asset forms that currently exist
  - record / knowledge
  - skill / recipe
  - implementation
  - evaluation evidence
lineage / provenance
Domain / Enterprise / Agent bindings when applicable
known limits / unproven boundaries
current implementation binding(s)
replacement / migration knowledge when known
latest material evidence / failure attribution
```

### Issue propagation rule

When a material failure is observed in Harness construction, Binding/Conformance, Runtime execution, Evaluation, or real use:

```text
OBSERVED FAILURE
  ↓
identify affected Agent + Capability identity/version when possible
  ↓
classify owning responsibility
  ↓
attach evidence / attribution to the same identity
  ↓
mark the boundary as limited / unproven / replacement-candidate as supported by evidence
  ↓
do not silently mutate another layer
```

V0.1 does NOT require background monitoring. The first proof is deterministic evidence propagation through an actual workflow. Continuous monitoring is a later requirement only if real operation justifies it.

---

## 5. External-reference policy

Catalyst deliberately learns from external systems, but external systems do not become Catalyst authority.

Known evidence donors include, at different levels:

- Penguin Harness: Harness/session/workspace/tool/approval separation, asset-aware construction, evaluation/optimization mechanisms;
- Codex / DeepSeek Harness: practical repository-development execution behavior;
- Inspect-style evaluation: frozen task/sample identity, public/private isolation, reproducible structured runs;
- Anthropic agent-eval methodology: task/trial/grader/infrastructure separation and responsibility-oriented evaluation;
- LangSmith: run evidence → dataset/regression feedback lifecycle;
- OpenAI testing principles: verify behavior at the real responsibility boundary and do not overclaim test doubles;
- Waku / Case02: real Agent decomposition, native evaluation/release evidence, state/side-effect verification and capability reconstruction;
- Catalyst Case01: professional evidence binding, fail-closed behavior, knowledge revision identity and governed Candidate evolution.

Rule:

```text
EXTERNAL METHOD / MECHANISM
  ↓
understand responsibility
  ↓
remove product-specific assumptions
  ↓
map to Catalyst boundary
  ↓
prove in a real Catalyst context
  ↓
preserve provenance
  ↓
keep replaceable
```

Catalyst-specific authority remains in:

```text
Agent identity / responsibility / admission
Capability semantic identity and public promise
Domain / Enterprise meaning
Stage authorization
Evidence / attribution
Lineage / binding
Harvest / preserve / replace authority
Platform Standard evolution
```

---

## 6. Integration sequence

### Phase I — Asset Census (READ-ONLY FIRST)

Inventory existing assets across `main`, `platform-harness`, Case01, Case02 and prior accepted evidence.

Classify each item as one or more of:

```text
Platform Contract
Runtime implementation/evidence
Adapter/Binding
Harness implementation/method
Agent
Capability record
Knowledge
Skill/Recipe
Workflow/Pattern
Evaluation pattern/evidence
Governance/Lineage
Case-local artifact
```

Required outcome:

- identify duplicated responsibility descriptions;
- identify assets that already solve proposed new work;
- identify stale/contradictory status claims;
- identify branch-only assets that are valuable but not yet Platform-integrated;
- do NOT move/merge code merely to make the tree look tidy.

### Phase II — Minimal Capability Asset Index

Create the smallest persistent index sufficient to rediscover existing organizational capability and its evidence.

Constraints:

- file-backed / repository-native first;
- reference existing authoritative artifacts instead of copying them;
- no production Registry service;
- no graph DB;
- no new Platform Core object unless later evidence requires it;
- must distinguish Agent identity from Capability identity.

Representation is selected only after Phase I shows the minimum useful fields.

### Phase III — Shared Responsibility / Evidence Handoff

Define a minimal replaceable method-level handoff used by Construction and Evaluation.

It must be able to carry, when relevant:

```text
TARGET / NEED
AGENT PURPOSE
RESPONSIBILITIES
DOMAIN / ENTERPRISE CONTEXT
CAPABILITY CLAIMS / REUSED CAPABILITIES
KNOWLEDGE BOUNDARY
ACTION BOUNDARY
STATE HORIZON
RUNTIME EXECUTION REQUIREMENTS
MATERIAL UNCERTAINTIES
MATERIAL RISKS
EVIDENCE NEEDED
NOT REQUIRED NOW
LINEAGE / SOURCE CONTEXT
```

This is NOT automatically a new Platform Core schema.

### Phase IV — Harness Construction Method Integration

Repair the existing replaceable `agent-construction` Skill rather than expanding Harness Core.

Required method:

```text
UNDERSTAND
→ infer what can be inferred
→ identify material uncertainty
→ targeted clarification only when material
→ confirm Agent responsibility
→ Capability Search
→ reuse / adapt / compose / reconstruct / build
→ characterize work
→ select replaceable reference pattern
→ select mechanism
→ invoke/compose relevant Skills/assets
→ construct bounded Agent/Skill/Workflow/implementation
→ produce Runtime requirements + Evaluation evidence requirements
→ Catalyst conformance handoff
```

Mandatory corrections:

- Capability Search > Skill Search;
- Pattern list is non-exhaustive / replaceable reference methodology;
- Agent remains primary governed operational/delivery unit;
- Capability remains reusable asset unit;
- Harness != Runtime;
- Harness does not own Evaluation/Admission authority;
- remove Case-specific procedure from the generic Skill.

### Phase V — Cross-component Integration Proof

Before returning to Case01, prove one small end-to-end identity/evidence chain:

```text
shared Agent/Capability responsibility
→ Harness decision / construction evidence
→ conformance/binding
→ Runtime execution
→ trace/result evidence
→ Evaluation attribution
→ same Capability record/evidence update
```

Pass requires that a failure at one layer is attributable without rewriting another layer's semantics.

### Phase VI — Case01 as first real Construction validation

Only after Phases I–V pass:

- do NOT resume patch-driven BREA history by default;
- give the real Case01 product need to Catalyst Harness;
- require Harness to understand/clarify/search existing capabilities first;
- allow reuse of existing BREA/Knowledge/Evaluation/Harvest evidence;
- allow an alternative simpler architecture if evidence supports it;
- construct a new governed Agent Candidate from the real need;
- then run → evaluate → harvest using the integrated lifecycle.

Case01 is a validation Case, not architecture authority.

---

## 7. Explicit non-goals

This Stage does NOT authorize:

```text
Capability production Registry / DB
Asset Graph / Graph DB
automatic capability replacement
background monitoring service
Control Plane
new Workflow Engine
new Evaluation Service
new Harvest Service
new Understanding Engine
Pattern Registry
Mechanism Registry
Platform Standard v0.2
Runtime rewrite / second Runtime
Case01 feature patching before integration proof
Case02 live evaluation
```

---

## 8. Success criteria

This integration Stage succeeds when all are true:

1. A contributor can discover what Catalyst already has before proposing new construction.
2. Agent and Capability identities are not conflated.
3. Harness, Runtime and Evaluation refer to compatible Responsibility/Evidence meaning.
4. A Capability implementation can be replaced without silently changing its public semantic promise.
5. A material failure can be attributed to its owning layer and attached to the affected Agent/Capability evidence.
6. Existing external ideas retain provenance but do not become architecture authority.
7. Catalyst-owned meaning/evidence/lineage survives replacement of Harness, Runtime, Skill, model or evaluator implementation.
8. No new Core object/service is introduced solely for conceptual neatness.
9. Case01 can be handed to Catalyst Harness as a real need rather than manually continued as a patch chain.

---

## 9. Stop conditions

STOP and return to Architecture Review if any of these occur:

- integration requires Runtime to own Domain/Enterprise meaning;
- Harness must become mandatory for all admitted Agents;
- Evaluation requires reverse-engineering implementation to define product responsibility;
- Capability-first design erases Agent admission/execution responsibility;
- a new Core field/service is proposed without repeated cross-boundary evidence;
- asset consolidation copies or rewrites authoritative evidence instead of referencing it;
- repository tidiness is used as justification for semantic migration;
- the Stage starts developing Case01 product features before integration proof.

---

## 10. First authorized action after this Stage Spec

The next action is **Phase I — Asset Census only**.

No functional implementation is authorized by this document until the census is reviewed and the minimum integration gap is confirmed.
