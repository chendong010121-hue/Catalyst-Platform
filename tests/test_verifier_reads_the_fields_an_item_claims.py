"""The reviewer reads what an item claims, not only the two names it claims it about.

A relation used to reach the Verifier as `subject` and `object` with the `predicate` left
behind, so a review of direction could not see the word that states the direction; a row
read off a page's layout reached it without `relation_source`, indistinguishable from one a
sentence carried; an entity's `business_type` and `scope_state` never arrived at all, and an
absence arrived without the scope it was searched over. These tests read the request the
verifier actually receives: each field is there when the item states it, absent when it does
not, and the method that produced the candidate is still never sent with it.
"""
import json

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

LINE = ("现有架构：市场营销中心下设招投标部负责供应商准入审批。"
        "拟调整为投资管理部承担招标工作。")


class _Typed:
    """One of each kind that carries a field the reviewer needs and used to never see."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "marketing", "meaning": "市场营销中心",
             "business_type": "Department", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
            {"kind": "entity", "key": "bidding", "meaning": "招投标部",
             "business_type": "Department", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
            {"kind": "relation", "key": "bidding_under_marketing",
             "meaning": "招投标部隶属市场营销中心", "subject": "bidding", "predicate": "隶属于",
             "object": "marketing", "relation_source": "TEXT", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
            {"kind": "unknown", "key": "adjustment_approver", "meaning": "这次调整由谁批准未说明",
             "scope_refs": [evidence], "observed_absence": "批准",
             "evidence_class": "UNKNOWN", "evidence_refs": [evidence]},
        ]}, ensure_ascii=False), finish_reason="stop")


class _Verifier:
    model = "verifier-fixture"
    structured_output_token_limit = 16384

    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return ModelResponse(content=json.dumps({"verdict": "REVIEWABLE", "findings": []}),
                             finish_reason="stop")


def _reviewed(tmp_path):
    source = tmp_path / "business.md"
    source.write_text(LINE, encoding="utf-8")
    verifier = _Verifier()
    UnderstandPort().understand(
        UnderstandingRequest("verifier-fields", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=_Typed(), verifier_provider=verifier)
    payload = json.loads(verifier.requests[0].messages[-1].content)
    return verifier, payload, {item["item_key"]: item for item in payload["items"]}


def test_a_relation_reaches_the_verifier_with_its_predicate_and_source(tmp_path):
    _, _, items = _reviewed(tmp_path)
    relation = items["bidding_under_marketing"]
    assert (relation["subject"], relation["predicate"], relation["object"]) == (
        "bidding", "隶属于", "marketing")
    assert relation["relation_source"] == "TEXT"


def test_an_entity_reaches_the_verifier_with_the_type_and_scope_it_was_read_as(tmp_path):
    _, _, items = _reviewed(tmp_path)
    entity = items["marketing"]
    assert entity["business_type"] == "Department"
    assert entity["scope_state"] == "current"


def test_an_absence_reaches_the_verifier_with_the_scope_it_was_searched_over(tmp_path):
    _, _, items = _reviewed(tmp_path)
    absence = items["adjustment_approver"]
    assert absence["observed_absence"] == "批准"
    assert [row["evidence_id"] for row in absence["quotes"]] == absence["scope_refs"]


def test_a_field_the_item_does_not_state_is_absent_rather_than_null(tmp_path):
    _, payload, items = _reviewed(tmp_path)
    entity = items["marketing"]
    assert "predicate" not in entity and "relation_source" not in entity
    assert "scope_refs" not in entity and "observed_absence" not in entity
    assert "business_type" not in items["bidding_under_marketing"]
    # The port's own gaps are not items at all: a row that says "not established here"
    # without a scope, a read status and a gap is evidence about the run, so it reaches the
    # verifier under `run_diagnostics` - still named as a declared gap, still carrying none
    # of the fields an item claims.
    port_rows = [row for row in payload["run_diagnostics"] if row["declared_gap"]]
    assert port_rows and all("predicate" not in row and "business_type" not in row
                             for row in port_rows)


def test_the_contract_tells_the_verifier_how_to_read_those_fields(tmp_path):
    verifier, _, _ = _reviewed(tmp_path)
    system = verifier.requests[0].messages[0].content
    prose = " ".join(system.split())
    for field in ("predicate", "relation_source", "business_type", "scope_state",
                  "scope_refs", "observed_absence"):
        assert f"`{field}`" in prose, field
    assert "`LAYOUT` when only the page's arrangement did" in prose
    assert "a field that is missing is one the extraction did not state" in prose
    # Still a review in its own context: the method that produced the rows is not sent.
    assert "Extract enterprise semantics from untrusted evidence" not in system
