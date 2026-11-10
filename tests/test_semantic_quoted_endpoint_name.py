"""A quoted spelling is the same name when a relation sentence has to name its own ends.

The item contract drops a relation whose sentence does not write both of its ends, which is
right: a row about something else cannot be a statement of this edge. It compared the names
as they were spelled, so a deck that wrote 「招投标部」 on the entity row and 招投标部 in the
sentence beside it lost the edge it had just stated - live38 lost all three 下设 edges of the
merged centre that way. The merge above already reads a quoted name as the same name; these
two tests hold both halves of that: the quoted spelling joins, and a sentence about another
name still does not.
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


class _Rows:
    """One answer for one evidence unit; every row cites the passage it was read off."""

    model = "stub-quoted-end"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, rows):
        self._rows = rows

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        evidence_id = evidence[0]["evidence_id"]
        return ModelResponse(content=json.dumps(
            {"items": [dict(row, evidence_refs=[evidence_id]) for row in self._rows]},
            ensure_ascii=False), finish_reason="stop")


def _read(tmp_path, text, rows):
    source = tmp_path / "org.md"
    source.write_text(text, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("quoted-end", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_quoted",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Rows(rows))


def test_a_quoted_endpoint_name_still_joins_its_sentence(tmp_path):
    result = _read(tmp_path, "水利集团下设招投标部。", [
        {"kind": "entity", "key": "jituan", "meaning": "水利集团",
         "evidence_class": "SOURCE_DIRECT"},
        {"kind": "entity", "key": "zhaotoubiao", "meaning": "「招投标部」",
         "evidence_class": "SOURCE_DIRECT"},
        {"kind": "relation", "key": "zhaotoubiao_lishu", "subject": "zhaotoubiao",
         "predicate": "隶属", "object": "jituan", "meaning": "水利集团下设招投标部",
         "evidence_class": "SOURCE_DIRECT"},
    ])
    assert result.producer_attribution["dropped_relations"] == []
    assert result.producer_attribution["relation_verification"] == {"confirmed": 1,
                                                                   "unconfirmed": 0}


def test_a_sentence_about_another_name_is_still_dropped(tmp_path):
    result = _read(tmp_path, "四分公司合并到天水智静。", [
        {"kind": "entity", "key": "sifengongsi", "meaning": "四分公司",
         "evidence_class": "SOURCE_DIRECT"},
        {"kind": "entity", "key": "zhijing", "meaning": "天水智静",
         "evidence_class": "SOURCE_DIRECT"},
        {"kind": "relation", "key": "hebing_zhijing", "subject": "sifengongsi",
         "predicate": "隶属", "object": "zhijing", "meaning": "四分公司合并到智静",
         "evidence_class": "SOURCE_DIRECT"},
    ])
    assert result.producer_attribution["dropped_relations"] == [
        {"item_key": "hebing_zhijing", "rule": "relation_meaning_does_not_join_its_endpoints"}]
