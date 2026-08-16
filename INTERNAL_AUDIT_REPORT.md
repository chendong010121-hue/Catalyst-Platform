# INTERNAL AUDIT REPORT — ExecutionCancelled Provenance Race Closure

> Implementer（Role A）完成 provenance race 修复后，切换到 Internal Auditor（Role B）做 fresh 攻击。
> 审计问题（Spec §15）：

> **Can any supported same-Runtime ordering convert an unproven/spurious `ExecutionCancelled` into authoritative cancellation merely because a cancellation request exists later?**

## 结论

**P0 = 0 / P1 = 0（supported model）。** 答案：**NO**。

## 修复范围

`agent_runtime/errors.py`（`ExecutionCancelled` 携带 marker）、`agent_runtime/execution.py`（`CancellationToken`/`CancellationSource` marker + runner `is_proven_cancellation` 校验，immediate 与 late 两条路径）。新增 `examples/test_execution_cancelled_provenance.py`（PRV-1..7）。

## 关键攻击尝试（均 fail-closed）

| 攻击 | 期望 | 结果 |
|---|---|---|
| raw `ExecutionCancelled()`（无 marker），无 request | `CapabilityContractError` → unresolved | PASS（PRV-1） |
| exception-before-request / observation-after-request（确定性 race） | `CapabilityContractError` → unresolved（不结算） | PASS（PRV-2） |
| foreign marker | unproven → `CapabilityContractError` | PASS（PRV-5） |
| late callback raw spurious（timeout 后 source 已 request） | uncertain evidence（非 authoritative cancel） | PASS（PRV-6） |
| late callback 本 token `raise_if_cancelled()` | authoritative `Failure("execution cancelled")` | PASS（PRV-7） |
| 本 token `raise_if_cancelled()`（manual + timeout） | 正常结算 `Failure("execution cancelled")` | PASS（PRV-3 / PRV-4） |

## Immediate vs late 语义 parity

| 路径 | proven | unproven |
|---|---|---|
| owner 立即观察 Future | `Failure("execution cancelled")` | `CapabilityContractError` → unresolved |
| done callback 晚观察 Future | authoritative evidence | uncertain evidence |

一致 ✓（PRV-6/PRV-7 vs PRV-1/PRV-2）。

## 验证数据

```text
DETERMINISTIC RACE (PRV-2): PASS（monkeypatch _futures_wait，Event 同步，非 sleep 证明）
FULL REGRESSION: 22 modules PASS（21 retained + 1 PRV），0 failures
500-STRESS: 500 iterations PASS（18.86s，0 intermittent failures）
     A timeout->late->reconcile: 200 iters
     B legitimate cancel:        150 iters
     C spurious unresolved:      150 iters
```

## 已知边界（非本轮引入）

- 跨 Runtime 同一 live Session 协调 = v0.x 不支持（非 P0）。
- `ExecutionCancelled` 的 marker 是 process-local、不 durable（crash 后 active token 丢失，durable PendingExecution 仍 fail-closed）。
- 外部审计其余 PARKED 发现（canonical domain authenticity / binding immutability / control-plane identity immutability）本轮未触及。

## 最终状态

```text
READY FOR USER GIT/PUSH APPROVAL
```
（不是 CLOSED / READY FOR MERGE / PRODUCTION READY）
