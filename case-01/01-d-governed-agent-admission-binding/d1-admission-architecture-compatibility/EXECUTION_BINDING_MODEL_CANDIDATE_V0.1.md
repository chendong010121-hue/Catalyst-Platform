# EXECUTION BINDING MODEL CANDIDATE — V0.1（D1 · §13）

> CASE-LOCAL 执行绑定候选（D2 实施依据）。Binding 是连接已准入受治理主体与执行实现/路径的适配关系；**不定义 Agent 含义**（I-05）。

## 绑定链

```text
已准入 Agent 版本（BREA v0.1-candidate；Admission Record）
        ↓ binding
实现身份（candidate/brea-v0.1 源树 + BUILDER_OUTPUT_MANIFEST 指纹）
        ↓ execution entry
BREA runner（实现 agent_runtime Capability 协议：describe()/invoke()）
        ↓ Platform seam（REUSE-AS-IS）
Invocation → PlatformValidator → RuntimeAdapter（(capability_id, version)→实现）→ Runtime → Result / ArtifactRef / Trace
```

## 模型回答（§13 清单）

- **What is being bound?** 已准入 Agent 版本（Admission Record 身份）→ 实现身份 → 执行入口。
- **What implementation is being bound?** `candidate/brea-v0.1`（确定性 Python 包；`python -m brea.runner` 入口）。
- **How is implementation identity frozen?** 源树全量 SHA-256 + BUILDER_OUTPUT_MANIFEST SHA（D2 计算并写入 Binding 记录；不静默重算）。
- **What execution entry is used?** BREA runner 的 `answer(request_id, question, project_context, regulation_context, enterprise_context)`（适配为 Runtime Capability `invoke(parameters, context)`；describe() 声明输入/输出 schema——直接绑定预检，runtime_adapter.py `_checked_direct_binding_descriptor`）。
- **Which Platform seam is reused?** Standard Invocation → Validator（validation.py）→ RuntimeAdapter（runtime_adapter.py）→ Runtime（agent_runtime）。
- **Which Adapter seam is reused?** RuntimeAdapter 绑定（(capability_id, version)→内部键→能力）＋ 可选 adapter-local artifact mapper（BREA 证据束→ArtifactRef；模式见 examples compose_report_artifact_mapper）。
- **How is Agent attribution preserved?** `governance.agent` Extension（payload={agent_id, agent_version, admission_ref, binding_ref}）置于 Invocation.extensions/context.extensions；执行后写 TraceEvent.extensions（模式=enterprise_extensions/identity.py attribute_trace；冲突 fail-closed）。
- **How does a mismatch fail closed?** 定义 SHA 不符（01-C Builder 已强制）；指纹不符（Binding 校验）；admission/binding 引用缺失；attribution 冲突（extension 规则）；Platform 验证失败（validation.py fail-closed）。

## Binding 明确不拥有（Q-05 / §13）

```text
专业 Domain 含义（适用性/事实/来源/数值/不确定）
企业策略 / 组织策略
Agent 产品目的
Runtime 执行语义（生命周期/确定性——Runtime 自有）
```

## 未来替换（概念，不实现 N+1）

```text
Agent v0.1（已准入）→ binding → 实现 A
Agent v0.2（另行受治理）→ 新 binding → 实现 B
```
