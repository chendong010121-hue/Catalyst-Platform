"""The Workspace Wiki read model: what a page cites, and what the copy still holds.

The model is what the reading surface renders, so it is checked where the reader would look:
the line a citation points at, the verdict when the file is gone, and the second hop a derived
proposal stands on. Nothing here may invent a quote, and the same store must give the same
model.
"""
import hashlib
import json
from pathlib import Path

from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.wiki_model import build, markdown, parse_evidence_line


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def evidence(source_id, locator, line, span, *, line_end=None, status="fresh",
             klass="observed_from_source"):
    return {"source_id": source_id, "source_revision": "rev", "locator": locator,
            "line_start": line, "line_end": line if line_end is None else line_end,
            "span_sha256": span, "evidence_class": klass, "freshness_status": status}


def meaning(meaning_id, kind, key, text, *, canonical_id=None, evidence_rows=None, **extra):
    row = {"meaning_id": meaning_id, "kind": kind, "key": key, "meaning": text,
           "canonical_key": key, "canonical_id": canonical_id, "business_type": "Department",
           "freshness_status": "fresh", "evidence": evidence_rows or []}
    row.update(extra)
    return row


class FakeStore:
    """The read surface the projection is allowed to use, and nothing else."""

    def __init__(self, tmp_path: Path, meanings, sources):
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.roots = (tmp_path,)
        self.scope_id = "enterprise:e/project:p"
        self._meanings = meanings
        self._sources = sources

    def accepted_meanings(self):
        return {"scope_id": self.scope_id, "active_version_id": "v1", "meanings": self._meanings}

    def sources(self):
        return self._sources

    def source_record(self, source_id):
        return next(row for row in self._sources if row["source_id"] == source_id)

    def semantic_state(self):
        return {"accepted_versions": {"v1": {"version_id": "v1"}}, "active_version_id": "v1",
                "candidates": {}}

    def verify(self):
        return {"status": "OK", "artifact_count": 8, "orphans": [], "problems": []}

    def index_digest(self):
        return "a" * 64


LINES = ["第一行：公司概况", "市场营销中心负责集团品牌与市场推广。", "第三行：其他说明"]


def source_row(source_id, relative_path, fmt="markdown"):
    return {"source_id": source_id, "scope_id": "enterprise:e/project:p",
            "relative_path": relative_path, "revision": "rev", "source_format": fmt,
            "extraction": {"status": "complete", "unit_count": 3, "locator_count": 3,
                           "truncated": False, "part_errors": [], "vision_missing": []}}


def org_store(tmp_path, *, on_disk=True):
    if on_disk:
        (tmp_path / "org.md").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    entity = meaning("m1", "entity", "marketing_center", "市场营销中心", canonical_id="c1",
                     evidence_rows=[evidence("source_a", "line:2", 2, sha(LINES[1]))])
    return FakeStore(tmp_path, [entity], [source_row("source_a", "org.md")])


def page_of(model, prefix):
    return next(page for page in model["pages"] if page["path"].startswith(prefix))


def test_a_page_cites_the_line_it_can_still_read(tmp_path):
    model = build(org_store(tmp_path))
    page = page_of(model, "entities/")
    assert page["evidence"] == ["entities/marketing_center.md#0"]
    assert '<h2 id="s0">关系</h2>' in page["html"]   # the body keeps the knowledge
    assert "`org.md` @" not in page["html"]          # the citation moved to the evidence drawer
    row = model["evidence"][page["evidence"][0]]
    assert row["verified"] is True
    assert row["snippet"] == LINES[1]
    assert row["source_label"] == "原件"
    assert row["line"] == 2 and row["located_by_line"] is True
    assert row["meaning_id"] == "m1"
    assert row["span_sha256"] == sha(LINES[1])
    assert model["meta"]["evidence"]["rows"] == 1
    assert model["meta"]["evidence"]["on_pages"] == 1
    assert model["meta"]["evidence"]["verified"] == 1


def test_a_missing_source_is_reported_not_rendered_as_a_quote(tmp_path):
    model = build(org_store(tmp_path, on_disk=False))
    row = next(iter(model["evidence"].values()))
    assert row["source_label"] == "缺失"
    assert row["snippet"] is None
    assert row["verified"] is False
    assert model["meta"]["evidence"]["missing"] == 1
    assert model["meta"]["sources"] == {**model["meta"]["sources"], "recorded": 1, "present": 0,
                                        "missing": 1, "missing_ids": ["source_a"]}


def test_the_second_hop_names_the_document_a_proposal_quotes(tmp_path):
    quoted = "市场营销中心负责集团品牌与市场推广。"
    record = json.dumps({"claim_id": "claim_1", "quote": quoted,
                         "relative_path": "02_组织架构/org.md", "locator": "line:12"},
                        ensure_ascii=False)
    proposals = tmp_path / ".catalyst-proposals"
    proposals.mkdir()
    (proposals / "proposal_1.md").write_text(record + "\n", encoding="utf-8")
    entity = meaning("m1", "entity", "marketing_center", "市场营销中心", canonical_id="c1",
                     evidence_rows=[evidence("source_p", "line:1", 1, sha(record), status="unknown",
                                             klass="inferred")])
    store = FakeStore(tmp_path, [entity], [source_row("source_p", ".catalyst-proposals/proposal_1.md")])
    model = build(store)
    row = next(iter(model["evidence"].values()))
    assert row["derived"] is True and row["verified"] is True
    assert row["chain"] == {"quote": quoted, "path": "02_组织架构/org.md", "locator": "line:12"}


def test_evidence_the_pages_cannot_carry_is_counted(tmp_path):
    store = org_store(tmp_path)
    store._meanings.append(meaning("m2", "claim", "k", "集团下辖若干分公司", evidence_rows=[
        evidence("source_a", "line:1", 1, sha(LINES[0])),
        evidence("source_a", "line:3", 3, sha(LINES[2])),
    ]))
    meta = build(store)["meta"]
    assert meta["evidence"]["rows"] == 3
    assert meta["evidence"]["on_pages"] == 1
    assert meta["evidence"]["off_pages"] == 2
    assert meta["evidence"]["off_page_kinds"] == {"claim": 2}
    assert meta["meanings"] == {"claim": 1, "entity": 1}


def test_the_same_store_projects_to_the_same_model(tmp_path):
    store = org_store(tmp_path)
    first, second = build(store), build(store)
    assert [page["html"] for page in first["pages"]] == [page["html"] for page in second["pages"]]
    assert first["evidence"] == second["evidence"]
    read_at = first["meta"].pop("read_at"), second["meta"].pop("read_at")
    assert first["meta"] == second["meta"]
    assert first["meta"]["index_stable"] is True
    assert first["meta"]["store_index_sha256"] == "a" * 64
    assert first["meta"]["verify"]["status"] == "OK"
    assert read_at[0] and read_at[1]


def test_an_empty_store_still_projects_the_meta_pages(tmp_path):
    wiki = ProjectWiki(tmp_path / "ws", [tmp_path], enterprise_id="synthetic",
                       project_id="empty", backend="json")
    model = build(wiki)
    kinds = {page["kind"] for page in model["pages"]}
    assert {"overview", "index", "gaps", "log"} <= kinds
    assert model["meta"]["verify"]["status"] == "EMPTY"
    assert model["meta"]["store_index_sha256"] is None
    assert model["meta"]["evidence"] == {"rows": 0, "on_pages": 0, "off_pages": 0,
                                         "off_page_kinds": {}, "verified": 0, "missing": 0,
                                         "derived": 0, "unlocated": 0}
    assert model["meta"]["sources"]["recorded"] == 0


def test_a_citation_that_is_not_a_line_is_shown_as_such():
    parsed = parse_evidence_line("- `deck.pptx` @ `ppt/slides/slide9.xml#text:2` "
                                 "(revision abc123456789, fresh, observed_from_source)")
    assert parsed["located_by_line"] is False
    assert parsed["line"] is None
    assert parsed["source"] == "deck.pptx"
    assert parsed["locator"] == "ppt/slides/slide9.xml#text:2"
    assert parse_evidence_line("not a citation") is None


def test_a_wikilink_to_a_title_no_page_carries_is_rendered_as_a_dead_end():
    body, toc = markdown("## 关系\n- [[市场营销中心]] 隶属 [[不存在的部门]]", {"市场营销中心": "entities/a.md"})
    assert toc == [{"id": "s0", "text": "关系"}]
    assert 'data-page="entities/a.md"' in body
    assert '<span class="dead"' in body
