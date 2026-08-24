# E2 — PROFESSIONAL COVERAGE SELECTION — V0.1

> E2-AB §9: compare at least 2 realistic candidate professional slices from actual
> local evidence, then select exactly one. Source Path A = existing admitted corpora.

## Candidate 1 — GB 55037-2022 §4.3.16 公共建筑防火分区最大允许建筑面积 (fire-compartment max area)

```text
QUESTION FAMILY
公共建筑每个防火分区的最大允许建筑面积不应大于多少？（依建筑形式/耐火等级/自动灭火系统）

LOCAL AUTHORITATIVE EVIDENCE (admitted corpus, verbatim)
4.3.16 除有特殊要求的建筑、木结构建筑和附建于民用建筑中的汽车库外，其他公共建筑中
每个防火分区的最大允许建筑面积应符合下列规定：
  1 对于高层建筑，不应大于 1500m²
  2 对于一、二级耐火等级的单、多层建筑，不应大于 2500m²；三级 1200m²；四级 600m²
  3 对于地下设备房，不应大于 1000m²；对于地下其他区域，不应大于 500m²
  4 当防火分区全部设置自动灭火系统时，上述面积可以增加 1.0 倍

REQUIRED PROJECT FACTS (NEW vs v0.2)
building_form（高层/单多层/地下）· fire_resistance_rating（一/二/三/四级）·
auto_extinguishing_system（全部/局部/无）· building_category（公共建筑）

DIFFERENCE FROM T-C01/T-C02
T-C01 防火间距=位置关系控制事项；T-C02 配建指标=数量配比事项；
本家族=分区规模控制事项，独立条件规则族（形式×耐火等级×灭火系统）
```

## Candidate 2 — DBJ33/T1021-2023 §4.3.4 + 表4.3.4 机动车停车场（库）出入口和车道数量

```text
QUESTION FAMILY
机动车停车场（库）应设置几个出入口/车道？（依机动车停车位当量数 + 建筑性质）

LOCAL AUTHORITATIVE EVIDENCE (admitted corpus, verbatim)
表4.3.4 机动车停车场（库）出入口和车道数量：
  ≤100 个      → 至少 1 个双车道出入口 或 2 个单车道出入口
  101~300 个   → 至少 1 个双车道 + 1 个单车道出入口
  301~800 个   → 至少 2 个双车道出入口
  801~3000 个（住宅）→ 至少 3 个双车道 + 每增800个车位（不足800按800计）宜增设1个双车道
  801~3000 个（非住宅）→ 至少 3 个双车道 + 每增600个车位（不足600按600计）宜增设1个双车道
  >3000 个     → 出入口和车道数量应经交通模拟计算确定

REQUIRED PROJECT FACTS (NEW vs v0.2)
parking_equivalent_count（停车位当量数）· building_nature（住宅/非住宅）

DIFFERENCE FROM T-C01/T-C02
同属"parking 家族"方向但问题是出入口/车道数量（T-C02 是配建指标数量）；
OCR 表4.3.4 存在"住宅/非住宅"跨行合并的解析风险（行内子条件），解析复杂度更高
```

## Decision criteria comparison

| Criterion | Candidate 1 (防火分区面积) | Candidate 2 (出入口/车道数量) |
|---|---|---|
| professional value | 高（防火设计基本控制事项，面向建筑方案阶段） | 中高（停车设施设计事项） |
| local authoritative evidence availability | 高（4.3.16 单条完整，含编号子项） | 高（表4.3.4 完整） |
| difference from T-C01/T-C02 family | 强（独立控制事项族：分区规模） | 中（仍属 parking/access 方向，但有独立问题） |
| project facts required | 3 项新事实（形式/耐火等级/灭火系统） | 2 项新事实（当量数/性质） |
| applicability complexity | 条件规则族（形式×耐火等级×灭火） | 区间行规则 + 建筑性质子条件 |
| evidence type | 编号子项条款（clause with numbered items） | 表格行（table row + 行内子条件） |
| source quality / OCR risk | 中低（4.3.16 文字清晰；需处理编号子项解析） | 中高（表4.3.4 存在跨行合并/子条件） |
| implementation risk | 中（子项条件解析器） | 中高（行内区间+性质条件） |
| evaluation feasibility | 高（数值可断言、可 fail closed） | 高 |

## SELECTED E2 PROFESSIONAL FAMILY

```text
GB 55037-2022 §4.3.16 — 公共建筑防火分区最大允许建筑面积（条件规则族）

WHY NOW
E1 已证明一般化证据查询；E2 必须证明"更广的专业覆盖=新专业适用性行为"，
而不仅是"更广的文本检索"。4.3.16 是本地已接纳语料中一条完整、独立、可判定的
条件规则族，正好把 v0.2 的两条专业主线扩为第三条主线。

WHY NOT RETRIEVAL-ONLY
仅检索 4.3.16 原文（QMODE-01）≠ 判定"我的高层一级耐火等级公共建筑分区面积应≤多少"。
新行为要求：解析编号子项 → 依项目事实选择子项 → 绑定数值 → 数值有原文证据；
这是专业适用性判定（SEAM-02 扩展），不是检索。

SOURCE PATH
A — existing admitted corpus（GB55037-2022 已接纳；无新源、无 Source Admission Record 必要）
```

## SUCCESS BEHAVIOR

```text
问题含"防火分区/最大允许建筑面积"且给出足够项目事实（建筑形式/耐火等级/灭火系统）
→ 解析 4.3.16 子项 → 依事实绑定子项数值（含"全部设置自动灭火系统增加1.0倍"修正）
→ status accepted_with_evidence + 逐字证据（含 locator）
```

## FAIL-CLOSED BEHAVIOR

```text
事实缺失（形式/耐火等级/灭火系统任一不足）→ insufficient_context（无数值）
问题不属于公共建筑防火分区事项 → no_reliable_evidence
4.3.16 排除项（特殊要求建筑/木结构/附建汽车库）→ no_reliable_evidence（明确不适用）
子项数值无法从原文解析 → no_reliable_evidence（不编造）
```

## 候选比较结论

两个候选均有真实本地证据。选择 **Candidate 1（防火分区最大允许建筑面积）**：
专业价值更高、OCR 风险更低、条件规则族更典型（形式×耐火等级×灭火系统）、
与 T-C01/T-C02 的差异更独立；同时其"编号子项条款"结构恰好构成对通用解析器的
真实压力测试（E2 Stage Plan §2 明确列为合格切片类型）。
