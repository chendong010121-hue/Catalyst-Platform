# Catalyst V0.2 Evidence Register

> **HISTORICAL EVIDENCE NOTICE**  
> This register preserves V0.2 evidence at the identities and assumptions that existed when those campaigns were accepted. The registered campaign files were not rerun for Operational V1. This register is not current-state authority and does not claim continuous recertification. For current state, use `CATALYST_OPERATIONAL_BASELINE_V1.md`, GitHub `main`, and the current `catalyst-platform-ci` workflow.

This register freezes two already-produced local live campaigns. The raw
campaign files under `immutable/` are copied byte-for-byte from their original
local evidence directories. No campaign was rerun or reconstructed for this
formalization.

## Registered evidence

| Record | Role | Tested SHA | Result | Status |
|---|---|---|---|---|
| [Formal Baseline Reference — 634cd852](FORMAL_BASELINE_REFERENCE_634cd852ced4ff838f22fb6587dcc5eba6086644.md) | V0.2 Formal Baseline Reference | `634cd852ced4ff838f22fb6587dcc5eba6086644` | 4/5, 0 infrastructure failure | REGISTERED |
| [Bounded Durability Candidate — b48b24c9](BOUNDED_CANDIDATE_b48b24c9b196c4326361d11c94e790d6dd231ae3.md) | bounded crash-window candidate | `b48b24c9b196c4326361d11c94e790d6dd231ae3` | 5/5, 0 infrastructure failure | ACCEPTED AS BOUNDED CANDIDATE |

## Provenance rules

- The 634 reference is intentionally retained as 4/5. Its UC-003 failure is
  not corrected, rerun, or cosmetically rewritten.
- The b48 candidate's UC-003 PASS is not attributed to the durability repair.
  The candidate basis is the crash-window deterministic evidence, the recorded
  full deterministic regression with no degradation, and the recorded live
  campaign with no new infrastructure regression.
- GitHub Actions run [32971140622](https://github.com/chendong010121-hue/agent-runtime/actions/runs/32971140622)
  is recorded separately as a CI credential/reproducibility issue: its model
  probe returned HTTP 401 before the benchmark. It is not a Formal Baseline
  failure and did not authorize any Catalyst change.
- PR #13 remains open and unmerged.
