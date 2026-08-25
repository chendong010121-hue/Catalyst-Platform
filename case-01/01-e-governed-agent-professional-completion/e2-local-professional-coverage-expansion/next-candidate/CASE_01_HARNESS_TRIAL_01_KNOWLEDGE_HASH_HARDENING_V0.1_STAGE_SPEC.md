# CASE 01 — HARNESS TRIAL 01
## KNOWLEDGE REVISION HASH HARDENING V0.1 STAGE SPEC

> **Status:** STAGE SPEC
> **Implementation Authorization:** **NO**
> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)
> **Case branch:** `case-01`
> **Case baseline before this Stage:** `30e85a917535773844df8f8af20f579ee2538f50`
> **Frozen product reference:** `case-01.brea @ 0.8-candidate`
> **Frozen candidate tree SHA256:** `761552b17cdd57754206d66fe5bfdd4615175ff16cf0fc7da1a67d873988e3df`
> **Frozen Harness executor implementation:** `platform-harness/harness-v0.2-candidate/** @ 2c2fc065d713b4060d3d6ba7200393a1e83e90a6`
> **Platform integration:** **NO**
> **Admission / Binding:** **NO**
> **Purpose:** perform the first real Case 01 development task through the frozen, external, replaceable Catalyst Harness without merging/copying Harness code into Case 01.

---

# 0. Why this is a real task

BREA v0.8 explicitly left one engineering closure item open:

```text
knowledge_hash_hardening = OPEN_AS_AUTHORIZED
```

The v0.8 Stage Contract also records the already-observed problem:

```text
cross-environment Knowledge Revision byte-SHA instability
```

and deliberately kept it out of the residential professional slice so it could be handled separately before final E2 admission / close decisions.

Therefore this Trial is not a manufactured Harness demo.

It closes one already-recorded Case 01 engineering gap.

---

# 1. Dual proof target

This Stage has two independent proof questions.

## CASE PRODUCT / ENGINEERING PROOF

Can BREA replace raw-file-byte Knowledge Revision identity with a stable Case-local canonical Knowledge Revision identity without weakening source integrity or changing professional behavior?

## HARNESS PRACTICAL-USE PROOF

Can the frozen Catalyst Harness V0.2 execute one real, bounded Case 01 development repair against a separately authorized Case workspace, with model → file tool → deterministic verification → evidence, while Harness itself remains external and replaceable?

Passing one does not silently prove the other.

---

# 2. Existing defect boundary

Current v0.8 binding computes Knowledge Revision SHA as:

```text
SHA256(exact file bytes)
```

before accepting the JSON Knowledge Revision.

This means identity can depend on serialization properties that do not represent a Knowledge Revision change, including formatting / key ordering / line-ending representation.

The Knowledge Revision also contains:

```text
sources[].local_reference
```

which is an execution-local machine path.

That path remains necessary for local source loading, but its machine location is not itself the professional / corpus knowledge identity.

Separately, the actual source content is already protected by:

```text
sources[].sha256
```

and `Corpus.verify()` fails closed when the file at `local_reference` does not match the bound source SHA.

Therefore this Stage may separate:

```text
KNOWLEDGE REVISION IDENTITY
from
MACHINE-LOCAL SOURCE LOCATION
```

without removing the runtime source-location binding or source-content SHA verification.

---

# 3. Target identity invariant

The hardened Knowledge Revision SHA must be stable when the same logical revision is represented with differences that are NOT knowledge changes.

Required stable cases:

```text
JSON indentation / whitespace changes
JSON object key order changes
line-ending changes in the JSON serialization
sources[].local_reference changes only because the same SHA-bound source exists at another machine-local path
```

Required identity-changing cases:

```text
knowledge_revision_id changes
schema_version changes
source_id / file_name / source sha256 changes
source authority / title / version / effective-status changes
standards / aliases / source identity changes
routes / applicability declarations change
fact descriptors change
other knowledge-bearing values change
```

The Stage does NOT authorize broad field-classification heuristics.

For V0.1 hardening, only this explicitly identified execution-local field is excluded from Knowledge Revision identity:

```text
sources[].local_reference
```

Do not exclude arbitrary fields named `path`, `location`, `reference`, or similar.

---

# 4. Minimum canonicalization contract

The exact private helper names remain implementation HOW, but the resulting identity must be equivalent to:

```text
1. read UTF-8 JSON
2. parse into structured JSON data
3. validate required Knowledge Revision identity/schema boundary
4. build an identity projection that preserves the complete revision
   EXCEPT sources[].local_reference
5. serialize the projection deterministically as UTF-8 JSON
   with stable object-key ordering and no formatting-dependent whitespace
6. SHA256 the canonical UTF-8 bytes
```

Requirements:

```text
no third-party dependency
no platform-specific newline dependence
no repository-relative-path dependence
no absolute machine-path dependence in the revision hash
no silent coercion of malformed JSON
```

If JSON contains unsupported non-standard numeric values or cannot be deterministically serialized, fail closed rather than inventing an identity.

This is Case-local Knowledge implementation HOW.

It is NOT a Platform-wide canonical JSON standard.

---

# 5. Binding behavior

`load_knowledge_binding(...)` must continue requiring:

```text
revision_id
path
sha256
```

The meaning of binding `sha256` after this hardening becomes:

```text
canonical Knowledge Revision SHA256
```

not raw file-byte SHA256.

Expected flow:

```text
binding.path
→ read + parse Knowledge Revision
→ validate revision/schema
→ compute canonical Knowledge Revision SHA
→ compare with binding.sha256
→ accept or fail closed
```

Successful result / trace continues exposing:

```text
knowledge_revision_id
knowledge_revision_sha256
```

No new Governed Seam is created.

---

# 6. Source integrity must remain independent

Excluding `sources[].local_reference` from Knowledge Revision identity must NOT weaken source-content integrity.

The existing source boundary remains:

```text
local_reference
→ local source file
+
sources[].sha256
→ exact source-content integrity check
```

Required invariant:

```text
same SHA-bound source at another local path
→ same Knowledge Revision identity

wrong source bytes at that path
→ CorpusIntegrityError / fail closed
```

Do not remove, weaken, bypass, or reinterpret `sources[].sha256`.

---

# 7. Professional behavior preservation

This Stage is NOT professional capability growth.

The following must remain unchanged:

```text
v0.8 residential Table（2-3） behavior
P-01..P-09
PC-01..PC-07
v0.7 source-structure behavior
E1 generalized local query
T-C01 / T-C02 / T-C03
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
Platform-bound compatibility
```

No new professional facts, routes, values, applicability semantics, verification obligations, source parsers, or Agent responsibilities are authorized.

---

# 8. Frozen v0.8 protection / repair-candidate semantics

The original v0.8 reference at:

```text
case-01 @ 30e85a917535773844df8f8af20f579ee2538f50
```

remains the frozen evidence baseline.

This Trial must NOT rewrite historical freeze/results evidence to pretend the repair existed in v0.8.

Execution will occur on a separately named temporary Trial branch derived from the later explicit Trial Authorization commit.

A modified `knowledge.py` on that Trial branch is:

```text
BREA KNOWLEDGE-HASH HARDENING PATCH CANDIDATE
```

It is NOT automatically:

```text
v0.8 rewritten
v0.9 formed
admitted
bound
merged to case-01
```

The branch difference itself is the repair candidate for review.

---

# 9. External Harness topology

The Trial must preserve Harness replaceability by using two isolated worktrees / execution roots.

Conceptually:

```text
WORKTREE A — EXECUTOR
agent-runtime @ 2c2fc065d713b4060d3d6ba7200393a1e83e90a6
platform-harness/harness-v0.2-candidate/**
DETACHED / FROZEN EXECUTOR

              acts on
                 ↓

WORKTREE B — TARGET
case-01-harness-trial-01
from exact Trial Authorization commit
CASE 01 repair workspace
```

Rules:

```text
Do NOT merge platform-harness into Case 01.
Do NOT copy Harness source into Case 01.
Do NOT modify frozen Harness implementation.
Do NOT use current platform-harness governance HEAD as executor identity;
pin the proven implementation commit 2c2fc065...
```

This is intentional evidence that Harness is an external replaceable executor capability.

---

# 10. Model-visible task boundary

The Harness model may inspect only the minimum authorized Case files needed for the repair.

Expected read set should include only the relevant subset such as:

```text
v0.8/brea/knowledge.py
v0.8/brea/corpus.py
KR-003.json
this Stage Spec / Trial verification contract if needed
```

The model must be allowed to write exactly one product implementation file:

```text
case-01/01-e-governed-agent-professional-completion/
e2-local-professional-coverage-expansion/
next-candidate/candidate/brea-v0.8/brea/knowledge.py
```

No model write to tests / verification contract is allowed.

No Git tool is exposed to the Harness model.

---

# 11. Deterministic verification — governance-owned

The deterministic verification used by the Harness must be created / frozen before the model-driven repair.

The model must not author or modify its own acceptance test.

Minimum targeted proof must establish:

```text
H-01 same logical JSON / different indentation → same canonical SHA
H-02 same logical JSON / different object-key order → same canonical SHA
H-03 same logical JSON / CRLF vs LF serialization → same canonical SHA
H-04 only sources[].local_reference changes → same canonical SHA
H-05 source sha256 changes → different canonical SHA
H-06 route/fact/other knowledge-bearing change → different canonical SHA
H-07 canonical binding accepts equivalent serialization / local-reference variant
H-08 wrong expected canonical SHA fails closed
H-09 malformed / identity-mismatched Knowledge Revision still fails closed
H-10 wrong actual source bytes still fail source SHA verification independently
H-11 retained v0.8 relevant regression passes
```

Do not create dozens of near-duplicate cases.

---

# 12. Harness behavior proof

The Trial evidence must independently show:

```text
executor implementation commit = 2c2fc065...
target workspace = temporary Case01 Trial worktree
preflight = READY
credential source = USER_LOCAL
fresh model execution uses real DeepSeekModelProvider
model reads only authorized files
model writes only authorized knowledge.py
ExecutionPolicy remains narrower than ApprovalPolicy
fixed governance-owned verification command executes
provider secret absent from tool subprocess environment
verification PASS
repair cycles <= 1
governance_authority = false
```

A passing code test without Harness execution evidence is not enough for the HARNESS PRACTICAL-USE PROOF.

---

# 13. Write / mutation boundary

During model-driven execution, authorized product write:

```text
ONE FILE ONLY:
.../candidate/brea-v0.8/brea/knowledge.py
```

Governance / orchestration may separately create only the minimum Trial control/evidence artifacts explicitly named by the later Authorization.

Forbidden product writes:

```text
KR-001.json
KR-002.json
KR-003.json
corpus.py
runner.py
professional.py
semantic.py
facts.py
any v0.8 professional test
any prior candidate
any prior freeze/results/review artifact
Runtime
RuntimeAdapter
Platform Standard
main
platform-harness implementation
```

If the repair genuinely requires more product files:

```text
STOP
→ REPORT MATERIAL GAP
```

Do not widen scope opportunistically.

---

# 14. Trial result semantics

Valid integrated Trial verdicts:

```text
CASE01_HARNESS_TRIAL_01_PASS
CASE01_HARNESS_TRIAL_01_TARGETED_REPAIR
CASE01_HARNESS_TRIAL_01_FAIL
```

PASS requires BOTH:

```text
KNOWLEDGE HASH HARDENING PROOF = PASS
HARNESS PRACTICAL-USE PROOF = PASS
```

PASS proves only:

> The frozen external Catalyst Harness V0.2 successfully completed one real, bounded Case 01 engineering repair candidate with deterministic evidence, and the proposed Knowledge Revision identity hardening satisfies this Case-local contract.

PASS does NOT automatically authorize:

```text
merge/cherry-pick into case-01
v0.9 identity
E2 close
Admission
Binding
Platform promotion
Platform-wide canonical JSON
future Harness feature work
```

---

# 15. Explicit non-scope

Do NOT add:

```text
new professional coverage
Table（3-2）
road setback
new corpus/source
new Knowledge schema
Knowledge registry/service/database
Platform canonicalization standard
OS/container sandbox
new Harness feature
session resume
MCP
multi-agent
context compaction
Git authority inside Harness
```

A discovered need is evidence, not authorization.

---

# 16. Minimality decision

This Stage deliberately chooses:

```text
one real open Case defect
one product implementation file
one pre-frozen deterministic verification surface
one external frozen Harness executor
one temporary Trial branch
```

It avoids copying the 27-file v0.8 Candidate into a new folder merely to create a test target.

Historical v0.8 remains preserved by commit identity; the Trial branch represents the patch candidate.

---

# 17. Next step after Stage acceptance

Before any implementation:

```text
1. self-review this Stage boundary
2. create the minimum governance-owned deterministic Trial verifier
3. create one explicit Trial Authorization Record
4. commit those pre-implementation control artifacts to case-01
5. only then create the temporary Trial branch/worktree and invoke the frozen Harness
```

No implementation is authorized by this Stage Spec alone.

---

# 18. STOP

```text
STAGE SPEC FORMED
IMPLEMENTATION AUTHORIZATION = NO
HARNESS EXECUTION = NO
TRIAL BRANCH = NOT YET AUTHORIZED
CASE-01 PRODUCT MUTATION = NO
MAIN MUTATION = NO
```
