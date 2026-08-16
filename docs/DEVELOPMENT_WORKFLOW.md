# Development Workflow Contract

> Permanent repository governance contract for `chendong010121-hue/agent-runtime`.
> This document is governance documentation, not Runtime architecture or a stage spec.

## Truth model

- **Canonical local workspace** = `E:\试验场地\Agent Harness`
- **Product truth** = user-approved architecture / stage spec
- **Accepted code truth** = GitHub `main`
- **Candidate code truth** = repository + branch + exact SHA
- **Working copy** = `E:\试验场地\Agent Harness`（不是正式 Source of Truth）

## Roles

| Role | Responsibility |
|---|---|
| User | Product / Release Authority（方向、阶段、merge、commit/push 批准） |
| DeepSeek | Local Implementer / Internal Auditor |
| GitHub | Version Ledger / CI / Review Transport |
| ChatGPT | Architecture / Triage / External Audit |

## Iteration chain (permanent)

```text
User stage decision
→ DeepSeek local implementation
→ local verification / internal audit
→ Finding Triage
→ READY FOR USER GIT/PUSH APPROVAL
→ explicit user approval
→ one publication cycle
→ GitHub verification
→ freeze exact SHA
→ ChatGPT External Audit
→ finding triage
→ user merge decision
```

一次明确的用户授权只对应**一次发布周期**（一次 commit + 一次 push）。
CI 失败需要另一次本地修复 + 另一次用户批准。

## Finding triage classification

每个 finding 必须归类为且仅归类为以下之一：

```text
FIX NOW
PARK
OUT OF SCOPE
USER ARCHITECTURE DECISION
```

External Audit finding ≠ automatic implementation authorization。

## Verification evidence policy

- GitHub governance CI 运行：compile + minimal loop + 全部 active regression modules
  （从 candidate tree 实际发现，不重新引入 retired RuntimeDomain tests）。
- Stage-local verification：deterministic concurrency + stage-specific stress。
- External Audit：GitHub evidence 与 local stress evidence 分开记录。
- Exact-ref audit 必须记录：requested ref、actual tested SHA、actual tested tree。
