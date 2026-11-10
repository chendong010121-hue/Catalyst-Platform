from __future__ import annotations

import pytest

from agent_runtime.contracts import (
    Allow,
    CapabilityDescriptor,
    ConfirmedExecuted,
    Continue,
    Goal,
    ModelResponse,
    ModelToolCall,
    Success,
)
from agent_runtime.errors import CapabilityExecutionError
from agent_runtime.native_tools_v2 import (
    NativeToolsV2ProtocolError,
    NativeToolsV2Reasoner,
    NativeToolsV2Runtime,
)
from catalyst_platform.storage import JsonFileStateStore


class _FixedProvider:
    def __init__(self, response: ModelResponse):
        self.response = response

    def request(self, request):
        return self.response


def test_truncated_tool_call_response_is_rejected_before_a_turn_can_execute():
    reasoner = NativeToolsV2Reasoner(
        _FixedProvider(
            ModelResponse(
                tool_calls=(
                    ModelToolCall(id="partial-1", name="read", arguments="{}"),
                ),
                finish_reason="length",
            )
        )
    )

    with pytest.raises(NativeToolsV2ProtocolError) as caught:
        reasoner.decide_turn(Goal("read a source"), {}, (), (), ())

    assert caught.value.attribution.failure_type == "unsupported_model_turn_shape"
    assert caught.value.attribution.downstream_tool_execution_started is False
    assert caught.value.attribution.side_effect_certainty == "none"
    assert "finish_reason='length'" in caught.value.attribution.observed_fact


def test_unresolved_first_batch_action_skips_every_pending_sibling_after_reconcile(tmp_path):
    class BatchProvider:
        def __init__(self):
            self.responses = [
                ModelResponse(
                    tool_calls=(
                        ModelToolCall(id="batch-1", name="uncertain", arguments="{}"),
                        ModelToolCall(id="batch-2", name="sibling", arguments="{}"),
                    ),
                    finish_reason="tool_calls",
                ),
                ModelResponse(content="halted safely", finish_reason="stop"),
            ]

        def request(self, request):
            return self.responses.pop(0)

    class Uncertain:
        def describe(self):
            return CapabilityDescriptor(
                "uncertain", "Uncertain", "may have side effects", {"type": "object"}, {"type": "object"}
            )

        def invoke(self, parameters, context):
            raise RuntimeError("unknown effect")

    class Sibling:
        def __init__(self):
            self.calls = 0

        def describe(self):
            return CapabilityDescriptor("sibling", "Sibling", "must be skipped", {"type": "object"}, {"type": "object"})

        def invoke(self, parameters, context):
            self.calls += 1
            return Success({"called": True})

    class Policy:
        def check_action(self, action, state):
            return Allow()

        def should_stop(self, state, history):
            return Continue()

    provider = BatchProvider()
    sibling = Sibling()
    store = JsonFileStateStore(tmp_path / "sessions")
    runtime = NativeToolsV2Runtime(
        NativeToolsV2Reasoner(provider),
        {"uncertain": Uncertain(), "sibling": sibling},
        Policy(),
        store,
    )
    session_id = runtime.create(Goal("check sibling suppression")).session_id

    with pytest.raises(CapabilityExecutionError):
        runtime.run(session_id)
    pending_snapshot = store.load(session_id)
    assert pending_snapshot.pending_execution is not None
    assert sibling.calls == 0

    settled = runtime.reconcile(
        session_id,
        pending_snapshot.pending_execution.execution_id,
        ConfirmedExecuted(Success({"accepted": True}), note="local test fixture only"),
    )
    assert settled.pending_execution is None
    assert settled.native_tools_v2_turns[0].calls[1].status == "skipped"
    runtime.run(session_id)
    assert sibling.calls == 0
