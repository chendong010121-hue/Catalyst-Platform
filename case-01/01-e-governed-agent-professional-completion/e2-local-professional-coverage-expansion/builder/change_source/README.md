# BREA — Building Regulation Evidence Agent · v0.3-candidate

CASE 01-E / E2 governed candidate — **Local Professional Coverage Expansion** (E2-AB).

Same governed Agent lineage: `case-01.brea`. New professional implementation Candidate:
**`v0.3-candidate`** (NOT admitted, NOT bound — E2 is not an admission stage).
Parent reference: `case-01.brea @ 0.2-candidate` (E1 accepted baseline, read-only).

## What is new in v0.3 (vs E1 v0.2 baseline)

```text
NEW PROFESSIONAL APPLICABILITY FAMILY
公共建筑防火分区最大允许建筑面积（GB 55037-2022 第4.3.16条，条件规则族）

NEW MECHANISM (reusable, not per-question)
brea/coverage.py — numbered-subitem conditional-rule parser:
  extract full clause incl. 编号子项 -> split items -> extract (条件,数值) rules
  -> match project facts (建筑形式/耐火等级/自动灭火系统) -> bind value
  -> apply modifier (全部设置自动灭火系统 → 面积增加1.0倍) -> verbatim evidence + locator

NEW PROFESSIONAL FACTS (SEAM-01 bounded EXTENDED)
building_form · fire_resistance_rating · auto_extinguishing_system

FAIL-CLOSED BEHAVIOR
排除项（特殊要求/木结构/附建汽车库）→ no_reliable_evidence（明确不适用）
事实缺失 → insufficient_context（无数值）
子项解析失败/无匹配 → no_reliable_evidence（不编造）
```

The mechanism is deterministic, stdlib-only (no LLM / RAG / Web / vector DB). E1
generalized local-query behavior (QMODE-01..04) and T-C01/02/03 professional cases
are preserved. `implementation_metadata` carries `query_mode`/`standard_id`.

## Source layout (E2 changes)

```text
brea/coverage.py    NEW      — numbered-subitem conditional-rule mechanism (PRIVATE HOW)
brea/facts.py       EXTENDED — SEAM-01 new professional facts
brea/runner.py      EXTENDED — fire-compartment family dispatch (reusable mechanism)
brea/identity.py    IMPL-ONLY — version v0.3-candidate
(corpus/evidence/query/applicability/contracts/result/uncertainty/__init__:
 byte-identical to v0.2 unless noted in the E2 change manifest)
```

## Professional boundaries (unchanged)

- Numeric authority stays in the admitted corpus text (OBL-03).
- Evidence retrieval ≠ professional applicability (SEAM-02 boundary preserved).
- Enterprise context remains attribution only (OBL-06).
- Corpus: exactly the two admitted local regulations; raw corpus never committed.

See `method/P01..P06_E2_*.md`, `professional/E2_PROFESSIONAL_COVERAGE_SELECTION_V0.1.md`,
`change/E2_CHANGE_IMPACT_REVIEW_V0.1.md`, `evaluation/E2_EVALUATION_CONTRACT_V0.1.md`
for the governed E2-AB trace. Specific independent benchmark cases are NOT created in
E2-AB (they belong to E2-C, after Freeze Review + new authorization).
