# D1 EVIDENCE INDEX — V0.1（§19）

> 每条 D1 断言可被外部审查复现：被检机制、其现有责任、为何可/不可复用、Case-local 语义留在何处、归因路径、Runtime 不变原因、Agent≠Capability 依据。

| D1E | 支持的断言 | 证据（主 SHA 5874be11 文件/符号 + Case 证据） | 复现 |
|---|---|---|---|
| D1E-01 | main 冻结 | git rev-parse origin/main = 5874be1130e8867082880fcd63f659fc909d9efd | `git -C <repo> rev-parse origin/main` |
| D1E-02 | case-01 HEAD/D0/01-C 冻结 | HEAD=4e9a16d；D0=75a23c5；01-C=dd491a7 | `git -C <repo> log --oneline` |
| D1E-03 | Common Envelope + extensions + Invocation.context/trace_id | platform_standard/models.py（CapabilityDescriptor/Invocation/Result/ArtifactRef/TraceEvent；每对象 extensions；Invocation.context: Mapping + trace_id） | 读 models.py |
| D1E-04 | Validator fail-closed；validate_invocation 要求 context.extensions；Trace subject_id 必需 | platform_standard/validation.py（validate_invocation L95-114；validate_trace_event L163-173；validate_extensions 经 extensions.py） | 读 validation.py |
| D1E-05 | Extension 契约；governance. 命名空间保留；Core 无扩展语义 | platform_standard/extensions.py（RESERVED_NAMESPACES 含 "governance."；required=True fail closed） | 读 extensions.py |
| D1E-06 | Registry=描述符存储，非治理权威（I-03） | platform_standard/registry.py（docstring："NOT the future production Registry Service"；register/get/list） | 读 registry.py |
| D1E-07 | Adapter 复用；版本路由；预检；无业务语义；runtime_factory 注入 | platform_standard/runtime_adapter.py（binding key；_checked_direct_binding_descriptor；"carries NO business/domain semantics"；runtime_factory required） | 读 runtime_adapter.py |
| D1E-08 | Extension 归因模式已证（TraceEvent.extensions；冲突 fail-closed） | enterprise_extensions/identity.py（attribute_trace；execute_with_enterprise_identity） | 读 identity.py |
| D1E-09 | 参考实现模式（capability + artifact mapper adapter-local + runtime factory 外部） | examples/platform_standard_reference.py（ComposeReport/CountWords；compose_report_artifact_mapper；reference_runtime_factory） | 读 reference.py |
| D1E-10 | Runtime 协议域无关（Capability.describe/invoke；context=runtime-only） | agent_runtime/contracts/interfaces.py（Capability 协议；Reasoner/Policy/StateStore 注释） | 读 interfaces.py |
| D1E-11 | BREA 形成证据（定义 SHA 6c6e4707；01-C 闭包；FN/SEAM/OBL） | case-01/01-b…/builder/BUILDER_CONSUMABLE_DEFINITION；case-01/01-c…/evidence/**（conformance/results）；identity.py | 读 case-01 证据 |
| D1E-12 | D0 外部判定 | D1 Stage Spec 头部（"D0 external review: EVIDENCE-BACKED PASS / CLOSED AS CASE 01 METHOD PROOF"） | 读 D1 Stage Spec |
| D1E-13 | Agent≠Capability 保持；准入记录 Case-local | MINIMUM_AGENT_ADMISSION_RECORD_CANDIDATE（REJECT Capability/Manifest 字段）；D1 review Q-06/07 | 读本 D1 输出 |
| D1E-14 | Runtime 零变更（执行路径证据） | runtime_adapter.py execute()（Goal→DirectedReasoner→Action→invoke→Success/Failure→Result 映射）；interfaces.py | 读 runtime_adapter.py §5-6 |

## 覆盖率

所有 §19 断言均有 D1E 锚点；无未经代码/契约证据的"Extension 可处理/Adapter 已支持/Runtime 无需变更"声明（§19 要求满足）。
