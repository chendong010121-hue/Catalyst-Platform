"""中性契约层 —— 值对象与占位类型。

只包含纯数据结构，不含任何行为实现、任何具体厂商、任何 I/O。
"互斥联合"均以类型结构表达合法状态：非法组合在类型上就不存在。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

# Capability ID / native tool function-name 的 portable subset。
# 当前 capability ID 直接成为 native tool function.name，DeepSeek/OpenAI-style
# 均支持该子集。禁止在 Provider 层做 name rewrite / alias。
_CAPABILITY_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _is_json_value(value) -> bool:
    """判断 value 是否为合法 JsonValue（None/bool/int/finite-float/str/list/dict[str keys]）。

    与 snapshot.snapshot_value 的接受集严格一致；bytes/tuple/set/frozenset/runtime
    object 一律 False。仅用于构造期校验，不做深拷贝。
    """
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(isinstance(k, str) and _is_json_value(v) for k, v in value.items())
    if isinstance(value, list):
        return all(_is_json_value(v) for v in value)
    return False

# ---------------------------------------------------------------------------
# 占位类型（具体形状在后续阶段定义）
# ---------------------------------------------------------------------------

# 会话当前状态：目标、进度、已积累的事实/计划/中间结果等。
State = Mapping[str, Any]

# 通用参数载体（能力参数、模型参数、约束等）。
Parameters = dict[str, Any]


# ---------------------------------------------------------------------------
# 基础值对象
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Goal:
    """任务目标：一段自然语言描述。"""

    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.description, str):
            raise ValueError("Goal.description must be a str")


@dataclass(frozen=True)
class Action:
    """一次"调用某个能力"的请求。

    capability_id：要调用的能力标识（由 Reasoner 在 Decision 中指名）。
    parameters：传给该能力的参数。
    """

    capability_id: str
    parameters: Parameters = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Decision：下一步决策（互斥联合，四选一）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Act:
    """继续执行：调用某个能力。"""

    action: Action


@dataclass(frozen=True)
class Complete:
    """目标已完成。reason 为可选的完成说明（仅供人读，不用于判断类型）。"""

    reason: str | None = None


@dataclass(frozen=True)
class Fail:
    """执行失败。reason 说明失败原因（仅供人读，不用于判断类型）。"""

    reason: str


@dataclass(frozen=True)
class Blocked:
    """被阻塞，无法继续。reason 说明阻塞原因（仅供人读，不用于判断类型）。"""

    reason: str


# 下一步决策 = 继续 | 完成 | 失败 | 阻塞。
# Core 用 isinstance 区分终止类型，而不是解析 reason 文本。
Decision = Act | Complete | Fail | Blocked


# ---------------------------------------------------------------------------
# Observation：能力调用的观测结果（互斥联合，二选一）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Success:
    """调用成功，data 携带返回负载。"""

    data: Any = None


@dataclass(frozen=True)
class Failure:
    """调用失败，error 携带错误说明。"""

    error: str


# 观测结果 = 成功 | 失败。成功不带 error，失败不带 data，矛盾组合在类型上不存在。
Observation = Success | Failure


# ---------------------------------------------------------------------------
# Model：厂商无关的请求 / 响应
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelToolDefinition:
    """model-visible 工具定义；来自 CapabilityDescriptor，但不是 Capability，没有 invoke()。"""

    name: str
    description: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("ModelToolDefinition.name must be a non-empty str")
        if not isinstance(self.description, str):
            raise ValueError("ModelToolDefinition.description must be a str")
        if not isinstance(self.parameters, Mapping) or not _is_json_value(self.parameters):
            raise ValueError(
                "ModelToolDefinition.parameters must be a JSON object "
                "(Mapping with string keys and JsonValue values)"
            )


@dataclass(frozen=True)
class ModelToolCall:
    """模型发起的一次工具调用；arguments 保留原始 JSON 字符串。"""

    id: str
    name: str
    arguments: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("ModelToolCall.id must be a non-empty str")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("ModelToolCall.name must be a non-empty str")
        if not isinstance(self.arguments, str):
            raise ValueError("ModelToolCall.arguments must be a str (raw provider JSON)")


@dataclass(frozen=True)
class Message:
    """一条消息。role 区分 system / user / assistant / tool。

    合法形态：
    - system / user：content=str
    - assistant：content=str 或 tool_calls 非空（可同时存在）
    - tool：content=str + tool_call_id
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: tuple[ModelToolCall, ...] = ()
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        # 通用：tool_call_id 只能是 None 或 str；tool_calls 只能是 ModelToolCall 序列。
        if self.tool_call_id is not None and not isinstance(self.tool_call_id, str):
            raise ValueError("tool_call_id must be None or str")
        if not isinstance(self.tool_calls, (tuple, list)):
            raise ValueError("tool_calls must be a tuple/list of ModelToolCall")
        if not all(isinstance(c, ModelToolCall) for c in self.tool_calls):
            raise ValueError("tool_calls must contain only ModelToolCall values")
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls))

        if self.role == "tool":
            if self.tool_calls:
                raise ValueError("tool message must not have tool_calls")
            if not isinstance(self.tool_call_id, str) or not self.tool_call_id:
                raise ValueError("tool message requires a non-empty string tool_call_id")
            if not isinstance(self.content, str):
                raise ValueError("tool message requires string content")
        elif self.role in ("system", "user"):
            if not isinstance(self.content, str):
                raise ValueError(f"{self.role} message requires string content")
            if self.tool_calls:
                raise ValueError(f"{self.role} message must not have tool_calls")
            if self.tool_call_id is not None:
                raise ValueError(f"{self.role} message must not have tool_call_id")
        elif self.role == "assistant":
            if self.tool_call_id is not None:
                raise ValueError("assistant message must not have tool_call_id")
            if self.content is not None and not isinstance(self.content, str):
                raise ValueError("assistant message content must be string or None")
            if (self.content is None or self.content == "") and not self.tool_calls:
                raise ValueError("assistant message must have non-empty content or tool_calls")
        else:
            raise ValueError(f"unknown role: {self.role!r}")


@dataclass(frozen=True)
class ModelRequest:
    """与厂商无关的通用模型请求。

    messages：由 Reasoner 组织好的消息列表。
    tools：native tool calling 的工具定义（可为空）。
    tool_choice：v0.1 只支持 None / "auto"。
    parameters：通用采样/输出参数（不得含厂商细节）。
    """

    messages: Sequence[Message]
    tools: tuple[ModelToolDefinition, ...] = ()
    tool_choice: str | None = None
    parameters: Parameters = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.messages, (tuple, list)):
            raise ValueError("ModelRequest.messages must be a tuple/list of Message")
        if not all(isinstance(m, Message) for m in self.messages):
            raise ValueError("ModelRequest.messages must contain only Message values")
        object.__setattr__(self, "messages", tuple(self.messages))

        if not isinstance(self.tools, (tuple, list)):
            raise ValueError("ModelRequest.tools must be a tuple/list of ModelToolDefinition")
        if not all(isinstance(t, ModelToolDefinition) for t in self.tools):
            raise ValueError("ModelRequest.tools must contain only ModelToolDefinition values")
        object.__setattr__(self, "tools", tuple(self.tools))

        if self.tool_choice is not None and self.tool_choice != "auto":
            raise ValueError("ModelRequest.tool_choice must be None or 'auto'")
        if not isinstance(self.parameters, Mapping) or not _is_json_value(self.parameters):
            raise ValueError(
                "ModelRequest.parameters must be a JSON object (Mapping with string keys)"
            )


@dataclass(frozen=True)
class ModelUsage:
    """标准化的 token 用量（为预算 Policy 提供事实数据）。"""

    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"ModelUsage.{name} must be a non-negative int, got {value!r}")

    @property
    def total_tokens(self) -> int:
        """总 token = 输入 + 输出（派生值，避免与字段不一致）。"""
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ModelResponse:
    """与厂商无关的通用模型响应。

    content：模型输出的文本内容；native tool call 时可为 None。
    tool_calls：native tool calls（可为空）。
    finish_reason：结束原因（stop / tool_calls / length ...），可为 None。
    usage：token 用量，可为 None。
    """

    content: str | None = None
    tool_calls: tuple[ModelToolCall, ...] = ()
    finish_reason: str | None = None
    usage: ModelUsage | None = None

    def __post_init__(self) -> None:
        if self.content is not None and not isinstance(self.content, str):
            raise ValueError("ModelResponse.content must be None or str")
        if not isinstance(self.tool_calls, (tuple, list)):
            raise ValueError("ModelResponse.tool_calls must be a tuple/list of ModelToolCall")
        if not all(isinstance(c, ModelToolCall) for c in self.tool_calls):
            raise ValueError("ModelResponse.tool_calls must contain only ModelToolCall values")
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls))
        if self.finish_reason is not None and not isinstance(self.finish_reason, str):
            raise ValueError("ModelResponse.finish_reason must be None or str")
        if self.usage is not None and not isinstance(self.usage, ModelUsage):
            raise ValueError("ModelResponse.usage must be None or ModelUsage")


@dataclass(frozen=True)
class ModelCallRecord:
    """一次"成功产生 Decision 的模型调用"的最小事实。

    usage：本次调用的 token 用量，可为 None（厂商可能不返回）。
    finish_reason：结束原因，可为 None。
    tool_calls：native tool calls（原始 id/name/arguments 持久化）。
    assistant_message：provider-neutral 的 assistant 消息（content + tool_calls），
                       用于 native 下一轮 lossless 重建。

    canonical source：assistant_message 是 canonical assistant output；
    tool_calls 是 derived convenience projection。两者若同时存在必须完全一致，
    否则构造即失败（不允许 silent divergence）。
    """

    usage: ModelUsage | None = None
    finish_reason: str | None = None
    tool_calls: tuple[ModelToolCall, ...] = ()
    assistant_message: Message | None = None

    def __post_init__(self) -> None:
        if self.usage is not None and not isinstance(self.usage, ModelUsage):
            raise ValueError("ModelCallRecord.usage must be None or ModelUsage")
        if self.finish_reason is not None and not isinstance(self.finish_reason, str):
            raise ValueError("ModelCallRecord.finish_reason must be None or str")
        if not isinstance(self.tool_calls, (tuple, list)):
            raise ValueError("ModelCallRecord.tool_calls must be a tuple/list of ModelToolCall")
        if not all(isinstance(c, ModelToolCall) for c in self.tool_calls):
            raise ValueError("ModelCallRecord.tool_calls must contain only ModelToolCall values")
        object.__setattr__(self, "tool_calls", tuple(self.tool_calls))
        if self.assistant_message is not None:
            if not isinstance(self.assistant_message, Message):
                raise ValueError("ModelCallRecord.assistant_message must be None or Message")
            if self.assistant_message.role != "assistant":
                raise ValueError("ModelCallRecord.assistant_message must have role 'assistant'")
            # canonical consistency：projection 不得与 canonical 漂移
            if tuple(self.tool_calls) != tuple(self.assistant_message.tool_calls):
                raise ValueError(
                    "ModelCallRecord.tool_calls must equal assistant_message.tool_calls"
                )


@dataclass(frozen=True)
class ReasoningResult:
    """Reasoner.decide 的返回：结构化 Decision + 本次推理的模型调用事实。

    model_call 为 None 表示该 Decision 不是由模型调用产生的（如规则/脚本 Reasoner）。
    """

    decision: Decision
    model_call: ModelCallRecord | None = None


@dataclass(frozen=True)
class CapabilityDescriptor:
    """能力的自描述元数据，供 Reasoner 决定"用哪个能力"。

    id 直接成为 native tool function.name，因此必须是 portable function-name
    subset：^[A-Za-z0-9_-]{1,64}$。禁止 dotted/domain/带空格/超长 id。
    """

    id: str
    name: str
    description: str
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("CapabilityDescriptor.id must be a non-empty str")
        if not _CAPABILITY_ID_RE.fullmatch(self.id):
            raise ValueError(
                f"CapabilityDescriptor.id must match ^[A-Za-z0-9_-]{{1,64}}$ "
                f"(portable model tool name), got {self.id!r}"
            )
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("CapabilityDescriptor.name must be a non-empty str")
        if not isinstance(self.description, str):
            raise ValueError("CapabilityDescriptor.description must be a str")


# ---------------------------------------------------------------------------
# Policy 前置校验判定（互斥联合，二选一）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Allow:
    """允许执行。"""


@dataclass(frozen=True)
class Deny:
    """拒绝执行，reason 说明明确原因。

    Core 把 Deny 结果记入历史/上下文，交由 Reasoner 重新决策。
    Action 的产生与修改始终属于 Reasoner。
    """

    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str):
            raise ValueError("Deny.reason must be a str")


# 前置校验判定 = 允许 | 拒绝。
PolicyVerdict = Allow | Deny


# ---------------------------------------------------------------------------
# Native tools v2：model-turn batch progress（独立于 v0.1 Act/PendingExecution）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NativeToolsV2FailureAttribution:
    """Bounded Harness-side attribution fact for one v2 model-turn failure."""

    stage: str
    owner: str
    failure_type: str
    observed_fact: str
    provider_completed: bool
    downstream_tool_execution_started: bool
    side_effect_certainty: str
    unproven_downstream_boundary: str
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "stage",
            "owner",
            "failure_type",
            "observed_fact",
            "side_effect_certainty",
            "unproven_downstream_boundary",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"NativeToolsV2FailureAttribution.{name} must be a non-empty str")
        if type(self.provider_completed) is not bool:
            raise ValueError("NativeToolsV2FailureAttribution.provider_completed must be bool")
        if type(self.downstream_tool_execution_started) is not bool:
            raise ValueError(
                "NativeToolsV2FailureAttribution.downstream_tool_execution_started must be bool"
            )
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValueError(
                "NativeToolsV2FailureAttribution.evidence_reference must be None or str"
            )


@dataclass(frozen=True)
class NativeToolsV2RecoveryEvidence:
    """Durable bounded fact about a v2 recovery decision."""

    kind: Literal["settled_history_recovered"]
    tool_call_id: str
    execution_id: str
    source: Literal["authoritative_history"]
    replayed: bool
    observed_fact: str

    def __post_init__(self) -> None:
        if self.kind != "settled_history_recovered":
            raise ValueError(f"invalid NativeToolsV2RecoveryEvidence.kind: {self.kind!r}")
        if not isinstance(self.tool_call_id, str) or not self.tool_call_id:
            raise ValueError("NativeToolsV2RecoveryEvidence.tool_call_id must be a non-empty str")
        if not isinstance(self.execution_id, str) or not self.execution_id:
            raise ValueError("NativeToolsV2RecoveryEvidence.execution_id must be a non-empty str")
        if self.source != "authoritative_history":
            raise ValueError(f"invalid NativeToolsV2RecoveryEvidence.source: {self.source!r}")
        if type(self.replayed) is not bool:
            raise ValueError("NativeToolsV2RecoveryEvidence.replayed must be bool")
        if not isinstance(self.observed_fact, str) or not self.observed_fact:
            raise ValueError(
                "NativeToolsV2RecoveryEvidence.observed_fact must be a non-empty str"
            )


@dataclass(frozen=True)
class NativeToolsV2Call:
    """Durable progress for one provider-neutral tool-call intent."""

    tool_call_id: str
    name: str
    arguments: str
    action: Action | None = None
    status: Literal["pending", "settled", "denied", "skipped", "invalid"] = "pending"
    policy_verdict: PolicyVerdict | None = None
    execution_id: str | None = None
    observation: Observation | None = None
    uncertainty: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tool_call_id, str) or not self.tool_call_id:
            raise ValueError("NativeToolsV2Call.tool_call_id must be a non-empty str")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("NativeToolsV2Call.name must be a non-empty str")
        if not isinstance(self.arguments, str):
            raise ValueError("NativeToolsV2Call.arguments must be a str")
        if self.action is not None and not isinstance(self.action, Action):
            raise ValueError("NativeToolsV2Call.action must be None or Action")
        if self.status not in ("pending", "settled", "denied", "skipped", "invalid"):
            raise ValueError(f"invalid NativeToolsV2Call.status: {self.status!r}")
        if self.policy_verdict is not None and not isinstance(self.policy_verdict, (Allow, Deny)):
            raise ValueError("NativeToolsV2Call.policy_verdict must be None, Allow, or Deny")
        if self.execution_id is not None and (
            not isinstance(self.execution_id, str) or not self.execution_id
        ):
            raise ValueError("NativeToolsV2Call.execution_id must be None or non-empty str")
        if self.observation is not None and not isinstance(self.observation, (Success, Failure)):
            raise ValueError("NativeToolsV2Call.observation must be None or Observation")
        if self.uncertainty is not None and not isinstance(self.uncertainty, str):
            raise ValueError("NativeToolsV2Call.uncertainty must be None or str")
        if self.status == "settled" and self.execution_id is None:
            raise ValueError("settled NativeToolsV2Call requires execution_id")
        if self.status == "denied" and not isinstance(self.policy_verdict, Deny):
            raise ValueError("denied NativeToolsV2Call requires Deny policy_verdict")
        if self.status in ("settled", "denied") and self.uncertainty is not None:
            raise ValueError("settled/denied NativeToolsV2Call must not carry uncertainty")


@dataclass(frozen=True)
class NativeToolsV2Turn:
    """Durable model-turn batch; one turn owns zero or more correlated calls."""

    turn_id: str
    model_call: ModelCallRecord
    calls: tuple[NativeToolsV2Call, ...] = ()
    next_index: int = 0
    status: Literal["executing", "completed", "failed", "blocked"] = "executing"
    failure_attribution: NativeToolsV2FailureAttribution | None = None
    recovery_evidence: tuple[NativeToolsV2RecoveryEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.turn_id, str) or not self.turn_id:
            raise ValueError("NativeToolsV2Turn.turn_id must be a non-empty str")
        if not isinstance(self.model_call, ModelCallRecord):
            raise ValueError("NativeToolsV2Turn.model_call must be ModelCallRecord")
        if not isinstance(self.calls, (tuple, list)):
            raise ValueError("NativeToolsV2Turn.calls must be a tuple/list")
        if not all(isinstance(call, NativeToolsV2Call) for call in self.calls):
            raise ValueError("NativeToolsV2Turn.calls must contain NativeToolsV2Call values")
        object.__setattr__(self, "calls", tuple(self.calls))
        if type(self.next_index) is not int or self.next_index < 0 or self.next_index > len(self.calls):
            raise ValueError("NativeToolsV2Turn.next_index must point inside calls")
        if self.status not in ("executing", "completed", "failed", "blocked"):
            raise ValueError(f"invalid NativeToolsV2Turn.status: {self.status!r}")
        if self.failure_attribution is not None and not isinstance(
            self.failure_attribution, NativeToolsV2FailureAttribution
        ):
            raise ValueError(
                "NativeToolsV2Turn.failure_attribution must be None or NativeToolsV2FailureAttribution"
            )
        if not isinstance(self.recovery_evidence, (tuple, list)):
            raise ValueError("NativeToolsV2Turn.recovery_evidence must be a tuple/list")
        if not all(
            isinstance(event, NativeToolsV2RecoveryEvidence) for event in self.recovery_evidence
        ):
            raise ValueError(
                "NativeToolsV2Turn.recovery_evidence must contain "
                "NativeToolsV2RecoveryEvidence values"
            )
        object.__setattr__(self, "recovery_evidence", tuple(self.recovery_evidence))
        ids = [call.tool_call_id for call in self.calls]
        if len(ids) != len(set(ids)):
            raise ValueError("NativeToolsV2Turn.call tool_call_id values must be unique")
        model_ids = [call.id for call in self.model_call.tool_calls]
        if tuple(ids) != tuple(model_ids):
            raise ValueError("NativeToolsV2Turn.calls must match model_call.tool_calls")


# ---------------------------------------------------------------------------
# Execution reconciliation：resolution 类型 + durable audit fact
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfirmedNotExecuted:
    """外部事实确认：该 pending execution 没有产生 authoritative side effect。"""

    note: str | None = None


@dataclass(frozen=True)
class ConfirmedExecuted:
    """外部事实确认：真实 side effect 已发生，且 caller 提供 authoritative Observation。"""

    observation: Observation
    note: str | None = None


# reconciliation 的外部判定（二选一，类型结构表达合法状态）。
ExecutionResolution = ConfirmedNotExecuted | ConfirmedExecuted


@dataclass(frozen=True)
class ExecutionReconciliation:
    """reconciliation 的 durable audit fact。"""

    execution_id: str
    resolution: str  # "confirmed_not_executed" | "confirmed_executed"
    observation: Observation | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, str) or not self.execution_id:
            raise ValueError("ExecutionReconciliation.execution_id must be a non-empty str")
        if self.resolution not in ("confirmed_not_executed", "confirmed_executed"):
            raise ValueError(f"invalid reconciliation resolution: {self.resolution!r}")
        if self.note is not None and not isinstance(self.note, str):
            raise ValueError("ExecutionReconciliation.note must be None or str")
        if self.observation is not None and not isinstance(
            self.observation, (Success, Failure)
        ):
            raise ValueError("ExecutionReconciliation.observation must be None or Observation")
        # 交叉字段语义：resolution 与 observation 必须自洽
        if self.resolution == "confirmed_executed":
            if not isinstance(self.observation, (Success, Failure)):
                raise ValueError(
                    "confirmed_executed requires a Success or Failure observation"
                )
        elif self.resolution == "confirmed_not_executed":
            if isinstance(self.observation, Success):
                raise ValueError(
                    "confirmed_not_executed must not carry a Success observation"
                )


# ---------------------------------------------------------------------------
# StepRecord：一次 Agent step 的执行记录
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StepRecord:
    """一次 Agent step 的记录。

    index：step 序号（起始值由 Core 决定）。
    decision：本步的决策（必填，每步必有决策）。
    policy_verdict：前置校验判定（若发生；如 Deny 时填写）。
    observation：能力调用的观测结果（若发生了调用；Complete/Blocked/Deny
                 等未执行 Capability 的 step 为 None）。
    model_call：产生本步 decision 的模型调用事实（usage / finish_reason；
                非模型 Reasoner 或失败 attempt 时为 None）。
    termination：本步执行后 Policy 的强制终止（Stop.reason 为停止原因；
                 正常继续或未触发停止时为 None）。
    """

    index: int
    decision: Decision
    policy_verdict: PolicyVerdict | None = None
    observation: Observation | None = None
    model_call: ModelCallRecord | None = None
    termination: Stop | None = None
    execution_id: str | None = None
    reconciliation: ExecutionReconciliation | None = None


# ---------------------------------------------------------------------------
# PendingExecution：尚未可靠结算的执行意图
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PendingExecution:
    """一个已耐久记录、但尚未耐久结算的 execution intent。

    含义：Harness 已记录"准备执行什么"，但没有耐久记录正常结算结果。
    因此外部副作用可能未发生、部分发生或已发生（final save 丢失），Harness 不知道。
    """

    execution_id: str
    step_index: int
    action: Action
    model_call: ModelCallRecord | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_id, str) or not self.execution_id:
            raise ValueError("execution_id must be a non-empty string")
        if (
            isinstance(self.step_index, bool)
            or not isinstance(self.step_index, int)
            or self.step_index < 0
        ):
            raise ValueError("step_index must be a non-negative integer")


# ---------------------------------------------------------------------------
# Session 快照
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionSnapshot:
    """一个 Session 当前可恢复的快照：目标 + 状态 + 历史 + pending execution + 身份。

    保存 Goal，使程序退出后仅凭快照即可恢复并知道任务原目标。
    这是 StateStore 读写的基本单位；一次 step 的状态变化与新增历史
    作为同一个快照一次性提交（见 StateStore.commit）。
    pending_execution 非 None 表示存在 unresolved execution，resume 必须 fail-closed。
    """

    session_id: str
    goal: Goal
    state: State
    history: tuple[StepRecord, ...] = ()
    pending_execution: PendingExecution | None = None
    native_tools_v2_turns: tuple[NativeToolsV2Turn, ...] = ()


# ---------------------------------------------------------------------------
# Policy 终止判定（互斥联合，二选一）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Continue:
    """继续执行，不停止。"""


@dataclass(frozen=True)
class Stop:
    """应停止执行，reason 说明停止原因（如预算耗尽、步数用尽、致命错误）。"""

    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str):
            raise ValueError("Stop.reason must be a str")


# 终止判定 = 继续 | 停止。停止必带原因。
Termination = Continue | Stop


__all__ = [
    # 基础值对象
    "Goal",
    "Action",
    "CapabilityDescriptor",
    # Decision 联合
    "Act",
    "Complete",
    "Fail",
    "Blocked",
    "Decision",
    # Observation 联合
    "Success",
    "Failure",
    "Observation",
    # Model
    "Message",
    "ModelToolDefinition",
    "ModelToolCall",
    "ModelRequest",
    "ModelUsage",
    "ModelResponse",
    "ModelCallRecord",
    "NativeToolsV2Call",
    "NativeToolsV2FailureAttribution",
    "NativeToolsV2RecoveryEvidence",
    "NativeToolsV2Turn",
    "ReasoningResult",
    # Policy 前置校验联合
    "Allow",
    "Deny",
    "PolicyVerdict",
    # Reconciliation
    "ConfirmedNotExecuted",
    "ConfirmedExecuted",
    "ExecutionResolution",
    "ExecutionReconciliation",
    # Session 快照
    "PendingExecution",
    "SessionSnapshot",
    # Policy 终止联合
    "Continue",
    "Stop",
    "Termination",
    # 占位类型
    "State",
    "StepRecord",
    "Parameters",
]
