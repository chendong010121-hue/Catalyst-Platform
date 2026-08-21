# FORMATION EVIDENCE INDEX — V0.1 (CASE 01-C) — REPAIRED (C-01..C-05, 2026-08-21)

> FE-01..FE-16。每条证据指向可复现文件/测试/运行。整机形成已通过（evidence/CASE_RESULTS）。修复后 Builder 为**定义驱动**。

| FE | 证据项 | 位置 | 状态 |
|---|---|---|---|
| FE-01 | Builder input path + SHA（**强制执行**，C-02） | `builder/BUILDER_OUTPUT_MANIFEST_V0.1.json`（accepted_sha = verified_sha = `6c6e4707…`；sha_enforced=true）；BT-01/BT-02 | PASS |
| FE-02 | Builder output manifest（定义驱动） | `builder/BUILDER_OUTPUT_MANIFEST_V0.1.json`（解析架构 + 校验矩阵 + 19 生成文件 + clean-target） | PASS |
| FE-03 | Agent identity/version | `candidate/brea-v0.1/brea/identity.py`（AGENT_ID=BREA, VERSION=v0.1-candidate, PURPOSE）；结果 `engine=brea-deterministic-v0.1` | PASS |
| FE-04 | FN-01..11 implementation mapping | `evidence/FUNCTION_CONFORMANCE_V0.1.md` + `brea/identity.py:BREA_FUNCTION_MAP` + manifest（来自解析定义） | PASS |
| FE-05 | SEAM-01..03 mapping + tests | `evidence/GOVERNED_SEAM_CONFORMANCE_V0.1.md` + `tests/test_seams.py`（4 PASS） | PASS |
| FE-06 | OBL-01..06 conformance | `evidence/OBLIGATION_CONFORMANCE_V0.1.md`（含义务→真实测试映射，与 manifest 一致）+ 测试 | PASS |
| FE-07 | legacy adaptation trace A-02/A-04/A-11/A-12/A-13a | `evidence/LEGACY_ADAPTATION_TRACE_V0.1.md` | PASS |
| FE-08 | Domain / Enterprise separation | ST-05 + 结果归属元数据 | PASS |
| FE-09 | corpus hash proof | ST-07 PASS（失配 fail closed）+ `evidence/CASE_RESULTS/01c_repair_selfcheck.txt`（修复重跑真实日志）+ `01c_selfcheck_original.txt`（原始日志保留）+ 结果 `implementation_metadata.corpus`（全 SHA） | PASS |
| FE-10 | direct-clause result | `evidence/CASE_RESULTS/T-C01_result.json`（accepted；50m 出自逐字条文） | PASS |
| FE-11 | conditional-table result | `evidence/CASE_RESULTS/T-C02_result.json`（表5.0.1→级别→表5.0.4 行→1.1 车位/100m²） | PASS |
| FE-12 | fail-closed result | `evidence/CASE_RESULTS/T-C03_result.json`（insufficient_context；结论无数值） | PASS |
| FE-13 | numeric-safety proof | ST-06 + T-C01/02 结论数值均存在于逐字证据 | PASS |
| FE-14 | Prompt non-authority proof | ST-04（无 prompt/AGENTS.md） | PASS |
| FE-15 | no Platform/Runtime/root contamination | `review/CATALYST_INTEGRITY_CHECK_V0.1.txt` + git status（仅授权路径） | PASS |
| FE-16 | Builder formation trace（定义驱动） | `evidence/BUILDER_FORMATION_TRACE_V0.1.md` + `BUILDER_RUN_REPORT_V0.1.md`（C-01..C-05 修复 + 定义解析/校验矩阵）+ `builder/test_builder.py`（BT-01..10 PASS） | PASS |

## 整机形成门（§27）

request → FN-01 → 受治理/私有组合 → FN-07 → RegulationEvidenceResult：T-C01/T-C02/T-C03 均通过真实组装候选（修复重跑：15/15 PASS）。
