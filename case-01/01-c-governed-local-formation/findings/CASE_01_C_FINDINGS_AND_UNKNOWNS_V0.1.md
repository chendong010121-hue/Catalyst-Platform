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
