# BREA SCALABLE RETRIEVAL & REASONING ARCHITECTURE REVIEW — V0.1

> Final Review per Review Contract §29. Falsification-first; minimum sufficient
> mechanism preferred over maximum future-proof stack.

---

## 1. Was the diagnosis that BREA's current implementation model does not scale actually correct?

```text
PARTIALLY CORRECT — 且比假设更窄。

正确部分：
  A) 查询面是 OPEN：E1 反 fixture 证明 7 个未编码查询成功（B-E1-01/02/03/05/06/07/09）。
  B) 知识外置方向正确：v0.3 把 FIRE_COMPARTMENT 声明为数据，同类编号子项可复用解析器。
  C) 确定性验证可靠：source identity / verbatim / missing-facts / fail-closed 全部有效。

错误/过度部分：
  D) "LLM/RAG 可能必要" —— 无任何 Case 证据显示当前责任需要 LLM（H-06 PARTIALLY FALSIFIED）。
  E) "当前模式完全错误" —— 未成立：缺陷是知识表示缺口（PC-01/02/04），可被更充分的
     数据模型修复，无需放弃确定性（H-03 收窄）。
  F) "ingestion/indexing 必然需要" —— 当前 2 源 + parse-on-demand 工作良好；
     "必要"无证据（H-04 INSUFFICIENT EVIDENCE）。
```

## 2. Which part was correct? Which part was wrong?

| 判断 | 对/错 | 证据 |
|---|---|---|
| OPEN QUERY 成立 | 对 | E1 7 未编码查询 |
| 知识应移出代码 | 对 | PC-01..04 + Change-Cost 分类 |
| 确定性验证保留 | 对 | v0.1..v0.3 验证机制无失败证据 |
| LLM/RAG 必要 | 错（无证据） | H-06 |
| dense 检索必要 | 错（当前无证据） | H-05 → NO DENSE YET |
| 大型 ingestion 必然 | 未定（INSUFFICIENT） | H-04 |
| 当前模式完全不可扩展 | 未定（部分收窄） | H-03 |

## 3. What should normally change when new knowledge arrives?

```text
新知识（新规范/新版本/新条款/新表格/新措辞）默认应只引起：
  DATA / CORPUS REVISION（admission + ingest + normalize + index update + evaluation）
Agent 代码不变；模型不变（Scale Invariant Class 1）。
关键条件：知识充分外置于 RegulationUnit（本 Review 的 Regulation Data Model 决策）。
```

## 4. What should require a new Agent Candidate?

```text
新能力（新推理原语 / 新验证义务 / 新权威冲突语义 / 高风险安全契约）
→ DOMAIN SCHEMA change + Candidate N+1（Scale Invariant Class 2）。
E2 的防火分区家族若为"新推理原语"则合法触发 v0.3；
但同类结构的"新实例"不应要求新候选（灰色地带须由 IR/规则引擎吸收）。
```

## 5. What retrieval mechanism is minimally sufficient?

```text
REQUIRED NOW : exact locator + lexical(n-gram 现行) + metadata filter
DEFER        : dense semantic / rerank / cross-document
REJECT       : Vector DB 产品决策（本 Review 范围外）
证据：E1 7 未编码查询（exact+lexical+metadata 已证充分）；H-05 收窄。
```

## 6. Where, if anywhere, is LLM justified?

```text
当前：无处 justified —— 每个已测试责任都有工作的确定性实现（H-06 PARTIALLY FALSIFIED）。
未来候选场景（无证据、纯预期）：
  - 大规模开放式措辞的问题理解（若确定性 recall/鲁棒性出现真实缺口 → F-EXP-04 对照）
  - 跨条款/跨文档合成（先试确定性组合，B 方向；LLM 为最后选项）
LLM 永不进入：source existence / version / unsupported numeric / final authority /
citation binding（除非同等可审计控制，Contract §15 强制）。
```

## 7. What must remain deterministic / strongly verified?

```text
验证面全部（source identity/version/evidence/citation/facts/preconditions/numeric/
exclusions/provenance/fail-closed）+ 新增 V-GAP-01..04（PC-01..04 的 validator 契约）。
H-08 NOT FALSIFIED：安全关键不变量不得为架构优雅而移除。
```

## 8. Does BREA need a Regulation IR, and how much?

```text
需要"最小 RegulationUnit"（非大本体）：
  source_id / edition+effective status / jurisdiction / unit_type / locator /
  subject / scope_conditions / exceptions / conditions / numeric_operands /
  numeric_modifiers / derivation_trace / raw_evidence / source_sha256
证据：PC-01（scope）、PC-02（condition 分解）、PC-04（numeric operands/modifiers/
derivation）—— 恰好是当前缺失的结构。
不做：通用监管本体 / 跨引用全结构化 / 提示文本结构化（Contract §13 禁止）。
```

## 9. How do Agent Version, Corpus Revision, Index Revision, Domain Schema Version, Evaluation Version differ?

```text
五身份分离（BREA_VERSION_AND_REVISION_MODEL 决策）：
  Agent：能力（代码/推理）
  Corpus：接纳哪些源/版本（edition/effective status）
  Index：语料的检索表示
  Domain Schema：RegulationUnit/事实/契约结构
  Evaluation：benchmark/gold/契约修订
不变量：Agent Evolution != Knowledge Evolution（E1/E2 已实证；RegulationUnit 使其稳定成立）。
```

## 10. What exact next Candidate architecture should be tested?

```text
推荐方向（B 的最小形态）—— 但最终裁决为 INSUFFICIENT EVIDENCE，需先两个有界实验：

  B-MIN：
    admit → normalize → ingest（轻量 RegulationUnit）→ index
    + exact/lexical/metadata 检索
    + 通用确定性规则引擎（条件匹配 + scope/exceptions 校验 + numeric 派生轨迹）
    + 确定性验证（PC-01..07 validator 契约）
    + 五身份版本模型
  不包含：dense / rerank / LLM / Vector DB / Web / Upload。

  该方向与 PC-01/02/04 缺陷证据吻合，且不引入 LLM/dense 依赖 —— 最小充分候选。
  但 "A'(重构确定性) vs B(正式 IR+ingest)" 的边界与 "unseen-source 零代码进入"
  必须由 F-EXP-01 / F-EXP-03 证明后才能冻结为下代候选架构。
```

## 11. What evidence would still prove that recommendation wrong?

```text
F-EXP-01（unseen source ingestion）：
  若一份同结构类 unseen 规范经 admit+ingest+index 后仍必须改 Agent 代码才能
  满足专业契约 → B-MIN 的"corpus≠code growth"核心主张被证伪 → 需重新设计
  （可能退回 A' 或升级为 C）。

F-EXP-03（raw chunk vs 最小 IR）：
  若 raw chunks + metadata + 确定性规则已能通过 PC-01..07（无需 RegulationUnit 字段）
  → 最小 IR 可再缩小（更接近 A'）；若最小 IR 仍不够 → 需更多结构化（加深 IR）。

F-EXP-02 / F-EXP-04：
  若 lexical 在 unseen 措辞出现实质 recall 缺口 → dense（OPTIONAL UPGRADE）；
  若确定性在某责任出现真实失败 → 该责任才考虑 LLM（per-responsibility）。

任何显示"当前包络其实 CLOSED/FIXED"的产品权威证据 → 收窄为 A'。
```

---

## 12. Final Review Statement（Contract §29 逐问回答）

```text
1) 诊断是否成立？        PARTIALLY CORRECT（开放查询/知识外置/确定性验证对；LLM/RAG 预设错）
2) 哪部分对/错？         对：OPEN QUERY、知识外置、确定性验证。错：LLM/dense 必要性预设。
3) 新知识应改变什么？     DATA/CORPUS/INDEX 层（admission+ingest+normalize+index+evaluation）
4) 什么需要新候选？      新推理原语/验证义务/权威语义 → Candidate N+1
5) 最小充分检索？        exact + lexical + metadata（dense DEFER）
6) LLM 在哪 justified？  当前无处；未来仅限语言类责任（有真实缺口后，per-responsibility）
7) 什么必须确定性？      全部验证不变量 + 规范结论 + 派生数值轨迹
8) Regulation IR？       需要最小 RegulationUnit（非大本体）
9) 五身份如何区分？      Agent≠Corpus≠Index≠Schema≠Evaluation（已决策）
10) 下代候选架构？       B-MIN 方向（IR+确定性）为候选；但先需 F-EXP-01/F-EXP-03
11) 什么能推翻？         unseen-source 需改代码 / raw chunk 足够 / 产品包络收窄

VERDICT
PARTIALLY FALSIFIED — NARROWER ARCHITECTURE RECOMMENDED
+ 
INSUFFICIENT EVIDENCE — BOUNDED EXPERIMENT REQUIRED
（最终架构裁决前须执行 F-EXP-01 与 F-EXP-03；不得自行执行）

READY FOR EXTERNAL ARCHITECTURE REVIEW
```

---

## 13. Verdict model（Contract §28）

```text
REPORTED STATUS
PARTIALLY FALSIFIED — NARROWER ARCHITECTURE RECOMMENDED
（叠加）INSUFFICIENT EVIDENCE — BOUNDED EXPERIMENT REQUIRED

NOT AUTHORIZED（本 Review 未授权，也不自我授权）
  v0.4 Candidate / E2-C / Method 永久修订 / Platform 变更
```
