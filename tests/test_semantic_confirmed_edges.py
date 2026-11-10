"""An edge is confirmed only when the passage says that relation, not that it changes.

A deck writes a change as a change: 综合办公室…分为行政服务办公室、党委办公室、纪检室三个部门,
整合投资管理中心、市场营销中心，设置为市场营销中心. Read as a standing edge, the first says the
three new departments sit under the office they were split out of, and the second says one centre
sits under the centre it merged into. Both are the reverse of what the page states, and live37
stored four such edges as confirmed.
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
from catalyst_platform.understand_semantic import states_its_relation
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, admission_plan
from catalyst_platform.wiki import ProjectWiki

SPLIT = "综合办公室根据工作性质的差异，界定职责，分为行政服务办公室、党委办公室、纪检室三个部门"
MERGE = "整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部、投资管理部"


def test_a_split_sentence_does_not_state_a_membership():
    # 党委办公室 is what the office becomes, not what sits under it.
    assert states_its_relation("隶属", SPLIT, ("党委办公室", "综合办公室")) is False
    assert states_its_relation("隶属", SPLIT, ("纪检室", "综合办公室")) is False


def test_a_merge_sentence_does_not_state_a_membership():
    assert states_its_relation("隶属", MERGE, ("投资管理中心", "市场营销中心")) is False


def test_the_word_this_deck_uses_still_states_one():
    # 下设 does name a member, and the list after it is one clause, three members.
    for member in ("招投标部", "策划部", "投资管理部"):
        assert states_its_relation("隶属", MERGE, (member, "市场营销中心")) is True


def test_a_change_is_not_a_production():
    # 设置为 states what the merged centre becomes, not what a step produced.
    assert states_its_relation("产出", MERGE, ("中台调整", "市场营销中心")) is False
    assert states_its_relation("产出", "技术研发中心产出质量报告", ("技术研发中心", "质量报告")) is True


class _SplitReadAsMembership:
    model = "stub-confirmed"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        quote = {row["quote"]: row["evidence_id"] for row in evidence}[SPLIT]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "zonghe", "meaning": "综合办公室",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [quote]},
            {"kind": "entity", "key": "jiwei", "meaning": "纪检室",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [quote]},
            {"kind": "relation", "key": "@jiwei|隶属", "subject": "jiwei",
             "predicate": "隶属", "object": "zonghe",
             "meaning": "「纪检室」隶属「综合办公室」",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [quote]},
        ]}, ensure_ascii=False), finish_reason="stop")


def _card(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "org.md"
    source.write_text(SPLIT, encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [sources], enterprise_id="synthetic",
                       project_id="confirmed")
    result = UnderstandPort().understand(
        UnderstandingRequest("confirmed", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id=wiki.scope_id,
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=_SplitReadAsMembership())
    return sources, wiki, result


def _publish(wiki, sources, result, *, selected=None):
    plan = admission_plan(result)
    if selected is None:
        selected = [row["item_id"] for row in plan["default_adopt"]]
    recorder = RunRecorder(JsonlTraceStore(wiki.workspace), run_id="run_confirmed",
                           request_id="req_confirmed", invocation_id="inv_confirmed",
                           trace_id=hashlib.md5(b"confirmed").hexdigest())
    recorder.start(request_kind="publish_test", actor="local_cli_user", component="CatalystGateway")
    actor = {"verified": True, "simulation": True, "permissions": ("knowledge.propose",),
             "readable_scope_ids": (wiki.scope_id,)}
    return UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), sources).propose_native(
        result, selected_item_ids=selected, actor_context=actor)


def test_the_port_counts_a_change_read_as_a_membership_as_unconfirmed(tmp_path):
    _, _, result = _card(tmp_path)
    assert result.producer_attribution["relation_verification"] == {"confirmed": 0,
                                                                    "unconfirmed": 1}


def test_an_edge_nobody_stated_is_not_adopted_by_default(tmp_path):
    _, _, result = _card(tmp_path)
    plan = admission_plan(result)
    assert plan["relation_verification"] == {"confirmed": 0, "unconfirmed": 1}
    # The entities are still taken; only the edge waits, and it waits with a reason.
    assert [row["item_key"] for row in plan["default_adopt"] if row["kind"] == "entity"] == [
        "zonghe", "jiwei"]
    assert not [row for row in plan["default_adopt"] if row["kind"] == "relation"]
    assert {row["item_key"]: row["reason"] for row in plan["pending"]} == {
        "jiwei": "relation_not_confirmed"}


def test_an_owner_can_publish_it_and_the_store_says_unconfirmed(tmp_path):
    sources, wiki, result = _card(tmp_path)
    kept = [item.item_id for item in result.semantic_candidate.items]
    published = _publish(wiki, sources, result, selected=kept)

    entries = wiki.semantic_state()["candidates"][published["proposal"]["candidate_id"]]["entries"]
    stored = {entry["subject"]: entry.get("verification")
              for entry in entries if entry["kind"] == "relation"}
    assert stored == {"@jiwei": "unconfirmed"}
    # The downgrade is named in the report rather than left to a re-reading of the card.
    assert published["unconfirmed_relations"] == [
        {"item_key": "jiwei", "rule": "relation_reads_a_change"}]
