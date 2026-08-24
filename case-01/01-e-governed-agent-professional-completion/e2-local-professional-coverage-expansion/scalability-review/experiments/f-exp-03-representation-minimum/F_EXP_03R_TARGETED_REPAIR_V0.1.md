# F-EXP-03R — TARGETED FAIRNESS REPAIR V0.1

> Parent experiment: F-EXP-03 Representation Minimum Experiment  
> Baseline experiment commit: `00ae01df7cdc8909d0289fa7a63e65b551ef9802`  
> Scope: repair experiment fairness only  
> New BREA Candidate: NOT AUTHORIZED  
> F-EXP-01 / E2-C: NOT AUTHORIZED

## Single purpose

Re-run the existing F-EXP-03 comparison after removing four experiment-design contaminations found by external review.

Do not add new regulation forms, new architecture questions, new retrieval mechanisms, or new long-lived artifacts.

## R-01 — Give A' a real generic semantic-derivation path

Current A' passes only G-BASE and leaves professional semantic fields empty. The shared validator then requires typed scope/conditions and therefore makes A' lose by construction.

Repair A' so that it may derive a temporary semantic view from `raw_evidence` / `unit_type` through a generic, non-source-specific and non-family-specific mechanism.

Forbidden:

```text
source ID branches
locator branches
regulation-family branches
hardcoded tested conclusions / numeric values
one parser per tested clause/family
```

The derived semantic view is ephemeral experiment output, not persisted typed B-MIN data.

## R-02 — Compare one shared semantic interface

The shared validator must evaluate the same semantic interface for both tracks:

```text
A'     raw/light evidence -> generic derivation -> semantic view
B-MIN  stored typed data -----------------------> semantic view
                                            ↓
                                  same validator / PC-01..07
```

The validator must not require a field merely because B-MIN stores it. It may require the professional meaning represented by that field.

## R-03 — Remove project-specific Gold from B-MIN knowledge

For RF-05, B-MIN may store only source-derived normative data such as:

```text
operand reference
operator
modifier 0.02
advisory cap 20
```

Do not store the project-specific derived result `12` in the regulation representation.

The experiment mechanism must calculate the result from project facts and normative data, then compare it with the independent expected Gold.

## R-04 — Actually validate table numeric values

RF-03 must validate the source-backed table values, including `0.8` and `1.1`, not only an outcome label such as `commercial_large_rates`.

The shared result contract must make these values auditable.

## Test-oracle repair

Tests must not assert in advance that:

```text
A' FAILS
B-MIN PASSES
```

Tests may assert only experiment invariants, contract integrity, protected boundaries, and that the reported decision candidate follows observed results.

## Fixed test surface

Keep exactly the existing:

```text
5 representative forms
2 negative controls
1 same-structure extension
PC-01..PC-07
```

No new case family is authorized.

## Artifact minimum

Reuse the existing F-EXP-03 artifact surface. Do not create new result/report families.

Update only what the repair requires inside:

```text
01_EXPERIMENT_DESIGN.md
lab/**
02_RESULTS.json
03_EXPERIMENT_REVIEW.md
```

The original experiment commit remains historical evidence.

## Valid re-run outcomes

```text
A_PRIME_SUFFICIENT
B_MIN_EVIDENCED
BOTH_INSUFFICIENT
INCONCLUSIVE
EXPERIMENT_INVALID
```

If repaired A' still fails a mandatory contract for a representation reason while repaired B-MIN passes with no hidden knowledge and all retained field groups remain justified, `B_MIN_EVIDENCED` may be returned again as a decision candidate.

## Publication boundary

After explicit authorization:

```text
ONE targeted repair implementation+evidence commit
ONE push to case-01
STOP
```

No BREA Candidate, F-EXP-01, E2-C Benchmark, Platform, Runtime, Enterprise or main mutation is authorized.
