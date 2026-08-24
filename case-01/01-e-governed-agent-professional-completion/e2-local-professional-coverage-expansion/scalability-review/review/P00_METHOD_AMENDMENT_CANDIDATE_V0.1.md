# P-00 METHOD AMENDMENT CANDIDATE — V0.1

> Review Contract §20. Propose (not permanently amend) a lightweight conditional
> gate: P-00 PRODUCT CAPABILITY ENVELOPE / SCALE JUDGMENT, before normal P-01.

## Proposed P-00 gate

```text
P-00 PRODUCT CAPABILITY ENVELOPE / SCALE JUDGMENT
Trigger questions:
  open knowledge?
  open natural-language query?
  dynamic source growth?
  user-upload natural?
  controlled Web natural?
  semantic paraphrase heavy?
  high corpus growth?

If all materially NO:
  normal P-01 (Problem Extraction)

If one or more materially YES:
  Scale Invariant
  + Change-Cost Classification
  + Mechanism Pattern Selection
  → then P-01
```

## Does P-00 add decision quality? — 实证检验

### 支持（YES，值得加入）

| 证据 | 说明 |
|---|---|
| 本 Review 的经验 | BREA 的 P-01 问题记录（E2）在实施前未先做 Scale/Change-Cost 判定，导致 E2-AB 后才发现"新家族=代码变更"与"知识/代码边界模糊"（PC-01..04）——P-00 会在 P-01 前暴露此风险 |
| OPEN 判定先行 | E1/E2 变更请求均隐含 open query；P-00 可把"开放度"作为显式前置判定，避免把 open product 当 CLOSED 处理 |
| Mechanism Pattern Selection | 若 P-00 判定 open/growth，直接触发 Scale Invariant + Change-Cost + Mechanism Selection（即本 Review 的产物），使后续 P-01..P-06 有架构上下文 |

### 反对/限制（需谨慎）

| 证据 | 说明 |
|---|---|
| 增加流程开销 | 小型/封闭 Agent 走 P-00 是多余；但触发器"all NO"可快速短路 |
| 判定依赖产品权威 | open/growth 判定本质是 Product Authority 决策，不能由执行者单方假设——P-00 须以"产品证据 + 权威确认"为输入 |
| 不解决内容问题 | P-00 只是前置分类，不替代 P-01..P-06 的实质工作 |

## 判定

```text
P-00 增加决策质量的证据：YES（本 Review 的 E2 后验经验支持）
但：
  1) P-00 是 CONDITIONAL gate（all NO → 短路），不是每 Stage 强制步骤
  2) P-00 判定须引用产品证据与 Product Authority 确认（防执行者自行假设包络）
  3) 方法修订不是自动的 —— 本 Review 仅提交 CANDIDATE，
     永久修订需外部 Method Review（Method §25：E2 后外部评审决定 CASE 01 VALIDATED METHOD）
```

## 提交状态

```text
P00_METHOD_AMENDMENT_CANDIDATE
PROPOSED（候选，未修订）
推荐文本：在 accepted Method §12 管线 "USER/BUSINESS NEED" 与 "GOVERNED INTERPRETATION"
之间（或作为 P-01 前置）加入条件性 P-00 判定。
等待外部 Method Review 决定是否并入。
```
