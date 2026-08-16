# HANDOFF —— Execution Certainty & Session Identity Closure

> 最后一轮与执行结果确定性、Session 身份、native tool fact 一致性、恢复预算安全直接相关的 closure。依据 `审计\FULL_ASSET_AUDIT_2026-08-16_EXECUTION_CERTAINTY.md` 与 `审计\EXECUTION_CERTAINTY_SESSION_IDENTITY_CLOSURE.md`。修复被 adversarial reproduction 证明会导致重复真实副作用、跨 Session 执行、durable model fact 自相矛盾或 Policy safety budget 绕过的问题。完成后停止。

---

## 1. 一句话结论

**Capability 抛异常代表"结果未知"（不是"确定失败"）；Session 必须证明自己就是调用方请求的 Session；Native tool facts 必须与真正执行的 Action 完全一致；任何恢复出来的 budget fact 都必须重新通过 canonical invariant。**

本轮**未**实现：timeout / cancellation / retry / idempotency / streaming / sandbox / approval / parallel tools / production DB / CAS / State projection / model-attempt ledger / configuration migration / automatic reconciliation。

---

## 2. Finding → Fix mapping

| 审计 finding | 文件 | 实际修复 | 测试 | 结果 |
|---|---|---|---|---|
| Capability exception 误判为 authoritative Failure | `capability_executor.py` + `errors.py` | `invoke` 抛异常 → `CapabilityExecutionError`（不再 `return Failure`）；新增错误类型 | E1 / 旧 `test_capability_executor.test_j` | PASS |
| 跨 Session 身份不一致 | `snapshot.py` + `core.py` + `runtime.py` | `validate_session_snapshot(snapshot, expected_session_id=...)`；所有 load 边界传 id | I1–I3 | PASS |
| Decision/native model fact 不一致 | `snapshot.py` + `core.py` | `json_value_equal` + `action_model_call_mismatch` + `decision_model_call_mismatch`；复用三处 | M1–M9 | PASS |
| recovered ModelUsage 绕过预算 | `snapshot.py` | `snapshot_model_usage` 重建 + `snapshot_model_call` 使用 | U1–U3 | PASS |
| Runtime.create 绕过 canonical commit | `runtime.py` | `create` validate-before-commit | C1–C3 | PASS |
| composition continuity 未文档化 | `ARCHITECTURE.md` | Known Debt 新增一条 | — | DOC |

---

## 3. Capability certainty matrix

| case | body runs? | settle? | clear pending? | agent-visible? |
|---|---|---|---|---|
| unknown capability | no | yes（known `Failure`） | yes | yes（Failure） |
| schema invalid | no | yes（known `Failure`） | yes | yes（Failure） |
| return `Success` | yes | yes | yes | yes（Success） |
| return `Failure` | yes | yes | yes | yes（Failure） |
| return invalid type | yes | no（`CapabilityContractError`） | no | no |
| return unsnapshotable | yes | no（`CapabilityContractError`） | no | no |
| raise exception | yes（副作用可能已发生） | no（`CapabilityExecutionError`） | no | no |

`CapabilityExecutionError` 只携带 `capability_id` + 安全摘要，不把完整 exception repr 变成 agent-visible Observation（避免泄漏路径/凭据）。

---

## 4. Side-effect-then-raise（E1）

```text
Capability body:
  side_effect += 1
  raise RuntimeError("connection dropped ...")

→ effects == 1
→ durable pending_execution != None
→ 无 settled StepRecord（history == ()）
→ Runtime 抛 CapabilityExecutionError
→ resume → UnresolvedExecutionError（Reasoner/Executor/Capability 不再次调用）
→ effects 仍 == 1
```

无 auto retry / auto reconcile；只能 operator/external verification → `Runtime.reconcile`。

---

## 5. Session identity（I）

```text
load("A") 返回 SessionSnapshot(session_id="B")
→ validate_session_snapshot(snapshot, expected_session_id="A")
→ SessionConsistencyError
→ Reasoner/Policy/Executor/Capability call_count == 0
```

覆盖：`Runtime.run`（I1）、`Core` 第二次 authoritative load（I2，Runtime preflight 通过后 Core 仍失败）、`Runtime.reconcile`（I3）。

---

## 6. Native fact consistency（M）

```text
Decision Act(add, {"a":1,"b":2})
ModelCallRecord.tool_calls = [name="sub", ...]
→ ReasonerContractError → Capability 不执行   (M1)

Decision add(1,2) / tool_call add(9,9)         → fail  (M2)
Decision add({"a": True}) / tool_call '{"a":1}' → fail（bool≠number）(M3)
one Act + two tool_calls                       → fail  (M4)
Complete + native tool_calls                   → fail  (M5)
exactly one matching native call               → pass  (M6)
legacy Act + empty tool_calls                  → pass  (M7)
pending.action=add / model_call tool=sub       → SessionConsistencyError  (M8)
settled decision=add / model_call tool=sub     → SessionConsistencyError  (M9)
```

`json_value_equal` 是 type-aware JSON equality（`True != 1`，递归 dict/list/scalar）。shared validator `decision_model_call_mismatch` / `action_model_call_mismatch` 复用于 Core ReasoningResult contract、settled StepRecord recovery、PendingExecution recovery。

---

## 7. ModelUsage recovery（U）

```text
usage = ModelUsage(10, 5)
object.__setattr__(usage, "input_tokens", -100)
放入 Session
→ validate_session_snapshot → SessionConsistencyError
→ TokenBudgetPolicy 永远看不到 negative total_tokens
```

`snapshot_model_usage` 重建 `ModelUsage(input_tokens, output_tokens)`，重新触发 non-negative int / 排除 bool invariant；`snapshot_model_call` 不再直接 `usage=model_call.usage`。

---

## 8. Runtime.create Raw Store（C）

```text
Runtime.create("not a Goal")         → SessionConsistencyError → RawStore.commits == 0  (C1)
Runtime.create(corrupt Goal.desc=123) → SessionConsistencyError → commits == 0         (C2)
Runtime.create(valid Goal)            → commit 恰好 1 次，返回 canonical snapshot      (C3)
```

`Runtime.create` 现在 `validate_session_snapshot(snapshot, expected_session_id=session_id)` 后才 `StateStore.commit`。

---

## 9. Architecture Gate（§40）

| 问题 | 答案 |
|---|---|
| Can a raised Capability exception become a settled Failure? | **NO** |
| Can a raised Capability exception clear PendingExecution? | **NO** |
| Can Reasoner automatically retry after uncertain Capability raise? | **NO** |
| Can explicit returned Failure still settle normally? | **YES** |
| Can load("A") return snapshot.session_id="B" and continue? | **NO** |
| Can Runtime.reconcile settle a different session than requested? | **NO** |
| Can native tool_call.name differ from Action.capability_id? | **NO** |
| Can native tool arguments differ from Action.parameters? | **NO** |
| Can one Act carry multiple native tool calls in v0.1? | **NO** |
| Can terminal Decision carry native tool_calls? | **NO** |
| Can malformed pending native facts be reconciled? | **NO** |
| Can corrupt negative/bool ModelUsage reach TokenBudgetPolicy? | **NO** |
| Can Runtime.create commit an invalid/corrupt Goal on Raw Store? | **NO** |
| Is runtime-composition continuity explicitly documented as debt? | **YES** |

---

## 10. Regression（实际执行，全部通过）

```text
python -m compileall -q agent_runtime examples            → COMPILEALL OK

新：python -m examples.test_execution_certainty_identity → 22/22
   E1–E4（execution certainty）、I1–I3（session identity）、
   M1–M9（native fact consistency）、U1–U3（ModelUsage recovery）、
   C1–C3（Runtime.create canonical commit）

旧回归全部通过（16 个模块）：
   run_minimal_loop
   test_hardening(4)              test_runtime(8)
   test_llm_reasoner(10)          test_convergence(10)
   test_pre_provider_hardening(14) test_durable_boundary(4)
   test_deepseek_provider(12)     test_capability_executor(13)
   test_schema_integrity(6)       test_native_tool_reasoner(22)
   test_execution_lifecycle(17)   test_execution_reconciliation(17)
   test_global_contract_integrity(26)
   test_model_session_consistency(45)
   test_provider_session_closure(27)
```

按新语义调整的旧测试（非行为回归，反映"raise ≠ Failure"）：

- `test_capability_executor.test_j`：改为断言 `CapabilityExecutionError`。
- `test_execution_lifecycle.test_d`：改用 `ReturnsFailureCapability`（explicit Failure 仍 settle）。
- `test_hardening` / `test_runtime` / `test_convergence` / `test_pre_provider_hardening`：把 `invoke` 抛异常的 capability 改为 `return Failure(...)`，保留"known Failure settles"断言；raise→unresolved 由新 module 覆盖。
- `test_provider_session_closure.test_l2`：corruption vector 从 tool_calls 改为 corrupt ModelUsage（更贴合 commit-boundary 语义）。

---

## 11. Known debt（保持准确）

```text
failed model-attempt usage 不持久化（TokenBudgetPolicy 是 post-step budget，非完整 billing ledger）
native Reasoner 未消费 State projection
无生产 durable StateStore
single-writer only，无 CAS/versioning
reconciliation Observation 复制（只强制一致，未去重）
runtime composition compatibility 不持久化（resume 需语义兼容的 Runtime composition）
snapshot-first，非 event sourcing
```

---

## 12. 修改文件清单（Review Payload）

| 文件 | 层 | 修改内容 |
|---|---|---|
| `agent_runtime/errors.py` | Error | `CapabilityExecutionError` |
| `agent_runtime/capability_executor.py` | Executor | invoke 异常 → raise `CapabilityExecutionError`（不再 return Failure） |
| `agent_runtime/snapshot.py` | Durable | `json_value_equal` + `action_model_call_mismatch` + `decision_model_call_mismatch` + `snapshot_model_usage`；`validate_session_snapshot(expected_session_id=...)`；pending/settled native 一致性；identity 检查 |
| `agent_runtime/core.py` | Core | `_validate_reasoning_result` 加 native 一致性；每次 load 传 `expected_session_id` |
| `agent_runtime/runtime.py` | Runtime | run/resume/reconcile 传 `expected_session_id`；`create` validate-before-commit |
| `examples/test_execution_certainty_identity.py` | Test | 新增 22 个 adversarial tests |
| `examples/test_capability_executor.py` / `test_execution_lifecycle.py` / `test_hardening.py` / `test_runtime.py` / `test_convergence.py` / `test_pre_provider_hardening.py` / `test_provider_session_closure.py` | Test | 按新执行确定性语义调整 |
| `ARCHITECTURE.md` | Doc | v1.2；execution certainty；session identity；native provenance；Known Debt |

`providers/deepseek.py` / `policies.py` / `llm_reasoner.py` / `contracts/values.py` / `contracts/interfaces.py` 本轮**无 semantic changes**。

---

## 13. 下一步

本轮通过后，**直接进入 Cooperative Cancellation & Timeout v0.1**。执行确定性语义（`exception != proof of non-execution`，pending unresolved）正是 Timeout/Cancellation 的基础。届时注意：store 无 CAS/versioning，不得引入"两个 session writer"或"background settlement writer 与 Runtime.resume/reconcile 竞争"。本轮**不提前实现**。

按停止原则，除非新的可复现问题能造成"非预期/重复真实副作用、跨 Session 执行、durable fact corruption、recovery safety bypass、Policy safety bypass"，否则不再开启新的泛化 hardening 轮次。
