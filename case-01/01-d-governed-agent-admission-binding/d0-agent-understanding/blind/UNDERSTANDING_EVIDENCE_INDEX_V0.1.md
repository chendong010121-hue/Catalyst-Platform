# UNDERSTANDING EVIDENCE INDEX — V0.1（BLIND · D0）

> 盲证据索引。每条恢复主张可回溯到 Legacy 2.0 工作区文件。路径相对 `E:\试验场地\规范查询agent2.0`。

| BLD-E | 支持的主张 | 证据位置（legacy 2.0 工作区） | 置信 |
|---|---|---|---|
| BLD-E01 | 迁移治理先行；legacy1 只读参考 | README.md:3-5; docs/migration/source-assets.yaml | PROVEN |
| BLD-E02 | 产品=本地建筑规范分析 Agent；两类核心任务 | docs/superpowers/specs/...design.md §1/§2（1103 行规格） | STRONGLY SUPPORTED |
| BLD-E03 | 交付目标（Windows 一键/Workbench/DOCX-PDF/离线优先/双 provider） | design spec §2.2; AGENTS.md | STRONGLY SUPPORTED |
| BLD-E04 | 业务范围（方案/初设）与排除（结构/HVAC/BIM 等） | design spec §3.1/3.2/3.3; AGENTS.md | STRONGLY SUPPORTED |
| BLD-E05 | LLM/harness 职责边界；三分离判断；单一事实来源 | design spec §4.1/4.2/4.3 | STRONGLY SUPPORTED |
| BLD-E06 | 保留架构级策略（架构范围/已确认事实保护/正式-候选边界/不编造/引用可追溯） | docs/migration/prompt-charter-audit.md（retain_in_charter 行） | STRONGLY SUPPORTED |
| BLD-E07 | 文档摄入/保真/指纹/坐标实现 | src/standards_agent/documents/*; domain/documents.py | PROVEN |
| BLD-E08 | 事实提取/修订/确认/不可变实现 | src/standards_agent/facts/*; domain/facts.py; api/facts.py | PROVEN |
| BLD-E09 | 领域词汇硬编码于提取器 | facts/extractor.py `_FACT_ANCHORS`/`_STRUCTURAL_FACT_HEADINGS` | PROVEN |
| BLD-E10 | 项目隔离/持久化实现 | domain/projects.py; storage/schema.py; docs/migration/phase-2-report.md（跨重启隔离 e2e 2 passed） | PROVEN |
| BLD-E11 | 运行事件 append-only | domain/runs.py; storage/schema.py（触发器） | PROVEN |
| BLD-E12 | provider 边界实现（codex；openai_compatible 声明未实现） | providers/{base,codex}.py; config.py | PROVEN（codex）/STRONGLY（缺口） |
| BLD-E13 | network_mode 声明无消费点 | config.py; （无引用点） | WEAKLY SUPPORTED |
| BLD-E14 | 检索/证据治理/答案/导出/网络/评价未在 2.0 实现（意图声明） | design spec §5.1；2.0 无对应模块 | STRONGLY SUPPORTED |
| BLD-E15 | 语料/检索在 legacy1（跨工作区依赖） | ASSET_INVENTORY（2.0 无 data/）；docs/migration（迁移边界） | STRONGLY SUPPORTED |
| BLD-E16 | 评价资产：60 题 golden（VG/L/N）冻结待裁决；三层比较；阻断错误 | docs/migration/2026-08-14-golden-corpus-and-subagent-preflight-audit.md | STRONGLY SUPPORTED |
| BLD-E17 | 前端 Workbench 实现 + e2e 通过 | frontend/**; test-results/.last-run.json | PROVEN |
| BLD-E18 | 启动/运行时所有权脚本 | scripts/*.ps1; tests/integration/test_launcher_scripts.py | PROVEN |
| BLD-E19 | 事实提取收敛修复史（git） | .git log（agent2-delivery；abbcaf1 等） | PROVEN |
| BLD-E20 | 无 org/user 归属字段（仅 project） | domain/projects.py（Project/Location） | PROVEN |

## 置信分布（盲）

PROVEN=10（E01,07,08,09,10,11,12,17,18,19,20→11）· STRONGLY=9 · WEAKLY=2（E13；L11-openai 部分已并入 E12）· UNKNOWN=0。
（精确计数以本索引为准：PROVEN 11 / STRONGLY 8 / WEAKLY 2 / UNKNOWN 0。）
