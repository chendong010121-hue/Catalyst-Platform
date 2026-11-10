"""A hierarchy line reads one way, and a line the chain already carries is the chain again.

One 14-page card stated the same subordination in both directions (集团 隶属 党委会 beside
党委会 隶属 集团), because the prompt listed 下设 and 隶属 as one predicate while the two
sentences name their subjects the other way round; it also wrote the skip-level line beside
the chain that already states it. Neither is a reading of the material, so both are dropped
here, and each names why.
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
from catalyst_platform.understand_semantic import semantic_extraction_rules
from catalyst_platform.understand_verify import verification_integrity, verification_local_checks


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_relation_direction",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_relation_direction",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    """One answer, built from the evidence ids the request carried."""

    model = "stub-direction-model"
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
    """The id of the line that spells each name: one line quotes one name."""
    return {row["quote"]: row["evidence_id"] for row in evidence}


def _entity(key, meaning, evidence_id):
    return {"kind": "entity", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id]}


def _relation(key, subject, target, ends, predicate="隶属"):
    """One hierarchy line read off the layout, so its wording never decides the test."""
    return {"kind": "relation", "key": key,
            "meaning": "「%s」在版式中列于「%s」之下" % (subject, target),
            "subject": subject, "object": target, "predicate": predicate,
            "relation_source": "LAYOUT", "layout_ref": "org.md 版面：名称上下排布",
            "evidence_class": "INFERRED", "evidence_refs": list(ends)}


def _run(tmp_path, build):
    source = tmp_path / "org.md"
    source.write_text("水利集团\n党委会\n分公司\n招投标部", encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build))


def test_a_mirror_pair_is_dropped_whole_and_each_half_names_the_other(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        both = [ids["水利集团"], ids["党委会"]]
        return [_entity("jituan", "水利集团", ids["水利集团"]),
                _entity("dangweihui", "党委会", ids["党委会"]),
                _relation("jituan_in_dangweihui", "jituan", "dangweihui", both),
                _relation("dangweihui_in_jituan", "dangweihui", "jituan", both)]

    result = _run(tmp_path, build)
    assert [item.key for item in result.semantic_candidate.items if item.kind == "relation"] == []
    dropped = {row["item_key"]: row for row in result.producer_attribution["dropped_relations"]}
    assert dropped["jituan_in_dangweihui"]["rule"] == "relation_direction_conflict"
    assert dropped["jituan_in_dangweihui"]["inverse_of"] == "dangweihui_in_jituan"
    assert dropped["dangweihui_in_jituan"]["inverse_of"] == "jituan_in_dangweihui"
    assert dropped["jituan_in_dangweihui"]["predicate"] == "隶属"


def test_the_review_is_told_which_keys_mirrored(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        both = [ids["水利集团"], ids["党委会"]]
        return [_entity("jituan", "水利集团", ids["水利集团"]),
                _entity("dangweihui", "党委会", ids["党委会"]),
                _relation("jituan_in_dangweihui", "jituan", "dangweihui", both),
                _relation("dangweihui_in_jituan", "dangweihui", "jituan", both)]

    result = _run(tmp_path, build)
    attribution = result.producer_attribution
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    [check] = [row for row in checks if row["rule"] == "relation_direction_conflict"]
    assert {pair["item_key"] for pair in check["pairs"]} == {"jituan_in_dangweihui",
                                                             "dangweihui_in_jituan"}
    assert "mirror each other" in check["detail"]


def test_a_skip_level_line_is_dropped_when_the_chain_already_states_it(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("zhaobiao", "招投标部", ids["招投标部"]),
                _entity("gongsi", "分公司", ids["分公司"]),
                _entity("jituan", "水利集团", ids["水利集团"]),
                _relation("zhaobiao_in_gongsi", "zhaobiao", "gongsi",
                          [ids["招投标部"], ids["分公司"]]),
                _relation("gongsi_in_jituan", "gongsi", "jituan",
                          [ids["分公司"], ids["水利集团"]]),
                _relation("zhaobiao_in_jituan", "zhaobiao", "jituan",
                          [ids["招投标部"], ids["水利集团"]])]

    result = _run(tmp_path, build)
    kept = {item.key for item in result.semantic_candidate.items if item.kind == "relation"}
    assert kept == {"zhaobiao_in_gongsi", "gongsi_in_jituan"}
    dropped = {row["item_key"]: row for row in result.producer_attribution["dropped_relations"]}
    assert dropped["zhaobiao_in_jituan"]["rule"] == "relation_transitive_closure"
    assert dropped["zhaobiao_in_jituan"]["via"] == ["zhaobiao_in_gongsi"]


def test_two_parents_with_no_chain_between_them_are_both_kept(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("zhaobiao", "招投标部", ids["招投标部"]),
                _entity("gongsi", "分公司", ids["分公司"]),
                _entity("jituan", "水利集团", ids["水利集团"]),
                _relation("zhaobiao_in_gongsi", "zhaobiao", "gongsi",
                          [ids["招投标部"], ids["分公司"]]),
                _relation("zhaobiao_in_jituan", "zhaobiao", "jituan",
                          [ids["招投标部"], ids["水利集团"]])]

    result = _run(tmp_path, build)
    kept = {item.key for item in result.semantic_candidate.items if item.kind == "relation"}
    # A matrix leaves two parents standing side by side; only a stated chain makes one of
    # them the chain read again.
    assert kept == {"zhaobiao_in_gongsi", "zhaobiao_in_jituan"}
    assert result.producer_attribution["dropped_relations"] == []


def test_a_hierarchy_inside_a_cycle_is_kept(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("zhaobiao", "招投标部", ids["招投标部"]),
                _entity("gongsi", "分公司", ids["分公司"]),
                _entity("jituan", "水利集团", ids["水利集团"]),
                _relation("zhaobiao_in_gongsi", "zhaobiao", "gongsi",
                          [ids["招投标部"], ids["分公司"]]),
                _relation("gongsi_in_jituan", "gongsi", "jituan",
                          [ids["分公司"], ids["水利集团"]]),
                _relation("jituan_in_zhaobiao", "jituan", "zhaobiao",
                          [ids["水利集团"], ids["招投标部"]])]

    result = _run(tmp_path, build)
    kept = {item.key for item in result.semantic_candidate.items if item.kind == "relation"}
    # Nothing here says a ring is wrong; it only refuses to call one of its edges the
    # chain read twice.
    assert kept == {"zhaobiao_in_gongsi", "gongsi_in_jituan", "jituan_in_zhaobiao"}


def test_a_duty_read_either_way_is_not_a_hierarchy_conflict(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        both = [ids["水利集团"], ids["党委会"]]
        return [_entity("jituan", "水利集团", ids["水利集团"]),
                _entity("dangweihui", "党委会", ids["党委会"]),
                _relation("jituan_owns", "jituan", "dangweihui", both, predicate="负责"),
                _relation("dangweihui_issues", "dangweihui", "jituan", both, predicate="产出")]

    result = _run(tmp_path, build)
    kept = {item.key for item in result.semantic_candidate.items if item.kind == "relation"}
    assert kept == {"jituan_owns", "dangweihui_issues"}
    assert result.producer_attribution["dropped_relations"] == []


def test_the_contract_reads_a_hierarchy_line_with_the_part_first():
    rules = semantic_extraction_rules()
    assert "a hierarchy line read with the part first" in rules
    # The four sentences the model collapsed into one predicate are split by their subject.
    assert "Y 下设 X and Y 设立 X state the same thing upside down" in rules
    assert "A hierarchy line's subject is the part and its object the whole" in rules
    # A mirror costs both lines, not one of them chosen at random.
    assert "an answer that writes both of them has both dropped" in rules
    # A collecting heading never stands as the part.
    assert "is not a thing the answer declares" in rules
    assert "the chain read once more" in rules
