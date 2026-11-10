"""A page whose answer runs past the window is read up to the cut, and says so.

One card lost two index pages that way: the model wrote 79 and 77 rows before the window
closed, and the refusal is per unit while the unit is the page, so a third of the deck
never reached the candidate. The rows whose braces closed are whole rows, so they are
kept; the unit is named as truncated, and the review reads that name as an incomplete
candidate rather than as a complete one.

Every test drives the Port through a stub provider; no credential is read and no network
call is made.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_semantic import _MAX_UNIT_ITEMS
from catalyst_platform.understand_wiki import admission_plan


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_truncated",
        message="请理解这些资料中的经营职责、规则和未知项",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_truncated",
        requested_depth="semantic",
        budget_steps=16,
    )


def _lines(tmp_path: Path, count: int) -> Path:
    source = tmp_path / "business.md"
    source.write_text(
        "\n".join(f"第{index}条：财务部门{index}向法务部门报送第{index}项月度经营分析"
                  for index in range(count)),
        encoding="utf-8")
    return source


def _entity(key: str, meaning: str, evidence_id: str) -> str:
    return json.dumps({"kind": "entity", "key": key, "meaning": meaning,
                       "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
                      ensure_ascii=False)


class _CutProvider:
    """Answers every unit; the cut unit's answer stops in the middle of a row."""

    model = "stub-cut-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, cut=1, finished=2, extra_cut_row=False, wide_cut=0):
        self.cut, self.finished, self.extra_cut_row, self.wide_cut = cut, finished, extra_cut_row, wide_cut
        self.payloads = []

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        self.payloads.append(payload)
        index = len(self.payloads) - 1
        rows = payload["evidence"]
        if index != self.cut:
            return ModelResponse(content=json.dumps({"items": [json.loads(_entity(
                f"dept_{index}", rows[0]["quote"].split("：", 1)[1].split("向", 1)[0],
                rows[0]["evidence_id"]))]}, ensure_ascii=False), finish_reason="stop")
        if self.wide_cut:
            kept = ",".join(_entity(f"dept_{index}_{n}",
                                    rows[n % len(rows)]["quote"].split("：", 1)[1].split("向", 1)[0],
                                    rows[n % len(rows)]["evidence_id"])
                            for n in range(self.wide_cut))
        else:
            kept = ",".join(_entity(f"dept_{index}_{n}",
                                    rows[n]["quote"].split("：", 1)[1].split("向", 1)[0],
                                    rows[n]["evidence_id"]) for n in range(self.finished))
        if self.extra_cut_row:
            kept += ',{"kind": "entity", "key": "dept_cjk", "meaning": "财务部门"'
        # The window closes here: the first rows closed, the last one did not.
        return ModelResponse(content='{"items": [' + kept, finish_reason="length")


def test_a_cut_page_keeps_every_row_it_finished(tmp_path):
    result = UnderstandPort().understand(_request(_lines(tmp_path, 90)), source_root=tmp_path,
                                         semantic_provider=_CutProvider())
    assert [item.key for item in result.semantic_candidate.items
            if item.kind == "entity"] == ["dept_0", "dept_1_0", "dept_1_1", "dept_2"]
    assert result.producer_attribution["unit_item_counts"] == [1, 2, 1]
    assert result.producer_attribution["refused_units"] == []


def test_the_cut_page_is_named_with_the_rows_it_kept(tmp_path):
    result = UnderstandPort().understand(_request(_lines(tmp_path, 90)), source_root=tmp_path,
                                         semantic_provider=_CutProvider())
    [truncated] = result.producer_attribution["truncated_units"]
    assert truncated["unit"].startswith("lines:") and truncated["items"] == 2
    assert result.producer_attribution["truncated_unit_items"] == 2
    plan = admission_plan(result)
    assert plan["gaps"]["truncated_units"] == [truncated["unit"]]
    # A page read only up to the cut is a gap the plan must not report as no gap.
    assert plan["coverage_gap"] is True


def test_a_cut_with_no_finished_row_still_refuses_the_unit(tmp_path):
    provider = _CutProvider(finished=0)
    result = UnderstandPort().understand(_request(_lines(tmp_path, 90)), source_root=tmp_path,
                                         semantic_provider=provider)
    [refused] = result.producer_attribution["refused_units"]
    assert refused["code"] == "truncated"
    assert result.producer_attribution["unit_item_counts"] == [1, 0, 1]
    assert result.producer_attribution["truncated_units"] == []


def test_a_row_the_cut_left_open_is_never_guessed_at(tmp_path):
    result = UnderstandPort().understand(_request(_lines(tmp_path, 90)), source_root=tmp_path,
                                         semantic_provider=_CutProvider(extra_cut_row=True))
    keys = [item.key for item in result.semantic_candidate.items if item.kind == "entity"]
    assert "dept_cjk" not in keys and len(keys) == 4
    assert result.producer_attribution["truncated_unit_items"] == 2


def test_a_cut_answer_past_the_unit_budget_is_refused_whole(tmp_path):
    # One page may hold a bounded number of rows; an answer cut after more of them broke
    # that before it broke the window, and a trimmed page must never look complete.
    result = UnderstandPort().understand(
        _request(_lines(tmp_path, 90)), source_root=tmp_path,
        semantic_provider=_CutProvider(wide_cut=_MAX_UNIT_ITEMS + 1))
    [refused] = result.producer_attribution["refused_units"]
    assert refused["code"] == "semantic_capacity_exceeded"
    assert "dept_1_0" not in [item.key for item in result.semantic_candidate.items]

def test_the_cut_row_counts_as_a_kept_row_only_after_its_key_can_be_stored(tmp_path):
    # Two finished rows and a third the cut left open: the open one is dropped before
    # the key check ever sees it, so the unit is kept rather than refused for a row it
    # never wrote.
    result = UnderstandPort().understand(_request(_lines(tmp_path, 90)), source_root=tmp_path,
                                         semantic_provider=_CutProvider(finished=3, extra_cut_row=True))
    assert result.producer_attribution["truncated_unit_items"] == 3
    assert result.producer_attribution["refused_units"] == []
