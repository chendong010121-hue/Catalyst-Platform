# CASE 01-D / D2 — EVIDENCE INDEX — V0.1

> Governed evidence index for the D2 Local Admission & Binding stage.
> All paths relative to `case-01/01-d-governed-agent-admission-binding/d2-local-admission-binding/`.

## Authorization

| Item | Value |
|---|---|
| D2 authorization record | `D2_AUTHORIZATION_RECORD_V0.1.yaml` — **granted** |
| Authorization model | `D2_AUTHORIZATION_MODEL_V0.2.md` |
| Stage spec | `CASE_01_D_D2_LOCAL_ADMISSION_AND_BINDING_V0.1_STAGE_SPEC.md` (accepted) |

## Implementation (case-local only)

| File | Role |
|---|---|
| `implementation/brea_execution_capability.py` | BREA runner → Runtime Capability protocol adapter; Platform execution-routing descriptor (`case-01.brea.execute @ 0.1`); case-local artifact mapper |
| `implementation/governance_agent.py` | `governance.agent` parser (canonical source = `Invocation.extensions` only), record validation, trace attribution (conflict → fail closed) |
| `implementation/d2_pipeline.py` | Admission gates G-A01..G-A07; Admission Record; Binding Record + validation; stack composition (existing Platform pieces unchanged); governed execution; provenance verification |

## Scripts

| File | Role |
|---|---|
| `scripts/compute_fingerprint.py` | Deterministic implementation fingerprint (source tree SHA + manifest SHA) |
| `scripts/implementation_fingerprint.json` | Fingerprint values consumed by Admission/Binding records |
| `scripts/run_d2.py` | Full D2 orchestrator (regression → gates → records → tests → platform-bound cases → provenance chain) |

## Tests

| File | Role |
|---|---|
| `tests/run_d2_tests.py` | D2-T01..T16 (stdlib only) |

## Admission & Binding Records

| File | Status |
|---|---|
| `admission/BREA_V0_1_ADMISSION_RECORD.json` | **ADMITTED** (admission_ref=`admission-case-01-brea-v0.1-001`) |
| `binding/BREA_V0_1_EXECUTION_BINDING.json` | **BOUND** (binding_id=`binding-case-01-brea-v0.1-001`) |

## Evidence Logs

| File | Result |
|---|---|
| `evidence/D2_CANDIDATE_REGRESSION_RESULTS.log` (+ `.log.txt` twin) | **PASS** — 15/15 self-check + T-C01/02/03 |
| `evidence/D2_TEST_RESULTS.log` (+ `.log.txt` twin) | **PASS** — D2-T01..T16: **16/16** |
| `evidence/D2_PLATFORM_BOUND_CASE_RESULTS.log` (+ `.log.txt` twin) | **PASS** — T-C01/02/03 whole-Agent through D2 binding path |

> Note: root `.gitignore` excludes `*.log`; D2 commits the `.log.txt` twins while keeping the `.log` locally (01-C precedent).

## Provenance

| File | Result |
|---|---|
| `evidence/D2_PROVENANCE_CHAIN_V0.1.json` | **PASS** — all verification checks true |
| `evidence/D2_PROVENANCE_CHAIN_V0.1.md` | Human-readable chain |

## Governance / Integrity

| File | Role |
|---|---|
| `evidence/D2_REPOSITORY_INTEGRITY_V0.1.md` | Contamination / main integrity evidence |
| `evidence/PLATFORM_GAP_UPDATE_D2_V0.1.md` | D1 gap dispositions after D2 |
| `review/CASE_01_D_D2_EXECUTION_REPORT_V0.1.md` | Final D2 execution report |
| `review/CASE_01_E_ENTRY_BOUNDARY_V0.1.md` | CASE 01-E entry boundary (authorization = NO) |

## Identity / Fingerprint Facts

| Item | Value |
|---|---|
| Agent | `case-01.brea @ 0.1-candidate` |
| Execution capability | `case-01.brea.execute @ 0.1` |
| Governed definition SHA | `6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4` |
| candidate_tree_sha256 | `cbdd6b4d13df0f2b4408ab6a50a9b882fd4aa35cb2ddeeb668e98d6634599193` |
| builder_output_manifest_sha256 | `394ef4da3658776b34a4ad2c2d3fbd803b3ff332f7b7f6669c82a5917f00e3de` |

## Protected Boundaries (verified unchanged)

`platform_standard/**` · `agent_runtime/**` · `enterprise_extensions/**` · `examples/**` · root tests · CI · CASE 01-B · CASE 01-C Candidate · raw corpus (never committed) · main (`5874be11…`)
