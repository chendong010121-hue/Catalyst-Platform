# GOVERNED SEAM CONFORMANCE — V0.1 (CASE 01-C)

> SEAM-01..03 显式且可测试（§8）。稳定含义/依赖方向/实现 HOW 可替换/私有实现不可重定义接缝语义。不创建 Platform Standard 对象。

## SEAM-01 — Professional Project Facts（Domain；FN-02）

- 模块：`brea/facts.py`（词汇表 + 归一化 + 缺失检测）。
- 稳定含义：`FACT_VOCABULARY`/`FACT_LABELS` 为 Domain 资产（代码数据，非提示词）。
- 依赖方向：FN-01 → facts；facts 不依赖 evidence/corpus 语义。
- 可替换：归一化算法可换；词汇稳定。
- 测试：test_seam01_facts PASS；ST-04（无提示词承载）。

## SEAM-02 — Regulation Applicability（Domain；FN-03）

- 模块：`brea/applicability.py`（标准注册表 + 表5.0.1 级别解析 + 适用链）。
- 稳定含义：标准身份/版次/法域/级别来自 Domain 元数据 + 语料表5.0.1（原文权威）。
- 依赖方向：facts → applicability → evidence；applicability 不拥有数值权威。
- 可替换：规则/元数据可更新；适用链语义稳定。
- 测试：test_seam02_applicability PASS。

## SEAM-03 — Regulation Evidence（Domain 权威 + Agent 绑定；FN-04/05/08）

- 模块：`brea/evidence.py`（定位/绑定/verbatim 断言/证据束）。
- 稳定含义：数值权威=语料原文；实现不生成数值；claim↔evidence 绑定。
- 依赖方向：applicability → evidence；evidence 仅经 corpus（私有）读原文。
- 可替换：定位/解析/绑定实现可换；义务稳定。
- 测试：test_seam03_evidence PASS；ST-06 PASS；T-C01/02 结果。

## 反证（私有实现不可重定义语义）

- ST-03：无 provider 模块；ST-04：无提示词/AGENTS.md；语料解析（FN-09）为纯 HOW，其输出经 verbatim 断言约束。
