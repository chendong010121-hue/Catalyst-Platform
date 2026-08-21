# CASE 01-C — TARGETED BUILDER PROOF REPAIR V0.1
## EXECUTION CONTRACT — USER AUTHORIZED

> **Base implementation commit:** `a0b03e1d23512f401a8ddb96efdb1f710383ff93`  
> **Branch:** `case-01`  
> **Authorization:** ONE repair implementation commit + ONE push  
> **CASE 01-D:** NOT AUTHORIZED  
> **Catalyst `main` / Platform Core / Runtime:** NO CHANGE

---

# 0. Goal

Preserve the already-formed BREA Candidate architecture while making the Case-scoped Builder proof genuinely **Governed-Definition-driven** and evidence-consistent.

Do **not** redesign BREA.

Current external verdict:

```text
BREA FORMATION
PASS

MINIMUM GOVERNED BUILDER
TARGETED REPAIR REQUIRED

CASE 01-C
SUBSTANTIVE PASS / TARGETED BUILDER REPAIR REQUIRED
```

The repair must close C-01..C-05 only.

---

# 1. C-01 — Governed Definition Must Control Architecture Projection

Current problem:

`builder/run_builder.py` verifies the definition exists and records its SHA, but generation architecture currently comes from the separately authored `BUILDER_REQUEST_V0.1.json` plus pre-authored templates.

The required proof is:

```text
ACCEPTED GOVERNED DEFINITION
→ BUILDER DETERMINISTIC EXTRACTION / VALIDATION
→ IMPLEMENTATION PROJECTION
→ CANDIDATE
```

not merely:

```text
pre-authored templates
+ manually duplicated architecture request
+ clean-target copy
```

Required repair:

1. Treat `BUILDER_CONSUMABLE_DEFINITION_V0.1.md` as the authoritative architecture input.
2. Case-scoped parsing is sufficient; do not build a generic schema engine.
3. Extract or deterministically validate from the accepted definition:
   - Agent identity/version/purpose where required;
   - FN-01..FN-11 names/governance;
   - SEAM-01..03 ownership/function membership;
   - OBL-01..06;
   - selected legacy adaptation assets;
   - corpus manifest reference;
   - private implementation freedom.
4. If `BUILDER_REQUEST_V0.1.json` remains, it may contain execution parameters such as candidate id/version/target paths, but must not remain an independent architecture authority.
5. Generated Candidate metadata/function/seam maps must be checked against the extracted/validated definition.
6. Any divergence → non-zero exit / no successful build manifest.

Do not change the accepted definition semantics.

---

# 2. C-02 — Enforce Accepted Definition SHA

Accepted SHA:

```text
6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4
```

Required:

```text
actual SHA != accepted SHA
→ FAIL CLOSED
→ non-zero exit
→ no Candidate generation
```

Recording the actual SHA is not sufficient.

Add an executable negative test proving the wrong/modified definition is rejected.

---

# 3. C-03 — Repair Obligation Mapping

Current output manifest references nonexistent test functions:

```text
test_obl_01 ... test_obl_06
```

Replace these with real test/evidence references.

A valid mapping may use:

```text
OBL-01 → T-C01/T-C02 + verbatim assertions
OBL-02 → test_seam02_applicability + T-C02
OBL-03 → test_st06_numeric_traceability + T-C01/T-C02
OBL-04 → test_t_c03_fail_closed
OBL-05 → T-C01/T-C02 provenance/evidence assertions
OBL-06 → test_st05_enterprise_orthogonality + attribution evidence
```

Exact implementation is free, but every referenced test/file must exist and the Builder must validate that it exists.

Reconcile:

```text
BUILDER_OUTPUT_MANIFEST_V0.1.json
OBLIGATION_CONFORMANCE_V0.1.md
FORMATION_EVIDENCE_INDEX_V0.1.md
```

No new public obligations.

---

# 4. C-04 — Repair Broken Evidence Reference

`FORMATION_EVIDENCE_INDEX_V0.1.md` currently references:

```text
01c_selfcheck.log
```

but the file is not committed.

If the authentic original log still exists, preserve it.

If it does not exist:

```text
DO NOT FABRICATE IT
```

Remove the nonexistent reference and preserve the repair rerun's real stdout/stderr as a new committed execution log.

---

# 5. C-05 — Platform Gap Status

Until this repair is proven:

```text
GAP-01 PARTIALLY PROVEN
GAP-05 PARTIALLY PROVEN
```

After successful repair + external audit they may become:

```text
CASE-CLOSED — FOR CASE 01 ONLY
```

Do not claim a generic Catalyst Builder Platform.

---

# 6. Required Builder Tests

At minimum add Case-scoped Builder tests:

```text
BT-01 exact accepted definition SHA passes
BT-02 wrong/modified definition SHA fails closed
BT-03 parsed/validated FN set == FN-01..FN-11
BT-04 parsed/validated seam set == SEAM-01..03
BT-05 parsed/validated obligations == OBL-01..06
BT-06 request cannot override accepted architecture
BT-07 generated Candidate maps match accepted definition
BT-08 manifest obligation references exist
BT-09 non-empty target fails closed
BT-10 raw corpus is not copied
```

Do not replace the existing Candidate tests; add Builder proof on top.

---

# 7. Required Rerun

After repair:

```text
R0  verify branch == case-01
R1  verify accepted definition SHA
R2  run Builder tests BT-01..BT-10
R3  generate Candidate from clean target
R4  validate definition-derived/validated FN/SEAM/OBL mappings
R5  import probe
R6  run all existing Candidate tests
R7  run T-C01 / T-C02 / T-C03
R8  verify corpus SHA / raw corpus absent
R9  verify no changes outside authorized Case 01 paths
R10 reconcile evidence + gap status
R11 self-audit
R12 ONE repair commit + ONE push to case-01
R13 STOP
```

The BREA Candidate behavior should remain materially unchanged unless a bounded repair is required to preserve the already accepted contracts.

---

# 8. Allowed Change Scope

Allowed:

```text
case-01/01-c-governed-local-formation/builder/**
case-01/01-c-governed-local-formation/candidate/brea-v0.1/**  (regenerated output only)
case-01/01-c-governed-local-formation/evidence/**
case-01/01-c-governed-local-formation/findings/**
case-01/01-c-governed-local-formation/review/**
```

Forbidden:

```text
BREA identity/purpose redesign
OBL-01..06 semantic changes
FN-01..11 architecture changes
SEAM-01..03 ownership changes
corpus widening
new model/provider requirement
Catalyst Platform Core change
Runtime change
main change
01-D implementation
generic Builder Platform implementation
raw corpus commit
```

---

# 9. Publication Authorization

The user has explicitly authorized:

```text
ONE targeted repair implementation commit
+
ONE push to case-01
```

No intermediate repair pushes.

If a new problem is discovered after that push:

```text
STOP
→ external review
→ new explicit authorization required
```

---

# 10. Final Report

DeepSeek must return:

```text
REPAIR STATUS
PASS / STOPPED / FAIL

BASE IMPLEMENTATION COMMIT
a0b03e1d23512f401a8ddb96efdb1f710383ff93

REPAIR COMMIT
<sha or NONE>

DEFINITION SHA ENFORCEMENT
PASS / FAIL

DEFINITION SEMANTIC CONSUMPTION / VALIDATION
PASS / FAIL

REQUEST ARCHITECTURE DUPLICATION
REMOVED / VALIDATED / FAIL

FN EXTRACTION / VALIDATION
PASS / FAIL

SEAM EXTRACTION / VALIDATION
PASS / FAIL

OBL EXTRACTION / VALIDATION
PASS / FAIL

MANIFEST OBLIGATION REFERENCES
0 BROKEN / N BROKEN

BUILDER TESTS
N/N PASS

CANDIDATE TESTS
15/15 PASS or details

T-C01
PASS / FAIL

T-C02
PASS / FAIL

T-C03
PASS / FAIL

RAW CORPUS COMMITTED
NO / YES

UNAUTHORIZED PATH CHANGES
0 / N

MAIN
UNCHANGED / CHANGED

GAP-01
CASE-CLOSED / STILL PARTIAL

GAP-05
CASE-CLOSED / STILL PARTIAL

CASE 01-D
NOT AUTHORIZED

FINAL
READY FOR CASE 01-C CLOSURE RE-AUDIT
or
STOPPED — USER / ARCHITECTURE DECISION REQUIRED
```

---

# 11. STOP

After the one authorized repair commit + push:

```text
STOP
→ ChatGPT external closure re-audit
```

Do not begin CASE 01-D.
