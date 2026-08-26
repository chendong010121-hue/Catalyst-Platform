# CATALYST V0.2 — MULTI-TOOL REPAIR / REPLACE DESIGN REVIEW

> Status: ARCHITECTURE / IMPLEMENTATION-CHOICE REVIEW
> Implementation authorization: **NO — review first, then implement the accepted candidate**
> Branch under review: `stage/catalyst-minimum-usable-v0.2`
> Reviewed head at start: `138bc30439be79a38aef8ba0fc3779791c887997`
> Scope: Harness native tool-call interaction only

## 1. Problem statement

The first real DeepSeek preflight exposed a concrete Harness compatibility gap:

```text
real model API                 works
provider response              works
model emits multiple tool calls
                               ↓
current native-tools v0.1 assumes exactly one tool call
                               ↓
DecisionParseError before tool execution
```

This is not evidence that the whole Catalyst Harness, Runtime, Capability model, or Platform architecture is wrong.

The current code already supports multiple `ModelToolCall` values at the provider-neutral message/response data level, but the current Reasoner/Core interaction contracts intentionally collapse a model turn to a single `Act(Action)` and validate native v0.1 as exactly one tool call.

The question is therefore not only "how do we make this pass?". The correct Catalyst question is:

> Should we PATCH the existing mechanism, REBUILD the affected component, ADOPT an external mature mechanism, or REPLACE the larger Harness?

## 2. External mature-pattern review

### 2.1 Provider-side model turn

Current OpenAI and DeepSeek APIs both treat multiple tool calls in one model response as normal behavior.

Common provider-level pattern:

```text
one model turn
→ zero / one / many tool-call intents
→ each call has its own call id + name + arguments
```

DeepSeek Chat Completions allows `auto` to choose one or more tools. Its Responses compatibility layer reports parallel tool calling as always enabled.

### 2.2 Harness-side execution is a separate concern

OpenAI Agents SDK distinguishes:

```text
provider-side: may the model emit multiple tool calls?

from

SDK-side: how many emitted local tool calls may execute concurrently?
```

This separation is important for Catalyst. Supporting multiple calls does **not** require parallel execution.

### 2.3 Correlation

LangChain/LangGraph preserves every emitted call and returns every tool result with the matching `tool_call_id` so the next model turn can correlate result ↔ request correctly.

Typical shape:

```text
assistant message
  tool_call A [id=A]
  tool_call B [id=B]

execution
  result A [tool_call_id=A]
  result B [tool_call_id=B]

next model turn
```

### 2.4 Parallelism is conditional, not universal

Mature frameworks may parallelize independent tools, but stateful/checkpointed workloads can require serialization. LangGraph explicitly documents cases where parallel calls can conflict through shared checkpoint state.

Therefore Catalyst V0.2 should not add a parallel execution engine merely because a provider emitted multiple calls.

## 3. Catalyst invariants worth preserving

The current implementation already has valuable, tested execution semantics:

```text
Policy
→ durable PendingExecution before real execution
→ execution_id
→ Capability execution
→ authoritative Observation or explicit uncertainty
→ durable settlement
→ recovery / reconciliation boundary
```

Those semantics are not the observed failure owner.

Likewise, the provider-neutral model value objects already represent multiple `ModelToolCall` values. The observed incompatibility begins where native-tools v0.1 translates a whole model turn into one `Decision = Act(Action)` and where snapshot validation enforces exactly one native tool call per Act.

Therefore the stable value to retain is:

```text
single real execution
→ single execution identity
→ explicit policy decision
→ explicit certainty / pending semantics
→ explicit observation
```

The assumption to discard is:

```text
one model turn == one real execution
```

## 4. Candidate decision matrix

### Candidate A — PATCH native-tools v0.1

Example shape:

```text
remove / weaken `len(tool_calls) > 1` guard
add branches and special cases around existing Act logic
```

Verdict: **REJECT**

Reasons:

- current `Decision`, `StepRecord`, native history reconstruction, and snapshot consistency all encode the single-call assumption;
- deleting the parser guard alone would create inconsistent evidence semantics;
- accumulating compatibility branches would make v0.1 harder to understand and replace;
- this is exactly the kind of repair that risks making Catalyst heavier and dirtier over time.

### Candidate B — REBUILD the affected native-tool interaction component as v2

Verdict: **ACCEPT AS PRIMARY IMPLEMENTATION CANDIDATE**

Principle:

```text
freeze native-tools v0.1
+
build a clean native-tools v0.2 interaction mechanism
```

The new mechanism starts from the correct primitive:

```text
Model Turn
→ 0..N Tool Calls
```

while each real tool execution still preserves the existing Catalyst execution lifecycle.

### Candidate C — ADOPT / ADAPT a mature external Tool Loop now

Candidate mechanisms include LangGraph ToolNode, OpenAI Agents SDK, Pydantic AI, or another mature Harness.

Verdict: **WATCH / CONDITIONAL FOLLOW-UP — NOT CURRENT DEFAULT**

Positive evidence:

- mature multi-call correlation;
- mature execution scheduling;
- error handling / approval / tracing already exist;
- likely lower long-term maintenance cost if Catalyst eventually needs a broad standard Agent loop.

Current integration cost:

- these frameworks already own significant portions of tool execution, state, orchestration, retries, tracing, or agent-loop semantics;
- a thin-looking adapter may silently bypass or duplicate Catalyst's tested PendingExecution / execution-certainty / reconciliation semantics;
- replacing the loop today would be broader than the observed failure evidence justifies.

External adoption becomes preferred if a later design spike proves that one of these mechanisms can preserve Catalyst's required execution/evidence contract through a genuinely thin adapter.

### Candidate D — REPLACE the whole Catalyst Harness now

Verdict: **REJECT FOR CURRENT EVIDENCE**

The observed failure does not implicate:

- capability-benchmark-design;
- capability-evaluation;
- capability-optimization;
- construction method;
- provider-neutral contracts as a whole;
- Runtime execution certainty as a whole.

Replacing all of them because one native interaction component has an obsolete assumption would discard more proven value than necessary.

## 5. Accepted minimum v2 direction

The implementation candidate should remain Harness-side and replaceable. It must **not** become Platform Standard or a new Platform Core service.

### 5.1 Preserve v1 as a frozen reference

Do not mutate native-tools v0.1 into a different protocol while retaining the old name and tests.

v1 remains useful as:

- deterministic regression reference;
- compatibility reference for single-call providers / tests;
- rollback target.

### 5.2 Add an explicit model-turn concept

The new mechanism must distinguish:

```text
MODEL TURN
assistant output + usage + finish reason + 0..N tool calls

from

TOOL EXECUTION
one concrete Action + one execution identity + one result
```

Exact class names are implementation details and are not authorized by this review. The conceptual boundary is required.

### 5.3 Sequential execution first

V0.2 should execute emitted calls in deterministic order first:

```text
Call A
→ policy / pending / execute / settle

Call B
→ policy / pending / execute / settle

Call C
→ policy / pending / execute / settle
```

No parallel execution engine is required for V0.2.

Parallelism may be considered later only when evidence shows latency matters and capability side-effect/state semantics permit safe concurrency.

### 5.4 Preserve call correlation

For every call, preserve at least:

```text
tool_call_id
tool name / Capability id
arguments / Action
policy verdict
execution_id
Observation or execution uncertainty
```

When returning results to the model, each result must reference the original `tool_call_id`.

### 5.5 Preserve durable batch progress

Sequential execution alone is insufficient if batch progress exists only in memory.

The v2 design must answer:

> If Call A settles, the process crashes before Call B starts, how does recovery know that A is complete and B/C remain part of the same model turn?

Therefore the accepted implementation must preserve enough durable model-turn/batch progress to distinguish:

```text
not yet started calls
current unresolved execution
already settled calls
completed model turn ready to return results
```

Do not fake this by simply looping over the provider response in memory.

### 5.6 Keep provider behavior provider-neutral

Do not add DeepSeek-specific multi-tool branches to AgentCore or Platform contracts.

The v2 mechanism should consume provider-neutral `ModelToolCall` facts. Provider adapters remain responsible only for mapping vendor envelopes into those facts.

## 6. Self-observability / failure attribution requirement

This failure should also become the first concrete proof that Catalyst Harness can move from self-observation toward self-diagnosis.

Each live evaluation failure should be able to preserve a bounded attribution record such as:

```text
stage
owner
failure_type
observed_fact
expected_contract_or_capability
model/provider call completed? yes/no
downstream tool execution started? yes/no
side-effect certainty
unproven downstream boundary
evidence reference
```

For the current failure, the desired automatic shape would be approximately:

```text
stage: native_model_interaction
owner: Harness native-tool protocol
failure_type: unsupported_model_turn_shape
observed_fact: multiple tool calls emitted
provider_completed: true
downstream_tool_execution_started: false
side_effect_certainty: none
unproven_boundary: external tool behavior
```

This attribution belongs to Harness-side evaluation/evidence. It is **not** a central Platform Monitoring Service and it does not give a failing component authority to certify itself.

Rule:

> Components report facts about themselves; independent Evaluation attributes and judges those facts.

## 7. Repair-vs-replace principle extracted from this case

Catalyst should preserve this engineering rule:

> Repair is not the default. Replacement is a first-class evolution path.

When a failure is observed, evaluate at least:

```text
PATCH
REBUILD COMPONENT
ADAPT EXTERNAL MECHANISM
REPLACE SUBSYSTEM
```

Selection should prefer the option that:

```text
preserves the stable responsibility / evidence contract
+
introduces the least hidden coupling
+
keeps rollback cheap
+
keeps the implementation understandable
+
has the lowest long-term maintenance burden
```

Do not preserve code merely because Catalyst originally wrote it.

## 8. External Harness replacement gate

A future external Harness/tool-loop mechanism should be considered a valid replacement candidate only if a thin adapter can demonstrate, with the same benchmark/evidence:

```text
provider/model identity preserved
multi-tool call ids preserved
Capability/tool responsibility preserved
Policy boundary preserved
per-execution identity preserved
execution uncertainty not collapsed into ordinary failure
durable recovery requirement preserved where material
raw evidence available to Evaluation
failure owner remains attributable
Domain / Enterprise / Platform semantics do not leak into the external runtime
```

If an external mechanism satisfies this contract with materially less code/complexity than the internal mechanism, Catalyst should prefer replacement over maintaining an inferior internal clone.

## 9. Minimum implementation acceptance tests

Before native-tools v2 can replace v1 for the V0.2 live path, require at least:

```text
1. zero tool calls → final model answer
2. one tool call → behavior parity with accepted single-call lifecycle
3. two tool calls in one model turn → both correlated and executed
4. second call denied by Policy → evidence remains coherent
5. malformed arguments in one call → fail closed with correct owner
6. Capability known Failure → correct tool result / attribution
7. Capability exception / execution uncertainty → no false known-failure claim
8. crash/recovery between calls → no silent replay / loss of remaining calls
9. all tool results returned to model with original tool_call_id
10. V0.1 deterministic regression remains green
11. real DeepSeek local preflight reaches the actual external GitHub REST tool
12. frozen 5-case campaign can establish a Formal Baseline
```

## 10. Review verdict

```text
OBSERVED PROBLEM OWNER
Harness native tool interaction protocol

PATCH EXISTING v1
REJECT

REBUILD A CLEAN v2 COMPONENT
ACCEPT / PRIMARY PATH

ADOPT EXTERNAL TOOL LOOP NOW
WATCH / CONDITIONAL

REPLACE WHOLE HARNESS NOW
REJECT

PLATFORM CORE EXPANSION
NOT AUTHORIZED

PARALLEL EXECUTION ENGINE
NOT AUTHORIZED

FAILURE ATTRIBUTION HARDENING
REQUIRED AS HARNESS-SIDE EVIDENCE IMPROVEMENT
```

## 11. Next deliverable

The next deliverable is a **small implementation Stage Spec / Codex instruction for native-tools v2**, derived from this review.

That Stage Spec should authorize only the minimum v2 component and its tests. It must explicitly protect:

- v1 rollback/reference path;
- existing Runtime execution-certainty semantics;
- no external-framework dependency unless a thin-adapter spike first proves it is simpler;
- no parallel engine;
- no Platform Core growth;
- local real-model preflight before the next Formal Baseline attempt.
