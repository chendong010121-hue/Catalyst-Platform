# BREA v0.9 Candidate Review

## Verdict

`BREA_V0_9_CANDIDATE_PASS`

The v0.9 candidate was formed from the complete frozen `candidate/brea-v0.8/**`
tree and adopts only the proven Trial 01 Knowledge Revision identity hardening.
It is frozen as `FROZEN / NOT ADMITTED / NOT BOUND`.

## Authorization and lineage

- Authorization commit: `54e2be38b9f6dfa2ce87032150b4593d7c366979`
- Execution baseline: `54e2be38b9f6dfa2ce87032150b4593d7c366979`
- Stage-contract baseline reference: `5ac4b3c8256655bed161db4b4297f8f4058e7e0b`
- Stage contract: `13633f341a820418ff3c61d87e3de58ef30bc651`
- Frozen predecessor: `case-01.brea@0.8-candidate`, historical freeze `30e85a917535773844df8f8af20f579ee2538f50`
- Trial donor: `3de91bbcf8c74cc9cfd96dd4eb40bbff230c660b`
- Trial External Review: `5ac4b3c8256655bed161db4b4297f8f4058e7e0b`
- Trial branch was neither merged nor cherry-picked.

## Adopted identity contract

`VERSION = "v0.9-candidate"` and
`LINEAGE_PARENT = "case-01.brea@0.8-candidate"`.

The canonical Knowledge Revision SHA is
`4049f7f00e709fd0d97fb30df2a5f59e3073448ad06ad4afa471babbe45a21d2`.
Canonicalization is deterministic UTF-8 JSON over the complete revision,
excluding only `sources[].local_reference`. Historical raw-byte SHA fallback is
rejected. Source-content SHA verification remains independent.

KR-003 is unchanged: its protected repository path has no diff from the
authorization commit, no KR-004 was created, and no knowledge source content was
written.

## Required hardening proof

| Proof | Result |
|---|---|
| V9-H01 indentation/whitespace stable | PASS |
| V9-H02 object key order stable | PASS |
| V9-H03 LF/CRLF stable | PASS |
| V9-H04 local_reference-only relocation stable | PASS |
| V9-H05 source SHA change changes identity | PASS |
| V9-H06 route/fact change changes identity | PASS |
| V9-H07 canonical KR-003 binding accepted | PASS |
| V9-H08 historical raw-byte SHA rejected | PASS |
| V9-H09 malformed/identity mismatch/NaN/Infinity fail closed | PASS |
| V9-H10 source SHA integrity remains independent | PASS |

## Regression closure

All four mandatory commands exited 0:

- `python tests/run_all.py` — PASS; retained structural, seam, and T-C01/T-C02/T-C03 checks.
- `python tests/test_v07_source_structure.py` — PASS; 10 tests.
- `python tests/test_v08_residential_slice.py` — PASS; 12 tests.
- `python tests/test_v09_knowledge_identity.py` — PASS; 10 tests.

P-01 through P-09, PC-01 through PC-07, S-01 through S-05, T-C01/T-C02/T-C03,
legacy clause/table behavior, E1 generalized local query, five professional
forms, FN-01 through FN-11, SEAM-01 through SEAM-03, OBL-01 through OBL-06,
Platform-bound compatibility, anti-hardcode behavior, and source-SHA fail-closed
behavior are PASS. `professional_behavior_changed = false`.

## Boundary and freeze review

- Candidate tree SHA256: `d68bd70cc8edd9900ff385f1cdc5a31f3b6f48b2003a442ccdb3c458c6af9eb0`
- Candidate file count: `29`
- Implementation fingerprint: `cf5ede8acc9528f0b3deab57659cb29f282f4575381474040d9d5b61834e70b6`
- v0.8 predecessor and all protected paths remain unchanged.
- `origin/main` remains `5874be1130e8867082880fcd63f659fc909d9efd`.
- No Platform, Runtime, Harness, admission, binding, E2-C, or new professional capability work was performed.

The only generated evidence is `V0_9_RESULTS.json`, this review, and
`V0_9_FREEZE_RECORD.json`. The candidate and evidence were scanned for
accidental credential or authorization-header exposure; none was found.
