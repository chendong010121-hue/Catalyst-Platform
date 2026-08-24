# BREA v0.8 Candidate Review

## Identity and scope

`case-01.brea@0.8-candidate` is the v0.7 lineage with KR-003 and one bounded
professional capability: single-nature urban residential land (0701) plus a
numeric residential average-storeys fact selects the applicable source row in
Table（2-3） and returns both source-backed maximum FAR and building density.

KR-003 inherits KR-002 unchanged and adds only the declarative Table（2-3） route,
the three authorized facts, and minimum numeric-band selector semantics. The
numeric values are extracted from the bound source row at execution time; Python
contains no Table（2-3） family answer tuple or source-specific branch.

## Observed results

P-01 through P-09: **PASS**. Positive applicability requires the supported
Hangzhou urban-area jurisdiction, single-nature 0701 land use, no unresolved or
overriding special-area status, and a numeric selector within the source bands.
Missing, invalid, mismatched, or unsupported facts fail closed without
extrapolation. Natural-language paraphrase uses the same generic route.

Native Table（2-3） locator, selected row, FAR/density values, provenance, and the
`住宅建筑高度不大于80米` note remain evidence-bound. The candidate explicitly
does not decide full-project 80m compliance.

The retained v0.7 S-01..S-05 source-structure behavior, legacy X.Y.Z and
`表5.0.4`, E1, PC-01..PC-07, five professional forms, T-C01/T-C02/T-C03,
KR-001/KR-002 binding, FN-01..FN-11, SEAM-01..SEAM-03, OBL-01..OBL-06, and
Platform-bound compatibility all passed.

## Boundary

Table（3-2）, road width, Q, road setback, orientation, mixed-use controls, full
80m compliance, all-Hangzhou planning coverage, v0.9, E2-C, Admission, Binding,
and Platform promotion remain out of scope. Knowledge canonical-hash hardening
remains explicitly open. No raw PDF or local derivative was committed.

Freeze status: **FROZEN / NOT ADMITTED / NOT BOUND**. External v0.8 Candidate
Freeze Review remains required.
