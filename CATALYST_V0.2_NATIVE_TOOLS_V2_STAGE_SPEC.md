# CATALYST V0.2 — NATIVE TOOLS V2 STAGE SPEC

> Status: IMPLEMENTATION AUTHORIZED — BOUNDED COMPONENT REBUILD
> Parent review: `CATALYST_V0.2_MULTI_TOOL_REPAIR_REPLACE_DESIGN_REVIEW.md`
> Target branch: `stage/catalyst-minimum-usable-v0.2`
> Purpose: replace the V0.2 live native-tool interaction mechanism without repairing native-tools v0.1 in place.

## 1. Authorization

This Stage Spec authorizes one bounded candidate:

> Build a clean, replaceable **native-tools v2** interaction path that accepts one model turn containing `0..N` provider-neutral tool calls and executes those calls safely through Catalyst execution semantics.

This Stage Spec does **not** authorize:

- mutation of native-tools v0.1 into a new protocol;
- Platform Standard or Platform Core expansion;
- a Workflow Engine;
- a parallel execution engine;
- Registry / Evaluation Service / Optimizer Service / monitoring platform;
- Domain or Enterprise semantics in Runtime;
- benchmark/rubric weakening;
- provider-specific DeepSeek branches in AgentCore;
- replacement of the entire Harness;
- introduction of LangGraph / OpenAI Agents SDK / Pydantic AI as a production dependency without a separate thin-adapter proof.

## 2. Stable behavior to preserve

The implementation must preserve the existing accepted single-execution lifecycle:

```text
Action
→ Policy
→ durable execution intent / PendingExecution before real execution
→ unique execution_id
→ Capability execution
→ Observation or explicit execution uncertainty
→ durable settlement
→ recovery / reconciliation semantics
```

The new component may refactor existing internal code to share this lifecycle, but only if the refactor is behavior-preserving and all V0.1 regression evidence remains green.

Do not duplicate the lifecycle into a second inconsistent implementation merely to make multi-tool work.

## 3. Obsolete assumption to remove from the v2 path

The v2 path must not assume:

```text
one model turn == one tool call == one Act
```

The correct v2 interaction primitive is:

```text
one model turn
→ 0..N tool-call intents
```

Each real tool execution remains independently identifiable and auditable.

## 4. V1 preservation rule

Native-tools v0.1 remains a frozen compatibility/reference path.

Required:

- its existing behavior stays deterministic;
- its existing tests remain green;
- no semantic broadening is hidden behind the old v0.1 name;
- v2 is selectable explicitly by the V0.2 live runner.

V1 may later be deprecated only after v2 evidence exists. Do not delete it in this stage.

## 5. Provider-neutral model-turn handling

Reuse the existing provider-neutral facts where valid:

```text
Message
ModelToolCall
ModelResponse
ModelCallRecord
```

Provider adapters already map vendor responses into these values. Do not move multi-tool orchestration into DeepSeek/OpenAI provider adapters.

The v2 path must preserve the complete assistant model turn, including:

```text
assistant message
all tool_call ids
all tool names
all raw arguments
finish_reason
usage when returned
```

## 6. Multi-call execution semantics

Initial V0.2 behavior is **sequential**.

For a turn containing calls A, B, C:

```text
A → policy → prepare → execute → settle
B → policy → prepare → execute → settle
C → policy → prepare → execute → settle
```

Do not infer that provider parallel-tool capability authorizes concurrent side effects.

Each call must preserve its own:

```text
tool_call_id
Action / capability_id / arguments
Policy verdict
execution_id when execution is prepared
Observation when known
execution uncertainty when outcome is not authoritative
```

## 7. Durable model-turn progress

A pure in-memory loop over `response.tool_calls` is insufficient.

The v2 implementation must preserve enough durable progress that, after process interruption, it can distinguish:

```text
calls not yet started
call currently unresolved / pending
calls already settled
model turn fully executed and ready to return tool results
```

Required recovery property:

> If Call A settled and the process stops before Call B starts, recovery must not replay A silently and must not forget B/C.

The exact internal representation is implementation-level and may be new v2-specific data or a minimal backward-compatible extension, but it must be explicit, snapshot-safe, and testable. Do not hide the queue in ephemeral process memory or an undocumented generic state key.

## 8. Tool-result reconstruction

After all executable calls for a model turn are resolved, the next model request must contain:

```text
original assistant message containing the full tool-call set
+
one tool-result message per original call
```

Every tool-result message must use the matching original `tool_call_id`.

Do not duplicate the assistant batch once per tool call and do not attach one call's Observation to sibling call ids.

## 9. Policy and failure behavior

Policy remains per concrete Action.

If one call is denied, fails, or becomes execution-uncertain:

- preserve the call-level fact;
- do not silently execute or retry it;
- do not erase already settled sibling calls;
- do not claim the whole model turn was a known ordinary capability failure when an execution outcome is uncertain;
- expose enough evidence for Evaluation to identify the owner and downstream boundary.

The implementation must define deterministic behavior for whether later sibling calls continue after a denied / known-failure call. Prefer the smallest fail-closed rule; document and test it. Do not let model prompt wording implicitly decide execution safety semantics.

## 10. Harness self-observability hardening

Extend the live evaluation evidence path so infrastructure/protocol failures can report a bounded structured attribution record with at least:

```text
stage
owner
failure_type
observed_fact
provider/model call completed? yes/no
downstream tool execution started? yes/no
side-effect certainty
unproven downstream boundary
```

This is Harness-side evidence, not Platform monitoring authority.

A component reports facts; independent Evaluation decides attribution/verdict.

## 11. Required deterministic tests

Add focused v2 tests for at least:

### V2-001 — zero tool calls
Model returns a normal final answer. No Capability executes.

### V2-002 — one tool call
Behavior/evidence remains compatible with the accepted single-execution lifecycle.

### V2-003 — two tool calls, same turn
Both calls execute in deterministic order and each result is returned with the correct `tool_call_id`.

### V2-004 — two different tools
Different Capability ids and argument schemas remain correctly correlated.

### V2-005 — malformed arguments
The malformed call fails closed before unintended Capability execution and the owner is attributable.

### V2-006 — Policy deny in batch
Denied call does not execute. Sibling/batch behavior follows the documented fail-closed rule.

### V2-007 — known Capability Failure
Known `Observation.Failure` remains distinct from infrastructure uncertainty.

### V2-008 — Capability exception / uncertain execution
Pending/reconciliation semantics are not collapsed into an ordinary failure.

### V2-009 — interruption between sibling calls
After A settles and before B begins, durable recovery does not replay A and does not lose B.

### V2-010 — history reconstruction
One assistant message with N calls is reconstructed once, followed by N correctly correlated tool results.

### V2-011 — V1 regression
All existing deterministic regression remains green.

## 12. Live preflight acceptance

After deterministic tests pass, run the same local real-model preflight with the already selected live provider/model configuration.

Do not change benchmark/rubric to obtain green.

Required preflight evidence:

```text
real model API probe PASS
provider/model identity
model may emit multiple tool calls
v2 accepts the turn
at least one real GitHub REST capability invocation occurs when required
per-call tool_call_id + execution evidence retained
5 case outcomes recorded
failure owners preserved
```

A poor capability score is acceptable preflight evidence. Infrastructure/protocol inability to execute the intended benchmark is not.

## 13. Formal Baseline rule

Do **not** optimize answer quality before preserving the first valid frozen Formal Baseline.

Once the v2 live path can execute the frozen 5-case campaign end-to-end:

```text
freeze candidate SHA
freeze benchmark / rubric revision
freeze provider / model / mode
freeze external tool/source identity
run campaign
preserve evidence
```

That campaign becomes the Reference even if some capability cases FAIL.

Only then may `capability-optimization` form the first bounded product/capability Candidate.

## 14. External-adoption checkpoint

While implementing v2, do not independently recreate broad framework features such as:

```text
general graph orchestration
parallel scheduler
human approval framework
universal retry middleware
tracing backend
memory subsystem
multi-agent runtime
```

If implementing the minimum v2 unexpectedly requires several of those responsibilities, STOP and reopen the parent Repair/Replace review. At that point, a mature external Harness adapter may be cheaper than continuing internal construction.

## 15. Acceptance verdict required from implementer

Return a concise implementation report containing:

```text
changed files
new v2 boundary
what v1 code was left untouched
whether execution lifecycle was refactored/shared
new durable model-turn representation
batch fail-closed rule
new tests and results
full deterministic regression result
local live preflight result
evidence paths
known remaining gaps
whether an external Harness now appears materially cheaper
```

Do not merge PR #13 and do not claim V0.2 MINIMUM USABLE merely because native-tools v2 tests pass.
