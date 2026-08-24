# BREA v0.6 Candidate Review

## Identity and scope

`case-01.brea@0.6-candidate` is the v0.5 candidate lineage with only the proven Knowledge Revision lifecycle coupling removed. The candidate binds an external Case-local `KR-001` explicitly. KR-001 contains only the two knowledge sources already used by v0.5: GB55037-2022 and DBJ33T1021-2023. No Hangzhou source, new fact, new route, source-format parser, Platform, Runtime, or RuntimeAdapter change was introduced.

## Observed results

K-01 through K-09: **PASS**.

The v0.6 runner has no fixed dependency on `LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md` and no candidate-local `professional_data.json` ownership. Missing or invalid explicit knowledge binding fails closed. Successful result metadata and professional trace contain both `knowledge_revision_id=KR-001` and the verified KR-001 SHA-256.

The retained v0.5 professional path, E1 generalized local query, T-C01, T-C02, T-C03, FN-01..FN-11, SEAM-01..SEAM-03, OBL-01..OBL-06, and Platform-bound compatibility all passed or remained preserved in the construction checks.

## Boundary

This evidence proves only Case-local Knowledge Lifecycle Decoupling for KR-001. It does not prove Hangzhou ingestion, KR-002, new professional coverage, Admission, Binding, E2-C, or Platform promotion. The two upstream corpus files remain external read-only inputs and raw corpus was not committed.

Freeze status: **FROZEN / NOT ADMITTED / NOT BOUND**. External v0.6 Freeze Review remains required.
