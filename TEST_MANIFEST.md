# TEST MANIFEST — RuntimeDomain Identity Closure

## DI-1..DI-8（`examples/test_runtime_domain_identity.py`）

| ID | threat / invariant | old failure | fixed | deterministic |
|---|---|---|---|---|
| DI-1 | domain identity（I1） | store+cp 独立参数 | 同一 domain → 同一 store+cp | YES |
| DI-2 | timeout-disabled bypass live guard（I5） | B private cp → false reconcile | B 同 domain 见 live → ExecutionStillLiveError | YES |
| DI-3 | timeout-disabled sees late evidence（I3） | B 不见 evidence | B 同 domain 见 evidence → reject | YES |
| DI-4 | cross-runtime cancel（I2） | cancel 不路由 | B.cancel → 同一 execution_id | YES |
| DI-5 | 独立 store+cp pair（I6） | Runtime(state_store, control_plane) 合法 | → TypeError | YES |
| DI-6 | alternate constructor bypass（I6） | Runtime(state_store) 合法 | → TypeError | YES |
| DI-7 | store/cp 恰为 domain 值（I1） | 可独立 re-derive | Runtime 直接使用 domain 值 | YES |
| DI-8 | live worker → 无法第二次执行（I5） | false reconcile → 第二次执行 | live guard + pending gate → calls==1 | YES |

## AU-1..AU-8（Internal Auditor 自创）

| ID | threat | verdict |
|---|---|---|
| AU-1 | 两个 domain 有 distinct cp（host 必须共享单 domain） | PASS |
| AU-2 | lower-level executor timeout 无 cp → error（I4） | PASS |
| AU-3 | timeout-disabled Runtime 仍可 cancel（I5） | PASS |
| AU-4 | reconcile 后 evidence 清理，二次 reconcile 是 no-pending 非 stale | PASS |
| AU-5 | cp identity 是 object identity（值等价 ≠ 同 domain） | PASS |
| AU-6 | lower-level executor 显式 cp 正常 | PASS |
| AU-7 | Runtime 经 domain 看到 evidence（I3） | PASS |
| AU-8 | domain 绑定单一 store 对象（I1） | PASS |

## 上一轮（Control Plane Publication & Evidence Integrity）测试保持

`test_control_plane_evidence_integrity.py`（19，B1 已按 domain contract 更新）、
`test_late_completion_control_plane.py`、`test_live_execution_quiescence.py`、`test_cancellation_timeout.py` 等。
