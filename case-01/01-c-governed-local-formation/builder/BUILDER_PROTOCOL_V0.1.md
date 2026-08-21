# BUILDER PROTOCOL — V0.2 (CASE 01-C targeted builder proof repair)

> Minimum Case-scoped Governed Builder — **definition-driven**（C-01…C-05 修复后）。不是通用 Builder Platform。

## 1. 架构权威

```text
ACCEPTED GOVERNED DEFINITION（BUILDER_CONSUMABLE_DEFINITION_V0.1.md, SHA 6c6e4707…）
→ 确定性解析/校验（identity/purpose/FN-01..11/SEAM-01..03/OBL-01..06/allowed assets/corpus/private freedom）
→ 实现投影（templates → candidate）
```

`BUILDER_REQUEST_V0.1.json` 仅含执行参数（candidate id/version、target、定义路径、语料清单路径）。
**请求不得携带架构字段**（functions/seams/obligations/allowed_asset_manifest/private_implementation_freedom）——出现即 fail closed。

## 2. SHA 强制执行（C-02）

实际 SHA ≠ 接受 SHA（`6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4`）→ **生成前 fail closed**（非零退出）。记录哈希不足以保证。

## 3. Clean-Target 规则（§14 / BT-09）

目标非空 → 拒绝并停止（不自动删除）。生成文件 + SHA 记录于输出清单。

## 4. 生成与校验

- 源：`builder/templates/**`；目标：`candidate/brea-v0.1/**`。
- 生成后校验：候选 FN/SEAM/OBL 映射 == 解析定义（BT-07）；义务测试引用存在（BT-08）；import 探针。
- 任何分歧 → 非零退出 / 无成功清单。

## 5. 义务映射（C-03）

`run_builder.OBLIGATION_MAPPING` 为真实测试引用（如 OBL-03 → test_st06_numeric_traceability + T-C01/T-C02）；Builder 校验每个引用存在。

## 6. Builder 测试（BT-01..BT-10）

```text
BT-01 接受 SHA 通过      BT-02 篡改 SHA fail closed     BT-03 FN 集 == FN-01..11
BT-04 SEAM 集 == 01..03   BT-05 OBL 集 == 01..06        BT-06 请求不得覆盖架构
BT-07 生成候选映射匹配    BT-08 义务引用存在             BT-09 非空目标 fail closed
BT-10 未复制语料
```

## 7. 输出

```text
BUILDER_OUTPUT_MANIFEST_V0.1.json（解析架构 + 校验结果 + 义务映射 + 生成清单）
BUILDER_RUN_REPORT_V0.1.md（定义驱动证明 + 修复记录 C-01..C-05）
```

## 8. 边界

只写授权 Case 路径；不改 Catalyst 根/Platform/Runtime/main；不复制语料；不改已接受定义。
