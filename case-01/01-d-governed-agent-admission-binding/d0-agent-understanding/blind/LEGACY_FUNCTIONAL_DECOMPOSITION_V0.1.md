# LEGACY FUNCTIONAL DECOMPOSITION — V0.1（BLIND · D0 · U-8）

> 从 Legacy 2.0 工作区恢复的功能分解。**不使用**当前 BREA FN-01..11 作为提取模板（冻结前）；比较在 `comparison/` 阶段进行。
> 字段：legacy_function_id / name / professional purpose / input/output / evidence refs / semantic owner / implementation location(s) / implementation status / coupling finding / replaceability boundary / confidence。

| LF | name | purpose | I/O | evidence refs | semantic owner | location | status | coupling/mixed finding | replaceability boundary | confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| LF-01 | Project lifecycle | 项目创建/列表/隔离目录 | in: ProjectCreate; out: Project | domain/projects.py; services/projects.py; api/projects.py; phase-2-report | AGENT（行为） | 2.0 services/api/domain | IMPLEMENTED | 项目目录与记录耦合（创建回滚） | 高（可换存储） | PROVEN |
| LF-02 | Document intake & parsing | 文件夹摄入、只读保真、PDF/OCR/DOCX/TXT 解析 | in: files+paths; out: DocumentBatch/ParsedDocument | documents/*; domain/documents.py; tests/unit/documents | AGENT + PRIVATE HOW（解析） | 2.0 documents | IMPLEMENTED | 来源语义（指纹/坐标）由 schema 触发器+代码强执 | 高 | PROVEN |
| LF-03 | Fact extraction (provider-backed) | 从解析块提取事实候选（schema 校验、来源锚定） | in: batch; out: FactExtractionPayload/candidates | facts/extractor.py; domain/facts.py; providers/base.py | DOMAIN 意图（词汇）+ AGENT（提取） | 2.0 facts/extractor | IMPLEMENTED | **领域词汇硬编码于实现**（_FACT_ANCHORS）；提示词承载规则（charter） | 中（词汇需资产化） | PROVEN |
| LF-04 | Fact revision ledger & confirmation | draft→confirmed 不可变修订；确认锁；KnownFacts 保护 | in: edits/confirm; out: FactRevision | facts/ledger.py; storage/schema.py; tests/unit/facts | AGENT（治理行为） | 2.0 facts/storage | IMPLEMENTED | 治理强度依赖 SQLite 触发器+代码双保险 | 高 | PROVEN |
| LF-05 | Run & context manager | analysis_runs + append-only run_events | in: run create; out: AnalysisRun/RunEvent | domain/runs.py; storage/schema.py | AGENT | 2.0 domain/storage | IMPLEMENTED | — | 高 | PROVEN |
| LF-06 | Local RAG / retrieval | 本地规范检索（候选） | （未在 2.0 实现） | design spec §5.1（声明）；legacy1 有实现 | PRIVATE HOW（声明） | 2.0 无；legacy1 | INTENDED_NOT_IMPLEMENTED | 检索不得宣告"已回答"（design spec §4.2） | 高（实现可换） | STRONGLY SUPPORTED |
| LF-07 | Evidence governance | 正式/候选边界、来源准入状态 | （未在 2.0 实现） | AGENTS.md; prompt-charter-audit（dispositions） | DOMAIN/AGENT 意图 | 2.0 无；legacy1 | INTENDED_NOT_IMPLEMENTED | 语义由提示词/审计承载 | 高 | STRONGLY SUPPORTED |
| LF-08 | Normative reasoning & binding | 规范理解/适用性/证据绑定 | （未在 2.0 实现） | design spec §5.1/§4.2 | DOMAIN 意图 | 2.0 无 | INTENDED_NOT_IMPLEMENTED | 三分离判断未实现 | 高 | STRONGLY SUPPORTED |
| LF-09 | Bounded ReAct network supplement | 本地缺口/用户验证时网络补证（候选化） | （未在 2.0 实现） | config.py network_mode（无消费点）；AGENTS.md | AGENT + PRIVATE HOW | 2.0 配置仅声明 | INTENDED_NOT_IMPLEMENTED | 声明-实现矛盾 | 高 | WEAKLY SUPPORTED |
| LF-10 | Answer composition / AnswerDocument | 单一答案源、状态受控 | （未在 2.0 实现） | AGENTS.md; design spec §4.3 | AGENT 行为 | 2.0 无 | INTENDED_NOT_IMPLEMENTED | — | 高 | STRONGLY SUPPORTED |
| LF-11 | Export service | DOCX/PDF（正式）/Excel/JSON（调试） | （未在 2.0 实现） | design spec §2.2; requirements.lock（reportlab） | AGENT + PRIVATE HOW | 2.0 无实现 | INTENDED_NOT_IMPLEMENTED | 依赖存在 | 高 | WEAKLY SUPPORTED |
| LF-12 | Audit & diagnostics | 审计/恢复/导出/交付状态 | （部分） | domain/runs.py（事件）；design spec §5.1 | AGENT | 2.0 部分 | PARTIAL | — | 高 | WEAKLY SUPPORTED |
| LF-13 | Provider boundary | 模型执行边界（超时/schema 校验/身份） | in: ModelRequest; out: ModelResult | providers/base.py; providers/codex.py | RUNTIME 意图（执行语义） | 2.0 providers | IMPLEMENTED | openai_compatible 声明未实现 | 高（provider 可换） | PROVEN |
| LF-14 | Workbench frontend | 浏览器工作台（项目/文档/事实 UI） | in: UI 交互; out: API 调用 | frontend/**; frontend/e2e（passed） | AGENT + PRIVATE HOW | 2.0 frontend | IMPLEMENTED | — | 高 | PROVEN |
| LF-15 | Launcher / service shell | Windows 一键启动/停止/运行时所有权 | in: 脚本; out: 服务 | scripts/*.ps1; tests/integration/test_launcher_scripts.py | PRIVATE HOW | 2.0 scripts | IMPLEMENTED | 端口所有权逻辑 | 高 | PROVEN |

## 盲观察：耦合/混合责任（提取）

- LF-03：领域词汇硬编码于实现（提取器锚词）——实现静默持有领域语义。
- LF-07/08/10：证据治理/适用性/答案语义主要由提示词/设计文档承载，2.0 代码无实现——语义所有权悬空。
- LF-09/13：声明-实现矛盾（network_mode；openai_compatible）。
