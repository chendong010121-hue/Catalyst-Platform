"""一页自己说明它是现状还是方案，它的行就继承这句话。

抽取规则一直写着「a row taken from such a page carries scope_state」，但六张冻结卡
296 条里一条都没有：规则对，却没人把它落成动作。这里落成两步——

1. 页面自己的字先判这一页是哪一态（`_page_scope_state`，纯函数、可复现、不猜）；
2. 判定随请求交给模型，没回答的行由端口补上（`_inherit_scope_state`）。

页面什么都没说、或两态都说，就不判、不填——猜出来的状态比空的更坏。
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_semantic import _inherit_scope_state, _page_scope_state


def test_a_page_saying_it_is_the_current_arrangement_names_its_state():
    assert _page_scope_state(["水利集团现有组织结构："]) == ("current", "现有")
    assert _page_scope_state(["目前的分工"]) == ("current", "目前")


def test_a_page_saying_it_is_a_proposal_names_its_state():
    assert _page_scope_state(["组织机构调整方案"]) == ("proposed", "调整")
    assert _page_scope_state(["整合后的前台部门"]) == ("proposed", "整合后")


def test_a_page_saying_both_or_neither_stays_unlabelled():
    assert _page_scope_state(["现有组织结构", "调整方案"]) == (None, None)
    assert _page_scope_state(["财务部门负责月度经营分析"]) == (None, None)
    assert _page_scope_state([]) == (None, None)


def test_a_heading_outranks_the_body_it_sits_above():
    """A current-state page says 「调整生产关系」 in the paragraph under its title.

    Reading the whole page would find both states and refuse to decide; the heading is
    where the page says which of the two it draws.
    """
    quotes = ["水利集团现有组织结构：", "天津市水利工程集团有限公司", "党委会", "董事会", "监事会",
              "二、主要问题（调整生产关系激发生产力）："]
    assert _page_scope_state(quotes) == ("current", "现有")


def test_inheritance_fills_only_rows_that_said_nothing():
    rows = [
        {"kind": "entity", "key": "finance"},
        {"kind": "claim", "key": "duty"},
        {"kind": "entity", "key": "legal", "scope_state": "proposed"},
    ]
    assert _inherit_scope_state(rows, "current") == 1
    assert [row.get("scope_state") for row in rows] == ["current", None, "proposed"]


class _Rows:
    """One answer per unit, built from the evidence ids the port actually supplied."""

    model = "stub-scope-inheritance"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build
        self.notes: list[str] = []

    def request(self, request):
        self.notes.append(request.messages[0].content)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _run(tmp_path, text, build):
    source = tmp_path / "deck.md"
    source.write_text(text, encoding="utf-8")
    provider = _Rows(build)
    result = UnderstandPort().understand(
        UnderstandingRequest("scope-inheritance", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_inherit",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=provider)
    return result, provider


def _entity(meaning, evidence):
    """The row cites the line that spells the name, not merely the first line of the page."""
    row = next(item for item in evidence if meaning in item["quote"])
    return {"kind": "entity", "key": "finance", "meaning": meaning,
            "evidence_class": "SOURCE_DIRECT", "evidence_refs": [row["evidence_id"]]}


def test_a_current_page_reaches_the_card_with_the_state_its_own_wording_declared(tmp_path):
    result, provider = _run(tmp_path, "水利集团现有组织结构：\n财务部门\n",
                            lambda evidence: [_entity("财务部门", evidence)])
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    assert entity.scope_state == "current"
    inherited = result.producer_attribution["scope_state_inheritance"]
    assert [{k: row[k] for k in ("scope_state", "word", "filled")} for row in inherited] == [
        {"scope_state": "current", "word": "现有", "filled": 1}]
    assert result.producer_attribution["scope_state_inherited_count"] == 1
    # The model is told which word did it, so it is not guessing beside the reader.
    assert "so the page is read as current" in provider.notes[0]


def test_a_page_whose_rows_answer_for_themselves_is_still_listed_as_decided(tmp_path):
    """What a live card looks like: the note works and the backstop has nothing left to do.

    Listing only the filled rows would read as "this page said nothing", which is the
    opposite of what happened, so the unit is listed with what its answer declared.
    """
    def build(evidence):
        row = _entity("财务部门", evidence)
        return [{**row, "scope_state": "current"}]

    result, _ = _run(tmp_path, "水利集团现有组织结构：\n财务部门\n", build)
    inherited = result.producer_attribution["scope_state_inheritance"]
    assert [{k: row[k] for k in ("scope_state", "word", "carried", "filled")} for row in inherited] == [
        {"scope_state": "current", "word": "现有", "carried": 1, "filled": 0}]
    assert result.producer_attribution["scope_state_inherited_count"] == 0
    assert result.producer_attribution["scope_state_carried_count"] == 1


def test_in_a_deck_of_many_units_each_page_decides_only_its_own_rows(tmp_path):
    """Long sources are extracted one unit at a time; a live card always takes this path.

    The second page says nothing about itself, so its entity is left unlabelled even
    though the first page of the same source declared a state.
    """
    # One unit is forty lines; the first page keeps its heading and its entity, the
    # second page starts past the boundary and says nothing about itself.
    lines = ["水利集团现有组织结构："] + [f"备注说明{i}" for i in range(1, 37)]
    lines += ["财务部门", "备注收尾", "水厂运行部负责供水调度", "水厂运行部", ""]
    text = "\n".join(lines)

    def build(evidence):
        quotes = "".join(item["quote"] for item in evidence)
        rows = []
        for key, name in (("finance", "财务部门"), ("water", "水厂运行部")):
            if name in quotes:
                rows.append({"kind": "entity", "key": key, "meaning": name,
                             "evidence_class": "SOURCE_DIRECT",
                             "evidence_refs": [item["evidence_id"] for item in evidence
                                               if name in item["quote"]]})
        return rows

    result, provider = _run(tmp_path, text, build)
    attribution = result.producer_attribution
    assert attribution["extraction_units"] == 2
    assert len(provider.notes) == 2
    assert [{k: row[k] for k in ("unit", "scope_state", "filled")}
            for row in attribution["scope_state_inheritance"]] == [
        {"unit": "lines:0", "scope_state": "current", "filled": 1}]
    states = {item.key: item.scope_state for item in result.semantic_candidate.items
              if item.kind == "entity"}
    assert states == {"finance": "current", "water": None}


def test_a_page_and_its_rows_both_silent_stay_unlabelled(tmp_path):
    result, provider = _run(tmp_path, "财务部门\n法务部门\n",
                            lambda evidence: [_entity("财务部门", evidence)])
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    assert entity.scope_state is None
    assert result.producer_attribution["scope_state_inheritance"] == []
    assert "so the page is read as" not in provider.notes[0]
