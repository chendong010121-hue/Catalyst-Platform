# UNDERSTANDING SNAPSHOT — V0.1（BLIND · D0）

> 本快照完全基于 **Legacy Agent 2.0 工作区**（`E:\试验场地\规范查询agent2.0`，READ ONLY）的盲扫证据生成。
> 冻结前**未读取**任何 01-A/01-B/01-C 输出或本会话重述的产品要求（见 `FORBIDDEN_SOURCES_DECLARATION.txt`）。

## 快照元数据

```text
Legacy root            E:\试验场地\规范查询agent2.0
File inventory used     101 files（scripts/legacy_inventory.txt）
Git HEAD                <recorded in BLIND_SNAPSHOT_MANIFEST>（branch: agent2-delivery）
Scan start/end          <recorded in manifest>
Forbidden sources read  NONE（declaration frozen before this snapshot）
```

## U-1 意图中的产品目的（盲恢复，证据锚定）

> 一个**本地建筑规范分析 Agent**（Standards Agent 2.0）：为建筑前期设计/方案设计工作提供基于本地规范库的专业咨询（单问题规范咨询）与项目资料自动分析（文件夹→规划条件提取→事实确认→关注事项），产出**可追溯、证据支撑**的回答/事项清单，并显式处理缺失信息与不确定性；交付形态=Windows 本地一键启动 + 浏览器 Workbench + 可打包交付；**离线优先**，网络仅在本地证据不足时按策略补证。

盲证据（BLD-E）：README.md（"clean, delivery-grade migration of the local architectural-standards analysis workflow"）、design spec §1/§2（两类核心任务、交付目标、离线优先）、AGENTS.md（本地资产、网络仅 gap/verify、AnswerDocument 单一答案源）、prompt-charter-audit.md（保留架构级策略：架构范围/已确认事实保护/正式-候选边界/不编造/引用可追溯）。

## U-2 意图能力/要求（盲恢复）

见 `PRODUCT_INTENT_REQUIREMENT_MATRIX_V0.1.md`（REQ-L01..L16）。

## U-3 观察到的已实现能力

见 `OBSERVED_CAPABILITY_MATRIX_V0.1.md`（以代码/测试/配置为准，不因 README/Prompt 描述推断实现）。

## U-4 缺失/部分/矛盾

见 `OBSERVED_CAPABILITY_MATRIX_V0.1.md`（IMPLEMENTED/PARTIAL/INTENDED_NOT_IMPLEMENTED/CONTRADICTED/UNKNOWN）。

## U-5 责任模型（盲恢复）

见 `RESPONSIBILITY_RECOVERY_V0.1.md`（DOMAIN/ENTERPRISE/AGENT/PRIVATE HOW/RUNTIME/PLATFORM CANDIDATE/UNRESOLVED；不以文件位置作责任证明）。

## 盲证据索引 / 未知项

见 `UNDERSTANDING_EVIDENCE_INDEX_V0.1.md` 与 `UNDERSTANDING_UNCERTAINTIES_V0.1.md`。
