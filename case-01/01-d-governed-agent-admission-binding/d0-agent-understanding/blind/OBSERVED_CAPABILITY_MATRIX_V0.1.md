# OBSERVED CAPABILITY MATRIX — V0.1（BLIND · D0 · U-3/U-4）

> 已实现=代码/测试/配置可直接执行者；**不因 README/Prompt 描述推断实现**。状态：IMPLEMENTED / PARTIAL / INTENDED_NOT_IMPLEMENTED / CONTRADICTED / UNKNOWN。

| REQ | 能力 | 观察状态 | 观察证据（2.0 工作区） | 说明 |
|---|---|---|---|---|
| REQ-L03 | 文档摄入/保真（PDF/OCR/DOCX/TXT、SHA 指纹、来源坐标） | **IMPLEMENTED** | documents/{batches,ocr,pdf,docx,text,_source}.py；domain/documents.py；tests/unit/documents | 解析+指纹+坐标代码存在；测试覆盖 |
| REQ-L04 | 事实提取/确认/不可变修订 | **IMPLEMENTED** | facts/{extractor,ledger,normalizer}.py；domain/facts.py；api/facts.py；tests/unit/facts | 修订生命周期+确认锁+KnownFacts；测试覆盖 |
| REQ-L02 部分 | 文件夹摄入→事实候选（分析输出未实现） | **PARTIAL** | documents/batches.py；api/documents.py；phase-2-report（e2e 项目隔离通过） | 摄入/提取已实现；"关注事项/风险"分析未在 2.0 |
| REQ-L11 | provider 边界：Codex | **IMPLEMENTED** | providers/codex.py；tests/unit/providers | codex exec 结构化调用实现 |
| REQ-L11 | provider：OpenAI-compatible | **INTENDED_NOT_IMPLEMENTED** | config.py provider_kind="openai_compatible" 声明；providers/ 无实现类 | 仅声明，无实现（CONTRADICTED：声明 vs 代码） |
| REQ-L12 | 项目/上下文隔离 | **IMPLEMENTED** | domain/projects.py；storage/schema.py；phase-2-report（跨项目 404） | 隔离实证 |
| REQ-L13 | 运行/审计事件（append-only） | **IMPLEMENTED** | domain/runs.py；storage/schema.py（触发器） | 表+触发器存在 |
| REQ-L14 | OCR（扫描 PDF） | **IMPLEMENTED** | documents/ocr.py（rapidocr_onnxruntime）；requirements.lock | 代码+依赖 |
| REQ-L01 | 单问题规范咨询（检索→适用性→回答） | **INTENDED_NOT_IMPLEMENTED（2.0）** | 2.0 无 retrieval/answer 模块；design spec §2.1.1 仅意图 | 检索/回答链在 legacy1（跨工作区） |
| REQ-L05/06 | 证据治理/引用可追溯 | **PARTIAL** | provenance 实现（documents/facts）；证据分级/引用校验语义在 legacy1 提示与 AGENTS 规则 | 保真已实现；正式/候选晋升机制未在 2.0 |
| REQ-L07 | 三分离判断 | **INTENDED_NOT_IMPLEMENTED（2.0）** | 仅 design spec/AGENTS 声明 | 无实现 |
| REQ-L08 | 网络补证策略 | **INTENDED_NOT_IMPLEMENTED** | config.py network_mode 声明；无消费点 | CONTRADICTED：声明 vs 未消费 |
| REQ-L09 | 规范理解/适用性/证据绑定 | **INTENDED_NOT_IMPLEMENTED（2.0）** | design spec §5.1 声明 | 无实现 |
| REQ-L10 | AnswerDocument + DOCX/PDF 导出 | **INTENDED_NOT_IMPLEMENTED（2.0）** | AGENTS.md/design spec 声明；reportlab 依赖在 requirements.lock | 依赖存在，无导出实现 |
| REQ-L15 | 评价/验收（60 题） | **INTENDED_NOT_IMPLEMENTED（2.0）** | golden-corpus-audit（语料冻结待裁决）；2.0 无评价模块 | 语料在 legacy1 |
| REQ-L16 | 打包/一键启动 | **PARTIAL** | pyproject.toml build extra；scripts/{start,stop,runtime}.ps1 | 脚本/构建声明存在；打包产物未见 |

## 关键观察（盲）

1. **2.0 = 文档→事实→确认 前段**；检索/证据/答案/导出/网络/评价 全为意图声明（主要实现位于 legacy1 或缺失）。
2. **两处声明-实现矛盾**（CONTRADICTED）：`openai_compatible` provider；`network_mode`。
3. 事实提取器含领域锚词（`facts/extractor.py` `_FACT_ANCHORS`）——领域词汇内嵌实现（耦合观察）。
4. 已确认事实保护/不可变修订为强实现证据（代码+测试）。
