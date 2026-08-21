# PLATFORM GAP UPDATE — V0.1 (CASE 01-C) — REPAIRED (C-05, 2026-08-21)

> 依据 01-B PLATFORM_GAP_REGISTER（GAP-01..10）与修复契约（C-05）。发现缺口 ≠ Platform 修改授权。

## GAP-01 — Builder-consumable Governed Agent definition

- 01-C 修复后状态：**CASE-CLOSED — for Case 01 only**（定义驱动证明；待外部闭包再审计确认）
- 证据：`BUILDER_CONSUMABLE_DEFINITION_V0.1.md`（SHA `6c6e4707…`）被 Builder **解析并校验**（identity/purpose/FN-01..11/SEAM-01..03/OBL-01..06/assets/corpus/freedom），
  生成 19 文件 + 映射清单；`builder/test_builder.py` BT-01..10 PASS；`BUILDER_OUTPUT_MANIFEST_V0.1.json` validation 矩阵全 PASS。
- 泛化：LOCAL ONLY → CASE CANDIDATE（不视为 Catalyst Platform 能力）。

## GAP-05 — Minimum local Builder capability

- 01-C 修复后状态：**CASE-CLOSED — for Case 01 only**（定义驱动证明；待外部闭包再审计确认）
- 证据：`builder/`（definition_parser + run_builder + tests + 协议/请求/清单/报告）；BUILDER_FORMATION_TRACE（BC-01..10 PASS）。
- 泛化：LOCAL ONLY → CASE CANDIDATE（非通用 Builder Platform）。

## 其他 GAP（未变，未实现）

GAP-02/03/04/06/07 保持 LOCAL ONLY；GAP-08 保持 Runtime 边界足够；GAP-09（admission/binding）与 GAP-10（版本/快照/回滚）→ 01-D / 01-F 输入，NOT AUTHORIZED。

## 新缺口

- **无新增平台缺口**。修复期摩擦均为实现级（解析器首行义务声明、定义键位）——已修复并记录于 Builder 测试/报告，不构成 Platform gap。
