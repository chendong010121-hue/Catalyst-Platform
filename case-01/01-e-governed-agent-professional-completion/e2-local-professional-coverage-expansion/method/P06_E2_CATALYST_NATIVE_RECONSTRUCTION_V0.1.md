# E2 — P-06 CATALYST-NATIVE RECONSTRUCTION — V0.1

> Method step P-06 (Catalyst-Native Reconstruction) — accepted Construction Method §11.
> External vocabulary is NOT inherited as Catalyst vocabulary; the mechanism is
> rebuilt inside Catalyst-native responsibilities.

## Catalyst-native chain

```text
Professional Coverage Need（防火分区最大允许建筑面积）
        ↓
Governed Change Interpretation（P-01..P-05）
        ↓
Function / Seam / Obligation Impact（E2_CHANGE_IMPACT_REVIEW）
        ↓
Implementation Capability Selection（E2_IMPLEMENTATION_CAPABILITY_SELECTION）
        ↓
BREA v0.3 Candidate（builder overlay）
        ↓
Candidate Freeze（freeze/E2_V0_3_CANDIDATE_FREEZE_RECORD）
        ↓
Independent Evaluation Contract（evaluation/E2_EVALUATION_CONTRACT，无具体 cases）
        ↓
(E2-C) post-freeze professional Benchmark + Decision Evidence
```

## External → Catalyst vocabulary mapping

| External (Penguin benchmark-design) | Catalyst-native (E2) |
|---|---|
| benchmark designer freezes evaluation conditions | **Evaluation Contract** 先于冻结（capability 级）；具体 cases 冻结后建 |
| separate public task / private decision standard | Evaluation Contract 公开；E2-C Decision Standard 后建（未授权则不建） |
| leak check | E2-AB anti-hardcode review（只许用 capability 契约/家族/来源/自测，不用未来 cases） |
| freeze one valid benchmark revision | E2-C frozen Benchmark identity + SHA |
| traceable evaluation identity | frozen Candidate fingerprint + benchmark SHA + per-case evidence |

## 实施重建（本阶段 E2-AB 实际内容）

| 组件 | Catalyst 职责 | 实现 |
|---|---|---|
| 4.3.16 条件规则解析 | FN-09/证据层（PRIVATE HOW） | `brea/coverage.py`（新私有模块）：编号子项条款 → {条件,数值,证据} 结构化 |
| 专业事实扩展 | SEAM-01（Domain） | `brea/facts.py`：新增 building_form / fire_resistance_rating / auto_extinguishing_system 词汇 + 标签 |
| 适用性判定扩展 | SEAM-02（Domain） | `brea/applicability.py`：识别防火分区控制事项 → 4.3.16 家族 |
| 数值绑定 + 逐字证据 | SEAM-03（Agent 绑定） | `brea/runner.py`：事实→子项→数值，verbatim 断言 + locator |
| 候选 N+1 | Builder 机制 | `builder/run_e2_builder.py`（复用 E1 机制，v0.2→v0.3 overlay） |
| 冻结 | 治理纪律 | `freeze/E2_V0_3_CANDIDATE_FREEZE_RECORD_V0.1.json` |

## 预期行为变化

```text
BEFORE (v0.2)
"某高层办公楼每个防火分区的最大允许建筑面积？" + 足够事实
→ QMODE-05 无适用依据 → no_reliable_evidence（无法判定）

AFTER (v0.3)
同问 + 事实（高层 / 一级耐火 / 全部自动灭火）
→ 4.3.16 子项1（高层≤1500m²）× 子项4（全部自动灭火增加1.0倍）
→ accepted_with_evidence：≤3000m²，逐字证据 + locator
```

## 预期 fail-closed 行为

```text
事实缺失（形式/耐火等级/灭火系统）→ insufficient_context（无数值）
排除项（特殊要求/木结构/附建汽车库）→ no_reliable_evidence（明确不适用）
子项解析失败 / 数值无原文 → no_reliable_evidence（不编造）
```

## 不继承声明

```text
不继承 Penguin Agent State / Skill schema / Benchmark layout / Scoreboard /
evaluator protocol / Runtime / identity model
不引入 AGENTS.md 作为治理权威
外部机制仅作为 Stage 设计输入（Method 权威 < Stage Spec < Governing Baseline）
```
