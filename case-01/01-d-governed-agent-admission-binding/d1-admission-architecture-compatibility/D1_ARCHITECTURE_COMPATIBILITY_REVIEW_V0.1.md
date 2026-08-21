# D1 ARCHITECTURE COMPATIBILITY REVIEW — V0.1（CASE 01-D / D1）

> **ARCHITECTURE REVIEW ONLY**（docs / architecture-evidence）。主 SHA：`5874be1130e8867082880fcd63f659fc909d9efd`；case-01 HEAD：`4e9a16d813df0f09b05d9cd473818f3fbba57635`。
> 依据：D1 Stage Spec（CASE_01_D_D1_ADMISSION_ARCHITECTURE_COMPATIBILITY_V0.1_STAGE_SPEC.md）+ D1_EXECUTION_AUTHORIZATION_V0.1.md。

## 受治理对象（Q-01 — 被准入的精确对象）

```text
BREA — Building Regulation Evidence Agent
版本 v0.1-candidate
已接受治理定义 SHA 6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4
形成证据：CASE 01-C closure dd491a7（FN-01..11 / SEAM-01..03 / OBL-01..06 conformance；整机 15/15 + T-C01..03）
实现指纹：candidate/brea-v0.1 源树 + BUILDER_OUTPUT_MANIFEST 哈希（D2 计算）
```

最小证据支撑的受治理主体 = **Agent 身份 + 版本 + 定义引用 + 形成证据引用 + 实现指纹**（一个 Case-local Admission Record 元组）——不是文件、类、注册表条目或 manifest SDK。

## 主要架构问题（Q-01..Q-12）

### Q-02 最小 Agent Admission Record
见 `MINIMUM_AGENT_ADMISSION_RECORD_CANDIDATE_V0.1.md`（CASE-LOCAL；字段 REQUIRED/REFERENCE/DERIVED/DEFER/REJECT 分类）。

### Q-03 准入证据
Formation Evidence（已存在，REUSE-AS-IS）：定义 SHA、01-C 形成闭包、Builder→Candidate 溯源、FN/SEAM/OBL 符合、整机测试、语料边界引用（LOCAL_CORPUS_REFERENCE_MANIFEST）。
Admission Decision（CASE-LOCAL）：所有者/验收权威（F-07 User/CASE 01）、准入状态记录。
**Formation Evidence ≠ Admission Decision**（形成证据告知准入，不自授权）。

### Q-04 实现指纹
最小确定性：`candidate/brea-v0.1` 源树全量 SHA-256 + BUILDER_OUTPUT_MANIFEST SHA（D2 以脚本计算并记录）。目标=已准入版本不得静默绑定到不同实现。不建签名/供应链系统。

### Q-05 执行绑定
`已准入 Agent 版本 → 实现身份（指纹）→ 执行入口（BREA runner 以 Runtime Capability 协议适配）→ 现有 Platform 兼容路径（Invocation→Validator→RuntimeAdapter→Runtime→Result/ArtifactRef/Trace）`。
Binding 拥有：兼容/翻译、实现目标、版本关系、执行入口引用。Binding 不拥有：专业 Domain 含义、企业策略、Agent 产品目的、Runtime 执行语义。

### Q-06 当前 Platform Standard 能否执行 BREA 而不致 Agent==Capability —— **PARTIAL（可本地实现）**
- 执行机制（Invocation/Validator/Adapter/Runtime/Result/ArtifactRef/Trace）可 **REUSE-AS-IS**：BREA runner 实现 Runtime Capability 协议（describe/invoke，interfaces.py；参考 examples/platform_standard_reference.py 的 reference capabilities），经 RuntimeAdapter 绑定（(capability_id, version)→实现；预检结构符合；版本路由）执行。
- Agent 身份/版本/准入 保持独立于 Capability 身份：存放于 Case-local Admission Record + `governance.agent` Extension 归因（Q-07）。**Agent != Capability 保持**（I-02）。
- 证据：models.py（Invocation.context/trace_id/extensions）、validation.py（context.extensions 必需——扩展可携带归因）、extensions.py（`governance.` 保留命名空间）、runtime_adapter.py（"carries NO business/domain semantics"；版本路由；预检）。

### Q-07 精确 Agent 归因如何穿越执行 —— **EXTENSION（优先）**
`governance.agent` Extension（version/required=false/payload={agent_id, agent_version, admission_ref, binding_ref}）：
- 置于 `Invocation.extensions`（Validator 结构校验；Core v0.1 对可选扩展原样保留——extensions.py）与/或 `Invocation.context.extensions`；
- 执行后由 Case-local attribution 助手写入 `TraceEvent.extensions`（模式已由 `enterprise_extensions/identity.py::attribute_trace` 证明：冲突 fail-closed、无 Core 新字段）。
- **PREFER EXTENSION；无需修改 Platform Core**。

### Q-08 Adapter 需要知道什么 —— **REUSE AS-IS + 最小 Case-local 包装**
- 现有 RuntimeAdapter 保持通用（无业务/治理语义）——REUSE AS-IS。
- Case-local：BREA runner 作为 capability 实现（describe/invoke）+ 可选 artifact mapper（BREA 证据束→ArtifactRef；模式见 compose_report_artifact_mapper）。
- Adapter **不**成为 Agent 治理/工作流/策略/企业所有者（runtime_adapter.py 已强制 runtime_factory 外部注入 Policy/StateStore）。

### Q-09 Runtime 是否需要变更 —— **NO（证明）**
- 执行路径：Invocation → RuntimeAdapter.execute → Runtime.start(Goal) → DirectedReasoner 注入 Action(internal_key, input) → CapabilityExecutor → BREA runner.invoke → Success/Failure → Result 映射（success/failure/unresolved）。
- Runtime 只需能力映射（capabilities 键控）与执行语义；BREA 以 capability 实现身份进入——Runtime 无需理解 Domain/Enterprise/治理语义（interfaces.py；runtime_adapter.py §5-6）。
- 无 Runtime 变更（S-D1-06 未触发）。

### Q-10 最小企业参与
- organization_ref / owner（Product-Release Authority）/ project_ref / evaluation-acceptance authority / Agent ownership → CASE-LOCAL Enterprise 上下文记录（沿用 F-07 最小归属）。
- 不实现 IAM/RBAC/审批流/来源信任平台/网络策略平台/保留平台（D1 §10；Q-10 排除清单）。

### Q-11 Domain 保持
- 专业适用性/事实词汇/来源权威/数值安全/专业不确定性 全部留在 Domain/BREA；Admission/Binding 不拥有其中任何一项（Domain 不进 Platform/Runtime——I-06/I-11 保持）。

### Q-12 D2 必须证明（见 `CASE_01_D2_ENTRY_BOUNDARY_V0.1.md`）

## 不变量核对（I-01..I-10 / S-D1-01..12）

I-01 Agent=主治理单元 ✓（Admission Record 以 Agent 为对象）· I-02 Agent≠Capability ✓（Q-06/07）· I-03 Admission≠Registry.register ✓（registry.py=描述符存储，注释明确"NOT the future production Registry Service"）· I-04 Admission≠runnable ✓（形成/准入/执行三分离）· I-05 Binding≠identity ✓（Q-05）· I-06 Domain/Enterprise 不沉底 ✓（Q-10/11）· I-07 Runtime 域无关 ✓（Q-09）· I-08 Extension First ✓（Q-07）· I-09 小核心 ✓（无厚 Agent 对象模型——Admission Record 为 Case-local 最小元组）· I-10 可替换 ✓（Binding 支持未来 Implementation B，I-05/Q-05）。
S-D1-01..12：**均未触发**（无需 Agent==Capability；无需 Registry 作治理权威；无需 Runtime 承载身份；Adapter 非治理所有者；无需改 Platform 公共契约；无需改 Runtime；未重设计 FN/SEAM/OBL；D0 意图未作为规范性；企业分类未静默提升；未设计厚对象模型；未开始实现；无未授权变更）。

## 判定（§22）

**VERDICT: B — PASS WITH NON-BLOCKING GAP CANDIDATES**
D2 可在本地进行（REUSE-AS-IS + CASE-LOCAL + EXTENSION + ADAPTER-LOCAL；无 Platform Core/Runtime 变更）；可泛化缺口已记录（PLATFORM_GAP_REGISTER_D1：G-D1-01..05）为后续评审候选，**D1 不实现任何缺口**。
