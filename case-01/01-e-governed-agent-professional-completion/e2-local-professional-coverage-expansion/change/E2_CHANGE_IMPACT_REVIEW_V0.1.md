# E2 — CHANGE IMPACT REVIEW — V0.1

> E2-AB §18: classify responsibilities. Only UNCHANGED / bounded EXTENDED /
> implementation changes may proceed; material change triggers STOP (AB-S04/05/06).

## Professional purpose

```text
UNCHANGED
"use project context to provide reliable, applicable, traceable building-regulation evidence…"
防火分区判定是既有目的（provide applicable evidence）内的能力扩展，非目的变更
```

## FN classification

| FN | Class | Rationale |
|---|---|---|
| FN-01 Intake | **EXTENDED** | 识别防火分区控制事项意图（问题触发词族） |
| FN-02 Facts | **EXTENDED** | SEAM-01 新增 3 个专业事实（形式/耐火等级/灭火系统）——E2 证据证明需要（P-01） |
| FN-03 Applicability | **EXTENDED** | SEAM-02 新增防火分区家族判定链（区别于检索） |
| FN-04 Evidence Locating | **EXTENDED** | 编号子项条款定位（4.3.16 子项行定位） |
| FN-05 Evidence Binding | **EXTENDED** | 子项数值绑定 + 自动灭火修正 + 逐字断言 |
| FN-06 Uncertainty | **UNCHANGED** | 沿用 decide()（fail closed / uncertainty 语义不变） |
| FN-07 Result | **UNCHANGED** | 结果契约 7 字段不变；query_mode/standard_id 沿用 |
| FN-08 Artifact | **UNCHANGED** | 证据束机制沿用（可复用） |
| FN-09 Corpus | **EXTENDED** | 编号子项解析器（`coverage.py` 私有模块） |
| FN-10 Provider | **UNCHANGED** | 无 provider 工作 |
| FN-11 Runner | **EXTENDED** | 防火分区家族分发（复用机制，非 per-question 分支） |

## SEAM classification

| SEAM | Class | Rationale |
|---|---|---|
| SEAM-01 Professional Project Facts | **EXTENDED** | 新增事实词汇：building_form / fire_resistance_rating / auto_extinguishing_system（E2 证据证明必需） |
| SEAM-02 Regulation Applicability | **EXTENDED** | 新增防火分区家族适用性链（可观察，Domain 权威） |
| SEAM-03 Regulation Evidence | **EXTENDED** | 编号子项证据定位/绑定扩展 |

## OBL classification

| OBL | Class | Rationale |
|---|---|---|
| OBL-01 | **UNCHANGED** | 直接条文专业回答仍然提供（4.3.16 判定=直接条文适用） |
| OBL-02 | **UNCHANGED** | 适用性链条保持可观察（家族判定链输出） |
| OBL-03 | **UNCHANGED** | 数值权威仍在语料原文；无实现生成数值 |
| OBL-04 | **UNCHANGED** | 不编造：事实不足/排除项/解析失败 → fail closed |
| OBL-05 | **UNCHANGED** | 每个接受回答含 source+locator+逐字内容 |
| OBL-06 | **UNCHANGED** | 企业上下文保持 attribution only |

## Domain / Enterprise / Agent / HOW / Evaluation

```text
Domain semantics  : EXTENDED（防火分区条件规则族——来自条文，Domain 权威）
Enterprise        : UNCHANGED（attribution only；无组织级策略）
Agent behavior    : EXTENDED（事实→子项→数值绑定行为）
Implementation HOW: EXTENDED（coverage.py 私有解析器；FN-09 内）
Evaluation        : EXTENDED（Evaluation Contract 先于冻结；benchmark 后建）
```

## 触发检查

```text
AB-S04 professional purpose material change : NO
AB-S05 new obligation necessary             : NO
AB-S06 new Governed Seam structurally needed: NO
→ 允许在既有责任内进行 bounded EXTENDED 实施
```

## 结论

```text
PURPOSE UNCHANGED · OBL-01..06 UNCHANGED · SEAM-01/02/03 bounded EXTENDED ·
FN-01/02/03/04/05/09/11 bounded EXTENDED · FN-06/07/08/10 UNCHANGED ·
无 material change → 可进入 E2-B 候选构建
```
