# Catalyst Platform — Development Workflow Contract

> Permanent repository governance contract for `chendong010121-hue/Catalyst-Platform`.
> This document governs repository change and evidence flow. It is not Runtime architecture, Platform ontology, or a Stage Spec.

## 1. Truth model

- **Current operational state** = `CATALYST_OPERATIONAL_BASELINE_V1.md`
- **Architecture authority** = `ARCHITECTURE.md`
- **Stable governing principles** = active Governing Baseline
- **Accepted code truth** = GitHub `main`
- **Candidate code truth** = repository + branch + exact SHA
- **Verification truth** = tests / CI / frozen evidence tied to exact identity
- **Working copy** = implementation workspace only; never accepted truth by itself
- **Current implementation authorization** = explicit user-approved bounded task / Stage when such work is active

No local path, tool, model, or coding Agent is a permanent Source of Truth.

## 2. Roles, not products

Repository governance is defined by responsibility. Current tools may fill these roles, but the tools themselves are replaceable.

| Role | Responsibility |
|---|---|
| **Product / Release Authority** | decides direction, bounded authorization, acceptance, release, and merge |
| **Implementer** | makes the bounded candidate change |
| **Internal Verifier** | runs local checks and records candidate evidence before publication |
| **Independent Reviewer / Auditor** | reviews architecture, responsibility, evidence, and candidate claims independently when material |
| **GitHub** | version ledger, review transport, branch / SHA identity, CI evidence |

One person or tool may temporarily fill more than one role when the project is small, but self-observation does not automatically become independent certification.

Examples of replaceable role implementations may include Codex, DeepSeek Harness, Pi, Claude Code, another coding Agent, a human developer, or a future system. None is permanently privileged by this workflow.

## 3. Normal change chain

```text
real need / accepted finding
→ identify owning responsibility
→ explicit bounded authorization when implementation is required
→ candidate branch / exact baseline
→ implementation
→ local verification / internal review
→ finding triage
→ publication to GitHub
→ CI / exact-ref evidence
→ independent review when material
→ accept / repair / rebuild / replace / reject
→ merge only after the acceptance boundary is satisfied
→ preserve lineage
→ STOP
```

After Catalyst Minimum Operational V1, do not invent a new Stage merely to continue platform development. Real use or a concrete finding must justify the next bounded change.

## 4. Publication discipline

A publication cycle should be small enough that its responsibility and evidence remain reviewable.

When a candidate changes after review or CI, its exact identity changes. Re-run the evidence that is material to the acceptance claim.

Do not treat:

```text
local success
PR opened
review comment
old CI result
old Stage status
```

as proof that a different commit is accepted.

## 5. Finding triage

Each material finding should be classified into one of:

```text
FIX NOW
PARK / WATCH
OUT OF SCOPE
PRODUCT / ARCHITECTURE DECISION REQUIRED
```

A finding is not automatic authorization to modify Architecture, Platform Core, Runtime, or another layer.

When an implementation fails, use the accepted capability-preserving evolution rule:

```text
OBSERVE
→ ATTRIBUTE
→ PRESERVE durable capability value
→ DIAGNOSE
→ compare REPAIR / REBUILD / REPLACE / ADOPT / RETIRE candidates
→ same responsibility / evidence boundary
→ ACCEPT or ROLLBACK
```

Repair has no automatic priority.

## 6. Verification evidence policy

Current normal CI should cover the active accepted tree, including:

```text
compile / import integrity
minimal Runtime loop
current Platform / Extension contract evidence
active regression modules
Operational V1 proof
```

Stage- or finding-specific verification may add focused deterministic, stress, live-provider, professional, or external-system evidence when the claim actually requires it.

Exact-ref review must record enough identity to know what was tested, such as:

```text
requested ref
actual tested SHA
actual tested tree / artifact identity when material
```

Local evidence and GitHub CI evidence should remain distinguishable when they prove different things.

## 7. Merge rule

Merge when, and only when:

```text
the bounded responsibility is clear
+
required evidence is green / accepted
+
blocking findings are closed or explicitly rejected with rationale
+
Architecture / Contract changes, if any, were separately authorized
+
no unrelated platform expansion was smuggled into the candidate
```

A successful implementation does not automatically redefine Architecture or the Platform Standard.

## 8. Repository hygiene

`main` is the current operational surface, not an archive.

Closed Stages, superseded candidates, old Handoffs, audit campaigns, and Case work should remain recoverable through Git history, closed PRs, and bounded historical refs without competing with current authority.

Do not keep a PR open merely because it is historically interesting. Do not copy historical files back into the active root merely to make them easier to find.

Use `docs/history/README.md` for historical navigation.

## 9. STOP

After an accepted bounded change:

> **STOP.**

Do not automatically continue into the next attractive architecture idea.

The next change must be justified by real use, a concrete failure, or a separately authorized architecture/governance review.
