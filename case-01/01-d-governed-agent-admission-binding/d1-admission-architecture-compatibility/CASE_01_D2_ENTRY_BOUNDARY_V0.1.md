# CASE 01-D2 ENTRY BOUNDARY — V0.1（D1 · §27）

> D1 输出（架构边界）。**D1 不授权 D2。**

```text
D1 VERDICT
PASS WITH NON-BLOCKING GAPS（Verdict B）

D2 PURPOSE
证明：BREA v0.1-candidate 经当前 Platform 兼容路径被准入并执行，执行结果/溯源可精确归属到已准入 Agent 版本——无需 Agent==Capability、无需 Platform Core/Runtime 变更。

GOVERNED SUBJECT
BREA — Building Regulation Evidence Agent · v0.1-candidate
定义 SHA 6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4
01-C closure dd491a7 · D0 75a23c5 · D1 4e9a16d

ADMISSION INPUTS
Admission Record（agent_id/version/owner/purpose ref/definition SHA/formation refs/obligations ref/seams ref/fingerprint/enterprise ref/corpus ref/status/decision ref）
定义文件（BUILDER_CONSUMABLE_DEFINITION，SHA 校验）
01-C 形成证据（conformance + 整机 15/15 + T-C01..03）
LOCAL_CORPUS_REFERENCE_MANIFEST（语料边界）

MINIMUM ADMISSION RECORD
MINIMUM_AGENT_ADMISSION_RECORD_CANDIDATE 的 REQUIRED NOW 字段（agent_id/agent_version/owner_ref/definition SHA/fingerprint/enterprise_context/admission_status/decision_ref）+ REFERENCE ONLY 引用

MINIMUM BINDING
已准入 Agent 版本 → BREA runner 实现（fingerprint）→ describe()/invoke() 适配 → RuntimeAdapter 绑定（(capability_id, version)）→ Platform 执行路径

PLATFORM SEAMS REUSED
Invocation · Validator（validation.py）· RuntimeAdapter（runtime_adapter.py）· Runtime（agent_runtime）· Result · ArtifactRef · Trace · Extension 契约（extensions.py）

CASE-LOCAL SEMANTICS
Admission Record 表示 · 实现指纹计算 · BREA runner capability 适配（describe/invoke）· artifact mapper（证据束→ArtifactRef）· 结果契约映射（RegulationEvidenceResult）

EXTENSIONS USED
governance.agent（payload={agent_id, agent_version, admission_ref, binding_ref}，required=false）——置于 Invocation.extensions/context.extensions，执行后写 TraceEvent.extensions（模式=enterprise.identity）
（enterprise.identity 视需要复用承载 org/user/project 归属）

ADAPTER-LOCAL WORK
BREA runner 绑定项 + 证据束 artifact mapper（均为案例局部；不改 RuntimeAdapter 本身）

PLATFORM CORE CHANGE
NONE（S-D1-05 未触发；执行机制全部 REUSE-AS-IS）

RUNTIME CHANGE
NONE（S-D1-06 未触发；Runtime 域无关保持）

REQUIRED D2 TESTS（fail-closed 类，§22 D2 草案）
定义 SHA 不符 → 拒绝准入
指纹不符 → 绑定拒绝
形成证据缺失 → 准入拒绝
未知 Agent 版本 → 拒绝
错误绑定（capability 键错）→ 失败
Agent 归因不匹配（admission/binding ref 与 Trace 不一致）→ fail closed
执行结果不可溯源（无 trace/artifact）→ fail closed
Agent 整机经 Platform 路径执行成功 + 精确版本归因（正向）

D2 ALLOWED WRITE PATHS
case-01/01-d-governed-agent-admission-binding/d2-*（D2 授权后）· 只读引用 case-01/01-b/**、01-c/** 与 Platform/Runtime

D2 FORBIDDEN PATHS
Platform Core / Platform Standard 代码 · Runtime / Runtime Adapter 代码 · enterprise_extensions/ · tests / CI · main · BREA candidate（01-c）· legacy 工作区 · raw corpus

D2 STOP CONDITIONS
需要 Platform Core / 公共契约 / Runtime 变更 → STOP → ARCHITECTURE REVIEW
Agent 必须等于 Capability 才能执行 → STOP
准入需要 Registry 成为治理权威 → STOP
Adapter 成为 Agent 治理所有者 → STOP
硬不变量（I-01..I-10）被违反 → STOP
任何未授权路径写入 → STOP

CASE 01-E
NOT AUTHORIZED
```

**D2 未授权。** D1 完成后 STOP → ChatGPT 外部审查 → 明确授权后 D2。
