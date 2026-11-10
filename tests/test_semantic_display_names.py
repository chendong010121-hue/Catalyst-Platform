"""A name is the page's own text, and a line of prose is not a name.

The reading wrapped whole names in quotation marks, so the store held 「部门架构」 where the
page wrote 部门架构. One slide also writes a heading and its explanation on one line, and the
reading opened an entity for the whole line: a statement sat in the graph as a thing nothing
could be placed under.
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


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_display_names",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_display_names",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    model = "stub-name-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        return ModelResponse(content=json.dumps({"items": self._build(payload["evidence"])},
                                                ensure_ascii=False),
                             finish_reason="stop")


def _ids(evidence):
    return {row["quote"]: row["evidence_id"] for row in evidence}


def _entity(key, meaning, evidence_id):
    return {"kind": "entity", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id]}


def _run(tmp_path, build, lines):
    source = tmp_path / "org.md"
    source.write_text("\n".join(lines), encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build))


SENTENCE = "现有业务模式升级：深度融入区域发展，从价值分享者到价值创造者"


def test_a_quoted_name_is_stored_without_its_quotation_marks(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("bumen_jiagou", "「部门架构」", ids["二、各部门梳理职责边界与部门架构"])]

    result = _run(tmp_path, build, ["二、各部门梳理职责边界与部门架构"])
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    # The marks are how the reading says "this is the literal text", not part of the name.
    assert entity.meaning == "部门架构"
    assert "entity_name_unwrapped" in result.producer_attribution["catalyst_transforms"]


def test_spacing_inside_a_name_is_left_as_the_page_wrote_it(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("kehu", "「客 户」", ids["客 户"])]

    result = _run(tmp_path, build, ["客 户"])
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    # The store also holds a name against the line it came from, so a name tidied to 客户
    # would no longer be in that line. The marks go, the spacing stays.
    assert entity.meaning == "客 户"


def test_a_line_nothing_joins_is_read_as_the_claim_it_is(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("huanjie_shengji", f"「{SENTENCE}」", ids[SENTENCE])]

    result = _run(tmp_path, build, [SENTENCE])
    items = result.semantic_candidate.items
    assert not [item for item in items if item.kind == "entity"]
    claim = next(item for item in items if item.key == "huanjie_shengji")
    assert claim.kind == "claim"
    assert claim.meaning == SENTENCE
    assert claim.evidence_refs
    attribution = result.producer_attribution
    assert attribution["sentence_names_read_as_claim_count"] == 1
    assert attribution["sentence_names_read_as_claim"][0]["item_key"] == "huanjie_shengji"
    assert "sentence_name_read_as_claim" in attribution["catalyst_transforms"]


def test_a_sentence_a_relation_joins_stays_the_node_it_is(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [
            _entity("huanjie_shengji", f"「{SENTENCE}」", ids[SENTENCE]),
            _entity("zongbu", "总部", ids["总部"]),
            {"kind": "relation", "key": "zongbu_tui_shengji", "meaning": f"总部 推进 「{SENTENCE}」",
             "subject": "zongbu", "object": "huanjie_shengji", "predicate": "负责",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [ids[SENTENCE], ids["总部"]]},
        ]

    result = _run(tmp_path, build, [SENTENCE, "总部"])
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # Something in the graph was placed against the line, so it is not moved out from under
    # that edge; the count names it instead.
    assert "huanjie_shengji" in keys
    attribution = result.producer_attribution
    assert attribution["sentence_names_kept_joined"][0]["item_key"] == "huanjie_shengji"
    assert attribution["sentence_names_read_as_claim_count"] == 0
