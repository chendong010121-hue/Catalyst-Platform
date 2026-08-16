"""Native Tool Calling v0.1 测试：contract / reasoner / structured history / e2e。"""

from __future__ import annotations

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Deny,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
    SessionSnapshot,
    StepRecord,
    Success,
)
from agent_runtime.llm_reasoner import DecisionParseError, LLMReasoner
from agent_runtime.runtime import Runtime
from agent_runtime.snapshot import snapshot_model_call

from .fakes import AllowAllPolicy, FakeCapability, InMemoryStateStore, ScriptedModelProvider


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_a_modeltoolcall_durable_snapshot():
    call = ModelToolCall(id="call_1", name="add", arguments='{"a":20,"b":22}')
    mc = ModelCallRecord(
        usage=ModelUsage(10, 5), finish_reason="tool_calls", tool_calls=(call,)
    )
    snap = snapshot_model_call(mc)
    assert snap.tool_calls[0].id == "call_1"
    assert snap.tool_calls[0].name == "add"
    assert snap.tool_calls[0].arguments == '{"a":20,"b":22}'
    assert snap.tool_calls[0] is not call  # 独立对象


def test_b_message_invariants():
    # 合法
    Message(role="assistant", content="hi")
    Message(role="assistant", content=None, tool_calls=(ModelToolCall("c", "f", "{}"),))
    Message(role="tool", content="42", tool_call_id="c")

    # 非法组合 fail-fast
    invalid = [
        lambda: Message(role="user", content="hi", tool_call_id="c"),
        lambda: Message(
            role="tool", content="42", tool_call_id="c",
            tool_calls=(ModelToolCall("x", "f", "{}"),),
        ),
        lambda: Message(role="tool", content="42"),  # tool_call_id=None
        lambda: Message(role="user", content=123),  # 非 str content
        lambda: Message(
            role="system", content="sys", tool_calls=(ModelToolCall("x", "f", "{}"),)
        ),
        lambda: Message(role="tool", content=123, tool_call_id="c"),  # tool 非 str content
        lambda: Message(role="assistant", content=None),  # 空 assistant（无 content 无 tool_calls）
        lambda: Message(role="assistant", content="hi", tool_call_id="c"),
    ]
    for make in invalid:
        try:
            make()
        except ValueError:
            continue
        raise AssertionError("expected ValueError for invalid message")


def test_c_modelresponse_toolcall():
    resp = ModelResponse(content=None, tool_calls=(ModelToolCall("c", "f", "{}"),))
    assert resp.content is None
    assert len(resp.tool_calls) == 1


# ---------------------------------------------------------------------------
# LLMReasoner native tests
# ---------------------------------------------------------------------------

def _native(provider):
    return LLMReasoner(provider, decision_protocol="native_tools")


def test_1_tools_visible():
    provider = ScriptedModelProvider([ModelResponse(content="done")])
    reasoner = _native(provider)
    cap = CapabilityDescriptor(
        id="add",
        name="add",
        description="adds two ints",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    )
    reasoner.decide(Goal("x"), {}, [], [cap])

    req = provider.requests[0]
    assert len(req.tools) == 1
    tool = req.tools[0]
    assert tool.name == "add"
    assert tool.description == "adds two ints"
    assert tool.parameters["properties"]["a"]["type"] == "integer"


def test_2_single_tool_call_to_act():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_1", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            )
        ]
    )
    result = _native(provider).decide(Goal("x"), {}, [], [])

    assert isinstance(result.decision, Act)
    assert result.decision.action.capability_id == "add"
    assert result.decision.action.parameters == {"a": 20, "b": 22}
    assert result.model_call.tool_calls[0].id == "call_1"
    assert result.model_call.tool_calls[0].arguments == '{"a":20,"b":22}'


def test_3_final_text_to_complete():
    provider = ScriptedModelProvider([ModelResponse(content="The result is 42.")])
    result = _native(provider).decide(Goal("x"), {}, [], [])
    assert isinstance(result.decision, Complete)
    assert result.decision.reason == "The result is 42."


def test_4_malformed_arguments():
    provider = ScriptedModelProvider(
        [ModelResponse(content=None, tool_calls=(ModelToolCall("c", "add", "{a:20}"),))]
    )
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for malformed arguments")


def test_5_arguments_root_not_object():
    provider = ScriptedModelProvider(
        [ModelResponse(content=None, tool_calls=(ModelToolCall("c", "add", "[20,22]"),))]
    )
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for non-object arguments")


def test_6_multiple_calls():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(
                    ModelToolCall("c1", "f", "{}"),
                    ModelToolCall("c2", "f", "{}"),
                ),
            )
        ]
    )
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for multiple tool calls")


def test_7_empty_response():
    provider = ScriptedModelProvider([ModelResponse(content=None)])
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for empty response")


# ---------------------------------------------------------------------------
# Structured history tests
# ---------------------------------------------------------------------------

def _tool_msgs(provider):
    return [m for m in provider.requests[0].messages if m.role == "tool"]


def test_8_success_history():
    provider = ScriptedModelProvider([ModelResponse(content="done")])
    step = StepRecord(
        index=0,
        decision=Act(Action("add", {"a": 20, "b": 22})),
        policy_verdict=Allow(),
        observation=Success(42),
        model_call=ModelCallRecord(
            tool_calls=(ModelToolCall("call_1", "add", '{"a":20,"b":22}'),)
        ),
    )
    _native(provider).decide(Goal("compute"), {}, [step], [])

    assistant = [m for m in provider.requests[0].messages if m.role == "assistant"]
    tool = _tool_msgs(provider)
    assert len(assistant) == 1
    assert assistant[0].tool_calls[0].id == "call_1"
    assert len(tool) == 1
    assert tool[0].tool_call_id == "call_1"
    assert tool[0].content == "42"


def test_9_policy_deny_history():
    provider = ScriptedModelProvider([ModelResponse(content="done")])
    step = StepRecord(
        index=0,
        decision=Act(Action("write_file", {"path": "/etc/passwd"})),
        policy_verdict=Deny("outside workspace"),
        observation=None,
        model_call=ModelCallRecord(
            tool_calls=(ModelToolCall("call_1", "write_file", '{"path":"/etc/passwd"}'),)
        ),
    )
    _native(provider).decide(Goal("x"), {}, [step], [])

    tool = _tool_msgs(provider)
    assert len(tool) == 1
    assert tool[0].tool_call_id == "call_1"
    assert "outside workspace" in tool[0].content


def test_10_executor_failure_history():
    provider = ScriptedModelProvider([ModelResponse(content="done")])
    step = StepRecord(
        index=0,
        decision=Act(Action("boom", {})),
        policy_verdict=Allow(),
        observation=Failure("RuntimeError: boom"),
        model_call=ModelCallRecord(tool_calls=(ModelToolCall("call_1", "boom", "{}"),)),
    )
    _native(provider).decide(Goal("x"), {}, [step], [])

    tool = _tool_msgs(provider)
    assert len(tool) == 1
    assert tool[0].tool_call_id == "call_1"
    assert "Tool execution failed" in tool[0].content


def test_11_resume_safe():
    store = InMemoryStateStore()
    step0 = StepRecord(
        index=0,
        decision=Act(Action("add", {"a": 20, "b": 22})),
        policy_verdict=Allow(),
        observation=Success(42),
        model_call=ModelCallRecord(
            tool_calls=(ModelToolCall("call_1", "add", '{"a":20,"b":22}'),)
        ),
        execution_id="exec_0",
    )
    store.commit(SessionSnapshot("s-native", Goal("compute"), {}, (step0,)))

    # 新 Runtime + 新 Reasoner，从持久 history resume
    provider2 = ScriptedModelProvider([ModelResponse(content="done")])
    rt2 = Runtime(_native(provider2), {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    final = rt2.resume("s-native")

    tool = _tool_msgs(provider2)
    assert len(tool) == 1
    assert tool[0].tool_call_id == "call_1"  # 从持久 model_call 恢复，非临时内存
    assert tool[0].content == "42"
    assert isinstance(final.history[-1].decision, Complete)


# ---------------------------------------------------------------------------
# End-to-end offline native test
# ---------------------------------------------------------------------------

def test_e2e_native_offline():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_1", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            ),
            ModelResponse(content="The result is 42."),
        ]
    )
    rt = Runtime(_native(provider), {"add": FakeCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())
    final = rt.start(Goal("compute 20 + 22"))

    assert len(final.history) == 2
    step0 = final.history[0]
    assert isinstance(step0.decision, Act)
    assert isinstance(step0.observation, Success) and step0.observation.data == 42
    assert step0.model_call.tool_calls[0].id == "call_1"
    assert isinstance(final.history[1].decision, Complete)


# ---------------------------------------------------------------------------
# finish_reason + assistant content lossless
# ---------------------------------------------------------------------------

def test_finish_reason_tool_call_ok():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("c", "add", '{"a":1}'),),
                finish_reason="tool_calls",
            )
        ]
    )
    assert isinstance(_native(provider).decide(Goal("x"), {}, [], []).decision, Act)


def test_finish_reason_tool_call_none_ok():
    provider = ScriptedModelProvider(
        [ModelResponse(content=None, tool_calls=(ModelToolCall("c", "add", '{"a":1}'),))]
    )
    assert isinstance(_native(provider).decide(Goal("x"), {}, [], []).decision, Act)


def test_finish_reason_tool_call_wrong():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("c", "add", '{"a":1}'),),
                finish_reason="stop",
            )
        ]
    )
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for single tool call + finish_reason 'stop'")


def test_finish_reason_final_text_stop_ok():
    provider = ScriptedModelProvider([ModelResponse(content="done", finish_reason="stop")])
    assert isinstance(_native(provider).decide(Goal("x"), {}, [], []).decision, Complete)


def test_finish_reason_final_text_length_fails():
    provider = ScriptedModelProvider([ModelResponse(content="done", finish_reason="length")])
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for final text + finish_reason 'length'")


def test_finish_reason_tool_calls_no_calls():
    provider = ScriptedModelProvider([ModelResponse(content=None, finish_reason="tool_calls")])
    try:
        _native(provider).decide(Goal("x"), {}, [], [])
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for finish_reason 'tool_calls' without tool_calls")


def test_assistant_content_lossless():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content="I will calculate",
                tool_calls=(ModelToolCall("call_1", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            ),
            ModelResponse(content="done", finish_reason="stop"),
        ]
    )
    rt = Runtime(_native(provider), {"add": FakeCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())
    final = rt.start(Goal("compute"))

    assert len(final.history) == 2
    step0 = final.history[0]
    assert step0.model_call.assistant_message is not None
    assert step0.model_call.assistant_message.content == "I will calculate"

    assistant = [m for m in provider.requests[1].messages if m.role == "assistant"]
    assert len(assistant) == 1
    assert assistant[0].content == "I will calculate"
    assert assistant[0].tool_calls[0].id == "call_1"
    assert isinstance(final.history[1].decision, Complete)


def main() -> None:
    tests = [
        ("A ModelToolCall durable snapshot", test_a_modeltoolcall_durable_snapshot),
        ("B Message invariants", test_b_message_invariants),
        ("C ModelResponse tool_calls", test_c_modelresponse_toolcall),
        ("1 tools visible", test_1_tools_visible),
        ("2 single tool call → Act", test_2_single_tool_call_to_act),
        ("3 final text → Complete", test_3_final_text_to_complete),
        ("4 malformed arguments", test_4_malformed_arguments),
        ("5 arguments root not object", test_5_arguments_root_not_object),
        ("6 multiple calls", test_6_multiple_calls),
        ("7 empty response", test_7_empty_response),
        ("8 success history", test_8_success_history),
        ("9 policy deny history", test_9_policy_deny_history),
        ("10 executor failure history", test_10_executor_failure_history),
        ("11 resume safe", test_11_resume_safe),
        ("e2e native offline", test_e2e_native_offline),
        ("finish_reason tool_call ok", test_finish_reason_tool_call_ok),
        ("finish_reason tool_call None ok", test_finish_reason_tool_call_none_ok),
        ("finish_reason tool_call wrong", test_finish_reason_tool_call_wrong),
        ("finish_reason final text stop ok", test_finish_reason_final_text_stop_ok),
        ("finish_reason final text length fails", test_finish_reason_final_text_length_fails),
        ("finish_reason tool_calls without calls", test_finish_reason_tool_calls_no_calls),
        ("assistant content lossless", test_assistant_content_lossless),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except AssertionError as exc:
            failed.append(name)
            print(f"FAILED: {name} -> {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"ERROR : {name} -> {type(exc).__name__}: {exc}")

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        raise SystemExit(1)
    print("\nALL NATIVE TOOL REASONER TESTS PASSED")


if __name__ == "__main__":
    main()
