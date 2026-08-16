# IMPLEMENTATION NOTES — Cooperative Cancellation & Timeout v0.1 Mainline Alignment

> 本轮把 Runtime 拉回 v0.x 支持契约：`ExecutionControlPlane` 从「跨 Runtime 共享的 domain 协调器」收窄为「单个 Runtime 组合根拥有的 Runtime-local 服务」，并移除 `RuntimeDomain` 对 StateStore 的 claim。

## 实现要点

- **A. Runtime 组合根回归直连形式**：`Runtime(reasoner, capabilities, policy, state_store, *, timeout_config=None)`。不再有 `domain` 参数。
- **B. Runtime-local ExecutionControlPlane**：`Runtime.__init__` 内部 `self._control_plane = ExecutionControlPlane()`，注入 `DefaultCapabilityExecutor(control_plane=self._control_plane)`。`Runtime.cancel` / `Runtime.reconcile` 与 executor/runner 查询同一份 active/evidence 状态。
- **C. 只读观察入口**：`@property Runtime.control_plane` 返回内部 plane（供测试/诊断观察 active/evidence），不提供注入 / 跨 Runtime 共享 API。
- **D. StateStore 契约回归纯 load/commit**：不再要求 `claim_runtime_domain` / `get_runtime_domain` / `RuntimeDomainBindable`。`InMemoryStateStore` 及所有测试 store 回归普通类。
- **E. 下层 executor guard 保留但改理由**：timeout-enabled `DefaultCapabilityExecutor` 无 `control_plane` → `RuntimeConfigurationError`，理由是「execution-control 依赖」，不再是「RuntimeDomain / cross-Runtime safety domain」。

## 移除清单

| 符号 | 位置 | 处置 |
|---|---|---|
| `RuntimeDomain` | execution.py | 删除 |
| `RuntimeDomainBindable` | execution.py | 删除 |
| `claim_runtime_domain` / `get_runtime_domain` | execution.py | 删除 |
| `RuntimeDomainConflictError` | errors.py | 删除 |
| `Runtime(..., domain=...)` | runtime.py | 改为 `state_store` |

## 保留不变式（与 v1.8 一致，仅去掉 domain 层）

| Invariant | 含义 | 支撑 | 是否可能绕过 |
|---|---|---|---|
| I-cancel-ownership | 同一 Runtime 拥有 run/resume/reconcile/cancel + execution-control 状态 | Runtime-local plane | NO（同一 Runtime） |
| I-timeout-uncertain | deadline/request ≠ Failure；未 quiesce → pending unresolved | CapabilityTimeoutUncertainError | NO |
| I-live-guard | live worker 阻止同 Runtime reconcile（ExecutionStillLiveError） | ActiveExecutionRegistry | NO |
| I-late-evidence | late authoritative outcome 与 reconcile 不得矛盾 | LateCompletionEvidenceRegistry | NO |
| I2 publish-before-remove | done callback 先 publish evidence 再 remove active | ThreadedExecutionRunner._on_uncertain_done | NO |
| I-owner-only-writes | 只有 owner 线程写 Session；worker 只产出 outcome | AgentCore / Runtime | NO |
| I-store-purity | StateStore 只 load/commit，不含 execution-domain claim | Protocol | NO（CT-MA-10） |
| I-no-domain | Runtime 公共契约不含 RuntimeDomain | 构造函数签名 | NO（CT-MA-11） |

## 并发 / 确定性

`ActiveExecutionRegistry` / `LateCompletionEvidenceRegistry` 各自独立短锁；done callback 固定顺序 `publish evidence → remove active`；无嵌套锁、无持锁 commit/execute。确定性并发测试以 `Event`/线程为 primary proof，`sleep` 仅用于 quiescence 轮询窗口。

## 不支持（明确 out-of-scope，v0.x 非 P0）

```text
Runtime A 与 Runtime B 并发驱动同一 Session
跨 Runtime 取消路由 / 跨 Runtime 同一 live Session reconcile
多进程同 Session 执行 / 分布式执行所有权 / 多写者
```

「Python 能构造出多 Runtime 组合」本身不构成 v0.x P0。
