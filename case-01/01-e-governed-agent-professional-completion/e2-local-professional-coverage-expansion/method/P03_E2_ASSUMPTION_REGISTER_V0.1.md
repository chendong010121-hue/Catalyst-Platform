# E2 — P-03 ASSUMPTION REGISTER — V0.1

> Method step P-03 (Assumption Extraction) — accepted Construction Method §8.
> Examine assumptions carried by the external mechanism and the professional slice;
> classify COMPATIBLE / CASE-LOCAL / REQUIRES ADAPTATION / INCOMPATIBLE / UNKNOWN.

| # | Assumption | Classification | Note |
|---|---|---|---|
| A-01 | benchmark designer knows Candidate implementation | **CASE-LOCAL** | 单人执行下无法完全消除；E2 用"冻结在先、评审在后"缓解（Candidate freeze 先发布，benchmark 后建） |
| A-02 | benchmark and Candidate live in same repo | **CASE-LOCAL** | 同一 case-01 分支；用发布时序分离（Gate1 冻结 → Gate2 benchmark） |
| A-03 | all evaluation cases may be public | **CASE-LOCAL** | E2 Evaluation Contract 公开；具体 cases 属 E2-C 独立发布 |
| A-04 | evaluation runtime is deterministic | **COMPATIBLE** | BREA v0.2/v0.3 全确定性（无模型/无网络） |
| A-05 | local corpus is professionally clean | **REQUIRES ADAPTATION** | OCR 语料含页脚数字/分页噪声；需逐字/行级 verbatim 断言 |
| A-06 | OCR text equals normative source | **REQUIRES ADAPTATION** | 以原文行级包含校验保证证据忠实；不得在无证据时假设 OCR 数值正确 |
| A-07 | retrieval success equals professional applicability | **INCOMPATIBLE** | E1/E2 明确分离：检索结果 ≠ 适用性结论（SEAM-02 保留） |
| A-08 | selected professional facts are complete | **CASE-LOCAL** | 事实完整性由 fail-closed 处理（缺失 → insufficient_context） |
| A-09 | one successful source is universally authoritative | **INCOMPATIBLE** | 单一本地语料仅为 pilot 边界；不声明普遍权威 |
| A-10 | 4.3.16 编号子项行以"1/2/3/4"独立行开始 | **REQUIRES ADAPTATION** | OCR 存在行内续接（如"27对于…"跨行），解析需按子项文本语义而非纯行首数字 |
| A-11 | 全部设置自动灭火系统=面积增加1.0倍（翻倍） | **REQUIRES ADAPTATION** | 需原文校验"增加1.0倍"语义并只在该子项存在时应用 |
| A-12 | 公共建筑定义可由 building_category 事实判定 | **CASE-LOCAL** | 用排除项（特殊要求/木结构/附建汽车库）fail-closed 处理不适用情形 |

## 未知假设处理

```text
UNKNOWN 假设数：0
未经验证的专业假设不得静默成为规范行为：
  4.3.16 数值绑定仅在子项原文可解析且事实匹配时发生；否则 fail closed。
```

## 关键结论

- A-07 / A-09 为 **INCOMPATIBLE**：E2 明确拒绝"检索=适用性""单源=普遍权威"。
- A-05/A-06 驱动 verbatim 断言策略（行级包含校验）。
- A-10/A-11 驱动 4.3.16 子项解析器设计。
