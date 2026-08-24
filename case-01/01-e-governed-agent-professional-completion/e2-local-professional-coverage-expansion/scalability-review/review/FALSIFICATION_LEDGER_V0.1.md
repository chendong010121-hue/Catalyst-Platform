# BREA FALSIFICATION LEDGER — V0.1

> Review Contract §3/§22. Central artifact. Every hypothesis is written with working
> hypothesis, strongest supporting evidence, strongest disconfirming evidence,
> falsifier attempted, result, confidence, unresolved uncertainty, architecture
> consequence. Disconfirming evidence is never omitted.

---

## H-01 — OPEN PRODUCT CLASSIFICATION

```text
WORKING HYPOTHESIS
BREA is naturally an OPEN KNOWLEDGE / OPEN QUERY product.

STRONGEST SUPPORTING EVIDENCE
- E1 PCR: "让 BREA 能够对已经接入的本地建筑规范进行一般化查询"（open query 意图）
- E1 反 fixture 审查：7 个未编码查询成功（B-E1-01/02/03/05/06/07/09）→ 查询面开放
- E2 新增第三专业家族（防火分区）→ 专业面开放（知识面预期增长）
- PCE 包络：Query Space = OPEN NATURAL LANGUAGE（有运行证据）

STRONGEST DISCONFIRMING EVIDENCE
- 当前语料恰为 2 份本地规范（固定）；无用户上传、无受控 Web、无异构格式
- 产品权威从未正式声明开放包络；E2 规格 §5 明确把 Web/RAG 排除于当前面
- "OPEN" 有界：开放的是查询面 + 有界本地知识面，不是任意知识/任意来源

FALSIFIER ATTEMPTED
寻找"有限/封闭文档集 + 有限问题族 + 无上传/无增长/无 Web/无开放措辞"的产品边界。
产品权威（User）未提供此类边界；变更请求语言明确使用"一般化查询/更广覆盖"。

RESULT
NOT FALSIFIED（有界 OPEN：查询面开放已证；知识面开放为预期）
CONFIDENCE
HIGH（查询面）；MEDIUM（知识面规模）
UNRESOLVED UNCERTAINTY
知识面增长速率（LOW 现实值 vs MEDIUM 预期值）未经验证；
"开放"是否扩展到 user upload / web / 异构格式 属于长程设计边界，未授权。

ARCHITECTURE CONSEQUENCE
查询面开放 → 检索/理解机制必须应对未编码措辞（E1 已证可确定性地做）
知识面有界开放 + 预期增长 → 数据/索引/版本分离值得纳入架构（但必要性未证）
```

---

## H-02 — CORPUS GROWTH SHOULD NOT REQUIRE PROPORTIONAL CODE GROWTH

```text
WORKING HYPOTHESIS
ordinary new regulations should enter through data ingestion / index revision,
not per-document Agent code changes.

STRONGEST SUPPORTING EVIDENCE
- E1 证明"已支持结构内的新条款/新表格/新措辞"零代码（7 未编码查询）
- E2 v0.3 把 FIRE_COMPARTMENT 规则表声明为数据 → 知识外置方向可行
- Change-Cost 分类显示：new paraphrase 已零代码；add ordinary regulation 的理想 owner 是 DATA

STRONGEST DISCONFIRMING EVIDENCE
- E2 新增防火分区家族时实际修改了 4 个 Python 模块（coverage/facts/runner/identity）
- 无 F-EXP-01（unseen document ingestion）证据：从未证明"新规范仅经
  admission+ingest+index 即查询可用"在 BREA 当前机制下成立
- 若"新专业家族"本质上属 Structural Growth（新推理原语），则代码变更合法，
  H-02 的"proportional code growth"批评对 Structural 情形不适用

FALSIFIER ATTEMPTED
寻找"代表性普通规范反复引入全新专业原语，即使合理 schema/数据抽象后仍必须
per-source 代码"的证据。现有证据不足以判此：只有一个家族（防火分区）样本，
且该家族是否为"普通规范"或"新推理原语"存在解释分歧。

RESULT
INSUFFICIENT EVIDENCE（无法判定；需 F-EXP-01 unseen-source 实验）
CONFIDENCE
LOW-MEDIUM
UNRESOLVED UNCERTAINTY
一份与既有结构同类的 unseen 规范，能否零 Agent 代码进入可用状态？
（这是 Review Contract §25 的核心证明目标，尚未执行）

ARCHITECTURE CONSEQUENCE
不能仅凭当前证据断言"ingestion 必须建"；但也不能断言"当前模式够用"。
下一步候选必须设计并证明 §25 的 unseen-source 证明。
```

---

## H-03 — CURRENT FAMILY-SPECIFIC DETERMINISTIC REASONING DOES NOT SCALE

```text
WORKING HYPOTHESIS
question family → new facts → new parser → new applicability branch → new runner
dispatch is not a sufficient long-term architecture.

STRONGEST SUPPORTING EVIDENCE
- E2 v0.3 新增家族 = 4 模块代码变更（facts+coverage+runner+identity）
- v0.3 Freeze 缺陷 PC-01..04 证明"家族专用代码"产生专业契约缺口：
  PC-01 正向适用性不完整、PC-02 地下区分不完整、PC-04 派生数值轨迹缺结构化
- 每次新家族都需人写新 Python（当前无声明式规则引擎）

STRONGEST DISCONFIRMING EVIDENCE
- v0.3 同时证明"规则表外置为数据"可行：FIRE_COMPARTMENT 是声明式数据，
  同一 coverage.py 的 parse/match 逻辑对同类编号子项通用
- AB-T13 构造自测通过：证明"声明式数据 + 通用解析器"在已覆盖家族内有效
- 即：缺陷的根源可能是"知识外置不充分/数据模型太浅"，而非"确定性推理不可扩展"

FALSIFIER ATTEMPTED
检验 falsifier："最小重构的确定性架构能否以声明式数据/配置为主表达多个
实质不同的规范家族，同时通用代码保持稳定？"
当前证据：部分支持（规则数据化可行），但数据模型缺 scope/zone/numeric-trace 字段
（PC-01/02/04）→ 重构后能否满足 PC-01..07 未经验证。

RESULT
PARTIALLY FALSIFIED（收窄）："家族专用 Python 分支模式不够"成立；
"确定性推理本质上不可扩展"未成立（可被更充分的数据模型修复）
CONFIDENCE
MEDIUM-HIGH（收窄结论）；LOW（"必须 LLM"的反向推论）
UNRESOLVED UNCERTAINTY
最小充分数据模型（RegulationUnit 深度）需 F-EXP-03 界定；
FIRE_COMPARTMENT 式声明 + 更强 schema 是否满足 PC-01..07 需实验。

ARCHITECTURE CONSEQUENCE
支持"KNOWLEDGE MUST MOVE OUT OF CODE"（Review Contract §4 明示的合法结论）。
架构 A/B 优于 C/D 的方向得到证据支撑；A vs B 的边界仍需 F-EXP-03。
```

---

## H-04 — SCALABLE INGESTION / INDEXING IS REQUIRED

```text
WORKING HYPOTHESIS
BREA needs a stable path: Document → Parse/OCR → Normalize → Structured Units →
Metadata → Index → Queryable.

STRONGEST SUPPORTING EVIDENCE
- Change-Cost 分类：add ordinary regulation / replace edition 的理想 owner 是 DATA，
  而当前无 ingest/index/version 层
- E1/E2 均为运行时 parse-on-demand（每次查询重解析全文）→ 语料增长时成本线性上升
- 外部机制（RAGFlow/LlamaIndex/Haystack）普遍提供 ingestion pipeline（机制事实，
  非架构权威）

STRONGEST DISCONFIRMING EVIDENCE
- 当前语料仅 2 份；parse-on-demand 在现有规模下工作良好（E1/E2 全通过）
- 无证据显示用户上传或高增长即将到来（均为预期/长程）
- Review Contract §4 禁止"因为 RAG 框架有 ingestion 就说必要"

FALSIFIER ATTEMPTED
检验 falsifier："产品范围足够小/静态，直接语料解析在相同可维护性与
用户上传/更新成本下复杂度更低。"
当前 2 源 + parse-on-demand 确实满足；但"小/静态"本身是预期而非事实。

RESULT
INSUFFICIENT EVIDENCE（"必要"未证；"当前直接解析够用"也未证未来）
CONFIDENCE
MEDIUM（当前够用）；LOW（长期必要）
UNRESOLVED UNCERTAINTY
增长速率与 unseen-source 需求决定 ingest/index 是否必要（F-EXP-01）。

ARCHITECTURE CONSEQUENCE
不建大型 ingestion 子系统；但最小"稳定 admit→normalize→index"路径是
下代候选的可选结构（若 §25 证明需要）。不得以 RAG 框架存在为由判定必要。
```

---

## H-05 — HYBRID RETRIEVAL IS A STRONGER LONG-TERM FIT THAN SINGLE-MODE

```text
WORKING HYPOTHESIS
exact locator + lexical/BM25 + metadata + optional dense semantic retrieval
is likely a better fit than a single retrieval mode.

STRONGEST SUPPORTING EVIDENCE
- 外部机制普遍采用 hybrid（RAGFlow/LlamaIndex/Haystack 检索层事实）
- 未来语义措辞面扩大时，lexical 可能有 recall 缺口（预期）

STRONGEST DISCONFIRMING EVIDENCE
- E1 证明 exact + lexical(n-gram) 对 7 个未编码查询（含同条款不同措辞 B-E1-02）
  完全够用；无 dense 必要
- 当前语料仅 2 份、查询面为规范术语（术语高度规范，lexical 命中率高）
- 无 F-EXP-02 证据证明 dense 带来实质收益

FALSIFIER ATTEMPTED
检验 falsifier："exact + lexical + metadata 在代表性 paraphrase/locator 工作负载上
达到所需 recall/precision，dense 无实质收益或风险成本不可接受。"
E1 的 7 个未编码查询构成初步支持，但样本小、无 F-EXP-02 正式对照。

RESULT
PARTIALLY FALSIFIED / NARROWED → "NO DENSE RETRIEVAL YET"
（hybrid 作为未来选项保留，但 dense 当前无必要性证据）
CONFIDENCE
MEDIUM-HIGH（当前不需要 dense）；LOW（未来是否需要）
UNRESOLVED UNCERTAINTY
语义 paraphrase 面扩大后的 recall 缺口是否真实（F-EXP-02 待跑）。

ARCHITECTURE CONSEQUENCE
Retrieval 架构 = exact + lexical + metadata（REQUIRED NOW）；
dense = OPTIONAL UPGRADE / DEFER，不在下代候选承诺之列。
```

---

## H-06 — LLM IS NEEDED FOR SOME OPEN-LANGUAGE / REASONING RESPONSIBILITIES

```text
WORKING HYPOTHESIS
LLM may be useful for question understanding / fact extraction / query rewriting /
candidate applicability reasoning / cross-clause synthesis / answer composition.

STRONGEST SUPPORTING EVIDENCE
- 外部机制中 LLM 广泛用于语言类任务（事实，非权威）
- 未来开放式自然语言面扩大时，确定性解析可能遇到措辞多样性（预期）

STRONGEST DISCONFIRMING EVIDENCE（per responsibility）
- question understanding：E1 classify_query（正则/别名/n-gram）处理 7 未编码查询成功
- fact extraction：normalize_facts + required facts 已覆盖既有家族（AB-T13）
- query rewriting：E1 B-E1-02 同条款不同措辞 → 无需改写即命中
- applicability candidate reasoning：FIRE_COMPARTMENT 条件匹配已工作（AB-T13）
- cross-clause synthesis：当前无跨条款合成需求证据
- answer composition：build_result 已工作
- 每个已测试责任都有工作的确定性实现；无证据显示任一责任当前需要 LLM

FALSIFIER ATTEMPTED
对每个责任检验 falsifier："确定性/schema 方法以显著更低风险成本达到所需
覆盖/准确/可维护/措辞鲁棒。"
已测责任：成立（E1/E2 证据）。未测责任（大范围开放式措辞、跨条款合成）：无证据。

RESULT
PARTIALLY FALSIFIED（当前包络内：无任何责任被证明需要 LLM）
CONFIDENCE
HIGH（当前不需要）；UNKNOWN（未来面）
UNRESOLVED UNCERTAINTY
开放式措辞扩大后的鲁棒性边界（F-EXP-04 可界定 per-responsibility 放置）

ARCHITECTURE CONSEQUENCE
LLM 不得进入当前架构的规范性结论路径（source existence/version/unsupported
numeric/final authority/citation 必须保持确定性或同等可审计控制）。
"LLM for query understanding only, NO LLM for normative conclusion" 是允许的
未来选项，但当前连前者都无必要性证据。
```

---

## H-07 — REGULATION INTERMEDIATE REPRESENTATION / DATA MODEL IS REQUIRED

```text
WORKING HYPOTHESIS
raw text chunks alone may be insufficient for robust professional applicability,
numeric derivation, exclusions, versioning and provenance.

STRONGEST SUPPORTING EVIDENCE
- PC-01（正向适用性不完整）：is_excluded 只查排除项，不校验"公共建筑"正向条件
  → raw text + 简单规则无法表达 scope 语义
- PC-02（地下设备房 vs 其他区域）：同一子项含两个条件-值对（1000/500），
  当前 match 只按 building_form 匹配 → 需要结构化 condition/exception 分解
- PC-04（派生数值轨迹）：1500×2.0=3000 无结构化 operand+modifier+derivation 记录
  → 需要 numeric operands/modifiers 字段
- Change-Cost：new table/appendix shape 需要 DOMAIN SCHEMA 级支持

STRONGEST DISCONFIRMING EVIDENCE
- E1 证明 raw text + verbatim 断言 + 定位器足以支撑"检索"契约（evidence retrieval）
- F-EXP-03（raw chunk vs Regulation IR）未执行：无法证明 large IR 必要
- Review Contract §13 禁止"仅因结构化数据吸引人就建大本体"

FALSIFIER ATTEMPTED
检验 falsifier："raw chunks + metadata + reasoning/verification 可满足
professional applicability / numeric / provenance 契约（代表规则形式）而无隐藏
非结构化知识所有。"
PC-01/02/04 显示 raw+浅规则不满足（正向 scope、zone 区分、派生轨迹）；
但"多深的结构才够"未界定。

RESULT
PARTIALLY SUPPORTED → 需要**最小** RegulationUnit（source/edition/locator +
typed condition/exception/numeric operands/modifiers/derivation），
不需要通用监管本体
CONFIDENCE
MEDIUM-HIGH（最小结构必要）；HIGH（大本体不必要）
UNRESOLVED UNCERTAINTY
最小结构的精确字段集（F-EXP-03 界定）；跨文档/权威冲突语义（长程）

ARCHITECTURE CONSEQUENCE
Regulation Data Model 决策：轻量 RegulationUnit（见专门决策文档），
不做通用 ontology；"哪些结构化、哪些按需抽取"按 F-EXP-03 证据确定。
```

---

## H-08 — DETERMINISTIC LOGIC SHOULD MOVE TOWARD CONTRACT / VALIDATOR ROLE

```text
WORKING HYPOTHESIS
knowledge-specific Python branches should decrease, while deterministic invariant
enforcement remains strong.

STRONGEST SUPPORTING EVIDENCE
- 全部验证不变量在 v0.1..v0.3 中均为确定性实现且有效：
  source identity / version（manifest SHA）/ evidence existence（verbatim 断言）/
  mandatory-fact completeness（missing_facts）/ unsupported numeric prevention /
  derived numeric trace（部分）/ exclusions / citation / provenance / fail-closed
- PC-01..04 是"知识表示"缺陷而非"验证机制"缺陷 → 验证层本身可靠
- E1 反 fixture：确定性验证未被 fixture 化

STRONGEST DISCONFIRMING EVIDENCE
- 无证据显示"更声明式/生成式验证"更强（未测试）
- 当前验证与知识混杂在 runner/coverage Python 中，难以单独审计

FALSIFIER ATTEMPTED
检验 falsifier："更声明式/生成式验证提供同等或更强的安全/可审计/可替换，
且无隐藏规范性推理。"
未测试；但当前确定性验证无失败证据，故无理由替换。

RESULT
NOT FALSIFIED（确定性验证是已证明的不变层；知识应向数据迁移）
CONFIDENCE
HIGH
UNRESOLVED UNCERTAINTY
验证与知识的解耦程度（是否独立 validator 层）属下代候选设计问题

ARCHITECTURE CONSEQUENCE
验证面保持确定性 + 强化（PC-01..07 成为 validator 契约/回归用例）；
知识从 Python 移向声明式数据。安全关键不变量不得为架构优雅而移除。
```

---

## 汇总

| Hypothesis | Result | Confidence | Architecture consequence |
|---|---|---|---|
| H-01 OPEN product | NOT FALSIFIED（有界 OPEN） | HIGH/查询面 MEDIUM/知识面 | 检索/理解须应对未编码措辞 |
| H-02 corpus≠code growth | **INSUFFICIENT EVIDENCE** | LOW-MEDIUM | 需 §25 unseen-source 证明（F-EXP-01） |
| H-03 family reasoning not scale | PARTIALLY FALSIFIED（收窄） | MEDIUM-HIGH | 知识移出代码；A/B 方向；PC-01..07 契约 |
| H-04 ingestion/indexing required | **INSUFFICIENT EVIDENCE** | MEDIUM/LOW | 最小 admit→normalize→index 可选；不因 RAG 建 |
| H-05 hybrid retrieval stronger | NARROWED → NO DENSE YET | MEDIUM-HIGH | exact+lexical+metadata；dense DEFER |
| H-06 LLM needed | PARTIALLY FALSIFIED（当前无责任需 LLM） | HIGH | LLM 不进规范结论路径；per-responsibility 复核 |
| H-07 Regulation IR required | PARTIALLY SUPPORTED → 最小 IR | MEDIUM-HIGH | 轻量 RegulationUnit；非大本体 |
| H-08 deterministic → validator | NOT FALSIFIED | HIGH | 验证保持确定性强化；知识数据化 |

**结论：现有 Case 证据足以收窄（拒绝 C/D 当前必要性、确认确定性验证、确认知识外置方向），
但不足以在 A vs B（是否需要正式 ingestion + 结构化 Regulation IR 管线）之间做出最终裁决 ——
该边界依赖 F-EXP-01（unseen source）与 F-EXP-03（raw chunk vs 最小 IR）证据。**
