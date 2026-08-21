# BUILDER FORMATION TRACE — V0.1 (CASE 01-C) — REPAIRED (C-01..C-05, 2026-08-21)

> "Agent builds Governed Agent" 的定义驱动验证（TRACK B · GAP-01/GAP-05 case closure）。§12/§14/§25 + 修复契约。

## 1. Builder 输入（FE-01；C-01/C-02）

```text
BUILDER_CONSUMABLE_DEFINITION_V0.1.md
accepted SHA 6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4
actual  SHA 6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4  （= accepted；sha_enforced）
```

## 2. 定义驱动投影（C-01）

```text
ACCEPTED GOVERNED DEFINITION
→ definition_parser.parse_definition（identity/purpose/FN-01..11/SEAM-01..03/OBL-01..06/allowed assets/corpus reference/private freedom）
→ dp.validate_architecture（FN/SEAM/OBL 集合 + purpose + corpus + freedom 校验）
→ BUILDER_REQUEST（仅执行参数；架构字段被拒——request_architecture_duplication=REJECTED）
→ templates 投影 → candidate/brea-v0.1
→ validate_generated_candidate（候选 FN/SEAM/OBL 映射 vs 解析定义；PASS）
→ validate_obligation_refs（义务→真实测试引用；PASS）
```

## 3. Clean-Target 与生成（§14 / BT-09）

修复重跑：删除 Builder 生成目标（修复程序允许）→ 空目标生成 19 文件 → import 探针 PASS。非空目标拒绝（BT-09）。

## 4. Builder 测试（BT-01..BT-10，全部 PASS）

BT-01 接受 SHA ✓ · BT-02 篡改 SHA fail closed ✓ · BT-03 FN 集 ✓ · BT-04 SEAM 集 ✓ · BT-05 OBL 集 ✓ ·
BT-06 请求不得覆盖架构 ✓ · BT-07 生成候选映射匹配 ✓ · BT-08 义务引用存在 ✓ · BT-09 非空目标 fail closed ✓ · BT-10 未复制语料 ✓

## 5. 修复闭合（C-01..C-05）

```text
C-01 定义控制架构投影      CLOSED（解析 + 校验 + 请求去架构化 + 候选映射核对）
C-02 SHA 强制执行          CLOSED（生成前 fail closed；BT-02 负测试）
C-03 义务映射真实引用      CLOSED（OBLIGATION_MAPPING 真实测试引用 + BT-08 校验）
C-04 断链证据引用          CLOSED（原始日志保留 01c_selfcheck_original.txt；修复重跑真实日志 01c_repair_selfcheck.txt）
C-05 缺口状态对账          CLOSED（GAP-01/05 → CASE-CLOSED for Case 01，待外部再审计）
```

## 6. Builder 成功标准（BC-01..10）

BC-01 语义消费已接受定义 ✓（解析+校验）· BC-02 无手动架构再发明 ✓ · BC-03 清洁目标生成 ✓ · BC-04 函数映射齐（来自定义）✓ ·
BC-05 接缝所有权保留 ✓ · BC-06 私有自由保留 ✓ · BC-07 未复制语料 ✓ · BC-08 未改 Catalyst 根/Platform/Runtime ✓ ·
BC-09 清单+报告 ✓ · BC-10 形成 PASS（候选 15/15；三案重跑通过）✓

## 结论

**GAP-01 / GAP-05 → CONDITIONALLY CASE-CLOSED — for Case 01 only**（定义驱动证明 + 最终语义解析器修复；经最终外部闭包审计后 → CASE-CLOSED）。机制 Case-scoped，非通用 Builder Platform。

## 7. Final semantic parser repair（2026-08-21，契约 CASE_01_C_FINAL_SEMANTIC_PARSER_REPAIR_V0.1.md）

- §7 legacy 资产语义分裂：`parse_legacy_assets` 输出 `selected_assets={A-02,A-04,A-11,A-12,A-13a}` 与 `deferred_assets={A-01,A-03,A-05}`（BT-11/12/13；disjoint；deferred 永不作为 build-authorized）。
- 私有实现自由：Option A 解析实际条目（BT-14；12 项）。
- Builder 清单记录 `selected_legacy_adaptation_assets` / `deferred_legacy_assets` / `private_freedom`；FN/SEAM/OBL 映射未变（F5 校验）；候选行为实质不变（15/15 + 三案重跑）。
