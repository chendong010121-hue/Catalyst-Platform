"""An answer the output window cut is refused as a cut, and carries the text it reached.

One live card lost two slides this way: the model wrote nineteen and twenty-one thousand
characters, the window closed, and the budget layer refused the answer as malformed JSON.
The rows the model finished are whole rows, so the refusal has to say "cut" and hand the
text on; the port already knows how to keep what closed.
"""
from __future__ import annotations

import json

import pytest

from agent_runtime.contracts import Message, ModelRequest, ModelResponse, ModelUsage
from catalyst_platform.llm_controls import ModelControlError, TaskBudget
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

from tests.test_api_infrastructure_p0 import task


def _request():
    return ModelRequest(
        messages=(Message(role="user", content="读这一页"),),
        parameters={"max_tokens": 512, "response_format": {"type": "json_object"}})


def _response(content, finish_reason):
    return ModelResponse(content=content, finish_reason=finish_reason,
                         usage=ModelUsage(input_tokens=100, output_tokens=40,
                                          cache_hit_input_tokens=0,
                                          cache_miss_input_tokens=100))


def test_a_cut_answer_is_not_reported_as_malformed_json():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    cut = '{"items": [{"kind": "entity", "key": "a", "meaning": "财务部"'
    with pytest.raises(ModelControlError) as caught:
        budget.finish(_response(cut, "length"), prepared)
    assert caught.value.public_code == "llm_output_truncated"
    # The text the model reached travels with the refusal, so the rows that closed are kept.
    assert caught.value.partial == cut
    # The request was paid for: the meter is settled, not uncertain.
    assert budget.settled is True and budget.uncertain is False
    assert budget.status == "invalid_structured_output"


def test_a_malformed_answer_still_says_malformed():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    with pytest.raises(ModelControlError) as caught:
        budget.finish(_response("这不是 JSON", "stop"), prepared)
    assert caught.value.public_code == "llm_structured_output_invalid"


def test_a_complete_answer_is_metered_without_an_error():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    budget.finish(_response(json.dumps({"items": []}), "stop"), prepared)
    assert budget.status == "metered"
    assert budget.settled is True and budget.uncertain is False


class _WindowCutProvider:
    """A provider that refuses the way the budget layer does: cut, with the text it got."""

    model = "stub-window-cut"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self):
        self.payloads = []

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        self.payloads.append(payload)
        rows = payload["evidence"]
        index = len(self.payloads) - 1
        if index != 1:
            name = rows[0]["quote"].split("：", 1)[1].split("向", 1)[0]
            return ModelResponse(content=json.dumps({"items": [
                {"kind": "entity", "key": f"dept_{index}", "meaning": name,
                 "evidence_class": "SOURCE_DIRECT",
                 "evidence_refs": [rows[0]["evidence_id"]]}]}, ensure_ascii=False),
                finish_reason="stop")
        kept = ",".join(json.dumps({"kind": "entity", "key": f"dept_{index}_{n}",
                                    "meaning": rows[n]["quote"].split("：", 1)[1].split("向", 1)[0],
                                    "evidence_class": "SOURCE_DIRECT",
                                    "evidence_refs": [rows[n]["evidence_id"]]},
                                   ensure_ascii=False) for n in range(2))
        error = ModelControlError("llm_output_truncated", "stopped at the output window")
        error.partial = '{"items": [' + kept
        raise error


def test_the_port_keeps_what_the_cut_page_finished(tmp_path):
    source = tmp_path / "business.md"
    source.write_text("\n".join(
        f"第{index}条：财务部门{index}向法务部门报送第{index}项月度经营分析"
        for index in range(90)), encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("req_window_cut", "请理解这些资料",
                             source_refs=(source,), intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_window_cut", requested_depth="semantic",
                             budget_steps=16),
        source_root=tmp_path, semantic_provider=_WindowCutProvider())
    assert result.producer_attribution["refused_units"] == []
    [truncated] = result.producer_attribution["truncated_units"]
    assert truncated["items"] == 2
    keys = [item.key for item in result.semantic_candidate.items if item.kind == "entity"]
    assert keys == ["dept_0", "dept_1_0", "dept_1_1", "dept_2"]


def _escaped(value):
    """The answer as one live card received it: the same object, one quoting layer down.

    deepseek sent `{\"items\": ...}` with every inner quote escaped; `json.loads` refuses
    that string although the object is right there, and the page was refused as malformed
    while the card went on without it.
    """
    return json.dumps(value, ensure_ascii=False).replace('"', '\\"')


def test_an_answer_that_arrived_escaped_is_read_rather_than_refused():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    answer = {"items": [{"kind": "entity", "key": "fengongsi_jingli", "meaning": "分公司经理"}]}
    budget.finish(_response(_escaped(answer), "stop"), prepared)
    assert budget.status == "metered"
    assert budget.settled is True and budget.uncertain is False


def test_an_answer_wrapped_in_a_string_is_read_once_more():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    answer = {"items": []}
    budget.finish(_response(json.dumps(json.dumps(answer, ensure_ascii=False), ensure_ascii=False), "stop"), prepared)
    assert budget.status == "metered"


def test_an_escaped_answer_the_window_cut_is_still_a_cut():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    cut = _escaped({"items": [{"kind": "entity", "key": "a", "meaning": "财务部"}]})[:-2]
    with pytest.raises(ModelControlError) as caught:
        budget.finish(_response(cut, "length"), prepared)
    assert caught.value.public_code == "llm_output_truncated"
    assert caught.value.partial == cut


def test_a_top_level_array_is_still_not_a_json_object():
    budget = TaskBudget(task())
    prepared = budget.prepare(_request())
    budget.dispatch()
    with pytest.raises(ModelControlError) as caught:
        budget.finish(_response('[{"kind": "entity"}]', "stop"), prepared)
    assert caught.value.public_code == "llm_structured_output_invalid"
