"""Host-side model input boundary for replaceable context strategies."""

import json
from dataclasses import asdict, dataclass, replace

from agent_runtime.contracts import Message, ModelRequest


SERVICE = "context.strategy"


@dataclass(frozen=True)
class Turn:
    run_id: str
    question: str
    answer: str


@dataclass(frozen=True)
class Projection:
    history: tuple[Message, ...] = ()
    recent_ids: tuple[str, ...] = ()
    checkpoint_ids: tuple[str, ...] = ()
    tool_prefixes: tuple[tuple[str, int], ...] = ()


def estimate(request: ModelRequest) -> int:
    """Conservative local proxy: one token per serialized UTF-8 byte, plus framing."""
    return len(json.dumps(asdict(request), ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 512


def apply_projection(request: ModelRequest, plan: Projection) -> ModelRequest:
    prefixes = dict(plan.tool_prefixes)
    if any(message.role not in ("user", "assistant") or message.tool_calls for message in plan.history):
        raise ValueError("invalid_context_history")
    tool_messages = {m.tool_call_id: m for m in request.messages if m.role == "tool"}
    if any(key not in tool_messages or type(size) is not int or size < 0 for key, size in prefixes.items()):
        raise ValueError("invalid_context_tool_excerpt")
    tail = [
        replace(message, content=message.content[:prefixes[message.tool_call_id]]
                + f"\n[Tool result excerpt; full result is in this run receipt: {message.tool_call_id}]")
        if message.role == "tool" and message.tool_call_id in prefixes
        and len(message.content) > prefixes[message.tool_call_id]
        else message
        for message in request.messages[1:]
    ]
    return replace(request, messages=(request.messages[0], *plan.history, *tail))


class ContextLimitExceeded(ValueError):
    """The Host did not dispatch the projected request."""


class BoundedProvider:
    def __init__(self, provider, strategy, turns, input_budget, max_requests=4, max_output_tokens=None):
        self.provider = provider
        self.strategy = strategy
        self.turns = tuple(turns)
        self.input_budget = input_budget
        self.max_requests = max_requests
        self.max_output_tokens = max_output_tokens
        self.attempts = 0
        self.calls = []

    def request(self, request):
        plan = (
            self.strategy.project(request, self.turns, self.input_budget)
            if self.strategy is not None else Projection()
        )
        all_ids = {turn.run_id for turn in self.turns}
        selected = {*plan.recent_ids, *plan.checkpoint_ids}
        if not selected <= all_ids or set(plan.recent_ids) & set(plan.checkpoint_ids):
            raise ValueError("invalid_context_sources")
        projected = apply_projection(request, plan)
        estimated = estimate(projected)
        blocked = (
            "BLOCKED_INPUT_LIMIT" if estimated > self.input_budget else
            "BLOCKED_REQUEST_LIMIT" if self.attempts >= self.max_requests else None
        )
        evidence = {
            "input_budget": self.input_budget,
            "estimated_input": estimated,
            "recent_run_ids": list(plan.recent_ids),
            "checkpoint_run_ids": list(plan.checkpoint_ids),
            "omitted_run_count": len(all_ids - selected),
            "excerpted_tool_call_ids": [
                m.tool_call_id for m, revised in zip(request.messages[1:], projected.messages[1 + len(plan.history):])
                if m.role == "tool" and m.content != revised.content
            ],
            "dispatch": blocked or "PROVIDER_ATTEMPT",
        }
        if plan.checkpoint_ids:
            evidence["checkpoint"] = plan.history[0].content
        self.calls.append(evidence)
        if blocked:
            raise ContextLimitExceeded("context_input_limit" if blocked == "BLOCKED_INPUT_LIMIT" else "model_request_limit")
        self.attempts += 1
        response = self.provider.request(projected)
        evidence["reported_usage"] = asdict(response.usage) if response.usage is not None else None
        if self.max_output_tokens is not None:
            if response.usage is None:
                raise ContextLimitExceeded("model_usage_missing")
            if response.usage.input_tokens > self.input_budget or response.usage.output_tokens > self.max_output_tokens:
                raise ContextLimitExceeded("model_usage_exceeded_limit")
        return response
