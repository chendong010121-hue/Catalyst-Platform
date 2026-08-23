# CASE 01-E / E2 — ENTRY BOUNDARY — V0.1（E1 · §31）

> E1 输出（进入边界）。**E1 不授权 E2。**

```text
V0.2 CANDIDATE MATURITY
case-01.brea @ 0.2-candidate
GENERALIZED LOCAL EVIDENCE QUERY PROVEN（未准入、未绑定）
仍 ≠ production-ready Building Regulation Agent

LOCAL-QUERY BEHAVIORS PROVEN
QMODE-01 explicit standard + clause locator        → verbatim clause evidence
QMODE-02 explicit standard + missing clause        → no_reliable_evidence（不编造）
QMODE-03 local topic evidence search               → bounded source-backed candidates
QMODE-04 explicit table / table-region query       → verbatim table region
QMODE-05 existing professional applicability       → T-C01 / T-C02 / T-C03 preserved
（查询模式通过 metadata query_mode/standard_id 可观察；检索 ≠ 适用性判定）

BENCHMARK COVERAGE
B-E1-01..13 全部 PASS（evidence/E1_BENCHMARK_RESULTS_V0.1.json）
7 个未预先编码的查询成功（≥3 要求）
anti-hardcode review PASS

REMAINING HARDCODED / PARSER LIMITATIONS
- 语料仅两份本地规范（GB55037-2022、DBJ33/T1021-2023）；无第三份规范
- 表格解析依赖该来源格式的通用 caption 模式；无法可靠解析的表格 fail closed
- 主题检索为确定性 n-gram 词法打分（无语义/同义词理解）
- 专业适用性仍限于既有规则（防火间距 / 配建指标两条主线）

CURRENT PRODUCT GAPS
- Web 回退 / 官方来源核验 / URL 补充：无（scope excluded）
- RAG / LLM / Loop / Memory：无（scope excluded）
- 多轮交互 / 前端 / 后端产品壳：无
- 更广泛专业覆盖（更多规范、更多条款/表格类型）：未做
- 真实专业评估（建筑师/审图/消防审查）：未做

BUILDER-DEVELOPMENT EVIDENCE
E1_AGENT_DEVELOPMENT_TRACE_V0.1.md + builder/E1_BUILDER_RUN_REPORT_V0.1.md
BUILDER GAP（01-C builder 不能消费专业变更）→ Case-local change mechanism 已实现
Agent identity 在 Candidate N+1 中保持（case-01.brea 谱系不变）

DOMAIN / ENTERPRISE ISSUES EXPOSED
- Domain：OCR 语料质量（页脚数字、分页内嵌）限制表格/条款解析边界；需专业复核
- Domain：专业适用性规则覆盖窄（两条主线），扩展需 Domain 权威输入
- Enterprise：仍为 attribution only（OBL-06）；无 IAM/RBAC/策略（正确未实现）

PLATFORM GAPS EXPOSED
- Builder 变更机制：CASE-PROVEN（Case-local）；泛化候选需跨 Agent 证据
- G-D1-01..05 状态不变；无自动提升；无 GENERIC 声明
- D2 admission/binding 机制概念上可复用于未来 v0.2 准入（需单独准入阶段）

RECOMMENDED NEXT PROFESSIONAL-COMPLETION SLICE
E2 — Local Professional Coverage Expansion（建议，未开始）：
  在现有确定性证据管线内扩展第三/更多本地规范并复制 QMODE 证据模式，
  或扩展既有规范的条款/表格覆盖并做 Domain 复核。
  （如证据显示更重要瓶颈，E1 保留调整建议的权利——但 E1 未开始任何切片。）

E2 AUTHORIZATION
NO（NOT AUTHORIZED）
```

**E1 已 STOP。** E2 未开始。DeepSeek 不授权自身；E2 需 User/Release 权威单独授权。
