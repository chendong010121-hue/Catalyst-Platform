# BREA REGULATION DATA MODEL DECISION — V0.1

> Review Contract §13. Decide: chunks+metadata only? lightweight RegulationUnit?
> structured Condition/Exception/Numeric fields? Which structures are universal
> enough to justify schema? Which should remain extracted on demand?
> Default: MINIMUM STRUCTURE THAT SUPPORTS THE CONTRACT.

## Questions and answers

| Question | Answer | Evidence |
|---|---|---|
| Do we need only chunks + metadata? | **NO** — 不足以支撑专业契约 | PC-01（正向 scope 缺失）、PC-02（zone 区分缺失）、PC-04（派生数值轨迹缺失）；E2 冻结缺陷证据 |
| Do we need a lightweight RegulationUnit? | **YES（最小）** | 需要结构化承载 source/edition/locator/scope/conditions/exceptions/numerics 才能满足 PC-01..07 |
| Do we need structured Condition / Exception / Numeric fields? | **YES（有界字段集）** | PC-02 需要 condition 分解（设备房 vs 其他区域）；PC-04 需要 numeric operands/modifiers/derivation；PC-01 需要 scope/exceptions 正向+负向 |
| Which structures are universal enough to justify schema? | source identity / edition+effective status / jurisdiction / locator / unit type / scope+exclusions / condition→value rules / numeric operands+modifiers / derivation trace / raw evidence+source SHA（下表） | 三类家族（条文直接/条件规则/表格规则）与 4.3.16 缺陷共同指向这些字段 |
| Which structures should remain extracted on demand? | 跨引用解析、词汇表、提示性文本、非规范性注释、URL/网络元数据 | 无需求证据；避免过度结构化 |

## 最小 RegulationUnit 提案（Candidate，非实现）

```text
RegulationUnit {
  source_id           // GB55037-2022 / DBJ33T1021-2023
  edition             // 2022 / 2023-09-28（含 effective status）
  jurisdiction        // 全国 / 浙江省
  unit_type           // clause | numbered_subitem | table | table_row | scope_note
  locator             // 条款号 / 表格号 / 行 / page / 本地行
  subject             // control item（防火分区 / 防火间距 / 配建指标 …）
  scope_conditions    // 正向适用条件（如"公共建筑"）[PC-01]
  exceptions          // 排除项（特殊要求/木结构/附建汽车库）[PC-01]
  conditions          // 条件→值规则列表（如 高层→1500；设备房→1000）[PC-02]
  numeric_operands    // 规则值（1500/2500/1200/600/1000/500）
  numeric_modifiers   // 修正规则（全部自动灭火 → 增加1.0倍）[PC-04]
  derivation_trace    // operand + modifier + formula + result 的结构化记录 [PC-04]
  cross_references    // 可选（表引用/条款引用），按需抽取
  raw_evidence        // 逐字原文（verbatim 断言源）
  source_sha256       // 来源指纹
}
```

## 明确不建（避免过度设计）

```text
- 不建通用监管本体/全量法规知识图（Review Contract §13 禁止）
- 不把跨引用/提示文本/非规范注释结构化（按需抽取）
- 不引入 LLM 参与结构化（确定性解析 + 验证）
```

## 决策

```text
REGULATION DATA MODEL DECISION
采用"轻量 RegulationUnit（上表字段集）"作为 Regulation IR 的最小形态。
驱动证据：PC-01/02/04 + Change-Cost（new table/appendix shape → DOMAIN SCHEMA）。
深度边界：仅含支撑 PC-01..07 与检索/引用契约的字段；其余按需抽取。
验证要求：每字段须有来源（原文 locator/行号），raw_evidence 必须 verbatim。
```

## 未决（交实验）

```text
精确字段集的最终确认需要 F-EXP-03（raw chunk vs 最小 IR 对照，覆盖 5 种代表规则形式：
直接条文 / 条件编号规则 / 表格规则 / 例外排除 / 派生数值修正）。
本决策给出方向性最小集，F-EXP-03 可增删字段。
```
