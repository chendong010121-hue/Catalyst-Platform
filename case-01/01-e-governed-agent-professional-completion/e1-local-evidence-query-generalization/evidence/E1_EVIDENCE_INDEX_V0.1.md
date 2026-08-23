# CASE 01-E / E1 — EVIDENCE INDEX — V0.1

> Governed evidence index for the E1 Local Evidence Query Generalization stage.
> All paths relative to `case-01/01-e-governed-agent-professional-completion/e1-local-evidence-query-generalization/`.

## Authorization & Contract

| Item | Value |
|---|---|
| E1 authorization record | `E1_AUTHORIZATION_RECORD_V0.1.yaml` — **granted** |
| Stage spec | `CASE_01_E_E1_LOCAL_EVIDENCE_QUERY_GENERALIZATION_V0.1_STAGE_SPEC.md` (accepted) |
| Professional change request | `E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md` (commit `9ca6bbd`) |

## Change Governance

| File | Role |
|---|---|
| `change/E1_CHANGE_IMPACT_REVIEW_V0.1.md` | responsibility classification (FN/SEAM/OBL) before implementation |
| `change/E1_AGENT_DEVELOPMENT_TRACE_V0.1.md` | full change chain + per-module rationale |

## Builder / Development Mechanism

| File | Role |
|---|---|
| `builder/run_e1_builder.py` | Case-local Builder change mechanism (baseline copy + authorized overlay) |
| `builder/change_source/**` | authorized changed modules (brea/*.py + README) |
| `builder/E1_CANDIDATE_CHANGE_MANIFEST_V0.1.json` | file-level change provenance |
| `builder/E1_BUILDER_RUN_REPORT_V0.1.md` | builder run report (8 changed / 13 unchanged byte-identical, import probe PASS) |

## Candidate

| Item | Value |
|---|---|
| `candidate/brea-v0.2/**` | v0.2 Candidate workspace (separate; v0.1 untouched) |
| agent lineage / version | `case-01.brea` @ `v0.2-candidate` (NOT admitted, NOT bound) |
| Candidate self-check | **15/15 PASS** (copied v0.1 tests: T-C01/02/03 + seams + structural) |

## Tests & Benchmark

| File | Role |
|---|---|
| `tests/run_e1_tests.py` | E1 test runner (structural + anti-hardcode + benchmark + regression) |
| `tests/benchmark/E1_BENCHMARK_V0.1.json` | B-E1-01..13 benchmark data (not code) |
| `tests/e1_platform_check.py` | Platform compatibility check through unchanged D2-shape adapter |
| `tests/e1_integrity_checks.py` | v0.1 baseline / v0.2 conformance / repository integrity |

## Evidence

| File | Result |
|---|---|
| `evidence/E1_TEST_RESULTS.log.txt` | **23/23 PASS** |
| `evidence/E1_BENCHMARK_RESULTS_V0.1.json` | B-E1-01..13 all PASS |
| `evidence/E1_ANTI_HARDCODE_REVIEW_V0.1.md` | **PASS** (7 unencoded queries succeed; ≥3 required) |
| `evidence/E1_V01_BASELINE_INTEGRITY_V0.1.md` | **PASS** (v0.1 byte-unchanged; D2 fingerprint valid) |
| `evidence/E1_V02_FUNCTION_SEAM_OBLIGATION_CONFORMANCE_V0.1.md` | **PASS** (FN/SEAM/OBL mapping valid) |
| `evidence/E1_PLATFORM_COMPATIBILITY_CHECK_V0.1.md` | **PASS** (Platform/Runtime unchanged; D2 shape reusable) |
| `evidence/E1_REPOSITORY_INTEGRITY_V0.1.md` | **PASS** (no contamination; main unchanged) |
| `evidence/PLATFORM_GAP_UPDATE_E1_V0.1.md` | gap dispositions after E1 |

## Review

| File | Role |
|---|---|
| `review/CASE_01_E_E1_EXECUTION_REPORT_V0.1.md` | final E1 execution report |
| `review/CASE_01_E_E2_ENTRY_BOUNDARY_V0.1.md` | E2 entry boundary (authorization = NO) |

## Protected Boundaries (verified unchanged)

`platform_standard/**` · `agent_runtime/**` · `enterprise_extensions/**` · `examples/**` ·
root tests · CI · admitted `brea-v0.1` (fingerprint re-verified) · D2 accepted evidence ·
raw corpus (never committed) · main (`5874be11…`)
