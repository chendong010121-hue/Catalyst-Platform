# BUILDER RUN REPORT — V0.1 (CASE 01-C)

- candidate: brea-v0.1 (v0.1-candidate)
- builder input: BUILDER_CONSUMABLE_DEFINITION_V0.1.md
- builder input SHA256: 6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4
- clean target: E:\试验场地\Agent Harness\case-01\01-c-governed-local-formation\candidate\brea-v0.1
- generated files: 19
- import probe: PASS
- defects: NONE remaining (see bounded repairs below; final formation PASS)
- generated_at: 2026-08-21T15:11:14+00:00

## Bounded recorded repairs (C5 — §14)

| # | class | defect | correction | changed generated files |
|---|---|---|---|---|
| R-01 | MECHANICAL | first run resolved TARGET_REL with a `..` prefix → generated into `case-01/candidate/` (outside authorized `01-c-governed-local-formation/**`) | `TARGET_REL = Path("candidate") / "brea-v0.1"`; removed erroneous builder output (my own artifact); re-ran into correct clean target | none (regenerated identically into correct path) |
| R-02 | MECHANICAL | `load_corpora` keyed only by CORPUS-* id; standard-id lookups (`GB55037-2022`) failed | template fixed to key by corpus id AND file stem | candidate/brea-v0.1/brea/corpus.py |
| R-03 | INTERPRETATION | source identity vs corpus key confusion (`GB55037-2022` vs `GB 55037-2022`) broke applicability branch and identity display | separated `GB_KEY`/`DBJ_KEY` (corpus keys) from `GB`/`DBJ` (display identities); branch compares keys | candidate/brea-v0.1/brea/runner.py |
| R-04 | MECHANICAL | fail-closed conclusion printed raw fact keys (`floor_area_m2` contained a digit), violating the no-digit invariant | added digit-free Domain `FACT_LABELS`; runner displays labels | candidate/brea-v0.1/brea/facts.py, brea/runner.py |
| R-05 | MECHANICAL | test `_first_number` grabbed the city-class number (`50`) instead of the normative value; fixed to `_normative_number` (value after 不应小于) | test-only correction | candidate/brea-v0.1/tests/test_cases.py |

No ARCHITECTURE defect. No governed definition change. Final state: formation PASS.

See BUILDER_OUTPUT_MANIFEST_V0.1.json for the full mapping.
