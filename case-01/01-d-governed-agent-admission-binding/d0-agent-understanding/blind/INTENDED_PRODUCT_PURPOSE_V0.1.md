# INTENDED PRODUCT PURPOSE — V0.1（BLIND · D0 · U-1）

> 仅从 Legacy 2.0 工作区证据恢复的**产品意图**（区别于当前实现现实，U-3）。

## 恢复的意图目的

**本地建筑规范分析 Agent（Standards Agent 2.0）**——"干净、交付级"迁移的本地建筑规范分析工作流（README.md）：

1. **单问题规范咨询**：用户输入项目条件 + 自然语言问题 → Agent 理解问题、检索本地规范、判断证据适用性 → 自然、专业、可读的回答；每个关键结论可展开查看原规范/页码/条文/表格（design spec §2.1.1）。
2. **项目文件夹自动分析**：用户指定文件夹 → 解析资料并提取规划条件 → 用户确认/修改/删除/补充事实并锁定事实版本 → Agent 结合已确认条件与本地规范库，主动提出方案/初设阶段应关注的规范事项、风险与缺失信息（design spec §2.1.2）。

## 交付意图

- Windows 本地一键启动、浏览器 Workbench 前端、程序包与知识库快照分开交付（design spec §2.2）。
- 支持 Codex Runtime 与 OpenAI-compatible API provider（可配置）（design spec §2.2）。
- 正式模式导出 DOCX/PDF；调试模式导出 Excel 证据矩阵与完整 JSON 审计（design spec §2.2）。
- 不依赖互联网完成本地规范分析；仅本地证据不足时按策略调用网络补证（design spec §2.2 / AGENTS.md）。

## 意图边界（业务范围）

- 主结论覆盖建筑前期设计/方案设计：规划控制与总图、建筑分类/功能/空间、方案阶段防火、无障碍/停车/日照/退界/间距、规划条件与规范初步核对（design spec §3.1）。
- 默认排除：结构专项、给排水/暖通/电气专项、BIM/海绵、施工工艺/设备选型/材料选型、需专项计算或法定审查的最终结论（design spec §3.2）。
- 非目标：通用聊天机器人；网络结果自动成为正式依据；"流程完成"代替"证据支持的回答"；关键词补丁；固定计划步骤数（design spec §3.3）。

## 意图中的专业语义原则（源自工作区设计/审计文档）

- 原始用户问题/项目级目标贯穿 Plan/Solve/Answer（design spec §4.2）。
- 正式来源身份 / 语义适用性 / 覆盖充分性 = **三个不同判断**（design spec §1-7；prompt-charter-audit）。
- 已确认事实不可降级；候选证据不得自动成为正式证据（AGENTS.md；design spec §4.3）。
- 单一事实来源：`FactRevision`（事实）、`EvidenceRecord.evidence_id`（证据）、`AnswerDocument`（用户可见答案）（design spec §4.3）。
- 展示层只渲染 AnswerDocument，不重新决定结论（design spec §4.2）。

## 与当前实现现实的区别（详见 OBSERVED_CAPABILITY_MATRIX）

当前 2.0 代码已实现：文档摄入/OCR/指纹、事实提取/确认/不可变修订、项目隔离、运行事件、Workbench、provider 边界；
**尚未在 2.0 代码中实现**（意图声明存在）：本地 RAG/检索、规范理解/适用性/证据绑定、AnswerDocument/回答组装、导出、网络补证、评价验收。
