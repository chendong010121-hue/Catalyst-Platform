# ADMISSION NEED COMPATIBILITY MATRIX — V0.1（D1 · §8）

> 每个 D1 需求恰用一种主处置：REUSE-AS-IS / CASE-LOCAL / EXTENSION / ADAPTER-LOCAL / PLATFORM-GAP / RUNTIME-GAP / DEFER / REJECT。
> 证据列：主 SHA 5874be11 文件 + 符号/节（详见 D1_EVIDENCE_INDEX）。

| Need | Governed meaning | Default owner | Current Catalyst evidence | Disposition | D2 required? | Gap? |
|---|---|---|---|---|---|---|
| Agent identity | 精确受治理 Agent（BREA） | Agent governance | 无 Agent 级身份契约（Capability 有 id；models.py CapabilityDescriptor） | **CASE-LOCAL**（Admission Record.agent_id） | YES | NO |
| Agent version | 精确版本（v0.1-candidate） | Agent governance | 无 Agent 级版本契约 | **CASE-LOCAL** | YES | NO |
| owner | 问责（User/CASE 01 Product-Release Authority，F-07） | Enterprise/Governance | F-07 决策记录（01-B ENTRY_DECISIONS） | **CASE-LOCAL**（Enterprise 上下文 + 记录字段） | YES | NO |
| definition SHA | 定义身份（6c6e4707…） | Governance evidence | 01-B BUILDER_CONSUMABLE_DEFINITION（已提交）+ 01-C Builder 强制执行 | **REUSE-AS-IS** | YES | NO |
| formation evidence | 形成证明（01-C closure dd491a7） | Governance evidence | 01-C evidence/**（conformance、整机测试、结果） | **REUSE-AS-IS** | YES | NO |
| implementation fingerprint | 绑定的实现（brea-v0.1 源树+manifest） | Binding | 01-C BUILDER_OUTPUT_MANIFEST（已提交）；哈希由 D2 脚本计算 | **CASE-LOCAL** | YES | NO |
| admission status | 准入决策 | Governance | 无机制（registry.py 明确非生产 Registry） | **CASE-LOCAL**（准入记录状态字段 + 决策引用） | YES | NO |
| execution binding | 版本→实现→入口 | Binding/Adapter | runtime_adapter.py（(capability_id,version)→实现绑定、版本路由、预检） | **ADAPTER-LOCAL**（BREA runner 为 capability 实现 + 绑定） | YES | NO |
| Agent attribution | 执行溯源（agent_id/version/admission/binding） | Governance/Extension | extensions.py（governance. 保留命名空间）；enterprise_extensions/identity.py（Extension 归因模式已证）；TraceEvent.extensions | **EXTENSION**（governance.agent） | YES | NO |
| Platform invocation | 公共执行路径 | Platform Standard | Invocation/Validator/Adapter/Result/ArtifactRef/Trace（models/validation/runtime_adapter） | **REUSE-AS-IS** | YES | NO |
| Runtime execution | 生命周期/确定性 | Runtime | agent_runtime/**（execution certainty、unresolved、runtime-local control） | **REUSE-AS-IS** | YES | NO |
| Enterprise attribution | 组织上下文 | Enterprise | enterprise.identity（organization/user/project） | **REUSE-AS-IS**（enterprise.identity 直接承载）+ CASE-LOCAL（agent 归因包） | YES | NO |
| Domain semantics | 专业含义 | Domain | 01-C candidate（facts/applicability/evidence）；Platform 无 Domain 概念 | **REUSE-AS-IS**（Platform 无需承载；Domain 留在 Agent） | NO | NO |
| corpus boundary | 受保护输入 | Agent/Domain/Governance | 01-B LOCAL_CORPUS_REFERENCE_MANIFEST（已提交；只读/不提交） | **CASE-LOCAL**（准入记录引用语料清单） | YES | NO |
| owner/acceptance authority 引用 | 验收权威 | Enterprise/Governance | F-07（evaluation owner=User/CASE 01） | **CASE-LOCAL** | YES | NO |
| 通用 Agent Manifest / 对象模型 | （无证据需要的预测概念） | — | — | **REJECT**（I-09 小核心；禁止厚对象模型） | NO | NO |

## 汇总

- REUSE-AS-IS：definition SHA、formation evidence、Platform invocation、Runtime execution、Enterprise attribution、Domain semantics = **6**
- CASE-LOCAL：Agent identity、Agent version、owner、fingerprint、admission status、corpus boundary、acceptance authority 引用 = **7**
- EXTENSION：Agent attribution = **1**
- ADAPTER-LOCAL：execution binding = **1**
- PLATFORM-GAP / RUNTIME-GAP：**0** · DEFER：**0**（当前 15 项均 D2 需要或 REJECT）· REJECT：通用 Agent Manifest = **1**
- 无任何 Need 因"Case-local 不便"被提升为 Platform（§7 规则）。
