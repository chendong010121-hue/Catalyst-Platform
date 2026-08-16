# INTERNAL AUDIT REPORT — RuntimeDomain Identity Closure

## 1. Audit conclusion
Implementer（Role A）引入 RuntimeDomain 后，切换到 Internal Auditor（Role B）从反方视角攻击。审查后未发现新的 P0/P1。RuntimeDomain 结构绑定 StateStore + ExecutionControlPlane，Runtime 不再接受独立 store/cp 参数。

## 2. Asset/version reviewed
- `agent_runtime` v1.7（ARCHITECTURE header）
- `agent_runtime/execution.py`（RuntimeDomain）、`runtime.py`、`capability_executor.py`、`errors.py`

## 3. Scope
RuntimeDomain identity / timeout-disabled bypass / explicit-wrong-cp bypass / alternate construction / lower-level composition guard / cross-runtime live+evidence+cancel+resume。

## 4. Invariants reviewed（source trace）
| invariant | enforcement | test | bypassable? |
|---|---|---|---|
| I1 Domain Identity | `Runtime.__init__` 只收 domain | DI-1/DI-5/DI-6/DI-7 | NO |
| I2 Active Visibility | domain 共享 active | DI-2/DI-4 | NO |
| I3 Late Evidence Visibility | domain 共享 evidence | DI-3/AU-7 | NO |
| I4 No Safety Island | timeout executor 无 cp → error | AU-2 | NO |
| I5 Timeout-independent Safety | 同 domain 共享 cp | DI-2/DI-3/AU-3 | NO |
| I6 Wrong Identity Fails Closed | 无独立配对 API + 下层 guard | DI-5/DI-6/AU-2 | NO |
| I7 Owner-only Writes | callback 只写 registry/evidence | 上一轮 L11/T20 | NO |
| I8 Evidence Semantics | 沿用 | 上一轮 CP-EI + L 系列 | NO |

## 5. Source-level findings
无 P0/P1。锁审计：active/evidence 独立短锁，无嵌套，无持锁 commit/execute。done callback 先 publish evidence 再 remove active（无 visibility hole）。

## 6. Deterministic adversarial tests
`test_runtime_domain_identity.py` 16/16（DI-1..DI-8 + AU-1..AU-8）。另 `test_control_plane_evidence_integrity.py` 19/19（B1 已按 domain contract 更新）。

## 7. Auditor-created new tests（>=8，非 DI 逐字复制）
AU-1..AU-8（两个 domain distinct cp / lower-level guard / timeout-disabled cancel / reconcile 后 no-pending / cp object identity / lower-level 显式 cp ok / runtime 经 domain 见 evidence / domain 绑定单一 store）。

## 8. Cross-runtime tests
DI-2/DI-3/DI-4/DI-8（同 domain 的 timeout-enabled A + timeout-disabled B：live guard、late evidence、cancel、resume safety）。

## 9. Failure injection
lower-level timeout 无 cp（AU-2）、commit failure evidence 保留（上一轮 F2）、submit failure（L10）、late ordinary exception（L6）。

## 10. Ownership / type / identity
AU-1（两个 domain distinct cp）、AU-5（cp object identity）、DI-5/DI-6/DI-7（无独立 store/cp 配对）。

## 11. Full regression results
22 模块全部 PASS（`audit_artifacts/post_fix_full_regression.txt`）。compileall OK。

## 12. Stress results
500 iterations，0 failures（cross-runtime reconcile during timeout uncertainty / late evidence / cancel / resume safety / evidence lookup），`audit_artifacts/stress_output.txt`。

## 13. Documentation consistency
`ARCHITECTURE.md` v1.7 + RuntimeDomain 组合段；§8 Non-goals 移除已实现的 timeout/cancellation；Known Debt 的 late-result 文案改为"记录为 late evidence（不 auto-settle）"。

## 14. Remaining debt（P2）
- thread 无法强杀；non-cooperative worker 可能持续占用 worker slot
- control plane / late evidence 不 durable，crash 后丢失
- 无 process isolation / 分布式取消 / 分布式 lease / CAS
- 无 automatic late-result reconciliation
- 同一 StateStore 只应创建一个 RuntimeDomain 并由 host 共享（host composition rule；runtime API 已结构上禁止独立 store/cp 配对）
- 既有 Known Debt（failed model-attempt usage ledger / native State omission / 无生产 durable Store / reconciliation Observation 复制 / snapshot-first）

## 15. Release gate
```
RuntimeDomain structural identity              PASS
Timeout-disabled bypass                        PASS
Explicit wrong-control-plane bypass            PASS
Alternate constructor bypass                   PASS
Cross-runtime live guard                       PASS
Cross-runtime late evidence                    PASS
Cross-runtime cancel                           PASS
Cross-runtime resume safety                    PASS
Lower-level composition contract               PASS

Known previous regressions                      PASS (22 modules)
Deterministic interleavings                     PASS
>=500 stress iterations                        PASS (500, 0 failures)
Auditor-created >=8 adversarial tests           PASS (AU-1..AU-8)
Documentation consistency                      PASS
Audit evidence package complete                PASS

P0 findings remaining                          0
P1 findings remaining                          0
Known P2 debt                                  documented

Internal verdict:
READY FOR EXTERNAL AUDIT
```
