# CASE 01-D / D2 — REPOSITORY INTEGRITY — V0.1

> Contamination / integrity evidence for the D2 implementation + evidence publication.

## Boundaries

D2 authorized writes: **`case-01/01-d-governed-agent-admission-binding/d2-local-admission-binding/**` only.

Forbidden changes (Stage Spec §16, §19 S-D2-17/18):

```text
Catalyst main · README / ARCHITECTURE / Governing Baseline · platform_standard/**
agent_runtime/** · enterprise_extensions/** · examples/** · root tests/** · CI
CASE 01-B accepted artifacts · CASE 01-C Candidate implementation / accepted evidence
Legacy Agent 2.0 workspace · raw regulation corpus
```

## Preflight (P-D2-00..P-D2-09)

| Check | Result |
|---|---|
| P-D2-00 explicit User D2 execution authorization | PASS — `D2_AUTHORIZATION_RECORD_V0.1.yaml` (granted) |
| P-D2-01 branch == `case-01` | PASS |
| P-D2-02 case-01 includes D1 commit `747317afd0d2f8ca3a09394b4d5de1a22405eec2` | PASS |
| P-D2-03 accepted main == `5874be1130e8867082880fcd63f659fc909d9efd` | PASS |
| P-D2-04 CASE 01-C closure remains present | PASS (G-A02) |
| P-D2-05 D1 external verdict EVIDENCE-BACKED PASS / CLOSED | PASS |
| P-D2-06 no unauthorized local work overwritten | PASS |
| P-D2-07 01-C Candidate unchanged before D2 | PASS (G-A03) |
| P-D2-08 raw corpus outside GitHub | PASS (G-A04) |
| P-D2-09 D2 dir contained Stage Spec / authorization only before implementation | PASS (git status at D2 start: clean except spec/auth) |

## Working-tree contamination check (G-A07 / D2-19)

`git status --porcelain` was evaluated during gate evaluation: the only non-D2 paths
reported were the D2 implementation files themselves (under
`d2-local-admission-binding/`), which the gate explicitly permits.

Verified unchanged paths (git diff vs HEAD at D2 entry `285cfe5`):

```text
platform_standard/  → unchanged
agent_runtime/      → unchanged
enterprise_extensions/ → unchanged
examples/           → unchanged
tests/ (root)       → unchanged
case-01/01-b-governed-agent-definition/  → unchanged
case-01/01-c-governed-local-formation/   → unchanged (candidate + accepted evidence)
```

## Main integrity (S-D2-18)

| Ref | SHA | Status |
|---|---|---|
| `origin/main` at D2 | `5874be1130e8867082880fcd63f659fc909d9efd` | UNCHANGED |

## Raw corpus boundary (S-D2-16 / AC-D2-23)

Raw corpus files (`GB55037-2022.md`, `DBJ33T1021-2023.md`) exist only at the admitted
local source boundary (`E:\试验场地\catalyst-local-lab\building-regulation-evidence-v0.1\artifacts\sources\`),
are never copied into the repo, and are excluded from this commit.
`LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md` remains the only corpus reference in git.

## Publication rule (spec §22)

```text
ONE D2 implementation + evidence commit
+ ONE push to case-01
+ STOP
```

No intermediate push. No PR to main. No post-push repair without new authorization.

## Final integrity statement

```text
UNAUTHORIZED PATH CHANGES   : 0
PLATFORM CORE CHANGE        : NO
RUNTIME / ADAPTER CHANGE    : NO
ENTERPRISE EXTENSION CHANGE : NO
MAIN                        : UNCHANGED
RAW CORPUS COMMITTED        : NO
```
