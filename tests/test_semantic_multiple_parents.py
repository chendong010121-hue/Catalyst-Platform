"""A matrix is named, never flattened, and a grouping heading is not a thing of its own.

One card let 二分公司 hang under two parents at once and gave 分公司, 子公司 and 中台部门 a
place on both sides of the hierarchy, because nothing in the contract said what a heading
that only collects the names below it is. The matrix is counted and left standing for the
review; the heading is no longer declared at all.
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
        request_id="req_multiple_parents",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_multiple_parents",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    model = "stub-parents-model"
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


def _relation(key, subject, target, ends):
    return {"kind": "relation", "key": key,
            "meaning": "「%s」在版式中列于「%s」之下" % (subject, target),
            "subject": subject, "object": target, "predicate": "隶属",
            "relation_source": "LAYOUT", "layout_ref": "org.md 版面：名称上下排布",
            "evidence_class": "INFERRED", "evidence_refs": list(ends)}


def _run(tmp_path, build):
    source = tmp_path / "org.md"
    source.write_text("水利集团\n区域公司\n二分公司", encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build))


def test_a_child_under_two_parents_is_named_and_left_standing(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("erfengongsi", "二分公司", ids["二分公司"]),
                _entity("quyu", "区域公司", ids["区域公司"]),
                _entity("jituan", "水利集团", ids["水利集团"]),
                _relation("er_in_quyu", "erfengongsi", "quyu", [ids["二分公司"], ids["区域公司"]]),
                _relation("er_in_jituan", "erfengongsi", "jituan", [ids["二分公司"], ids["水利集团"]])]

    result = _run(tmp_path, build)
    kept = {item.key for item in result.semantic_candidate.items if item.kind == "relation"}
    assert kept == {"er_in_quyu", "er_in_jituan"}
    attribution = result.producer_attribution
    assert attribution["multiple_parent_entity_count"] == 1
    [row] = attribution["multiple_parent_entities"]
    assert row["item_key"] == "erfengongsi"
    assert row["parent_count"] == 2
    assert sorted(row["parents"]) == ["jituan", "quyu"]
    assert attribution["dropped_relations"] == []


def test_the_review_reads_the_matrix_as_a_hint_not_a_drop(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("erfengongsi", "二分公司", ids["二分公司"]),
                _entity("quyu", "区域公司", ids["区域公司"]),
                _entity("jituan", "水利集团", ids["水利集团"]),
                _relation("er_in_quyu", "erfengongsi", "quyu", [ids["二分公司"], ids["区域公司"]]),
                _relation("er_in_jituan", "erfengongsi", "jituan", [ids["二分公司"], ids["水利集团"]])]

    result = _run(tmp_path, build)
    attribution = result.producer_attribution
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    [check] = [row for row in checks if row["rule"] == "multiple_parent_entity"]
    assert check["entities"] == [{"item_key": "erfengongsi", "parents": ["jituan", "quyu"]}]
    assert "nothing was dropped" in check["detail"]


def test_one_parent_is_not_a_matrix(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("erfengongsi", "二分公司", ids["二分公司"]),
                _entity("quyu", "区域公司", ids["区域公司"]),
                _relation("er_in_quyu", "erfengongsi", "quyu", [ids["二分公司"], ids["区域公司"]])]

    result = _run(tmp_path, build)
    attribution = result.producer_attribution
    assert attribution["multiple_parent_entity_count"] == 0
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    assert [row for row in checks if row["rule"] == "multiple_parent_entity"] == []


def test_the_contract_keeps_a_collecting_heading_out_of_the_answer():
    rules = semantic_extraction_rules()
    assert "is not a thing the answer declares" in rules
    assert "it is neither an entity nor the end of a 隶属 line" in rules
    # Membership is said with the type or a claim, never with a hierarchy line.
    assert "carrying the heading as its business_type" in rules
    # A heading that really is an organisation still enters on its page's own sentence.
    assert "that page's own sentence makes it an entity" in rules
