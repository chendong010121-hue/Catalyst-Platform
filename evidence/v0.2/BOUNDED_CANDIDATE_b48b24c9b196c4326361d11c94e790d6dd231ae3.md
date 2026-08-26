# V0.2 Bounded Durability Candidate

## Registration

- Status: **ACCEPTED AS BOUNDED CANDIDATE**
- Candidate SHA: `b48b24c9b196c4326361d11c94e790d6dd231ae3`
- Candidate scope: native-tools v2 settled-history crash-window recovery
- Original evidence source: `C:\Users\13752\AppData\Local\Temp\catalyst-live-v0-2-preflight-v2-repair-b48b24c9`
- Formalization method: original files copied byte-for-byte; no rerun and no result reconstruction
- Result: **5/5 cases, 0 infrastructure failure**

## Frozen execution identity

The candidate was evaluated against the same frozen benchmark and rubric as the
Formal Baseline Reference:

| Field | Frozen value |
|---|---|
| tested SHA | `b48b24c9b196c4326361d11c94e790d6dd231ae3` |
| benchmark revision | `public_cases.json` SHA256 `cd89c6fc5076bbd5c7f0395931fdc22b0acfb752362e0bc31bf34da1b02a929b` |
| rubric revision | `private_rubric.json` SHA256 `f742dc454865c34f9c48c60dc5ac660ef8cffdac2a79858e93661a34b4861905` |
| provider adapter | `agent_runtime.providers.OpenAICompatibleModelProvider`; source SHA256 `326b92e050310851347b1ffab28cda060f35e78829c66fb56152d9f00b0688ef` |
| base URL | `https://api.deepseek.com` |
| exact model | `deepseek-v4-flash` |
| external capability | `github_repo_read`, read-only GitHub REST API; 8 actual REST calls |
| execution method revision | `run_live_user_capability_eval.py` SHA256 `7e8d66645de59c31714b1797c6a6ea5ba4a5f1f3f4d94e036a706d4f9a8e5fcd` |
| workflow revision | `.github/workflows/live-capability-eval.yml` SHA256 `b3d966fcd1f5b70c3d40b54a982b67a969d8a156a1f7dca71f7d2dedb8b1c842` |

## Case results

| Case | Result | Score |
|---|---:|---:|
| UC-001-local-grounded | PASS | 100 |
| UC-002-remote-fallback | PASS | 100 |
| UC-003-fail-closed | PASS | 100 |
| UC-004-authority-conflict | PASS | 100 |
| UC-005-current-state-multitool | PASS | 100 |

## Acceptance attribution boundary

The UC-003 transition from FAIL in the 634 reference to PASS in this candidate
is **not attributed to the durability repair**. The accepted bounded-candidate
basis is:

1. crash-window deterministic evidence: v2 call A with `execution_id=exec-A`
   is recovered from settled Core history without a Capability replay, while
   sibling B executes once;
2. the recorded full deterministic regression had zero failures and no
   regression; and
3. the recorded live campaign had zero infrastructure failures and no new live
   campaign regression.

## Immutable raw evidence

| File | SHA256 |
|---|---|
| [live_capability_evaluation.json](immutable/bounded-candidate-b48b24c9b196c4326361d11c94e790d6dd231ae3/live_capability_evaluation.json) | `9f2e123fb124556dd85372d1657507c23b69b1febe440cd4c4697349909c6303` |
| [LIVE_CAPABILITY_EVALUATION_REPORT.md](immutable/bounded-candidate-b48b24c9b196c4326361d11c94e790d6dd231ae3/LIVE_CAPABILITY_EVALUATION_REPORT.md) | `3a64ece87d9ed79397c9fcd3cb2c77874b135648f916d3760634202b59e05aa0` |
