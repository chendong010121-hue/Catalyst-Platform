"""A date a row states is a date the page wrote.

The cover of the deck prints 2025年1月 and, in its own run, the page number 1. The reading joined
the five runs into 即2025年1月1日 and the card carried a day the page never wrote - the one kind of
fact a reader takes without re-checking it.
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

COVER = ["水利集团组织架构", "2025", "年", "1", "月"]


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_stated_dates",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_stated_dates",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    model = "stub-date-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        return ModelResponse(content=json.dumps({"items": self._build(payload["evidence"])},
                                                ensure_ascii=False),
                             finish_reason="stop")


def _claim(key, meaning, evidence_ids):
    return {"kind": "claim", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": list(evidence_ids)}


def _run(tmp_path, build, lines):
    source = tmp_path / "cover.md"
    source.write_text("\n".join(lines), encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build))


def test_a_date_the_page_wrote_in_runs_is_kept(tmp_path):
    def build(evidence):
        runs = [row["evidence_id"] for row in evidence][1:]
        return [_claim("yantao_shijian", "本页标注的日期为「2025」「年」「1」「月」，即2025年1月。", runs)]

    result = _run(tmp_path, build, COVER)
    # The four runs put back in order spell the date, so the row states what the page wrote.
    claim = next(item for item in result.semantic_candidate.items if item.key == "yantao_shijian")
    assert claim.kind == "claim"
    assert "date_not_in_evidence" not in result.producer_attribution["item_contract_drop_counts"]


def test_a_day_the_page_never_wrote_does_not_reach_the_card(tmp_path):
    def build(evidence):
        runs = [row["evidence_id"] for row in evidence][1:]
        return [_claim("yantao_shijian_2025_01_01",
                       "本页标注的日期为「2025」「年」「1」「月」「1」，即2025年1月1日。", runs)]

    result = _run(tmp_path, build, [*COVER, "1"])
    # The date cannot reach the card as a stated fact, and the row built on it cannot
    # either: what is left is the reading's own arithmetic, kept whole in run evidence.
    assert [item for item in result.semantic_candidate.items
            if item.key == "yantao_shijian_2025_01_01"] == []
    diagnostic = {row["key"]: row for row in result.run_diagnostics}["yantao_shijian_2025_01_01"]
    assert diagnostic["uncertainty"] == "degraded:date_not_in_evidence:2025年1月1日"
    assert diagnostic["reason"] == "date_not_in_evidence"
    attribution = result.producer_attribution
    assert attribution["item_contract_drop_counts"]["date_not_in_evidence"] == 1
    # 日 is a character no run carries, so the day is the reading's arithmetic and is named.
    assert attribution["item_contract_drops"][0]["dates"] == ["2025年1月1日"]


def test_a_day_the_page_does_write_is_a_date_the_row_may_state(tmp_path):
    def build(evidence):
        ids = [row["evidence_id"] for row in evidence]
        return [_claim("yantao_shijian", "研讨会于2025年1月1日召开", ids)]

    result = _run(tmp_path, build, ["研讨会于2025年1月1日召开"])
    claim = next(item for item in result.semantic_candidate.items if item.key == "yantao_shijian")
    # The rule costs a row nothing when the page spelled the day itself.
    assert claim.meaning == "研讨会于2025年1月1日召开"


def test_another_rows_passage_does_not_spell_this_rows_date(tmp_path):
    def build(evidence):
        rows = [row["evidence_id"] for row in evidence]
        cover_runs = rows[1:6]  # the four date runs and the page number
        return [_claim("yantao_shijian_2025_01_01", "本页标注的日期为2025年1月1日。", cover_runs)]

    # The page does spell that day elsewhere; this row does not cite the line that does.
    result = _run(tmp_path, build, [*COVER, "1", "上期计划于2025年1月1日启动"])
    # The day is on another page of the same source, not on the line this row cites, so
    # the row is the reading's arithmetic and stays in run evidence.
    assert [item for item in result.semantic_candidate.items
            if item.key == "yantao_shijian_2025_01_01"] == []
    assert "yantao_shijian_2025_01_01" in {row["key"] for row in result.run_diagnostics}
    assert result.producer_attribution["item_contract_drop_counts"]["date_not_in_evidence"] == 1
