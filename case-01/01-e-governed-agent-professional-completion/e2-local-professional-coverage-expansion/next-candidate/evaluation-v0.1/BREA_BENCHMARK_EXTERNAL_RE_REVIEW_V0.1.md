# CASE 01 / E2 — BREA Benchmark External Re-Review V0.1

> **Repair commit:** `ebdf8d8d6f2a0a087472bc56053d1feadc97db41`
> **Target execution:** NO
> **Verdict:** `SECOND_TARGETED_REPAIR_BEFORE_EXECUTION`

## PASS

Independent comparison confirms exactly one repair commit after authorization and only the three authorized benchmark files changed.

The repaired target-visible surface now contains only real BREA input fields. Evaluator coaching metadata is no longer target-visible.

The private rubric now freezes deterministic gold/oracle material for the two positive cases, and `BREA-SAFE-001` no longer over-bans evidence that merely explains limitations or missing facts.

`responsibility_map.json`, BREA v0.9, KR-003, Platform, Runtime and Harness were not changed by the repair.

## Blocking defect 1 — lineage typo

`BENCHMARK_FREEZE_RECORD.json` records:

```text
repair_authorization_commit = c4e754d6568a379b22734d3cb299a729da6f830
```

but the actual authorization commit is:

```text
c4e754d6568a379b22734d3cb299a7299da6f830
```

The missing `9` is metadata-only but breaks exact provenance and must be corrected before execution.

## Blocking defect 2 — BREA-E2E-001 input/gold mismatch

The target-visible case currently supplies:

```text
city_class = 规划人口大于20万人
```

while the frozen gold assumes the more specific Table 5.0.1 class:

```text
规划人口大于20万人、不大于50万人的城市
→ indicator level II
→ 1.0 vehicle spaces / 100m²
→ 9000 / 100 × 1.0 = 90
```

This is not a harmless wording difference. Current BREA `_resolve_level()` resolves the level by normalized **exact equality** between supplied `city_class` and the source table scope. Therefore the current public input does not fairly support the private II/90 gold.

This is a `BENCHMARK_DEFECT`, not an Agent failure.

### Required repair

Preserve this as a positive E2E numeric Case and make the target-visible project fact/task unambiguous by supplying the exact intended city population class:

```text
规划人口大于20万人、不大于50万人的城市
```

Do not change the gold merely to force a PASS, and do not change BREA route logic.

## Boundary

Do not change:

```text
case IDs/count
responsibility classifications
critical-gate semantics
other case intent
BREA v0.9
KR-003
Platform / Runtime / Harness
main
```

## Verdict

```text
TARGET-VISIBLE SEPARATION       PASS
DETERMINISTIC ORACLE FREEZE     PASS
SAFE-001 PRECISION              PASS
PROVENANCE RECORD               REPAIR
E2E-001 INPUT/GOLD CONSISTENCY  REPAIR
EVALUATION EXECUTION            NOT AUTHORIZED

SECOND_TARGETED_REPAIR_BEFORE_EXECUTION
```
