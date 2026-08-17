# HANDOFF — Platform Standard Core v0.1（第一 Vertical Slice）

> 阶段：在既有 Agent Runtime 之上实现 Platform Standard Core v0.1 的第一个完整 Vertical Slice（compose_report）。
> 依据：`新任务/ARCHITECTURE_FINAL_v2.2.md`（架构）+ `新任务/PLATFORM_STANDARD_CORE_V0.1_FINAL.md`（工程契约）。
> Runtime baseline：`main @ 9b88c26eef8faf2569cce8ffcb1cb3407e27b980`。
> 状态：**IMPLEMENTED / VERIFIED —— 交付完成，等待下一阶段决策（未 commit/push）**。

---

## 实现了什么

```text
platform_standard/ 包（位于既有 Runtime 之上，不进入 AgentCore）：
  models.py          Standard 对象（CapabilityDescriptor / Invocation / Result / ArtifactRef / TraceEvent / Producer）
  extensions.py      Extension 契约（version/required/payload；required=false 保留，required=true fail closed）
  validation.py      PlatformValidator（envelope / required fields / JSON compat / extension 结构 / result status 语义）
  registry.py        InMemoryDescriptorRegistry（register/get/list，duplicate id+version 拒绝）
  runtime_adapter.py RuntimeAdapter + DirectedReasoner（Standard Invocation → 既有 Runtime → Standard Result）

reference implementation：
  examples/platform_standard_reference.py     ComposeReportCapability + CountWordsCapability + descriptors

vertical slice：
  examples/run_platform_standard_vertical_slice.py   compose_report → Standard Result + ArtifactRef + Minimal Trace

tests：
  tests/test_platform_standard_core.py        PS-1 .. PS-14
```

## 没有实现什么（严格非目标）

```text
Identity / IAM / RBAC / ABAC / Tenant / Delegation
Policy Engine / Approval System
Enterprise Profile / Domain Package / Ontology
Workflow Engine / Control Plane / MCP / A2A / OpenTelemetry
Multi-Agent / Plugin Framework / Production Registry Service
新 Runtime / 新 Agent Loop / AgentCore redesign
```

（这些属于长期架构，未在本阶段实施；如需其中任何一项才能继续，我会先报 BLOCKER，不擅自扩范围。）

## 关键设计决策

- **Adapter 语义映射（不依赖 Runtime exception 类名）**：
  - `rt.start()` 正常返回 + Success observation → `success`
  - `rt.start()` 正常返回 + Failure observation → `failure`
  - `rt.start()` 抛 `RuntimeExecutionError`（capability 异常 / timeout / cancellation 后可能副作用）→ `unresolved`
- **Extension First**：未来 enterprise/domain/governance 变化一律先走 `extensions`（`enterprise.*` / `domain.*` / `governance.*` / `interop.*` / `experimental.*`），不新增 Core 字段。
- **Validator 不重复 Runtime 校验**：execution-time 的 capability input 校验仍由 Runtime/CapabilityExecutor 负责。

## Vertical Slice 是否 PASS

✅ **PASS**（compose_report 完整闭环：descriptor → registry → invocation → validator → adapter → existing Runtime → Standard Result success + 1 个 ArtifactRef + trace events `invocation.started/completed/artifact.created`）。

## Second Capability 是否 PASS

✅ **PASS**（count_words：新增 descriptor + binding，零改动 Core schema / Validator / Runtime / AgentCore；同一 stack 上 compose_report 仍可用；零 artifact 路径也通过）。

## AgentCore 是否保持不变

✅ **保持不变**（`git diff --name-only` 为空：`agent_runtime/**` 零 diff；Runtime / CapabilityExecutor / contracts 均未修改）。

## Runtime 是否发生修改

❌ **未修改**（`agent_runtime/**` 与 `main @ 9b88c26` 完全一致）。

## 所有测试结果

```text
PLATFORM STANDARD (PS-1..PS-14): 14/14 PASS
  PS-1 valid Capability accepted          ✓   PS-8 unresolved no safe retry      ✓
  PS-2 malformed Capability rejected      ✓   PS-9 ArtifactRef validates         ✓
  PS-3 valid Invocation accepted          ✓   PS-10 Trace Event validates        ✓
  PS-4 required Extension rejected        ✓   PS-11 duplicate registry rejected  ✓
  PS-5 optional Extension preserved       ✓   PS-12 vertical slice passes        ✓
  PS-6 success Result validates           ✓   PS-13 second Capability portable   ✓
  PS-7 failure Result validates           ✓   PS-14 uncertain -> unresolved      ✓

EXISTING REGRESSION (examples): 22/22 modules PASS（无回归）
VERTICAL SLICE EXAMPLE: PASS
```

## 发现的架构问题

1. **Adapter 线程模型**：`RuntimeAdapter` 复用单一 Runtime + `DirectedReasoner.pending_action`，当前非线程安全（一次一个 invocation）。v0.1 参考实现可接受；未来若并发调用需独立 adapter/锁或 per-invocation runtime。
2. **`(capability_id, capability_version)` binding 的唯一实现**：同一 capability_id 不同 version 目前映射到同一 Runtime 实现（Runtime key 只有 capability_id）。v0.1 内可接受；未来 version-aware registry 会解决。
3. **Runtime 每次 start 创建新 session**：Adapter 内部每个 invocation 一个 session（正确），但 Runtime 内 ThreadPoolExecutor 随 Runtime 生命周期存在（复用，不泄漏）。
4. **Extension 语义由 Core 未知性决定**：Core v0.1 不实现任何 extension，因此所有 required=true extension 都 fail closed——这是 Spec §4 的预期行为，未来由层实现时逐步放行。

## 下一阶段建议

```text
1. 先由用户审阅本 HANDOFF + vertical slice 运行结果；
2. 若认可，决定是否将本次新增文件纳入 git（commit/push/PR 流程需单独授权）；
3. 下一阶段候选（需独立架构决策，不自动开始）：
   - Extension 层首个真实语义（如 enterprise.* profile 雏形）
   - 第二/第三条 vertical slice 路径（不同 Runtime 组合验证 portability）
   - 显式 timeout 语义映射到 Standard unresolved 的 Adapter 测试
4. 任何 Identity / Policy / Approval / Domain / Workflow / MCP / A2A / Control Plane 都需新 Stage Spec。
```

---

## STOP —— 交付完成，等待用户决策

按架构 §11 release gate：完成 1-5 项（vertical slice / unresolved 映射 / AgentCore 不变 / second capability 不加 Core-Runtime-AgentCore / 全部验收测试）后 **STOP**。未开始 Identity、Policy、Approval、Enterprise Profile、Domain Package、Workflow、MCP、A2A、Control Plane。
