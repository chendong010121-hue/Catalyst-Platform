# BREA RETRIEVAL ARCHITECTURE DECISION — V0.1

> Review Contract §14. Decide each retrieval mechanism separately:
> REQUIRED NOW / OPTIONAL UPGRADE / DEFER / REJECT.
> No Vector DB product/provider decision allowed in this Review.

## Decisions

| Mechanism | Decision | Evidence / reasoning |
|---|---|---|
| Exact locator retrieval | **REQUIRED NOW** | E1 QMODE-01（条款定位）、QMODE-04（表格定位）已实现且通过；精确引用是 OBL-05 基础 |
| Lexical / BM25 retrieval | **REQUIRED NOW（等效实现已存在：n-gram 词法打分）** | E1 QMODE-03 主题检索已工作（7 未编码查询含 B-E1-05/06）；当前实现为 n-gram token 打分，可视为 BM25 的轻量等价；正式 BM25 为 OPTIONAL 升级 |
| Metadata filter | **REQUIRED NOW（最小）** | source_id / unit_type / jurisdiction 过滤已隐含（query.py STANDARD_ALIASES + 标准解析）；结构化后应显式化 |
| Dense semantic retrieval | **DEFER** | H-05 NARROWED：E1 证据显示 exact+lexical 对当前面够用；无 dense 必要性证据；F-EXP-02 后方可复议 |
| Reranking | **DEFER** | 当前 top-3 足够；无 rerank 必要性证据 |
| Cross-document retrieval | **DEFER（设计契约）** | 当前无跨文档合成需求；未来 edition 替换/冲突需跨文档检索，属长程 |
| Vector DB product/provider | **REJECT（本 Review 范围）** | Review Contract §14 明确禁止任何 Vector DB 产品/提供商决策 |

## 关键证据

```text
- E1 反 fixture：7 个未编码查询成功 = exact/lexical/metadata 组合的实证
- B-E1-02（同条款不同措辞）→ 无 query rewriting / dense 即命中
- B-E1-05/06（主题检索）→ n-gram 词法打分命中
- H-05 收窄："NO DENSE RETRIEVAL YET" 是合法结论（Review Contract §4 明示）
- 外部框架 hybrid 事实 ≠ BREA 必要性（§19）
```

## 决策陈述

```text
RETRIEVAL ARCHITECTURE DECISION
REQUIRED NOW : exact locator + lexical(n-gram 现行/BM25 可选升级) + metadata filter
DEFER        : dense semantic retrieval / rerank / cross-document
REJECT       : Vector DB 产品决策（本 Review 范围外）

最小充分性论证：
当前证据（E1 7 未编码查询）表明 exact+lexical+metadata 达到所需 recall/precision；
任何 dense/rerank/vector-DB 的加入都增加复杂度、依赖与审计面，而无必要性证据。
```

## 下一候选必须证明

```text
对 unseen 措辞的检索 recall/precision 保持（§25 proof target 的检索部分）；
若 lexical 出现 recall 缺口，再启动 F-EXP-02 评估 dense（OPTIONAL UPGRADE）。
```
