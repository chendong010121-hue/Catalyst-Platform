# HANDOFF — RuntimeDomain Identity Closure

> 阶段：把 StateStore 与 ExecutionControlPlane 提升为同一个 composition identity（`RuntimeDomain`），关闭 `One Safety Domain` P0。依据 `审核\FULL_ASSET_AUDIT_2026-08-16_RUNTIME_DOMAIN_IDENTITY.md` 与 `审核\RUNTIME_DOMAIN_IDENTITY_CLOSURE_EXECUTION_SPEC.md`。

---

## 状态

```text
Internal verdict:
READY FOR EXTERNAL AUDIT
```

（不自行写 CLOSED；最终阶段关闭由外部审核决定。）

---

## Implemented

| 项 | 内容 |
|---|---|
| RuntimeDomain | 新增 `RuntimeDomain(state_store, execution_control_plane=None)`，绑定持久化 namespace + execution safety namespace |
| Runtime 构造 | `Runtime(reasoner, capabilities, policy, domain, *, timeout_config=None)` —— 不再接受独立 `state_store`/`control_plane` |
| lower-level guard | `DefaultCapabilityExecutor` timeout enabled 且无 control plane → `RuntimeConfigurationError` |
| 不变式 I1–I8 | 见 IMPLEMENTATION_NOTES.md（全部源码级 enforced，无 caller-must-remember） |

## 关闭的 P0

```text
DI-RED-1（timeout-disabled B + same store → false reconcile）
DI-RED-2（explicit wrong cp → false reconcile）
```

修复前外部审计已稳定复现 `effects=2` 重复副作用；修复后：
- `Runtime(state_store=..., control_plane=...)` → TypeError（独立配对 API 不存在）
- timeout-disabled Runtime（同 domain）仍见 live worker / late evidence
- cross-runtime cancel 路由同一 execution

## Verified

```text
compileall                          PASS
post-fix full regression            PASS  22 modules（audit_artifacts/post_fix_full_regression.txt）
stress / interleaving               PASS  500 iters, 0 failures（audit_artifacts/stress_output.txt）
new domain identity tests           PASS  test_runtime_domain_identity 16/16（DI-1..DI-8 + AU-1..AU-8）
previous evidence integrity tests   PASS  test_control_plane_evidence_integrity 19/19
```

## Internal audit

详见 `INTERNAL_AUDIT_REPORT.md`：

```text
P0 = 0
P1 = 0
Internal verdict = READY FOR EXTERNAL AUDIT
```

## Remaining known debt（P2）

```text
thread 无法强杀；non-cooperative worker 可能持续占用 worker slot
control plane / late evidence 不 durable，crash 后丢失
无 process isolation / 分布式取消 / 分布式 lease / CAS
无 automatic late-result reconciliation（late result 仅作 evidence，不 auto-settle）
同一 StateStore 只应创建一个 RuntimeDomain 并由 host 共享（runtime API 已禁止独立 store/cp 配对）
既有 Known Debt：failed model-attempt usage ledger / native State omission /
无生产 durable Store / reconciliation Observation 复制 / snapshot-first
```

## 交付物

```text
1. 源码（agent_runtime/ + examples/）
2. ARCHITECTURE.md（v1.7）
3. HANDOFF.md（本文件）
4. IMPLEMENTATION_NOTES.md（I1–I8 + composition boundary + locking review）
5. INTERNAL_AUDIT_REPORT.md
6. TEST_MANIFEST.md
7. audit_artifacts/baseline_identity.txt
8. audit_artifacts/baseline_test_output.txt
9. audit_artifacts/pre_fix_reproductions.txt
10. audit_artifacts/post_fix_full_regression.txt
11. audit_artifacts/stress_output.txt
```
