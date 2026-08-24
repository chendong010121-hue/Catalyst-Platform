# CASE 01-E / E2-AB — CANDIDATE FREEZE REPORT — V0.1

> E2-AB Gate 1 publication report per Stage Spec §48. DeepSeek does not close E2;
> ChatGPT external Candidate-Freeze Review decides next.

```text
E2-AB STATUS
READY FOR CANDIDATE-FREEZE EXTERNAL REVIEW

CASE-01 HEAD INPUT
a8b9b4611306778e58574b0770da9c1827c83f93

METHOD REF
a5e7b0b9384f8108d5af22bfe9fea317d8e60cee

REFERENCE
case-01.brea @ 0.2-candidate

TARGET CANDIDATE
case-01.brea @ 0.3-candidate

SELECTED PROFESSIONAL FAMILY
公共建筑防火分区最大允许建筑面积（GB 55037-2022 第4.3.16条，条件规则族）

SOURCE PATH
A（existing admitted corpus；无新源，无需 Source Admission Record）

NEW SOURCE
NONE

P-01..P-06
PASS（6/6 artifacts complete）

PROFESSIONAL PURPOSE CHANGE
NO

NEW GOVERNED SEAM
NO

NEW OBLIGATION
NO

IMPLEMENTATION CAPABILITY
确定性编号子项条款解析器（brea/coverage.py，PRIVATE HOW；LLM/RAG 明确拒绝）

V0.2 REFERENCE INTEGRITY
PASS（byte-identical 验证 + E1 指纹有效）

V0.3 FORMATION
PASS（builder: 5 changed / 17 unchanged byte-identical, import probe PASS）

FN / SEAM / OBL
PASS（FN-01..11 / SEAM-01..03 / OBL-01..06 保持；bounded EXTENDED）

CONSTRUCTION SELF-CHECKS
22/22 PASS（AB-T01..T22）+ candidate regression 15/15 PASS

ANTI-HARDCODE
PASS（AB-T18；无 benchmark 字面量/分支/结论映射）

PLATFORM COMPATIBILITY
PASS（AB-T19；Platform/Runtime/Adapter 不变）

RAW CORPUS COMMITTED
NO

CANDIDATE TREE SHA256
37bb4864a9dd39812d9d77c24bb48d9b7abe2403c2ed6f4df31d2e7db847fa7b

EVALUATION CONTRACT
GENERATED（evaluation/E2_EVALUATION_CONTRACT_V0.1.md，无具体 cases）

SPECIFIC INDEPENDENT BENCHMARK CASES
NOT CREATED（evaluation/benchmark/ 不存在）

GATE-1 COMMIT
<filled at publication>

MAIN
UNCHANGED

E2-C
NOT AUTHORIZED

FINAL
READY FOR CANDIDATE-FREEZE EXTERNAL REVIEW
```

---

## What E2-AB proved

1. **Method intentional application (P-01..P-06)** — first intentional execution of the
   accepted Construction Method chain: Problem → Mechanism → Assumptions →
   Responsibility → Compatibility → Catalyst-native Reconstruction. The external
   benchmark-isolation mechanism (Penguin reference, pinned) was reconstructed as
   "Evaluation Contract before freeze; benchmark after freeze" without inheriting any
   Penguin architecture.
2. **New professional family with real decision behavior** — fire-compartment max area
   (GB 4.3.16) is a conditional-rule family (form × fire-resistance × auto-extinguishing
   modifier) requiring 3 new professional facts; it is implemented via a reusable
   numbered-subitem parser, NOT per-question branches; AB-T13 proves supported cases,
   fail-closed (missing facts), and explicit non-applicability (excluded building types).
3. **Reference integrity** — v0.1 (admitted) and v0.2 (E1 baseline) byte-unchanged;
   v0.3 formed as Candidate N+1 by the Case-local builder; 22/22 construction
   self-checks and 15/15 candidate regression pass.
4. **Freeze discipline** — v0.3 frozen (tree SHA `37bb4864…`); Evaluation Contract
   exists at capability level with NO specific benchmark cases; no benchmark files
   exist (leakage-control chronology preserved for E2-C).
5. **Boundaries held** — no Platform/Runtime/Adapter/enterprise change; main unchanged;
   raw corpus not committed.

## Non-blocking findings

- OCR 语料中 4.3.16 子项行首数字存在噪声（如 "27对于…"），子项解析按行首数字
  之后的语义文本进行，数值从"不应大于N m²"原文提取——已通过 verbatim 断言保护。
- candidate `run_all.py` 头部仍打印 "BREA v0.1-candidate self-check"（拷贝自 v0.1 的
  测试外壳文本）；实际被测代码为 v0.3（CANDIDATE_ROOT 解析到 v0.3），纯显示问题，NON-BLOCKING。

## STOP

DeepSeek stops after ONE E2-AB Candidate-Freeze implementation+evidence commit and ONE
push to `case-01`. E2-C is NOT authorized: it requires Freeze Review PASS + second
explicit User authorization. E3 / v0.3 admission-binding NOT authorized.
