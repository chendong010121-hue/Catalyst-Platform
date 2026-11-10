"""The structure channel: a hierarchy read from the connections a page draws.

An org chart says its structure twice — in the words of its boxes and in the lines between
them. These checks pin the second reading: one cell per connection with the page's own
address, which end sits above which, category bands stepped through rather than obeyed, a
page's declared state carried as a cell, and every relation the drawing does not support
handed back as a question with its locators, never as an assertion.
"""
import json
import zipfile

import pytest

from types import SimpleNamespace

from catalyst_platform import understand_structure as structure
from catalyst_platform.understand_models import GroundedItem
from catalyst_platform.understand_semantic import _structure_relations
from catalyst_platform.understand_route import choose_channels
from catalyst_platform.understand_sources import _extract

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def box(shape_id, text, y, *, x=0, width=200, height=40, placeholder=None):
    placeholder_xml = f'<p:ph type="{placeholder}"/>' if placeholder else ""
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="box{shape_id}"/><p:nvPr>'
            f"{placeholder_xml}</p:nvPr></p:nvSpPr>"
            f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{width}" cy="{height}"/></a:xfrm></p:spPr>'
            f'<p:txBody><a:bodyPr/><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>')


def titled(shape_id, text, y):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="title"/><p:nvPr>'
            f'<p:ph type="title"/></p:nvPr></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="0" y="{y}"/><a:ext cx="600" cy="40"/></a:xfrm></p:spPr>'
            f'<p:txBody><a:bodyPr/><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>')


def line(connector_id, start, end):
    return (f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{connector_id}" name="连接符 {connector_id}"/>'
            f'<p:cNvCxnSpPr><a:stCxn id="{start}" idx="0"/><a:endCxn id="{end}" idx="0"/></p:cNvCxnSpPr>'
            f"<p:nvPr/></p:nvCxnSpPr>"
            f'<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="10" cy="10"/></a:xfrm></p:spPr></p:cxnSp>')


def deck(tmp_path, body, name="deck.pptx"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as package:
        package.writestr(
            "ppt/slides/slide1.xml",
            f'<p:sld xmlns:p="{_P}" xmlns:a="{_A}"><p:cSld><p:spTree>'
            f"<p:nvGrpSpPr/><p:grpSpPr/>{body}</p:spTree></p:cSld></p:sld>")
    return path


def org_chart(tmp_path, *, title="水利集团现有组织结构：", same_row=False):
    """集团 over 经理层 over the 中台部门 column over one department."""
    y_department = 300
    y_line = 300 if same_row else 300
    body = "".join([
        titled(1, title, 0),
        box(2, "天津市水利工程集团有限公司", 40, x=100),
        box(3, "经理层", 100, x=100),
        box(4, "中台部门", 160, x=100),
        box(5, "市场营销中心", y_department if not same_row else 160, x=100),
        line(6, 4, 5),
        line(7, 3, 4),
        line(8, 2, 3),
    ])
    return deck(tmp_path, body)


def test_a_drawn_connection_is_a_cell_of_its_own(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    cells = [unit for unit in units if "#cxn:" in unit.locator]
    assert [unit.locator for unit in cells] == [
        "ppt/slides/slide1.xml#cxn:1", "ppt/slides/slide1.xml#cxn:2", "ppt/slides/slide1.xml#cxn:3"]
    body = json.loads(cells[0].quote)
    assert body["parent"] == 0                      # 中台部门 is the upper box on the page
    assert [end["text"] for end in body["ends"]] == ["中台部门", "市场营销中心"]
    assert body["ends"][1]["locator"] == "ppt/slides/slide1.xml#shape:5"
    assert body["basis"] == "page_vertical"
    assert cells[0].unit_kind == "structure" and cells[0].role == "connector"


def test_a_page_states_which_state_it_shows(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    state = next(unit for unit in units if unit.locator.endswith("#state"))
    assert json.loads(state.quote) == {"title": "水利集团现有组织结构：", "declares": "current"}
    assert structure.page_states(units) == {"ppt/slides/slide1.xml": "current"}


def test_a_band_is_stepped_through_not_obeyed(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    claims = structure.claims(structure.drawn_edges(units), structure.page_states(units))
    pairs = {(claim.child, claim.parent) for claim in claims}
    assert ("市场营销中心", "天津市水利工程集团有限公司") in pairs
    assert ("市场营销中心", "中台部门") not in pairs      # a column heading is not a superior
    assert ("市场营销中心", "经理层") not in pairs        # neither is a management layer


def test_two_boxes_on_one_row_state_no_hierarchy(tmp_path):
    units, _ = _extract(org_chart(tmp_path, same_row=True), "deck.pptx", "s1", "r1")
    edges = structure.drawn_edges(units)
    assert [edge.basis for edge in edges] == ["same_row", "page_vertical", "page_vertical"]
    pairs = {(claim.child, claim.parent) for claim in structure.claims(edges, {})}
    # The two boxes share a row, so the page states no hierarchy between them.
    assert ("市场营销中心", "中台部门") not in pairs
    assert ("市场营销中心", "天津市水利工程集团有限公司") not in pairs


def test_a_connection_to_an_unlabelled_box_is_kept_and_named(tmp_path):
    body = "".join([
        titled(1, "水利集团现有组织结构：", 0),
        box(2, "经理层", 40, x=100),
        box(3, "", 100, x=100),          # a box with no words: no cell of its own
        line(4, 2, 3),
    ])
    units, _ = _extract(deck(tmp_path, body), "deck.pptx", "s1", "r1")
    cell = next(unit for unit in units if "#cxn:" in unit.locator)
    assert json.loads(cell.quote)["basis"] == "unnamed_end"
    assert structure.claims(structure.drawn_edges(units), {}) == ()


def _relation(subject, object_, locator="ppt/slides/slide1.xml#shape:5"):
    return {"item_id": "item_1", "kind": "relation", "subject": subject, "object": object_,
            "evidence_refs": ["ev_1"]}


def test_a_relation_into_a_band_is_refused_and_asked(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    findings = structure.relation_findings(
        [_relation("市场营销中心", "中台部门")], units,
        names={}, locators={"ev_1": "ppt/slides/slide1.xml#shape:5"})
    assert [finding.verdict for finding in findings] == ["band_parent"]
    assert "分类列标题" in findings[0].why
    assert findings[0].question and "上级" in findings[0].question


def test_a_relation_the_page_draws_is_kept_with_its_connection(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    findings = structure.relation_findings(
        [_relation("市场营销中心", "天津市水利工程集团有限公司")], units,
        names={}, locators={"ev_1": "ppt/slides/slide1.xml#shape:5"})
    assert [finding.verdict for finding in findings] == ["drawn_through"]
    assert "#cxn:" in " ".join(findings[0].locators)
    assert findings[0].question and "压平" in findings[0].question


def test_a_relation_no_page_draws_is_asked_with_its_locators(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    findings = structure.relation_findings(
        [_relation("市场营销中心", "企管部")], units,
        names={}, locators={"ev_1": "ppt/slides/slide1.xml#shape:5"})
    assert [finding.verdict for finding in findings] == ["undrawn"]
    assert "没有画出连线" in findings[0].question
    assert findings[0].locators == ("ppt/slides/slide1.xml#shape:5",)


def test_a_page_that_declares_no_state_only_asks(tmp_path):
    units, _ = _extract(org_chart(tmp_path, title="水利集团组织架构："), "deck.pptx", "s1", "r1")
    findings = structure.relation_findings(
        [_relation("市场营销中心", "天津市水利工程集团有限公司")], units,
        names={}, locators={"ev_1": "ppt/slides/slide1.xml#shape:5"})
    assert [finding.verdict for finding in findings] == ["unstated_state"]
    assert "没说" in findings[0].question


def test_a_bracketed_second_name_is_an_alias_not_a_second_thing():
    assert structure.split_alias("技术研发中心（质量技术部）") == ("技术研发中心", "质量技术部")
    assert structure.split_alias("市场营销中心") == ("市场营销中心", None)


def test_channels_follow_the_probe_not_the_model_name(tmp_path):
    record = {"schema_version": 1, "model": "m", "base_url": "https://example",
              "probed_at": "2026-11-01T00:00:00Z", "prompt": "p", "answer_expected": "右下",
              "answer": "右下", "passed": True, "total_tokens": 200}
    seen = choose_channels(model="m", structure_cells=12, raster_pages=2, vision_record=record)
    assert seen.structure and seen.vision and seen.questions
    unseen = choose_channels(model="m", structure_cells=12, raster_pages=2, vision_record=None)
    assert unseen.structure and not unseen.vision and unseen.questions
    assert "识图探针" in unseen.reason
    text_only = choose_channels(model="m", structure_cells=12, raster_pages=0, vision_record=record)
    assert text_only.structure and not text_only.vision
    failed = dict(record, passed=False)
    assert not choose_channels(model="m", structure_cells=0, raster_pages=1, vision_record=failed).vision


def _entity(key, meaning, evidence="ev_0"):
    return GroundedItem(item_id=f"item_{key}", kind="entity", key=key, meaning=meaning,
                        evidence_refs=(evidence,), evidence_class="observed_from_source",
                        confidence="source_anchored_not_truth")


def test_the_drawing_writes_the_edges_it_states(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    refs = [SimpleNamespace(evidence_id=f"ev_{index}", locator=unit.locator, quote=unit.quote)
            for index, unit in enumerate(units)]
    entities = [_entity("jituan", "天津市水利工程集团有限公司"),
                _entity("yingxiao", "市场营销中心")]
    rows, report = _structure_relations(entities, refs, "req-1")
    assert report["added"] == 1
    row = rows[0]
    assert (row.subject, row.predicate, row.object) == ("yingxiao", "隶属", "jituan")
    assert row.meaning == "市场营销中心 隶属 天津市水利工程集团有限公司"
    assert row.relation_source == "LAYOUT" and row.scope_state == "current"
    # The row cites the page it was read from, never a quote it invented.
    assert row.evidence_refs and all(ref.startswith("ev_") for ref in row.evidence_refs)
    assert all(any(ref == item.evidence_id and ref in row.evidence_refs for item in refs)
               for ref in row.evidence_refs)
    # An edge the candidate already holds is never written twice.
    again, second = _structure_relations(entities + rows, refs, "req-1")
    assert (again, second["added"]) == ([], 0)
    assert second["skipped"] == 1


def test_an_edge_to_a_name_the_candidate_lacks_is_not_invented(tmp_path):
    units, _ = _extract(org_chart(tmp_path), "deck.pptx", "s1", "r1")
    refs = [SimpleNamespace(evidence_id=f"ev_{index}", locator=unit.locator, quote=unit.quote)
            for index, unit in enumerate(units)]
    rows, report = _structure_relations([_entity("yingxiao", "市场营销中心")], refs, "req-2")
    assert rows == [] and report["skipped"] == 1
