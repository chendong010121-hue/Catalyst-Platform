"""Model Protocol & Session Consistency Hardening 测试。

覆盖：
- M：provider-neutral model value objects（ModelToolCall/ModelToolDefinition/Message/
     ModelResponse/ModelCallRecord）runtime fail-closed
- L：legacy finish_reason 语义（length/content_filter/... 绝不当作 Complete）
- C：ModelCallRecord tool-call canonical consistency（assistant_message 为 canonical）
- D：CapabilityDescriptor model-visible metadata + portable capability ID + registry key
- S：Session load/recovery structural consistency（validate_session_snapshot）
- R：ExecutionReconciliation 交叉字段语义
"""

from __future__ import annotations

import threading

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    Blocked,
    CapabilityDescriptor,
    Complete,
    ConfirmedNotExecuted,
    Deny,
    ExecutionReconciliation,
    Fail,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelResponse,
    ModelToolCall,
    ModelToolDefinition,
    ModelUsage,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Stop,
    Success,
    PendingExecution,
)
from agent_runtime.core import AgentCore
from agent_runtime.errors import (
    CapabilityRegistrationError,
    ReasonerContractError,
    SessionConsistencyError,
)
from agent_runtime.llm_reasoner import DecisionParseError, LLMReasoner
from agent_runtime.runtime import Runtime
from agent_runtime.snapshot import snapshot_model_call, validate_session_snapshot

from .fakes import AllowAllPolicy, FakeCapability, FakeReasoner, ScriptedModelProvider


# ---------------------------------------------------------------------------
# M：provider-neutral model value contract
# ---------------------------------------------------------------------------

def test_m1_invalid_tool_call_id():
    try:
        ModelToolCall(id=object(), name="add", arguments="{}")
    except ValueError:
        return
    raise AssertionError("ModelToolCall(id=object()) should raise ValueError")


def test_m2_invalid_tool_call_name():
    try:
        ModelToolCall(id="id", name=object(), arguments="{}")
    except ValueError:
        return
    raise AssertionError("ModelToolCall(name=object()) should raise ValueError")


def test_m3_invalid_tool_call_arguments():
    try:
        ModelToolCall(id="id", name="add", arguments=object())
    except ValueError:
        return
    raise AssertionError("ModelToolCall(arguments=object()) should raise ValueError")


def test_m4_invalid_message_tool_call_id():
    try:
        Message(role="tool", content="42", tool_call_id=123)
    except ValueError:
        return
    raise AssertionError("Message(tool_call_id=123) should raise ValueError")


def test_m5_invalid_message_tool_calls_element():
    try:
        Message(role="assistant", tool_calls=(123,))
    except ValueError:
        return
    raise AssertionError("Message(tool_calls=(123,)) should raise ValueError")


def test_m6_invalid_model_call_record_finish_reason():
    try:
        ModelCallRecord(finish_reason=object())
    except ValueError:
        return
    raise AssertionError("ModelCallRecord(finish_reason=object()) should raise ValueError")


def test_m7_invalid_model_call_record_usage():
    try:
        ModelCallRecord(usage=object())
    except ValueError:
        return
    raise AssertionError("ModelCallRecord(usage=object()) should raise ValueError")


def test_m8_invalid_model_response_nested():
    for make in [
        lambda: ModelResponse(usage=object()),
        lambda: ModelResponse(finish_reason=123),
        lambda: ModelResponse(tool_calls=(123,)),
        lambda: ModelResponse(content=123),
    ]:
        try:
            make()
        except ValueError:
            continue
        raise AssertionError("ModelResponse nested invalid should raise ValueError")


def test_m9_invalid_tool_definition():
    for make in [
        lambda: ModelToolDefinition(name=123, description="d", parameters={}),
        lambda: ModelToolDefinition(name="x", description=123, parameters={}),
        lambda: ModelToolDefinition(name="x", description="d", parameters={"k": threading.Lock()}),
        lambda: ModelToolDefinition(name="x", description="d", parameters=123),
    ]:
        try:
            make()
        except ValueError:
            continue
        raise AssertionError("ModelToolDefinition invalid should raise ValueError")


def test_m10_invalid_model_call_not_committed():
    class BadModelCallReasoner:
        def decide(self, goal, state, history, capabilities):
            return ReasoningResult(decision=Complete(reason="done"), model_call=threading.Lock())

    store = _RawStore(SessionSnapshot("s", Goal("x"), {}, ()))
    core = AgentCore(
        reasoner=BadModelCallReasoner(),
        capability_executor=DefaultCapabilityExecutor({}),
        policy=AllowAllPolicy(),
        state_store=store,
    )
    try:
        core.run("s")
    except ReasonerContractError:
        pass
    else:
        raise AssertionError("expected ReasonerContractError for invalid model_call")
    assert store.snapshot.history == ()  # 无 durable step 提交


# ---------------------------------------------------------------------------
# L：legacy finish_reason 语义
# ---------------------------------------------------------------------------

def _legacy_decide(finish_reason, content='{"kind":"complete","reason":"done"}'):
    provider = ScriptedModelProvider([ModelResponse(content=content, finish_reason=finish_reason)])
    return LLMReasoner(provider).decide(Goal("x"), {}, [], [])


def test_l1_legacy_stop_ok():
    assert isinstance(_legacy_decide("stop").decision, Complete)


def test_l2_legacy_none_ok():
    assert isinstance(_legacy_decide(None).decision, Complete)


def _legacy_fails(finish_reason):
    try:
        _legacy_decide(finish_reason)
    except DecisionParseError:
        return
    raise AssertionError(f"finish_reason={finish_reason!r} should raise DecisionParseError")


def test_l3_legacy_length_fails():
    _legacy_fails("length")


def test_l4_legacy_content_filter_fails():
    _legacy_fails("content_filter")


def test_l5_legacy_tool_calls_fails():
    _legacy_fails("tool_calls")


def test_l6_legacy_insufficient_system_resource_fails():
    _legacy_fails("insufficient_system_resource")


def test_l7_legacy_unknown_finish_reason_fails():
    _legacy_fails("some_unknown_reason")


def test_l8_legacy_non_str_finish_reason_fails_closed():
    try:
        ModelResponse(content='{"kind":"complete","reason":"done"}', finish_reason=123)
    except ValueError:
        return
    raise AssertionError("ModelResponse(finish_reason=123) should raise ValueError")


# ---------------------------------------------------------------------------
# C：ModelCallRecord tool-call canonical consistency
# ---------------------------------------------------------------------------

def _call(cid):
    return ModelToolCall(id=cid, name="add", arguments='{"a":20,"b":22}')


def test_c1_consistent_tool_calls_pass():
    call = _call("call_1")
    mc = ModelCallRecord(
        tool_calls=(call,),
        assistant_message=Message(role="assistant", content=None, tool_calls=(call,)),
    )
    snap = snapshot_model_call(mc)
    assert snap.tool_calls[0].id == "call_1"
    assert snap.assistant_message.tool_calls[0].id == "call_1"


def test_c2_contradictory_tool_calls_fail():
    try:
        ModelCallRecord(
            tool_calls=(_call("a"),),
            assistant_message=Message(
                role="assistant", content=None, tool_calls=(_call("b"),)
            ),
        )
    except ValueError:
        return
    raise AssertionError("contradictory tool_calls should raise ValueError")


def test_c3_legacy_tool_calls_without_assistant_message_pass():
    # assistant_message 为 None 时 tool_calls 是唯一 source，允许非空（legacy/历史重建路径）
    mc = ModelCallRecord(tool_calls=(_call("call_1"),))
    snap = snapshot_model_call(mc)
    assert snap.tool_calls[0].id == "call_1"
    assert snap.assistant_message is None


# ---------------------------------------------------------------------------
# D：CapabilityDescriptor model-visible metadata + portable ID
# ---------------------------------------------------------------------------

def _desc(id, name="n", description="d"):
    return CapabilityDescriptor(id=id, name=name, description=description)


def test_d1_non_string_id_fails():
    try:
        _desc(1)
    except ValueError:
        return
    raise AssertionError("CapabilityDescriptor(id=1) should raise ValueError")


def test_d2_empty_id_fails():
    try:
        _desc("")
    except ValueError:
        return
    raise AssertionError("CapabilityDescriptor(id='') should raise ValueError")


def test_d3_dotted_id_fails():
    try:
        _desc("bad.name")
    except ValueError:
        return
    raise AssertionError("CapabilityDescriptor(id='bad.name') should raise ValueError")


def test_d4_long_id_fails():
    try:
        _desc("a" * 65)
    except ValueError:
        return
    raise AssertionError("CapabilityDescriptor(id len 65) should raise ValueError")


def test_d5_non_string_name_fails():
    try:
        _desc("x", name=object())
    except ValueError:
        return
    raise AssertionError("CapabilityDescriptor(name=object()) should raise ValueError")


def test_d6_non_string_description_fails():
    try:
        _desc("x", description=object())
    except ValueError:
        return
    raise AssertionError("CapabilityDescriptor(description=object()) should raise ValueError")


def test_d7_portable_ids_pass():
    _desc("rhino-create-wall")
    _desc("search_code_v2")
    _desc("add")


def test_d8_registry_key_must_be_string():
    class Cap:
        def describe(self):
            return _desc("add")

        def invoke(self, parameters, context):
            return Success(None)

    try:
        DefaultCapabilityExecutor({1: Cap()})
    except CapabilityRegistrationError:
        return
    raise AssertionError("DefaultCapabilityExecutor({1: ...}) should raise CapabilityRegistrationError")


def test_d9_non_portable_descriptor_registration_fails():
    class DottedCap:
        def describe(self):
            return _desc("bad.name")

        def invoke(self, parameters, context):
            return Success(None)

    try:
        DefaultCapabilityExecutor({"bad.name": DottedCap()})
    except CapabilityRegistrationError:
        return
    raise AssertionError("non-portable descriptor id should raise CapabilityRegistrationError")


# ---------------------------------------------------------------------------
# S：Session load/recovery structural consistency
# ---------------------------------------------------------------------------

class _RawStore:
    """不校验、不拷贝的存储替身，用于模拟 future/损坏 persistent backend。"""

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.snapshot = snapshot


def _expect_consistency_error(snapshot):
    try:
        validate_session_snapshot(snapshot)
    except SessionConsistencyError:
        return
    raise AssertionError("expected SessionConsistencyError")


def test_s1_bad_session_id():
    _expect_consistency_error(SessionSnapshot("", Goal("x"), {}, ()))


def test_s2_history_index_mismatch():
    _expect_consistency_error(
        SessionSnapshot("s", Goal("x"), {}, (StepRecord(index=3, decision=Complete("done")),))
    )


def test_s3_invalid_decision():
    _expect_consistency_error(
        SessionSnapshot("s", Goal("x"), {}, (StepRecord(index=0, decision=123),))
    )


def test_s4_invalid_policy_verdict():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Act(Action("add", {})), policy_verdict="ALLOW"),),
        )
    )


def test_s5_invalid_termination():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Complete("done"), termination="STOP"),),
        )
    )


def test_s6_invalid_model_call():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Complete("done"), model_call=threading.Lock()),),
        )
    )


def test_s7_duplicate_settled_execution_id():
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
                ),
                StepRecord(
                    index=1,
                    decision=Act(Action("add", {})),
                    policy_verdict=Allow(),
                    observation=Success(2),
                    execution_id="e",
                ),
            ),
        )
    )


def test_s8_pending_step_index_mismatch():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (StepRecord(index=0, decision=Complete("done")),),
            pending_execution=PendingExecution("exec_1", 5, Action("add", {})),
        )
    )


def test_s9_pending_execution_id_duplicates_settled():
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
                    execution_id="exec_1",
                ),
            ),
            pending_execution=PendingExecution("exec_1", 1, Action("add", {})),
        )
    )


def test_s10_pending_malformed_action():
    _expect_consistency_error(
        SessionSnapshot(
            "s",
            Goal("x"),
            {},
            (),
            pending_execution=PendingExecution("exec_1", 0, Action(threading.Lock(), {})),
        )
    )


def test_s11_runtime_resume_validates_before_reasoner():
    class CountingReasoner:
        def __init__(self):
            self.decide_calls = 0

        def decide(self, goal, state, history, capabilities):
            self.decide_calls += 1
            return ReasoningResult(decision=Complete(reason="done"))

    malformed = SessionSnapshot(
        "s", Goal("x"), {}, (StepRecord(index=5, decision=Complete("done")),)
    )
    store = _RawStore(malformed)
    reasoner = CountingReasoner()
    rt = Runtime(reasoner, {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.resume("s")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError on resume")
    assert reasoner.decide_calls == 0  # Reasoner 未被调用


def test_s12_runtime_reconcile_validates_before_settlement():
    malformed = SessionSnapshot(
        "s",
        Goal("x"),
        {},
        (),
        pending_execution=PendingExecution("exec_1", 0, Action(threading.Lock(), {})),
    )
    store = _RawStore(malformed)
    rt = Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    before = store.snapshot
    try:
        rt.reconcile("s", "exec_1", ConfirmedNotExecuted())
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError on reconcile")
    assert store.snapshot.history == before.history  # history 未追加
    assert store.snapshot.pending_execution is not None  # pending 未清


# ---------------------------------------------------------------------------
# R：ExecutionReconciliation 交叉字段语义
# ---------------------------------------------------------------------------

def test_r1_confirmed_executed_requires_observation():
    try:
        ExecutionReconciliation("e", "confirmed_executed", observation=None)
    except ValueError:
        return
    raise AssertionError("confirmed_executed + None observation should raise ValueError")


def test_r2_confirmed_not_executed_rejects_success():
    try:
        ExecutionReconciliation("e", "confirmed_not_executed", observation=Success(1))
    except ValueError:
        return
    raise AssertionError("confirmed_not_executed + Success should raise ValueError")


def test_r3_valid_reconciliation_forms():
    ExecutionReconciliation("e", "confirmed_executed", observation=Success(1))
    ExecutionReconciliation("e", "confirmed_executed", observation=Failure("x"))
    ExecutionReconciliation("e", "confirmed_not_executed", observation=None)
    ExecutionReconciliation("e", "confirmed_not_executed", observation=Failure("x"))


def main() -> None:
    tests = [
        ("M1 invalid ModelToolCall.id", test_m1_invalid_tool_call_id),
        ("M2 invalid ModelToolCall.name", test_m2_invalid_tool_call_name),
        ("M3 invalid ModelToolCall.arguments", test_m3_invalid_tool_call_arguments),
        ("M4 invalid Message.tool_call_id", test_m4_invalid_message_tool_call_id),
        ("M5 invalid Message.tool_calls element", test_m5_invalid_message_tool_calls_element),
        ("M6 invalid ModelCallRecord.finish_reason", test_m6_invalid_model_call_record_finish_reason),
        ("M7 invalid ModelCallRecord.usage", test_m7_invalid_model_call_record_usage),
        ("M8 invalid ModelResponse nested", test_m8_invalid_model_response_nested),
        ("M9 invalid ModelToolDefinition", test_m9_invalid_tool_definition),
        ("M10 invalid model_call not committed", test_m10_invalid_model_call_not_committed),
        ("L1 legacy stop ok", test_l1_legacy_stop_ok),
        ("L2 legacy None ok", test_l2_legacy_none_ok),
        ("L3 legacy length fails", test_l3_legacy_length_fails),
        ("L4 legacy content_filter fails", test_l4_legacy_content_filter_fails),
        ("L5 legacy tool_calls fails", test_l5_legacy_tool_calls_fails),
        ("L6 legacy insufficient_system_resource fails", test_l6_legacy_insufficient_system_resource_fails),
        ("L7 legacy unknown finish_reason fails", test_l7_legacy_unknown_finish_reason_fails),
        ("L8 legacy non-str finish_reason fails", test_l8_legacy_non_str_finish_reason_fails_closed),
        ("C1 consistent tool_calls pass", test_c1_consistent_tool_calls_pass),
        ("C2 contradictory tool_calls fail", test_c2_contradictory_tool_calls_fail),
        ("C3 legacy tool_calls without assistant_message", test_c3_legacy_tool_calls_without_assistant_message_pass),
        ("D1 non-string id", test_d1_non_string_id_fails),
        ("D2 empty id", test_d2_empty_id_fails),
        ("D3 dotted id", test_d3_dotted_id_fails),
        ("D4 long id", test_d4_long_id_fails),
        ("D5 non-string name", test_d5_non_string_name_fails),
        ("D6 non-string description", test_d6_non_string_description_fails),
        ("D7 portable ids pass", test_d7_portable_ids_pass),
        ("D8 registry key must be string", test_d8_registry_key_must_be_string),
        ("D9 non-portable descriptor registration", test_d9_non_portable_descriptor_registration_fails),
        ("S1 bad session_id", test_s1_bad_session_id),
        ("S2 history index mismatch", test_s2_history_index_mismatch),
        ("S3 invalid decision", test_s3_invalid_decision),
        ("S4 invalid policy_verdict", test_s4_invalid_policy_verdict),
        ("S5 invalid termination", test_s5_invalid_termination),
        ("S6 invalid model_call", test_s6_invalid_model_call),
        ("S7 duplicate settled execution_id", test_s7_duplicate_settled_execution_id),
        ("S8 pending step_index mismatch", test_s8_pending_step_index_mismatch),
        ("S9 pending execution_id duplicates settled", test_s9_pending_execution_id_duplicates_settled),
        ("S10 pending malformed Action", test_s10_pending_malformed_action),
        ("S11 resume validates before Reasoner", test_s11_runtime_resume_validates_before_reasoner),
        ("S12 reconcile validates before settlement", test_s12_runtime_reconcile_validates_before_settlement),
        ("R1 confirmed_executed requires observation", test_r1_confirmed_executed_requires_observation),
        ("R2 confirmed_not_executed rejects Success", test_r2_confirmed_not_executed_rejects_success),
        ("R3 valid reconciliation forms", test_r3_valid_reconciliation_forms),
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
    print("\nALL MODEL/SESSION CONSISTENCY TESTS PASSED")


if __name__ == "__main__":
    main()
