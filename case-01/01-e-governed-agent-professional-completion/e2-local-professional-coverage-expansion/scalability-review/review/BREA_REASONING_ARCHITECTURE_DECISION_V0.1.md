# BREA REASONING ARCHITECTURE DECISION — V0.1

> Review Contract §15. Per-responsibility mechanism classification.
> LLM must not silently become authority for source existence/version/unsupported
> numeric/final authority/citation unless an equally auditable control is shown.

## Per-responsibility decision

| Responsibility | Preferred mechanism | Evidence / reasoning |
|---|---|---|
| question understanding | **DETERMINISTIC**（现行 classify_query） | E1 7 未编码查询成功；无 LLM 必要性证据（H-06） |
| professional fact extraction | **DETERMINISTIC / DECLARATIVE**（normalize_facts + required facts） | AB-T13 已覆盖既有家族；结构化为 facts schema |
| missing-fact detection | **DETERMINISTIC**（missing_facts） | 已实现且通过（T-C03 / AB-T13 case4） |
| query rewriting | **NOT NEEDED**（当前） | B-E1-02 同条款不同措辞未改写即命中；若未来出现 recall 缺口再评估 |
| source selection | **DETERMINISTIC / DECLARATIVE**（STANDARD_ALIASES + jurisdiction） | 已实现；结构化 source metadata |
| applicability candidate generation | **DECLARATIVE / SCHEMA**（RegulationUnit conditions） | v0.3 FIRE_COMPARTMENT 数据化方向 + PC-02 需结构化 condition 分解 |
| applicability final decision | **DETERMINISTIC**（条件匹配 + scope/exceptions 校验） | PC-01 显示须加正向 scope 校验；保持确定性可审计 |
| cross-clause synthesis | **DEFER**（当前无需求） | 无跨文档合成证据；未来若需要，先试确定性组合（B 方向），再评估 LLM |
| numeric derivation | **DETERMINISTIC + SCHEMA**（operands/modifiers/derivation_trace） | PC-04：派生轨迹必须结构化；不得由 LLM 生成规范数值 |
| answer composition | **DETERMINISTIC**（build_result） | 已实现；7 字段契约稳定 |

## LLM 边界（Contract §15 强制）

```text
LLM 不得成为以下事项的权威（除非有同等可审计控制）：
  source existence        → 保持 manifest/SHA 确定性
  source version          → 保持 edition/effective status 数据
  unsupported numeric     → 保持 fail-closed 确定性
  final authority class   → 保持 scope/exceptions 校验
  citation binding        → 保持 verbatim + locator 确定性

当前：上述全部由确定性机制承担且无失败证据 → LLM 不进入任何责任。
```

## 决策陈述

```text
REASONING ARCHITECTURE DECISION
ALL responsibilities: DETERMINISTIC / DECLARATIVE / SCHEMA（当前包络内）
LLM-ASSISTED : 无（任何责任当前都无必要性证据；per-responsibility 复核待 F-EXP-04）
HUMAN REVIEW : 长程（高权威冲突/网络补证时评估，非当前）
COMPOSED     : 未来若需跨条款合成，先试确定性组合（B 方向），LLM 为最后选项

最小充分性论证：
每个已测试责任都有工作的确定性实现（E1/E2 证据）；LLM 引入外部依赖与
可审计性风险而无任何必要性证据。
```

## 下一候选必须证明

```text
对未编码措辞的问题理解/事实抽取保持鲁棒（§25 proof target 的推理部分）；
若确定性在某一责任出现真实缺口，才对该责任启动 F-EXP-04 对照。
```
