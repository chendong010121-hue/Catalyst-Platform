# HANDOFF — Platform Standard Core v0.1（Merge 前 Audit Repair）

> 阶段：Platform Standard Core v0.1 **Merge 前 Audit Repair**（repair, not expansion）。
> 依据：`新任务/ARCHITECTURE_FINAL_v2.2.md` + `新任务/PLATFORM_STANDARD_CORE_V0.1_FINAL.md` + 本轮 Audit Repair Plan。
> PR：#4，branch `ds/platform-standard-core-v0.1`，base `main @ 9b88c26…`。
> Previous reviewed head：`328c40b6ef2dc702e20b02570b500d51e7904375`。
> 状态：修复完成（LOCAL + CI VERIFIED），**PR #4 UNDER EXTERNAL REVIEW / NOT YET ACCEPTED INTO MAIN**。未 merge。

---

## Fixed（本轮 audit repair 修复项）

```text
1. CI coverage      ci.yml + audit-ref.yml 现在 compile agent_runtime+platform_standard+examples+tests，
                    并真实执行 tests/test_platform_standard_core.py（PS-1..14 + AR-1..7），
                    证据日志：tested_sha / tested_tree / compile.log / regression.log / platform_standard.log
2. version routing  RuntimeAdapter 内 (capability_id, capability_version) -> 唯一 internal Runtime key
                    （adapter-local wrapper），同 ID 多版本不再互相覆盖；V1/V2 路由回归 PASS
3. artifact mapping generic RuntimeAdapter 不再硬编码 artifact 语义（无 "report"）；
                    per-capability artifact mapper 位于 binding/reference 层（compose_report mapper 产生 report ArtifactRef）
4. dependency 方向  platform_standard/** 不再 import examples.*；Runtime composition 通过 runtime_factory 注入
                    （reference factory 在 examples/platform_standard_reference.py 选择 AllowAllPolicy/InMemoryStateStore）
5. validator 严格度  extensions 必须为 map（None 拒绝）；context.extensions 必须存在且为 map；
                    NaN / Infinity / -Infinity 拒绝为非 JSON number
6. 状态措辞        ARCHITECTURE (v2.2) / PLATFORM_STANDARD_CORE_V0.1 改为
                    IMPLEMENTED / LOCAL+CI VERIFIED / PR #4 UNDER EXTERNAL REVIEW / NOT YET ACCEPTED INTO MAIN
```

## Preserved（未破坏）

```text
AgentCore                       ZERO DIFF
Runtime                         ZERO DIFF
CapabilityExecutor              ZERO DIFF
Runtime execution-certainty 语义（exception != non-execution；timeout != failure；
                                unresolved 永不自动重放；reconciliation 显式）
Core object set（envelope / extension / capability / invocation / result / artifact_ref / trace_event）
Extension First 原则
compose_report vertical slice    PASS
count_words second-capability    PASS（零 Core/Runtime/AgentCore 改动）
```

## Not implemented（明确未实现）

```text
Identity / IAM / RBAC / ABAC / Tenant / Delegation
Policy Engine / Approval System
Enterprise Profile / Domain Package / Ontology
Workflow Engine / Control Plane / MCP / A2A / OpenTelemetry
Multi-Agent / Plugin Framework / Production Registry Service
新 Runtime / 新 Agent Loop / AgentCore redesign
```

## 测试结果

```text
PLATFORM STANDARD: PS-1..PS-14  14/14 PASS
AUDIT REPAIR:      AR-1..AR-7   7/7  PASS
  AR-1 CI 覆盖 Platform Standard          AR-2 同 ID 多版本路由
  AR-3 generic Adapter 无 artifact 语义   AR-4 无 examples.* 依赖
  AR-5 extensions=None 拒绝               AR-6 context 无有效 extensions 拒绝
  AR-7 NaN/Infinity 拒绝
vertical slice (compose_report):  PASS（Standard Result + ArtifactRef + trace）
second capability (count_words):  PASS（零 artifact 路径）
same-ID multi-version routing:    PASS（V1 -> V1 实现，V2 -> V2 实现）
EXISTING REGRESSION (examples):   22/22 PASS
agent_runtime/** diff:            零
```

## 发现的架构问题 / 备注

1. `runtime_factory` 为必填：generic RuntimeAdapter 不再决定 Policy/StateStore（依赖方向 examples → platform_standard → agent_runtime）。
2. version routing 的 internal key（`cap_<sha1>`）是 adapter-local 实现细节，不是新的 Standard object；wrapper 仅桥接 (id, version) → Runtime key。
3. RuntimeAdapter 非线程安全（复用单一 Runtime + DirectedReasoner.pending_action），v0.1 参考实现可接受。

## 下一阶段建议

```text
1. 等 PR #4 外部 re-audit 结果；
2. 若 PASS，再决定 merge 到 main（需用户批准）；
3. 后续候选（需独立架构决策）：Extension 首个真实语义 / 更多 vertical slice 路径 / CI 对 PS 的 evidence artifact 消费。
```

---

# STOP —— 未 merge，等待外部 re-audit
