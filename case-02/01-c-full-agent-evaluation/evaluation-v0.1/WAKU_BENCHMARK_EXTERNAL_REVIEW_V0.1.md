# CASE 02-C — Waku Benchmark External Review V0.1

> **Review status:** COMPLETE
> **Benchmark formation commit:** `12acca7ee0b29971d8b1dbed659285bf6986587f`
> **Authorization parent:** `6023f2dd1a0d46440867e68ed3a23e2d3cd80be2`
> **Pinned target:** `ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad`
> **Target execution during formation:** NO
> **Evaluation execution authorization:** NO
> **Verdict:** `TARGETED_REPAIR_BEFORE_EXECUTION`

---

# 1. Formation chronology

Independent comparison confirms exactly one benchmark-formation commit after authorization and exactly four added evaluation files:

```text
responsibility_map.json
benchmark/public/benchmark_cases.json
benchmark/private/rubric.json
BENCHMARK_FREEZE_RECORD.json
```

No frozen Case02-A / Case02-B evidence or Catalyst Platform / Runtime / Harness file was modified by the benchmark formation commit.

`main` remains `5874be1130e8867082880fcd63f659fc909d9efd`.

Therefore:

```text
FORMATION CHRONOLOGY
PASS

PROTECTED BOUNDARY
PASS
```

---

# 2. Responsibility-map review

The map reuses WR-01..WR-22 and WAKU-A01..WAKU-A06 rather than building a second analysis/evaluation ontology.

The classification is intentionally core-product focused and keeps optional integrations outside the first complete-product requirement surface.

The strong distinction between structural/offline evidence and missing live provider-backed evidence is useful and consistent with Case02-A's `NOT LIVE-VERIFIED` boundary.

Therefore:

```text
RESPONSIBILITY-FIRST DESIGN
PASS

NATIVE-EVIDENCE REUSE
PASS

OPTIONAL-INTEGRATION CONTROL
PASS
```

No broad Waku re-analysis is required before benchmark repair.

---

# 3. Case selection review

Seven Catalyst-added Cases provide a credible first live surface around:

```text
local calendar side effects
semantic memory + restart
stale-memory correction
session/reload continuity
progressive skill loading
tool-failure honesty
trace / provider / eval / release semantics
```

This complements rather than mechanically duplicates Waku's native deterministic/judge assets.

The six critical gates CG-01..CG-06 are represented.

Therefore:

```text
CASE COUNT / SCOPE
PASS

REAL USER LOOP INTENT
PASS

CRITICAL-GATE COVERAGE
PASS
```

---

# 4. Blocking issue A — target-visible surface exposes evaluator metadata

The public file is marked target-visible but includes evaluator-oriented fields beyond normal user task input, including:

```text
setup_state
isolated_world_requirements
expected_observable_outcome
hidden rubric reference
critical_gate_conditions
acceptable_partial_credit_if_any
forbidden_shortcuts
required_trace_or_state_evidence
trajectory_constraints_if_any
failure_attribution_hints
```

Some setup facts may need to be created by the evaluator, but they do not need to be shown to Waku as prompt-visible material.

Likewise, expected outcomes, forbidden shortcuts and failure attribution are evaluation metadata and may coach the Agent.

## Required repair

Freeze two distinct surfaces:

```text
TARGET INPUT
→ only the user-facing turn(s) and any product-visible context that a real gateway would provide

EVALUATOR SETUP / PRIVATE CONTRACT
→ fixture construction, isolated-state requirements, expected outcome, gates, state checks, failure attribution
```

The benchmark freeze record must separately hash the exact target-visible prompt/turn sequence and evaluator-private setup/rubric.

---

# 5. Blocking issue B — executable fixtures / world-state are not frozen

Several Cases depend on deterministic initial world state:

```text
calendar overlap
empty/new personal preference
stale preference
session identifiers / chat history
matching + unrelated SKILL.md files
controlled note-tool failure
```

The current benchmark freezes these only as prose descriptions.

That leaves too much execution-time freedom to change the initial world after seeing target behavior.

## Required repair

Freeze concrete evaluator-owned fixtures before Waku execution.

Examples may include compact JSON/SQL/text fixture files under the private benchmark area representing:

```text
initial calendar events
initial memory/fact state
session IDs/history setup
local SKILL.md fixture content
controlled failure-injection contract
expected before/after state checks
```

Do not use the user's real `.waku` state.

The exact fixture bytes/hash must be recorded in the freeze record.

The evaluator may materialize these fixtures into a fresh temporary `WAKU_HOME` later, but may not improvise them after execution starts.

---

# 6. Blocking issue C — WAKU-CAP-002 mixes product turn with evaluator/ops duties

Current public task asks Waku to:

> complete a bounded local knowledge turn, **and produce an inspectable trace and evaluation result**, with later evaluation recording provider/model identity and distinguishing deterministic completion from judge quality.

This crosses responsibility boundaries.

Waku's product turn produces the Agent interaction/trace. Native eval/release-gate operations are separate LLM-Ops responsibilities that occur around/after the turn.

A normal user should not need to ask the Agent to “produce an evaluation result” in the same prompt to prove WR-16 / WR-17.

## Required repair

Split the execution semantics inside the Case without necessarily adding another Case:

```text
TARGET STEP
→ one normal bounded no-side-effect user turn

EVALUATOR / OPS STEP
→ inspect trace
→ run or inspect native deterministic/judge/release-gate behavior under the separately authorized provider environment
→ record provider/model identity externally
```

Keep the Case ID if desired. Repair responsibility ownership rather than expanding benchmark count.

---

# 7. Important scope review — Waku core product claim

Pinned Waku README explicitly describes the core product as a local-first personal assistant with Harness, Loop, Memory and Eval/LLM-Ops, and publicly demonstrates restart memory, local calendar tool behavior, dashboard/CLI gateways and built-in evaluation/release gating.

Therefore live evaluation of these responsibilities is fair.

However the benchmark should continue to avoid requiring optional Telegram/voice/MCP/external calendar integrations for core PASS.

No scope expansion is needed.

---

# 8. Non-blocking implementation observations

During repair, confirm that each proposed trace/state check is actually observable at the pinned commit.

For example, if a desired event such as exact skill-match metadata or gateway reload event is not directly emitted in the current trace format, the rubric should use the strongest available external observable evidence rather than inventing a trace field that does not exist.

If reliable verification would require modifying Waku instrumentation, STOP and classify that as an evaluation observability limitation rather than patching Waku under benchmark repair.

---

# 9. What must NOT change

The targeted repair does NOT authorize:

```text
Waku source mutation
Waku native-test patching
Case02-A / B evidence rewrite
new WAKU asset identities for existing mechanisms
optional integration promotion
Catalyst adapter/integration
Platform / Runtime / Harness change
main mutation
live provider execution
```

Do not add cases solely because repair is occurring.

Seven Cases are sufficient unless one becomes invalid after responsibility correction.

---

# 10. Review verdict

```text
BENCHMARK FORMATION GOVERNANCE
PASS

RESPONSIBILITY MAP
PASS

NATIVE WAKU EVIDENCE REUSE
PASS

CASE SELECTION / USER-LOOP INTENT
PASS

OPTIONAL FEATURE CONTROL
PASS

TARGET-VISIBLE / PRIVATE SEPARATION
TARGETED REPAIR REQUIRED

EXECUTABLE FIXTURE FREEZE
TARGETED REPAIR REQUIRED

WAKU-CAP-002 RESPONSIBILITY SEPARATION
TARGETED REPAIR REQUIRED

WAKU LIVE EXECUTION
NOT AUTHORIZED
```

# FINAL VERDICT

```text
WAKU BENCHMARK V0.1
FORMATION EVIDENCE-BACKED
BUT NOT YET EXECUTION-READY

TARGETED_REPAIR_BEFORE_EXECUTION
```

After a separately authorized benchmark-only repair, perform one short External Benchmark Re-Review before live Evaluation Execution authorization.
