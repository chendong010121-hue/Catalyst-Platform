"""Native tools v2 deterministic stage tests (V2-001..V2-010).

V2-011 is the existing full v0.1 deterministic regression, run separately so
the frozen v0.1 test module remains untouched.
"""

from __future__ import annotations

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Continue,
    Deny,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelResponse,
    ModelToolCall,
    NativeToolsV2Call,
    NativeToolsV2Turn,
    SessionSnapshot,
    StepRecord,
    Success,
)
from agent_runtime.errors import CapabilityExecutionError, UnresolvedExecutionError
from agent_runtime.native_tools_v2 import (
    NativeToolsV2ProtocolError,
    NativeToolsV2Reasoner,
    NativeToolsV2Runtime,
)

from .fakes import InMemoryStateStore, ScriptedModelProvider


class CountingCapability:
    def __init__(self, capability_id: str, result=None):
        self.capability_id = capability_id
        self.result = result if result is not None else {"capability": capability_id}
        self.calls: list[dict] = []

    def describe(self):
        return CapabilityDescriptor(
            id=self.capability_id,
            name=self.capability_id,
            description=f"test capability {self.capability_id}",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        self.calls.append(dict(parameters))
        return Success(self.result)


class FailureCapability(CountingCapability):
    def invoke(self, parameters, context):
        self.calls.append(dict(parameters))
        return Failure("known capability failure")


class RaisingCapability(CountingCapability):
    def invoke(self, parameters, context):
        self.calls.append(dict(parameters))
        raise RuntimeError("uncertain capability outcome")


class AllowAllPolicy:
    def check_action(self, action, state):
        return Allow()

    def should_stop(self, state, history):
        return Continue()


class DenyOnePolicy(AllowAllPolicy):
    def __init__(self, denied_id: str):
        self.denied_id = denied_id

    def check_action(self, action, state):
        if action.capability_id == self.denied_id:
            return Deny("v2 test policy deny")
        return Allow()


def _tool(call_id: str, name: str, arguments: str = "{}") -> ModelToolCall:
    return ModelToolCall(call_id, name, arguments)


def _response(*calls: ModelToolCall) -> ModelResponse:
    return ModelResponse(content=None, tool_calls=calls, finish_reason="tool_calls")


def _runtime(provider, capabilities, policy=None, store=None):
    return NativeToolsV2Runtime(
        reasoner=NativeToolsV2Reasoner(provider),
        capabilities=capabilities,
        policy=policy or AllowAllPolicy(),
        state_store=store or InMemoryStateStore(),
    )


def _raised(expected_type, operation):
    try:
        operation()
    except expected_type as exc:
        return exc
    raise AssertionError(f"expected {expected_type.__name__}")


def test_v2_001_zero_tool_calls_final_answer():
    provider = ScriptedModelProvider([ModelResponse(content="final", finish_reason="stop")])
    runtime = _runtime(provider, {})

    final = runtime.start(Goal("answer without a tool"))

    assert isinstance(final.history[-1].decision, Complete)
    assert final.native_tools_v2_turns == ()


def test_v2_002_one_tool_call_reuses_execution_lifecycle():
    provider = ScriptedModelProvider(
        [_response(_tool("call-a", "a", '{"x":1}')), ModelResponse(content="done")]
    )
    capability = CountingCapability("a")

    final = _runtime(provider, {"a": capability}).start(Goal("run one tool"))

    assert capability.calls == [{"x": 1}]
    turn = final.native_tools_v2_turns[0]
    call = turn.calls[0]
    assert turn.status == "completed"
    assert call.tool_call_id == "call-a"
    assert call.execution_id
    assert isinstance(call.observation, Success)


def test_v2_003_two_tool_calls_execute_in_order_and_correlate_results():
    events = []
    provider = ScriptedModelProvider(
        [
            _response(_tool("call-a", "a"), _tool("call-b", "b")),
            ModelResponse(content="done"),
        ]
    )
    first = CountingCapability("a")
    second = CountingCapability("b")
    first.invoke = lambda parameters, context: (events.append("a"), first.calls.append(dict(parameters)), Success("A"))[2]
    second.invoke = lambda parameters, context: (events.append("b"), second.calls.append(dict(parameters)), Success("B"))[2]

    final = _runtime(provider, {"a": first, "b": second}).start(Goal("run two tools"))

    assert events == ["a", "b"]
    assert [call.tool_call_id for call in final.native_tools_v2_turns[0].calls] == ["call-a", "call-b"]
    messages = provider.requests[1].messages
    assistants = [message for message in messages if message.role == "assistant"]
    tools = [message for message in messages if message.role == "tool"]
    assert len(assistants) == 1
    assert [call.id for call in assistants[0].tool_calls] == ["call-a", "call-b"]
    assert [message.tool_call_id for message in tools] == ["call-a", "call-b"]


def test_v2_004_different_tools_keep_capability_and_arguments_correlated():
    provider = ScriptedModelProvider(
        [_response(_tool("call-a", "a", '{"value":1}'), _tool("call-b", "b", '{"value":2}')), ModelResponse(content="done")]
    )
    first = CountingCapability("a")
    second = CountingCapability("b")

    final = _runtime(provider, {"a": first, "b": second}).start(Goal("run different tools"))

    assert first.calls == [{"value": 1}]
    assert second.calls == [{"value": 2}]
    assert [call.action.capability_id for call in final.native_tools_v2_turns[0].calls] == ["a", "b"]


def test_v2_005_malformed_call_fails_closed_before_any_execution():
    provider = ScriptedModelProvider(
        [_response(_tool("call-a", "a", "{bad}"), _tool("call-b", "b"))]
    )
    first = CountingCapability("a")
    second = CountingCapability("b")
    runtime = _runtime(provider, {"a": first, "b": second})
    created = runtime.create(Goal("malformed batch"))

    exc = _raised(NativeToolsV2ProtocolError, lambda: runtime.run(created.session_id))

    assert first.calls == []
    assert second.calls == []
    assert exc.attribution.owner == "Harness native-tools v2 interaction"
    stored = runtime._state_store.load(created.session_id)
    assert stored.native_tools_v2_turns[0].status == "failed"


def test_v2_006_policy_deny_stops_later_siblings_only_as_v2_fail_closed_strategy():
    provider = ScriptedModelProvider([_response(_tool("call-a", "a"), _tool("call-b", "b"), _tool("call-c", "c"))])
    first = CountingCapability("a")
    denied = CountingCapability("b")
    later = CountingCapability("c")

    final = _runtime(
        provider,
        {"a": first, "b": denied, "c": later},
        policy=DenyOnePolicy("b"),
    ).start(Goal("policy batch"))

    turn = final.native_tools_v2_turns[0]
    assert first.calls == [{}]
    assert denied.calls == []
    assert later.calls == []
    assert [call.status for call in turn.calls] == ["settled", "denied", "skipped"]
    assert turn.failure_attribution.failure_type == "policy_denied_batch_halted"


def test_v2_007_known_capability_failure_is_not_infrastructure_uncertainty():
    provider = ScriptedModelProvider([_response(_tool("call-a", "a"), _tool("call-b", "b"))])
    failed = FailureCapability("a")
    later = CountingCapability("b")

    final = _runtime(provider, {"a": failed, "b": later}).start(Goal("known failure batch"))

    call = final.native_tools_v2_turns[0].calls[0]
    assert isinstance(call.observation, Failure)
    assert call.uncertainty is None
    assert later.calls == []


def test_v2_008_exception_leaves_existing_pending_uncertainty_semantics():
    provider = ScriptedModelProvider([_response(_tool("call-a", "a"), _tool("call-b", "b"))])
    raising = RaisingCapability("a")
    runtime = _runtime(provider, {"a": raising, "b": CountingCapability("b")})
    created = runtime.create(Goal("uncertain batch"))

    _raised(CapabilityExecutionError, lambda: runtime.run(created.session_id))

    stored = runtime._state_store.load(created.session_id)
    assert stored.pending_execution is not None
    assert stored.native_tools_v2_turns[0].calls[0].status == "pending"
    _raised(UnresolvedExecutionError, lambda: runtime.resume(created.session_id))


def test_v2_009_recovery_continues_unstarted_sibling_without_replaying_settled_call():
    provider = ScriptedModelProvider([ModelResponse(content="done")])
    first = CountingCapability("a")
    second = CountingCapability("b")
    runtime = _runtime(provider, {"a": first, "b": second})
    model_call = ModelCallRecord(
        finish_reason="tool_calls",
        tool_calls=(_tool("call-a", "a"), _tool("call-b", "b")),
        assistant_message=Message(
            role="assistant",
            content=None,
            tool_calls=(_tool("call-a", "a"), _tool("call-b", "b")),
        ),
    )
    batch = NativeToolsV2Turn(
        turn_id="turn-1",
        model_call=model_call,
        calls=(
            NativeToolsV2Call(
                tool_call_id="call-a",
                name="a",
                arguments="{}",
                action=Action("a", {}),
                status="settled",
                policy_verdict=Allow(),
                execution_id="exec-a",
                observation=Success("A"),
            ),
            NativeToolsV2Call(
                tool_call_id="call-b",
                name="b",
                arguments="{}",
                action=Action("b", {}),
            ),
        ),
        next_index=1,
        status="executing",
    )
    runtime._state_store.commit(
        SessionSnapshot(
            "recover",
            Goal("recover batch"),
            {},
            (StepRecord(0, Act(Action("a", {})), Allow(), Success("A"), execution_id="exec-a"),),
            native_tools_v2_turns=(batch,),
        )
    )

    final = runtime.resume("recover")

    assert first.calls == []
    assert second.calls == [{}]
    assert final.native_tools_v2_turns[0].status == "completed"


def test_v2_010_history_reconstructs_one_full_assistant_batch_and_results():
    provider = ScriptedModelProvider(
        [_response(_tool("call-a", "a"), _tool("call-b", "b")), ModelResponse(content="done")]
    )

    _runtime(provider, {"a": CountingCapability("a"), "b": CountingCapability("b")}).start(Goal("history"))

    messages = provider.requests[1].messages
    assistant = [message for message in messages if message.role == "assistant"]
    results = [message for message in messages if message.role == "tool"]
    assert len(assistant) == 1
    assert len(assistant[0].tool_calls) == 2
    assert [message.tool_call_id for message in results] == ["call-a", "call-b"]


def main() -> None:
    tests = [
        test_v2_001_zero_tool_calls_final_answer,
        test_v2_002_one_tool_call_reuses_execution_lifecycle,
        test_v2_003_two_tool_calls_execute_in_order_and_correlate_results,
        test_v2_004_different_tools_keep_capability_and_arguments_correlated,
        test_v2_005_malformed_call_fails_closed_before_any_execution,
        test_v2_006_policy_deny_stops_later_siblings_only_as_v2_fail_closed_strategy,
        test_v2_007_known_capability_failure_is_not_infrastructure_uncertainty,
        test_v2_008_exception_leaves_existing_pending_uncertainty_semantics,
        test_v2_009_recovery_continues_unstarted_sibling_without_replaying_settled_call,
        test_v2_010_history_reconstructs_one_full_assistant_batch_and_results,
    ]
    failed = []
    for test in tests:
        try:
            test()
            print(f"PASSED: {test.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed.append(test.__name__)
            print(f"FAILED: {test.__name__} -> {type(exc).__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print("ALL NATIVE TOOLS V2 TESTS PASSED")


if __name__ == "__main__":
    main()
