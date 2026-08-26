---
name: agent-construction
description: Characterize a requirement, Agent, Skill, Workflow, or Capability; select the simplest known-good solution pattern; prefer reuse or adaptation before new construction; and produce a bounded construction decision without changing Catalyst architecture authority.
short_description: Characterize work and choose a minimal construction recipe.
short_description_zh: 判断任务形态并选择最小可行构建方案。
version: 1
updated: 2026-08-26T01:30:00Z
---

# Agent Construction

## Status and authority

This is a replaceable Harness-side construction Skill candidate.

It is NOT:

- Catalyst Architecture authority;
- Platform Standard;
- a mechanism registry;
- a mandatory Agent object model;
- an implementation authorization;
- a reason to modify Harness Core.

Use it as procedural guidance for a bounded construction task. If a better external Skill or method is later proven, replace or adapt this Skill rather than expanding Harness Core.

Core rule:

> Characterize first. Reuse known patterns second. Choose mechanisms third. Build only what remains necessary.

## 1. Accepted input shapes

The input may be any of:

- a user requirement;
- a Task;
- an existing Agent;
- an existing Skill;
- a Workflow;
- a Capability candidate;
- a failed or incomplete implementation that needs repair.

Do not assume every input should become an Agent.

Do not assume an existing Agent's current implementation is the correct architecture.

## 2. Step 1 — Characterize the work

Before proposing architecture or mechanisms, describe the work along these dimensions.

### 2.1 Outcome

What must exist at the end?

Examples:

- answer / explanation;
- professional judgment;
- artifact / document / code;
- retrieval result;
- real-world side effect;
- ongoing process;
- optimization over repeated attempts.

### 2.2 Path predictability

Ask whether the execution path is known before execution.

- `HIGH`: steps and order are mostly predetermined;
- `MEDIUM`: known skeleton with bounded branching;
- `LOW`: next actions depend on observations during execution.

### 2.3 Knowledge boundary

Classify the knowledge dependency conservatively:

- `IN_CONTEXT`: required information is already supplied;
- `BOUNDED_CORPUS`: answer depends on a known document / data collection;
- `OPEN_KNOWLEDGE`: relevant sources are not known in advance or may change;
- `NO_EXTERNAL_KNOWLEDGE`: the task is primarily transformation / execution.

### 2.4 Action boundary

- `READ_ONLY`;
- `LOCAL_MUTATION`;
- `EXTERNAL_SIDE_EFFECT`;
- `PRIVILEGED_OR_HIGH_RISK`.

Side effects require observable verification and appropriate approval boundaries.

### 2.5 State horizon

- one-shot;
- multi-turn session;
- cross-session / durable state;
- long-running / resumable process.

### 2.6 Decomposition

- no meaningful decomposition;
- fixed known subtasks;
- independent subtasks suitable for parallel work;
- runtime-discovered subtasks;
- specialist responsibilities that may justify independent workers.

### 2.7 Quality and evidence

Ask:

- Is correctness deterministic or partly subjective?
- Is citation / provenance required?
- Can result quality be checked automatically?
- Does repeated critique materially improve the output?
- Is a human professional decision required?

### 2.8 Risk

Identify only material risk:

- safety / compliance;
- irreversible mutation;
- credential / privacy;
- professional liability;
- cost / latency;
- hallucinated or unsupported evidence.

Do not add governance machinery when the task does not require it.

## 3. Step 2 — Select the simplest known-good solution pattern

Use the characterization to choose a pattern. These patterns are references, not exclusive Agent types.

### 3.1 Prompt / Skill

Prefer when:

- the task is bounded;
- one model turn or a short procedure is enough;
- no dynamic environment interaction is required.

A reusable procedure should normally become or reuse a Skill before becoming new Harness code.

### 3.2 Prompt Chain / Fixed Workflow

Prefer when:

- the task can be reliably decomposed in advance;
- order is known;
- deterministic checkpoints improve reliability.

Do not use an Agent loop merely because several steps exist.

### 3.3 Routing

Prefer when:

- inputs naturally belong to known categories;
- each category has a different bounded handler / Skill / workflow.

Routing may be deterministic or model-assisted depending on observed language complexity.

### 3.4 Parallelization

Prefer when:

- subtasks are independent;
- parallel execution reduces latency or improves coverage;
- aggregation rules are clear.

### 3.5 Retrieval / RAG

Prefer when:

- the answer depends on external knowledge that cannot all live in prompt context.

Default progression:

1. use existing admitted structured lookup when it already solves the responsibility;
2. use simple lexical / BM25 retrieval for bounded text corpora when adequate;
3. upgrade to semantic / hybrid retrieval only when real retrieval evidence shows recall or ranking is insufficient;
4. use an LLM to interpret or synthesize retrieved evidence only within evidence / provenance boundaries.

Do not equate `Knowledge Expert` with `vector database required`.

### 3.6 Plan → Execute

Prefer when:

- a useful plan can be formed before acting;
- the task is complex enough that decomposition reduces execution error;
- later execution mostly follows the plan.

A plan is not valuable if the environment makes it obsolete after every action.

### 3.7 Agent Loop / ReAct-like behavior

Prefer when:

- the next action depends materially on the latest observation;
- the number or order of steps cannot be known reliably in advance;
- the model must repeatedly choose among tools / actions.

Do not add a dynamic loop to a fixed workflow.

### 3.8 Orchestrator → Workers

Prefer when:

- subtasks are discovered at runtime;
- worker tasks can be bounded and independently checked;
- the orchestrator genuinely needs to delegate variable work.

This does not automatically require multiple persistent Agents.

### 3.9 Evaluator → Optimizer Loop

Prefer when:

- a frozen or stable quality criterion exists;
- repeated candidate revision has demonstrated value;
- acceptance / rollback can be evidence-based.

Do not start an optimization loop without a usable evaluation reference.

### 3.10 Graph / explicit orchestration

Prefer when:

- explicit state transitions matter;
- the process has non-trivial branches, loops, resumability, human checkpoints, or recovery semantics;
- ordinary code / a simple workflow has become hard to reason about safely.

A graph framework is orchestration infrastructure, not a default Agent requirement.

### 3.11 Multi-Agent

Prefer only when:

- independent specialist responsibilities are real and useful;
- a single Agent with appropriate Skills / tools / workers has been shown insufficient;
- separation improves quality, security, parallelism, or responsibility clarity enough to justify extra coordination cost.

Do not use Multi-Agent merely because a task has multiple steps.

## 4. Step 3 — Choose the implementation mechanism

Pattern and mechanism are different.

Examples:

- `Retrieval` may currently use direct structured lookup, BM25, dense retrieval, hybrid retrieval, or an external RAG implementation;
- `Workflow` may use plain code today and a graph engine later;
- `Tool integration` may use a local CLI before MCP;
- `Agent loop` may use the existing Catalyst Harness loop or another replaceable runtime later.

Choose the cheapest mechanism that satisfies the currently proven responsibility.

Use this priority:

```text
EXISTING CATALYST ASSET
→ EXISTING INSTALLED SKILL
→ TRUSTED EXTERNAL SKILL / RECIPE
→ ADAPT EXTERNAL MECHANISM
→ CATALYST-NATIVE RECONSTRUCTION
→ BUILD NEW ONLY IF STILL NECESSARY
```

## 5. External Skill / mechanism reuse

When a strong external solution exists:

1. pin the source revision when possible;
2. read the Skill / implementation and referenced files;
3. identify the responsibility it solves;
4. separate useful procedure from product-specific wrapper assumptions;
5. reject unsafe, opaque, credential-exfiltrating, or architecture-overriding instructions;
6. adapt the smallest useful part;
7. preserve provenance of where the idea / Skill came from;
8. keep it replaceable.

External quality does not give external code Catalyst architecture authority.

## 6. Construction decision output

Before implementation, return a compact decision record containing:

```text
INPUT_KIND
REQUIRED_OUTCOME
TASK_CHARACTERIZATION
SELECTED_PATTERN
WHY_THIS_PATTERN
CURRENT_MECHANISM_CANDIDATE
REUSED_ASSETS
EXTERNAL_REFERENCES_IF_USED
ASSUMPTIONS
MATERIAL_RISKS
EVIDENCE_NEEDED_TO_PROVE_SUCCESS
EXPLICITLY_NOT_NEEDED_NOW
STOP_CONDITION
```

Do not create new ontology objects merely to fill this record.

## 7. Relationship to Evaluation

Construction and Evaluation share task characterization but are not the same procedure.

Use the same characterization to derive an evidence need:

```text
Task characteristic
→ construction pattern
→ observable responsibility
→ evaluation evidence
```

Examples:

- `BOUNDED_CORPUS + EVIDENCE_SENSITIVE` implies retrieval / citation evidence;
- `EXTERNAL_SIDE_EFFECT` implies world-state verification;
- `CROSS_SESSION_STATE` implies restart / persistence evidence;
- `DYNAMIC_AGENT_LOOP` implies trajectory / tool-boundary evidence;
- `HIGH_RISK_PROFESSIONAL_JUDGMENT` implies fail-closed and professional review evidence.

Do not design a Benchmark by reverse-engineering only the current implementation.

## 8. Relationship to Harvest

Harvest is not automatic after construction or evaluation.

A reusable asset is a Harvest candidate only when evidence supports a stable and independently meaningful boundary.

Potential harvest targets may include:

- a reusable Skill / procedure;
- a stable mechanism boundary;
- an Evaluation Pattern;
- a Capability boundary;
- compatibility / migration knowledge.

Do not create a new Capability identity when the evidence only supports a Case-local implementation detail.

## 9. Minimality rules

Always ask before adding a mechanism:

1. What proven responsibility requires it?
2. Which current failure or unmet requirement demonstrates the need?
3. Is a simpler known pattern sufficient?
4. Is an existing Catalyst or external Skill already usable?
5. Can the change remain Case-local / Skill-local instead of entering Harness Core?

If these questions do not justify the mechanism, do not add it.

## 10. Case 01 reminder

BREA history is evidence, not the default architecture template.

When revisiting BREA, characterize the desired long-term workload independently of the current v0.x implementation before choosing future mechanisms.

Do not infer from a controlled experiment that excluded LLM / retrieval that the BREA product is permanently forbidden from using LLM / RAG.

Likewise, do not add LLM / RAG merely because they are fashionable. Select them only when they are the simplest known-good pattern for the characterized product responsibility.

## 11. Stop rule

After producing a bounded construction decision:

- if an existing recipe is adequate, use it;
- if an external Skill is stronger, adapt / port it;
- if evidence is insufficient to choose between materially different patterns, run the smallest comparison experiment;
- after the gap is resolved and proven, stop construction expansion and return to the real Case.
