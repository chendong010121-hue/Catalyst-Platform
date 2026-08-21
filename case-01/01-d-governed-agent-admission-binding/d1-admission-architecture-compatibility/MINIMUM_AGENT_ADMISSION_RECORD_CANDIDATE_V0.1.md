# MINIMUM AGENT ADMISSION RECORD CANDIDATE — V0.1（D1 · §12）

> **CASE-LOCAL CANDIDATE MODEL —— NOT PLATFORM CORE · NOT GENERIC AGENT MANIFEST。**
> 最小 Case-local 准入记录候选（D2 实施依据）；不是 Platform Standard 提案；无未来完整 Agent 对象模型（I-09）。

## 目的

记录一个精确受治理 Agent 版本被准入的证据支撑决策（I-03：Admission ≠ Registry.register；I-04：Admission ≠ runnable）。

## 候选字段（分类：REQUIRED NOW / REFERENCE ONLY / DERIVED / DEFER / REJECT）

| 字段 | 存在原因 | Owner | Source of truth | 状态 |
|---|---|---|---|---|
| agent_id | 受治理 Agent 身份（BREA） | Agent governance | Admission Record（Case-local 文件） | REQUIRED NOW |
| agent_version | 精确版本（v0.1-candidate） | Agent governance | 01-B/01-C 已接受定义 + 本记录 | REQUIRED NOW |
| owner_ref | 问责（User / CASE 01 Product-Release Authority） | Enterprise/Governance | 01-B ENTRY_DECISIONS（F-07） | REQUIRED NOW |
| professional_purpose_ref | 目的引用（不可混入测试 Catalyst） | Agent governance | 01-B IDENTITY（已提交） | REFERENCE ONLY |
| governed_definition_ref / SHA | 定义身份与完整性（6c6e4707…） | Governance evidence | 01-B BUILDER_CONSUMABLE_DEFINITION（已提交；SHA 已强制） | REQUIRED NOW |
| formation_evidence_refs | 形成证明（conformance/整机/三案） | Governance evidence | 01-C evidence/**（已提交） | REFERENCE ONLY（引用 01-C 闭包） |
| obligations_ref | OBL-01..06 引用 | Agent governance | 01-B INITIAL_AGENT_OBLIGATIONS（已提交） | REFERENCE ONLY |
| governed_seams_ref | SEAM-01..03 引用 | Agent/Domain | 01-B GOVERNANCE_DEPTH（已提交） | REFERENCE ONLY |
| implementation_fingerprint_ref | 绑定实现身份（源树+manifest SHA） | Binding | D2 计算并记录（源树全量 SHA + BUILDER_OUTPUT_MANIFEST SHA） | REQUIRED NOW |
| enterprise_context_ref | 最小组织/归属（org/user/project + owner + acceptance） | Enterprise | F-07 + D2 记录（enterprise.identity 语义复用） | REQUIRED NOW |
| corpus / protected-input boundary ref | 受保护语料边界（只读/不提交） | Agent/Domain/Governance | 01-B LOCAL_CORPUS_REFERENCE_MANIFEST（已提交） | REFERENCE ONLY |
| admission_status | 准入决策状态 | Governance | 本记录（ADMITTED / REJECTED / PENDING） | REQUIRED NOW |
| admission_decision_ref | 决策依据（本 D1/D2 证据 + 外部审查） | Governance | D1/D2 evidence + ChatGPT 外部审查 | REQUIRED NOW |
| CapabilityDescriptor / registry 字段 | （Capability 身份≠Agent 身份） | — | — | REJECT（I-02） |
| 通用 Agent Manifest / 对象模型字段 | （预测概念） | — | — | REJECT（I-09） |

## 使记录失效的条件

```text
定义 SHA 不匹配（6c6e4707…）
实现指纹不匹配（绑定实现被换）
形成证据缺失（01-C 闭包不可解析）
所有者/验收权威未记录
语料边界违反（raw corpus 被提交）
Agent 身份/版本与执行归因不一致
```

## 版本替换影响（概念，D2 不实现 N+1）

```text
Agent v0.1-candidate（已准入）→ 新版本 → 新 Admission Record（新定义 SHA + 新指纹）
旧记录保留为历史准入决策；实现替换经新 Binding（I-10：可替换但不随意替换）
```

## 显式排除

- 无运行时注册表条目（Admission ≠ Registry.register）；无 SDK；无 catalog；无 control-plane；无 IAM/RBAC/审批（D1 §9）。
