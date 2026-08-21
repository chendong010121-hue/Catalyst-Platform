# BLIND VS CURRENT BREA COMPARISON — V0.1（D0 · D0-B）

> 冻结后对比：盲恢复的 Legacy 意图/功能 vs 当前 BREA（01-B 定义 + 01-C 候选）。比较，非重写。

## 1. 意图 → BREA 义务映射（blind PRODUCT_INTENT_REQUIREMENT_MATRIX → 01-B OBLIGATIONS）

| 盲 REQ | BREA OBL | 覆盖判断 |
|---|---|---|
| REQ-L01 单问题规范咨询（检索→适用性→回答） | OBL-01 逐字证据溯源 / OBL-02 适用性 / OBL-03 数值安全 / OBL-05 来源保真 | BREA 覆盖其"证据+适用性+安全"核心；完整"咨询→回答"（AnswerDocument）超出 BREA 首建（DEFERRED） |
| REQ-L03 来源保真/指纹/坐标 | OBL-05 + SEAM-03 | ✓ 一致 |
| REQ-L04 事实提取/确认 | SEAM-01（事实词汇）+（修订/确认机制超出首建） | 部分——BREA 采用事实词汇与归一化；2.0 的修订/确认锁为 A-04 语义（01-C DEFER 持久化） |
| REQ-L07 三分离判断 | OBL-02 适用链 + SEAM-02 | ✓ 语义一致（适用性显式） |
| REQ-L09 规范理解/证据绑定 | SEAM-02/SEAM-03（适用性+证据绑定+数值安全） | ✓ BREA **实现了 2.0 声明未实现的中段** |
| REQ-L11 provider 双支持 | FN-10 DEFERRED（首建无模型） | BREA 首建确定性无 provider；2.0 的 codex 为历史实现（REFERENCE ONLY） |
| REQ-L10 AnswerDocument/导出 | DEFERRED（OBL-09/01-E） | 超出首建 |
| REQ-L08 网络补证 | DEFERRED（OBL-10） | 超出首建 |
| REQ-L15 评价（60 题） | DEFERRED（01-E） | 超出首建 |
| REQ-L12 项目隔离 | （BREA 首建无项目持久化——归属仅元数据 OBL-06） | 部分——BREA 以 enterprise 归属回显替代项目隔离（首建范围） |

## 2. Legacy 函数 → BREA FN 映射（blind LEGACY_FUNCTIONAL_DECOMPOSITION → 01-B/01-C FN）

| 盲 LF | BREA FN | 关系 |
|---|---|---|
| LF-02 文档摄入/解析 | FN-09（Corpus Access & Parsing，私有）+ A-01 DEFER | 语义对应；2.0 为文档摄入，BREA 为语料解析（私有 HOW） |
| LF-03 事实提取（词汇硬编码） | FN-02 SEAM-01（词汇资产化） | **修复点**：BREA 将 2.0 硬编码词汇提升为 Domain 接缝 |
| LF-04 事实修订/确认 | （超出 BREA 首建；A-04 语义参考） | 01-C 未建持久化修订 |
| LF-06 本地 RAG | FN-04 定位（私有 HOW 检索）+ FN-09 | BREA 以确定性定位实现（无向量） |
| LF-07 证据治理 | FN-05/08 SEAM-03（绑定+保真+verbatim） | BREA 实现 2.0 声明语义 |
| LF-08 规范理解/适用性 | FN-03 SEAM-02 | ✓ |
| LF-13 provider | FN-10 DEFERRED | 首建无模型 |
| LF-14 Workbench | （BREA 首建 CLI，无前端） | 超出首建 |
| LF-15 Launcher | FN-11（Runner） | ✓ 对应 |
| LF-05 run 事件 / LF-10 AnswerDocument / LF-11 导出 / LF-09 网络 | DEFERRED（01-C 未建） | 超出首建 |

## 3. Domain/Enterprise 分离一致性

- 盲（RESPONSIBILITY_RECOVERY/DOMAIN/ENTERPRISE）：Domain=事实词汇/来源/适用性/证据/不确定；Enterprise=项目归属/接入约束/人工验收。
- BREA（01-B RS 表）：DOMAIN=RS-01/02/03；ENTERPRISE=RS-04 最小归属；AGENT=RS-05。
- **一致**：BREA 将盲恢复的 Domain 意图落实为 SEAM-01/02/03；Enterprise 收窄为最小归属（OBL-06）。

## 4. 关键差异（如实记录）

1. **范围差异**：盲产品意图=完整分析 Agent（两类任务+导出+网络+评价）；BREA 首建=证据能力子集（fail-closed 优先）。BREA 是受治理形成的第一步，非完整产品。
2. **实现差异**：2.0 实现了"文档→事实"前段；BREA 实现了"事实→适用性→证据→结论"中段（2.0 仅声明）。
3. **词汇所有权**：2.0 硬编码；BREA 资产化为 SEAM-01。
4. 2.0 无 org/user；BREA 引入最小归属（F-07）。
5. 2.0 的 OCR/文档摄入/项目隔离/修订锁在 BREA 首建中 DEFER 或不在范围。

## 结论

盲理解正确识别了 2.0 的"前段已实现 + 中段仅声明"形态；BREA 首建恰好落地其中段语义并修复词汇所有权——**盲 vs BREA 无矛盾，互为补充**（01-E 完整产品完成需回头补齐 2.0 前段与导出/评价）。
