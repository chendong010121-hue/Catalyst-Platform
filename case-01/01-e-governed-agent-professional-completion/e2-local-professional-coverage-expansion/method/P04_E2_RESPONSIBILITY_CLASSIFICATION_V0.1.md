# E2 — P-04 RESPONSIBILITY CLASSIFICATION — V0.1

> Method step P-04 (Responsibility Classification) — accepted Construction Method §9.
> Map every material E2 change across responsibility classes. No external mixed
> boundary is preserved merely because it works.

## 1. Selected slice — 公共建筑防火分区最大允许建筑面积（GB 4.3.16）

| Change | DOMAIN | ENTERPRISE | AGENT BEHAVIOR | GOVERNANCE | PLATFORM STANDARD | ADAPTER / BINDING | RUNTIME | IMPLEMENTATION HOW | EVALUATION |
|---|---|---|---|---|---|---|---|---|---|
| 4.3.16 条件规则族语义（形式×耐火等级×灭火系统→数值） | **PRIMARY（专业权威，来自条文）** | — | 绑定事实→子项→数值的行为 | — | — | — | — | 规则解析器是 HOW | — |
| 新增专业事实（building_form / fire_resistance_rating / auto_extinguishing_system） | **PRIMARY（SEAM-01 事实词汇）** | — | 事实归一化 | — | — | — | — | — | — |
| 编号子项条款解析（"1/2/3/4…"） | — | — | — | — | — | — | — | **PRIMARY（FN-09/证据层 HOW）** | — |
| 数值绑定 + 逐字证据 + locator | — | — | SEAM-03 绑定（Agent 侧） | — | — | — | — | verbatim 断言实现 | — |
| 适用性 vs 检索分离（4.3.16 查询≠判定） | — | — | SEAM-02 判定边界 | — | — | — | — | — | — |
| Candidate Freeze → 独立评估隔离 | — | — | — | **PRIMARY（评审时序纪律）** | — | — | — | — | **PRIMARY（冻结身份/评估身份分离）** |
| 企业上下文归属 | — | 仅 attribution（沿用） | — | — | — | — | — | — | — |

## 2. 明确拒绝的错误边界（Method §9 不保留外部混合边界）

```text
外部"Benchmark 与 Candidate 同目录"的混合边界 → 不保留：E2 用发布时序分离
"检索命中=适用性"混合语义 → 不保留：SEAM-02 判定独立于 QMODE 检索
"OCR 文本=规范原文"假设 → 不保留：verbatim 行级断言
```

## 3. 最小化 Enterprise 使用

E2 无组织级需求：不引入 source policy / IAM / RBAC / approval workflow。
Enterprise 保持为 attribution（organization_id/user_id/project_id），OBL-06 不变。

## 4. 结论

- 本切片是 **Domain / Agent 专业完成切片**（E2 Spec §38 预期）。
- Platform Standard / Runtime / Adapter / Enterprise extensions：**无变更**。
- 评估隔离属 **GOVERNANCE / EVALUATION**，不进入 Platform。
