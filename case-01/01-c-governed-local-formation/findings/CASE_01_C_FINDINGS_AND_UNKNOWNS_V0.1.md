# CASE 01-C FINDINGS & UNKNOWNS — V0.1

> 处置：RESOLVED / NON-BLOCKING / BLOCKING / DEFERRED / PARK。

| ID | 观察 | 处置 | 说明 |
|---|---|---|---|
| F-01 | Builder 首次运行目标路径解析错误（MECHANICAL，R-01） | RESOLVED | 修复并记录于 BUILDER_RUN_REPORT R-01；最终生成位置正确 |
| F-02 | 语料键 vs 标准身份键错位（R-02/R-03） | RESOLVED | corpus 双键 + 显示身份分离；测试全绿 |
| F-03 | fail-closed 结论曾含原始键数字（R-04） | RESOLVED | Domain 标签（无数字） |
| F-04 | `python -m brea.runner` 触发良性 RuntimeWarning（'brea.runner' in sys.modules） | NON-BLOCKING | 由 `__init__` 导入 runner 引起；不影响结果；01-D 前可优化 |
| F-05 | OCR 语料已知瑕疵（表5.0.4"中型商业"行标签行序交错；条文编号跨页丢失） | NON-BLOCKING | 首建仅用行序干净的"大型商业"行 + 编号完整的 3.1.3；verbatim 断言兜底 |
| F-06 | 候选无提示词文件、无 provider（ST-03/04） | RESOLVED（设计满足） | Prompt/RAG/provider 未成为语义权威 |
| F-07 | 语料哈希失配 fail closed（ST-07） | RESOLVED | CorpusIntegrityError |
| F-08 | GAP-01/GAP-05 Case-closed；其余 GAP 未实现 | RESOLVED（记录） | PLATFORM_GAP_UPDATE |
| F-09 | 01-D/01-E/01-F 未授权；admission/binding/assetization/evolution 未开始 | NON-BLOCKING（边界） | 01-D 边界文档已备 |

## 阻塞性未知

**BLOCKING：NONE**。01-C 全部 CG/AC/BC 判定 PASS；无迫使 01-D 猜测的架构未知。

## 修复期发现（2026-08-21，C-01..C-05）

| ID | 观察 | 处置 |
|---|---|---|
| RF-01 | 外部审查 C-01：Builder 未语义消费定义（仅复制模板+手动请求） | RESOLVED —— 定义驱动解析/校验/候选映射核对（BT-01..10 PASS） |
| RF-02 | C-02：SHA 仅记录未强制执行 | RESOLVED —— 生成前 fail closed + BT-02 负测试 |
| RF-03 | C-03：义务映射指向不存在的 test_obl_* | RESOLVED —— 真实测试引用 + BT-08 校验 + 对账 OBLIGATION_CONFORMANCE |
| RF-04 | C-04：FE-09 引用未提交的 01c_selfcheck.log | RESOLVED —— 原始日志保留（01c_selfcheck_original.txt）+ 修复重跑真实日志（01c_repair_selfcheck.txt） |
| RF-05 | C-05：GAP-01/05 CASE-CLOSED 过早 | RESOLVED —— 修复证明后标 CASE-CLOSED for Case 01（待外部再审计） |
| RF-06 | 解析器把 §4 续行"DEFERRED：OBL-07..10"计入义务集 | RESOLVED —— 只取首行义务声明；BT-05/BT-07 通过 |

## 最终语义解析器修复（2026-08-21，契约 CASE_01_C_FINAL_SEMANTIC_PARSER_REPAIR_V0.1.md）

| ID | 观察 | 处置 |
|---|---|---|
| RF-07 | §7 legacy 资产语义缺陷：DEFERRED（A-01/A-03/A-05）被当作 allowed（单字段含两组） | RESOLVED —— `parse_legacy_assets` 分裂为 selected/deferred 两组精确集合（BT-11/12/13；disjoint）；Builder 清单记录 selected_legacy_adaptation_assets 与 deferred_legacy_assets；deferred 永不 build-authorized |
| RF-08 | 私有自由度仅"present"布尔，未语义提取 | RESOLVED —— Option A：解析实际条目（12 项；BT-14）；清单记录 private_freedom 列表 |
| RF-09 | GAP-01/05 状态标注需按 §8 限定 | RESOLVED —— CONDITIONALLY CASE-CLOSED（最终外部闭包审计后 → CASE-CLOSED） |
