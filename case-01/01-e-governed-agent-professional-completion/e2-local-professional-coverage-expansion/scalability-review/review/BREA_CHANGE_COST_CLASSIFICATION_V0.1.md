# BREA CHANGE-COST CLASSIFICATION — V0.1

> Review Contract §7. For each future change type classify the expected owner, and
> for each required case state the expected change surface. A strong architecture
> minimizes unnecessary movement to the right side of the list.

## Change-type → owner mapping

| Change type | Expected owner | v0.3 today | Notes |
|---|---|---|---|
| DATA / CORPUS REVISION | data/source admission + ingest | 语料清单（LOCAL_CORPUS_REFERENCE_MANIFEST）只记录身份/SHA；无 ingest 层 | 当前"换语料"=改 manifest + 重跑 |
| INDEX REVISION | index layer | 无持久索引（每次运行解析原文） | v0.2/v0.3 均为运行时 parse-on-demand |
| DOMAIN SCHEMA REVISION | Domain schema / data model | 无独立 schema（coverage.py 内嵌 FIRE_COMPARTMENT 表） | 灰色地带主要来源 |
| CONFIG REVISION | config / rule data | 部分（FIRE_COMPARTMENT 是数据声明） | 但解析/匹配逻辑在 Python |
| PRIVATE HOW CHANGE | implementation | coverage.py/query.py 等 | 合法，不需治理 |
| GOVERNED SEAM CHANGE | SEAM review | SEAM-01/02/03 固定 | 新 seam 未授权 |
| AGENT CANDIDATE CHANGE | Candidate N+1 | 是（E2 新增家族即新候选） | Structural Growth 合法路径 |
| PLATFORM CONTRACT REVIEW | Platform review | 未触发 | 禁止 |

## Required cases → expected change surface

| Case | Ideal owner | v0.3 actual | Gap |
|---|---|---|---|
| add ordinary regulation | DATA（admission+ingest） | 需改 manifest；若结构同类则 E1 检索可用，但专业判定需新代码 | 检索可、判定不可 |
| replace regulation with new edition | DATA + VERSION | 无 version/effective-status 语义；manifest 仅记录 SHA | 缺版本模型 |
| add local standard | DATA + DOMAIN SCHEMA（若新结构） | 同"add ordinary regulation" | 同 |
| upload temporary PDF | DATA（USER CORPUS，长程） | 未授权/无支持 | 长程边界 |
| new table shape | DOMAIN SCHEMA 或 PRIVATE HOW | extract_table 依赖 ncols/caption 约定；新表形可能需解析代码 | 灰色 |
| new appendix structure | DOMAIN SCHEMA 或 PRIVATE HOW | 无附录结构化支持 | 灰色 |
| new applicability reasoning type | STRUCTURAL（Candidate N+1） | 是（防火分区即一例） | 正确归属 |
| new numeric modifier type | DOMAIN SCHEMA（modifier 声明化） | modifier_rule 是数据；但派生轨迹无结构化记录 | PC-04 |
| new source-authority conflict | VERIFICATION / DOMAIN SCHEMA | 无冲突语义 | 长程 |
| controlled Web supplement | 长程设计边界 | 未授权 | 长程 |
| new natural-language paraphrase | INDEX / RETRIEVAL（零代码） | E1 已证（7 未编码查询成功） | 无 |

## 关键观察

```text
1. "检索面"（新条款/新表格/新措辞）在 E1 已实现零代码 —— Normal Growth 的检索部分成立。
2. "判定面"（新专业家族/新条件规则）当前落在 Candidate N+1 —— 部分正确（Structural），
   但同一结构的新实例不应要求新代码（灰色地带）。
3. v0.3 的最大成本风险：DOMAIN SCHEMA 不存在 → 灰色地带只能靠 Python 修补（PC-01..04 即后果）。
4. 版本/权威语义缺失 → "replace regulation with new edition"目前无合法成本路径。
```

## 对架构选择的含义

```text
最小充分架构应把"常见变更"的成本尽量左移：
  add ordinary regulation      → DATA（需 ingest + index + 版本模型）
  new paraphrase              → INDEX（已达成）
  new table/appendix shape    → DOMAIN SCHEMA（需最小 RegulationUnit 化结构）
  new reasoning/numeric type  → DOMAIN SCHEMA + 必要时 Candidate N+1（Structural 合法）

LLM/RAG/密集检索 对上述任一成本条目均不构成必要前置（见 Retrieval/Reasoning 决策）。
```
