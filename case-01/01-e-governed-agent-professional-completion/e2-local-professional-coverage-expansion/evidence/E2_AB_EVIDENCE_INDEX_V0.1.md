# CASE 01-E / E2-AB — EVIDENCE INDEX — V0.1

> Governed evidence index for the E2-AB phase (Professional Coverage Selection +
> Method P-01..P-06 + Candidate Freeze). All paths relative to
> `case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/`.

## Authorization & Contract

| Item | Value |
|---|---|
| E2-AB authorization | `E2_AB_AUTHORIZATION_RECORD_V0.1.yaml` — **granted** |
| Stage spec | `CASE_01_E_E2_LOCAL_PROFESSIONAL_COVERAGE_EXPANSION_V0.1_STAGE_SPEC.md` (commit `5ffa497`) |
| Stage plan | `CASE_01_E_E2_LOCAL_PROFESSIONAL_COVERAGE_EXPANSION_V0.1_STAGE_PLAN.md` (commit `b0ddce6`) |
| Accepted Construction Method | `case-01/methods/CATALYST_GOVERNED_AGENT_CONSTRUCTION_METHOD_V0.1_ACCEPTED.md` (commit `a5e7b0b`) |

## Method artifacts (P-01..P-06)

| File | Status |
|---|---|
| `method/P01_E2_PROBLEM_RECORD_V0.1.md` | COMPLETE（技术无关问题记录） |
| `method/P02_E2_MECHANISM_ABSTRACTION_V0.1.md` | COMPLETE（冻结隔离 + 条件规则机制） |
| `method/P03_E2_ASSUMPTION_REGISTER_V0.1.md` | COMPLETE（12 假设分类） |
| `method/P04_E2_RESPONSIBILITY_CLASSIFICATION_V0.1.md` | COMPLETE（9 类责任映射） |
| `method/P05_E2_CATALYST_COMPATIBILITY_REVIEW_V0.1.md` | COMPLETE（两轴判定） |
| `method/P06_E2_CATALYST_NATIVE_RECONSTRUCTION_V0.1.md` | COMPLETE（Catalyst-native 重建） |

## Professional selection & capability

| File | Status |
|---|---|
| `professional/E2_PROFESSIONAL_COVERAGE_SELECTION_V0.1.md` | 选择 GB 4.3.16 防火分区家族（SOURCE PATH A） |
| `professional/E2_IMPLEMENTATION_CAPABILITY_SELECTION_V0.1.md` | 确定性编号子项解析器；LLM/RAG 拒绝 |
| （`E2_SOURCE_ADMISSION_RECORD` 不需要：SOURCE PATH A，无新源） | — |

## Change governance

| File | Status |
|---|---|
| `change/E2_PROFESSIONAL_CHANGE_REQUEST_V0.1.md` | COMPLETE |
| `change/E2_CHANGE_IMPACT_REVIEW_V0.1.md` | COMPLETE（bounded EXTENDED 允许） |
| `change/E2_CANDIDATE_CHANGE_MANIFEST_V0.1.json` | 生成（builder 输出） |

## Builder & Candidate

| File | Status |
|---|---|
| `builder/run_e2_builder.py` | 复用 E1 机制（v0.2→v0.3 overlay） |
| `builder/change_source/**` | 授权变更模块（coverage/facts/runner/identity/README） |
| `builder/E2_BUILDER_RUN_REPORT_V0.1.md` | 5 changed / 17 unchanged byte-identical, import probe PASS |
| `candidate/brea-v0.3/**` | v0.3 Candidate（case-01.brea @ 0.3-candidate, NOT admitted/bound） |
| candidate self-check | **15/15 PASS**（v0.1/v0.2 测试回归面） |

## Evaluation Contract（冻结前，无具体 cases）

| File | Status |
|---|---|
| `evaluation/E2_EVALUATION_CONTRACT_V0.1.md` | GENERATED（能力级；**不含未来 benchmark cases**） |
| `evaluation/benchmark/` | **不存在**（E2-C 冻结后创建） |

## Freeze

| File | Value |
|---|---|
| `freeze/E2_V0_3_CANDIDATE_FREEZE_RECORD_V0.1.json` | candidate_tree_sha256=`37bb4864a9dd39812d9d77c24bb48d9b7abe2403c2ed6f4df31d2e7db847fa7b` |
| `freeze/E2_V0_3_CANDIDATE_FREEZE_REPORT_V0.1.md` | freeze report |

## Evidence

| File | Result |
|---|---|
| `evidence/E2_AB_CONSTRUCTION_TEST_RESULTS.log.txt` | **AB-T01..T22: 22/22 PASS** |
| `evidence/E2_AB_REGRESSION_RESULTS.log.txt` | **15/15 PASS** |
| `evidence/E2_AB_FN_SEAM_OBL_CONFORMANCE_V0.1.md` | PASS（FN/SEAM/OBL 保持） |
| `evidence/E2_AB_PLATFORM_COMPATIBILITY_CHECK_V0.1.md` | PASS（Platform/Runtime 不变） |
| `evidence/E2_AB_REPOSITORY_INTEGRITY_V0.1.md` | PASS（无污染；main 不变） |

## Review

| File | Role |
|---|---|
| `review/CASE_01_E_E2_AB_CANDIDATE_FREEZE_REPORT_V0.1.md` | Gate-1 候选冻结报告 |

## Key identifiers

```text
parent reference : case-01.brea @ 0.2-candidate（E1 已接受基线，read-only）
frozen candidate : case-01.brea @ 0.3-candidate
tree sha256      : 37bb4864a9dd39812d9d77c24bb48d9b7abe2403c2ed6f4df31d2e7db847fa7b
professional src : GB 55037-2022 §4.3.16（语料 SHA 2a217dea…）
method ref       : a5e7b0b9384f8108d5af22bfe9fea317d8e60cee
```

## Protected Boundaries

`platform_standard/**` · `agent_runtime/**` · `enterprise_extensions/**` · root tests · CI ·
admitted v0.1 · E1 v0.2 baseline · D2/E1 accepted evidence · raw corpus（never committed）·
main（`5874be11…`）
