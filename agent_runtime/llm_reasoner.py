"""LLMReasoner：领域无关的通用推理器（v0.1，架构收敛版）。

职责：
- 依据 Goal / State / Step history / CapabilityDescriptor 构造 provider-neutral
  ModelRequest（system + user 消息）；
- 调用 ModelProvider 得到 ModelResponse；
- 把 ModelResponse 的 JSON 输出解析并校验为结构化 Decision
  （Act / Complete / Fail / Blocked）；
- 把本次模型调用的 usage / finish_reason 封装为 ModelCallRecord，
  随 ReasoningResult 一起返回（供 StepRecord 持久化，避免 usage 蒸发）。

边界：
- 不依赖任何厂商 SDK、不直接网络 I/O；
- 不执行 Capability（只产出 Decision）；
- 不认识 AgentCore / Policy / StateStore；
- 一次 ModelProvider.request = 一次模型 attempt，不隐藏 retry。
"""

from __future__ import annotations

import json
from typing import Sequence

from .contracts import (
    Act,
    Action,
    Allow,
    Blocked,
    CapabilityDescriptor,
    Complete,
    Decision,
    Deny,
    Fail,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelToolDefinition,
    ReasoningResult,
    State,
    StepRecord,
    Success,
)


class DecisionParseError(Exception):
    """模型输出无法解析为合法 Decision（Reasoner / 模型协议失败）。"""


_SYSTEM_PROMPT = (
    "You are a decision-making agent. Respond with exactly one JSON object "
    "and nothing else.\n"
    "Valid decisions:\n"
    '  {"kind": "act", "capability_id": "<string>", "parameters": {<object>}}\n'
    '  {"kind": "complete", "reason": "<string>"}\n'
    '  {"kind": "fail", "reason": "<string>"}\n'
    '  {"kind": "blocked", "reason": "<string>"}\n'
)

_NATIVE_SYSTEM_PROMPT = (
    "You are an agent. Use the supplied tools when needed. "
    "When a tool result gives you enough information, answer directly. "
    "Do not invent tool results."
)


# ---------------------------------------------------------------------------
# 确定性 renderer：把历史/观测渲染为稳定、可读、JSON-safe 的文本
# ---------------------------------------------------------------------------

def _to_json_safe(value):
    """把任意值转成 JSON 可序列化值；非 JSON-native 用稳定类型名兜底。

    无序集合（set/frozenset）按稳定表示排序，保证确定性输出（不依赖 hash seed）。
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted((_to_json_safe(v) for v in value), key=repr)
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v) for v in value]
    return f"<{type(value).__name__}>"


def _render_json(value) -> str:
    return json.dumps(_to_json_safe(value), ensure_ascii=False)


def _format_observation(observation) -> str:
    if isinstance(observation, Success):
        return f"Success({_render_json(observation.data)})"
    if isinstance(observation, Failure):
        return f"Failure({observation.error!r})"
    return "None"


def _format_policy_verdict(verdict) -> str:
    if isinstance(verdict, Deny):
        return f"Deny(reason={verdict.reason!r})"
    if isinstance(verdict, Allow):
        return "Allow"
    return "None"


def _format_step(step: StepRecord) -> str:
    decision = step.decision
    lines = [f"- step {step.index}:"]

    if isinstance(decision, Act):
        lines.append("  decision: Act")
        lines.append(f"  capability_id: {decision.action.capability_id}")
        lines.append(f"  parameters: {_render_json(decision.action.parameters)}")
        lines.append(f"  policy: {_format_policy_verdict(step.policy_verdict)}")
        lines.append(f"  observation: {_format_observation(step.observation)}")
    elif isinstance(decision, Complete):
        lines.append("  decision: Complete")
        lines.append(f"  reason: {decision.reason}")
    elif isinstance(decision, Fail):
        lines.append("  decision: Fail")
        lines.append(f"  reason: {decision.reason}")
    elif isinstance(decision, Blocked):
        lines.append("  decision: Blocked")
        lines.append(f"  reason: {decision.reason}")

    if step.termination is not None:
        lines.append(f"  termination: Stop(reason={step.termination.reason!r})")

    return "\n".join(lines)


def _format_history(history: Sequence[StepRecord]) -> str:
    if not history:
        return "(empty)"
    return "\n".join(_format_step(step) for step in history)


class LLMReasoner:
    """把 Agent 决策问题翻译成 ModelRequest，并把 ModelResponse 解析成 Decision。

    decision_protocol: "legacy_json"（默认，模型输出 JSON Decision 文本）或
    "native_tools"（native tool calling）。不做 provider-specific 分支。
    """

    def __init__(
        self, model_provider: ModelProvider, decision_protocol: str = "legacy_json"
    ) -> None:
        if decision_protocol not in ("legacy_json", "native_tools"):
            raise ValueError(f"unknown decision_protocol: {decision_protocol!r}")
        self._model_provider = model_provider
        self._decision_protocol = decision_protocol

    def decide(
        self,
        goal: Goal,
        state: State,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
    ) -> ReasoningResult:
        if self._decision_protocol == "native_tools":
            request = self._build_native_request(goal, history, capabilities)
            response = self._model_provider.request(request)
            decision = self._parse_native(response)
            assistant_message = self._native_assistant_message(response)
        else:
            request = self._build_request(goal, state, history, capabilities)
            response = self._model_provider.request(request)
            decision = self._parse(response)
            assistant_message = None

        model_call = ModelCallRecord(
            usage=response.usage,
            finish_reason=response.finish_reason,
            tool_calls=response.tool_calls,
            assistant_message=assistant_message,
        )
        return ReasoningResult(decision=decision, model_call=model_call)

    # -- 内部：构造请求 -----------------------------------------------------

    def _build_request(
        self,
        goal: Goal,
        state: State,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
    ) -> ModelRequest:
        user_content = self._build_user_content(goal, state, history, capabilities)
        return ModelRequest(
            messages=[
                Message(role="system", content=_SYSTEM_PROMPT),
                Message(role="user", content=user_content),
            ]
        )

    def _build_user_content(
        self,
        goal: Goal,
        state: State,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
    ) -> str:
        parts = [
            f"Goal: {goal.description}",
            f"State: {_render_json(state)}",
            "",
            "Available capabilities:",
        ]
        if capabilities:
            parts.extend(self._format_capability(cap) for cap in capabilities)
        else:
            parts.append("(none)")
        parts.extend(["", "History:", _format_history(history)])
        return "\n".join(parts)

    @staticmethod
    def _format_capability(cap: CapabilityDescriptor) -> str:
        return (
            f"- id: {cap.id}\n"
            f"  name: {cap.name}\n"
            f"  description: {cap.description}\n"
            f"  input_schema: {_render_json(cap.input_schema)}\n"
            f"  output_schema: {_render_json(cap.output_schema)}"
        )

    # -- 内部：native tool calling -------------------------------------------

    def _build_native_request(
        self,
        goal: Goal,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
    ) -> ModelRequest:
        tools = tuple(
            ModelToolDefinition(
                name=cap.id,
                description=cap.description,
                parameters=dict(cap.input_schema),
            )
            for cap in capabilities
        )
        messages = [
            Message(role="system", content=_NATIVE_SYSTEM_PROMPT),
            Message(role="user", content=goal.description),
        ]
        messages.extend(self._build_native_history_messages(history))
        tool_choice = "auto" if tools else None
        return ModelRequest(messages=messages, tools=tools, tool_choice=tool_choice)

    def _build_native_history_messages(self, history) -> list:
        messages = []
        for step in history:
            model_call = step.model_call
            if model_call is None or not model_call.tool_calls:
                continue
            assistant_message = model_call.assistant_message
            if assistant_message is not None:
                messages.append(assistant_message)
            else:
                messages.append(
                    Message(
                        role="assistant",
                        content=None,
                        tool_calls=tuple(model_call.tool_calls),
                    )
                )
            for call in model_call.tool_calls:
                messages.append(
                    Message(
                        role="tool",
                        content=self._tool_result_text(step),
                        tool_call_id=call.id,
                    )
                )
        return messages

    @staticmethod
    def _tool_result_text(step) -> str:
        if isinstance(step.policy_verdict, Deny):
            return f"Tool call denied by policy: {step.policy_verdict.reason}"
        if isinstance(step.observation, Failure):
            return f"Tool execution failed: {step.observation.error}"
        if isinstance(step.observation, Success):
            return _render_json(step.observation.data)
        return "null"

    @staticmethod
    def _native_assistant_message(response):
        if response.tool_calls:
            return Message(
                role="assistant",
                content=response.content,
                tool_calls=tuple(response.tool_calls),
            )
        return None

    def _parse_native(self, response: ModelResponse) -> Decision:
        tool_calls = response.tool_calls
        content = response.content
        finish_reason = response.finish_reason

        if len(tool_calls) > 1:
            raise DecisionParseError(
                "multiple tool calls unsupported in native-tools v0.1"
            )
        if len(tool_calls) == 1:
            if finish_reason not in (None, "tool_calls"):
                raise DecisionParseError(
                    f"single tool call requires finish_reason 'tool_calls' or None, "
                    f"got {finish_reason!r}"
                )
            call = tool_calls[0]
            try:
                parsed = json.loads(call.arguments)
            except json.JSONDecodeError as exc:
                raise DecisionParseError(
                    f"tool call arguments are not valid JSON: {exc}"
                ) from exc
            if not isinstance(parsed, dict):
                raise DecisionParseError("tool call arguments must be a JSON object")
            return Act(Action(call.name, parsed))

        # 0 tool calls
        if finish_reason == "tool_calls":
            raise DecisionParseError("finish_reason 'tool_calls' but no tool_calls")
        if content and content.strip():
            if finish_reason not in (None, "stop"):
                raise DecisionParseError(
                    f"final text requires finish_reason 'stop' or None, "
                    f"got {finish_reason!r}"
                )
            return Complete(reason=content)
        raise DecisionParseError("empty model response (no content and no tool calls)")

    # -- 内部：解析与校验（legacy JSON） ----------------------------------------

    def _parse(self, response: ModelResponse) -> Decision:
        # finish_reason 语义在 parse JSON 之前先 fail-closed。
        # 只有 None（provider 未暴露 finish_reason，见 ARCHITECTURE）或 "stop"
        # 才是可解析为 legacy Decision 的成功终止；length/content_filter/tool_calls/
        # insufficient_system_resource/未知值一律按协议失败处理，绝不把截断前缀当 Complete。
        finish_reason = response.finish_reason
        if finish_reason not in (None, "stop"):
            raise DecisionParseError(
                f"legacy JSON protocol requires finish_reason 'stop' or None, "
                f"got {finish_reason!r}"
            )
        if not isinstance(response.content, str):
            raise DecisionParseError(
                f"legacy JSON protocol requires string content, "
                f"got {type(response.content).__name__}"
            )
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise DecisionParseError(f"model returned non-JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise DecisionParseError(
                f"expected a JSON object, got {type(data).__name__}"
            )

        kind = data.get("kind")

        if kind == "act":
            capability_id = data.get("capability_id")
            if not isinstance(capability_id, str) or not capability_id:
                raise DecisionParseError(
                    "act decision requires a non-empty string 'capability_id'"
                )
            parameters = data.get("parameters", {})
            if not isinstance(parameters, dict):
                raise DecisionParseError(
                    "act decision 'parameters' must be a JSON object"
                )
            return Act(Action(capability_id, parameters))

        if kind == "complete":
            reason = data.get("reason")
            if reason is None:
                return Complete(reason=None)
            if isinstance(reason, str):
                return Complete(reason=reason)
            raise DecisionParseError(
                "complete decision 'reason' must be a string or null"
            )

        if kind == "fail":
            reason = data.get("reason")
            if not isinstance(reason, str):
                raise DecisionParseError("fail decision requires a string 'reason'")
            return Fail(reason)

        if kind == "blocked":
            reason = data.get("reason")
            if not isinstance(reason, str):
                raise DecisionParseError("blocked decision requires a string 'reason'")
            return Blocked(reason)

        raise DecisionParseError(f"unknown decision kind: {kind!r}")
