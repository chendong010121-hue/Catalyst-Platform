# CASE 01-E / E2 — BREA v0.9 Knowledge Identity Hardening Adoption
## STAGE CONTRACT V0.1

> **Status:** STAGE CONTRACT
> **Implementation Authorization:** **NO**
> **Baseline branch HEAD:** `5ac4b3c8256655bed161db4b4297f8f4058e7e0b`
> **Frozen predecessor:** `case-01.brea @ 0.8-candidate`
> **Historical v0.8 freeze reference:** `30e85a917535773844df8f8af20f579ee2538f50`
> **Trial donor:** `case-01-harness-trial-01 @ 3de91bbcf8c74cc9cfd96dd4eb40bbff230c660b`
> **Trial external review:** `CASE_01_HARNESS_TRIAL_01_EXTERNAL_REVIEW_V0.1.md @ 5ac4b3c8256655bed161db4b4297f8f4058e7e0b`
> **Target Candidate:** `case-01.brea @ 0.9-candidate`
> **Knowledge Revision:** `KR-003` — UNCHANGED
> **Professional capability growth:** **NO**
> **E2-C:** **NOT AUTHORIZED**
> **Admission / Binding:** **NOT AUTHORIZED**

---

# 1. Stage thesis

Preserve frozen v0.8 as immutable historical evidence and form Candidate N+1 with exactly one adopted engineering repair:

```text
raw JSON-file-byte Knowledge Revision identity
→
deterministic canonical Knowledge Revision identity
```

The repair has already been independently proven on the isolated Harness Trial 01 branch.

This Stage does NOT rediscover or redesign the mechanism.

It adopts the proven repair into the active BREA product lineage through a new Candidate tree.

```text
FROZEN v0.8
+
TRIAL 01 PROVEN REPAIR
→
v0.9-candidate
```

This is a product repair / lifecycle-hardening Candidate, not a new professional capability version.

---

# 2. Why Candidate N+1 is required

v0.8 explicitly deferred Knowledge hash hardening and required it to remain open before final E2 admission / close decisions.

The historical v0.8 tree is frozen and must not be rewritten.

Case 01 already has precedent that a targeted engineering repair forms Candidate N+1 rather than mutating a frozen predecessor (`v0.4 → v0.5`).

Therefore the Trial repair must not be cherry-picked directly onto the `candidate/brea-v0.8/**` historical tree on `case-01`.

Instead:

```text
candidate/brea-v0.8/**
        ↓ copy as immutable predecessor content
candidate/brea-v0.9/**
        ↓ bounded repair adoption
new frozen Candidate
```

---

# 3. Version / Revision model

This Stage intentionally proves the existing architecture distinction:

```text
Agent Candidate Version changes:
0.8-candidate → 0.9-candidate

Knowledge Revision does NOT change:
KR-003 → KR-003
```

Reason:

The professional/corpus knowledge content is unchanged. Only the Agent-side binding identity mechanism changes.

This Stage must not create `KR-004` merely because the Agent implementation changes.

`Agent Evolution != Knowledge Evolution` remains the governing rule.

---

# 4. Required repair adoption

The new v0.9 `brea/knowledge.py` must adopt the behavior proven by Harness Trial 01.

Required identity semantics:

```text
Knowledge Revision identity
=
SHA256(deterministic canonical UTF-8 JSON projection)
```

The projection preserves all Knowledge Revision content EXCEPT exactly:

```text
sources[].local_reference
```

because this field is the already-proven machine-local execution location rather than professional/corpus knowledge identity.

Stable identity is required across:

```text
JSON indentation / whitespace
object key ordering
JSON serialization line endings
sources[].local_reference-only relocation
```

Identity MUST change when knowledge-bearing content changes, including:

```text
knowledge_revision_id
schema_version
source_id
file_name
source sha256
source authority / title / version / effective status
standards
aliases
routes
applicability declarations
fact descriptors
other knowledge-bearing fields
```

Do not add generic rules that exclude arbitrary fields named `path`, `location`, `reference`, or similar.

---

# 5. Strict JSON / fail-closed boundary

The adopted binding mechanism must continue to fail closed on:

```text
missing binding
missing / unreadable Knowledge Revision file
malformed JSON
non-object top-level JSON
knowledge_revision_id mismatch
required schema boundary missing
unsupported non-standard numeric JSON constants such as NaN / Infinity
canonical SHA mismatch
```

No compatibility fallback to raw-byte SHA is authorized.

A binding that supplies the historical raw file-byte hash should NOT silently pass merely for backward compatibility.

The active v0.9 binding meaning is:

```text
binding.sha256 = canonical Knowledge Revision SHA256
```

---

# 6. Source-content integrity remains independent

Do not weaken or reinterpret:

```text
sources[].sha256
```

Source integrity remains:

```text
sources[].local_reference
→ local source bytes
+
sources[].sha256
→ exact source-content integrity verification
```

Required invariant:

```text
same SHA-bound source at another local path
→ same Knowledge Revision identity

wrong source bytes at that path
→ CorpusIntegrityError / fail closed
```

No source file or source SHA changes are authorized.

---

# 7. Candidate formation boundary

Create a new tree:

```text
candidate/brea-v0.9/**
```

from the complete frozen `candidate/brea-v0.8/**` tree.

Do not mutate:

```text
candidate/brea-v0.8/**
V0_8_RESULTS.json
V0_8_CANDIDATE_REVIEW.md
V0_8_FREEZE_RECORD.json
Harness Trial 01 branch
Harness Trial 01 evidence
KR-001.json
KR-002.json
KR-003.json
```

v0.9 must preserve the same professional implementation unless a file change is mechanically required by the new binding identity or Candidate identity.

---

# 8. Required Candidate identity changes

At minimum:

```text
VERSION = "v0.9-candidate"
LINEAGE_PARENT = "case-01.brea@0.8-candidate"
```

README / Candidate identity text must state that v0.9 is:

```text
Knowledge Revision identity hardening adoption
professional behavior unchanged from frozen v0.8
KR-003 unchanged
```

Do not describe v0.9 as a new professional slice.

FN-01..FN-11, SEAM-01..SEAM-03 and OBL-01..OBL-06 remain unchanged.

No new Governed Seam or Obligation is authorized.

---

# 9. Binding-producer migration inside Candidate tests

The v0.8 test suite contains Candidate-local helpers that construct Knowledge Bindings using raw file-byte SHA for KR-001 / KR-002 / KR-003.

Those helpers are test infrastructure, not normative identity authority.

When copied into v0.9 they must be migrated to construct the canonical Knowledge Revision SHA expected by the new binding contract.

Allowed test changes are limited to:

```text
binding SHA construction needed for canonical identity
v0.9 VERSION / LINEAGE assertions
new v0.9 Knowledge identity hardening tests
path/version text mechanically required by the new Candidate root
```

Forbidden test changes:

```text
weaken professional assertions
remove existing fail-closed assertions
change expected professional facts / outputs
change source evidence expectations
skip previously passing regression cases
rewrite tests merely to accommodate unrelated behavior changes
```

If an existing professional test fails for a reason other than binding identity / Candidate identity migration:

```text
STOP
→ REPORT REGRESSION
```

---

# 10. Minimum new v0.9 proof

Add only the focused Candidate-local checks necessary to prove adoption.

At minimum:

```text
V9-H01 indentation / whitespace stable
V9-H02 object key order stable
V9-H03 JSON LF / CRLF serialization stable
V9-H04 sources[].local_reference-only relocation stable
V9-H05 source sha256 change changes identity
V9-H06 route/fact knowledge change changes identity
V9-H07 canonical KR-003 binding accepted
V9-H08 historical raw-byte SHA does not silently pass as canonical identity
V9-H09 malformed / identity mismatch / NaN / Infinity fail closed
V9-H10 source-content SHA verification remains independent
```

These may reuse the logic already proven by Trial 01 rather than inventing a new canonicalization mechanism.

Do not duplicate eleven nearly identical Trial tests merely for test count if fewer focused Candidate-local tests prove the same contract.

---

# 11. Full regression requirement

v0.9 must run the complete inherited Candidate test suite after binding-producer migration.

Must preserve at minimum:

```text
v0.8 P-01..P-09 residential Table（2-3） behavior
PC-01..PC-07
v0.7 S-01..S-05 source-structure behavior
legacy X.Y.Z
legacy 表5.0.4
E1 generalized local query
five professional forms
T-C01 / T-C02 / T-C03
KR-001 / KR-002 / KR-003 binding semantics under canonical SHA
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
Platform-bound compatibility
anti-hardcode boundary
source-content SHA fail-closed
```

Professional output / applicability behavior must remain unchanged from v0.8.

---

# 12. Trial donor use

Harness Trial 01 is a repair donor and evidence source.

Allowed use:

```text
inspect the proven knowledge.py diff
reconstruct / apply the same bounded mechanism into v0.9
cite Trial 01 as repair lineage evidence
reuse the proven identity invariant
```

Forbidden:

```text
merge the Trial branch
cherry-pick the Trial commit into case-01
copy TRIAL_01_RESULTS / REVIEW into v0.9 evidence
claim Trial PASS automatically equals v0.9 Candidate PASS
```

v0.9 must pass its own Candidate formation / regression / freeze proof.

---

# 13. No Harness expansion

This Stage is Case 01 product work.

It does NOT authorize:

```text
new Harness feature
Harness trace redesign
session resume
multi-agent
MCP
context compaction
new tool surface
new sandbox
```

The Trial 01 audit observation about distinguishing Trial-level session chronology remains an observed gap only.

If the chosen executor can complete v0.9 with current mechanisms, do not reopen Harness development.

---

# 14. Explicit professional non-scope

Do NOT add in v0.9:

```text
Table（3-2） road setback
road_width_m
Q semantics
planning orientation
mixed-use control
full 80m compliance
new source/corpus
new professional route
new professional fact
new reasoning primitive
E2-C
Admission
Binding
```

A discovered need remains evidence, not authorization.

---

# 15. Minimum persistent artifact surface

After explicit implementation authorization, long-lived output only:

```text
candidate/brea-v0.9/**
V0_9_RESULTS.json
V0_9_CANDIDATE_REVIEW.md
V0_9_FREEZE_RECORD.json
```

Do not create a separate design summary, evidence index, migration report, Trial summary, or canonicalization standard document.

The existing Stage Contract + Trial Review are sufficient lineage sources.

---

# 16. Required v0.9 results evidence

`V0_9_RESULTS.json` must record at minimum:

```text
baseline commit
frozen predecessor identity
Trial donor commit
Trial External Review commit
v0.9 version / lineage parent
KR-003 canonical SHA
explicit statement KR-003 content unchanged
canonical identity proof status
historical raw-byte SHA rejection status
source SHA integrity status
full inherited regression status
professional behavior unchanged status
Candidate tree SHA256
Candidate file count
implementation fingerprint
protected-boundary status
```

Do not record machine-local credential / Harness data because this Stage is product adoption, not another Harness Trial proof.

---

# 17. Freeze chronology

After implementation and all required checks pass:

```text
record canonical KR-003 binding identity
record v0.9 Candidate tree SHA
record implementation fingerprint
freeze v0.9
status = FROZEN / NOT ADMITTED / NOT BOUND
ONE implementation + evidence + freeze commit
ONE push to case-01
STOP
```

Then ChatGPT performs External v0.9 Candidate Freeze Review.

Only after External Review PASS may the next E2 close / evaluation / admission decision be considered.

---

# 18. Success boundary

A successful v0.9 may claim only:

```text
KNOWLEDGE REVISION IDENTITY HARDENING
ADOPTED INTO ACTIVE BREA CANDIDATE LINEAGE

KR-003
UNCHANGED KNOWLEDGE REVISION

PROFESSIONAL BEHAVIOR
PRESERVED FROM FROZEN v0.8

CANONICAL KNOWLEDGE BINDING
CASE-PROVEN
```

It may NOT claim:

```text
new professional capability
full Hangzhou planning coverage
E2 complete
production readiness
Admission
Binding
Platform-wide canonical JSON standard
Platform promotion
```

---

# 19. Stage verdict

```text
FROZEN v0.8 IMMUTABILITY
PRESERVED

TRIAL 01 REPAIR DONOR
ACCEPTED AS EVIDENCE SOURCE

TARGET VERSION
case-01.brea@0.9-candidate

KNOWLEDGE REVISION
KR-003 UNCHANGED

PROFESSIONAL CAPABILITY GROWTH
NO

IMPLEMENTATION AUTHORIZATION
NO
```

# VERDICT — READY FOR EXPLICIT v0.9 IMPLEMENTATION AUTHORIZATION
