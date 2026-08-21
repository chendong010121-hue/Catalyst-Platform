# UNDERSTANDING UNCERTAINTIES — V0.1（BLIND · D0）

> 盲扫中的未知/冲突/不确定。不静默调和冲突（§7）。

| UID | 不确定/冲突 | 盲证据 | 处置 |
|---|---|---|---|
| UN-01 | `network_mode`（off/missing_only/verify_requested）声明存在但未发现消费点 | config.py | CONTRADICTED（声明 vs 未消费）；对照阶段核实 |
| UN-02 | `openai_compatible` provider 声明存在但无实现类 | config.py; providers/（仅 base/codex） | CONTRADICTED；实现=仅 Codex |
| UN-03 | 证据治理/适用性/答案语义所有权：2.0 无实现，legacy1 有；提示词审计承载规则 | prompt-charter-audit; design spec | 所有权悬空；对照阶段核实 |
| UN-04 | 语料/检索跨工作区依赖（2.0 无 data/；legacy1 有 index.sqlite/wiki/OCR） | 工作区清单 | 依赖边界未定；对照阶段核实 |
| UN-05 | 打包/一键启动：脚本与构建声明存在，打包产物未见 | scripts/*.ps1; pyproject build extra | PARTIAL 证据 |
| UN-06 | 评价状态：golden 语料冻结待裁决（16/174 断言已核验），评价实现未见 | golden-corpus-audit | 验收未就绪 |
| UN-07 | AnswerDocument/导出：意图+依赖（reportlab）存在，实现未见 | AGENTS.md; design spec §2.2; requirements.lock | 意图 vs 实现分离 |
| UN-08 | 项目事实词汇完整范围未知（锚词为样本） | facts/extractor.py | 范围未知 |
| UN-09 | approved Agent/version 机制未见（Enterprise 层） | （无证据） | UNKNOWN（不编造） |

## 盲结论

- 无任何恢复主张以"当前会话重述要求"为证据源（S-U6 未触发）。
- 冲突（UN-01/02）如实保留，未静默调和。
