# FUNCTION CONFORMANCE — V0.1 (CASE 01-C)

> FN-01..FN-11 实现映射。无一消失；不塌缩为单一 Prompt/类/模块（§7 硬不变量）。
> 依据：`brea/identity.py:BREA_FUNCTION_MAP` + Builder 输出清单 + 测试证据。

| FN | 函数 | 实现位置 | 治理状态 | 测试证据 |
|---|---|---|---|---|
| FN-01 | Question & Context Intake | `brea/runner.py::answer`（入参校验） | DECLARED FUNCTION BOUNDARY | test_cases（三案请求走通） |
| FN-02 | Professional Fact Normalization | `brea/facts.py` | **SEAM-01** | test_seam01_facts PASS |
| FN-03 | Regulation Applicability Resolution | `brea/applicability.py` | **SEAM-02** | test_seam02_applicability PASS |
| FN-04 | Evidence Locating & Extraction | `brea/evidence.py` | **SEAM-03** | test_seam03_evidence PASS |
| FN-05 | Evidence Binding & Numeric Safety | `brea/evidence.py`（assert_verbatim + 数值仅来自语料） | **SEAM-03** | ST-06 PASS；T-C01/02 |
| FN-06 | Uncertainty & Fail-Closed Decision | `brea/uncertainty.py` | DECLARED FUNCTION BOUNDARY | T-C03 PASS |
| FN-07 | Result Composition & Attribution | `brea/result.py` | DECLARED FUNCTION BOUNDARY | T-C01/02/03 结果 JSON |
| FN-08 | Artifact & Provenance Preservation | `brea/evidence.py::write_artifact` + runner | **SEAM-03** | T-C01_bundle/T-C02_bundle |
| FN-09 | Corpus Access & Parsing | `brea/corpus.py` | PRIVATE IMPLEMENTATION | ST-07 PASS |
| FN-10 | Provider & Execution Plumbing | （deferred；无 provider 模块） | PRIVATE / DEFERRED | ST-03 PASS（无 provider） |
| FN-11 | Local Runner / Service Shell | `brea/runner.py`（CLI + `python -m brea.runner`） | PRIVATE / DEFERRED | 三案 CLI 运行 exit 0 |

## 结论

FN-01..FN-11 全部显式映射；依赖方向：FN-01→FN-02→FN-03→FN-04/05/08；FN-06/07 为编排/契约边界；私有 HOW（FN-09/10/11）不持有语义。
