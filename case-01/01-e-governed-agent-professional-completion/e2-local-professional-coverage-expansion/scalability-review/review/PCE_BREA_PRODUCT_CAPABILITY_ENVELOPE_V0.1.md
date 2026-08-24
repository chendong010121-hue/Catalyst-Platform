# BREA PRODUCT CAPABILITY ENVELOPE — V0.1

> Review Contract §5. Explicit classification of the BREA product envelope along the
> required axes. For every `OPEN / HIGH / COMPLEX` classification an evidence source
> is required. The review actively looked for evidence that the envelope is smaller
> than currently assumed.

## Classification

| Axis | Classification | Evidence source | Disconfirming evidence considered |
|---|---|---|---|
| Knowledge Space | **OPEN**（有界） | 变更请求措辞："对已经接入的本地建筑规范进行一般化查询"（E1 PCR）；E2 选择第三个专业家族（防火分区）并加入既有语料之外的判定语义；P-01 问题记录"更广专业覆盖" | 语料目前恰为 2 份本地规范；无任何用户上传/受控 Web 已授权 —— 开放度有界于"本地源集合 + 自然语言查询面" |
| Query Space | **OPEN NATURAL LANGUAGE** | E1 反 fixture 证明：7 个未编码查询成功（B-E1-01/02/03/05/06/07/09）；B-E1-02 同条款不同措辞成功；E1 诊断报告 V0.2 | 无 —— 查询面开放已有直接证据 |
| Source Space | **FIXED LOCAL**（当前） + **LOCAL + USER / CONTROLLED WEB**（长程设计边界，未授权） | E2 授权记录 scope：无 user-upload / web；E2 阶段规格 §5 明确 deferred；Review Contract §18 仅设计边界 | 无当前证据显示 Source Space 已含 Web —— 不得把设计边界当作已实现能力 |
| Corpus Growth | **MEDIUM**（预期） | E2 选择了第 3 个专业家族（不是第 3 份语料，但证明"新增专业面"是常态）；E2-AB 阶段结论建议 E2 扩展更多本地规范；Review Contract §25 以"unseen source revision"为下代候选证明目标 | 当前实际语料 = 2 份（GB55037-2022、DBJ33T1021-2023），LOW 是现实值；MEDIUM 是基于产品意图的预期值 —— 标注为"预期"而非"已验证" |
| Document Formats | **stable → heterogeneous（过渡）** | 现 2 份均为 OCR markdown；E2 已遇到编号子项、表、跨行等结构（P-03 A-10/A-11） | 无 PDF/DOCX/扫描件证据；heterogeneous 为长程风险，非当前事实 |
| User Upload | **not required**（当前） / natural（长程设计边界） | E2 授权无 upload；Review Contract §18 仅设计边界 | 无任何用户上传需求证据 |
| Web Supplement | **rejected**（当前，scope excluded） | E2 规格 §5：Web 属于后续单独评审切片；E1 PCR scope excluded Web | 无 —— Web 明确被排除于当前产品面 |
| Cross-document Need | **medium**（预期） | E2 选择"跨条款适用性"为合格切片类型之一（E2 规格 §3）；未来 edition 替换需 cross-document（old/new） | 当前家族均单条款（3.1.3 / 5.0.1+5.0.4 / 4.3.16）；无真正跨文档合成证据 |
| Professional Risk | **HIGH** | 规范数值直接约束工程合规（防火分区/防火间距/配建指标）；E2 PC-01..04 专业缺陷即由高风险契约暴露 | 无 —— 专业风险高是产品性质 |
| Numeric Risk | **HIGH** | OBL-03/04；E2 PC-04 派生数值契约缺陷；数值必须可溯源原文 | 无 —— 数值风险高是产品性质 |
| Version / authority | **complex**（预期） | 语料清单已有"版本/废止/施行"字段（LOCAL_CORPUS_REFERENCE_MANIFEST）；E2 规格 §39 需 source identity/edition/effective status；未来 edition 替换明确需要 version 语义 | 当前 2 份均为单版（2022/2023），简单是现实值；complex 为预期值 |

## 主动寻找"包络比假设更小"的证据

```text
考察过：BREA 是否可能是 CLOSED / FIXED 产品？
证据：变更请求与 E1/E2 规格全部使用"一般化查询/更广专业覆盖"；
      产品权威（User）从未声明有限问题族或固定语料集。
结论：CLOSED 包络不成立（无产品权威证据支持）。
```

```text
考察过：Query Space 是否实际 FIXED（预设题）？
证据：E1 B-E1-01..13 全部为未编码查询且成功；E1 反 fixture 审查 PASS。
结论：OPEN NATURAL LANGUAGE 成立，且有直接运行证据。
```

```text
考察过：Corpus Growth 是否实际 LOW（无增长需求）？
证据：E2 选择新家族本身即"专业面增长"证据；产品主线的后续切片（更多本地规范）
      明确被列为方向（E2 规格 §50）。
结论：MEDIUM（预期）成立，但标注为预期值。
```

## 包络结论

```text
BREA = OPEN QUERY + OPEN (有界本地) KNOWLEDGE + FIXED LOCAL SOURCE(当前)
  + MEDIUM 预期增长 + HIGH 专业/数值风险 + complex 预期版本/权威语义

OPEN/HIGH/COMPLEX 分类的证据来源均已记录；无证据支持的更大包络
（user upload / web / heterogeneous formats）一律保持"长程设计边界，未授权"。
```

## 对架构选择的含义（先行结论，详见各决策文档）

```text
OPEN QUERY + OPEN KNOWLEDGE → 检索/知识面不能依赖"每问题硬编码"（E1 已证）
MEDIUM 增长 + complex 版本 → 数据/索引/版本分离值得认真考察（H-02/H-04）
HIGH 专业/数值风险 → 验证面必须保持确定性/强校验（H-08 方向）
当前 2 源 + 无 upload/web → 密集检索/LLM 当前无必要性证据（H-05/H-06 收窄）
```
