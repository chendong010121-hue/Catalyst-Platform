# E2 — AB FN / SEAM / OBL CONFORMANCE — V0.1

> Stage Spec §25 AB-T10/11/12 + §15 gate. v0.3 Candidate keeps the accepted
> FN-01..11 / SEAM-01..03 / OBL-01..06 decomposition; E2 only extends bounded
> semantics inside accepted responsibilities (no material change).

## FN conformance (AB-T10)

| FN | v0.3 state | E2 class |
|---|---|---|
| FN-01 Question & Context Intake | present | EXTENDED（防火分区控制事项识别） |
| FN-02 Professional Fact Normalization | present | EXTENDED（SEAM-01 新增 3 事实） |
| FN-03 Regulation Applicability Resolution | present | EXTENDED（SEAM-02 防火分区家族） |
| FN-04 Evidence Locating & Extraction | present | EXTENDED（coverage 子项定位） |
| FN-05 Evidence Binding & Numeric Safety | present | EXTENDED（子项数值绑定） |
| FN-06 Uncertainty & Fail-Closed Decision | present | UNCHANGED |
| FN-07 Result Composition & Attribution | present | UNCHANGED（7 字段契约不变） |
| FN-08 Artifact & Provenance Preservation | present | UNCHANGED |
| FN-09 Corpus Access & Parsing | present | EXTENDED（coverage.py 解析器） |
| FN-10 Provider & Execution Plumbing | present | UNCHANGED（PRIVATE/DEFERRED） |
| FN-11 Local Runner / Service Shell | present | EXTENDED（家族分发） |

**AB-T10: PASS** — `sorted(BREA_FUNCTION_MAP) == FN-01..11`.

## SEAM conformance (AB-T11)

| SEAM | v0.3 state | E2 class |
|---|---|---|
| SEAM-01 Professional Project Facts | present | EXTENDED（新增 building_form / fire_resistance_rating / auto_extinguishing_system） |
| SEAM-02 Regulation Applicability | present | EXTENDED（防火分区家族判定链；检索≠适用性保持） |
| SEAM-03 Regulation Evidence | present | EXTENDED（编号子项证据定位/绑定） |

**AB-T11: PASS** — `set(SEAM_MAP) == {SEAM-01, SEAM-02, SEAM-03}`; no new seam
(AB-S06 未触发; P-05 AXIS A = PRIVATE HOW / 既有 seam 扩展).

## OBL conformance (AB-T12)

| OBL | v0.3 evidence |
|---|---|
| OBL-01 | 防火分区判定=直接条文专业回答（4.3.16 子项绑定） |
| OBL-02 | 适用性链条可观察（conclusion 含"判定链"说明） |
| OBL-03 | 数值权威仍在语料原文（subitem value 从原文解析；无实现生成数值） |
| OBL-04 | 事实缺失/排除项/解析失败 → fail closed（AB-T13 case4/5） |
| OBL-05 | 每个接受回答含 source+locator+逐字内容（verbatim 断言通过） |
| OBL-06 | 企业上下文 attribution only（回归 ST-05 PASS） |

**AB-T12: PASS** — `sorted(OBLIGATIONS) == OBL-01..06`.

## §15 gate conclusion

```text
PROFESSIONAL PURPOSE CHANGE : NO
NEW OBLIGATION              : NO
NEW GOVERNED SEAM           : NO
FN / SEAM / OBL REMOVAL     : NO
→ 允许 bounded EXTENDED 实施（不触发设计评审）
```
