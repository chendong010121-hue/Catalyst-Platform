# CASE 01 / E2 — BREA Benchmark External Review V0.1

> **Review status:** COMPLETE
> **Benchmark formation commit:** `112251a14ffb1698211d89317406ea00fe788ee9`
> **Authorization parent:** `e2701a3fdaad22c6beca8585e76d7bd341dea8fa`
> **Target:** `case-01.brea@0.9-candidate`
> **Target execution during formation:** NO
> **Evaluation execution authorization:** NO
> **Verdict:** `TARGETED_REPAIR_BEFORE_EXECUTION`

---

# 1. Formation chronology

Independent repository comparison confirms:

```text
e2701a3fdaad22c6beca8585e76d7bd341dea8fa
    ↓ exactly one benchmark-formation commit
112251a14ffb1698211d89317406ea00fe788ee9
```

Exactly four files were added:

```text
evaluation-v0.1/responsibility_map.json
evaluation-v0.1/benchmark/public/benchmark_cases.json
evaluation-v0.1/benchmark/private/rubric.json
evaluation-v0.1/BENCHMARK_FREEZE_RECORD.json
```

No pre-existing Candidate / Knowledge / Platform / Runtime / Harness file was modified by the benchmark-formation commit.

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

The map correctly reuses PR-01..PR-18 rather than inventing a second evaluation ontology.

The current classifications are broadly coherent with the frozen declared product envelope.

Particularly important:

```text
PR-05 full jurisdiction hierarchy
PR-06 competing edition/effective-status selection
PR-11 cross-source/cross-rule composition
PR-13 multi-turn clarification UI
PR-18 web/external supplementation
```

are not automatically promoted into current product obligations.

This is consistent with the bounded KR-003 / local authoritative-source product promise.

`PR-04` still retains the narrower current responsibility to reject clearly inapplicable jurisdiction-specific evidence, which is correctly distinguished from full PR-05 jurisdiction-hierarchy resolution.

Therefore:

```text
RESPONSIBILITY-FIRST DESIGN
PASS

IDEAL-AGENT FEATURE WISHLIST CONTROL
PASS
```

No responsibility classification needs to be changed merely to proceed with benchmark repair.

---

# 3. Case selection review

Five new Cases is a reasonable V0.1 surface.

The Cases cover:

```text
positive evidence-backed clause behavior
positive end-to-end table/numeric behavior
missing-fact fail-closed behavior
obvious jurisdiction mismatch fail-closed behavior
out-of-KR source-boundary honesty
```

The Cases trace to REQUIRED responsibilities and avoid forcing PR-05 / PR-06 / PR-11 / PR-13 / PR-18 into the current product boundary.

Critical Gates GATE-01..GATE-06 are represented across the set.

Therefore:

```text
CASE COUNT / SCOPE
PASS

RESPONSIBILITY TRACEABILITY
PASS

CRITICAL-GATE COVERAGE
PASS
```

---

# 4. Blocking issue A — target-visible benchmark surface is too broad

The benchmark has public/private directories, but the current public file is marked:

```text
visibility = TARGET_VISIBLE_LATER
```

and contains more than normal task input.

Besides the user task and supplied context, it exposes evaluator-oriented fields such as:

```text
expected_observable_outcome
hidden rubric reference
critical_gate_conditions
acceptable_partial_credit_if_any
forbidden_shortcuts
required_evidence_properties
trajectory_constraints_if_any
failure_attribution_hints
```

This is not equivalent to a clean hidden-rubric boundary.

Even if a future runner intends to pass only selected fields, that target-input contract is not currently frozen.

A credible evaluation must not depend on an unstated assumption that the target will ignore or never receive evaluator metadata.

## Required repair

Freeze an explicit target-visible input projection.

For BREA, target-visible material should normally be limited to the actual task inputs needed by the product interface, e.g.:

```text
case_id if operationally needed
public_task_statement
provided_project_context
provided_regulation_context
available_source_scope when this is genuinely supplied to the product
```

Evaluator-only material must move to the private surface or be explicitly marked `EVALUATOR_ONLY` and never supplied to BREA.

The benchmark freeze record must hash the exact target-visible projection separately from the private evaluation contract.

This repair changes benchmark packaging / visibility only, not product scope or Agent behavior.

---

# 5. Blocking issue B — deterministic gold/oracle is not fully frozen

BREA is currently deterministic and several Cases test deterministic professional facts.

The private rubric contains useful constraints such as:

```text
required_route
required_locator
selected row must match context
numeric conclusion must be supported
```

but for positive deterministic Cases it does not yet freeze enough exact gold/oracle information to make grading independently reproducible before target execution.

Examples:

```text
BREA-CAP-001
→ required route + locator are frozen
→ exact accepted professional result / independent derivation oracle is not fully specified

BREA-E2E-001
→ correct table/row behavior is required
→ exact expected selected row / normative operands / deterministic result oracle is not frozen in the private rubric
```

A later evaluator could derive these from the fixed KR-003 source, but the derivation method itself is currently not frozen.

That leaves unnecessary grader discretion after target output exists.

## Required repair

Before execution, freeze one of the following per deterministic positive Case:

```text
A. exact source-backed expected value / selected row / derivation operands
```

or

```text
B. a deterministic independent oracle specification that derives the gold from the frozen source without using BREA output
```

The oracle must be frozen before BREA sees the benchmark.

Do not create unsupported gold values; derive only from KR-003 / frozen authoritative source evidence.

---

# 6. Non-blocking rubric observation

`BREA-SAFE-001` currently requires:

```text
no evidence items claimed as supporting a result
```

The safety intent is correct: no evidence item may be used to support a normative numeric conclusion when required facts are missing.

However, an `insufficient_context` result could legitimately cite source evidence to explain why those facts are required, depending on the actual result schema.

During targeted repair, phrase the rule narrowly enough to forbid:

```text
evidence presented as support for an accepted normative value
```

without accidentally forbidding useful evidence that supports the limitation / missing-fact explanation.

This is a rubric precision repair, not a product behavior change.

---

# 7. What must NOT change

The targeted repair does NOT justify changing:

```text
PR-01..PR-18 identity
current REQUIRED / NOT_REQUIRED_NOW classification merely for benchmark convenience
BREA v0.9
KR-001 / KR-002 / KR-003
professional routes / facts / sources
critical-gate meaning
Evaluation Stage / Evaluation Contract
Platform / Runtime / Harness
main
```

Do not add more Cases merely because a repair commit is being made.

Five Cases remain sufficient unless the repair itself proves one is invalid.

---

# 8. Review verdict

```text
BENCHMARK FORMATION GOVERNANCE
PASS

RESPONSIBILITY MAP
PASS

CASE SELECTION
PASS

PRODUCT-SCOPE DISCIPLINE
PASS

CRITICAL-GATE COVERAGE
PASS

TARGET-VISIBLE / PRIVATE SEPARATION
TARGETED REPAIR REQUIRED

DETERMINISTIC GOLD / ORACLE FREEZE
TARGETED REPAIR REQUIRED

BREA TARGET EXECUTION
NOT AUTHORIZED

E2-C
NOT AUTHORIZED
```

# FINAL VERDICT

```text
BREA BENCHMARK V0.1
FORMATION EVIDENCE-BACKED
BUT NOT YET EXECUTION-READY

TARGETED_REPAIR_BEFORE_EXECUTION
```

After a separately authorized benchmark-only repair, perform one short External Benchmark Re-Review before Evaluation Execution authorization.
