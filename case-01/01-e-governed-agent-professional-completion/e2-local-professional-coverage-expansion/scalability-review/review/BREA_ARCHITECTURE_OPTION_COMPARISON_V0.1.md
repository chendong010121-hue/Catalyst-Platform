# BREA ARCHITECTURE OPTION COMPARISON — V0.1

> Review Contract §9/§10. Compare A/B/C/D seriously; E = insufficient evidence is a
> valid outcome. Score alone is insufficient — each major score carries
> evidence/reasoning. Preferred outcome: minimum sufficient mechanism.

## Options (Contract §9)

```text
A — CURRENT / REFACTORED DETERMINISTIC
   generic parser + declarative rules/config + lexical retrieval + deterministic verification
   thesis: current direction was not wrong; knowledge was simply in Python instead of data/schema

B — STRUCTURED KNOWLEDGE + DETERMINISTIC REASONING
   ingestion + Regulation IR / structured data + exact/BM25/metadata retrieval
   + generic deterministic rule engine + deterministic verification
   No LLM required for normative reasoning

C — HYBRID RETRIEVAL + BOUNDED LLM UNDERSTANDING
   ingestion + exact/BM25/metadata/dense as justified
   + LLM for language/fact/query understanding
   + structured applicability engine/validators + deterministic professional verification

D — HYBRID RETRIEVAL + LLM-ASSISTED PROFESSIONAL REASONING
   ingestion + hybrid retrieval + structured facts/Regulation data
   + LLM-assisted applicability/synthesis + strong evidence/numeric/authority verification
```

## Evaluation matrix (evidence-anchored)

| Criterion | A | B | C | D | Evidence / reasoning |
|---|---|---|---|---|---|
| ordinary corpus growth cost | MEDIUM | **LOW** | LOW | LOW | 无 ingest 则新规范仍手工 parse（A）；B/C/D 有 ingest |
| new regulation code-change freq | HIGH | **LOW** | LOW | LOW | A 靠规则数据化程度；B/C/D 靠 ingest+IR（但均为未验证假设） |
| open natural-language robustness | MEDIUM | MEDIUM | HIGH | HIGH | E1 n-gram 已证中等；C/D 的 LLM 提升未验证 |
| exact-locator precision | **HIGH** | **HIGH** | HIGH | HIGH | E1 QMODE-01 已证 |
| semantic paraphrase recall | MEDIUM | MEDIUM | HIGH(预计) | HIGH(预计) | E1 7 查询已证中等；无 dense 证据 |
| professional applicability accuracy | LOW（现状 PC-01..04） | **MEDIUM-HIGH（若 IR 足够）** | MEDIUM-HIGH | MEDIUM-HIGH(预计) | PC-01..04 证明 A 现状不足；B 需 F-EXP-03 验证 |
| numeric safety | MEDIUM | **HIGH** | HIGH | HIGH | A 派生轨迹缺结构化（PC-04）；B 结构化 operands/modifiers |
| source/version authority | LOW | **HIGH** | HIGH | HIGH | A 无版本模型；B/C/D 含 edition/effective status |
| cross-clause reasoning | LOW | MEDIUM | MEDIUM | HIGH(预计) | 无需求证据；D 的 LLM 合成未验证 |
| explainability | **HIGH** | **HIGH** | MEDIUM | LOW | A/B 确定性全可审计；C/D LLM 部分黑盒 |
| citation/provenance | **HIGH** | **HIGH** | MEDIUM | MEDIUM | verbatim 断言已证；LLM 需额外控制 |
| fail-closed quality | MEDIUM | **HIGH** | MEDIUM | MEDIUM | A 现状 PC-01/02 fail-closed 有缺口；B 结构化契约 |
| user-upload compatibility | LOW | MEDIUM | MEDIUM | MEDIUM | 长程；B/C/D 有 ingest 基础 |
| controlled-Web compatibility | LOW | MEDIUM | MEDIUM | MEDIUM | 长程；需 source-trust 语义（B 的 IR 更顺） |
| offline operation | **HIGH** | **HIGH** | MEDIUM | LOW | C/D 依赖外部 LLM |
| operational complexity | **LOW** | MEDIUM | MEDIUM-HIGH | HIGH | A 无 ingest/无 LLM；B 有 ingest；C/D 加 LLM |
| provider dependency | **NONE** | **NONE** | MEDIUM | HIGH | A/B 无外部 provider |
| replaceability | **HIGH** | HIGH | MEDIUM | LOW | A/B 组件简单可换；D 绑定 LLM 生态 |
| benchmarkability | MEDIUM | **HIGH** | MEDIUM | LOW | B 结构化可精确断言；D LLM 输出难稳定基准 |
| Case-local implementation cost | **LOW** | MEDIUM | MEDIUM-HIGH | HIGH | A 最小改动；B 建 IR/ingest；C/D 加 LLM 集成 |

## 关键证据锚点

```text
A 的缺陷（PC-01..04）→ 现状 A 不足以承载专业契约；但 A 的"重构版"（知识充分数据化）
   尚未被测试（F-EXP-03 才可区分 A' 与 B）
B 的强项（结构化 IR/版本/派生轨迹）→ 恰好对应 PC-01/02/04 的缺失结构 → B 方向被
   现有缺陷证据支持；但"需要多深结构"未证（F-EXP-03）
C/D 的强项（语义/合成）→ 全部为"预计"；无任何 Case 证据表明当前责任需要 LLM
   （H-06 PARTIALLY FALSIFIED）；成本/依赖/可审计风险显著更高
E（insufficient evidence）→ A' vs B 的边界依赖未执行实验（F-EXP-01/03）
```

## 明确排除的决策

```text
- 不得因外部框架使用 hybrid/LLM 就选 C/D（Review Contract §19：popularity ≠ evidence）
- 不得因 A 现状有缺陷就选 D（A 的缺陷 = 知识表示缺陷，可被 B 修复，无需 LLM）
- 不得仅因结构化数据吸引人建大 Regulation 本体（§13 禁止）
```

## 结论

```text
现有证据支持的收窄：
  D 作为当前必要性 → 证据不支持（H-06；成本/风险高）
  C 作为当前必要性 → 证据不支持（H-05/H-06；dense 与 LLM 均无必要性证据）
  A（重构版：知识外置 + 确定性验证）→ 方向被 E1/E2 证据支持，但充分性未验证
  B（结构化 IR + 确定性推理）→ 方向被 PC-01/02/04 缺陷支持，深度未验证
  E → A' vs B 的最终裁决依赖 F-EXP-01/F-EXP-03

MINIMUM SUFFICIENT 判定（本 Review 阶段）：
  在 A' 与 B 之间，B 的最小版本（轻量 RegulationUnit + 稳定 ingest/normalize/index +
  确定性规则引擎 + 确定性验证）与现有缺陷证据（PC-01/02/04）最为吻合，
  且不引入 LLM/dense 依赖 —— 但其"最小结构深度"必须由 F-EXP-03 界定，
  其"零代码 unseen-source 进入"必须由 F-EXP-01 证明。
  因此：**推荐 B 作为下代候选架构方向，但最终裁决为 E —— 需先执行两个有界实验。**
```

## 最终 Review 输出状态

```text
CURRENT SCALABILITY DIAGNOSIS  : PARTIALLY FALSIFIED（收窄）
  正确部分：OPEN query / 知识外置方向 / 验证确定性
  错误部分："LLM/RAG 可能必要"—— 当前无证据；"当前模式完全错误"—— 未成立
SELECTED MINIMUM SUFFICIENT    : B 方向（轻量 IR + 确定性）候选
BUT FINAL ARCHITECTURE         : INSUFFICIENT EVIDENCE — BOUNDED EXPERIMENT REQUIRED
  （A' vs B 边界、unseen-source 证明需 F-EXP-01/F-EXP-03）
```
