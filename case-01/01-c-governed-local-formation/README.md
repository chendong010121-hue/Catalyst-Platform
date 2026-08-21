# CASE 01-C — GOVERNED LOCAL FORMATION（V0.1）

> BUILD Stage · CASE-SCOPED · CASE ↔ PLATFORM CO-EVOLUTION。本目录承载 BREA 候选的本地形成证据。

## 内容

```text
builder/    最小 Case-scoped Builder（协议/请求/生成器/模板/输出清单/运行报告）
candidate/  brea-v0.1 生成候选（实现 + 测试 + README）
evidence/   Formation 证据（索引、符合性、追踪、三案结果）
findings/   发现与未知
review/     执行报告、01-D 入口边界、Catalyst 完整性校验
```

## 关键契约引用

- Stage Spec：`CASE_01_C_GOVERNED_LOCAL_FORMATION_V0.1_STAGE_SPEC.md`（本目录）
- 已接受 Builder 输入：`../01-b-governed-agent-definition/builder/BUILDER_CONSUMABLE_DEFINITION_V0.1.md`（SHA `6c6e4707…`）
- 语料清单：`../01-b-governed-agent-definition/evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md`（只读；不提交语料）

## 运行

```powershell
# Builder（清洁目标生成）
python builder\run_builder.py

# 候选自检（全部结构/接缝/整机测试）
cd candidate\brea-v0.1
python tests\run_all.py

# 三案整机证据
python -m brea.runner --case T-C01 --out ../../evidence/CASE_RESULTS/T-C01_result.json
python -m brea.runner --case T-C02 --out ../../evidence/CASE_RESULTS/T-C02_result.json
python -m brea.runner --case T-C03 --out ../../evidence/CASE_RESULTS/T-C03_result.json
```

## 状态

```text
TRACK A  BREA v0.1 Candidate    FORMED（formation PASS）
TRACK B  minimum local Builder  CASE-CLOSED（GAP-01/GAP-05 for Case 01）
CASE 01-D / admission / binding NOT AUTHORIZED
```
