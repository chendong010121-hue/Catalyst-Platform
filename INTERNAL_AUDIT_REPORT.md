# INTERNAL AUDIT REPORT — RuntimeDomain Uniqueness Final Closure

## 1. Audit conclusion
Implementer（Role A）把 uniqueness authority 移到 persistence namespace 边界（`RuntimeDomainBindable.claim_runtime_domain`）后，切换到 Internal Auditor（Role B）攻击。未发现新的 P0/P1。同一 StateStore 的第二个独立 RuntimeDomain（默认/显式/等价 CP 均）在 claim 处 fail closed。

## 2. Asset/version reviewed
`agent_runtime` v1.8（ARCHITECTURE header）：`execution.py`（RuntimeDomain / RuntimeDomainBindable）、`runtime.py`、`capability_executor.py`、`errors.py`、`fakes.py` + 全部 test/smoke。

## 3. Scope
RuntimeDomain uniqueness / second-domain rejection / explicit-wrong-cp / equivalent-but-distinct-cp / concurrent claim / timeout-disabled cross-runtime / duplicate-side-effect closure / failed-claim side-effect-free。

## 4. Invariants reviewed
| invariant | enforcement | test | bypassable? |
|---|---|---|---|
| I-UNIQUE-DOMAIN | store 边界的 claim（第二 claim → RuntimeDomainConflictError） | UD-1/2/3, UD-CONCURRENT | NO |
| I2 Active Visibility | 共享 cp.active | UD-5/7, DI-2/4 | NO |
| I3 Late Evidence Visibility | 共享 cp.evidence | UD-6, DI-3 | NO |
| I4 No Safety Island | 唯一 claim + 下层 executor guard | AU-2 | NO |
| I5 Timeout-independent Safety | 同 domain 共享 cp | UD-5/6/8 | NO |
| I6 Wrong Identity Fails Closed | 无独立配对 API + claim 冲突 | DI-5/6, UD-1/2/3 | NO |
| I7 Owner-only Writes | callback 只写 registry/evidence | 上一轮 L11/T20 | NO |
| I8 Evidence Semantics | 沿用 | 上一轮 CP-EI + L 系列 | NO |

## 5. Source-level findings
无 P0/P1。claim 线程安全（实例锁 + 类级双检懒 init）；claim 是 process-local monotonic metadata（无 release/close，避免 release 竞态）；不写 SessionSnapshot / 不 agent-visible / 不 durable。done callback 仍先 publish evidence 再 remove active。

## 6. Deterministic adversarial tests
`test_runtime_domain_uniqueness.py` 11/11（UD-1..UD-10 + UD-CONCURRENT）。`test_runtime_domain_identity.py` 16/16（DI/AU，AU-1 已按 uniqueness 更新）。

## 7. Auditor-created new tests（>=8）
UD-1/2/3（second-domain + explicit-wrong-cp + equivalent-cp）、UD-9/10（failed claim 不改 first domain / 不改 session data）、UD-CONCURRENT（并发 exactly one wins）、AU-1（更新）、以及既有 DI/AU 的 identity-mismatch 攻击矩阵。

## 8. Cross-runtime tests
UD-5/6/7/8（timeout-disabled B 见 live worker / late evidence / cancel / resume 防重复副作用）。

## 9. Failure injection
lower-level timeout 无 cp（AU-2）、commit failure evidence 保留（F2）、failed second claim 无副作用（UD-9/10）。

## 10. Ownership / type / identity
UD-3（equivalent-but-distinct cp 仍拒）、UD-9（first domain claim 不被覆盖）、DI-5/6（无独立 store+cp 配对）。

## 11. Full regression
23 模块全部 PASS（`audit_artifacts/post_fix_full_regression.txt`）。compileall OK。

## 12. Stress
500 iterations，0 failures（second-domain rejection + cross-runtime reconcile/cancel/resume/evidence），`audit_artifacts/stress_output.txt`。

## 13. Documentation consistency
`ARCHITECTURE.md` v1.8（I-UNIQUE-DOMAIN 描述：第二个 domain fail closed，非"host must remember"）；IMPLEMENTATION_NOTES 含 uniqueness authority 语义与 locking review。

## 14. Remaining debt（P2）
- thread 无法强杀；non-cooperative worker 可能持续占用 worker slot
- control plane / late evidence / domain claim 不 durable，crash 后丢失（domain claim 无 release，monotonic）
- 无 process isolation / 分布式取消 / 分布式 lease / CAS
- 无 automatic late-result reconciliation
- 既有 Known Debt（failed model-attempt usage ledger / native State omission / 无生产 durable Store / reconciliation Observation 复制 / snapshot-first）

## 15. Release gate（本地）
```
Runtime accepts RuntimeDomain only                     PASS
Persistence namespace owns unique domain claim         PASS
Second RuntimeDomain over same namespace               REJECTED
Second explicit CP over same namespace                 REJECTED
Concurrent second-domain creation                      EXACTLY ONE WINS
Timeout-disabled cross-runtime live guard              PASS
Cross-runtime late evidence                            PASS
Cross-runtime cancel                                   PASS
Cross-runtime resume duplicate-side-effect prevention  PASS
Lower-level timeout composition guard                  PASS

Previous cancellation/timeout regressions              PASS
All historical regression modules                     PASS (23)
Deterministic interleavings                            PASS
>=500 stress iterations                                PASS (500, 0 failures)
Fresh auditor >=8 new attacks                          PASS
P0 remaining                                           0
P1 remaining                                           0
Documentation consistency                              PASS
GitHub evidence claims truthful                        N/A（working dir 非 git repo）
User push approval obtained                            PENDING（见 HANDOFF）

Internal verdict:
READY FOR USER PUSH APPROVAL
```
