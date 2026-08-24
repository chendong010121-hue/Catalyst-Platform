# NEXT CANDIDATE ARCHITECTURE DECISION — V0.1（HANDOFF）

> Review Contract §25. Designs (does NOT execute) the next-Candidate proof, and
> states the architecture recommendation + the bounded experiment required before
> the final architecture can be frozen.

## Decision summary

```text
FINAL ARCHITECTURE
NOT SELECTED YET（INSUFFICIENT EVIDENCE — BOUNDED EXPERIMENT REQUIRED）

RECOMMENDED DIRECTION（证据支持的收窄）
B-MIN（轻量 RegulationUnit + 确定性推理 + exact/lexical/metadata 检索 + 确定性验证）
  作为下代候选架构方向；最终冻结前须执行 F-EXP-01 与 F-EXP-03。

EXCLUDED（当前证据不支持）
  D（LLM 辅助专业推理）— H-06 PARTIALLY FALSIFIED
  C（hybrid + bounded LLM）— H-05/H-06 无必要性证据
  dense / rerank / Vector DB / Web / Upload — DEFER / REJECT / 长程边界
```

## Next-Candidate proof target（Contract §25 — 设计，不执行）

```text
freeze next Candidate implementation
↓
introduce an unseen but supported regulation / source revision
↓
source admission + ingestion + index only
↓
NO Agent source change
↓
ask previously unseen natural-language questions
↓
retrieve correct evidence
↓
apply professional contracts (PC-01..07)
↓
bind citations / numeric derivation
↓
fail closed when applicability cannot be established

直接测试：Corpus Growth != Code Growth
```

若所选架构无法陈述此证明如何通过，其可扩展性声明为弱。

## 执行前必须的有界实验（本 Review 不执行）

### F-EXP-01 — UNSEEN DOCUMENT INGESTION（决定 H-02/H-04 与 B-MIN 核心主张）

```text
问题：一份"同结构类"的 unseen 规范，能否仅经 admission+ingest+index 进入可用状态
      （零 Agent 代码）？
方法：使用 1 份 lab/非生产源（记录 provenance：来源/版本/日期/SHA），
      走 admit→normalize→index→query 最小管线；记录：
        Agent source files changed?  Domain schema changed?  index only?
        exact citation possible?  professional contract（PC-01..07）成立?
最小规模：1 份 unseen 同结构类源 + ≥5 条未编码查询（含同条款不同措辞）。
通过标准：零 Agent 代码、索引唯一变更、引用/契约成立 → B-MIN 核心主张获证；
失败标准：必须改 Agent 代码 → 退回 A' 或升级 C 的重新设计。
```

### F-EXP-03 — RAW CHUNK vs MINIMUM REGULATION IR（决定 H-07 与 IR 深度）

```text
问题：raw chunks + metadata + 确定性规则 是否已能满足 PC-01..07（则最小 IR 可更小），
      还是必须 RegulationUnit 字段（scope/condition/numeric/derivation）？
方法：取 5 种代表规则形式（直接条文 / 条件编号规则 / 表格规则 / 例外排除 / 派生数值修正）
      各 ≥1 实例；分别以 (a) raw chunk + 规则逻辑、(b) 最小 RegulationUnit 满足 PC-01..07；
      记录契约满足度与代码/数据变更面。
通过标准：确定 RegulationUnit 最小字段集（可能增删本 Review 提案字段）。
```

### 后续条件实验（仅在 F-EXP-01/03 出现缺口时）

```text
F-EXP-02（lexical vs dense）：unseen 措辞 recall 缺口存在时才评估 dense。
F-EXP-04（deterministic vs LLM per responsibility）：某责任确定性真实失败时才对照。
```

## 下代候选必须证明（v0.4 或等价 N+1，未授权）

```text
1) unseen-source 零 Agent 代码进入（F-EXP-01 通过后）
2) PC-01..07 全部作为 validator 契约 + 回归用例通过
3) RegulationUnit 最小字段集支撑 5 种代表规则形式（F-EXP-03 通过后）
4) exact+lexical+metadata 对 unseen 措辞 recall/precision 保持
5) 五身份版本模型（corpus 修订不触发 agent 版本）可操作
6) 无 LLM/dense/Vector DB/Web/Upload 依赖
```

## 触发条件

```text
F-EXP-01/03 需外部架构评审 + 单独授权；本 Review 不执行、不 spike。
E2-C 与 v0.4 均未授权。
```
