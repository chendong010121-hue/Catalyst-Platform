# DOMAIN INTENT RECOVERY — V0.1（BLIND · D0 · §10）

> 从 Legacy 工作区恢复的**专业语义意图**（应存活实现替换的长期意义）。不预置具体值/要求（§10）。类别为盲恢复，非已知答案。

| 领域意图类别 | 盲恢复内容 | 盲证据 | 置信 |
|---|---|---|---|
| professional project facts（专业项目事实） | 项目条件事实（建筑高度、层数、用地性质、业态、地下室等）有唯一正式来源（FactRevision），已确认事实不可降级 | facts/extractor.py `_FACT_ANCHORS`；design spec §4.3 | PROVEN |
| source authority（来源权威） | 正式来源身份须确定性准入（真实性、来源身份、地区、版本、证据等级）；候选不得自动成为正式证据 | design spec §4.1；prompt-charter-audit（formal/candidate boundary） | STRONGLY SUPPORTED |
| applicability meaning（适用性语义） | 正式来源身份 ≠ 语义适用性 ≠ 覆盖充分性（三分离）；适用性须显式而非推断 | design spec §1-7；prompt-charter-audit | STRONGLY SUPPORTED |
| clause/table/numeric evidence meaning（条文/表格/数值证据语义） | 规范对象、术语、适用前提、分支、表格行列与项目事实的关系由专业语义解释；禁止编造数值/条文/版本/法域 | design spec §4.1/4.2；prompt-charter-audit（no fabrication） | STRONGLY SUPPORTED |
| professional uncertainty（专业不确定性） | 保留证据缺口而非猜测；缺失信息显式；输出初步（preliminary）并保留状态链接 | design spec §4.2/4.4；prompt-charter-audit（preserve evidence gaps） | STRONGLY SUPPORTED |
| professional result expectations（专业结果期望） | 主结论只覆盖建筑前期/方案设计范围；确定性结论需正式证据或已绑定事实；展示层只渲染 AnswerDocument | design spec §3.1/§4.2/§4.3 | STRONGLY SUPPORTED |

## 盲观察

- 领域语义在**意图文档 + 提示词审计 + 部分代码锚词**中强证据存在；2.0 实现仅落实其中事实保真/提取子集。
- 数值/条文/适用性的**权威语义目前主要由提示词规则（charter 审计）承载**——实现未落地的领域语义存在所有权悬空。
- 具体条款/表值等专业值未在盲恢复中预置（对照阶段前不设种子值）。
