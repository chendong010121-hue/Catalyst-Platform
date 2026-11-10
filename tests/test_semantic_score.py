"""The thirteen measures read what the Wiki holds, and absence is not quality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from catalyst_platform.semantic_chain import run_chain
from catalyst_platform.semantic_score import score_items, score_wiki, write_report
from catalyst_platform.semantic_wiki import SemanticTransitionError
from catalyst_platform.wiki import ProjectWiki

MATERIAL = (
    "# Quality review\n"
    "Rule: Reviewer checks the package before release\n"
    "relation: reviewer | performs | quality_review\n"
    "condition: quality_review_ready | Package is ready for review\n"
    "exception: month_end_close | A month-end close may release before review\n"
)


def _published(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    material = sources / "responsibility.md"
    material.write_text(MATERIAL, encoding="utf-8")
    review = tmp_path / "review.md"
    review.write_text("# review\nACCEPT\n", encoding="utf-8")
    report = run_chain(workspace=tmp_path / "workspace", source=material, review=review)
    wiki = ProjectWiki((tmp_path / "workspace").resolve(), [sources], enterprise_id="synthetic",
                       project_id="ontology-chain")
    return wiki, report


def _by_id(report: dict) -> dict[int, dict]:
    return {row["id"]: row for row in report["metrics"]}


def test_the_active_version_is_scored_and_its_publication_counts(tmp_path):
    wiki, published = _published(tmp_path)
    report = score_wiki(wiki)
    measured = _by_id(report)

    assert report["target"]["kind"] == "version"
    assert report["target"]["version_id"] == published["version_id"]
    assert report["metric_count"] == 13
    assert measured[1]["value"] == 1.0 and measured[1]["passed"]
    assert measured[4]["passed"] and measured[5]["passed"]
    assert measured[10]["value"] == 1.0 and measured[10]["passed"]
    assert measured[11]["passed"], "a relation whose predicate names an action is an action"


def test_a_candidate_that_never_published_cannot_be_traced(tmp_path):
    wiki, published = _published(tmp_path)
    report = score_wiki(wiki, candidate_id=published["candidate_id"])
    measured = _by_id(report)

    assert report["target"]["kind"] == "candidate"
    assert measured[10]["value"] == 0.0
    assert measured[10]["passed"] is False
    assert "候选" in measured[10]["note"]


def test_an_untyped_orphan_entity_is_what_costs_the_points():
    entries = [
        {"kind": "entity", "key": "pos_a", "canonical_id": "c_a", "meaning": "岗位甲",
         "business_type": "Position", "source_id": "s1", "line_start": 1, "span_sha256": "a"},
        {"kind": "entity", "key": "pos_b", "canonical_id": "c_b", "meaning": "岗位乙",
         "source_id": "s1", "line_start": 2, "span_sha256": "b"},
        {"kind": "relation", "key": "pos_a|隶属", "predicate": "隶属",
         "canonical_subject_id": "c_a", "canonical_object_id": "c_a",
         "subject": "@pos_a", "object": "@pos_a",
         "source_id": "s1", "line_start": 1, "span_sha256": "a"},
    ]
    measured = _by_id(score_items(entries, sources={"s1": "岗位甲\n岗位乙\n"}, target={}))

    assert measured[2]["value"] == 0.5
    assert measured[2]["note"] == "1/2 个实体带概念集内的 business_type"
    assert measured[3]["value"] == 0.5
    assert measured[7]["value"] == 0.5
    assert measured[7]["note"].startswith("1/2")


def test_an_overlong_name_is_not_readable():
    entries = [
        {"kind": "entity", "key": "e1", "meaning": "「（技术副经理）」", "source_id": "s1",
         "line_start": 1, "span_sha256": "a"},
        {"kind": "entity", "key": "e2", "meaning": "entity_" + "x" * 40, "source_id": "s1",
         "line_start": 2, "span_sha256": "b"},
    ]
    measured = _by_id(score_items(entries, sources={"s1": "a\nb\n"}))

    assert measured[9]["value"] == 0.5
    assert measured[9]["passed"] is False


def test_a_line_nobody_covers_is_reported_with_the_ratio():
    entries = [
        {"kind": "entity", "key": "e1", "meaning": "部门", "source_id": "s1",
         "line_start": 2, "span_sha256": "a"},
    ]
    measured = _by_id(score_items(entries, sources={"s1": "# 标题\n部门\n岗位\n"}))

    assert measured[6]["value"] == pytest.approx(0.3333)
    assert measured[6]["passed"] is False
    assert measured[6]["note"].startswith("1/3")


def test_a_metric_with_no_denominator_does_not_pass():
    measured = _by_id(score_items([
        {"kind": "claim", "key": "k", "meaning": "一句陈述", "source_id": "s1",
         "line_start": 1, "span_sha256": "a"},
    ], sources={"s1": "一句陈述\n"}))

    for number in (2, 3, 7, 8, 9):
        assert measured[number]["value"] is None
        assert measured[number]["passed"] is False
    assert measured[1]["passed"] is True


def test_an_unknown_has_to_say_what_is_missing():
    measured = _by_id(score_items([
        {"kind": "unknown", "key": "u1", "meaning": "第 4 页版式未读，箭头关系无法确认",
         "evidence_class": "unresolved", "source_id": "s1", "line_start": 2, "span_sha256": "a"},
        {"kind": "unknown", "key": "u2", "meaning": "",
         "evidence_class": "unresolved", "source_id": "s1", "line_start": 3, "span_sha256": "b"},
    ], sources={"s1": "# 标题\n第 4 页\n"}))

    assert measured[8]["value"] == 0.5
    assert measured[8]["passed"] is False


def test_a_version_that_was_never_accepted_cannot_be_scored(tmp_path):
    wiki, _ = _published(tmp_path)

    with pytest.raises(SemanticTransitionError) as raised:
        score_wiki(wiki, version_id="version_missing")
    assert raised.value.code == "accepted_version_not_found"


def test_the_report_is_written_as_utf8_json(tmp_path):
    wiki, _ = _published(tmp_path)
    report = score_wiki(wiki)
    path = write_report(report, tmp_path / "score.json")

    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    assert saved["schema"] == "catalyst.ontology_score.v0.1"
    assert saved["passed"] == report["passed"]
