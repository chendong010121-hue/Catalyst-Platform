# TEST MANIFEST — ExecutionCancelled Provenance Race Closure

## Active regression（22 modules，全绿）

| Module | 覆盖 |
|---|---|
| `test_execution_cancelled_provenance.py` | **PRV-1..7** ExecutionCancelled provenance（raw spurious / post-hoc request race / legitimate token / timeout cooperative / foreign marker / late spurious / late legitimate） |
| `test_cancellation_timeout_mainline.py` | **CT-MA-1..12** mainline alignment 验收（normal / explicit cancel / cooperative cancel / non-cooperative timeout / same-Runtime live guard / late evidence / reconcile / task-TimeoutError 分类 / 纯 load-commit store / 无 domain 构造 / regression） |
| `test_cancellation_timeout.py` | T1..T22 cooperative cancellation / timeout / cancel-race / timeout-race / context 不 durable / worker 不写 store |
| `test_live_execution_quiescence.py` | Q1..Q12 registry 保留、cancel 定位、live guard、identity-safe remove、spurious cancel、timeout 分类 |
| `test_late_completion_control_plane.py` | L1..L11 late Success/Failure/异常 evidence、matching/矛盾 reconcile、live guard+cancel+quiesce、submit-failure、done-callback 不写 store |
| `test_control_plane_evidence_integrity.py` | A..G publication order、下层 executor guard、late-cancel parity、JsonValue equality、evidence isolation/cleanup、commit-failure |
| `test_execution_reconciliation.py` | pending/模型会话/reconcile/note/duplicate/legacy/native tool round-trip |
| `test_execution_lifecycle.py` | execution_id 分配、pending priority、prepare-before-side-effect、resume terminal |
| `test_execution_certainty_identity.py` | Capability Failure vs exception、execution identity、模型会话 identity |
| `test_durable_boundary.py` | durable fact 边界、mutation isolation |
| `test_global_contract_integrity.py` | 全局契约 / recovery integrity |
| `test_capability_executor.py` | resolve/validate/invoke/normalize、schema 校验 |
| `test_schema_integrity.py` | schema 完整性 |
| `test_hardening.py` | 生命周期加固 |
| `test_runtime.py` | Runtime 生命周期基础 |
| `test_llm_reasoner.py` | legacy_json reasoner |
| `test_native_tool_reasoner.py` | native_tools reasoner |
| `test_convergence.py` | 收敛 |
| `test_model_session_consistency.py` | 模型/会话一致性 |
| `test_provider_session_closure.py` | provider/session closure |
| `test_pre_provider_hardening.py` | pre-provider 加固 |
| `test_deepseek_provider.py` | DeepSeek provider |

## Retired（已从 active mainline 移除；历史保留在 GitHub PR #1 head `2d546c07`）

| Module | 原因 |
|---|---|
| `test_runtime_domain_identity.py`（DI/AU） | RuntimeDomain / multi-Runtime identity 断言不再是当前产品需求 |
| `test_runtime_domain_uniqueness.py`（UD-1..UD-10 + UD-CONCURRENT） | RuntimeDomain uniqueness 断言不再是当前产品需求 |

## 运行方式

```powershell
# 单模块
python -m examples.test_cancellation_timeout_mainline
# 全量（在 workspace 根）
foreach ($m in (Get-ChildItem examples\test_*.py | % BaseName)) { python -m examples.$m }
```

## 结果（本轮）

```text
DETERMINISTIC RACE (PRV-2): PASS
FULL REGRESSION: 22 modules PASS，0 failures
500-STRESS: 500 iterations PASS（18.86s）
```
