"""最小确定性测试替身，仅用于证明 Agent Loop 独立工作。

FakeReasoner          —— 确定性推理：先 add(20,22)，看到 42 后 Complete。
FakeCapability        —— add 能力：返回 a + b。
AllowAllPolicy        —— 始终放行、永不强制终止。
InMemoryStateStore    —— 最小内存快照存储。
ScriptedModelProvider —— 按预置顺序返回 ModelResponse 并记录收到的 ModelRequest。

不含真实模型、网络 I/O、任何领域逻辑。
"""

from __future__ import annotations

from typing import Sequence

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Continue,
    Goal,
    ModelRequest,
    ModelResponse,
    Observation,
    Parameters,
    PolicyVerdict,
    ReasoningResult,
    SessionSnapshot,
    State,
    StepRecord,
    Success,
    Termination,
)
from agent_runtime.snapshot import validate_session_snapshot


class FakeReasoner:
    """确定性推理：历史为空时调用 add(20, 22)；看到 42 后 Complete。"""

    def decide(
        self,
        goal: Goal,
        state: State,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
    ) -> ReasoningResult:
        if history:
            last = history[-1]
            if isinstance(last.observation, Success) and last.observation.data == 42:
                return ReasoningResult(decision=Complete(reason="得到 42"))
        return ReasoningResult(
            decision=Act(Action("add", {"a": 20, "b": 22}))
        )


class FakeCapability:
    """add 能力：把 a、b 相加。"""

    def describe(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="add",
            name="add",
            description="把两个数 a、b 相加并返回结果。",
            input_schema={
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
                "additionalProperties": False,
            },
            output_schema={"sum": "number"},
        )

    def invoke(self, parameters: Parameters) -> Observation:
        return Success(parameters["a"] + parameters["b"])


class AllowAllPolicy:
    """始终放行；永不强制终止。"""

    def check_action(self, action: Action, state: State) -> PolicyVerdict:
        return Allow()

    def should_stop(self, state: State, history: Sequence[StepRecord]) -> Termination:
        return Continue()


class InMemoryStateStore:
    """最小内存快照存储；commit/load 均做 ownership isolation。

    commit 时防御性深拷贝（validate_session_snapshot），load 时再次深拷贝，
    因此调用方改动已加载的快照不会污染存储，也不会反过来被存储污染。
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, SessionSnapshot] = {}

    def load(self, session_id: str) -> SessionSnapshot:
        return validate_session_snapshot(self._snapshots[session_id])

    def commit(self, snapshot: SessionSnapshot) -> None:
        self._snapshots[snapshot.session_id] = validate_session_snapshot(snapshot)


class ScriptedModelProvider:
    """按预置顺序返回 ModelResponse 的确定性 Provider，并记录收到的请求。

    responses 中每个元素可以是 str（作为 content）或完整 ModelResponse
    （可携带 usage / finish_reason）。
    """

    def __init__(self, responses: Sequence[str | ModelResponse]) -> None:
        self._responses = list(responses)
        self._cursor = 0
        self.requests: list[ModelRequest] = []

    def request(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self._cursor >= len(self._responses):
            raise RuntimeError("scripted responses exhausted")
        item = self._responses[self._cursor]
        self._cursor += 1
        if isinstance(item, ModelResponse):
            return item
        return ModelResponse(content=item)
