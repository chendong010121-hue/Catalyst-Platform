"""An absence is published with the places it searched.

A page that says 本页未说明 is stating what it looked at, not what the material holds. The store
kept the sentence and threw the scope away, so the card read as a statement about the whole deck -
and a reviewer could not tell that a neighbouring page states the thing.
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
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, admission_plan
from catalyst_platform.wiki import ProjectWiki


class _AbsenceAndAClaim:
    """One absence scoped to the page, and one claim that quotes the page."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "claim", "key": "finance_duty", "meaning": "「财务部门负责月度经营分析」",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
            {"kind": "unknown", "key": "approval_absent",
             "meaning": "本页未说明财务部门的审批权限",
             "evidence_class": "UNKNOWN", "evidence_refs": [evidence],
             "scope_refs": [evidence], "observed_absence": "审批权限"},
        ]}, ensure_ascii=False), finish_reason="stop")


def _publish(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "duties.md"
    source.write_text("财务部门负责月度经营分析。\n", encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [sources], enterprise_id="synthetic",
                       project_id="absence-scope")
    result = UnderstandPort().understand(
        UnderstandingRequest("absence-scope", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id=wiki.scope_id,
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=_AbsenceAndAClaim())
    plan = admission_plan(result)
    selected = [row["item_id"] for row in plan["default_adopt"]]
    recorder = RunRecorder(JsonlTraceStore(wiki.workspace), run_id="run_absence",
                           request_id="req_absence", invocation_id="inv_absence",
                           trace_id=hashlib.md5(b"absence").hexdigest())
    recorder.start(request_kind="publish_test", actor="local_cli_user", component="CatalystGateway")
    actor = {"verified": True, "simulation": True, "permissions": ("knowledge.propose",),
             "readable_scope_ids": (wiki.scope_id,)}
    published = UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), sources).propose_native(
        result, selected_item_ids=selected, actor_context=actor)
    entries = wiki.semantic_state()["candidates"][published["proposal"]["candidate_id"]]["entries"]
    return result, {entry.get("key"): entry for entry in entries}


def test_an_absence_is_published_with_the_places_it_searched(tmp_path):
    _, entries = _publish(tmp_path)
    absence = entries["approval_absent"]
    # The wording that was missing and where it was looked for, in the same row.
    assert absence["absence"] == "审批权限"
    assert absence["searched"] == ["line:1"]


def test_a_claim_carries_no_absence_fields(tmp_path):
    _, entries = _publish(tmp_path)
    claim = entries["finance_duty"]
    # An absence belongs to the row that searched; a claim states what the page says.
    assert "absence" not in claim
    assert "searched" not in claim
