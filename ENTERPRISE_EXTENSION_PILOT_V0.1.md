# ENTERPRISE_EXTENSION_PILOT_V0.1.md

## Goal

验证架构假设：

> **Stable Platform Core + Adjustable Enterprise Semantics**

Platform Standard Core v0.1 已证明多 Capability 共享同一 Core/Runtime；本阶段证明多企业上下文也能通过 **Extension** 使用同一 Core/Runtime，而无需修改 Core / Runtime / AgentCore。

## Accepted Baseline

```text
main  @ a99629549f700a859e9393a0a46281ea4350b985
tree  @ b50f09ab0f66fc43c87fb7547a7beed98f9ce110
```

## In Scope

```text
enterprise.identity semantic（唯一企业语义）
reference extension parser/handler（enterprise_extensions/identity.py）
organization_id / user_id / optional project_id
identity preservation
minimal trace attribution（经 TraceEvent.extensions，不新增 Core trace 字段）
一个 enterprise identity vertical slice
Org A / Org B 两个企业上下文 portability
tests（EE-1..EE-12）
Stage 文档
```

## Out of Scope

```text
Authentication / Login / Password / IAM / RBAC / ABAC / Roles / Permissions
Authority / Delegation / Policy Engine / Allow-Deny / Approval / Tenant Isolation
SSO / OAuth / LDAP / Active Directory / User Database / Organization Database
Enterprise Profile / Domain Package / Workflow Engine / Control Plane / MCP / A2A / Multi-Agent
```

## enterprise.identity semantic

```yaml
extensions:
  enterprise.identity:
    version: "0.1"
    required: false
    payload:
      organization_id: "org_001"   # required, non-empty string
      user_id: "user_001"          # required, non-empty string
      project_id: "project_001"    # optional, if present must be non-empty string
```

Identity ≠ Authentication ≠ Authorization。它只是本次 Invocation 的 **attribution context**，不是 business parameter，不决定 Allow/Deny。

## Reference Path

```text
Standard Invocation
  ├── input
  └── extensions.enterprise.identity
              ↓
   Enterprise Extension Handler（validate/preserve）
              ↓
   Platform Validator（Core 级扩展结构）
              ↓
   Runtime Adapter（generic，无企业语义）
              ↓
   Existing Runtime
              ↓
   Reference Capability
              ↓
   Standard Result
   + Trace Attribution（TraceEvent.extensions 注入 enterprise.identity）
```

## Release Gate（EE-1..EE-12）

```text
EE-1  valid enterprise.identity accepted
EE-2  missing organization_id rejected
EE-3  missing user_id rejected
EE-4  invalid optional project_id rejected
EE-5  enterprise.identity preserved through reference invocation path
EE-6  identity visible in trace attribution
EE-7  Org A / User A executes correctly（org_alpha / user_001 / project_a）
EE-8  Org B / User B executes correctly（org_beta / user_927 / project_z）
EE-9  switching enterprise identity changes no Core schema
EE-10 unknown optional enterprise extension preserves original Core behavior
EE-11 agent_runtime/** ZERO DIFF
EE-12 existing PS-1..PS-14 + AR-1..AR-7 regression PASS
```

## Stop Condition

EE-1..EE-12 全部 PASS 后 STOP。不开始 Role / Authority / Policy / Approval。
