# E2 — P-02 MECHANISM ABSTRACTION — V0.1

> Method step P-02 (Mechanism Extraction) — accepted Construction Method §7.
> Primary external mechanism: **Candidate Freeze → Independent Evaluation Isolation**
> (pinned reference: Prism-Shadow/penguin-harness commit `8e4a77d…`,
> `packages/skills/skills/benchmark-design/SKILL.md`, blob SHA `3ed641c47ab2072d3424a6863857ebe7e97459b5`).
> Also includes the E2 professional family mechanism (conditional-rule clause parsing).

## 1. Benchmark-isolation mechanism (spec §7)

```text
problem solved
Candidate implementation and Benchmark published together (E1 chronology weakness)
→ reviewer cannot verify the Candidate was not tuned to the Benchmark.

mechanism abstraction
capability/evaluation contract
→ freeze Candidate identity
→ separate evaluation identity
→ design/reveal evaluation AFTER Candidate freeze
→ preserve exact evaluation revision
→ detect leakage
→ retain traceable decision evidence

observable benefit
independent evaluation integrity: Candidate implementation cannot adapt to the Benchmark.

failure mode
leakage: Benchmark questions/gold appear in Candidate logic; or Candidate repaired post-reveal.

source reference
Prism-Shadow/penguin-harness @ 8e4a77d… benchmark-design SKILL.md (blob 3ed641c…)

what is deliberately NOT inherited
Penguin Agent State / Skill model / Benchmark directory schema / Scoreboard /
evaluator protocol / Runtime / identity model
```

Catalyst-native reconstruction (E2-AB):

```text
E2 Evaluation Contract (pre-freeze, capability-level only)
→ frozen BREA v0.3 identity + deterministic fingerprint
→ (E2-C, after Freeze Review + new authorization) post-freeze professional Benchmark
→ frozen Benchmark identity
→ professional evaluation evidence
→ governance decision evidence
```

## 2. Professional-family mechanism (P-01 selected slice)

```text
problem solved
公共建筑防火分区最大允许建筑面积的专业适用性判定（v0.2 无法判定）

mechanism abstraction
把"编号子项条款"解析为条件规则表：子项文本 + 数值 + 适用条件
→ 依项目事实（建筑形式/耐火等级/灭火系统）选择子项 → 绑定数值
→ 数值始终来自原文，逐字证据 + locator

observable benefit
一条可复用机制支撑任意同构编号子项条款；非 fixture 专用

failure mode
子项无法解析 / 事实不足 / 属于排除项 → fail closed，不编造数值

source reference
GB 55037-2022 第4.3.16条（本地已接纳语料，read-only）

what is deliberately NOT inherited
无外部产品结构；机制完全在 Catalyst 现有 FN/SEAM 职责内重建
```
