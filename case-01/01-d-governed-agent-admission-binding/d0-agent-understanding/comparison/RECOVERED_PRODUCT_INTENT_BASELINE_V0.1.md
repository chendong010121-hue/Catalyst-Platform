# RECOVERED PRODUCT INTENT BASELINE — V0.1（D0 · §13/§24）

> **Catalyst Understanding 的输出**（非手工种子的需求文档）。作为未来 CASE 01-E 专业完成的显式产品意图参考。
> 每条：recovered intent / confidence / evidence source / current BREA status / future completion relevance。

| 恢复的意图 | 置信 | 证据源（盲） | 当前 BREA 状态 | 未来完成相关性（01-E+） |
|---|---|---|---|---|
| 本地建筑规范分析 Agent（单问题咨询 + 项目文件夹分析） | STRONGLY SUPPORTED | design spec §1/§2；README | BREA 覆盖"证据能力"子集 | 完整产品=补齐咨询/分析前端与导出 |
| 结论可展开来源（原文/页码/条文/表格） | STRONGLY SUPPORTED | design spec §2.1.1 | OBL-01/05（逐字+locator）已实现 | 需要 UI 展开/导出（01-E） |
| 已确认事实不可降级；用户确认锁定事实版本 | PROVEN | AGENTS.md；facts/ledger.py | SEAM-01 词汇+归一化；修订机制 DEFER | 需要事实修订/确认回到产品（A-04 语义） |
| 正式/候选证据边界；候选不自动晋升 | STRONGLY SUPPORTED | prompt-charter-audit；AGENTS.md | SEAM-03 verbatim/绑定（无晋升机制） | 需要证据治理（01-E） |
| 三分离判断（来源身份≠适用性≠充分性） | STRONGLY SUPPORTED | design spec §1-7 | SEAM-02 适用链已实现 | 需要覆盖充分性判断（01-E） |
| 本地规范优先；网络仅缺口/验证时补证（候选化） | STRONGLY SUPPORTED | AGENTS.md；config network_mode | DEFERRED（OBL-10） | 需要网络策略实现（01-E/01-F） |
| AnswerDocument 单一答案源 + DOCX/PDF 导出 | STRONGLY SUPPORTED | AGENTS.md；design spec §4.3 | DEFERRED（OBL-09） | 需要答案契约+导出（01-E） |
| 60 题 golden 验收（三层比较；阻断错误门禁） | STRONGLY SUPPORTED | golden-corpus-audit | DEFERRED（01-E） | 需要评价实现（01-E） |
| 项目隔离/持久化；跨重启隔离 | PROVEN | phase-2-report；storage/schema | 首建无项目持久化（归属元数据） | 需要项目生命周期回归（01-E/01-F） |
| 双 provider（Codex + OpenAI-compatible） | STRONGLY SUPPORTED（codex PROVEN） | config.py；providers/* | FN-10 DEFERRED（首建无模型） | 需要 provider 接入（01-E 或后续） |
| Windows 本地一键启动 + 打包交付 | STRONGLY SUPPORTED | scripts/*.ps1；pyproject build | FN-11 最小 Runner（CLI） | 需要一键启动/打包（01-E） |

## 结论（§24 双线）

- **PLATFORM 线**：Catalyst 已能理解（D0 盲恢复）→ 构建（01-C）→ 定义（01-B）→ 理解 legacy（01-A）。✓
- **CASE 线**：BREA 目前=证据能力形成候选；**完整专业产品**（咨询/分析/导出/网络/评价/事实修订/项目生命周期）仍为未来完成工作（01-E/01-F）。两线均未完成——本基线为 01-E 的显式输入。
- 本基线**不回溯重定义**已接受 BREA 契约（§24）。
