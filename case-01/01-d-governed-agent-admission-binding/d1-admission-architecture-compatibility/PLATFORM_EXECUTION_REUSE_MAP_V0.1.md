# PLATFORM EXECUTION REUSE MAP — V0.1（D1 · §14）

> BREA 整机执行需求 vs 当前 Platform 执行缝（主 SHA 5874be11）。每项：能否复用/承载含义/须留在外部/是否隐含 Agent==Capability/D2 是否需改动。

| Platform 缝 | 可复用？ | 承载含义 | 须留在外部 | 隐含 Agent==Capability？ | D2 改动 |
|---|---|---|---|---|---|
| Capability Descriptor（models.py CapabilityDescriptor） | 部分（仅执行机制声明） | 能力级输入/输出 schema 与 side_effect | Agent 身份/版本/准入语义（不放 Descriptor） | **会**（若把 Agent 身份塞进 Descriptor.id→打破 I-02）→ 避免 | 需 Case-local 映射：BREA runner 的 describe() 仅声明执行契约；Agent 身份另存 Admission Record |
| Standard Invocation（models.py Invocation；validation.py） | **是**（REUSE-AS-IS） | 请求/输入/context.extensions/trace_id | 无 | 否（Invocation 是执行请求，非身份） | 需携带 governance.agent extension |
| Validator（validation.py PlatformValidator） | **是**（REUSE-AS-IS） | Platform 契约校验（fail-closed；context.extensions 必需——扩展可合法携带归因） | 无 | 否 | 无（现有校验接受可选扩展） |
| Extension（extensions.py） | **是**（REUSE-AS-IS + 语义在扩展） | 可选扩展原样保留；`governance.` 命名空间保留 | 无 | 否 | Case-local governance.agent 扩展（非 Core） |
| Runtime Adapter（runtime_adapter.py RuntimeAdapter） | **是**（REUSE-AS-IS） | (capability_id,version)→实现绑定、版本路由、预检、semantics 映射；"carries NO business/domain semantics" | Agent 治理/工作流/策略/企业含义 | 否（Adapter 是执行翻译，非身份） | Case-local 绑定项（BREA runner 实现）+ artifact mapper |
| Runtime（agent_runtime/**） | **是**（REUSE-AS-IS） | 执行生命周期、执行确定性（unresolved）、runtime-local control | Domain/Enterprise/治理准入语义 | 否 | **无（Runtime 零变更）** |
| Standard Result（models.py Result） | **是**（REUSE-AS-IS） | status/output/error（success/failure/unresolved） | Agent 归属（经 Trace/extension） | 否 | 无（Case-local 结果契约已映射；见 01-C RegulationEvidenceResult） |
| ArtifactRef（models.py ArtifactRef + Producer） | **是**（REUSE-AS-IS） | 证据/产物引用（producer=capability+invocation） | Domain 证据含义（留在 BREA 证据束） | 否 | Case-local artifact mapper（BREA 证据→ArtifactRef） |
| Trace（models.py TraceEvent；validation.py subject_id） | **是**（REUSE-AS-IS） | 执行事件 + subject_id + extensions | 无 | 否 | Case-local attribution（governance.agent 写 TraceEvent.extensions，模式=enterprise.identity） |

## 结论

- 执行机制全部 **REUSE-AS-IS**；唯一需要的是 Case-local（Admission Record + Binding 包装 + `governance.agent` Extension 归因 + artifact mapper）。
- **Agent != Capability 保持**：Agent 身份/版本/准入存放在 Case-local 记录与扩展归因，绝不放 CapabilityDescriptor 身份。
- **无 Platform Core / Runtime 改动**（S-D1-05/06 未触发）。
