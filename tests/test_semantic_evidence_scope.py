"""A direct observation may only use wording its own passages contain.

Three rules, all mechanical, all named so a bounded revision can act on them:

* an entity's meaning is the name itself — a category or role about it is a
  claim with its own evidence (`entity_name_not_in_evidence`);
* a SOURCE_DIRECT meaning may not contain a substantive stretch of text that
  none of its cited passages contains (`meaning_not_in_evidence`);
* an unknown or a conflict states the scope it searched (`scope_refs`) and the
  phrasing it looked for and did not find (`observed_absence`), so an absence
  is a state rather than a quotation (`absence_scope_incomplete`,
  `absence_contradicted_by_scope`).

Both refusals name the item key and never the passage text, so the model can
either cite the passage that says it or declare the item INFERRED.
"""
from types import SimpleNamespace

import json
import pytest

from agent_runtime.contracts import Failure, ModelResponse
from catalyst_platform.semantic_tool import UnderstandCapabilityAdapter
from catalyst_platform.understand_only import (
    SemanticContractError,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    _unquoted_runs,
)

LINE = "财务部门负责月度经营分析，法务部门复核合同预算。"


def _base(tmp_path):
    source = tmp_path / "business.md"
    source.write_text(LINE, encoding="utf-8")
    port = UnderstandPort()
    result = port.understand(
        UnderstandingRequest("scope-gate", "整理职责", source_refs=(source,), intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path)
    return port, result, result.evidence_refs[0].evidence_id


def _attach(port, base, evidence_id, rows):
    return port.attach_producer_items(base, producer_kind="CODEX_EXTERNAL",
                                      producer_invocation_id="scope-gate", items=rows)


def test_entity_name_written_as_the_source_writes_it_is_accepted(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "entity", "key": "finance", "meaning": "财务部门",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert any(item.kind == "entity" and item.meaning == "财务部门" for item in result.semantic_candidate.items)


def test_entity_name_written_inside_quotation_marks_is_accepted(tmp_path):
    """The model quoting the source's own name is the model being precise.

    Live run-30 wrote 「科信检测」 for a passage that says 科信检测; 33 of its entities
    were dropped for the brackets alone, which is the check mistaking a quotation
    mark for part of the name. The row stands, and the store spells the name the way
    the page did: the marks were the reading saying "this is the literal text".
    """
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "entity", "key": "finance", "meaning": "「财务部门」",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert [item.meaning for item in result.semantic_candidate.items] == ["财务部门"]
    assert result.producer_attribution.get("item_contract_drops", []) == []


def test_quotation_marks_do_not_let_a_gloss_through(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "entity", "key": "finance", "meaning": "「财务部门，经营分析的承担机构」",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "finance", "rule": "entity_name_not_in_evidence"}]


def test_a_name_that_only_begins_with_a_bracket_keeps_it(tmp_path):
    from catalyst_platform.understand_semantic import _unwrapped_name

    assert _unwrapped_name("「「党委会」」") == "党委会"
    assert _unwrapped_name("（天津）公司") == "（天津）公司"
    assert _unwrapped_name("「天津」公司") == "「天津」公司"


def test_entity_carrying_a_role_is_dropped_and_named(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "entity", "key": "finance", "meaning": "财务部门，经营分析的承担机构",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "finance", "rule": "entity_name_not_in_evidence"}]
    # The name was never written, so what is left is a question about the reading: the row
    # leaves the candidate whole, with the rule on its face, and the card keeps no claim.
    assert list(result.semantic_candidate.items) == []
    diagnostic = {row["key"]: row for row in result.run_diagnostics}["finance"]
    assert diagnostic["uncertainty"] == "degraded:entity_name_not_in_evidence"
    assert diagnostic["kind"] == "unknown" and diagnostic["destination"] == "run_evidence"


def test_entity_name_must_be_one_passage_not_an_assembled_phrase(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "entity", "key": "both", "meaning": "财务部门与法务部门",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "both", "rule": "entity_name_not_in_evidence"}]


def test_claim_spelled_with_its_own_passage_is_accepted(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert any(item.kind == "claim" and item.key == "duty" for item in result.semantic_candidate.items)


def test_claim_wording_outside_its_passage_is_recorded_not_refused(tmp_path):
    """A claim joins several runs and paraphrases glue, so the screen reports, never blocks.

    The verifier decides support (step 2); the port only tells it where to look.
    """
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析，是核心职能部门",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}])
    assert any(item.kind == "claim" and item.key == "duty" for item in result.semantic_candidate.items)
    advisories = result.producer_attribution["wording_outside_evidence"]
    assert advisories == [{"item_key": "duty", "outside": ["是核心职能"]}]


def test_inferred_wording_beyond_the_passage_is_allowed_when_the_step_is_stated(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "claim", "key": "approval", "meaning": "财务部门可能承担预算审批职责",
         "evidence_class": "INFERRED", "evidence_refs": [evidence_id],
         "uncertainty": "材料只写财务部门负责经营分析，预算审批是按部门职能推断的"}])
    assert any(item.kind == "claim" and item.key == "approval" for item in result.semantic_candidate.items)


def test_the_screen_reports_only_substantive_stretches():
    quotes = ["财务部门负责月度经营分析"]
    # Two-character glue survives a refusal; a three-character category does not.
    assert _unquoted_runs("财务部门负责月度经营分析", quotes) == []
    assert _unquoted_runs("财务部门是核心部门", quotes) == ["是核心部门"]


class _FixtureProvider:
    model = "scope-fixture"

    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "finance", "meaning": "财务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence[0]["evidence_id"]]}]},
            ensure_ascii=False), finish_reason="stop")


def test_the_prompt_states_the_entity_rule_and_the_wording_preference(tmp_path):
    (tmp_path / "business.md").write_text(LINE, encoding="utf-8")
    provider = _FixtureProvider()
    UnderstandPort().understand(
        UnderstandingRequest("prompt-rules", "整理职责", source_refs=(tmp_path / "business.md",),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)
    system = provider.requests[0].messages[0].content
    assert "An entity meaning is the name exactly as one quoted passage writes it" in system
    assert "An entity meaning that the evidence does not spell is refused" in system
    assert "Prefer the source's own wording everywhere else" in system
    assert "at most 64 entities" in system
    assert "A relation's meaning must name both of its endpoints" in system
    assert "sets relation_source to LAYOUT" in system
    assert "put the evidence rows you searched in scope_refs" in system
    assert "recorded as unscoped" in system


def test_the_refusal_reaches_the_agent_with_the_key():
    def refuse(source_ids):
        raise SemanticContractError("entity_name_not_in_evidence", ["finance"])

    context = SimpleNamespace(plugin_services={"understand.execute": refuse}, raise_if_cancelled=lambda: None)
    observation = UnderstandCapabilityAdapter().invoke({"source_ids": ["s1"]}, context)
    assert isinstance(observation, Failure)
    assert observation.error == (
        "understand_proposal_failed:semantic_item_contract_violation:"
        "entity_name_not_in_evidence items=finance")
def _relation_rows(evidence_id, **overrides):
    """Two declared entities and one relation between them, the run-6 shape."""
    relation = {"kind": "relation", "key": "reports",
                "meaning": "财务部门向法务部门报送月度经营分析",
                "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
                "subject": "finance", "predicate": "报送", "object": "legal"}
    relation.update(overrides)
    return [
        {"kind": "entity", "key": "finance", "meaning": "财务部门",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
        {"kind": "entity", "key": "legal", "meaning": "法务部门",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
        relation,
    ]


def test_relation_sentence_that_does_not_name_its_ends_is_dropped(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _relation_rows(evidence_id, meaning="财务部门负责月度经营分析"))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "reports", "rule": "relation_meaning_does_not_join_its_endpoints"}]
    rows = result.semantic_candidate.items
    assert [row.kind for row in rows] == ["entity", "entity", "relation"]
    # The sentence really was on the page: it stays as an unresolved relation whose
    # ends are kept, instead of vanishing with its pair.
    assert rows[-1].evidence_class == "unresolved"
    assert rows[-1].uncertainty == "degraded:relation_meaning_does_not_join_its_endpoints"


def test_relation_sentence_that_names_both_ends_is_accepted(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _relation_rows(evidence_id, subject="@finance"))
    item = next(row for row in result.semantic_candidate.items if row.kind == "relation")
    assert item.relation_source == "TEXT"
    assert item.layout_ref is None


def test_layout_relation_without_a_layout_reference_is_dropped(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _relation_rows(
        evidence_id, relation_source="LAYOUT", evidence_class="INFERRED",
        uncertainty="两部门在汇报线图上相连，材料未成文说明"))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "reports", "rule": "layout_ref_required"}]


def test_layout_relation_may_not_be_presented_as_an_observation(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _relation_rows(
        evidence_id, relation_source="LAYOUT", layout_ref="组织结构图 第3层",
        evidence_class="SOURCE_DIRECT"))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "reports", "rule": "layout_relation_must_be_inferred"}]


def test_layout_relation_is_accepted_as_inferred_and_keeps_its_place(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _relation_rows(
        evidence_id, relation_source="LAYOUT", layout_ref="组织结构图 第3层",
        evidence_class="INFERRED", subject="finance", object="legal",
        uncertainty="两部门在汇报线图上相连，材料未成文说明"))
    item = next(row for row in result.semantic_candidate.items if row.kind == "relation")
    assert item.evidence_class == "inferred"
    assert item.relation_source == "LAYOUT"
    assert item.layout_ref == "组织结构图 第3层"
def _unknown(evidence_id, **overrides):
    row = {"kind": "unknown", "key": "approval", "meaning": "材料是否已获批准，文本未说明。",
           "evidence_class": "UNKNOWN", "evidence_refs": [evidence_id],
           "uncertainty": "材料只写职责分工，未见审批或生效标识"}
    row.update(overrides)
    return [row]


def test_absence_without_a_scope_is_accepted_and_recorded_as_unscoped(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(evidence_id))
    assert result.producer_attribution["absence_without_scope"] == [
        {"item_key": "approval", "kind": "unknown"}]


def test_absence_that_states_its_scope_keeps_both_halves(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(
        evidence_id, scope_refs=[evidence_id], observed_absence="审批"))
    item = next(row for row in result.semantic_candidate.items if row.kind == "unknown")
    assert item.scope_refs == (evidence_id,)
    assert item.observed_absence == "审批"
    assert result.producer_attribution["absence_without_scope"] == []


def test_scope_without_the_phrase_it_looked_for_is_dropped(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(evidence_id, scope_refs=[evidence_id]))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "approval", "rule": "absence_scope_incomplete"}]
    # Half an absence is not an absence: the row is run evidence, named, and no scope
    # without its phrase ever reaches a Wiki as a claim of silence.
    assert list(result.semantic_candidate.items) == []
    diagnostic = {row["key"]: row for row in result.run_diagnostics}["approval"]
    assert diagnostic["missing"] == ["gap_basis"]
    assert diagnostic["uncertainty"] == "degraded:absence_scope_incomplete:scope_without_phrase"


def test_an_absence_phrase_too_long_to_check_is_dropped_and_named(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(
        evidence_id, scope_refs=[evidence_id], observed_absence="审" * 260))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "approval", "rule": "observed_absence_too_long"}]


def test_phrase_without_the_scope_it_searched_is_dropped(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(evidence_id, observed_absence="审批"))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "approval", "rule": "absence_scope_incomplete"}]


def test_absence_its_own_scope_contradicts_is_dropped(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(
        evidence_id, scope_refs=[evidence_id], observed_absence="合同预算"))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "approval", "rule": "absence_contradicted_by_scope"}]


def test_scope_may_only_name_supplied_evidence(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, _unknown(
        evidence_id, scope_refs=["ev_not_supplied"], observed_absence="审批"))
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "approval", "rule": "scope_ref_not_supplied"}]
    # A scope the run never issued cannot be recomputed, so the absence is a question about
    # the reading: it travels in run evidence, with the refusal named.
    assert list(result.semantic_candidate.items) == []
    diagnostic = {row["key"]: row for row in result.run_diagnostics}["approval"]
    assert diagnostic["uncertainty"] == "degraded:scope_ref_not_supplied:kind=unknown"


def test_a_claim_may_not_declare_an_absence_scope(tmp_path):
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, evidence_id, [
        {"kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
         "scope_refs": [evidence_id], "observed_absence": "审批"}])
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "duty", "rule": "absence_scope_not_applicable"}]
    # The scope fields go, the claim stays: a claim is not an absence, but it is still
    # the statement the page made.
    kept = result.semantic_candidate.items
    assert [item.kind for item in kept] == ["claim"]
    assert kept[0].scope_refs == () and kept[0].observed_absence is None

class _RelationProvider:
    """One answer with two sound rows and two relations that break a relation rule."""

    def __init__(self, relation_overrides, *, include_dangling=True):
        self.overrides = relation_overrides
        self.include_dangling = include_dangling
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        evidence_id = evidence[0]["evidence_id"]

        def relation(key, meaning, subject, obj):
            return {"kind": "relation", "key": key, "meaning": meaning,
                    "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
                    "subject": subject, "predicate": "报送", "object": obj}

        items = [
            {"kind": "entity", "key": "finance", "meaning": "财务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
            {"kind": "entity", "key": "legal", "meaning": "法务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
            {"kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
            relation("reports", "财务部门向法务部门报送月度经营分析", "finance", "legal"),
            relation("paraphrase", "财务部门向法务部门报送月度经营分析", "finance", "legal"),
        ]
        if self.include_dangling:
            # Inserted before the paraphrased row so the indices stay stable.
            items.insert(-1, relation("dangling", "财务部门向法务部门报送月度经营分析", "finance", "audit"))
        if self.overrides:
            items[-1].update(self.overrides)
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False), finish_reason="stop")


def test_a_relation_that_breaks_its_own_rule_is_dropped_and_counted(tmp_path):
    """One bad edge must not cost the rows beside it; the count and keys travel."""
    (tmp_path / "business.md").write_text(LINE, encoding="utf-8")
    provider = _RelationProvider({"meaning": "财务部门负责月度经营分析"})
    result = UnderstandPort().understand(
        UnderstandingRequest("drop-relations", "整理职责", source_refs=(tmp_path / "business.md",),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)
    relations = [row for row in result.semantic_candidate.items if row.kind == "relation"]
    assert [row.key for row in relations] == ["reports"]
    dropped = result.producer_attribution["dropped_relations"]
    assert result.producer_attribution["dropped_relation_count"] == 2
    assert {row["item_key"]: row["rule"] for row in dropped} == {
        "dangling": "relation_endpoint_not_declared",
        "paraphrase": "relation_meaning_does_not_join_its_endpoints",
    }
    # The sound rows are untouched.
    assert {"finance", "legal", "duty"} <= {row.key for row in result.semantic_candidate.items}


def test_a_relation_that_points_at_its_own_start_is_dropped_and_counted(tmp_path):
    """A merge whose two ends carry one name is a claim, not an edge onto itself."""
    (tmp_path / "business.md").write_text(LINE, encoding="utf-8")
    provider = _RelationProvider({"subject": "finance", "object": "finance",
                                  "meaning": "财务部门合并为财务部门"}, include_dangling=False)
    result = UnderstandPort().understand(
        UnderstandingRequest("self-relation", "整理职责", source_refs=(tmp_path / "business.md",),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)
    relations = [row for row in result.semantic_candidate.items if row.kind == "relation"]
    assert [row.key for row in relations] == ["reports"]
    assert result.producer_attribution["dropped_relations"] == [
        {"item_key": "paraphrase", "rule": "relation_endpoints_are_the_same_item"}]
    assert {"finance", "legal", "duty"} <= {row.key for row in result.semantic_candidate.items}


def test_a_relation_answer_with_nothing_to_drop_is_not_changed(tmp_path):
    (tmp_path / "business.md").write_text(LINE, encoding="utf-8")
    provider = _RelationProvider({}, include_dangling=False)
    result = UnderstandPort().understand(
        UnderstandingRequest("no-drop", "整理职责", source_refs=(tmp_path / "business.md",),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)
    assert result.producer_attribution["dropped_relation_count"] == 0
    assert len([row for row in result.semantic_candidate.items if row.kind == "relation"]) == 2
