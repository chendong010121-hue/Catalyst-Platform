# CASE 01-C — FINAL SEMANTIC PARSER REPAIR V0.1
## EXECUTION CONTRACT — USER AUTHORIZED

> **Branch:** `case-01`  
> **Base repair commit:** `623dce34b468bc28e381a45282a79be48d4c5571`  
> **Authorization:** ONE final repair implementation commit + ONE push  
> **CASE 01-D:** NOT AUTHORIZED  
> **Catalyst main / Platform Core / Runtime:** NO CHANGE

---

# 0. Goal

Close the final CASE 01-C semantic parser defect without redesigning BREA or widening scope.

Current external status:

```text
BREA FORMATION
PASS

DEFINITION-DRIVEN BUILDER
SUBSTANTIVE PASS

REMAINING DEFECT
SELECTED vs DEFERRED LEGACY ASSET SEMANTICS

CASE 01-C
SUBSTANTIVE PASS / FINAL TARGETED REPAIR REQUIRED
```

---

# 1. Problem

The accepted Governed Definition states:

```text
SELECTED FOR 01-C
A-02
A-04
A-11
A-12
A-13a

DEFER
A-01
A-03
A-05
```

Current `definition_parser.parse_allowed_assets()` extracts all `A-*` tokens from the section and therefore incorrectly treats deferred assets as allowed.

This is a governance-semantic defect.

The Builder must preserve the distinction:

```text
SELECTED FOR ADAPTATION
!=
DEFERRED
```

---

# 2. Required Parser Repair

Change the Case-scoped parser so Section 7 produces two explicit sets:

```text
selected_assets
= {A-02, A-04, A-11, A-12, A-13a}

deferred_assets
= {A-01, A-03, A-05}
```

Required invariants:

```text
selected_assets == exact accepted selected set

deferred_assets == exact accepted deferred set

selected_assets ∩ deferred_assets == empty
```

Do not use a single ambiguous `allowed_assets` field containing both groups.

If an `allowed_assets` compatibility field remains, it may contain **selected_assets only**.

---

# 3. Builder / Manifest Semantics

Update Builder output so it explicitly records:

```text
selected_legacy_adaptation_assets

deferred_legacy_assets
```

Only selected assets may be eligible for CASE 01-C adaptation.

Deferred assets must never be represented as build-authorized.

If generated Candidate metadata or Builder logic consumes the asset set, validate it against `selected_assets` only.

Do not change the already accepted actual adaptation trace unless a consistency update is needed.

---

# 4. Private Implementation Freedom Precision

Current parser records only:

```text
private_freedom_present = true
```

Choose one bounded option:

## Option A — Preferred

Parse the actual private implementation freedom entries from the accepted definition and record them explicitly.

## Option B — Acceptable

Keep only presence validation, but rename the claim to:

```text
private_freedom_section_present
```

and do not claim full semantic extraction of that list.

Do not create a generic schema engine.

---

# 5. Required Builder Tests

Keep BT-01..BT-10 passing and add at minimum:

```text
BT-11 selected legacy asset set exact

BT-12 deferred legacy asset set exact

BT-13 selected/deferred disjoint
```

If Option A is used:

```text
BT-14 private implementation freedom extraction / validation
```

If Option B is used, test only the explicit section-presence claim.

---

# 6. Required Rerun

After repair:

```text
F0  verify branch == case-01
F1  verify accepted definition SHA
F2  run Builder tests BT-01..BT-13/14
F3  regenerate Candidate from clean target
F4  verify selected/deferred asset semantics
F5  verify FN/SEAM/OBL mapping unchanged
F6  run Candidate tests
F7  require 15/15 PASS
F8  rerun T-C01 / T-C02 / T-C03
F9  verify corpus SHA / raw corpus absent
F10 verify unauthorized path changes = 0
F11 reconcile Builder manifest + formation evidence + gap update
F12 self-audit
F13 ONE final repair commit + ONE push to case-01
F14 STOP
```

BREA behavior must remain materially unchanged.

---

# 7. Files Allowed to Change

Allowed only as needed:

```text
case-01/01-c-governed-local-formation/builder/**
case-01/01-c-governed-local-formation/candidate/brea-v0.1/**  (regenerated output only)
case-01/01-c-governed-local-formation/evidence/**
case-01/01-c-governed-local-formation/findings/**
case-01/01-c-governed-local-formation/review/**
```

Forbidden:

```text
BREA identity / purpose change
OBL-01..06 change
FN-01..11 change
SEAM-01..03 ownership change
corpus widening
new model/provider requirement
Platform Core change
Runtime change
main change
01-D implementation
generic Builder Platform
raw corpus commit
```

---

# 8. Gap Status

Before final external closure:

```text
GAP-01
CONDITIONALLY CASE-CLOSED

GAP-05
CONDITIONALLY CASE-CLOSED
```

After this repair passes external audit:

```text
GAP-01
CASE-CLOSED — CASE 01 ONLY

GAP-05
CASE-CLOSED — CASE 01 ONLY
```

Do not claim generic Catalyst Platform capability.

---

# 9. Publication Authorization

The user explicitly authorizes:

```text
ONE final semantic-parser repair implementation commit
+
ONE push to case-01
```

No intermediate implementation pushes.

If any new architecture problem appears:

```text
STOP
→ do not widen scope
→ do not consume another commit authorization
→ return for external review
```

---

# 10. Final Report

DeepSeek must return:

```text
FINAL SEMANTIC REPAIR
PASS / STOPPED / FAIL

BASE COMMIT
623dce34b468bc28e381a45282a79be48d4c5571

FINAL REPAIR COMMIT
<sha or NONE>

SELECTED ASSETS
A-02 / A-04 / A-11 / A-12 / A-13a

DEFERRED ASSETS
A-01 / A-03 / A-05

SELECTED-DEFERRED OVERLAP
0 / N

PRIVATE FREEDOM HANDLING
PARSED / PRESENCE-ONLY

BUILDER TESTS
N/N PASS

CANDIDATE TESTS
15/15 PASS

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
CASE-CLOSED / STILL OPEN

GAP-05
CASE-CLOSED / STILL OPEN

CASE 01-D
NOT AUTHORIZED

FINAL
READY FOR CASE 01-C FINAL CLOSURE RE-AUDIT
or
STOPPED — USER / ARCHITECTURE DECISION REQUIRED
```

---

# 11. STOP

After the one authorized final repair commit + push:

```text
STOP
→ ChatGPT final closure re-audit
```

Do not begin CASE 01-D.
