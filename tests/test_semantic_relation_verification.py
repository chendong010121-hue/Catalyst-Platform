"""An edge off a diagram is stored unconfirmed, and a reader can tell it from a sentence.

BKN words a stored relation confirmed or unconfirmed, and a result built on the second is
the one to call 待确认. One deck's 132 relations were 105 read off the layout of a page,
which is a reading of where two names sit and not a sentence that names them both.
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
from catalyst_platform.understand_verify import verification_integrity, verification_local_checks
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, admission_plan
from catalyst_platform.wiki import ProjectWiki


class _OneSaidOneDrawn:
    """One edge the page states in words, one edge read off where the names sit."""

    model = "stub-verification"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        by_quote = {row["quote"]: row["evidence_id"] for row in evidence}
        group, dept, other = (by_quote["水利集团"], by_quote["财务部隶属水利集团"],
                              by_quote["法务部"])
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "jituan", "meaning": "水利集团",
             "business_type": "BusinessUnit", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [group]},
            {"kind": "entity", "key": "caiwu", "meaning": "财务部",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [dept]},
            {"kind": "entity", "key": "fawu", "meaning": "法务部",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [other]},
            {"kind": "relation", "key": "caiwu_in_jituan", "subject": "caiwu",
             "predicate": "隶属", "object": "jituan",
             "meaning": "「财务部」隶属「水利集团」",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [dept, group]},
            {"kind": "relation", "key": "fawu_in_jituan", "subject": "fawu",
             "predicate": "隶属", "object": "jituan",
             "meaning": "「法务部」在版式中列于「水利集团」之下",
             "relation_source": "LAYOUT", "layout_ref": "org.md 版面：法务部置于集团名称之下",
             "evidence_class": "INFERRED", "evidence_refs": [other, group]},
        ]}, ensure_ascii=False), finish_reason="stop")


def _understand(tmp_path, project="verification"):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "org.md"
    source.write_text("水利集团\n财务部隶属水利集团\n法务部", encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [sources], enterprise_id="synthetic",
                       project_id=project)
    result = UnderstandPort().understand(
        UnderstandingRequest(project, "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id=wiki.scope_id,
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=_OneSaidOneDrawn())
    return sources, wiki, result


def _publish(wiki, sources, result, *, with_unconfirmed=False):
    plan = admission_plan(result)
    selected = [row["item_id"] for row in plan["default_adopt"]]
    if with_unconfirmed:
        # The plan holds an edge nobody stated back for a person; publishing it is that
        # person's decision, and the store still records that it is unconfirmed.
        held = {row["item_key"] for row in plan["pending"] if row["reason"] == "relation_not_confirmed"}
        selected += [item.item_id for item in result.semantic_candidate.items
                     if item.kind == "relation" and item.key in held]
    recorder = RunRecorder(JsonlTraceStore(wiki.workspace), run_id="run_verification",
                           request_id="req_verification", invocation_id="inv_verification",
                           trace_id=hashlib.md5(b"verification").hexdigest())
    recorder.start(request_kind="publish_test", actor="local_cli_user", component="CatalystGateway")
    actor = {"verified": True, "simulation": True, "permissions": ("knowledge.propose",),
             "readable_scope_ids": (wiki.scope_id,)}
    return UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), sources).propose_native(
        result, selected_item_ids=selected, actor_context=actor)


def test_the_port_counts_what_a_sentence_says_and_what_a_layout_shows(tmp_path):
    _, _, result = _understand(tmp_path)
    assert result.producer_attribution["relation_verification"] == {"confirmed": 1,
                                                                    "unconfirmed": 1}
    attribution = result.producer_attribution
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    [check] = [row for row in checks if row["rule"] == "layout_relation_unconfirmed"]
    assert check["counts"] == {"confirmed": 1, "unconfirmed": 1}
    assert "待确认" in check["detail"]


def test_the_store_keeps_which_kind_each_edge_is(tmp_path):
    sources, wiki, result = _understand(tmp_path)
    published = _publish(wiki, sources, result, with_unconfirmed=True)
    entries = wiki.semantic_state()["candidates"][published["proposal"]["candidate_id"]]["entries"]
    stored = {entry["predicate"] + ":" + entry["subject"]: entry.get("verification")
              for entry in entries if entry["kind"] == "relation"}
    # One edge the page states in words, one read off where the two names sit.
    assert stored["隶属:@caiwu"] == "confirmed"
    assert stored["隶属:@fawu"] == "unconfirmed"


def test_the_plan_says_how_much_it_carries_each_way(tmp_path):
    _, _, result = _understand(tmp_path)
    plan = admission_plan(result)
    # Read over the candidate, not over what was taken: an unconfirmed edge is held back,
    # and a count of zero would hide how much of the graph still rests on the layout.
    assert plan["relation_verification"] == {"confirmed": 1, "unconfirmed": 1}
    assert {row["item_key"]: row["reason"] for row in plan["pending"]} == {
        "fawu_in_jituan": "relation_not_confirmed"}
    assert [row["item_key"] for row in plan["default_adopt"] if row["kind"] == "relation"] == [
        "caiwu_in_jituan"]
