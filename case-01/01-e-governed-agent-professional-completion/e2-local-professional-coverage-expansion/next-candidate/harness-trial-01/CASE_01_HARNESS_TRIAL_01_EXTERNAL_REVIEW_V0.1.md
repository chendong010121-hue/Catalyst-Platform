# CASE 01 — HARNESS TRIAL 01 EXTERNAL REVIEW V0.1

> **Review status:** COMPLETE
> **Trial branch:** `case-01-harness-trial-01`
> **Trial commit:** `3de91bbcf8c74cc9cfd96dd4eb40bbff230c660b`
> **Authorization commit:** `093d6ec2214a98096dbfaf55fa4f1571b97d92bf`
> **Frozen Harness executor:** `2c2fc065d713b4060d3d6ba7200393a1e83e90a6`
> **Merge / cherry-pick authorization:** **NO**
> **Admission / Binding:** **NO**

---

# 1. Independent repository verification

The Trial branch is exactly one commit ahead of the active Authorization commit:

```text
093d6ec2214a98096dbfaf55fa4f1571b97d92bf
    ↓ one commit
3de91bbcf8c74cc9cfd96dd4eb40bbff230c660b
```

The one Trial commit contains exactly the three authorized persistent files:

```text
candidate/brea-v0.8/brea/knowledge.py
harness-trial-01/TRIAL_01_RESULTS.json
harness-trial-01/TRIAL_01_REVIEW.md
```

The persistent `case-01` branch remained at the Authorization commit after Trial execution.

`main` remained unchanged at:

```text
5874be1130e8867082880fcd63f659fc909d9efd
```

No merge or PR was created by the Trial.

---

# 2. Knowledge Hash Hardening Review

## Verdict

```text
KNOWLEDGE_HASH_HARDENING_PROOF
PASS
```

The repair changes the Knowledge Revision binding from raw JSON-file-byte SHA identity to a deterministic canonical SHA over parsed Knowledge Revision content.

The implementation:

```text
reads strict UTF-8 JSON
rejects NaN / Infinity and malformed JSON
preserves full structured knowledge content
excludes only sources[].local_reference from identity
sorts object keys
uses deterministic compact JSON serialization
hashes canonical UTF-8 bytes
compares the canonical SHA with the explicit binding SHA
fails closed on mismatch
```

The excluded field is narrowly scoped to the already-identified machine-local source location:

```text
sources[].local_reference
```

No broad `path` / `location` / `reference` heuristic was introduced.

Source-content integrity remains independently protected by each `sources[].sha256` and the existing Corpus verification path.

The implementation does not modify professional routes, facts, source parsing, Agent obligations, Runtime, Platform, or Enterprise responsibility.

---

# 3. Deterministic Contract Review

The pre-frozen governance verifier reports:

```text
H-01 PASS — indentation identity stability
H-02 PASS — object-key-order identity stability
H-03 PASS — line-ending identity stability
H-04 PASS — local_reference-only relocation identity stability
H-05 PASS — source SHA remains identity-bearing
H-06 PASS — route / fact changes remain identity-bearing
H-07 PASS — canonical binding accepts equivalent revision
H-08 PASS — wrong canonical SHA fails closed
H-09 PASS — malformed / identity mismatch / non-standard numeric JSON fails closed
H-10 PASS — source-content SHA verification remains independent
H-11 PASS — product diff isolation + representative v0.8 behavior preservation
```

Verifier execution:

```text
11 tests
0 failures
0 errors
exit code 0
```

Representative v0.8 professional behavior remained valid, including the retained T-C01 / T-C02 / T-C03 regression set.

Therefore the repair is supported as a Case-local Knowledge identity hardening mechanism.

It does NOT establish a Platform-wide canonical JSON standard.

---

# 4. Harness Practical-Use Review

## Verdict

```text
HARNESS_PRACTICAL_USE_PROOF
PASS
```

The successful bounded Harness session proves the following practical path:

```text
frozen external Catalyst Harness implementation
        ↓
separate Case 01 target worktree
        ↓
USER_LOCAL credential resolution
        ↓
preflight READY
        ↓
real DeepSeekModelProvider
        ↓
authorized repository reads
        ↓
one authorized product write
        ↓
fixed governance-owned deterministic verifier
        ↓
PASS
```

Observed final-session facts:

```text
model_attempts = 6
repair_cycles = 0
governance_authority = false
provider secret absent from process/tool execution environment as required by the Trial evidence
```

The successful session read only the five authorized repository-relative files and wrote only the authorized `knowledge.py`.

The frozen Harness implementation was not copied into Case 01 and no Harness implementation mutation was required.

This is sufficient evidence that the current frozen Harness can act as an external replaceable development executor for at least one real bounded Case task.

---

# 5. Non-blocking audit chronology observation

`TRIAL_01_REVIEW.md` explicitly records that before the final successful bounded invocation, earlier bounded invocation attempts exposed:

```text
an abbreviated read-path issue
and
a multi-call response issue
```

Those attempts produced no product-file write, no policy widening, no Harness modification, and no scope expansion. The final successful invocation remained inside the authorized boundary.

This does NOT invalidate the current Trial PASS.

However the Trial-level evidence vocabulary can be improved in future real Trials.

Current evidence records:

```text
model_attempts = 6
```

which describes the final successful Harness session and can be misread as the complete Trial-level provider chronology.

For future Trials, evidence SHOULD distinguish at minimum:

```text
trial_session_count
session_outcomes[]
total_model_calls_across_trial
final_session_model_attempts
final_session_repair_cycles
```

This is an observed audit/evidence clarity gap, not current authorization for Harness feature expansion.

Do not modify Harness solely to clean up this notation. Incorporate the distinction when the next real Trial needs execution evidence.

---

# 6. Frozen v0.8 immutability decision

The successful Trial patch modifies the historical path:

```text
candidate/brea-v0.8/brea/knowledge.py
```

on the isolated Trial branch.

The historical v0.8 candidate remains frozen by its original Case commit/tree identity.

Therefore:

```text
DO NOT directly merge or cherry-pick the Trial commit onto case-01
```

because doing so would mutate the current `brea-v0.8` tree while the historical v0.8 freeze records still identify the original candidate tree.

The Trial branch is evidence and a repair donor, not an authorized rewrite of v0.8.

If the repair is adopted into the active Case lineage, it must occur through a separately authorized next Candidate / version formation that preserves v0.8 historical identity and records lineage from both:

```text
frozen v0.8
+
Harness Trial 01 repair evidence
```

The exact next version identity is not authorized by this Review.

---

# 7. Integrated External Verdict

```text
KNOWLEDGE HASH HARDENING
PASS

HARNESS PRACTICAL USE
PASS

AUTHORIZATION / PERSISTENT MUTATION BOUNDARY
PASS

MAIN PROTECTION
PASS

CASE-01 BRANCH PROTECTION DURING TRIAL
PASS

FROZEN HARNESS REPLACEABLE-EXECUTOR CLAIM
CASE-PROVEN FOR THIS BOUNDED TASK

TRIAL-LEVEL INVOCATION CHRONOLOGY VOCABULARY
NON-BLOCKING OBSERVED GAP

DIRECT MERGE / CHERRY-PICK INTO CASE-01
NOT AUTHORIZED

INTEGRATED EXTERNAL REVIEW
CASE01_HARNESS_TRIAL_01 — EVIDENCE-BACKED PASS / CLOSED
```

---

# 8. What this Trial now proves

This Trial supports only the bounded claims below:

1. Catalyst's frozen Harness V0.2 can operate externally against a real Case workspace without being merged into that Case.
2. A real model can inspect bounded Case artifacts, produce one governed code mutation, and satisfy a pre-frozen deterministic verifier.
3. Harness execution intelligence does not gain governance authority.
4. The Case can preserve product/history boundaries while using a replaceable external executor.
5. BREA's Case-local Knowledge Revision identity can be hardened against serialization and machine-local source-path instability without weakening source SHA integrity or changing representative professional behavior.

It does NOT prove:

```text
production-ready Harness
general software-development competence across Cases
provider portability beyond the already proven DeepSeek path
full sandboxing
automatic Agent construction
automatic Capability reuse
Platform integration
E2 completion
BREA admission / binding
```

---

# 9. Next legitimate decision

The Harness Trial itself is closed.

Do not continue horizontal Harness feature development.

Return to CASE 01 product progression.

The next Case decision should ask only:

> Should the proven Knowledge Hash Hardening patch now be adopted through a new BREA Candidate/version while preserving immutable v0.8 history, and what is the smallest Stage needed to do that before E2 close/admission decisions resume?

No adoption implementation is authorized by this Review.
