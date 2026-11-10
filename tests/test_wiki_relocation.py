"""A citation follows its own text, and only its own text.

The store is never rewritten by an edit on disk: a stale citation either points at the line
that still holds the identical text, or stays stale and says so.
"""
from __future__ import annotations

import copy
import hashlib
import json

from pathlib import Path

from catalyst_platform.wiki_pages import materialize, project
from catalyst_platform.wiki_relocation import (
    RELOCATED,
    RelocationResolver,
    apply_relocations,
    load_overlays,
    map_spans,
    overlay_root,
    relocate,
)


def sha(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


class FakeStore:
    """The read surface relocation is allowed to use, and nothing else."""

    def __init__(self, tmp_path: Path, meanings, contents, revision="new-rev"):
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.roots = (tmp_path,)
        self._meanings = meanings
        self._contents = contents
        self._revision = revision
        self._sources = [{
            "source_id": "source_a", "scope_id": "enterprise:e/project:p", "relative_path": "org.md",
            "revision": revision, "source_format": "markdown",
            "extraction": {"status": "complete", "unit_count": 4, "locator_count": 4, "truncated": False,
                           "part_errors": [], "vision_missing": []},
        }]

    def accepted_meanings(self):
        return {"scope_id": "enterprise:e/project:p", "active_version_id": "v1", "meanings": self._meanings}

    def sources(self):
        return self._sources

    def source_record(self, source_id):
        return next(row for row in self._sources if row["source_id"] == source_id)

    def source_snapshot(self, source_id):
        if source_id not in self._contents:
            raise RuntimeError("the staged Wiki source has no readable original")
        return {"current_revision": self._revision, "content": self._contents[source_id]}

    def semantic_state(self):
        return {"accepted_versions": {"v1": {"version_id": "v1"}}, "candidates": {}, "active_version_id": "v1"}


def evidence(line_start, span_sha256, *, line_end=None, source_id="source_a", revision="old-rev",
             status="stale", locator=None):
    row = {
        "claim_id": None, "source_id": source_id, "source_revision": revision,
        "line_start": line_start,
        "line_end": line_start if line_end is None else line_end,
        "span_sha256": span_sha256,
        "evidence_class": "observed_from_source", "freshness_status": status,
    }
    if locator is not None:
        row["locator"] = locator
    return row


def meaning(rows):
    return {
        "meaning_id": "m1", "kind": "entity", "key": "marketing_center", "meaning": "市场营销中心",
        "canonical_key": "marketing_center", "canonical_id": "c1", "business_type": "Department",
        "freshness_status": "stale", "evidence": rows,
    }


OLD_LINE = "市场营销中心负责预算。"
NEW_CONTENT = "# 标题\n新增一行说明\n" + OLD_LINE + "\n总部负责审批。\n"


def store(tmp_path: Path, *, status="stale") -> FakeStore:
    return FakeStore(tmp_path, [meaning([evidence(2, sha(OLD_LINE), status=status)])],
                     {"source_a": NEW_CONTENT})


def test_a_line_that_moved_is_found_by_its_own_hash():
    moved, unmapped = map_spans([(2, 2, sha(OLD_LINE))], NEW_CONTENT)

    assert unmapped == []
    assert moved[0]["new_line_start"] == 3
    assert moved[0]["new_line_end"] == 3
    assert moved[0]["confidence"] == "exact"


def test_a_line_that_is_gone_is_not_mapped_to_its_neighbour():
    # Same paragraph, one word changed: similar, not identical — so it stays stale.
    edited = NEW_CONTENT.replace(OLD_LINE, "市场营销中心负责年度预算。")

    moved, unmapped = map_spans([(2, 2, sha(OLD_LINE))], edited)

    assert moved == []
    assert unmapped[0]["reason"] == "span_absent"


def test_a_duplicated_line_maps_to_the_nearest_copy_and_says_so():
    content = "共同条款\n甲\n共同条款\n"

    moved, _ = map_spans([(2, 2, sha("共同条款"))], content)

    assert moved[0]["new_line_start"] == 1
    assert moved[0]["confidence"] == "exact_nearest"
    assert moved[0]["candidates"] == 2


def test_relocating_writes_an_overlay_beside_the_store_and_changes_no_version(tmp_path):
    wiki = store(tmp_path)
    before = copy.deepcopy(wiki.accepted_meanings())
    before_state = copy.deepcopy(wiki.semantic_state())

    report = relocate(wiki)

    assert report["moved"] == 1 and report["unmapped"] == 0
    overlay = Path(report["overlays"][0])
    assert overlay.is_file()
    assert overlay.resolve().is_relative_to(overlay_root(wiki.workspace).resolve())
    assert json.loads(overlay.read_text(encoding="utf-8"))["method"] == "line_sha256_exact"
    assert wiki.accepted_meanings() == before
    assert wiki.semantic_state() == before_state
    assert load_overlays(wiki.workspace)


def test_a_stale_citation_is_rendered_as_relocated_and_points_at_the_new_line(tmp_path):
    wiki = store(tmp_path)
    relocate(wiki)

    pages = project(wiki).pages
    entity = next(page for page in pages if page.kind == "entity")

    assert "@ `line:3`" in entity.content
    assert "relocated from line:2" in entity.content
    assert f"{'old-rev'[:8]}->{'new-rev'[:8]}" in entity.content


def test_without_an_overlay_the_same_citation_stays_stale(tmp_path):
    wiki = store(tmp_path)

    pages = project(wiki).pages
    entity = next(page for page in pages if page.kind == "entity")

    assert "@ `line:2`" in entity.content
    assert "stale" in entity.content
    assert "relocated" not in entity.content


def test_relocation_does_not_mutate_the_meaning_it_was_given(tmp_path):
    wiki = store(tmp_path)
    relocate(wiki)
    original = copy.deepcopy(wiki.accepted_meanings()["meanings"])

    relocated = apply_relocations(wiki.accepted_meanings()["meanings"], RelocationResolver(wiki))

    assert wiki.accepted_meanings()["meanings"] == original
    assert relocated[0]["evidence"][0]["freshness_status"] == RELOCATED
    assert original[0]["evidence"][0]["freshness_status"] == "stale"


def test_a_second_projection_writes_nothing(tmp_path):
    wiki = store(tmp_path)
    relocate(wiki)
    pages_root = tmp_path / "pages"
    materialize(project(wiki).pages, pages_root)

    again = materialize(project(wiki).pages, pages_root, dry_run=True)

    assert again["written"] == []


def test_a_source_whose_file_is_gone_is_left_alone(tmp_path):
    wiki = FakeStore(tmp_path, [meaning([evidence(2, sha(OLD_LINE))])], {})

    report = relocate(wiki)

    assert report["overlays"] == []
    assert report["skipped"] == [{"source_id": "source_a", "reason": "source_unavailable"}]


def test_a_source_that_never_changed_needs_no_overlay(tmp_path):
    wiki = FakeStore(tmp_path, [meaning([evidence(2, sha(OLD_LINE), revision="new-rev")])],
                     {"source_a": NEW_CONTENT})

    report = relocate(wiki)

    assert report["overlays"] == []
    assert report["skipped"] == [{"source_id": "source_a", "reason": "revision_unchanged"}]


def test_fresh_evidence_is_never_touched(tmp_path):
    wiki = store(tmp_path, status="fresh")
    relocate(wiki)

    relocated = apply_relocations(wiki.accepted_meanings()["meanings"], RelocationResolver(wiki))

    assert relocated[0]["evidence"][0]["freshness_status"] == "fresh"
    assert relocated[0]["evidence"][0]["line_start"] == 2


def test_an_identity_without_a_file_is_kept_and_says_so(tmp_path):
    # The registered source is not on disk any more: the page keeps the identity and admits
    # that nothing above it can be checked, instead of looking like an ordinary source.
    wiki = FakeStore(tmp_path, [meaning([evidence(2, sha(OLD_LINE), status="unknown")])], {})

    sources = [page for page in project(wiki).pages if page.kind == "source"]

    assert len(sources) == 1
    assert "原始文件当前不在任何 Wiki 根目录下" in sources[0].content


def test_a_source_that_is_still_on_disk_does_not_claim_otherwise(tmp_path):
    wiki = store(tmp_path)
    (tmp_path / "org.md").write_text(NEW_CONTENT, encoding="utf-8")

    sources = [page for page in project(wiki).pages if page.kind == "source"]

    assert "原始文件当前不在任何 Wiki 根目录下" not in sources[0].content


def test_a_relocated_citation_is_addressed_where_it_moved_to(tmp_path):
    # The store recorded `line:2` when the quote was there. After the move that address points
    # at a different line, so a page that repeated it would send the reader to the wrong place.
    wiki = FakeStore(tmp_path, [meaning([evidence(2, sha(OLD_LINE), locator="line:2")])],
                     {"source_a": NEW_CONTENT})
    relocate(wiki)

    entity = next(page for page in project(wiki).pages if page.kind == "entity")

    assert "@ `line:3`" in entity.content
    assert "@ `line:2`" not in entity.content
    assert "relocated from line:2" in entity.content
    # Rendering the new address does not rewrite the record it came from.
    assert wiki.accepted_meanings()["meanings"][0]["evidence"][0]["locator"] == "line:2"


def test_a_relocated_span_is_addressed_with_both_of_its_lines(tmp_path):
    wiki = FakeStore(
        tmp_path, [meaning([evidence(2, sha(OLD_LINE), line_end=4, locator="line:2-4")])],
        {"source_a": NEW_CONTENT})
    relocate(wiki)

    entity = next(page for page in project(wiki).pages if page.kind == "entity")

    assert "@ `line:3-5`" in entity.content
    assert "@ `line:2-4`" not in entity.content
    assert "relocated from line:2" in entity.content
