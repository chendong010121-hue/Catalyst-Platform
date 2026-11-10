"""A row says which chart its page drew, and the store keeps that word.

One deck printed the organisation as it stands on one page and the one it proposes on the
next, so 市场营销中心 and 营销中心, 工程管理中心 and 工程中心 arrived as four identities of
two organisations. The page's own heading says which is which; a row copied from that page
carries it, and nothing else does.
"""
from __future__ import annotations

import hashlib
import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_semantic import semantic_extraction_rules
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, admission_plan
from catalyst_platform.wiki import ProjectWiki


class _TwoCharts:
    """One current chart and one proposed, each row labelled from its own page."""

    model = "stub-two-charts"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        by_quote = {row["quote"]: row["evidence_id"] for row in evidence}
        now, later = by_quote["营销中心"], by_quote["市场营销中心"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "yingxiao_zhongxin", "meaning": "营销中心",
             "business_type": "Department", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [now]},
            {"kind": "entity", "key": "shichang_yingxiao", "meaning": "市场营销中心",
             "business_type": "Department", "scope_state": "proposed",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [later]},
            {"kind": "claim", "key": "yingxiao_duty", "meaning": "营销中心负责市场开发",
             "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [now]},
        ]}, ensure_ascii=False), finish_reason="stop")


def _source(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "org.md"
    source.write_text("营销中心\n市场营销中心", encoding="utf-8")
    return sources, source


def _understand(tmp_path, provider):
    sources, source = _source(tmp_path)
    return sources, UnderstandPort().understand(
        UnderstandingRequest("two-charts", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_two_charts",
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=provider)


def test_a_page_word_survives_onto_the_published_entity(tmp_path):
    sources, result = _understand(tmp_path, _TwoCharts())
    states = {item.key: item.scope_state for item in result.semantic_candidate.items
              if item.kind == "entity"}
    assert states == {"yingxiao_zhongxin": "current", "shichang_yingxiao": "proposed"}
    assert result.producer_attribution["scope_states"]["current"] == 1
    assert result.producer_attribution["scope_states"]["proposed"] == 1
    # A claim carries no state of its own: the field is dropped and counted, never fatal.
    assert result.producer_attribution["dropped_invalid_items"]["scope_state_not_applicable"] == 1

    wiki = ProjectWiki(tmp_path / "workspace", [sources], enterprise_id="synthetic",
                       project_id="scope-state")
    result = UnderstandPort().understand(
        UnderstandingRequest("two-charts", "整理组织", source_refs=(sources / "org.md",),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id=wiki.scope_id,
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=_TwoCharts())
    plan = admission_plan(result)
    selected = [row["item_id"] for row in plan["default_adopt"]]
    recorder = RunRecorder(JsonlTraceStore(wiki.workspace), run_id="run_scope_state",
                           request_id="req_scope_state", invocation_id="inv_scope_state",
                           trace_id=hashlib.md5(b"scope-state").hexdigest())
    recorder.start(request_kind="publish_test", actor="local_cli_user", component="CatalystGateway")
    actor = {"verified": True, "simulation": True, "permissions": ("knowledge.propose",),
             "readable_scope_ids": (wiki.scope_id,)}
    published = UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), sources).propose_native(
        result, selected_item_ids=selected, actor_context=actor)
    entries = wiki.semantic_state()["candidates"][published["proposal"]["candidate_id"]]["entries"]
    stored = {entry["canonical_key"]: entry.get("scope_state") for entry in entries
              if entry["kind"] == "entity"}
    assert stored == {"yingxiao_zhongxin": "current", "shichang_yingxiao": "proposed"}


def test_a_word_the_page_never_said_is_dropped_and_the_row_stays(tmp_path):
    class _Draft(_TwoCharts):
        def request(self, request):
            answer = json.loads(super().request(request).content)
            answer["items"][0]["scope_state"] = "draft"
            return ModelResponse(content=json.dumps(answer, ensure_ascii=False), finish_reason="stop")

    _, result = _understand(tmp_path, _Draft())
    kept = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    assert kept == {"yingxiao_zhongxin", "shichang_yingxiao"}
    assert result.producer_attribution["dropped_invalid_items"]["scope_state_unsupported"] == 1
    assert result.producer_attribution["scope_states"] == {"current": 0, "proposed": 1,
                                                           "unlabelled": 1}


def test_the_same_name_on_both_charts_stays_two_rows(tmp_path):
    class _SameNameTwice(_TwoCharts):
        def request(self, request):
            evidence = json.loads(request.messages[-1].content)["evidence"]
            by_quote = {row["quote"]: row["evidence_id"] for row in evidence}
            now, later = by_quote["营销中心"], by_quote["市场营销中心"]
            return ModelResponse(content=json.dumps({"items": [
                {"kind": "entity", "key": "yingxiao_now", "meaning": "营销中心",
                 "business_type": "Department", "scope_state": "current",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [now]},
                {"kind": "entity", "key": "yingxiao_later", "meaning": "营销中心",
                 "business_type": "Department", "scope_state": "proposed",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [later]},
            ]}, ensure_ascii=False), finish_reason="stop")

    _, result = _understand(tmp_path, _SameNameTwice())
    rows = {item.key: item.scope_state for item in result.semantic_candidate.items
            if item.kind == "entity"}
    # One name, two charts: folding them would answer the question the deck asks.
    assert rows == {"yingxiao_now": "current", "yingxiao_later": "proposed"}
    assert result.producer_attribution["merged_duplicate_entities"] == []


def test_the_contract_asks_for_the_page_word_and_nothing_else():
    rules = semantic_extraction_rules()
    assert "carries scope_state: current or proposed" in rules
    assert "the field is the page's word, never your guess" in rules
