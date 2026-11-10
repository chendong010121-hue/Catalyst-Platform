"""A re-reading that models part of a document must not delete the rest of it.

Sparse reconciliation is the rule behind that sentence: an accepted meaning this source still
states, but which the candidate never mentions, is carried into the new version — and only
when its own line is still there, byte for byte.
"""
from __future__ import annotations

import hashlib
import json

from pathlib import Path

from catalyst_platform.semantic_wiki import SemanticWiki, _merge_candidate_meanings
from catalyst_platform.wiki_pages import project

LINE_A = "市场营销中心负责年度预算。"
LINE_B = "总部负责审批重大合同。"
LINE_C = "法务风控部负责合规审查。"


def sha(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def content(*lines: str) -> str:
    return "# 说明\n" + "\n".join(lines) + "\n"


class FakeWiki:
    """Only what sparse reconciliation reads: one source snapshot and its revision."""

    def __init__(self, body: str, revision: str = "rev-new"):
        self._body = body
        self._revision = revision
        self.workspace = Path(".")
        self.roots = ()

    def source_snapshot(self, source_id):  # noqa: ARG002
        return {"current_revision": self._revision, "content": self._body}


def meaning(meaning_id: str, text: str, line_start: int, span: str, *, revision: str = "rev-old"):
    return {
        "meaning_id": meaning_id, "kind": "entity", "key": meaning_id, "meaning": text,
        "canonical_key": meaning_id, "canonical_id": f"canonical:{meaning_id}",
        "freshness_status": "fresh",
        "evidence": [{
            "source_id": "source_a", "source_revision": revision, "line_start": line_start,
            "line_end": line_start, "span_sha256": span, "evidence_class": "observed_from_source",
        }],
    }


def parent_meanings():
    return {
        "m_a": meaning("m_a", "市场营销中心", 2, sha(LINE_A)),
        "m_b": meaning("m_b", "总部", 3, sha(LINE_B)),
        "m_c": meaning("m_c", "法务风控部", 4, sha(LINE_C)),
    }


def candidate(entries, *, revision="rev-new"):
    return {"source_id": "source_a", "source_revision": revision, "entries": entries}


def entry(meaning_id: str, text: str):
    return {
        "meaning_id": meaning_id, "kind": "entity", "key": meaning_id, "meaning": text,
        "canonical_key": meaning_id, "canonical_id": f"canonical:{meaning_id}",
        "source_id": "source_a", "source_revision": "rev-new", "line_start": 4,
        "line_end": 4, "span_sha256": sha(LINE_C), "evidence_class": "observed_from_source",
    }


def service(body: str) -> SemanticWiki:
    return SemanticWiki(FakeWiki(body), recorder=object(), recover_pending=False)


def test_a_sparse_candidate_keeps_what_it_did_not_mention():
    wiki = service(content(LINE_A, LINE_B, LINE_C))
    carried = wiki._carry_confirmed_by_absence(
        parent_meanings(), candidate([entry("m_c", "法务风控部")]))

    assert set(carried) == {"m_a", "m_b"}
    assert all(row["confirmed_by_absence"] is True for row in carried.values())
    assert all(row["confirmed_at_source_revision"] == "rev-new" for row in carried.values())


def test_a_carried_meaning_points_at_the_line_that_still_holds_its_text():
    # Three lines inserted above: the text is at line 5 now, and the carried evidence says so.
    wiki = service(content("新增一", "新增二", "新增三", LINE_A, LINE_B, LINE_C))
    carried = wiki._carry_confirmed_by_absence(
        parent_meanings(), candidate([entry("m_c", "法务风控部")]))

    assert carried["m_a"]["evidence"][0]["line_start"] == 5
    assert carried["m_a"]["evidence"][0]["source_revision"] == "rev-new"


def test_a_meaning_whose_text_is_gone_is_not_carried():
    # The document really dropped 总部: not mentioning it is not the same as still saying it.
    wiki = service(content(LINE_A, LINE_C))
    carried = wiki._carry_confirmed_by_absence(
        parent_meanings(), candidate([entry("m_c", "法务风控部")]))

    assert "m_b" not in carried
    assert "m_a" in carried


def test_a_meaning_the_candidate_mentions_is_not_carried():
    wiki = service(content(LINE_A, LINE_B, LINE_C))
    carried = wiki._carry_confirmed_by_absence(
        parent_meanings(), candidate([entry("m_a", "市场营销中心"), entry("m_c", "法务风控部")]))

    assert "m_a" not in carried
    assert "m_b" in carried


def test_the_merge_keeps_carried_meanings_and_adds_the_new_ones(tmp_path):
    before = parent_meanings()
    carried = service(content(LINE_A, LINE_B, LINE_C))._carry_confirmed_by_absence(
        before, candidate([entry("m_c", "法务风控部")]))
    new_entry = {**entry("m_d", "工程管理部"), "span_sha256": sha("工程管理部负责施工。")}

    merged = _merge_candidate_meanings(before, candidate([entry("m_c", "法务风控部"), new_entry]),
                                       carried=carried)

    assert set(merged) == {"m_a", "m_b", "m_c", "m_d"}
    assert merged["m_a"]["confirmed_by_absence"] is True
    assert "confirmed_by_absence" not in merged["m_c"]


def test_without_carried_help_a_sparse_candidate_would_drop_the_rest(tmp_path):
    # The behaviour sparse reconciliation is here to prevent: one source only, so nothing else
    # holds the meaning up and a silent merge would lose it.
    merged = _merge_candidate_meanings(parent_meanings(), candidate([entry("m_c", "法务风控部")]))

    assert set(merged) == {"m_c"}


def test_a_source_with_no_readable_file_carries_nothing():
    class Missing(FakeWiki):
        def source_snapshot(self, source_id):
            raise RuntimeError("gone")

    wiki = SemanticWiki(Missing(content(LINE_A)), recorder=object(), recover_pending=False)

    assert wiki._carry_confirmed_by_absence(parent_meanings(), candidate([entry("m_c", "法务风控部")])) == {}


def test_a_line_deleted_without_a_revision_change_is_not_carried():
    # A file edited on disk but not re-staged still has the old revision: presence is checked
    # against the text, not against the revision string, so this meaning is not kept.
    same_revision = {key: {**row, "evidence": [{**row["evidence"][0], "source_revision": "rev-new"}]}
                     for key, row in parent_meanings().items()}
    wiki = service(content(LINE_A, LINE_C))

    carried = wiki._carry_confirmed_by_absence(same_revision, candidate([entry("m_c", "法务风控部")]))

    assert "m_b" not in carried
    assert "m_a" in carried
