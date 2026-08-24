# BREA VERIFICATION ARCHITECTURE DECISION — V0.1

> Review Contract §16. For each invariant: where enforced, evidence proving
> enforcement, behavior on uncertainty, how tested. Deterministic verification is
> the proven invariant layer (H-08 NOT FALSIFIED).

## Invariant matrix

| Invariant | Where enforced | Evidence proving enforcement | On uncertainty | How tested |
|---|---|---|---|---|
| source identity | corpus manifest + `load_manifest_rows` | LOCAL_CORPUS_REFERENCE_MANIFEST；AB-T03 | 清单缺失 → CorpusIntegrityError fail closed | test_corpus_fail_closed |
| source version / effective status | manifest 行字段（版本/施行/废止） | manifest 记录 2022/2023-09-28 等；无独立 version 模型（GAP→IR 决策） | 无 version 语义时按单一版本处理（需补） | 手工核对 manifest |
| evidence existence | `assert_verbatim`（行级包含） | E1/E2 全部证据通过 verbatim；B-E1 系列 | 不 verbatim → AssertionError → fail closed | test_seam03 / AB-T13 |
| verbatim / bounded citation | `assert_verbatim` + locator 构造 | locator 含条款号/表格号/page/行号；OBL-05 | 证据不在语料 → fail closed | ST-06 numeric traceability |
| required project facts | `missing_facts` + `_required_facts` | T-C03 / AB-T13 case4 → insufficient_context | 缺失 → insufficient_context（无数值） | T-C03 / AB-T13 |
| professional applicability preconditions | applicability chain（SEAM-02） | 防火间距/配建/防火分区家族判定链 | 无法判定 → no_reliable_evidence | test_seam02 / AB-T13 |
| numeric source support | 结论数值 ∈ 证据原文（ST-06 / AB-T13 value check） | 3000 来自 1500×2（派生）；直接值来自原文 | 数值不在证据 → FAIL | ST-06 / AB-T13 |
| derived numeric trace | **GAP（PC-04）** → 需 derivation_trace 结构化 | v0.3 结论含"×2"文本但无结构化 operand+modifier 记录 | 无轨迹 → 不可审计（须修复） | 待下代候选 |
| explicit exclusions | `is_excluded` | PC-05 木结构 → no_reliable_evidence | 排除项命中 → 明确不适用 | AB-T13 case5 |
| source conflict / authority uncertainty | **GAP（长程）** | 无冲突语义（单源现状） | 未来 edition 冲突需明确 | 长程设计契约 |
| local vs web evidence distinction | **GAP（长程）** | Web 未授权；未来需 label + URL | 未来需区分 | 长程设计契约 |
| provenance | evidence 字段 + implementation_metadata | E1/E2 溯源链（D2 机制） | 无法链接 → fail closed | E1 provenance 检查 |
| fail closed | decide() + 各 handler | T-C03 / AB-T13 / E1 B-E1-04/09 | 一律 fail closed | 回归测试 |

## 关键 GAP（来自 PC-01..04，成为 validator 契约）

```text
V-GAP-01 正向适用性校验（PC-01）：applicability 前须校验 scope_conditions（公共建筑），
         非公共建筑不得输出 4.3.16 结论
V-GAP-02 zone/condition 分解（PC-02）：设备房 vs 其他区域须按结构化 condition 区分
V-GAP-03 SEAM-02 归属（PC-03）：适用性判定链须通过 SEAM-02 责任路径可观察
V-GAP-04 派生数值轨迹（PC-04）：operand + modifier + formula + result 结构化记录
```

## 决策陈述

```text
VERIFICATION ARCHITECTURE DECISION
验证面保持 100% 确定性 + 强化：
  source identity/version/evidence/citation/facts/preconditions/numeric/exclusions/
  provenance/fail-closed 全部为确定性不变量
  新增 V-GAP-01..04 作为 validator 契约（对应 PC-01..04）
验证与知识解耦：RegulationUnit 承载知识，validator 承载契约（H-08 方向）
不确定性一律 fail closed；不得由 LLM 承担任何验证不变量
```

## 测试要求

```text
PC-01..07 → Gold / Regression Cases + Validator requirements（Review Contract §12）
不得将 PC 缺陷转为更多特设 runtime 分支；应成为 validator 契约与回归用例。
```
