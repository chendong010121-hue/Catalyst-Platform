"""Provider Envelope & Session Semantic Closure 测试。

覆盖（依据 PROVIDER_ENVELOPE_SESSION_SEMANTIC_CLOSURE.md）：
- P：DeepSeek non-stream concrete response envelope（role / finish_reason）fail-closed
- L：Core 每次 authoritative load 先 validate；commit 先 canonicalize（RawStore 证明）
- S：StepRecord cross-field semantic invariants + terminal ordering + corrupt payload
- R：Reconciliation duplicated Observation 一致性
- M：ModelRequest runtime contract + model sequence tuple isolation
"""

from __future__ import annotations

import threading

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    ConfirmedExecuted,
    ConfirmedNotExecuted,
    Deny,
    ExecutionReconciliation,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Stop,
    Success,
)
from agent_runtime.core import AgentCore
from agent_runtime.errors import ModelProviderError, SessionConsistencyError
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from agent_runtime.runtime import Runtime
from agent_runtime.snapshot import validate_session_snapshot

from .fakes import AllowAllPolicy, FakeCapability, InMemoryStateStore


# ---------------------------------------------------------------------------
# P：DeepSeek concrete response envelope
# ---------------------------------------------------------------------------

def _ds_provider(response):
    return DeepSeekModelProvider(api_key="k", transport=lambda u, h, b: (200, response))


def _expect_provider_error(response):
    provider = _ds_provider(response)
    try:
        provider.request(ModelRequest(messages=[Message(role="user", content="hi")]))
    except ModelProviderError:
        return
    raise AssertionError(f"expected ModelProviderError for {response!r}")


class CountingAddCapability:
    def __init__(self):
        self.call_count = 0

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="adds")

    def invoke(self, parameters, context):
        self.call_count += 1
        return Success(42)


def test_p1_missing_finish_reason_no_side_effect():
    cap = CountingAddCapability()
    provider = _ds_provider(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {"name": "add", "arguments": '{"a":20,"b":22}'},
                            }
                        ],
                    }
                    # finish_reason missing
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    )
    rt = Runtime(LLMReasoner(provider, decision_protocol="native_tools"), {"add": cap}, AllowAllPolicy(), state_store=InMemoryStateStore())
    snap = rt.create(Goal("x"))
    try:
        rt.run(snap.session_id)
    except ModelProviderError:
        pass
    else:
        raise AssertionError("expected ModelProviderError for missing finish_reason")
    assert cap.call_count == 0  # capability 未执行


def test_p2_null_finish_reason():
    _expect_provider_error(
        {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": None}]}
    )


def test_p3_non_string_finish_reason():
    _expect_provider_error(
        {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": 123}]}
    )


def test_p4_unknown_finish_reason():
    _expect_provider_error(
        {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "unknown"}]}
    )


def test_p5_missing_message_role():
    _expect_provider_error(
        {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
    )


def test_p6_wrong_message_role():
    _expect_provider_error(
        {"choices": [{"message": {"role": "user", "content": "ok"}, "finish_reason": "stop"}]}
    )


def test_p7_valid_envelope_regression():
    # Provider mapping 层：这些 vendor finish_reason 都合法（Reasoner 层再决定语义）
    for fr in ("stop", "length", "content_filter", "tool_calls", "insufficient_system_resource"):
        provider = _ds_provider(
            {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": fr}]}
        )
        result = provider.request(ModelRequest(messages=[Message(role="user", content="hi")]))
        assert result.finish_reason == fr


# ---------------------------------------------------------------------------
# L：Core authoritative load/commit boundary
# ---------------------------------------------------------------------------

class _RawStore:
    """只按原样保存/返回，不做任何 validate/copy。"""

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.snapshot = snapshot


class _SecondLoadMalformedStore:
    """load #1 valid，load #2 malformed。"""

    def __init__(self):
        self.load_count = 0
        self._valid = SessionSnapshot("s", Goal("x"), {}, ())
        self._malformed = SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict="ALLOW",  # raw string
                ),
            ),
        )

    def load(self, session_id):
        self.load_count += 1
        return self._valid if self.load_count == 1 else self._malformed

    def commit(self, snapshot):
        pass


class CountingReasoner:
    def __init__(self):
        self.decide_calls = 0

    def decide(self, goal, state, history, capabilities):
        self.decide_calls += 1
        return ReasoningResult(decision=Complete(reason="done"))


def test_l1_second_load_malformed_validated():
    store = _SecondLoadMalformedStore()
    reasoner = CountingReasoner()
    rt = Runtime(reasoner, {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.run("s")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError on second malformed load")
    assert reasoner.decide_calls == 0  # Reasoner 未被调用


class CorruptUsageReasoner:
    def decide(self, goal, state, history, capabilities):
        usage = ModelUsage(10, 5)
        # 模拟 deserialized/corrupt frozen dataclass：绕过 __post_init__ 注入非法 budget fact
        object.__setattr__(usage, "input_tokens", -100)
        mc = ModelCallRecord(usage=usage)
        return ReasoningResult(decision=Complete(reason="done"), model_call=mc)


def test_l2_core_commit_rejects_malformed_on_raw_store():
    store = _RawStore(SessionSnapshot("s", Goal("x"), {}, ()))
    core = AgentCore(
        reasoner=CorruptUsageReasoner(),
        capability_executor=DefaultCapabilityExecutor({}),
        policy=AllowAllPolicy(),
        state_store=store,
    )
    try:
        core.run("s")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError at Core commit boundary")
    assert store.snapshot.history == ()  # Raw Store 未收到 malformed snapshot


# ---------------------------------------------------------------------------
# S：StepRecord cross-field semantic consistency
# ---------------------------------------------------------------------------

def _expect_consistency_error(snapshot):
    try:
        validate_session_snapshot(snapshot)
    except SessionConsistencyError:
        return
    raise AssertionError("expected SessionConsistencyError")


def test_s1_act_allow_no_observation():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    execution_id="e",
                ),
            ),
        )
    )


def test_s2_act_allow_no_execution_id():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                ),
            ),
        )
    )


def test_s3_act_deny_with_observation():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Deny("nope"),
                    observation=Failure("x"),
                ),
            ),
        )
    )


def test_s4_act_deny_with_execution_id():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Deny("nope"),
                    execution_id="e",
                ),
            ),
        )
    )


def test_s5_complete_with_observation():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Complete("done"), observation=Success(1)),),
        )
    )


def test_s6_complete_with_execution_id():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Complete("done"), execution_id="e"),),
        )
    )


def test_s7_terminal_in_middle():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(index=0, decision=Complete("done")),
                StepRecord(
                    index=1,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                    execution_id="e",
                ),
            ),
        )
    )


def test_s8_stop_followed_by_later_history():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                    execution_id="e1",
                    termination=Stop("stop"),
                ),
                StepRecord(
                    index=1,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(2),
                    execution_id="e2",
                ),
            ),
        )
    )


def test_s9_malformed_native_settled_step():
    # Act+Allow + native model_call，但 observation=None → 绝不能生成 tool result "null"
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    model_call=ModelCallRecord(
                        tool_calls=(ModelToolCall("c1", "add", "{}"),)
                    ),
                    observation=None,
                ),
            ),
        )
    )


def test_s10_corrupted_deny_reason():
    deny = Deny("x")
    object.__setattr__(deny, "reason", threading.Lock())
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Act(Action("add", {})), policy_verdict=deny),),
        )
    )


def test_s11_corrupted_stop_reason():
    stop = Stop("x")
    object.__setattr__(stop, "reason", threading.Lock())
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                    execution_id="e",
                    termination=stop,
                ),
            ),
        )
    )


# ---------------------------------------------------------------------------
# R：Reconciliation duplicated Observation 一致性
# ---------------------------------------------------------------------------

def test_r1_confirmed_executed_observation_mismatch():
    recon = ExecutionReconciliation("e", "confirmed_executed", observation=Success(2))
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                    execution_id="e",
                    reconciliation=recon,
                ),
            ),
        )
    )


def test_r2_confirmed_not_executed_with_success():
    recon = ExecutionReconciliation("e", "confirmed_not_executed", observation=Failure("not run"))
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                    execution_id="e",
                    reconciliation=recon,
                ),
            ),
        )
    )


def test_r3_valid_reconciliation_forms_pass():
    recon_exec = ExecutionReconciliation("e", "confirmed_executed", observation=Success(1))
    validate_session_snapshot(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(1),
                    execution_id="e",
                    reconciliation=recon_exec,
                ),
            ),
        )
    )
    deterministic_failure = Failure(
        "execution reconciliation confirmed: capability did not execute"
    )
    recon_not = ExecutionReconciliation(
        "e", "confirmed_not_executed", observation=deterministic_failure
    )
    validate_session_snapshot(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (
                StepRecord(
                    index=0,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=deterministic_failure,
                    execution_id="e",
                    reconciliation=recon_not,
                ),
            ),
        )
    )


# ---------------------------------------------------------------------------
# M：ModelRequest runtime contract + sequence tuple isolation
# ---------------------------------------------------------------------------

def test_m1_invalid_modelrequest_messages():
    try:
        ModelRequest(messages=[123])
    except ValueError:
        return
    raise AssertionError("ModelRequest(messages=[123]) should raise ValueError")


def test_m2_invalid_modelrequest_tools():
    try:
        ModelRequest(messages=[Message(role="user", content="hi")], tools=[123])
    except ValueError:
        return
    raise AssertionError("ModelRequest(tools=[123]) should raise ValueError")


def test_m3_sequence_tuple_isolation():
    # ModelResponse
    calls = [ModelToolCall("a", "add", "{}")]
    resp = ModelResponse(tool_calls=calls)
    calls.append(ModelToolCall("b", "add", "{}"))
    assert isinstance(resp.tool_calls, tuple) and len(resp.tool_calls) == 1

    # Message
    calls2 = [ModelToolCall("a", "add", "{}")]
    msg = Message(role="assistant", content=None, tool_calls=calls2)
    calls2.append(ModelToolCall("b", "add", "{}"))
    assert isinstance(msg.tool_calls, tuple) and len(msg.tool_calls) == 1

    # ModelCallRecord
    calls3 = [ModelToolCall("a", "add", "{}")]
    mc = ModelCallRecord(tool_calls=calls3)
    calls3.append(ModelToolCall("b", "add", "{}"))
    assert isinstance(mc.tool_calls, tuple) and len(mc.tool_calls) == 1

    # ModelRequest
    msgs = [Message(role="user", content="hi")]
    req = ModelRequest(messages=msgs)
    msgs.append(Message(role="user", content="bye"))
    assert isinstance(req.messages, tuple) and len(req.messages) == 1


def main() -> None:
    tests = [
        ("P1 missing finish_reason no side effect", test_p1_missing_finish_reason_no_side_effect),
        ("P2 null finish_reason", test_p2_null_finish_reason),
        ("P3 non-string finish_reason", test_p3_non_string_finish_reason),
        ("P4 unknown finish_reason", test_p4_unknown_finish_reason),
        ("P5 missing message.role", test_p5_missing_message_role),
        ("P6 wrong message.role", test_p6_wrong_message_role),
        ("P7 valid envelope regression", test_p7_valid_envelope_regression),
        ("L1 second-load malformed validated", test_l1_second_load_malformed_validated),
        ("L2 Core commit rejects malformed on raw store", test_l2_core_commit_rejects_malformed_on_raw_store),
        ("S1 Act+Allow no observation", test_s1_act_allow_no_observation),
        ("S2 Act+Allow no execution_id", test_s2_act_allow_no_execution_id),
        ("S3 Act+Deny with observation", test_s3_act_deny_with_observation),
        ("S4 Act+Deny with execution_id", test_s4_act_deny_with_execution_id),
        ("S5 Complete with observation", test_s5_complete_with_observation),
        ("S6 Complete with execution_id", test_s6_complete_with_execution_id),
        ("S7 terminal in middle", test_s7_terminal_in_middle),
        ("S8 Stop followed by later history", test_s8_stop_followed_by_later_history),
        ("S9 malformed native settled step", test_s9_malformed_native_settled_step),
        ("S10 corrupted Deny.reason", test_s10_corrupted_deny_reason),
        ("S11 corrupted Stop.reason", test_s11_corrupted_stop_reason),
        ("R1 confirmed_executed observation mismatch", test_r1_confirmed_executed_observation_mismatch),
        ("R2 confirmed_not_executed with Success", test_r2_confirmed_not_executed_with_success),
        ("R3 valid reconciliation forms pass", test_r3_valid_reconciliation_forms_pass),
        ("M1 invalid ModelRequest messages", test_m1_invalid_modelrequest_messages),
        ("M2 invalid ModelRequest tools", test_m2_invalid_modelrequest_tools),
        ("M3 sequence tuple isolation", test_m3_sequence_tuple_isolation),
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
    print("\nALL PROVIDER/SESSION CLOSURE TESTS PASSED")


if __name__ == "__main__":
    main()
