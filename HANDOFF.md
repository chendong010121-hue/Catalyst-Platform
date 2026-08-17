# HANDOFF — Platform Standard Core v0.1 — Accepted Baseline Closure

> 阶段：Platform Standard Core v0.1（含 Merge 前 Audit Repair）—— 已 merge 进 main。
> 依据：`新任务/ARCHITECTURE_FINAL_v2.2.md` + `新任务/PLATFORM_STANDARD_CORE_V0.1_FINAL.md` + Audit Repair Plan。
> PR：#4，branch `ds/platform-standard-core-v0.1`。
> Previous reviewed head：`328c40b6ef2dc702e20b02570b500d51e7904375`；Repair head：`dd2424f283641e77f3a78b34a24427d5568eca7b`。
> 状态：**IMPLEMENTED / VERIFIED / MERGED / ACCEPTED / CLOSED**。
> 记录：old baseline `9b88c26…`；merge/new accepted main SHA `08932e1555743b5b5ff86639091ad3634654308c`；main tree `150ee3b2…`；post-merge CI run `32029892510`（success）。

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

## 下一阶段（PREPARED / NOT YET IMPLEMENTED）

```text
Enterprise Extension Pilot v0.1
PREPARED / NOT YET IMPLEMENTED
```

- 目的：验证 Stable Platform Core 能否承载 Adjustable Enterprise Semantics（不扩大 Core）。
- 首个企业语义：`enterprise.identity v0.1`（organization_id / user_id / optional project_id），经现有 Extension Contract 传入 Invocation，在 reference execution + trace attribution 中保持可见。
- 规则：Extension First. Core Promotion Later.；`agent_runtime/**` ZERO DIFF；不得新增 Core 字段。
- 前置：本 Documentation Closure 进入 accepted main 后，另行授权才可启动（创建 Stage branch / 写 Stage Spec / 实现）。

---

# CLOSED —— Platform Standard Core v0.1 已 ACCEPTED（main @ 08932e15…）

按 Merge Authorization：PR #4 MERGED、post-merge main CI PASS（compile / minimal loop / 22 regressions / PS-1..14 / AR-1..7 全 PASS）后，新 main 已声明为 ACCEPTED BASELINE。本阶段 CLOSED。

> 注意：ARCHITECTURE.md / HANDOFF.md 的本次状态更新为**未 commit 的本地修改**——按 Git Governance，独立 commit 需新的 publication approval，先报告后申请。

