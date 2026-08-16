# IMPLEMENTATION NOTES — RuntimeDomain Identity Closure

> 本轮把 StateStore 与 ExecutionControlPlane 提升为同一个 composition identity（RuntimeDomain），并固化 I1–I8 invariant。

## Composition boundary decision（spec §4）

- A. RuntimeDomain identity = 一个 session namespace 的持久化 namespace（StateStore）+ execution safety namespace（ExecutionControlPlane）的绑定对象。
- B. Runtime **不再**接受独立的 `state_store` / `control_plane`；只能由 `domain` 构造（`Runtime(reasoner, capabilities, policy, domain, *, timeout_config=None)`）。
- C. 所有 session 操作（create/run/resume/reconcile/cancel）都经由 domain 的 store + control plane。
- D. timeout-disabled Runtime 也必须由同一 domain 构造，因此它访问同一 control plane（live/evidence 可见），不能绕过。
- E. 下层 `DefaultCapabilityExecutor` / `ThreadedExecutionRunner`：timeout enabled 且无 control plane → `RuntimeConfigurationError`（Contract A：lower-level timeout composition supported but must belong to a control domain）。

## Invariants

| # | invariant | enforcement location | bypassable? |
|---|---|---|---|
| I1 Domain Identity | 同一 session namespace → 同一 RuntimeDomain | `Runtime.__init__` 只收 `domain`；`RuntimeDomain` 绑定 store+cp | NO（结构上无独立 store+cp 参数） |
| I2 Active Visibility | live execution → domain 内每个 Runtime 见同一 active fact | `RuntimeDomain.execution_control_plane.active`（共享） | NO |
| I3 Late Evidence Visibility | authoritative late result → domain 内每个 Runtime 见同一 evidence | `RuntimeDomain.execution_control_plane.evidence`（共享） | NO |
| I4 No Safety Island | 不能静默创建 private registry/evidence/cp | Runtime 不创建 private cp；timeout executor 无 cp → error | NO |
| I5 Timeout-independent Safety | timeout-disabled Runtime 仍遵守 live/evidence/reconcile guard | 同一 domain 的 control plane 共享（reconcile 查 domain cp） | NO |
| I6 Wrong Identity Fails Closed | domain/store/cp 不匹配 → 失败 | 无独立配对 API（TypeError）+ 下层 timeout 无 cp → error | NO |
| I7 Owner-only Durable Writes | 不引入 background settle / callback store write | done callback 只写 registry/evidence；owner 才 commit | NO |
| I8 Evidence Semantics Preserved | late Success/Failure authoritative / late requested cancel → Failure / 普通异常 uncertain / JsonValue equality / 防御快照 / post-commit cleanup | 沿用上一轮 `execution.py` / `runtime.py` / `snapshot.py` | NO |

## Locking review

active / evidence 各自独立短锁；done callback 先 publish evidence 再 remove active（无 visibility hole）；不持锁 commit / execute / provider call；无嵌套锁、无死锁路径。

## Late outcome classification（保持不变）

| future terminal | late evidence |
|---|---|
| Success / Failure（可 snapshot） | authoritative observation |
| ExecutionCancelled + requested | authoritative `Failure("execution cancelled")` |
| ExecutionCancelled + NOT requested | uncertain（defensive） |
| ordinary exception / invalid return | uncertain |
