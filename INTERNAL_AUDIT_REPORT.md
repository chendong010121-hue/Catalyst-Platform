# INTERNAL AUDIT REPORT — Cooperative Cancellation & Timeout v0.1 Mainline Alignment

> Implementer（Role A）完成 mainline realignment 后，切换到 Internal Auditor（Role B）做 fresh 攻击。
> 审计问题（本轮的真正问题，不再是「能否再造一个 RuntimeDomain bypass」）：

> **Did the realignment preserve all approved Cancellation/Timeout safety semantics while successfully removing the unsupported RuntimeDomain expansion?**

## 范围

`agent_runtime` v1.9（ARCHITECTURE header）：`execution.py`、`runtime.py`、`capability_executor.py`、`errors.py`、`contracts/interfaces.py`、`core.py`、`snapshot.py`、`fakes.py` + 全部 retained test + 新增 CT-MA。

## 结论

**P0 = 0 / P1 = 0（supported model）**。未发现真实支持路径上的 safety regression。

## 审计类别逐项

| # | 类别 | 结论 |
|---|---|---|
| 1 | same-Runtime cancellation ownership | PASS — Runtime-local plane；cancel/reconcile/executor 同一份 active/evidence |
| 2 | timeout uncertainty | PASS — deadline/request ≠ Failure；未 quiesce → pending unresolved |
| 3 | worker lifetime | PASS — active entry 在 future.done() 后才移除；timeout-uncertain 保留 |
| 4 | late evidence | PASS — publish-before-remove；authoritative/uncertain 分类正确 |
| 5 | reconciliation correctness | PASS — live guard + late-evidence guard + post-commit cleanup |
| 6 | durable owner-only writes | PASS — worker/done-callback 从不写 Session（L11） |
| 7 | StateStore contract purity | PASS — 纯 load/commit；CT-MA-10 无 claim/get/mixin |
| 8 | RuntimeDomain dependency removal | PASS — 全树 grep 无 RuntimeDomain/Bindable/claim/ConflictError |
| 9 | regression of pre-cancellation invariants | PASS — 20 个 retained 模块全绿 |
| 10 | documentation consistency | PASS — 5 份文档已对齐；无 stale cross-Runtime / domain 描述 |

## 关键攻击尝试（均 fail-closed）

| 攻击 | 期望 | 结果 |
|---|---|---|
| 无 state_store 构造 Runtime | TypeError | PASS（B1） |
| timeout-enabled 下层 executor 无 control_plane | RuntimeConfigurationError | PASS（B1） |
| timeout uncertain 后同 Runtime reconcile | ExecutionStillLiveError | PASS（B3/CT-MA-5） |
| late Success(42) 后 ConfirmedNotExecuted | ReconciliationError | PASS（L2/CT-MA-6） |
| late Success(42) 后 ConfirmedExecuted(Success(99)) | ReconciliationError | PASS（L3） |
| commit 失败后 evidence 是否保留 | 保留（不提前清理） | PASS（F2） |
| spurious ExecutionCancelled | CapabilityContractError → unresolved | PASS（Q8） |
| task TimeoutError | CapabilityExecutionError（非 harness timeout） | PASS（Q10/CT-MA-9） |
| bool/int Observation 混淆 | json_value_equal 区分 | PASS（D/D2/G5） |
| 纯 load/commit store | 正常构造运行 | PASS（CT-MA-10） |
| Runtime 构造函数要求 domain | 无 domain 参数 | PASS（CT-MA-11） |

## 验证数据

```text
FULL REGRESSION: 21 modules PASS（20 retained + 1 CT-MA），0 failures
CT-MA ACCEPTANCE: CT-MA-1..12 12/12 PASS
500-STRESS: 500 iterations PASS（27.22s，0 intermittent failures）
     scenario A timeout->late->reconcile: 300 iters
     scenario B cooperative cancel:       200 iters
```

## 已知边界（非本轮引入，记录为 Known Debt / out-of-scope）

- 跨 Runtime 同一 live Session 协调 = v0.x **不支持**（明确 unsupported，非 P0）。
- `ExecutionTimeoutConfig` 不持久化，resume 用当前 Runtime config（composition continuity Known Debt）。
- control plane / late evidence 不 durable，crash 后丢失（durable PendingExecution 仍 fail-closed）。
- 外部审计三条新发现（canonical domain authenticity / binding immutability / control-plane identity immutability）仍 **PARKED**，本轮未授权实现。

## 最终状态

```text
READY FOR USER GIT/PUSH APPROVAL
```
（不是 CLOSED / READY FOR MERGE / PRODUCTION READY）
