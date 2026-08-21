# BUILDER-CONSUMABLE DEFINITION — V0.1 (CASE 01-B / B11) — REPAIRED (B-01/B-02, 2026-08-20)

> 目标：让未来 Builder Agent 可**确定性消费**而无需发明架构。Markdown 可接受（01-B 不实现 parser/schema 引擎）。
> 本文件是 01-B 的**主输出之一**；它引用/内联全部受治理定义，且**不得被 Builder 反向发明**。

## 1. AGENT IDENTITY

```text
ID            BREA — Building Regulation Evidence Agent (CASE 01 Governed Candidate)
VERSION        v0.1 (design)
STATE          DESIGN
OWNER          USER / CASE 01 PRODUCT-RELEASE AUTHORITY (F-07)
DOMAIN         Building Regulation / Engineering Construction Standards — architecture_pre_design
```

## 2. PROFESSIONAL PURPOSE（冻结）

> 使用项目上下文，为建筑方案/初步设计工作提供可靠、适用、可追溯的建筑工程规范证据，并在可靠证据不可用时显式返回不确定性或 fail-closed 结果。

独立于 Catalyst；不得写入 "test Catalyst / validate Platform / prove Runtime"。

## 3. OWNER / ENTERPRISE / DOMAIN

- OWNER: USER / CASE 01 Product-Release Authority。
- ENTERPRISE CONTEXT: provisional local pilot（organization_id/user_id/可选 project_id 归属回显；无 IAM）。
- DOMAIN: 见 `governed_agent/RESPONSIBILITY_OWNERSHIP_V0.1.md`（RS-01/02/03 Domain 责任）。

## 4. INITIAL OBLIGATIONS（ACCEPTED FOR 01-C BUILD）

OBL-01 逐字证据可溯源 · OBL-02 适用性可判定 · OBL-03 数值安全（0 无依据数值；fail-closed）· OBL-04 Fail-closed 不确定性 · OBL-05 来源保真 · OBL-06 最小归属回显。
（完整字段：`governed_agent/INITIAL_AGENT_OBLIGATIONS_V0.1.md`；DEFERRED：OBL-07..10。
B-01：OBL-03 公共义务不含源码扫描；源码"义务短语+数值"字面量扫描=01-C formation self-check。）

## 5. FUNCTIONAL DECOMPOSITION（Builder 必须按函数实现，禁止整体塞进单一 Prompt/类/模块）

| FN | 函数 | 治理状态 | 依赖 |
|---|---|---|---|
| FN-01 | Question & Context Intake | DECLARED FUNCTION BOUNDARY | — |
| FN-02 | Professional Fact Normalization | **SEAM-01** | FN-01 |
| FN-03 | Regulation Applicability Resolution | **SEAM-02** | FN-02 |
| FN-04 | Evidence Locating & Extraction | **SEAM-03** | FN-03 |
| FN-05 | Evidence Binding & Numeric Safety | **SEAM-03** | FN-04 |
| FN-06 | Uncertainty & Fail-Closed Decision | DECLARED FUNCTION BOUNDARY | FN-02/03/05 |
| FN-07 | Result Composition & Attribution | DECLARED FUNCTION BOUNDARY | FN-01/05/06/08 |
| FN-08 | Artifact & Provenance Preservation | **SEAM-03** | FN-04/05 |
| FN-09 | Corpus Access & Parsing | PRIVATE | 语料 |
| FN-10 | Provider & Execution Plumbing | PRIVATE (DEFERRED) | — |
| FN-11 | Local Runner / Service Shell | PRIVATE (DEFERRED) | 各函数 |

（15 字段明细：`governed_agent/AGENT_FUNCTIONAL_DECOMPOSITION_V0.1.md`）

## 6. RESPONSIBILITY OWNERSHIP

```text
DOMAIN     RS-01 事实词汇 · RS-02 适用性 · RS-03 证据/数值权威（SEAM-01/02/03）
ENTERPRISE RS-04 最小归属回显
AGENT      RS-05 编排与输入/输出契约（FN-01/06/07）
PRIVATE    RS-06 检索/解析/存储/服务/Provider HOW
RUNTIME    RS-07 执行语义（不变）
PLATFORM   RS-08 已接受 Platform Standard 义务（不变）
DEFERRED   RS-09 Capability 资产化
```

## 7. ALLOWED LEGACY ADAPTATION ASSETS（01-C SELECTED）

A-02（domain 模型）· A-04（facts 生命周期语义）· A-11（迁移治理 manifest 模式）· A-12（测试思路）· A-13a（环境描述符）。
DEFER：A-01 / A-03 / A-05。REUSE=0。

## 8. ALLOWED LOCAL CORPUS（F-08）—— 确定性位置见清单

**Builder 不得猜测语料位置**：读取 `evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md`（完整路径 + 全 SHA-256 + 接纳状态）。摘要：

```text
CORPUS-01  GB55037-2022.md   全 SHA 2a217deac98636584dbd328d8449a21bfb4ab30d80483d5355915beaba0594f3
           位置 E:\试验场地\catalyst-local-lab\building-regulation-evidence-v0.1\artifacts\sources\GB55037-2022.md
           （provenance：E:\试验场地\规范查询agent\data\ocr\GB55037-2022.md，逐字一致）
CORPUS-02  DBJ33T1021-2023.md 全 SHA 1296922e3dd7ef209aa8c5cc447e4fdd9a64f37e4f4d403cb8533de8cb31d3f7
           位置 E:\试验场地\catalyst-local-lab\building-regulation-evidence-v0.1\artifacts\sources\DBJ33T1021-2023.md
           （provenance：E:\试验场地\规范查询agent\data\ocr\DBJ33T1021-2023.md，逐字一致）
LOCAL PILOT ADMITTED（F-08）— READ ONLY；非组织资产/非 upstream/非永久
```

## 9. FORBIDDEN / UNAVAILABLE ASSETS

A-16（index.sqlite/wiki.sqlite/raw PDF）· A-19（knowledge_snapshot）→ UNAVAILABLE BY DEFAULT。
legacy1 `app/` 代码 → 不继承。`.venv` 环境 → 不继承。

## 10. GOVERNED SEAMS（01-C 必须作为可独立测试/可替换边界实现）

```text
SEAM-01  Professional Project Facts（Domain；FN-02）
SEAM-02  Regulation Applicability（Domain；FN-03）
SEAM-03  Regulation Evidence（Domain 权威 + Agent 绑定；FN-04/05/08）
```

## 11. PRIVATE IMPLEMENTATION FREEDOM（01-C 自由决定）

检索算法/分块/排序/provider 选择/提示词措辞/内部数据结构/缓存/数据库/模块布局/内部编排/服务形态/语料解析实现。

## 12. EVIDENCE REQUIREMENTS（01-C 必须产出）

```text
identity/version 证据 · 责任归属证据 · 义务符合证据（OBL-01..06 逐项）·
legacy 改编追踪 · Domain/Enterprise 分离证据 · 无 Platform/Runtime 污染证据 ·
source/evidence 可追溯（专业主张处）· fail-closed 证据 · 数值一致性断言（0 无依据数值）
```

## 13. BUILD CONSTRAINTS

- 确定性优先（首建无模型依赖；Provider 可后置）；数值只来自语料原文；verbatim 一致性断言。
- **源码"义务短语+数值"字面量扫描 = 01-C 本地构建自检（formation evidence），不是公共义务 OBL-03 的组成部分（B-01）。**
- 输入契约：request_id/question/project_context/regulation_context/enterprise_context。
- 输出契约：RegulationEvidenceResult（status/conclusion/evidence_items/artifacts/uncertainty/implementation_metadata）。
- 局部工作区：`catalyst-local-lab/case-01/01-c-*`；**不得触碰 Catalyst 仓库**；无 git 发布。

## 14. STOP CONDITIONS（01-C）

实现代码污染 Catalyst / 修改 Runtime / 修改 Platform Core / 复制 legacy app 代码 /
提示词成为语义权威 / 引入 A-16/A-19 依赖 / 超越 01-B 义务范围 / 未按函数分解 / 出现无依据数值 /
Agent 目的混入"测试 Catalyst"→ 立即 STOP 并记录。

## 15. 引用（Builder 必读，按序）

01-B 包：IDENTITY → OBLIGATIONS → FUNCTIONAL DECOMPOSITION → RESPONSIBILITY OWNERSHIP →
LEGACY REUSE BOUNDARY → GOVERNANCE DEPTH & SEAMS → LOCAL_CORPUS_REFERENCE_MANIFEST → CASE_01_C_BUILD_ENTRY_BOUNDARY → ENTRY DECISIONS。
01-A（只读参考）：O-2/O-3/O-4/O-5/O-6。
