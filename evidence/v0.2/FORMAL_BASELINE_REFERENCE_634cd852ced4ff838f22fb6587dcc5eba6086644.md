# V0.2 Formal Baseline Reference

## Registration

- Status: **REGISTERED — V0.2 Formal Baseline Reference**
- Tested SHA: `634cd852ced4ff838f22fb6587dcc5eba6086644`
- Original evidence source: `C:\Users\13752\AppData\Local\Temp\catalyst-live-v0-2-preflight-v2-04`
- Formalization method: original files copied byte-for-byte; no rerun and no result reconstruction
- Result: **4/5 cases, 0 infrastructure failure**

The 4/5 result is valid for this reference. The original UC-003 FAIL is
preserved exactly and is not corrected or beautified.

## Frozen execution identity

| Field | Frozen value |
|---|---|
| benchmark revision | `platform-harness/live_eval/benchmark_v0_2/public_cases.json` SHA256 `cd89c6fc5076bbd5c7f0395931fdc22b0acfb752362e0bc31bf34da1b02a929b` at tested SHA |
| rubric revision | `platform-harness/live_eval/benchmark_v0_2/private_rubric.json` SHA256 `f742dc454865c34f9c48c60dc5ac660ef8cffdac2a79858e93661a34b4861905` at tested SHA |
| provider adapter | `agent_runtime.providers.OpenAICompatibleModelProvider`; source SHA256 `326b92e050310851347b1ffab28cda060f35e78829c66fb56152d9f00b0688ef` |
| base URL | `https://api.deepseek.com` |
| exact model | `deepseek-v4-flash` |
| external capability | `github_repo_read`, read-only GitHub REST API against `chendong010121-hue/agent-runtime` `main`; 8 actual REST calls |
| execution method revision | `platform-harness/live_eval/run_live_user_capability_eval.py` SHA256 `a86505779a767ecb8c4a2f6499931309661164ffc8bf1b9fca217dc34c9d2e4a` |
| workflow revision | `.github/workflows/live-capability-eval.yml` SHA256 `b3d966fcd1f5b70c3d40b54a982b67a969d8a156a1f7dca71f7d2dedb8b1c842` |

## Case results

| Case | Result | Score |
|---|---:|---:|
| UC-001-local-grounded | PASS | 100 |
| UC-002-remote-fallback | PASS | 100 |
| UC-003-fail-closed | **FAIL** | 0 |
| UC-004-authority-conflict | PASS | 100 |
| UC-005-current-state-multitool | PASS | 100 |

## Immutable raw evidence

| File | SHA256 |
|---|---|
| [live_capability_evaluation.json](immutable/formal-baseline-reference-634cd852ced4ff838f22fb6587dcc5eba6086644/live_capability_evaluation.json) | `5c86c548ecd501042b58aa906d7b494d3b792e334f18ae81ce9e1d6ce7b7b251` |
| [LIVE_CAPABILITY_EVALUATION_REPORT.md](immutable/formal-baseline-reference-634cd852ced4ff838f22fb6587dcc5eba6086644/LIVE_CAPABILITY_EVALUATION_REPORT.md) | `ba228b18410f7fa5f422ed7536975b87274087f316383d85bf73ed61e1424f70` |
