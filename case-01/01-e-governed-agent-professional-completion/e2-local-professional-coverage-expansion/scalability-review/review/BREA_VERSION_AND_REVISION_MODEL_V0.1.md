# BREA VERSION & REVISION MODEL — V0.1

> Review Contract §17. Distinguish Agent Version / Corpus Revision / Index Revision /
> Domain Schema Version / Evaluation Version. Key principle under review:
> **Agent Evolution != Knowledge Evolution**.

## Five identities

| Identity | What it is | Example | Change trigger |
|---|---|---|---|
| AGENT VERSION | 行为/代码/推理能力 | v0.1-candidate / v0.2-candidate / v0.3-candidate | 代码或推理能力变化（Candidate N+1） |
| CORPUS REVISION | 哪些源文档/版本被接纳 | GB55037-2022（SHA 2a217dea…）/ DBJ33T1021-2023 | 源 admission / edition 替换 |
| INDEX REVISION | 语料修订的检索表示 | E1/E2 运行时解析（当前无持久索引） | ingest / reindex |
| DOMAIN SCHEMA VERSION | Regulation 数据/专业事实/契约结构 | FIRE_COMPARTMENT 规则表（v0.3 内嵌） | RegulationUnit 字段增删（本 Review 提案） |
| EVALUATION VERSION | benchmark / gold / evaluation contract 修订 | E1_BENCHMARK / E2_EVALUATION_CONTRACT | 评估契约修订 |

## Corpus revision without Agent version change — 目标例子

```text
EXAMPLE 1 — 新增同一结构类规范（unseen）
  corpus revision: +新规范（admission + ingest + index）
  agent version:   不变
  要求：检索/定位/验证面零 Agent 代码（§25 proof target）

EXAMPLE 2 — 已知规范 edition 替换
  corpus revision: GB55037-2022 → 新版
  index revision:  reindex
  agent version:   不变（若结构类不变；数值/条款变化由 corpus+index 承载）
  要求：版本/effective-status 语义存在于 CORPUS/INDEX 层

EXAMPLE 3 — 新自然语言措辞
  index revision: 更新检索表示（如需）
  agent version:   不变（E1 已证）
```

## Candidate N+1 legitimately required — 目标例子

```text
EXAMPLE 4 — 新专业推理原语
  domain schema: 需新增 condition/exception 类型
  agent version: v0.4-candidate（新能力）
  触发：新 reasoning primitive / 新 verification obligation / 高风险安全契约

EXAMPLE 5 — 新权威/冲突语义
  domain schema: 需新增 authority-conflict 语义
  agent version: Candidate N+1
  触发：跨来源冲突 / edition 冲突处理策略
```

## 原则检验（Agent Evolution != Knowledge Evolution）

```text
支持证据：
  E1：新条款/新表格/新措辞 = knowledge change，Agent 未变（v0.2 内）
  E2：新专业家族 = 新能力，Agent 变（v0.3）
  → 区分在 E1/E2 已被实证：knowledge change 未变 Agent（E1 内部），
    capability change 变了 Agent（E1→E2）

当前缺口：
  v0.3 把 FIRE_COMPARTMENT 规则表写进 Python 模块（coverage.py）——
  即 knowledge 与 code 混合 → "corpus/domain-schema change"与"agent change"边界模糊
  本 Review 的 RegulationUnit 提案正是为了把 knowledge 移出 Agent 代码，
  使该区分稳定成立（H-03/H-07 收窄结论）
```

## 决策

```text
VERSION & REVISION MODEL DECISION
采纳五身份分离（Agent / Corpus / Index / Domain Schema / Evaluation）。
Agent Evolution != Knowledge Evolution 作为架构不变量：
  knowledge change（corpus/index/部分 domain schema）默认不应触发 Agent 版本变更；
  capability change（推理原语/验证义务/权威语义）应触发 Candidate N+1。
实现含义：knowledge 从 Python 移入数据（RegulationUnit），版本/有效状态入 corpus/index 层。
```

## 未决（交实验）

```text
F-EXP-01 将实证"unseen source revision 不触发 Agent 版本变更"是否成立；
若不能，该不变量需降级或重新定义。
```
