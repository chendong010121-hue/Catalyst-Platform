# PLATFORM GAP REGISTER — D1 — V0.1（§16）

> 区分：REAL D2 BLOCKER / CASE-LOCAL NEED / GENERALIZATION CANDIDATE / DEFERRED FUTURE NEED / REJECTED PREMATURE CONCEPT。
> **发现缺口 ≠ 实现授权**（§16；D1 不实现任何缺口）。

| gap_id | need | evidence | current owner | why current contract insufficient | smallest local alternative | D2 requires? | Platform review? |
|---|---|---|---|---|---|---|---|
| G-D1-01 | Agent 级 identity/version/admission 表示 | 无 Agent 级身份契约（Capability 有 id；models.py）；Admission Record 需字段 | Agent governance | Platform 仅有 Capability 身份；Agent≠Capability（I-02） | Case-local Admission Record（MINIMUM_AGENT_ADMISSION_RECORD_CANDIDATE） | YES | **GENERALIZATION CANDIDATE**（反复跨 Agent 需要时再评审；不自动提升） |
| G-D1-02 | 执行归因（agent 归属穿越执行） | extensions.py（governance. 命名空间保留）；enterprise.identity 证明 Extension 归因模式 | Governance/Extension | Core v0.1 无扩展语义（可选扩展原样保留——够用）；需 Case-local 助手写 TraceEvent.extensions | `governance.agent` Extension（payload）+ Case-local attribution 助手 | YES | **GENERALIZATION CANDIDATE**（governance.* 扩展若跨 Agent 重复出现→评审） |
| G-D1-03 | Agent 整机经 capability 机制执行（Agent≠Capability 适配） | runtime_adapter.py（capability 绑定/预检/版本路由）；interfaces.py Capability 协议 | Binding/Adapter | 执行机制为 capability-centric；Agent 身份须并行存在 | BREA runner 实现 Capability 协议（describe/invoke）+ Adapter 绑定 + Admission Record 并行 | YES | **GENERALIZATION CANDIDATE**（Adapter 适配模式若跨 Agent 重复→评审） |
| G-D1-04 | 实现指纹确定性（绑定防换） | 01-C BUILDER_OUTPUT_MANIFEST + candidate 源树 | Binding | 无生产指纹机制（不需要签名/供应链） | D2 脚本：源树全量 SHA + manifest SHA 记录于 Binding | YES | **CASE-LOCAL NEED**（无泛化证据） |
| G-D1-05 | 准入状态/决策记录 | registry.py 明确非生产 Registry（描述符存储） | Governance | Registry 非治理权威（I-03） | Case-local Admission Record（状态+决策引用） | YES | **CASE-LOCAL NEED** |
| G-D1-06 | 通用 Agent Manifest / 对象模型 | I-09 小核心 | — | 无真实跨边界证据 | — | NO | **REJECTED PREMATURE CONCEPT** |
| G-D1-07 | 网络补证/来源信任/记忆保留平台 | D0 UC-06 PARTIAL；01-C 无需求 | — | 非当前 BREA 首建 | — | NO | **DEFERRED FUTURE NEED**（01-E/01-F 按需拉动） |

## 判定

- **REAL D2 BLOCKER：NONE**（G-D1-01/02/03/04/05 均有 CASE-LOCAL/EXTENSION/ADAPTER-LOCAL 替代，D2 可本地进行）。
- 泛化候选：G-D1-01/02/03（记录，不提升）。
- 拒绝/推迟：G-D1-06/07。
