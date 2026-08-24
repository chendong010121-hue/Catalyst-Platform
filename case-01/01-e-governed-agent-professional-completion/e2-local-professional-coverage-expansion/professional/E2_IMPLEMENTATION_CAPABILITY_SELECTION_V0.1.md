# E2 — IMPLEMENTATION CAPABILITY SELECTION — V0.1

> E2-AB §16 Technology Selection Gate. Evidence-based selection, not preset rules.

## Decision sequence

```text
REQUIRED OBSERVABLE PROFESSIONAL BEHAVIOR
公共建筑防火分区最大允许建筑面积：依项目事实（形式/耐火等级/灭火系统）返回受控数值+逐字证据；不足则 fail closed

CURRENT V0.2 DETERMINISTIC CAPABILITY
QMODE-01 按条款定位检索（可拿到 4.3.16 原文）
QMODE-03 主题检索（可命中"防火分区"相关条文）
但均不能做"事实→子项→数值"的专业判定

DEMONSTRATED CAPABILITY GAP
条件规则族判定：解析编号子项条款、依事实选子项、绑定数值、应用修正规则（自动灭火增加1.0倍）
v0.2 无此能力（适用性仅有防火间距/配建两条主线）

CANDIDATE IMPLEMENTATION MECHANISMS
1. 既有确定性解析器扩展（编号子项条款解析器）        ← 选择
2. 结构化表格解析器（表4.3.4 方向）                 ← 备选（未选切片）
3. lexical expansion / synonym map                  ← 不需要（条款结构清晰）
4. full-text search                                 ← 已有（QMODE-03），不足以判定
5. cross-clause deterministic resolver              ← 本切片不跨条款
6. OCR normalization                                ← 已有 norm()；行级 verbatim 已证明
7. vector retrieval / RAG / LLM                     ← 不需要（E2 Spec §5/§16：确定性机制足够则不得添加）

EVIDENCE-BASED SELECTION
机制1：编号子项条款解析器（确定性、stdlib、可审计）
```

## Selected mechanism record

| Field | Value |
|---|---|
| mechanism | 编号子项条款 → 条件规则表解析器（`brea/coverage.py` 私有模块） |
| why needed | 4.3.16 是"1/2/3/4…"编号子项条件规则；需要把子项文本+数值+适用条件结构化，才能做事实→数值绑定 |
| Function owner | FN-09（解析，PRIVATE HOW）/ FN-04（定位）/ FN-05（数值绑定）/ FN-03+SEAM-02（适用性判定） |
| private HOW / governed-seam decision | PRIVATE HOW（P-05 AXIS A）；SEAM-02 扩展为既有 seam 职责内扩展 |
| failure mode | 子项无法解析/事实不足/排除项 → fail closed（不编造） |
| replacement path | 若未来需要跨条款/跨来源的条件规则，作为 Generalization Review 候选（P-09），不自动提升 |
| evaluation method | AB-T13 构造自测 + 回归 + 未来 E2-C 独立 benchmark（冻结后建） |

## 结论

```text
DO NOT ADD LLM / RAG（确定性机制充分，E2 Spec §16）
DO NOT ADD Web / vector DB / Memory（scope excluded）
唯一新增实现：确定性编号子项条款解析器（Case-local，PRIVATE HOW）
```
