"""A page that answered almost nothing is named, and is never refused for it.

One live deck had a twenty-cell page come back with one row and a twenty-four-cell page
with none. Nothing in the card said so: the rows that did arrive looked like the whole
page, and a reader could not tell "looked at, nearly empty" from "read almost nothing".
The unit is named in producer_attribution instead, and its rows still reach the card.
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


class _PerUnit:
    """One saved answer per extraction unit, in the order the units arrive."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        payload = json.loads(request.messages[-1].content)
        evidence = payload["evidence"][0]["evidence_id"]
        rows = self.answers[min(len(self.requests), len(self.answers)) - 1]
        items = [{**row, "evidence_refs": [evidence]} if isinstance(row, dict) else row for row in rows]
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                             finish_reason="stop")


def _source(tmp_path) -> Path:
    """A hundred lines, which the product reads as three units (forty, forty, twenty)."""
    source = tmp_path / "org.md"
    source.write_text("\n".join(f"第 {index} 行：甲岗、乙岗、丙岗负责复核。" for index in range(100)) + "\n",
                      encoding="utf-8")
    return source


def _entity(key: str, name: str) -> dict:
    return {"kind": "entity", "key": key, "meaning": name, "business_type": "Position",
            "evidence_class": "SOURCE_DIRECT"}


def _three() -> list[dict]:
    """An ordinary page: three named posts, above what the thin screen names."""
    return [_entity("post_a", "甲岗"), _entity("post_b", "乙岗"), _entity("post_c", "丙岗")]


def _run(tmp_path, provider):
    return UnderstandPort().understand(
        UnderstandingRequest("thin-unit", "整理组织", source_refs=(_source(tmp_path),),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)


def test_a_unit_that_answered_nothing_is_named_and_keeps_the_others(tmp_path):
    provider = _PerUnit([[], _three(), _three()])
    result = _run(tmp_path, provider)

    # The unit is named with what it gave and what it was asked to read; the two units
    # beside it are not, because three rows over forty cells is a page doing its work.
    assert result.producer_attribution["thin_units"] == [
        {"unit": "lines:0", "items": 0, "cells": 39}]
    assert [item.key for item in result.semantic_candidate.items if item.kind == "entity"] == [
        "post_a", "post_b", "post_c"]
    assert result.producer_attribution["refused_units"] == []


def test_a_unit_that_answered_one_row_is_named_too(tmp_path):
    provider = _PerUnit([[_entity("post_a", "甲岗")], _three(), _three()])
    result = _run(tmp_path, provider)

    assert [row["unit"] for row in result.producer_attribution["thin_units"]] == ["lines:0"]
    assert result.producer_attribution["thin_units"][0]["items"] == 1


def test_an_ordinary_page_is_not_named(tmp_path):
    provider = _PerUnit([_three(), _three(), _three()])
    result = _run(tmp_path, provider)

    assert result.producer_attribution["thin_units"] == []
