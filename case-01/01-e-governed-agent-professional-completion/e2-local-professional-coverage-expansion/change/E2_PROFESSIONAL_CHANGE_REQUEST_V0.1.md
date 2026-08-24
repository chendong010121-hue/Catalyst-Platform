# CASE 01-E / E2 — PROFESSIONAL CHANGE REQUEST — V0.1

> E2-AB §17: concise natural-language product change derived from P-01..P-06.
> Product-change input only — NOT implementation authorization.

## 变更请求（自然语言）

> **让 BREA 能够对公共建筑的"防火分区最大允许建筑面积"进行专业适用性判定：依据项目事实（建筑形式、耐火等级、自动灭火系统设置）和本地规范原文（GB 55037-2022 第4.3.16条），给出受控的建筑面积上限结论并附原文证据；事实不足或属条文排除情形时，必须明确 fail closed，不得编造数值。**

## 当前 v0.2 局限

```text
v0.2 仅能检索 4.3.16 原文（QMODE-01）或主题命中（QMODE-03）；
不能把 4.3.16 的编号子项条件规则（高层/单多层/地下 × 耐火等级 × 自动灭火系统）
解析为"我的项目分区面积应≤多少"的专业结论。
```

## 新增专业行为

```text
问题：公共建筑每个防火分区的最大允许建筑面积不应大于多少？
输入事实：building_form（高层/单多层/地下）· fire_resistance_rating（一/二/三/四级）·
         auto_extinguishing_system（全部/局部/无）· building_category（公共建筑）
输出：依事实绑定 4.3.16 子项数值（含"全部设置自动灭火系统增加1.0倍"修正），
      附逐字证据 + locator；适用性链条可观察
```

## 所需证据 / 适用性

```text
来源：GB 55037-2022 第4.3.16条（本地已接纳语料，SOURCE PATH A）
数值：高层≤1500m²；一二级单多层≤2500m²；三级≤1200m²；四级≤600m²；
      地下设备房≤1000m²；地下其他≤500m²；全部自动灭火 → 增加1.0倍
适用性判定：SEAM-02 扩展（防火分区家族），区别于 T-C01 防火间距 / T-C02 配建
```

## fail-closed 要求

```text
事实缺失（形式/耐火等级/灭火系统任一不足）→ insufficient_context（无数值）
排除项（特殊要求建筑/木结构建筑/附建汽车库）→ no_reliable_evidence（明确不适用）
子项解析失败 / 数值无原文证据 → no_reliable_evidence（不编造）
```

## Scope exclusions（明确不做）

```text
Web 回退 · RAG · LLM · vector DB · Memory · Agent loop · 多轮 UX ·
前端/后端产品壳 · IAM/RBAC/策略引擎 · 新 Governed Seam · Platform/Runtime 变更
```

## Candidate 版本目标

```text
agent_id: case-01.brea
candidate_version: 0.3-candidate
父参考: case-01.brea @ 0.2-candidate（E1 已接受基线，read-only）
```
