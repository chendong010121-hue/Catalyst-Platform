# HANDOFF — ExecutionCancelled Provenance Race Closure

> 阶段：窄修复外部审计发现的 `ExecutionCancelled temporal provenance race`（Triage: FIX NOW）。
> 依据：`EXECUTION_CANCELLED_PROVENANCE_RACE_CLOSURE_SPEC.md`（IMPLEMENTATION AUTHORIZED — LOCAL ONLY）。
> 前一阶段（mainline alignment）已发布 candidate `68baaa5`；本阶段在其上做本地修复，尚未 commit/push。

## 结果

`READY FOR USER GIT/PUSH APPROVAL`（本地实现 + 验证完成；尚未 commit/push）。

- WORKSPACE：`E:\试验场地\Agent Harness`
- BRANCH：`ds/cancellation-timeout-mainline-alignment`
- PRE-FIX SHA：`68baaa5beb5e362337f75da4ea385a78d512a291`
- 修复后本地工作树尚未 commit（新 SHA 待用户批准后生成）

## 问题与修复

旧 runner 在 catch `ExecutionCancelled` 时用 `source.is_cancel_requested()` 判断是否合法。若 worker 先 raise spurious `ExecutionCancelled`、owner 后 `request_cancel()`、再观察到 Future 异常，post-hoc request 会 retroactively 合法化该 spurious 异常 → 错误结算为 `Failure("execution cancelled")`。

**修复（provenance marker）**：

| 符号 | 变更 |
|---|---|
| `ExecutionCancelled` | 可携带 process-local `marker`（`__init__(marker=None)`） |
| `CancellationToken` | 持 `_marker`；`raise_if_cancelled()` 抛 `ExecutionCancelled(self._marker)` |
| `CancellationSource` | 持私有 `_marker = object()`；新增 `is_proven_cancellation(exc)`（marker 精确匹配） |
| `ThreadedExecutionRunner` | `_reject_spurious_cancelled(source, exc)` 与 late `_on_uncertain_done` 均改用 `is_proven_cancellation` |

语义：raw `ExecutionCancelled()` / foreign marker → unproven → `CapabilityContractError` → unresolved；本 token `raise_if_cancelled()` → proven → `Failure("execution cancelled")`。

## Change Manifest

```
FILES CHANGED (production):
  agent_runtime/errors.py     (ExecutionCancelled 携带 provenance marker)
  agent_runtime/execution.py  (token/source marker + runner provenance 校验，immediate + late 两条路径)

FILES ADDED:
  examples/test_execution_cancelled_provenance.py  (PRV-1..PRV-7)

FILES CHANGED (docs):
  ARCHITECTURE.md / HANDOFF.md / IMPLEMENTATION_NOTES.md / INTERNAL_AUDIT_REPORT.md / TEST_MANIFEST.md

PROVENANCE DESIGN: private per-execution marker；只认本 token raise_if_cancelled 产生的 ExecutionCancelled
DETERMINISTIC RACE TEST (PRV-2): PASS（monkeypatch execution._futures_wait，exception-before-request 仍 unresolved）
LATE CALLBACK PARITY (PRV-6/PRV-7): PASS（late spurious -> uncertain；late proven -> authoritative）
FULL REGRESSION: 22 modules PASS（21 retained + 1 PRV），0 failures
500-STRESS: 500 iterations PASS（18.86s，0 intermittent failures）
INTERNAL AUDIT: P0=0 / P1=0
```

## 尚未授权（STOP 边界）

```text
commit / push / merge / PR mutation / rebase / force-push
```

candidate `68baaa5` 仍为失败外审 target；本地修复后的新 SHA 需用户批准后 commit/push 生成。
