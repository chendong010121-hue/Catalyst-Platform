---
name: agent-construction
description: Understand a real need, discover reusable Catalyst Capabilities and evidence, choose the simplest justified solution form, and produce a bounded construction decision without changing Catalyst architecture authority.
short_description: Capability-first, solution-form-neutral construction method.
short_description_zh: 从真实需求出发，先复用能力，再选择最小可行方案形态。
version: 2
updated: 2026-08-26T15:32:00+08:00
---

# Agent Construction

## Status and authority

This is a replaceable Harness-side construction Skill. The historical name is retained for continuity; the method itself is solution-form neutral.

It is NOT:

- Catalyst Architecture authority;
- Platform Standard or a new Platform object;
- a Capability Registry, Pattern Registry, Mechanism Registry, or search service;
- a mandatory Agent object model;
- Runtime execution semantics;
- Evaluation, Admission, or Harvest authority;
- an implementation authorization by itself.

Core rule:

> Understand the need first. Search reusable Capability value second. Choose the simplest justified solution form third. Build only what remains necessary.

## 1. Accepted inputs

The input may be a raw user need, Task, existing Skill, Workflow, Agent, Service, Capability candidate, failed implementation, or an external complete solution.

Do not assume the requested noun is the correct architecture. A request to “build an Agent” may resolve to a Skill, Workflow, deterministic implementation, Service, Agent, or composition. A pre-existing Agent may be retained, decomposed, adapted, reconstructed, or replaced.

## 2. Step 1 — Understand the real need

Before architecture selection, identify:

- purpose / required outcome;
- observable responsibilities;
- delivery context;
- what is already known from supplied context or authoritative assets;
- material uncertainty that would change responsibility, risk, evidence, or solution form.

Infer what can safely be inferred. Ask a targeted clarification only when unresolved uncertainty is material. Do not convert harmless uncertainty into questionnaire overhead.

## 3. Step 2 — Establish responsibility and Capability need

Describe responsibilities as observable user/system obligations rather than modules or classes.

Then separate:

```text
REUSED CAPABILITY / ASSET VALUE
from
MISSING OR UNPROVEN CAPABILITY NEED
```

Do not mint a Platform Capability id for a provisional need. A Capability identity is referenced only when a stable governed identity already exists.

## 4. Step 3 — Capability Search before construction

Search in this order:

```text
Catalyst Capability Visibility Index
→ referenced authoritative Catalyst assets/evidence
→ installed Skills / local governed assets
→ trusted external Skills / mechanisms / complete solutions
→ only then consider new construction
```

The Visibility Index is navigation, not authority. Follow `authority_ref` / evidence / lineage references rather than copying their content into the construction decision.

Search for reusable semantic value, not only for the same asset form. A Capability may currently be represented by knowledge, a Skill, Workflow, deterministic implementation, Agent, Service, evaluation evidence, or a combination.

## 5. Step 4 — Choose reuse strategy

Use the smallest justified transition:

```text
REUSE
→ ADAPT
→ COMPOSE
→ RECONSTRUCT
→ BUILD NEW ONLY FOR THE REMAINING GAP
```

An existing solution may be reused even if it was built by Codex, DeepSeek, Penguin, another Harness, a human, or a future tool. External provenance must remain visible, but external code does not gain Catalyst architecture authority.

## 6. Step 5 — Characterize only what affects the solution

Record only material characteristics:

### Path predictability
- HIGH: predetermined steps/order;
- MEDIUM: known skeleton with bounded branching;
- LOW: next action materially depends on runtime observations.

### Knowledge boundary
- IN_CONTEXT;
- BOUNDED_CORPUS;
- OPEN_KNOWLEDGE;
- NO_EXTERNAL_KNOWLEDGE.

### Action boundary
- READ_ONLY;
- LOCAL_MUTATION;
- EXTERNAL_SIDE_EFFECT;
- PRIVILEGED_OR_HIGH_RISK.

### State horizon
- one-shot;
- multi-turn session;
- cross-session / durable;
- long-running / resumable.

### Quality / evidence
Identify whether proof requires deterministic output checks, provenance/citation, world-state verification, trajectory/tool evidence, repeated trials, or human/professional review.

### Risk
Record only risks that change design, approval, or evidence requirements.

Do not persist a full questionnaire when most dimensions are irrelevant.

## 7. Step 6 — Select the simplest justified solution form

Solution forms are delivery/execution choices, not value hierarchy:

```text
Skill
Deterministic implementation
Workflow / explicit orchestration
Service
Agent
Composition
Other
```

Prefer the least complex form that satisfies the current responsibility.

- bounded procedure → Skill or deterministic implementation;
- known ordered steps → Workflow / ordinary code;
- known routing/parallel structure → bounded orchestration;
- dynamic next action based on observations → Agent may be justified;
- reusable remotely operated boundary → Service may be justified;
- multiple forms may be composed when responsibility genuinely spans them.

Do not add an Agent loop because several steps exist. Do not add Multi-Agent because several responsibilities exist.

## 8. Step 7 — Select replaceable patterns and mechanisms

Patterns are reference techniques, not Catalyst ontology. Examples include prompt/Skill, fixed workflow, routing, parallelization, retrieval, plan-execute, bounded Agent loop, orchestrator-workers, evaluator-optimizer, and graph orchestration.

Mechanisms are replaceable implementations of the selected pattern. Examples:

- structured lookup / BM25 / semantic / hybrid retrieval;
- plain code / graph engine;
- local tool / MCP adapter;
- current Catalyst Runtime / another admissible runtime;
- current Catalyst Harness / another admissible Harness.

Use mature external machinery when it solves the mechanism. Do not create a Catalyst clone merely for ownership symmetry.

## 9. Step 8 — Emit Runtime requirements, do not absorb Runtime

Construction may state requirements such as:

- side-effect certainty;
- cancellation / timeout;
- durable session;
- restart / resumability;
- reconciliation;
- provider/tool constraints.

These are requirements handed to Runtime/execution infrastructure. Harness does not reimplement Runtime lifecycle or certainty semantics.

If current Runtime baseline is sufficient, record that and stop expanding execution architecture.

## 10. Step 9 — Emit Evaluation evidence requirements, do not absorb Evaluation

Construction defines what observable evidence would prove the responsibility. Evaluation remains free to choose benchmark, grader, sandbox, trial count, human rubric, or external evaluator.

Examples:

```text
BOUNDED_CORPUS + evidence-sensitive
→ source / citation fidelity evidence

EXTERNAL_SIDE_EFFECT
→ independent world-state verification

CROSS_SESSION_STATE
→ restart / persistence evidence

DYNAMIC_AGENT_LOOP
→ trajectory / tool-boundary evidence when material

HIGH_RISK_PROFESSIONAL_JUDGMENT
→ fail-closed + professional acceptance evidence
```

Do not define product responsibility by reverse-engineering the current implementation.

## 11. Construction Decision output

Return one compact, replaceable method-level record. It is NOT Platform Standard.

```text
1. NEED
   input_kind
   purpose_or_required_outcome

2. RESPONSIBILITY
   responsibilities[]
   material_uncertainties[]
   material_task_characteristics

3. CAPABILITY SEARCH
   reused_capability_refs[]
   reused_asset_or_evidence_refs[]
   missing_or_unproven_capability_needs[]

4. SOLUTION
   selected_solution_form
   selected_pattern_if_useful
   mechanism_or_implementation_candidate
   short_rationale

5. BOUNDARIES
   domain_or_enterprise_context_if_material
   runtime_execution_requirements_if_material
   material_risks[]

6. PROOF
   evidence_requirements[]
   not_required_now[]

7. GOVERNANCE
   stop_condition
```

Rules:

- references over copied authority;
- no fake Capability ids;
- no copied public schemas;
- no Evaluation score/health/Harvest verdict in this record;
- no Pattern/Mechanism ontology ids;
- fields may be omitted when genuinely irrelevant.

## 12. Relationship to Binding / Conformance / Runtime / Evaluation / Harvest

The method participates in this sequence:

```text
REAL NEED
→ UNDERSTAND
→ RESPONSIBILITY / CAPABILITY NEED
→ CAPABILITY SEARCH
→ REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD
→ SELECT SOLUTION FORM
→ CONSTRUCTION DECISION
→ Catalyst conformance/binding when applicable
→ Runtime/execution when applicable
→ raw evidence
→ Evaluation / attribution
→ Harvest / preserve / replace / do-not-harvest decision
```

Each downstream owner remains independent and replaceable.

## 13. External solution intake

For an external Skill/Workflow/Agent/Service:

1. pin source/revision when practical;
2. identify the responsibility it actually solves;
3. separate reusable mechanism from product-specific assumptions;
4. preserve provenance;
5. identify state, side-effect, tool, credential, and evidence boundaries;
6. reuse/adapt only the smallest useful portion;
7. keep admission/conformance/evaluation separate from construction.

Do not rebuild an external solution merely so Catalyst can claim authorship.

## 14. Harvest boundary

Construction does not decide Harvest. After evidence exists, Harvest may preserve:

- a Capability boundary;
- Skill/procedure;
- mechanism knowledge;
- Evaluation Pattern;
- compatibility/migration knowledge.

A whole Agent/Workflow may be disposable while some Capabilities remain reusable.

## 15. Stop rule

Stop construction expansion when the smallest selected solution satisfies the current responsibility and evidence requirements.

Do not add a Registry, Engine, Service, graph, monitoring layer, Agent, Workflow, model, retrieval stack, or other mechanism without a proven remaining responsibility that requires it.
