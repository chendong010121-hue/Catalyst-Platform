# BREA — Building Regulation Evidence Agent · v0.1-candidate

> CASE 01 Governed Candidate（CASE 01-C 生成）。由最小 Case-scoped Builder 依据已接受
> `BUILDER_CONSUMABLE_DEFINITION_V0.1.md` 生成；本目录为生成产物（生成痕迹见
> `../builder/BUILDER_OUTPUT_MANIFEST_V0.1.json` 与 `BUILDER_RUN_REPORT_V0.1.md`）。

## Identity / Purpose

```text
ID      BREA — Building Regulation Evidence Agent
VERSION v0.1-candidate
STATE   CASE 01 Governed Candidate
DOMAIN  Building Regulation / Engineering Construction Standards — architecture_pre_design
```

专业目的：使用项目上下文，为建筑方案/初步设计工作提供可靠、适用、可追溯的建筑工程规范证据，并在可靠证据不可用时显式返回不确定性或 fail-closed 结果。
（独立于 Catalyst；不含"测试 Catalyst / prove Platform / prove Runtime"。）

## Functional decomposition（FN-01..FN-11）

| FN | 函数 | 实现位置 | 治理状态 |
|---|---|---|---|
| FN-01 | Question & Context Intake | brea/runner.py | DECLARED FUNCTION BOUNDARY |
| FN-02 | Professional Fact Normalization | brea/facts.py | **SEAM-01** |
| FN-03 | Regulation Applicability Resolution | brea/applicability.py | **SEAM-02** |
| FN-04 | Evidence Locating & Extraction | brea/evidence.py | **SEAM-03** |
| FN-05 | Evidence Binding & Numeric Safety | brea/evidence.py | **SEAM-03** |
| FN-06 | Uncertainty & Fail-Closed Decision | brea/uncertainty.py | DECLARED FUNCTION BOUNDARY |
| FN-07 | Result Composition & Attribution | brea/result.py | DECLARED FUNCTION BOUNDARY |
| FN-08 | Artifact & Provenance Preservation | brea/evidence.py | **SEAM-03** |
| FN-09 | Corpus Access & Parsing | brea/corpus.py | PRIVATE IMPLEMENTATION |
| FN-10 | Provider & Execution Plumbing | （deferred，未实现） | PRIVATE / DEFERRED |
| FN-11 | Local Runner / Service Shell | brea/runner.py | PRIVATE / DEFERRED |

## Run

```powershell
# from candidate/brea-v0.1
python -m brea.runner --case T-C01            # whole-agent formation case
python -m brea.runner --case T-C02
python -m brea.runner --case T-C03
python -m brea.runner --case T-C01 --out ../../evidence/CASE_RESULTS/T-C01_result.json   # write evidence JSON
python tests/run_all.py                        # all structural + seam + whole-agent tests
```

## Corpus

- 通过 `case-01/01-b-governed-agent-definition/evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md` 解析已接纳语料位置。
- SHA-256 校验；失配 → fail closed（CorpusIntegrityError）。
- 语料 READ ONLY、不提交；组织资产=NO；upstream=FORBIDDEN。

## 约束

- 确定性、stdlib-only；无模型依赖（FN-10 deferred）；数值仅来自语料原文。
- 不写 Catalyst 根/Platform/Runtime；不复制语料；不发明架构。
