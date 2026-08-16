# HANDOFF — RuntimeDomain Uniqueness Final Closure

> 阶段：把 uniqueness authority 放到 persistence namespace 边界，关闭 `One Persistence Namespace → One RuntimeDomain → One Execution Safety Domain` P0。依据 `审核\RUNTIME_DOMAIN_UNIQUENESS_FINAL_CLOSURE.md`。

---

## 状态

```text
Internal verdict:
READY FOR USER PUSH APPROVAL
```

（本地实现 + 验证完成；尚未 commit/push。工作目录 `E:\试验场地\Agent Hardness` **不是 git 仓库**，故无法从此处直接 push。若需 push 到 `ds/runtime-domain-identity-closure`，需用户提供/确认 git 目标与授权。）

---

## Implemented

| 项 | 内容 |
|---|---|
| 唯一性 authority | `RuntimeDomain.__init__` 调用 `state_store.claim_runtime_domain(self)`；同一 namespace 的第二个独立 domain → `RuntimeDomainConflictError` |
| Store 边界 | 新增 `RuntimeDomainBindable`（process-local、thread-safe、lazy init、monotonic，无 release） |
| 显式 CP 不得绕过 | `RuntimeDomain(S, cp1)` + `RuntimeDomain(S, cp2)`（cp1 is not cp2，即使等价）→ 第二个 fail closed |
| 下层 guard 保持 | `DefaultCapabilityExecutor` timeout + 无 cp → `RuntimeConfigurationError` |

## 关闭的 P0

```text
d1 = RuntimeDomain(S)
d2 = RuntimeDomain(S)   # 旧：d1.cp is not d2.cp；新：RuntimeDomainConflictError
```

第二个独立 domain 在构造处 fail closed，杜绝"同一 persistence namespace → 两个 ExecutionControlPlane → 两个互相不可见的 safety island"。

## Verified（本地）

```text
compileall                          PASS
post-fix full regression            PASS  23 modules（audit_artifacts/post_fix_full_regression.txt）
stress / interleaving               PASS  500 iters, 0 failures（audit_artifacts/stress_output.txt）
uniqueness tests                    PASS  test_runtime_domain_uniqueness 11/11（UD-1..UD-10 + UD-CONCURRENT）
domain identity tests               PASS  test_runtime_domain_identity 16/16（DI/AU，AU-1 更新）
```

## Internal audit

详见 `INTERNAL_AUDIT_REPORT.md`：P0=0, P1=0，本地 verdict `READY FOR USER PUSH APPROVAL`。

## Remaining known debt（P2）

```text
thread 无法强杀；non-cooperative worker 可能持续占用 worker slot
control plane / late evidence / domain claim 不 durable，crash 后丢失（claim monotonic，无 release）
无 process isolation / 分布式取消 / 分布式 lease / CAS
无 automatic late-result reconciliation
既有 Known Debt：failed model-attempt usage ledger / native State omission /
无生产 durable Store / reconciliation Observation 复制 / snapshot-first
```

## 待办（需用户确认）

工作目录非 git 仓库；按 `RUNTIME_DOMAIN_UNIQUENESS_FINAL_CLOSURE.md` §23 的绑定工作流要求，commit/push 前必须由用户确认。请用户提供目标 GitHub 仓库/分支（`ds/runtime-domain-identity-closure`）与明确的 commit/push 授权；在此之前**不 commit、不 push、不 merge**。

## 交付物（本地）

```text
1. 源码（agent_runtime/ + examples/）
2. ARCHITECTURE.md（v1.8）
3. HANDOFF.md（本文件）
4. IMPLEMENTATION_NOTES.md
5. INTERNAL_AUDIT_REPORT.md
6. TEST_MANIFEST.md
7. audit_artifacts/baseline_identity.txt
8. audit_artifacts/baseline_test_output.txt
9. audit_artifacts/pre_fix_reproductions.txt
10. audit_artifacts/post_fix_full_regression.txt
11. audit_artifacts/stress_output.txt
```
