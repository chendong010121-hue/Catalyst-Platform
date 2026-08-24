# E2 — EVALUATION CONTRACT — V0.1

> E2-AB §22: defined BEFORE Candidate Freeze so the Candidate knows the capability it
> must satisfy. **Contains NO specific future benchmark cases / Gold answers** — those
> are created/revealed only in E2-C after Freeze Review + new authorization.

## 1. Target professional capability

```text
公共建筑防火分区最大允许建筑面积判定：
输入 = 自然语言问题 + 项目事实（building_form / fire_resistance_rating /
       auto_extinguishing_system / building_category / jurisdiction）
输出 = 依 GB 55037-2022 第4.3.16条编号子项条件规则，绑定受控数值结论 + 逐字证据 + locator
```

## 2. Observable success behavior

```text
事实充分（形式 + 耐火等级 + 灭火系统可匹配 4.3.16 子项）
→ status accepted_with_evidence
→ conclusion 含受控数值（如 "不应大于 X m²"）
→ evidence_items ≥1：source_identity=GB 55037-2022，evidence_type=normative_clause/
  numbered_subitem，locator 含"4.3.16"，内容为 4.3.16 原文（含被绑定子项）
→ 数值在证据原文中出现（numeric safety）
→ 全部设置自动灭火系统时应用"增加1.0倍"修正（仅当子项4存在且原文支持）
```

## 3. Required evidence properties

```text
source_identity / source_title / source_version_or_date / locator /
evidence_type / evidence_content / claim_relation — 全部字段必须存在
evidence_content 必须行级 verbatim（在本地已接纳语料中存在）
```

## 4. Professional applicability expectations

```text
防火分区家族 ≠ T-C01 防火间距 ≠ T-C02 配建指标（三族互不干扰）
检索 4.3.16 原文（QMODE-01）≠ 适用性判定：判定必须绑定项目事实
排除项（特殊要求建筑/木结构建筑/附建于民用建筑中的汽车库）→ 明确不适用
```

## 5. Numeric safety expectations

```text
任何结论数值必须来自 4.3.16 原文且可解析
事实不足时结论无数值（fail closed）
数值绑定失败 → no_reliable_evidence（不编造）
自动灭火修正仅在原文子项存在时应用
```

## 6. Source fidelity expectations

```text
证据内容 = 语料原文（行级 verbatim 断言通过）
locator 可定位（OCR page + 本地行号）
OCR 噪声（页脚/分页）不进入证据内容
```

## 7. Missing-context behavior

```text
必要事实任一缺失（形式/耐火等级/灭火系统）→ insufficient_context
结论无数值，明确列出缺失事实（专业标签）
```

## 8. Non-applicable behavior

```text
问题不属于公共建筑防火分区事项 / 属于 4.3.16 排除项
→ no_reliable_evidence（明确不适用，无数值）
```

## 9. No-reliable-evidence behavior

```text
子项无法解析 / 数值无原文 → no_reliable_evidence（不编造）
```

## 10. Regression obligations

```text
E1 一般化查询回归（QMODE-01/02/03/04 行为不变）
T-C01 PASS · T-C02 PASS · T-C03 PASS
FN/SEAM/OBL 映射保持（AB-T10/11/12）
Platform 兼容（AB-T19）
```

## 11. Common shortcuts / invalid success modes

```text
检索到含"防火分区"文本就 PASS                                        → 无效（须适用性绑定）
返回 4.3.16 原文但不绑定项目事实 → 不算专业 PASS（属 QMODE-01 检索）
per-question 硬编码（问题→数值）→ 无效（须可复用机制）
数值不在证据原文 → 无效（numeric safety）
```

## 12. Minimum benchmark class requirements (E2-C, created AFTER freeze)

```text
≥4 supported cases（新家族，事实充分 → 正确绑定数值）
≥2 natural-language / fact-layout variations
≥2 missing-context / insufficient-facts cases
≥1 non-applicable / wrong-source trap
≥1 unsupported numeric / normative-conclusion trap
≥1 no-reliable-evidence case
≥3 regression cases（T-C01 / T-C02 / T-C03）
（具体 cases 数量与内容由 E2-C 冻结后确定；本契约不含 cases）
```

## 声明

```text
本 Evaluation Contract 不含任何具体 benchmark case / Gold answer。
具体独立 Benchmark cases 仅在 Candidate Freeze 外部评审 PASS + 新授权后创建（E2-C）。
```
