# E1 — V0.1 BASELINE INTEGRITY — V0.1

> Stage Spec §2/§16/§17: the admitted v0.1 baseline must remain unchanged;
> the D2 implementation fingerprint must remain valid (P-E1-04, AC-E1-01/21).

generated_at: 2026-08-23T13:43:31+00:00

## D2 fingerprint recheck (accepted 01-C manifest vs current v0.1 tree)

| file | manifest sha256 | actual sha256 | match |
|---|---|---|---|
| brea\__init__.py | 0f51a29aff69b465… | 0f51a29aff69b465… | PASS |
| brea\applicability.py | 8dc26da64544e4ac… | 8dc26da64544e4ac… | PASS |
| brea\contracts.py | 365d078b2e453572… | 365d078b2e453572… | PASS |
| brea\corpus.py | 115c9fef1a2c0566… | 115c9fef1a2c0566… | PASS |
| brea\evidence.py | da16ee7b4d6844bb… | da16ee7b4d6844bb… | PASS |
| brea\facts.py | 2d4fa36de03e2c99… | 2d4fa36de03e2c99… | PASS |
| brea\identity.py | a1bc3658d89f885b… | a1bc3658d89f885b… | PASS |
| brea\result.py | b9432816038b7fc6… | b9432816038b7fc6… | PASS |
| brea\runner.py | a14f7c329a7a568b… | a14f7c329a7a568b… | PASS |
| brea\uncertainty.py | 35af56e82a3013d3… | 35af56e82a3013d3… | PASS |
| README.md | 306a199f245245c1… | 306a199f245245c1… | PASS |
| tests\__init__.py | 77a0acbb84c2926c… | 77a0acbb84c2926c… | PASS |
| tests\fixtures\requests\T-C01.json | a3201df11cef2b5c… | a3201df11cef2b5c… | PASS |
| tests\fixtures\requests\T-C02.json | 0c7f7e24e75a6515… | 0c7f7e24e75a6515… | PASS |
| tests\fixtures\requests\T-C03.json | 16f6c33560c6cecd… | 16f6c33560c6cecd… | PASS |
| tests\run_all.py | 6d924314452c77c5… | 6d924314452c77c5… | PASS |
| tests\test_cases.py | 1c830a5afd1d4907… | 1c830a5afd1d4907… | PASS |
| tests\test_seams.py | 20379aaa71dd1448… | 20379aaa71dd1448… | PASS |
| tests\test_structural.py | 9459db6d1ca8a2d0… | 9459db6d1ca8a2d0… | PASS |

## Result: PASS

The admitted v0.1 Candidate is byte-unchanged; the D2 admission/binding evidence
(admission-case-01-brea-v0.1-001 / binding-case-01-brea-v0.1-001) remains valid.
