# DOMAIN / ENTERPRISE RESPONSIBILITY CHECK — V0.1（D1 · §15）

> D0 UC-06 为 PARTIAL：D1 在证据不足处**保留组合/未决**，不把每项强行塞入单一语义层（§15 规则）。
> 类别：DOMAIN / ENTERPRISE / AGENT BEHAVIOR / GOVERNANCE / IMPLEMENTATION HOW / COMPOSED / UNRESOLVED。

| 项 | 分类 | 依据（证据） |
|---|---|---|
| Agent ownership | GOVERNANCE + ENTERPRISE（COMPOSED） | 01-B F-07（owner=User/CASE 01 Product-Release Authority）；Agent 为受治理单元（I-01） |
| project attribution | ENTERPRISE | 01-B F-07（project_ref）；BREA 结果归属（OBL-06） |
| organization attribution | ENTERPRISE | enterprise.identity 语义（organization_id/user_id；enterprise_extensions/identity.py）；F-07 |
| acceptance authority | ENTERPRISE + GOVERNANCE（COMPOSED） | F-07（evaluation owner=User/CASE 01 Acceptance Authority）；D0 外部审查 |
| professional purpose | AGENT BEHAVIOR（+DOMAIN 语境） | 01-B IDENTITY；D0 RECOVERED_PRODUCT_INTENT_BASELINE（意图≠规范性；S-D1-08 未触发） |
| professional facts（事实词汇） | DOMAIN | 01-C SEAM-01；01-A R-02（词汇硬编码缺陷→资产化） |
| applicability（适用性） | DOMAIN | 01-C SEAM-02；01-A R-04 |
| evidence semantics（证据语义） | DOMAIN + AGENT BEHAVIOR（COMPOSED） | 01-C SEAM-03（Domain 权威 + Agent 绑定）；01-A R-05 |
| numeric safety（数值安全） | DOMAIN | 01-C OBL-03/SEAM-03；01-A R-15 |
| network fallback（网络补证） | UNRESOLVED（D0 UC-06 PARTIAL） | Legacy config network_mode 无消费点（01-A F-05）；AGENTS 网络门槛——可能属 AGENT BEHAVIOR/GOVERNANCE/ENTERPRISE 策略，证据不足以定单一所有者 |
| source trust（来源信任） | COMPOSED（DOMAIN 来源语义 + GOVERNANCE 准入规则） | 01-C 语料只读/哈希校验；01-A prompt-charter（formal/candidate 边界）——D0 UC-06 PARTIAL 保留 |
| human review（人工审查） | ENTERPRISE（验收期望）+ AGENT BEHAVIOR（确认流） | Legacy AGENTS（事实确认强制）；01-C OBL-06/01-A F-07 |
| memory / retention（记忆/保留） | DEFER（无当前 BREA 首建需求） | 01-C 无记忆实现；01-B DEFERRED 项 |

## 结论

- Domain 语义（事实/适用性/证据/数值）明确留在 Domain/Agent——**Admission/Binding/Platform/Runtime 不承载**（I-06/I-11 保持）。
- Enterprise 保持一等语义维度但最小化（归属/所有者/验收权威；enterprise.identity 承载）。
- 不确定项（network fallback/source trust 的最终归属）**如实保留为 UNRESOLVED/COMPOSED**——不因 D0 部分恢复而静默定型（S-D1-09 未触发；§15 保留不确定性）。
