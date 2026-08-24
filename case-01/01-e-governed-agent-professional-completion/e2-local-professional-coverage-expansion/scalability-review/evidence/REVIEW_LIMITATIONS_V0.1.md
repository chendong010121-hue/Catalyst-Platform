# REVIEW LIMITATIONS — V0.1

> Review Contract §21. Honest limitations of this Review; the Review may not omit
> disconfirming evidence, and must be transparent about what it could NOT determine.

## 1. 无实验证据

```text
本 Review 为研究/分析/文档阶段：未执行任何 spike / 实验（授权限制）。
因此以下判定依赖"现有 Case 证据 + 外部机制研究"，而非受控实验：

  - H-02 / H-04（ingestion 必要性）→ INSUFFICIENT EVIDENCE
  - A' vs B 的最终边界（RegulationUnit 深度）→ 需 F-EXP-03
  - unseen-source 零代码进入 → 需 F-EXP-01
```

## 2. 单一案例样本

```text
BREA 仅 2 份语料、3 个专业家族（防火间距/配建/防火分区）。
"新家族=代码变更"只有 1 个观察（E1→E2），不足以区分
"新家族本质上属 Structural（合法）" 与 "知识未外置（可修复）"。
```

## 3. 产品包络依赖产品权威

```text
OPEN/HIGH/COMPLEX 分类中的预期值（Corpus Growth MEDIUM、Version complex、
Knowledge Space OPEN）部分依赖产品意图推断；最终包络须 Product Authority（User）
确认。本 Review 已标注"预期"与"已验证"的区别。
```

## 4. 外部机制研究边界

```text
外部框架（RAGFlow/LlamaIndex/Haystack/Penguin）仅作为机制证据登记；
未 clone / 未执行 / 未安装任何外部代码。framework popularity ≠ architecture evidence。
```

## 5. 专业契约（PC-01..07）的验证状态

```text
PC-01..04 为 v0.3 Freeze 评审记录的真实缺陷（本 Review 已在 v0.3 代码中定位：
is_excluded 无正向 scope / match 无 zone 区分 / SEAM-02 归属在 runner /
派生数值无结构化轨迹）。
PC-05..07（retrieval≠applicability / unsupported numeric / no evidence fail-closed）
为既有行为，E1/E2 已实证。
```

## 6. 未回答问题（明确列出）

```text
- RegulationUnit 精确字段集（F-EXP-03 界定）
- unseen-source 零代码进入是否成立（F-EXP-01 界定）
- 大规模开放式措辞下 lexical 的 recall 边界（F-EXP-02 界定）
- 跨条款合成是否需要 LLM（无需求证据，未测）
- 未来 edition 替换的版本/冲突语义（长程）
```

## 7. 结论可靠性

```text
"拒绝 C/D 当前必要性、确认确定性验证、确认知识外置方向" —— 高置信（E1/E2 直接证据）。
"B-MIN 为下代候选方向" —— 中等置信（与 PC-01/02/04 吻合，但深度未验证）。
"最终架构" —— 未选择（INSUFFICIENT EVIDENCE，诚实保留）。
```
