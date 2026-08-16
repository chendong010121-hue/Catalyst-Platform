# IMPLEMENTATION NOTES — RuntimeDomain Uniqueness Final Closure

> 本轮把 uniqueness authority 放在 persistence namespace 边界：同一 StateStore 只允许一个 RuntimeDomain identity（→ 一个 ExecutionControlPlane）。

## Composition boundary decision（spec §4）

- A. RuntimeDomain identity = 一个 session namespace 的持久化 namespace（StateStore）+ execution safety namespace（ExecutionControlPlane）的绑定对象。
- B. Runtime **不再**接受独立的 `state_store` / `control_plane`；只能由 `domain` 构造。
- C. 所有 session 操作（create/run/resume/reconcile/cancel）都经由 domain 的 store + control plane。
- D. timeout-disabled Runtime 也必须由同一 domain 构造，因此访问同一 control plane。
- E. 下层 `DefaultCapabilityExecutor` timeout enabled 且无 control plane → `RuntimeConfigurationError`。

## Uniqueness authority（本轮新增）

`RuntimeDomain.__init__` 调用 `state_store.claim_runtime_domain(self)`：

```text
no current claim + identity A   → claim succeeds
existing claim A + identity A   → idempotent（same object）
existing claim A + identity B   → RuntimeDomainConflictError（fail closed）
```

- claim 是 process-local、thread-safe、monotonic（本 closure 无 release/close，避免 release 竞态）。
- claim 是 execution-safety composition metadata：不写 SessionSnapshot、不 agent-visible、不 durable。
- StateStore 需实现 `RuntimeDomainBindable`（lazy-init，无需 super().__init__）；不支持则 `RuntimeConfigurationError`。

## Invariants

| # | invariant | enforcement | bypassable? |
|---|---|---|---|
| I-UNIQUE-DOMAIN | 同一 persistence namespace → 恰好一个 RuntimeDomain identity → 一个 ExecutionControlPlane | `RuntimeDomainBindable.claim_runtime_domain`（store 边界）+ `Runtime` 只收 domain | NO（第二个独立 claim 在构造时抛 RuntimeDomainConflictError） |
| I2 Active Visibility | live execution → domain 内每个 Runtime 见同一 active fact | 共享 `ExecutionControlPlane.active` | NO |
| I3 Late Evidence Visibility | authoritative late result → 同一 evidence | 共享 `ExecutionControlPlane.evidence` | NO |
| I4 No Safety Island | 不能静默创建 private registry/evidence/cp | 唯一 domain claim + 下层 executor guard | NO |
| I5 Timeout-independent Safety | timeout-disabled Runtime 仍遵守 guard | 同 domain 共享 cp | NO |
| I6 Wrong Identity Fails Closed | store/cp 不匹配 → 失败 | 无独立配对 API + claim 冲突 | NO |
| I7 Owner-only Durable Writes | 不引入 background settle | callback 只写 registry/evidence | NO |
| I8 Evidence Semantics Preserved | 沿用 | 上一轮 | NO |

## Locking review

`RuntimeDomainBindable` 用实例级 lock（lazy init 用类级 `_init_lock` 双检）。active/evidence 各自独立短锁；done callback 先 publish evidence 再 remove active；无嵌套锁、无持锁 commit/execute。


## Late outcome classification（保持不变）

| future terminal | late evidence |
|---|---|
| Success / Failure（可 snapshot） | authoritative observation |
| ExecutionCancelled + requested | authoritative `Failure("execution cancelled")` |
| ExecutionCancelled + NOT requested | uncertain（defensive） |
| ordinary exception / invalid return | uncertain |
