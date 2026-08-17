# HANDOFF — Enterprise Extension Pilot v0.1

> 阶段：Enterprise Extension Pilot v0.1 —— 验证「Stable Platform Core + Adjustable Enterprise Semantics」。
> 依据：`ENTERPRISE_EXTENSION_PILOT_V0.1.md`（Stage Spec）+ `新任务/ARCHITECTURE_FINAL_v2.2.md`。
> Accepted baseline：`main @ a99629549f700a859e9393a0a46281ea4350b985`（tree `b50f09ab…`）。
> 状态：本地实现 + 验证完成（LOCAL VERIFIED），PR 已开，等待 External Audit。未 merge。

---

## 实现了什么

```text
enterprise_extensions/identity.py     enterprise.identity v0.1 语义层
  - parse_enterprise_identity(invocation)   识别 + fail-closed 校验 payload（EE-2/3/4）
  - EnterpriseIdentity(organization_id, user_id, project_id?) 
  - attribute_trace(events, identity)       经 TraceEvent.extensions 注入 attribution（不新增 Core trace 字段）

examples/run_enterprise_identity_slice.py   reference enterprise identity vertical slice（Org A + Org B）

tests/test_enterprise_extension_pilot.py    EE-1..EE-12

ENTERPRISE_EXTENSION_PILOT_V0.1.md          Stage Spec

CI（ci.yml + audit-ref.yml）                 compile 增加 enterprise_extensions；新增 EE 测试步骤
```

## 架构边界（本阶段证明的核心）

```text
platform_standard Core schema      ZERO CHANGE（无 organization_id/user_id/project_id 新字段）
generic RuntimeAdapter             ZERO CHANGE（无 enterprise-specific semantics）
generic TraceEvent schema          ZERO CHANGE（attribution 走 extensions）
agent_runtime/**                   ZERO DIFF（AgentCore / Runtime / CapabilityExecutor 未修改）
enterprise.identity                通过现有 Extension Contract 进入，不污染 business input
```

## 企业语义（仅此一项）

```text
enterprise.identity:
  version: "0.1"
  required: false
  payload: organization_id（必填 non-empty str）/ user_id（必填 non-empty str）/ project_id（可选 non-empty str）
```

Identity ≠ Authentication ≠ Authorization —— 它是 attribution context，不是 business parameter，不决定 Allow/Deny。

## 测试结果

```text
EE-1..EE-12:  12/12 PASS
  EE-1 valid identity accepted          EE-7 Org A executes correctly（org_alpha/user_001/project_a）
  EE-2 missing org rejected             EE-8 Org B executes correctly（org_beta/user_927/project_z）
  EE-3 missing user rejected            EE-9 switching identity no Core schema change
  EE-4 invalid project_id rejected      EE-10 unknown optional extension preserved
  EE-5 identity preserved               EE-11 enterprise layer no agent_runtime import（+git zero diff 复核）
  EE-6 trace attribution visible        EE-12 PS-1..PS-14 + AR-1..AR-7 regression PASS
PS-1..PS-14: 14/14 PASS
AR-1..AR-7:  7/7  PASS
existing Runtime regression: 22/22 examples test modules PASS
reference enterprise identity slice: PASS（Org A + Org B）
```

## 没有实现什么（明确 out of scope）

```text
Authentication / Login / Password / IAM / RBAC / ABAC / Roles / Permissions / Authority
Delegation / Policy Engine / Allow-Deny / Approval / Tenant Isolation / SSO / OAuth
LDAP / Active Directory / User Database / Organization Database / Enterprise Profile
Domain Package / Workflow Engine / Control Plane / MCP / A2A / Multi-Agent
```

## 发现的架构问题 / 备注

1. enterprise.identity 是纯 attribution：本阶段未让 Capability 读取身份改变行为（保留给后续独立 Stage）。
2. `attribute_trace` 在 reference 层组合（generic Adapter 不感知企业语义）；trace attribution 依赖 `TraceEvent.extensions`。
3. 未知 optional enterprise extension（如 `enterprise.unknown_future_extension`）由 Core 保持原行为（接受/保留），验证 Extension 架构未被特化。

## 下一阶段（roadmap，不实施）

```text
Enterprise Identity → Role / Authority → Policy Decision → Approval
```

每一级单独 Stage，不允许一次实现整条链。当前 STOP。
