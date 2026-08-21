# ENTERPRISE INTENT RECOVERY — V0.1（BLIND · D0 · §9）

> 从 Legacy 工作区恢复的**组织特定意图**（与专业 Domain 意图分离）。不编造证据不支持的项（§9）。

| 企业意图类别 | 盲恢复内容 | 盲证据 | 置信 |
|---|---|---|---|
| organization / owner / user / project attribution | **project_id 归属**：一切业务数据归属一个项目；项目级隔离（跨项目 404）；**无 org/user 归属字段** | design spec §5.1（Project Service）；domain/projects.py；phase-2-report（隔离） | PROVEN |
| data admission constraints（数据接入约束） | 本地规范优先；网络仅在本地证据缺口或用户显式验证请求时触发；网络材料必须候选化后经受治理晋升 | AGENTS.md；design spec §4.1 | STRONGLY SUPPORTED |
| network access constraints（网络约束） | 本地不依赖互联网即可完成分析；网络按策略（network_mode）受限 | design spec §2.2；config.py | STRONGLY SUPPORTED |
| source trust rules（来源信任规则） | 正式来源身份需确定性准入与指纹校验（文件 SHA、来源坐标）；引用必须真实存在 | documents/_source.py；AGENTS.md；prompt-charter-audit | PROVEN |
| human review expectations（人工审查期望） | 事实确认强制（用户确认前不得用于分析）；发布验收需人工审查 + 逐组件审核，非仅自动总分 | AGENTS.md（confirm facts）；golden-corpus-audit（三层比较、人工裁决） | STRONGLY SUPPORTED |
| project persistence（项目持久化） | 项目记录 + 项目目录 + SQLite 持久化；重启后项目/事实隔离保持 | storage/schema.py；phase-2-report（跨重启隔离 e2e） | PROVEN |
| memory / retention expectations（记忆/保留期望） | 事实修订不可变、历史保留（rejected/superseded 可见）；append-only 事件 | domain/facts.py；storage/schema.py | PROVEN |
| approved Agent/version expectations（受控版本期望） | 无显式 approved-version 机制（盲证据未见） | — | UNKNOWN |
| organization-specific policy / risk / workflow meaning | 部分以"约束治理/减法门禁"体现（约束需不变量+测试+删除条件）；发布阻断错误清单（错误地域/编造条文/跨项目污染等） | design spec §4.5；golden-corpus-audit | STRONGLY SUPPORTED |

## 盲观察

- Enterprise 意图的**核心可实证部分=项目归属/隔离/持久化**（代码+报告实据）。
- 网络/来源信任/人工审查等企业约束主要由**策略文档（AGENTS/design）**承载——实现侧部分落地（来源指纹已实现；网络/晋升机制未实现）。
- 组织归属（org/user）在 2.0 数据模型中**缺失**（仅 project）。
