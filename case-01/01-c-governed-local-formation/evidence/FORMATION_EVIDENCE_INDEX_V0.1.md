# FORMATION EVIDENCE INDEX — V0.1 (CASE 01-C)

> FE-01..FE-16。每条证据指向可复现文件/测试/运行。单元测试不足；整机形成已通过（evidence/CASE_RESULTS）。

| FE | 证据项 | 位置 | 状态 |
|---|---|---|---|
| FE-01 | Builder input path + SHA | `builder/BUILDER_OUTPUT_MANIFEST_V0.1.json`（definition_sha256 = `6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4`） | PASS |
| FE-02 | Builder output manifest | `builder/BUILDER_OUTPUT_MANIFEST_V0.1.json`（19 生成文件+映射+clean-target） | PASS |
| FE-03 | Agent identity/version | `candidate/brea-v0.1/brea/identity.py`（AGENT_ID=BREA, VERSION=v0.1-candidate, PURPOSE）；结果 `implementation_metadata.engine=brea-deterministic-v0.1` | PASS |
| FE-04 | FN-01..11 implementation mapping | `evidence/FUNCTION_CONFORMANCE_V0.1.md` + `brea/identity.py:BREA_FUNCTION_MAP` + manifest.function_mapping | PASS |
| FE-05 | SEAM-01..03 mapping + tests | `evidence/GOVERNED_SEAM_CONFORMANCE_V0.1.md` + `tests/test_seams.py`（4 PASS） | PASS |
| FE-06 | OBL-01..06 conformance | `evidence/OBLIGATION_CONFORMANCE_V0.1.md` + `tests/test_cases.py` + ST 测试 | PASS |
| FE-07 | legacy adaptation trace A-02/A-04/A-11/A-12/A-13a | `evidence/LEGACY_ADAPTATION_TRACE_V0.1.md` | PASS |
| FE-08 | Domain / Enterprise separation | ST-05（`tests/test_structural.py`）+ 结果归属元数据（attribution 与证据链分离） | PASS |
| FE-09 | corpus hash proof | ST-07 PASS（失配 fail closed）+ `01c_selfcheck.log` + 结果 `implementation_metadata.corpus`（全 SHA） | PASS |
| FE-10 | direct-clause result | `evidence/CASE_RESULTS/T-C01_result.json`（accepted_with_evidence；50m 出自逐字条文） | PASS |
| FE-11 | conditional-table result | `evidence/CASE_RESULTS/T-C02_result.json`（表5.0.1→级别→表5.0.4 行→1.1 车位/100m²） | PASS |
| FE-12 | fail-closed result | `evidence/CASE_RESULTS/T-C03_result.json`（insufficient_context；结论无数值） | PASS |
| FE-13 | numeric-safety proof | ST-06 PASS + T-C01/02 结论数值均存在于逐字证据（verbatim 断言） | PASS |
| FE-14 | Prompt non-authority proof | ST-04 PASS（候选无 prompt/AGENTS.md 文件；语义在代码+语料） | PASS |
| FE-15 | no Platform/Runtime/root contamination | `review/CATALYST_INTEGRITY_CHECK_V0.1.txt`（git status/diff 仅授权路径）+ C13 | PASS |
| FE-16 | Builder formation trace | `evidence/BUILDER_FORMATION_TRACE_V0.1.md` + `BUILDER_RUN_REPORT_V0.1.md`（含有界修复 R-01..R-05） | PASS |

## 整机形成门（§27）

request → FN-01 → 受治理/私有组合 → FN-07 → RegulationEvidenceResult：T-C01/T-C02/T-C03 均通过真实组装候选（`tests/test_cases.py` 3 PASS）。
