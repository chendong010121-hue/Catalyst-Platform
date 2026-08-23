# E1 — V0.2 FUNCTION / SEAM / OBLIGATION CONFORMANCE — V0.1

> Stage Spec §16 / AC-E1-19: FN/SEAM/OBL mapping must remain valid for v0.2.

generated_at: 2026-08-23T13:43:31+00:00

## Mapping checks

- FN-01..11 preserved: PASS
- SEAM-01..03 preserved: PASS
- OBL-01..06 preserved: PASS
- no FN removed: PASS

## E1 change classification (from E1_CHANGE_IMPACT_REVIEW_V0.1.md)

| Responsibility | Class |
|---|---|
| FN-01 Intake | EXTENDED |
| FN-02 Facts | UNCHANGED |
| FN-03 Applicability | EXTENDED |
| FN-04/05 Evidence | EXTENDED (major completion) |
| FN-06 Uncertainty | EXTENDED |
| FN-07 Result | IMPLEMENTATION-ONLY |
| FN-08 Artifact | UNCHANGED |
| FN-09 Corpus | EXTENDED (major completion) |
| FN-10 Provider | UNCHANGED (PRIVATE/DEFERRED) |
| FN-11 Runner | EXTENDED |
| SEAM-01 | UNCHANGED |
| SEAM-02 | EXTENDED |
| SEAM-03 | EXTENDED |
| OBL-01..06 | UNCHANGED |

## Obligation evidence (v0.2)

- OBL-01 (direct clause + conditional table professional answers): T-C01/T-C02 PASS (regression).
- OBL-02 (observable applicability chain): E1-S-02 + candidate test_seam02 PASS.
- OBL-03 (numeric authority in corpus text): ST-06 + verbatim assertions in every QMODE handler.
- OBL-04 (no fabrication): QMODE-02/04 missing-clause/table fail closed; B-E1-04/09 PASS.
- OBL-05 (source + locator + verbatim): every evidence item carries source/locator; line-verbatim asserted.
- OBL-06 (enterprise orthogonality): ST-05 PASS (candidate regression).

## Result: PASS
