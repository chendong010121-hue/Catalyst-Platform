# HANDOFF — Cooperative Cancellation & Timeout v0.1 Mainline Alignment

> 阶段：把 Runtime 从「RuntimeDomain / cross-Runtime domain 扩张」拉回 v0.x 支持契约 —— 保留 Cooperative Cancellation / Timeout / late-evidence / live-guard 全部语义，移除「多个 Runtime 实例并发协调同一 live Session」这一从未属于 v0.x 支持契约的假设。
> 依据：`CANCELLATION_TIMEOUT_MAINLINE_REALIGNMENT_SPEC.md`（IMPLEMENTATION AUTHORIZED — LOCAL ONLY）。

## 结果

`READY FOR USER GIT/PUSH APPROVAL`（本地实现 + 验证完成；尚未 commit/push）。

工作目录 `E:\试验场地\Agent Hardness` **不是 git 仓库**（`CANONICAL WORKSPACE IS NON-GIT`）。若需 commit/push，必须先由用户批准「把此目录绑定为 Git 仓库」并创建新 stage 分支（见 §29/§30）。

## 核心变更（KEEP / REMOVE）

| 项 | 处置 |
|---|---|
| CancellationToken / CancellationSource / ExecutionCancelled / ExecutionContext / ExecutionDeadline / ExecutionTimeoutConfig | **KEEP** |
| ActiveExecutionRegistry / LateCompletionEvidenceRegistry | **KEEP**（Runtime-local） |
| ExecutionControlPlane | **KEEP，但收窄**：由单个 Runtime 组合根拥有，不再是多 Runtime 协调器 |
| Runtime.cancel / reconcile / run / resume / start / create | **KEEP**（同 Runtime 边界） |
| live-guard（ExecutionStillLiveError）/ late-evidence guard / post-commit evidence cleanup | **KEEP** |
| `RuntimeDomain` | **REMOVE**（从 Runtime 公共契约移除） |
| `RuntimeDomainBindable` / `claim_runtime_domain` / `get_runtime_domain` | **REMOVE** |
| `RuntimeDomainConflictError` | **REMOVE** |
| StateStore domain claim 要求 | **REMOVE**（StateStore 回归纯 `load`/`commit`） |

## 新组合

```python
Runtime(reasoner, capabilities, policy, state_store, *, timeout_config=None)
```

`Runtime` 内部自建一个 Runtime-local `ExecutionControlPlane`，注入 `DefaultCapabilityExecutor` / `ThreadedExecutionRunner`，供 `cancel`/`reconcile` 查询同一份 active/evidence 状态。只读观察入口：`runtime.control_plane`（不提供注入 / 跨 Runtime 共享 API）。

## Change Manifest

```
FILES CHANGED (production):
  agent_runtime/execution.py          (移除 RuntimeDomain / RuntimeDomainBindable / claim)
  agent_runtime/runtime.py            (构造函数改 state_store + 内部 ExecutionControlPlane)
  agent_runtime/capability_executor.py (guard 理由改为 execution-control 依赖)
  agent_runtime/errors.py             (移除 RuntimeDomainConflictError)
  examples/fakes.py                   (InMemoryStateStore 回归纯 load/commit)

FILES CHANGED (tests): 18 个 test_*.py + run_deepseek_e2e.py + run_deepseek_native_tool_e2e.py
FILES ADDED: examples/test_cancellation_timeout_mainline.py (CT-MA-1..12)

FILES REMOVED FROM ACTIVE MAINLINE (retired, history retained on GitHub PR #1):
  examples/test_runtime_domain_identity.py
  examples/test_runtime_domain_uniqueness.py

TESTS REWRITTEN (cross-Runtime -> same-Runtime):
  test_control_plane_evidence_integrity  A(spy->lower-level runner) / B3 / G2
  test_late_completion_control_plane     L7/L8/L9

FULL REGRESSION RESULT: 21 modules PASS (20 retained + 1 new CT-MA), 0 failures
500-STRESS RESULT: 500 iterations PASS (27.22s, 0 intermittent failures)
INTERNAL P0/P1 COUNT: P0=0 / P1=0
CURRENT ABSOLUTE WORKSPACE PATH: E:\试验场地\Agent Hardness
```

## 尚未授权（STOP 边界）

```text
commit / push / merge / close-reopen PR / force-push / rebase / reset
git init / remote rebinding
修改 agent-runtime-git 或任何临时 clone
```

PR #1 保持 `OPEN / FROZEN / NOT MERGED`（head `2d546c07`）。外部审计新发现仍 PARKED（canonical domain authenticity / binding immutability / control-plane identity immutability），本轮**未实现**。
