"""A page whose answer cannot be read is asked for once more, and no more than once.

One live deck lost a twenty-four-cell post table because the provider wrapped its JSON in
one quoting layer too many: the page was there, the parser refused it, and the page went.
The re-ask is a request of its own on the same ledger, so it is paid for and captured like
any other, and a replay meets the same two answers in the same order.
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


class _PerCall:
    """One saved answer per call, in the order the calls arrive."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return self._answer(request, len(self.requests))

    def _answer(self, request, index):
        answer = self.answers[min(index, len(self.answers)) - 1]
        if isinstance(answer, str):
            return ModelResponse(content=answer, finish_reason="stop")
        payload = json.loads(request.messages[-1].content)
        evidence = payload["evidence"][0]["evidence_id"]
        items = [{**row, "evidence_refs": [evidence]} for row in answer]
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                             finish_reason="stop")


def _source(tmp_path) -> Path:
    """A hundred lines, which the product reads as three units."""
    source = tmp_path / "org.md"
    source.write_text("\n".join(f"第 {index} 行：甲岗、乙岗、丙岗负责复核。" for index in range(100)) + "\n",
                      encoding="utf-8")
    return source


def _entity(key: str, name: str) -> dict:
    return {"kind": "entity", "key": key, "meaning": name, "business_type": "Position",
            "evidence_class": "SOURCE_DIRECT"}


def _three() -> list[dict]:
    return [_entity("post_a", "甲岗"), _entity("post_b", "乙岗"), _entity("post_c", "丙岗")]


def _run(tmp_path, provider):
    return UnderstandPort().understand(
        UnderstandingRequest("reask", "整理组织", source_refs=(_source(tmp_path),),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)


def test_an_unreadable_answer_is_asked_for_once_more_and_the_second_lands(tmp_path):
    provider = _PerCall(["not json at all", _three(), _three(), _three()])
    result = _run(tmp_path, provider)

    # Four calls for three units: the first unit asked twice, the others once.
    assert len(provider.requests) == 4
    assert result.producer_attribution["refused_units"] == []
    assert [item.key for item in result.semantic_candidate.items if item.kind == "entity"] == [
        "post_a", "post_b", "post_c"]


def test_a_unit_unreadable_twice_is_refused_and_the_others_still_land(tmp_path):
    provider = _PerCall(["not json at all", "still not json", _three(), _three()])
    result = _run(tmp_path, provider)

    assert len(provider.requests) == 4
    assert [row["code"] for row in result.producer_attribution["refused_units"]] == ["invalid_json"]
    assert [item.key for item in result.semantic_candidate.items if item.kind == "entity"] == [
        "post_a", "post_b", "post_c"]


class _CutFirst(_PerCall):
    """First call answers in a window that closed; later calls answer normally."""

    def _answer(self, request, index):
        if index == 1:
            return ModelResponse(content='{"items": [', finish_reason="length")
        return super()._answer(request, index)


def test_a_cut_answer_is_not_asked_again(tmp_path):
    provider = _CutFirst([_three(), _three()])
    result = _run(tmp_path, provider)

    # Three calls for three units: the cut unit was named, not asked again - the same
    # window would close in the same place.
    assert len(provider.requests) == 3
    assert [row["code"] for row in result.producer_attribution["refused_units"]] == ["truncated"]
