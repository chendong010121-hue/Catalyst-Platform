# BLIND VS CASE 01-A COMPARISON — V0.1（D0 · D0-B）

> 冻结后对比：盲理解（blind/）vs 01-A 已接受证据（catalyst-local-lab/case-01/01-a-legacy-assessment/**）。目的=比较，非重写。

## 1. 产品目的

- 盲：本地建筑规范分析 Agent（两类任务；方案/初设；离线优先；证据可追溯）。
- 01-A（O-2/O-6）：2.0=文档摄入→事实提取/确认前段；检索/证据/答案未迁移（legacy1）；语料真值=本地 OCR。
- **一致性：高**——盲恢复的产品意图与 01-A 的"未完成迁移"判断吻合；盲独立发现"检索/证据/答案为意图声明"。

## 2. 资产/实现清单

- 盲（ASSET_AND_IMPLEMENTATION_INVENTORY）：模块/文档/测试/配置/脚本/git 史逐项列出（101 文件）。
- 01-A（O-3 LEGACY_ASSET_CLASSIFICATION）：A-01..A-22 分类（REUSE 0 / RWA 8 / REF 12 / REJECT 0 / UNKNOWN 3；含 legacy1 语料/索引）。
- 一致性：高——盲清单覆盖 2.0 全部模块；01-A 额外覆盖 legacy1（语料/索引/旧引擎）与分类；盲未做分类（§8 禁止用 BREA 模板，故不分类）。

## 3. 责任恢复

| 盲（RESPONSIBILITY_RECOVERY） | 01-A（O-4 RESPONSIBILITY_DECOMPOSITION） | 一致 |
|---|---|---|
| 领域词汇硬编码于提取器（LF-03） | R-02 领域词汇硬编码（HIDDEN SEMANTIC OWNERSHIP） | ✓ |
| 证据治理/适用性/答案语义所有权悬空（2.0 无实现） | R-04/R-05 适用性/证据语义悬空（legacy1 实现） | ✓ |
| 无 org/user 归属（仅 project） | R-06/F-01 企业归属缺失（隔离≠归属） | ✓ |
| network_mode 声明无消费点（UN-01） | F-05 network_mode 消费点未证 | ✓ |
| openai_compatible 声明未实现（UN-02） | F-03 openai_compatible 声明未实现 | ✓ |
| 执行语义=Runtime 责任（超时/预算） | R-08 执行语义=Runtime | ✓ |
| 提示词/审计承载领域规则 | R-12 提示词即治理（混合/隐藏） | ✓ |
| 语料跨工作区依赖（legacy1） | EV-22/03 语料/索引在 legacy1 | ✓ |

## 4. 未知/冲突

- 盲 UN-01..09 与 01-A F-03/04/05/06/09 及 O-6 "must-not-assume" 高度重叠。
- 差异：01-A 另有 A-15（语料接纳=UNKNOWN→F-08 LOCAL PILOT ADMITTED）、A-16/A-19（索引/快照 UNKNOWN）——盲仅记"跨工作区依赖"，未评估接纳状态（盲不做资产分类，合理）。

## 5. 盲未覆盖/01-A 独有

- 01-A 的 corpus/索引清单（index.sqlite/wiki/knowledge_snapshot 大小/格式）——盲未深挖（2.0 工作区外）。
- 01-A 的运行观察（受控 305 passed）——盲仅引用 2.0 自身 test-results/.last-run.json 与 phase 报告。

## 结论

盲理解与 01-A 在目的/资产/责任/未知四维**实质一致**；无矛盾。盲未预置任何 01-A 结论（冻结前未读取）。
