# Agent Runtime — 架构（v1.9 · Cooperative Cancellation & Timeout v0.1 Mainline Alignment）

> 版本：v1.9 —— 反映当前真实实现，不是设计文档。
> 状态：Runtime（create/run/resume/start/reconcile/cancel）/ AgentCore / LLMReasoner / DeepSeekModelProvider / CapabilityExecutor（ExecutionRunner）/ 生产安全 Policy 已存在并可运行；Cooperative Cancellation & Timeout v0.1 已完成 mainline realignment（移除 RuntimeDomain / cross-Runtime domain 扩张，保留同 Runtime 执行所有权边界内的 cancellation/timeout/late-evidence/live-guard 语义）。本地实现 + 全量回归 + 500 stress + 内审完成，状态 READY FOR USER GIT/PUSH APPROVAL。
> 原则：只收敛与加固，不扩张。不引入第三方框架、事件总线、动态插件、多 Agent、Cordis。

---

## 1. 总体视图

```
                      目标 / 任务
                          │
                 ┌────────▼────────────────┐
                 │        Runtime          │  组合根 · 生命周期(create/run/start/resume/reconcile/cancel)
                 └────────┬────────────────┘
                          │ 装配并驱动
                 ┌────────▼────────────────┐
                 │       AgentCore          │  Agent Loop / 控制流（不推理、不直接调用 Capability）
                 └──┬─────────┬──────┬──────┘
                    │         │      │
        ┌───────────▼───┐ ┌───▼────┐ ┌▼───────────────┐
        │   Reasoner     │ │ Policy │ │ CapabilityExecutor │  以及 StateStore（读写快照）
        │ (如何思考)      │ │(fail-closed)│ │(resolve/validate/  │
        └───────┬───────┘ └────────┘ │ invoke/normalize) │
                │ 依赖接口           └───────┬────────┘
        ┌───────▼────────┐                  │
        │  ModelProvider  │                  ▼
        │ (DeepSeek 已接入)│            Capability（可执行能力）
        └────────────────┘
```

推理链：`AgentCore → Reasoner → ModelProvider → DeepSeek API`。
执行链：`AgentCore → CapabilityExecutor → Capability`。

---

## 2. 各模块职责

### 2.1 AgentCore —— Agent Loop / 控制流

只做两件事：跑 Agent Loop，编排循环内各抽象模块。**不推理、不解析模型文本、不认识 ModelRequest/ModelResponse、不直接调用 Capability、不做 input schema validation。**

关键不变量：

- 能力选择由 Reasoner 在 Decision 中指名；Core 把 Action 交给 `CapabilityExecutor.execute`。
- Core 不 lookup capability、不调用 `Capability.invoke`、不 normalize 异常、不校验返回契约（这些都是 CapabilityExecutor 的事）。
- Policy 返回值 **fail-closed**：非 `Allow/Deny` 或非 `Continue/Stop` → `PolicyContractError`，绝不默认为 Allow/Continue。
- Policy `Stop(reason)` 写入触发它的 step 的 `termination`。
- 成功 reasoning 的 `model_call`（usage/finish_reason）随 StepRecord 持久化。
- 进入 durable history 的数据负载（`Action.parameters` / `Observation.data`）在 StepRecord 构造边界 snapshot，与调用方后续 mutation 解耦。
- **Execution Lifecycle：Policy Allow 后在 Capability 执行前先 durable prepare（PendingExecution），得到 Observation 后单次 settle（StepRecord + pending=None）。**
- 分配 runtime `execution_id`（与 `tool_call_id` 分离）。

### 2.2 Reasoner —— 如何思考

组织 Goal / State / History / CapabilityDescriptor → 构造 provider-neutral `ModelRequest` → 调 `ModelProvider` → 解析并校验成 `Decision`，连同 `model_call` facts 返回 `ReasoningResult`。

契约：`decide(...) -> ReasoningResult`（无 `evaluate`）。解析失败抛 `DecisionParseError`（模型协议失败）。

`decision_protocol`：`legacy_json`（默认，模型输出 JSON Decision 文本）或 `native_tools`（native tool calling）。不做 provider-specific 分支。

**finish_reason 语义（legacy 与 native 统一 fail-closed）**：

```text
finish_reason in {None, "stop"}       → 允许 parse legacy/native 最终 Decision
finish_reason in {length, content_filter, tool_calls, insufficient_system_resource, 其它未知}
                                      → DecisionParseError（模型协议失败）
```

- `None = provider omitted finish reason`（FakeProvider / 本地 scripted provider），**不是**"默认当 stop"的 provider-specific 假设。
- 截断前缀（`length`）恰好是合法 JSON 时，**绝不**被当作权威 Complete。

### 2.3 ModelProvider —— 由哪个模型完成推理

provider-neutral 边界：收 `ModelRequest`，返回 `ModelResponse`。**一次 `request()` = 一次模型 attempt，无隐藏 retry。** 不认识 AgentCore / Reasoner / Capability / CapabilityExecutor / Policy。

当前实现：`DeepSeekModelProvider`（`deepseek-v4-flash`，non-thinking，非流式，one-attempt，finite timeout）。支持 native tool calling（`tools` / assistant `tool_calls` / `tool` 结果消息映射；`arguments` 保留原始 JSON string）。厂商差异只留在 Provider 内。

**DeepSeek concrete response envelope（non-stream）**：generic `ModelResponse` 仍允许 `finish_reason=None`（fake/local provider 可省略），但 DeepSeek adapter 对真实 non-stream response 严格要求：

```text
message.role == "assistant"                          （否则 ModelProviderError）
finish_reason ∈ {stop, length, content_filter,
                 tool_calls, insufficient_system_resource}
                                                     （missing/null/non-str/unknown → ModelProviderError）
```

malformed vendor envelope 里的 `ValueError`/`TypeError`/`KeyError`/`AttributeError` 统一归一化为 `ModelProviderError`，不泄漏到 Provider seam。`length`/`content_filter` 在 Provider 层是合法 vendor response，在 Reasoner 层再 fail-closed。

### 2.4 Runtime —— 宿主 / 生命周期 / 组合根

生命周期 API：

```python
create(goal)        -> SessionSnapshot   # 生成 id、建初始快照、持久化、返回（不跑 loop）
run(session_id)     -> SessionSnapshot   # load + 结构校验 + unresolved 检查 + AgentCore.run
resume(session_id)  -> SessionSnapshot   # run 的别名
start(goal)         -> SessionSnapshot   # create + run（run 失败抛 RuntimeExecutionError，含 session_id）
reconcile(session_id, execution_id, resolution)
                    -> SessionSnapshot   # load + 结构校验 + 显式恢复 unresolved；resolution 携带 observation/note（见 §4）
cancel(session_id)  -> CancelRequestResult  # 对 live execution 请求 cooperative cancellation（signal only，不写 Session）
```

recovery 顺序（run / resume / reconcile 共用）：

```text
load → validate_session_snapshot → pending gate → terminal / execution
```

组合：

```python
# Runtime 直接组合 StateStore；内部自建 Runtime-local ExecutionControlPlane
runtime = Runtime(
    reasoner=reasoner,
    capabilities=capabilities,
    policy=policy,
    state_store=state_store,
    timeout_config=ExecutionTimeoutConfig(...),   # 可选
)
```

**Execution ownership boundary（同 Runtime 边界）**：`ExecutionControlPlane` 是 Runtime-local 执行控制服务，由单个 Runtime 组合根创建并拥有（`Runtime.__init__` 内部创建 `ExecutionControlPlane()`，注入 `DefaultCapabilityExecutor` / `ThreadedExecutionRunner`，供 `Runtime.cancel` / `Runtime.reconcile` 查询同一份 active/evidence 状态）。它不是 StateStore namespace 身份、不是多 Runtime 协调器、不是分布式所有权服务、不是 process-wide singleton。`Runtime` 直接接受 `state_store`（纯 `load`/`commit` 契约），不再要求 domain claim / mixin。

> **Architecture statement（v0.1 mainline）**
> - Cooperative Cancellation & Timeout v0.1 is supported within one Runtime execution ownership boundary.
> - ExecutionControlPlane is Runtime-local.
> - Multiple Runtime instances concurrently coordinating the same live Session are not supported in v0.x.
> - RuntimeDomain / Store-domain claim is not part of the current Runtime contract.

关键语义：

- **Runtime 失败 ≠ Session 自动删除**。`create` 成功后 session 是持久事实，`run`/`start` 失败仍可 `resume`。
- `start` 的 run 阶段失败时，抛出 `RuntimeExecutionError(session_id=...)`，原始异常作为 `__cause__`。
- **Capability registration 不变量（key==descriptor.id、schema 支持）由 CapabilityExecutor 校验，Runtime 不重复实现。**
- **生产组合必须包含有限 loop guard**（如 `StepLimitPolicy`）；Runtime 不把预算逻辑写进自身。

### 2.5 CapabilityExecutor —— 执行 seam

本轮唯一新增的核心执行抽象（`DefaultCapabilityExecutor`）。

负责：

```text
resolve → validate input → invoke → normalize → Observation
```

- `descriptors()` 返回 model-visible descriptors（stable order，id 与 lookup identity 一致）。
- `execute(action)` 按固定顺序执行：snapshot → resolve → validate → invoke → normalize → snapshot durable Observation。
- 构造阶段校验 registration 不变量：**mapping key 是 non-empty str**、descriptor.id 是 portable capability ID、key==id、input_schema 只使用受支持的 subset。
- **不支持 ≠ 忽略**：schema 声明了 executor 不实现的 keyword（如 `minLength`）→ `CapabilityRegistrationError`。

**执行结果确定性（execution certainty）**：

```text
Capability RETURNS Failure   = 作者明确声明 authoritative known failure → 可 settle
Capability RAISES            = outcome uncertain（副作用可能已发生）→ CapabilityExecutionError
                               → Core 保留 durable PendingExecution unresolved
unknown capability / schema-invalid → body 未运行 → known Failure → settle
invalid return / unsnapshotable     → CapabilityContractError → pending unresolved
```

`exception != proof of non-execution`。这是 Timeout/Cancellation 的基础语义：不自动 retry / auto reconcile，只能 operator/external verification → `Runtime.reconcile`。

**执行 concurrency/cancellation（见 §2.11）**：`DefaultCapabilityExecutor` 持有 `ExecutionRunner`（默认 `ThreadedExecutionRunner`）与 `ActiveExecutionRegistry`，把 `execution_id`/`session_id` 传入执行；`invoke` 通过 `ExecutionContext` 获得 cooperative cancellation/deadline 检查。

不负责 reasoning、policy、session lifecycle、retry、approval、sandbox、model calls。

### 2.6 Capability —— Agent-facing 可执行能力

> **Agent-facing executable capability：Reasoner 可以选择，CapabilityExecutor 可以执行，并得到 Observation 的能力。**

- 实现 `describe()` + `invoke(parameters, context) -> Observation`；`invoke` 返回值**必须是** `Success` 或 `Failure`，否则 `CapabilityContractError`。
- `context` 是 runtime-only `ExecutionContext`：提供 `is_cancel_requested()` / `raise_if_cancelled()` / `remaining_seconds()`，供 cooperative cancellation/deadline 检查；它**不是** agent-visible tool argument，也**不**进入 `CapabilityDescriptor` schema。
- **`CapabilityDescriptor.input_schema` 是单一声明源：同时用于 Reasoner model-visible 描述 + Executor runtime validation。**
- **portable capability ID contract**：`descriptor.id` 必须是 `^[A-Za-z0-9_-]{1,64}$`。它直接成为 native tool `function.name`（DeepSeek/OpenAI-style 均兼容），禁止 dotted/domain/带空格/超长 id；Provider 层不做 name rewrite / alias。
- identity 不变量：`mapping key == descriptor.id`（CapabilityExecutor 构造时校验，key 必须是 non-empty str）。
- 基础设施服务（StateStore backend / filesystem / HTTP transport / credential store / sandbox / LLM provider / telemetry）不应被强迫实现 `invoke()`。

### 2.7 State / Session —— 事实源 + 快照

- History / StepRecord = 执行事实源；State = projection/cache（当前基本空 `{}`）。
- snapshot-first，非完整 Event Sourcing。
- `SessionSnapshot(session_id, goal, state, history, pending_execution)` 经 `StateStore.commit()` 原子提交；`pending_execution` 非 None 表示 unresolved execution。
- **StateStore durability contract：`commit(snapshot)` 正常返回意味着该 snapshot 已达到实现承诺的 durability level，并成为后续 load/recovery 的 authoritative snapshot；atomicity 与 durability 是两个不同要求。当前 InMemoryStateStore 只是测试替身。**
- **single-writer-per-session：同一 session 的并发写者是 harness 级 bug（未实现 optimistic concurrency / version 检查）。当前 Runtime 每次只串行驱动一个 loop；多进程/多实例并发驱动同一 session 不在支持范围内。**
- **ownership isolation：`StateStore.commit/load` 边界做防御性快照（`validate_session_snapshot`），commit 后调用方对 snapshot 的 mutation 不影响存储，load 出的对象改动也不污染存储（InMemoryStateStore 同样遵守）。**
- **recovery structural validation：`validate_session_snapshot(snapshot, expected_session_id=None)` 在 load 之后、任何 Reasoner/Policy/Executor 行为之前执行；校验 session_id / goal / state(JsonValue) / history(index==position、closed-union、execution_id 唯一、reconciliation 自洽) / pending(step_index==len(history)、execution_id 不与 settled 冲突、Action 合法)；malformed → `SessionConsistencyError`（fail-closed，不做 migration/repair/reorder）。**
- **Session identity：`StateStore.load(session_id)` 返回的 snapshot 必须满足 `snapshot.session_id == requested session_id`。`Runtime.run/resume/reconcile` 与 `AgentCore.run` 每次都传 `expected_session_id=session_id`；不匹配 → `SessionConsistencyError`（跨 Session 防护，不信任 Store routing）。**
- **Core authoritative state boundary**：每次 Core 使用的 authoritative load 都先 `validate_session_snapshot`（`AgentCore.run` 循环内每次 load 都 validate，不只在 Runtime 入口 validate 一次）；每次 Core/Runtime 构造的 authoritative commit 都先 `validate_session_snapshot` 再 `StateStore.commit`（`AgentCore._commit_snapshot` / `Runtime.create` / `Runtime.reconcile`）。StateStore 只负责 durability/ownership，不替 Core 兜底业务结构一致性。
- **native Action provenance：当 `model_call.tool_calls` 非空时，Decision 必须是 Act、恰好一个 tool call、`tool_call.name == action.capability_id`、`json.loads(tool_call.arguments)` 与 `action.parameters` 做 type-aware JSON equality（bool≠number）。该 shared validator 复用于 Core ReasoningResult contract、settled StepRecord recovery、PendingExecution recovery。**
- **StepRecord cross-field semantic shapes（真实 Agent Loop 只能产生的合法形态）**：

  ```text
  Act + Allow      → observation=Success|Failure + execution_id=non-empty str
  Act + Deny       → observation=None + execution_id=None + reconciliation=None
  Act + (其它)     → 非法（Act 必须有 Allow 或 Deny）
  Complete/Fail/Blocked → policy_verdict/observation/execution_id/reconciliation/termination 全 None
  terminal step（decision∈terminal 或 termination=Stop）→ 必须是 history 尾
  reconciliation   → step.observation == step.reconciliation.observation（同一 execution 只有一种 durable outcome）
  ```

- terminal 判定：最后一步 `decision ∈ {Complete, Fail, Blocked}` 或 `termination is Stop`；terminal 再 resume 直接返回。
- immutability：commit 后的数据负载与外部 mutation 解耦（snapshot 边界在 StepRecord / Observation 构造处；model 序列字段 tuple 规范化，不 alias 外部 mutable list）。

### 2.8 Policy —— fail-closed 确定性护栏

只做机械、可解释、确定性的裁决：

- 前置校验：`Allow` / `Deny(reason)`。
- 终止护栏：`Continue` / `Stop(reason)`。
- **返回未知类型是 contract violation（`PolicyContractError`），不是默认 Allow / Continue。**
- 无 Amend / constraints，不修改 Action 参数、不选替代能力；Action 的产生与修改始终属于 Reasoner。
- **Policy 仍在 CapabilityExecutor 外面**（`Action → Policy.check_action → Allow → Executor.execute`）。
- 生产安全 Policy：`StepLimitPolicy(max_steps)`、`TokenBudgetPolicy(max_tokens)`（见 `agent_runtime/policies.py`）。

### 2.9 Native Tool Calling 协议

- `ModelToolDefinition(name, description, parameters)`：model-visible 工具定义，来自 `CapabilityDescriptor`，不是 Capability，没有 `invoke()`。
- `ModelToolCall(id, name, arguments)`：模型发起的一次工具调用；`arguments` 保留原始 JSON string，Provider 不提前 `json.loads`。
- `Message` 可表达 structured tool history：`assistant(tool_calls)` + `tool(tool_call_id, content)`。
- Native 链：`CapabilityDescriptor → ModelToolDefinition → ModelRequest.tools → ModelProvider → ModelToolCall → Reasoner Act → Policy → CapabilityExecutor`。
- **`tool_call_id` 属于 model protocol history，不属于 Action/Capability execution identity（`execution_id`）。**
- Native Decision 语义：1 个 tool_call → Act；0 个 tool_call + 文本 → Complete；>1 → `DecisionParseError`；非法 JSON arguments → `DecisionParseError`；schema-invalid args → Act → Executor `Failure`。
- **ModelCallRecord tool-call canonical source**：`assistant_message` 是 canonical assistant output，`ModelCallRecord.tool_calls` 是 derived convenience projection。两者同时存在时必须完全一致，否则构造即 `ValueError`（不允许 silent divergence）；`assistant_message is None` 时 `tool_calls` 是唯一 source（legacy / 历史重建路径）。

### 2.10 Provider-neutral Model Value Contract

以下值对象均为 runtime validated（`__post_init__` fail-fast，非法即 `ValueError`），不是 annotation-only：

```text
ModelToolCall        id non-empty str / name non-empty str / arguments str（原始 JSON）
ModelToolDefinition  name non-empty str / description str / parameters 合法 JsonValue
Message              role 语义 + tool_call_id None|str + tool_calls 只含 ModelToolCall
ModelRequest         messages 只含 Message / tools 只含 ModelToolDefinition /
                     tool_choice None|"auto" / parameters 合法 JsonValue
ModelResponse        content None|str / tool_calls ModelToolCall 序列 /
                     finish_reason None|str / usage None|ModelUsage
ModelCallRecord      usage None|ModelUsage / finish_reason None|str /
                     tool_calls ModelToolCall 序列 / assistant_message None|Message(assistant)
                     + tool_calls == assistant_message.tool_calls（canonical consistency）
```

所有 model 序列字段（`Message.tool_calls` / `ModelResponse.tool_calls` / `ModelCallRecord.tool_calls` / `ModelRequest.messages` / `ModelRequest.tools`）在 `__post_init__` 里 `tuple` 规范化，`frozen` 值对象不再 alias 外部 mutable list。

`snapshot_model_call / snapshot_message / snapshot_model_tool_call` 逐字段 canonicalize 并 fail-closed；runtime object / 非 str 字段无法进入 durable history。DeepSeek 只负责把官方响应映射为已校验的值对象，不重复实现这些不变量。

### 2.11 Cooperative Cancellation & Timeout

> **Cancellation 是请求，不是事实；Timeout 是 deadline，不是结果。**

执行路径：`durable prepare → active execution register → ExecutionContext → worker/invoke → authoritative result / confirmed cancellation / unresolved → owner-only settlement`。

```text
RUNNING
  ├─ returns Observation            → SETTLED（Success/Failure）
  ├─ raises ExecutionCancelled（cooperative）→ SETTLED Failure("execution cancelled")
  ├─ raises ordinary exception      → UNRESOLVED（CapabilityExecutionError）
  └─ deadline reached
       ├─ request cancellation
       └─ wait grace period
            ├─ cooperative ExecutionCancelled → SETTLED Failure("execution cancelled")
            ├─ returns authoritative Observation → SETTLED with that Observation
            └─ still running / unknown          → UNRESOLVED（CapabilityTimeoutUncertainError）
```

- **cooperative，非 preemptive**：不支持杀线程/强杀 frame。`request_cancel` 只是 signal；只有 Capability 通过 Harness 拥有的 `CancellationToken.raise_if_cancelled()` 抛出携带 provenance marker 的 `ExecutionCancelled` 才算 confirmed cooperative cancellation。
- **timeout ≠ Failure**：timeout 只是 cancellation request source。deadline 后若拿到 authoritative Success/Failure 仍以之为准；不能因"曾经超时"覆盖为 Failure。
- **non-cooperative timeout**：grace 后未确认 quiesce → `CapabilityTimeoutUncertainError`（outcome unknown），Core 保留 durable `PendingExecution` unresolved。worker 可能在后台继续运行；其晚到结果被记录为 runtime-local late evidence（不 auto-settle），future 完成触发 publish evidence + identity-safe cleanup。
- **live execution registry lifetime**：`ActiveExecutionRegistry` 中存在某 entry 表示"该 execution 仍可能改变现实"（不是"owner 仍在 wait"）。timeout uncertain 时 worker 明确可能仍 live → **entry 保留**；只有 `future.done() == True` 后才移除（正常结果/异常/confirmed cancel 在 owner 观察到 future 完成时立即移除；uncertain 时 attach done callback 做 identity-safe cleanup）。
- **reconciliation vs live execution guard**：`Runtime.reconcile` 在 load+validate+pending 检查后，若 `registry.get(session_id) == pending.execution_id`，抛 `ExecutionStillLiveError`（无论 ConfirmedNotExecuted / ConfirmedExecuted）。因为外部断言可能在某一瞬间正确，而仍 live 的 worker 未来仍可改变现实；只有 worker 真正 quiesce（registry 清理）后才允许 reconcile。
- **late completion evidence**：timeout uncertain 后 worker 完成时，done callback 以固定顺序 `publish evidence → remove active`（Invariant I2，杜绝 active=None 且 evidence=None 的 visibility hole）；分类：返回 Success/Failure → authoritative；抛 proven ExecutionCancelled（本 token raise_if_cancelled）→ authoritative `Failure("execution cancelled")`（与 normal cooperative cancellation 一致）；抛 unproven/spurious ExecutionCancelled → uncertain；抛普通异常 / invalid return → uncertain。`Runtime.reconcile` 若本地有 authoritative late outcome：`ConfirmedNotExecuted` 被拒、矛盾 `ConfirmedExecuted` 被拒、匹配 `ConfirmedExecuted` 允许；late 异常（uncertain）仍允许外部 reconcile。
- **Runtime-local execution control plane**：`ExecutionControlPlane`（含 `ActiveExecutionRegistry` + `LateCompletionEvidenceRegistry`）由单个 Runtime 组合根拥有，供 `Runtime.cancel`/`Runtime.reconcile` 与 `CapabilityExecutor`/`ThreadedExecutionRunner` 查询同一份 active/evidence 状态。`Runtime` 直接接受 `state_store`（纯 load/commit），不再有 `RuntimeDomain` / domain claim。下层 `DefaultCapabilityExecutor` 若 timeout enabled 且无 control plane → `RuntimeConfigurationError`。
- **Observation equality（JsonValue-aware）**：`observation_equal` 用 `json_value_equal` 比较 Success.data，禁止 Python `==`（否则 `Success(True)==Success(1)` 会被误判相等）；用于 late evidence 校验与 recovery reconciliation 一致性。
- **evidence ownership isolation**：`LateCompletionEvidenceRegistry` 的 record/read 双向 `snapshot_observation` 防御快照，caller 不能 mutate registry 内部事实。
- **evidence cleanup lifecycle**：`Runtime.reconcile` 只在 `StateStore.commit` 成功后才 `evidence.remove(exact identity)`；commit 失败则 pending + evidence 都保留。
- **submit-failure cleanup**：`pool.submit` 在 Future 存在前抛异常 → 移除 false-live registry entry（worker 未启动），pending 保留，operator 可 reconcile `ConfirmedNotExecuted`。
- **ExecutionCancelled provenance**：`ExecutionCancelled` 是 internal provenance-bearing cooperative cancellation signal，可携带 process-local marker。只有 Harness 拥有的 `CancellationToken.raise_if_cancelled()` 才会抛出携带本 token marker 的 confirmed cancellation；手动 raise `ExecutionCancelled()`（无 marker）或 foreign marker 是 Capability contract violation → `CapabilityContractError` → unresolved。cancellation request 状态在后被观察到，不能 retroactively 合法化更早产生的 unproven exception。
- **timeout classification**：用 `concurrent.futures.wait([future], timeout=...)` 区分"wait deadline 到期"（future not in done）与"task 自身抛 TimeoutError"（future done + result() 抛）。只有前者才是 Harness deadline → request cancel；后者是 capability 普通异常 → `CapabilityExecutionError`。
- **deadline 用 monotonic clock**（`time.monotonic`），不做 wall-clock duration correctness；monotonic timestamp 不持久化。
- **runtime-only control plane**：`CancellationToken` / `CancellationSource` / `ExecutionContext` / `ActiveExecutionRegistry` / threading.Event 都不 durable，绝不进入 `SessionSnapshot` / `PendingExecution` / `StepRecord` / `snapshot_value`。process crash 后 active token/registry/manual cancel 请求丢失，但 durable `PendingExecution` 仍 fail-closed。
- **single-writer**：只有 AgentCore/Runtime owner thread 写 Session；worker 只返回 Observation/异常。`Runtime.cancel()` 只改 runtime-local cancellation source，不算第二个 Session writer。
- **explicit cancel API**：`Runtime.cancel(session_id) -> CancelRequestResult`（requested + execution_id）；无 active 时 `requested=False`，不修改 durable Session。registry 用 `session_id + execution_id` 做 identity 匹配，防止旧 cleanup 误删新 registration；同 session 重复 active register fail-closed。
- **`ExecutionTimeoutConfig(timeout_seconds=None, cancellation_grace_seconds=0.5)`**：timeout 是 runtime execution policy/config，不是 agent-visible tool argument；`None` 表示无 deadline（cooperative cancel 仍可用）。配置不持久化，resume 用当前 Runtime config（属 composition continuity Known Debt）。

Capability author 规范：只在语义安全的 cancellation point 检查 token；不要在不可回滚的原子 side effect 中间随便 cancel；长循环定期检查；可中断 I/O 用自身 timeout + `min(remaining_seconds, own_timeout)`；无法确认真实外部状态时不要改抛 `Failure`。

---

## 3. Agent Loop（真实顺序，与代码一致）

```text
load session → validate_session_snapshot（结构一致性 fail-closed）
→ 若 pending_execution != None → UnresolvedExecutionError（fail-closed）
→ reasoner.decide(...) → ReasoningResult(decision + model_call)
→ if Act:
     canonical Action snapshot
     policy.check_action → Allow / Deny（否则 PolicyContractError）
     if Allow:
        allocate execution_id
        持久化 PendingExecution（prepare save，BEFORE 执行）
        capability_executor.execute → Observation
        构造 settled StepRecord（execution_id + observation）
        policy.should_stop(next history) → Continue / Stop
        → 单次 settled commit（history += step，pending=None）
     if Deny:
        记录 Deny step（无 execution_id，无 pending）→ 单次 commit
→ next decide / terminal
```

注意：**prepare save 成功以前，Capability body 绝不运行。** 终止判定发生在"构造 next history"之后、"一次 commit"之前；Stop 原因写进当前 step 的 `termination` 字段后随该 step 一起 commit。

每一次 authoritative commit（prepare / settle / terminal）都先经 `validate_session_snapshot`（Core `_commit_snapshot`）再 `StateStore.commit`，因此任何 Core 构造的 malformed snapshot 都不会进入任意 StateStore。

---

## 4. Execution Lifecycle & Crash Semantics

真实顺序（Policy Allow 后）：

```text
Reasoner → Act → Policy Allow
→ allocate execution_id
→ 持久化 PendingExecution（prepare save）
→ CapabilityExecutor.execute
→ Observation
→ 单次 settled snapshot commit（history += StepRecord，pending=None）
```

Crash semantics：

```text
If prepare save fails:  capability does not run.
If execution returns Observation and settlement save succeeds:  execution is settled.
If execution may have run but no settled snapshot is durable:  pending_execution remains unresolved.
Resume never auto-replays unresolved execution（UnresolvedExecutionError）。

**unresolved real-world execution 的 recovery priority 高于 terminal history：pending != None 时 fail-closed，terminal fast-path 绝不隐藏 unresolved execution。**
```

Source of Truth：

```text
Unresolved execution → SessionSnapshot.pending_execution
Settled execution     → StepRecord(execution_id, decision, observation)
```

Identity（严格分离，不可互换）：

```text
ModelToolCall.id = model protocol correlation
execution_id      = harness execution lifecycle correlation
```

Reconciliation（显式、可审计、非自动化）：

```text
UNRESOLVED（pending != None）
→ external confirmation（人工/外部系统）
→ Runtime.reconcile（验证 execution_id + resolution；复用 resolve_step_termination 跑 post-step should_stop）
→ 单次 settled commit（StepRecord + reconciliation provenance + pending=None）
→ 显式 Runtime.resume → 正常 loop
```

reconcile 关键语义：

- **不再调用 `Policy.check_action`**：原始 Action 早已 Allow，reconciliation 不是新执行。
- **必须重跑 post-step `should_stop`**：与正常 `_finalize` 走同一 `resolve_step_termination`，因此 Stop 判定在 reconcile 路径同样生效。
- `confirmed_not_executed` → 确定性 `Failure("execution reconciliation confirmed: capability did not execute")`。
- `confirmed_executed` → 要求 caller 提供 authoritative `Observation`（structural union，Success/Failure）。

resolution 语义：

```text
confirmed_not_executed = 外部事实确认 authoritative side effect 未发生
confirmed_executed      = 外部事实确认执行已发生，且 caller 提供 authoritative Observation
```

Harness 不自动推断这两个状态。`confirmed_not_executed` 不等于 auto retry，只是让下一轮 Reasoner 重新获得决策权。

Source of Truth 更新：

```text
Unresolved         → SessionSnapshot.pending_execution
Settled normal     → StepRecord(reconciliation=None)
Settled reconciled → StepRecord(reconciliation=ExecutionReconciliation(...))
```

`PendingExecution` 保存原 `ModelCallRecord`（assistant_message / tool_call_id / usage），使 native structured history 在 reconciliation 后继续。

---

## 5. Failure taxonomy（失败分类）

### Agent-level failure（进入 Session history，Reasoner 可据此重新决策）

- Capability execution Failure → `Observation.Failure`
- **invalid model arguments（input_schema 校验失败）→ `Observation.Failure`，capability body 不执行**
- Policy `Deny(reason)`
- terminal Decision：`Complete / Fail / Blocked`
- Policy `Stop(reason)` → 写入 `StepRecord.termination`

### Harness / Infrastructure failure（作为异常向调用方传播，不伪装成 Capability Failure）

- Reasoner exception（如 `DecisionParseError`）
- ModelProvider exception
- Policy contract violation → `PolicyContractError`
- Capability contract violation → `CapabilityContractError`
- Capability execution uncertainty（invoke 抛异常，副作用可能已发生）→ `CapabilityExecutionError`（不伪装成 Observation.Failure）
- Capability cooperative cancellation（token 触发，body 已 quiesce）→ `ExecutionCancelled`（internal signal → settle Failure("execution cancelled")）
- deadline 后未确认 quiesce → `CapabilityTimeoutUncertainError`（不伪装成 Observation.Failure("timeout")）
- pending execution 对应的 local worker 仍 live 时 reconcile → `ExecutionStillLiveError`（ReconciliationError 子类）
- Capability registration error（含 unsupported schema / 非 portable id / 非 str key）→ `CapabilityRegistrationError`
- Session recovery structural violation → `SessionConsistencyError`（不伪装成 Observation.Failure / Blocked）
- StateStore failure
- Core invariant violation
- Unresolved execution → `UnresolvedExecutionError`（不伪装成 Observation.Failure / Blocked）

`Runtime.start` 的 run 阶段失败被包装为 `RuntimeExecutionError(session_id=...)`（保留 `__cause__`）。

---

## 6. 允许的依赖方向

| 依赖方 | 允许依赖 | 禁止依赖 |
|---|---|---|
| **AgentCore** | `Reasoner/CapabilityExecutor/Policy/StateStore` 接口 + 值对象 | 具体实现、推理逻辑、领域、I/O、SDK、ModelRequest/ModelResponse、具体 Capability |
| **Reasoner** | `ModelProvider` 接口 + 值对象 | Core、具体 Capability、Policy、Runtime、厂商 SDK、直接网络 I/O |
| **ModelProvider** | `ModelRequest/ModelResponse` 值对象 + 自身 SDK/配置 | Core、Reasoner、Capability、Policy、State |
| **CapabilityExecutor** | `Capability` 接口 + 值对象 + snapshot | Core、Reasoner、ModelProvider、Policy、retry/approval/sandbox |
| **Runtime** | Core、Reasoner、ModelProvider、CapabilityExecutor、所有具体实现（组合根） | 不做循环决策、不做推理 |
| **Capability** | 接口 + 值对象 + 自身客户端 | Core、Reasoner、ModelProvider、Policy、CapabilityExecutor、其他具体 Capability |
| **State/Session** | 接口 + 值对象 + 自身后端 | Core、Reasoner、其他具体实现 |
| **Policy** | 接口 + 值对象 + history 快照 | Core、Reasoner、ModelProvider、具体 Capability |

单向调用链：`Core → Reasoner → ModelProvider`；`Core → CapabilityExecutor → Capability`。

---

## 7. 绝对不能进入 AgentCore 的东西

1. 智能推理逻辑。
2. 具体模型实现。
3. 具体能力实现。
4. **capability mapping lookup / `Capability.invoke` / 异常归一化 / 返回契约校验（属 CapabilityExecutor）。**
5. **input schema validation（属 CapabilityExecutor）。**
6. 业务/领域逻辑。
7. 任何 I/O 与基础设施。
8. 具体存储细节。
9. 硬编码规则（预算、白名单、停止条件——属 Policy）。
10. 能力/模型的位置与实现细节（属 Runtime / Executor）。
11. 配置解析、日志、传输、并发调度、启停管理（属 Runtime）。
12. 任何"改 Core 才能换模型/加能力"的东西。

---

## 8. 当前未实现 / Non-goals

- streaming / multimodal / retry engine / context compaction。
- approval / sandbox / metrics / middleware / pre-post hooks。
- parallel capability calls。
- State projection / Event Sourcing / Session event system。
- HTTP / CLI / 动态插件发现 / DI 框架 / 多 Agent / workflow engine。
- 建筑规范 / Rhino 等任何领域能力。

### 8.1 Known debt（诚实记账，不伪装已实现）

- **无生产 durable backend**：StateStore 只有内存测试替身；`commit` 的 durability 由后端自行承诺，框架不提供磁盘/事务实现。
- **single-writer only**：无并发写保护 / version 检查（CAS/versioning 未实现），多写者冲突不在支持范围（见 §2.7）。
- **snapshot-first 非 event sourcing**：History 只保留终态快照，无法重放中间事件流。
- **reconciliation 的 Observation 复制**：`ExecutionReconciliation.observation` 与 settled StepRecord 的 `observation` 会各存一份权威 Observation（分别供审计与 loop 使用），存在事实重复，接受为当前取舍。
- **failed model-attempt usage 不持久化**：provider 返回 usage 但 Reasoner parse 失败（malformed JSON arguments / protocol mismatch / policy failure / terminal commit failure）时，usage 不进 Session history。因此 `TokenBudgetPolicy` 是"persisted successful-decision model calls"的 post-step budget，**不是**完整的 provider-attempt billing ledger。未实现 `ModelAttemptRecord` / usage journal。
- **native Reasoner 未消费 State projection**：legacy 请求包含 State，native 请求目前只包含 Goal/Tools/structured history，不含 State。State 当前基本为 `{}`，故行为一致；一旦 State projection 实现，两协议将语义分叉（本轮不实现）。
- **runtime composition continuity 不持久化**：Session 不保存 Reasoner 实现/版本、decision_protocol、Policy 配置、Capability set/version、provider 配置。因此 v0.x `resume` 假设"恢复 Session 的 Runtime composition 与创建时语义兼容"（否则 legacy↔native 历史解释、预算语义、能力契约可能错位）。未实现 composition hash / version / manifest / migration。
- **thread 无法强杀**：cooperative cancellation 依赖 Capability 主动检查 token；non-cooperative worker 会继续运行并占用 worker slot，真正强隔离需 process worker / sandbox / remote executor。
- **cancellation control plane 不 durable**：active token / registry / manual cancel 请求在进程 crash 后丢失（durable `PendingExecution` 仍 fail-closed）。
- **无自动 late-result reconciliation**：timeout unresolved 后 worker 晚到的 Success/Failure 被记录为 runtime-local late evidence（用于 reconciliation 一致性校验），不 auto-settle；future 完成触发 publish evidence + identity-safe cleanup。需显式 `Runtime.reconcile`（且在 registry 清理后）。
- **无 process isolation**：v0.1 只有 thread-based worker，无 OS 信号编排 / 分布式取消。
