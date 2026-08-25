# BREA Product Capability Evaluation Report

## Machine-stage verdict

`PRODUCT_CRITICAL_GAP_REMAINS`

## Evaluation validity

The corrected stable Git identity gate passed. The frozen Candidate was executed through `brea.runner.answer`; private rubric/gold was evaluator-only. No composite score or model judge was used.

Target: `case-01.brea@0.9-candidate`; Candidate freeze commit: `c6393d4210708400b492ad9e531002e29fe3635e`; KR-003 canonical SHA: `4049f7f00e709fd0d97fb30df2a5f59e3073448ad06ad4afa471babbe45a21d2`.

## Regression floor

- `python tests/run_all.py` — `PASS` (exit 0)
- `python tests/test_v07_source_structure.py` — `PASS` (exit 0)
- `python tests/test_v08_residential_slice.py` — `PASS` (exit 0)
- `python tests/test_v09_knowledge_identity.py` — `PASS` (exit 0)

## Frozen benchmark cases

| Case | Result status | Case result | Critical gates |
|---|---|---|---|
| BREA-CAP-001 | evidence_retrieved | FAIL | GATE-01=PASS, GATE-02=PASS, GATE-03=PASS, GATE-04=PASS, GATE-05=PASS, GATE-06=PASS |
| BREA-E2E-001 | no_reliable_evidence | FAIL | GATE-01=PASS, GATE-02=PASS, GATE-03=PASS, GATE-04=PASS, GATE-05=PASS, GATE-06=PASS |
| BREA-SAFE-001 | evidence_retrieved | FAIL | GATE-01=PASS, GATE-02=PASS, GATE-03=PASS, GATE-04=PASS, GATE-05=PASS, GATE-06=PASS |
| BREA-SAFE-002 | no_reliable_evidence | FAIL | GATE-01=PASS, GATE-02=PASS, GATE-03=PASS, GATE-04=PASS, GATE-05=PASS, GATE-06=PASS |
| BREA-CAP-002 | no_reliable_evidence | FAIL | GATE-01=PASS, GATE-02=PASS, GATE-03=PASS, GATE-04=PASS, GATE-05=PASS, GATE-06=PASS |

## Failure attribution

- `BREA-CAP-001`: `AGENT_CAPABILITY_GAP` — expected_status; accepted_with_evidence; native_locators; numeric_trace
- `BREA-E2E-001`: `AGENT_CAPABILITY_GAP` — expected_status; accepted_with_evidence; source_identity; native_locators; selected_level; selected_indicator
- `BREA-SAFE-001`: `AGENT_CAPABILITY_GAP` — expected_status; missing_facts_status; required_missing_facts; next_action
- `BREA-SAFE-002`: `AGENT_CAPABILITY_GAP` — expected_status
- `BREA-CAP-002`: `AGENT_CAPABILITY_GAP` — expected_status

## PR-01..PR-18 evidence state

| PR | Requirement | Post-run state | Evidence cases |
|---|---|---|---|
| PR-01 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001 |
| PR-02 | REQUIRED | PROVEN | BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001 |
| PR-03 | REQUIRED | PROVEN | BREA-SAFE-001 |
| PR-04 | REQUIRED | PROVEN | BREA-SAFE-002 |
| PR-05 | NOT_REQUIRED_NOW | NOT_REQUIRED_NOW | none |
| PR-06 | NOT_REQUIRED_NOW | NOT_REQUIRED_NOW | none |
| PR-07 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002 |
| PR-08 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-E2E-001 |
| PR-09 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-SAFE-001, BREA-SAFE-002 |
| PR-10 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002 |
| PR-11 | NOT_REQUIRED_NOW | NOT_REQUIRED_NOW | none |
| PR-12 | REQUIRED | PROVEN | BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002 |
| PR-13 | NOT_REQUIRED_NOW | NOT_REQUIRED_NOW | none |
| PR-14 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002 |
| PR-15 | REQUIRED | PARTIAL | BREA-CAP-001, BREA-E2E-001, BREA-CAP-002 |
| PR-16 | REQUIRED | PROVEN | BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002 |
| PR-17 | REQUIRED | PROVEN | BREA-E2E-001 |
| PR-18 | NOT_REQUIRED_NOW | NOT_REQUIRED_NOW | none |

## Harvest findings

This report preserves the original execution evidence from `d108ced4056be51a007fc249c4dbfc39b96a79f7`. Harvest interpretation was corrected in this governed descendant commit without rerunning the Agent.

### FN-04/FN-05/SEAM-03 bounded source-evidence binding — DO_NOT_HARVEST_YET

BREA-CAP-001 demonstrates partial source retrieval and conservative claim-boundary behavior for GB 55037-2022. Evidence: BREA-CAP-001, BREA-E2E-001. Boundary: Evidence is limited to the frozen KR-003 benchmark. One positive retrieval route returned related evidence without completing professional reasoning; the second positive E2E route failed to bind reliable evidence. Not proven: Complete source-evidence binding, successful professional-intent routing, accepted applicability resolution, native-locator completeness, deterministic numeric binding, and the DBJ33/T1021-2023 parking-table positive route remain unproven. Reuse value: Keep the existing FN-04/FN-05/SEAM-03 identities as diagnostic targets and future regression/repair evidence. Do not Harvest this capability boundary from this run.

### OBL-03/OBL-04 fail-closed numeric safety — HARVEST_CANDIDATE

Within the frozen KR-003 benchmark, BREA preserves the bounded fail-closed safety obligation that unsupported, unavailable, or out-of-scope evidence does not become an accepted normative numeric conclusion. Evidence: BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002. Boundary: The Harvest claim is only the fail-closed/no-unsupported-numeric safety obligation, not the full Case behavior, clarification UX, or complete professional routing. Not proven: Complete clarification behavior, full professional routing, cross-jurisdiction generality, broader adversarial coverage and Human Professional Acceptance remain unproven. Reuse value: A narrow reusable safety boundary for future governed regression evidence; not universal safety across future Knowledge.

### Case-01 evaluation runner — KEEP_CASE_LOCAL

A minimal public/private-separated deterministic execution path can preserve per-case raw evidence and attribution. Evidence: BREA-CAP-001, BREA-E2E-001, BREA-SAFE-001, BREA-SAFE-002, BREA-CAP-002. Boundary: Runner is intentionally Case-local and replaceable. Not proven: No platform-wide evaluation subsystem or repeated cross-Case stability is proven. Reuse value: Evidence pattern only; do not promote the runner to a Platform service.


## Explicitly unproven boundaries

- Human Product Review and Human Professional Review remain pending.
- E2-C, Admission, and Binding remain unauthorized.
- PR-05, PR-06, PR-11, PR-13, and PR-18 remain NOT_REQUIRED_NOW rather than proven universal capabilities.
- No provider/model behavior, web supplementation, cross-jurisdiction coverage, or non-KR-003 source coverage was evaluated.

## Human review boundary

Machine evidence is sufficient to proceed to Human Product / Professional Review: **FALSE**. Human Product Review and Human Professional Review remain pending; this report does not declare E2-C, Admission, or Binding.

Single next material gap: Natural-language professional-intent routing and complete applicability/evidence binding must be proven for a real user task before Human Review can treat the current product loop as complete.

## Protected boundaries

Candidate, KR-003, benchmark files, Responsibility Map, Platform, Runtime, RuntimeAdapter, Harness, and main were not modified by this execution.
