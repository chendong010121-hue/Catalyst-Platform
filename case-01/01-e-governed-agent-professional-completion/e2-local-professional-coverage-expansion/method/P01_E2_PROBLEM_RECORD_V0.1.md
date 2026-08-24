# E2 — P-01 PROBLEM RECORD — V0.1

> Method step P-01 (Problem Extraction) — accepted Construction Method §6.
> Technology-neutral problem statement, independent of implementation technology.

## EXTERNAL_PATTERN_PROBLEM_RECORD

| Field | Value |
|---|---|
| problem | BREA cannot determine professional applicability for fire-compartment maximum allowable building area of a public building from local normative evidence and project facts. |
| professional context | 建筑方案/初步设计阶段：公共建筑（商业、办公、教学楼等）每个防火分区的最大允许建筑面积是防火设计的基本控制事项；设计人需要根据建筑形式（高层/单多层/地下）、耐火等级、是否设置自动灭火系统得到受控数值。 |
| target user | 建筑方案/初步设计工程师、审查人员（CASE 01 pilot） |
| input class | 自然语言问题 + 项目事实（building_form、fire_resistance_rating、auto_extinguishing_system、jurisdiction、building_category） |
| observable output | 当事实与本地规范证据充分时：返回受控的防火分区最大允许建筑面积数值 + 原文条款/数值来源证据；证据不足或事实缺失时 fail closed，绝不编造数值 |
| current failure mode | BREA v0.2 对该问题走 QMODE-03 主题检索（若提及标准）或 QMODE-05 无适用依据 fail closed；不能把 4.3.16 的条件规则（高层/单多层/地下 × 耐火等级 × 自动灭火）解析为专业适用性结论 |
| why current behavior is professionally insufficient | v0.2 只有两条专业适用性主线（防火间距 GB 3.1.3；停车配建 DBJ 表5.0.1+表5.0.4）。防火分区最大允许建筑面积是另一条独立的专业控制事项，属于"fire-safety applicability beyond fire-distance"（E2 Spec §3 合格切片）；仅能检索到 4.3.16 条文 ≠ 能给出适用的分区面积结论 |
| technology-neutral statement | BREA 无法仅凭本地规范证据与项目事实，可靠判定"公共建筑防火分区最大允许建筑面积"这一专业适用性事项（含高层/单多层/地下与耐火等级、自动灭火系统的条件规则）。 |
| source evidence needed | GB 55037-2022 第4.3.16条（本地已接纳语料）原文，含编号子项条件规则：高层建筑≤1500m²；一、二级耐火等级单多层≤2500m²；三级≤1200m²；四级≤600m²；地下设备房≤1000m²、地下其他≤500m²；全部设置自动灭火系统面积可增加1.0倍 |

## 技术无关性确认

本记录不包含任何实现技术（无 RAG / LLM / 向量库 / Web）。问题、输入、输出、失败模式均以专业行为描述。

## 与既有专业家族的差异

```text
T-C01 防火间距（GB 3.1.3）        → 位置关系控制事项（间距）
T-C02 停车配建指标（DBJ 表5.0.1/5.0.4）→ 配建数量控制事项
P-01 防火分区最大允许建筑面积（GB 4.3.16）→ 分区规模控制事项（新家族，独立于前两者）
```
