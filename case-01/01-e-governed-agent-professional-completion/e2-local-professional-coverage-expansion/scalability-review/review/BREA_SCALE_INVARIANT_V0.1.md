# BREA SCALE INVARIANT — V0.1

> Review Contract §6. Define two change classes and determine whether the
> Normal-vs-Structural distinction is actually achievable for BREA.

## Class 1 — NORMAL KNOWLEDGE GROWTH

```text
ordinary new regulation (same class as supported sources)
new local edition of a known source class
new version of an already supported regulation form
new clauses / tables in supported structures
user upload of a supported document type
new natural-language paraphrase
```

**Desired default cost:**

```text
data/source admission → ingest → normalize → index update → evaluation
NO Agent code change
NO model retraining
```

## Class 2 — STRUCTURAL CAPABILITY GROWTH

```text
new document structure
new semantic primitive
new professional reasoning primitive
new authority/conflict semantics
new verification obligation
new high-risk safety contract
```

**Allowed cost:**

```text
Domain Schema change
Capability change
Candidate N+1
Governance review
```

## 该区分对 BREA 是否可实现 — 证据检验

### 支持"可实现"的证据

| 证据 | 说明 |
|---|---|
| E1 一般化查询（v0.2） | QMODE-01..04 全部为数据驱动：标准别名表、条款/表格定位正则、n-gram 检索——对"已支持结构内的新条款/新表格/新措辞"无需代码变更（B-E1-01..13 即未编码查询） |
| E1 反 fixture 审查 | 7 个未编码查询成功 → 在"已支持结构 + 已接纳语料"内，Normal Growth 的"新措辞/新定位"确实零代码 |
| E2 规则数据外置（v0.3） | FIRE_COMPARTMENT 规则表、condition_facts、modifier_rule 均为数据声明；同一 coverage.py 可服务同类编号子项条款 → 部分证明"知识可外置于数据" |

### 反对/限制"可实现"的证据（必须记录）

| 证据 | 说明 |
|---|---|
| E2 新家族仍需要新代码 | v0.3 新增 family 时改了 coverage.py + facts.py + runner.py + identity.py → 当前实现里"新专业家族"落在 Structural Growth 一侧，而非 Normal Growth。真正的问题：**防火分区家族是否本质上是 Structural（新推理原语）？** 若是，则 v0.3 的代码变更合法；若否（只是同类编号子项的新实例），则代码变更暴露了知识仍留在 Python 中（H-03 方向） |
| PC-01..04 | 冻结审查发现的专业缺陷（正向适用性不完整/地下分区区分不完整/SEAM-02 归属错位/派生数值契约缺口）说明：当前"声明式数据 + 解析器"模型**不足以自动满足**专业契约——Normal Growth 想要"零代码"就必须让数据模型承担这些契约，而当前模型没有 |
| 无未见语料实验 | F-EXP-01（unseen document ingestion）从未执行：没有任何证据证明"一份新规范仅经 admission+ingest+index 即查询可用"在 BREA 当前机制下成立 |

## 判定

```text
Normal vs Structural 的区分在概念上成立，且 E1 证明其在"已支持结构内"可实现；
但 v0.3 证据表明当前数据模型不足以让该区分稳定成立：
  - "新条款/新表格/新措辞"（Normal）→ 当前模型可零代码（E1 已证）
  - "新专业家族/新推理原语"（Structural）→ 需要 Candidate N+1（E2 证明正确归属）
  - 灰色地带：同一结构的新实例却被写成新代码（v0.3 防火分区是否属此？）
    → 需要 Regulation IR / 声明式规则引擎将该灰色地带推向 Normal Growth

结论：该区分**可达成但有条件** —— 条件是知识（条款/表格/条件/数值语义）充分外置于
数据模型。当前 v0.3 只部分外置（FIRE_COMPARTMENT 是数据，但匹配/解析/派生仍依赖
Python 逻辑与契约缺口）。这直接支撑 H-03 的收窄结论（见 Falsification Ledger）。
```

## 下一候选必须证明的 Scale Invariant

```text
对一份"已支持结构类"的新规范（unseen）：
  admission + ingest + normalize + index（零 Agent 代码）
  → 精确引用/条款定位可用
  → 新自然语言措辞可检索
  → 专业契约（PC-01..07）仍成立
（即 Review Contract §25 的 proof target）
```

若该证明无法在所选架构内设计成立，则该架构的可扩展性声明为弱。
