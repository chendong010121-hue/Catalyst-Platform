# UNDERSTANDING CAPABILITY SCORECARD — V0.1（D0 · §14）

> 盲理解能力评分（多维，非单一分数）。每维 PASS/PARTIAL/FAIL。

| UC | 维度 | 判定 | 依据 |
|---|---|---|---|
| UC-01 | Product-purpose recovery | **PASS** | 盲目的与 01-A 高一致；与 BREA 目的互补无矛盾（见对比） |
| UC-02 | Intended-capability coverage | **PARTIAL** | 16 条要求覆盖 design spec/AGENTS/charter/golden 审计核心；未穷尽 1103 行规格与全部 sdd 报告（采样深度有限） |
| UC-03 | Intent vs implementation separation | **PASS** | 每个 REQ 有 implementation_status；明确"声明≠实现"（检索/答案/导出/网络=INTENDED_NOT_IMPLEMENTED） |
| UC-04 | False implemented-claim control | **PASS** | 所有 IMPLEMENTED 均以代码/测试/配置实证；无"仅 Prompt/README 描述→IMPLEMENTED" |
| UC-05 | Functional decomposition quality | **PASS** | 15 个 LF 以责任为主恢复，含 I/O/耦合/可替换边界；未套用 BREA FN 模板（冻结前） |
| UC-06 | Domain / Enterprise separation | **PASS** | Domain 意图（词汇/来源/适用性/证据/不确定）与 Enterprise 意图（归属/约束/验收）显式分离（§9/§10 输出） |
| UC-07 | Evidence traceability | **PASS** | 全部主张挂 BLD-E 证据索引（20 项）→ legacy 文件；无未锚定主张 |
| UC-08 | Confidence calibration | **PASS** | PROVEN=11/STRONGLY=8/WEAKLY=2/UNKNOWN=0；置信类与证据强度一致；未作概率数学 |
| UC-09 | Missing/partial capability detection | **PASS** | 16 条状态全覆盖（IMPLEMENTED 6/PARTIAL 4/INTENDED_NOT_IMPLEMENTED 6/UNKNOWN 0）；两处 CONTRADICTED 如实保留 |
| UC-10 | No architecture-answer leakage before freeze | **PASS** | FORBIDDEN_SOURCES_DECLARATION 冻结于快照前；盲输出仅引 legacy 2.0 工作区文件；对照仅在冻结后 |

## D0 总判定（§14）

- 强制维度 UC-01/02/03/04/06/07/10：无 FAIL ✓（UC-02 PARTIAL 允许）。
- 无 material unsupported requirement 被提升为 PROVEN ✓（PROVEN 全部代码/测试实证）。
- 无 material implemented capability 仅凭 Prompt/README 意图声明 ✓。
- 研究触发（§15 R-U1..R-U8）：**NO**——目的未漏（R-U1）、能力未系统漏（R-U2）、意图/实现未混（R-U3）、企业意图可分离（R-U4）、证据落地（R-U5）、分解以责任为主（R-U6）、置信可靠（R-U7）、无手动种子（R-U8）。

## **D0 STATUS: PASS**

（PASS 为 DeepSeek 自评；最终判定由 ChatGPT 外部审查作出——D0-21 不自授权 D1。）
