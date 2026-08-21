# LEGACY ADAPTATION TRACE — V0.1 (CASE 01-C)

> 选自已闭包 01-A/01-B：A-02/A-04/A-11/A-12/A-13a。**复用证据与资产，不继承意外架构。** 未复制 legacy app 代码。

| 资产 | 01-C 中的改编 | 证据 |
|---|---|---|
| A-02 domain model concepts | 类型化事实/契约 dataclass（`brea/contracts.py`、`brea/facts.py` 归一化键/值） | contracts.py/facts.py；T-C01..03 结果 |
| A-04 facts lifecycle semantics | 事实归一化 + 缺失检测 + 不可变结果（修订/确认锁完整机制 DEFER——首建无需持久化修订） | facts.py（归一化/缺失）；结果不可变 dataclass |
| A-11 migration-governance manifest pattern | Builder 输入/输出清单（`BUILDER_REQUEST_V0.1.json` + `BUILDER_OUTPUT_MANIFEST_V0.1.json` + 语料清单引用） | builder/*.json；BUILDER_FORMATION_TRACE |
| A-12 test patterns | 合同/结构测试思路（T-C01..03 + ST-01..08 + SEAM 测试） | tests/*.py；01c_selfcheck.log |
| A-13a environment/dependency descriptors | Python 3.12 stdlib-only（无新增依赖）；README 记录运行命令 | README.md；运行日志 |

## 未适配/不可用（记录）

- A-01/A-03/A-05：DEFER（首建确定性无文档摄入/无持久化 schema/无 provider）。
- A-16/A-19：UNAVAILABLE BY DEFAULT（01-C 未依赖 index.sqlite/wiki/knowledge_snapshot）。
- legacy1 `app/` 代码 / `.venv`：未继承。
- 历史引擎架构（Phase 2B pilot）：仅参考（§11）；本候选为新的确定性实现。
