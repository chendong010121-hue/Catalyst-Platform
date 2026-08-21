# OBLIGATION CONFORMANCE — V0.1 (CASE 01-C)

> OBL-01..06 符合证据。OBL-03 数值安全=专业义务；源码字面量扫描仅为本地形成/构建验证（B-01 纪律，非公共语义）。

| OBL | 义务 | 形成证据 | 状态 |
|---|---|---|---|
| OBL-01 | Verbatim evidence traceability | T-C01/T-C02：`evidence_content` 逐字（verbatim 断言 assert_verbatim PASS）；`T-C01_result.json`/`T-C02_result.json` | PASS |
| OBL-02 | Applicability determination | `applicability_for_question` 适用链；T-C02 结论含"表5.0.1（…→级别）→表5.0.4（行）"；test_seam02 PASS | PASS |
| OBL-03 | Numeric safety — zero unsupported numeric claims | 结论数值仅来自语料解析（T-C01: 50m 出自条文原文；T-C02: 1.1 出自表5.0.4 行）；ST-06 PASS（结论数值均在逐字证据中）；测试不硬编码答案文本 | PASS |
| OBL-04 | Fail-closed uncertainty | T-C03：insufficient_context、结论无数值、缺失事实显式（领域标签）；uncertainty.decide 永不出猜测 | PASS |
| OBL-05 | Source fidelity / provenance | locator（条/表/页/行区间）可复现（T-C01: 第3.1.3条 [page 13] 行 451-454；T-C02: 表5.0.1/5.0.4 行区间）+ 证据束 artifacts | PASS |
| OBL-06 | Minimum enterprise attribution | `implementation_metadata.enterprise_context_attribution`（org/user/project）；ST-05 证明归属改变不影响结论/证据 | PASS |

## 本地构建验证（非 OBL-03 公共语义）

- 源码字面量扫描（`builder` 之外由候选自身 ST-06 承担数值可追溯）；无"义务短语+数值"字面量于候选源码（ST-06/自检日志）。
- 语料哈希失配 fail closed（ST-07 PASS）。

## 义务 → 测试映射（C-03，与 BUILDER_OUTPUT_MANIFEST_V0.1.json 一致）

| OBL | 真实测试/证据引用（Builder 校验存在，BT-08 PASS） |
|---|---|
| OBL-01 | tests/test_cases.py::test_t_c01_direct_clause；tests/test_cases.py::test_t_c02_conditional_table |
| OBL-02 | tests/test_seams.py::test_seam02_applicability；tests/test_cases.py::test_t_c02_conditional_table |
| OBL-03 | tests/test_structural.py::test_st06_numeric_traceability；test_t_c01_direct_clause；test_t_c02_conditional_table |
| OBL-04 | tests/test_cases.py::test_t_c03_fail_closed |
| OBL-05 | test_t_c01_direct_clause；test_t_c02_conditional_table；tests/test_seams.py::test_seam03_evidence |
| OBL-06 | tests/test_structural.py::test_st05_enterprise_orthogonality；test_t_c02_conditional_table |

（修复前 manifest 曾引用不存在的 test_obl_01..06 —— C-03 已修复；本表与 manifest 对账一致。）
