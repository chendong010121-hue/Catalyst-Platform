# RESPONSIBILITY RECOVERY — V0.1（BLIND · D0 · U-5）

> 恢复的意义所有权分类（**不以文件位置作责任证明**）。类别：DOMAIN INTENT / ENTERPRISE INTENT / AGENT BEHAVIOR / PRIVATE IMPLEMENTATION HOW / RUNTIME RESPONSIBILITY / PLATFORM-INTEROP CANDIDATE / UNRESOLVED。

| 恢复项 | 含义 | 分类 | 盲证据 | 置信 |
|---|---|---|---|---|
| 专业项目事实词汇（建筑高度/层数/用地/业态等） | 专业事实语义 | DOMAIN INTENT | facts/extractor.py `_FACT_ANCHORS`/`_STRUCTURAL_FACT_HEADINGS`；design spec §4.3（FactRevision 唯一正式事实源） | PROVEN |
| 来源身份/版本/法域/适用性语义（三分离） | 规范适用语义 | DOMAIN INTENT | design spec §1-7/§4.2；prompt-charter-audit（applicability explicit） | STRONGLY SUPPORTED |
| 条文/表格/行列/数值证据语义 | 规范证据语义 | DOMAIN INTENT | design spec §4.2（表格行列关系）；prompt-charter-audit（no fabrication of numbers/clauses） | STRONGLY SUPPORTED |
| 专业不确定性/缺失信息处理 | 专业结果语义 | DOMAIN INTENT + AGENT BEHAVIOR | design spec §4.2/4.4（显式状态；preserve evidence gaps）；AGENTS.md（fail-closed 精神） | STRONGLY SUPPORTED |
| 项目归属（project_id 隔离一切业务数据） | 组织/项目上下文 | ENTERPRISE INTENT | design spec §5.1（Project Service）；domain/projects.py | PROVEN |
| 数据接入/网络约束（本地优先、网络策略、来源信任） | 组织约束 | ENTERPRISE INTENT | AGENTS.md（network only gap/verify）；design spec §4.1（harness 网络权限）；config.py network_mode | STRONGLY SUPPORTED |
| 人工确认/验收期望（事实确认强制；golden 人工裁决） | 组织治理期望 | ENTERPRISE INTENT | AGENTS.md（users confirm facts）；golden-corpus-audit（human review，非逐字一致） | STRONGLY SUPPORTED |
| 协调专业任务/产生答案/显式不确定 | 行为义务 | AGENT BEHAVIOR | design spec §4.2（Plan-and-Solve Agent 拥有语义链）；AGENTS.md | STRONGLY SUPPORTED |
| 文档解析/OCR/检索/存储/服务/前端 | 实现 HOW | PRIVATE IMPLEMENTATION HOW | documents/*, frontend/*, scripts/*, config.py | PROVEN |
| 执行生命周期/超时/预算/取消/恢复 | 执行语义 | RUNTIME RESPONSIBILITY | providers/base.py（ProviderTimeout）；design spec §4.1（harness 工具/时间/轮数/token/网络预算） | STRONGLY SUPPORTED |
| 标准 Invocation/Result / provider 契约 | 互操作候选 | PLATFORM-INTEROP CANDIDATE | providers/base.py（ModelRequest/ModelResult）；api/*（ErrorEnvelope） | WEAKLY SUPPORTED |
| 证据治理/适用性/答案语义的最终所有权（2.0 无实现） | 语义悬空 | UNRESOLVED | 2.0 无对应代码；legacy1 有实现；prompt-charter-audit（dispositions） | STRONGLY SUPPORTED（存在性） |
| 组织归属（org/user） | 企业归属 | UNRESOLVED（2.0 无 org/user 字段；仅 project） | domain/projects.py（Location/name；无 organization_id） | PROVEN（缺失） |

## 盲结论

- Domain 意图（专业事实/来源/适用性/证据/不确定）在**意图文档与提示词审计**中强证据存在；2.0 实现仅覆盖事实保真/提取部分。
- Enterprise 意图（项目隔离、本地/网络约束、人工确认/验收）有实据；**组织归属（org/user）在 2.0 中缺失**。
- 执行语义（超时/预算）有实现证据（provider）——RUNTIME 责任。
- 检索/OCR/存储/前端=私有 HOW；证据治理/答案语义所有权 **UNRESOLVED**。
