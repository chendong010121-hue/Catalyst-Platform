# CASE 01-E / E2 — BREA v0.9 External Freeze Review V0.1

> **Review status:** COMPLETE
> **Candidate:** `case-01.brea @ 0.9-candidate`
> **Candidate freeze commit:** `c6393d4210708400b492ad9e531002e29fe3635e`
> **Implementation authorization:** `54e2be38b9f6dfa2ce87032150b4593d7c366979`
> **Frozen predecessor:** `case-01.brea @ 0.8-candidate`
> **Knowledge Revision:** `KR-003`
> **Admission / Binding:** **NOT AUTHORIZED**
> **E2-C:** **NOT AUTHORIZED BY THIS REVIEW**

---

# 1. Independent repository chronology review

The implementation/evidence/freeze commit is exactly one commit ahead of the explicit Authorization:

```text
54e2be38b9f6dfa2ce87032150b4593d7c366979
    ↓ exactly one implementation + evidence + freeze commit
c6393d4210708400b492ad9e531002e29fe3635e
```

The commit message is:

```text
case-01: freeze BREA v0.9 knowledge identity hardening
```

The persistent change surface contains only:

```text
candidate/brea-v0.9/**
V0_9_RESULTS.json
V0_9_CANDIDATE_REVIEW.md
V0_9_FREEZE_RECORD.json
```

No existing v0.8, Knowledge, Trial, Platform, Runtime, Harness, repository-root protected file, or main file is changed by the implementation commit.

Remote `case-01` reached the exact freeze commit above before this external review.

Remote `main` remained:

```text
5874be1130e8867082880fcd63f659fc909d9efd
```

Therefore the Authorization / commit chronology and protected branch boundary are PASS.

---

# 2. Candidate N+1 formation review

v0.9 is correctly formed as a complete new Candidate tree rather than a mutation of historical v0.8.

Recorded Candidate surface:

```text
candidate_file_count = 29
candidate_tree_sha256 = d68bd70cc8edd9900ff385f1cdc5a31f3b6f48b2003a442ccdb3c458c6af9eb0
implementation_fingerprint = cf5ede8acc9528f0b3deab57659cb29f282f4575381474040d9d5b61834e70b6
```

Independent Git tree comparison confirms that inside `brea/` all implementation files other than:

```text
identity.py
knowledge.py
```

retain the exact same Git blob identity as frozen v0.8.

The v0.9 README is intentionally changed for Candidate identity / hardening description.

The test fixture tree is byte-identical to v0.8, including:

```text
T-C01.json
T-C02.json
T-C03.json
```

The test changes are limited to the authorized migration surface:

```text
run_all.py
test_cases.py
test_seams.py
test_structural.py
test_v07_source_structure.py
test_v08_residential_slice.py
```

plus the two authorized new test-support/proof files:

```text
knowledge_binding_support.py
test_v09_knowledge_identity.py
```

No unexpected Candidate implementation change is observed.

---

# 3. Version / Knowledge Revision separation review

The operative Candidate identity is:

```text
VERSION = v0.9-candidate
LINEAGE_PARENT = case-01.brea@0.8-candidate
```

The Knowledge Revision remains:

```text
KR-003
```

No KR-004 was created.

The implementation commit contains no change to:

```text
KR-001.json
KR-002.json
KR-003.json
```

This is correct architecture behavior:

```text
AGENT CANDIDATE EVOLUTION
0.8 → 0.9

KNOWLEDGE EVOLUTION
KR-003 → KR-003
```

The Stage therefore provides a concrete Case proof that Agent Candidate Version and Knowledge Revision are independent identities.

---

# 4. Knowledge identity implementation review

The v0.9 `knowledge.py` adopts the Trial-01-proven Case-local canonical Knowledge Revision identity mechanism.

The implementation:

```text
reads UTF-8 JSON
rejects malformed JSON
rejects NaN / Infinity through strict parse handling
requires top-level JSON object
checks revision identity and minimum schema boundary
copies the structured Knowledge Revision
removes only sources[].local_reference from the identity projection
serializes deterministically with sorted keys + compact separators
uses UTF-8 canonical bytes
computes SHA256 over those bytes
compares against binding.sha256
fails closed on mismatch
```

Only:

```text
sources[].local_reference
```

is excluded from Knowledge Revision identity.

There is no broad path/location/reference exclusion rule.

There is no raw-file-byte SHA compatibility fallback.

The historical raw-byte SHA is explicitly tested as rejected under the new v0.9 binding contract.

Source-content integrity remains independent through each source's existing `sources[].sha256` verification.

Therefore:

```text
KNOWLEDGE REVISION IDENTITY HARDENING
PASS
```

This remains Case-local implementation HOW and is NOT a Platform-wide canonical JSON standard.

---

# 5. Test migration integrity review

The inherited professional tests have not been weakened to make the migration pass.

For the v0.8 residential slice, the P-01 through P-09 assertions retain their professional values, applicability conditions, evidence requirements, height-note qualification, paraphrase behavior, and fail-closed conditions.

The material migration is limited to:

```text
raw-byte Knowledge Binding helper
→ canonical Knowledge Binding helper
```

and:

```text
v0.8 VERSION / LINEAGE assertion
→ v0.9 VERSION / LINEAGE assertion
```

The new shared Candidate-local helper centralizes canonical binding construction for KR-001 / KR-002 / KR-003 tests.

The new v0.9 focused suite independently exercises the required property contract:

```text
V9-H01 indentation / whitespace stability
V9-H02 object-key-order stability
V9-H03 LF / CRLF stability
V9-H04 local_reference-only relocation stability
V9-H05 source SHA remains identity-bearing
V9-H06 route/fact knowledge remains identity-bearing
V9-H07 canonical KR-003 binding accepted
V9-H08 historical raw-byte SHA rejected
V9-H09 malformed / mismatch / NaN / Infinity fail closed
V9-H10 source-content SHA integrity remains independent
```

Therefore the migration does not gain PASS by removing or weakening the prior professional contract.

---

# 6. Regression evidence review

The Candidate evidence records all four mandatory commands as exit code `0`:

```text
python tests/run_all.py
python tests/test_v07_source_structure.py
python tests/test_v08_residential_slice.py
python tests/test_v09_knowledge_identity.py
```

The two standalone inherited unittest surfaces report:

```text
test_v07_source_structure.py = 10 tests PASS
test_v08_residential_slice.py = 12 tests PASS
```

The new v0.9 identity surface reports:

```text
test_v09_knowledge_identity.py = 10 tests PASS
```

Recorded preserved Case behavior includes:

```text
P-01..P-09 PASS
PC-01..PC-07 PASS
S-01..S-05 PASS
T-C01 PASS
T-C02 PASS
T-C03 PASS
legacy clause/table behavior PASS
E1 generalized local query PASS
five professional forms PASS
KR-001 canonical binding PASS
KR-002 canonical binding PASS
KR-003 canonical binding PASS
FN-01..FN-11 PASS
SEAM-01..SEAM-03 PASS
OBL-01..OBL-06 PASS
Platform-bound compatibility PASS
anti-hardcode boundary PASS
source-SHA fail-closed PASS
```

`professional_behavior_changed = false` is consistent with both the test evidence and independent tree comparison showing the professional implementation modules are unchanged.

Therefore:

```text
FULL REQUIRED REGRESSION
PASS
```

---

# 7. Freeze evidence review

The evidence artifacts consistently identify:

```text
Candidate = case-01.brea@0.9-candidate
Lineage parent = case-01.brea@0.8-candidate
Knowledge Revision = KR-003
Knowledge SHA semantics = canonical
Status = FROZEN / NOT ADMITTED / NOT BOUND
```

They also record the Trial donor lineage without claiming merge or cherry-pick:

```text
Trial donor = 3de91bbcf8c74cc9cfd96dd4eb40bbff230c660b
Trial external review = 5ac4b3c8256655bed161db4b4297f8f4058e7e0b
```

This is the correct lineage relationship:

```text
frozen v0.8
+
proven Trial repair knowledge
→
new v0.9 Candidate
```

rather than historical rewrite.

---

# 8. Non-blocking documentation observation

`brea/identity.py` correctly declares:

```text
VERSION = v0.9-candidate
LINEAGE_PARENT = case-01.brea@0.8-candidate
```

but one inherited explanatory comment still says:

```text
# v0.8 keeps the accepted function, seam, and obligation identifiers.
```

This is stale inherited prose only. The actual identifiers and operative Candidate identity are correct and the governed maps remain unchanged.

It does NOT justify reopening or mutating the frozen v0.9 Candidate solely for comment cleanup.

If that file is legitimately touched by a future Candidate, the wording should be updated then.

---

# 9. External Freeze Review verdict

```text
AUTHORIZATION CHRONOLOGY
PASS

ONE IMPLEMENTATION + EVIDENCE + FREEZE COMMIT
PASS

FROZEN v0.8 IMMUTABILITY
PASS

COMPLETE v0.9 CANDIDATE N+1 FORMATION
PASS

VERSION / KNOWLEDGE REVISION SEPARATION
PASS

TRIAL-01 REPAIR ADOPTION
PASS

CANONICAL KNOWLEDGE REVISION IDENTITY
PASS

RAW-BYTE SHA FALLBACK REJECTED
PASS

SOURCE-CONTENT SHA INTEGRITY
PASS

TEST MIGRATION WITHOUT PROFESSIONAL WEAKENING
PASS

FULL REQUIRED REGRESSION
PASS

PROFESSIONAL BEHAVIOR PRESERVED
PASS

PLATFORM / RUNTIME / HARNESS / MAIN PROTECTION
PASS

FREEZE STATUS
FROZEN / NOT ADMITTED / NOT BOUND

EXTERNAL FREEZE REVIEW
BREA v0.9 — EVIDENCE-BACKED PASS / CLOSED
```

---

# 10. What v0.9 now proves

v0.9 supports the bounded claims below:

1. The previously proven Knowledge identity repair can be adopted into the active BREA product lineage without rewriting frozen history.
2. Agent Candidate Version may evolve independently from Knowledge Revision identity.
3. KR-003 can be bound through a serialization- and machine-local-path-stable canonical identity while exact source-content SHA verification remains separate.
4. The complete inherited professional behavior survives the binding-identity migration.
5. Harness Trial evidence can act as a repair donor without making Harness part of the product or granting Trial branches merge authority.

v0.9 does NOT prove or authorize:

```text
new professional capability
full Hangzhou planning coverage
E2 complete
E2-C
Admission
Binding
production readiness
Platform-wide canonical JSON
Platform promotion
```

---

# 11. Next legitimate decision

The v0.9 Candidate formation stage is closed.

Do not create v0.10 merely to continue development momentum.

Do not add another professional slice unless a separate E2 decision proves one is required.

The next legitimate work is an **E2 completion / evaluation readiness decision** against the current frozen v0.9 Candidate:

```text
Is the accumulated E2 evidence now sufficient to enter the previously deferred
independent E2-C evaluation / close path,
or is there one still-unclosed requirement that materially blocks it?
```

That question must be answered from the existing E2 contracts / evidence before any new implementation is authorized.
