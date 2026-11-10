"""A verified handoff also publishes the typed reading it stands on.

The handoff re-reads the original and compares every span, so the rows that survive that
check already have a passage. This test pins what the product path does with them: one
typed candidate beside the handoff candidate, a package of passages that never carries the
document a second time, and a named reason for every row that could not be placed.
"""
import base64
import hashlib

import pytest

from pathlib import Path

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.understand_only import UnderstandPort, UnderstandingRequest
from catalyst_platform.understand_wiki import UnderstandWikiAdapter
from catalyst_platform.wiki import ProjectWiki


def _offline_result(wiki, root, source):
    return UnderstandPort().understand(
        UnderstandingRequest(
            "offline-typed-handoff", "read document",
            source_refs=(source,), intent="KNOWLEDGE_PROPOSE",
            scope_id=wiki.scope_id, requested_depth="semantic", budget_steps=16,
        ),
        source_root=root,
    ).to_dict()


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("maker,extension", [("_docx", "docx"), ("_pptx_table", "pptx")])
def test_a_verified_handoff_publishes_one_typed_candidate(tmp_path, backend, maker, extension):
    from tests import test_understand_only as fixtures

    root = tmp_path / "sources"
    root.mkdir()
    source = root / f"evidence.{extension}"
    # One row the port can read, written the way a page states one. The fixtures' own
    # sentence is prose, and the only rows a prose page yields are the port's two standing
    # unknowns - which are evidence about the run and never candidates, so a handoff with
    # nothing else publishes nothing (and says so).
    getattr(fixtures, maker)(source, text="Claim: dept_duty | 部门承担经营分析")
    wiki = ProjectWiki(tmp_path / "workspace", [root], enterprise_id="synthetic",
                       project_id="typed", backend=backend)
    gateway = CatalystGateway(wiki.workspace)
    result = _offline_result(wiki, root, source)

    def submit(recorder):
        return UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), root).submit(
            result, declared_scope_id=wiki.scope_id)

    receipt = gateway.semantic_operation(
        operation="understand.candidate.submit", scope_id=wiki.scope_id,
        actor_origin="offline_fixture",
        input_value={"contract_version": "catalyst.understand_handoff.v1"},
        action=submit,
    )["result"]

    typed_receipt = receipt["typed"]
    assert typed_receipt["status"] == "proposed", typed_receipt
    state = wiki.semantic_state()
    typed = state["candidates"][typed_receipt["candidate_id"]]
    handoff = state["candidates"][receipt["candidate_id"]]

    # One document, two candidates: the frozen handoff and the typed reading made from it.
    assert "candidate_type" not in typed
    assert typed["status"] == "PROPOSED"
    assert typed["entries"], "a verified handoff must place at least one row"
    assert typed["entries"][0]["kind"] in {"entity", "claim", "relation", "condition",
                                           "exception", "unknown"}
    assert handoff["candidate_type"] == "understand_handoff.v1"
    assert handoff["typed_candidate_id"] == typed["candidate_id"]

    # Every stored anchor hashes to the passage the package actually holds.
    package = Path(typed_receipt["package_path"])
    assert package.parent.name == ".catalyst-proposals"
    text = package.read_text(encoding="utf-8")
    lines = text.splitlines()
    for entry in typed["entries"]:
        passage = lines[entry["line_start"] - 1]
        assert hashlib.sha256(passage.encode("utf-8")).hexdigest() == entry["span_sha256"]
        assert entry["line_end"] == entry["line_start"]

    # The package carries the passages, never the document a second time.
    assert "bytes_base64" not in text
    assert base64.b64encode(source.read_bytes()).decode("ascii") not in text

    # The original is untouched: identity only, and its revision still the file's own.
    staged = [row for row in handoff["source_bindings"] if row["status"] == "STAGED"]
    assert len(staged) == 1
    original = wiki.source_record(staged[0]["wiki_source_id"])
    assert original["content_status"] == "NOT_PARSED"
    assert original["revision"] == staged[0]["source_sha256"]
    assert wiki.claim_history(staged[0]["wiki_source_id"]) == []

    # The typed candidate is a normal candidate: structural evaluation reaches it. The
    # handoff beside it is still the thing the lifecycle refuses.
    evaluated = gateway.semantic_operation(
        operation="candidate.evaluate", scope_id=wiki.scope_id,
        actor_origin="independent_evaluator",
        input_value={"candidate_id": typed["candidate_id"]},
        action=lambda recorder: SemanticWiki(wiki, recorder=recorder).evaluate(
            typed["candidate_id"], actor_origin="independent_evaluator"),
    )
    assert evaluated["status"] == "success", evaluated.get("error")
    assert evaluated["result"]["status"] in {"pass", "needs_review"}
    refused = gateway.semantic_operation(
        operation="candidate.evaluate", scope_id=wiki.scope_id,
        actor_origin="independent_evaluator",
        input_value={"candidate_id": handoff["candidate_id"]},
        action=lambda recorder: SemanticWiki(wiki, recorder=recorder).evaluate(
            handoff["candidate_id"], actor_origin="independent_evaluator"),
    )
    assert refused["status"] == "failure"
    assert refused["error"]["code"] == "candidate_requires_mapping"


def test_a_row_that_cannot_be_placed_is_named_and_does_not_decide_the_publish(tmp_path):
    root = tmp_path / "sources"
    root.mkdir()
    wiki = ProjectWiki(tmp_path / "workspace", [root], enterprise_id="synthetic",
                       project_id="typed", backend="json")

    class Reader:
        def _emit(self, *args, **kwargs):
            pass

    adapter = UnderstandWikiAdapter(wiki, Reader(), root)
    items = {
        "kept": {"item_id": "kept", "kind": "entity", "key": "alpha", "meaning": "Alpha",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": ["e1"]},
        "conflict": {"item_id": "conflict", "kind": "claim", "key": "beta", "meaning": "Beta",
                     "evidence_class": "conflict", "evidence_refs": ["e1"]},
        "loose": {"item_id": "loose", "kind": "relation", "key": "gamma",
                  "meaning": "Alpha owns Gamma", "evidence_class": "SOURCE_DIRECT",
                  "subject": "@alpha", "object": "@gamma", "predicate": "owns",
                  "evidence_refs": ["e1"], "relation_source": "SENTENCE"},
    }
    refs = {"e1": {"evidence_id": "e1", "source_id": "src", "locator": "lines:1-1",
                   "quote": "Alpha owns Gamma", "span_sha256": "0" * 64}}

    entries, report = adapter.harvest_entries(items, refs, list(items), lines=["# header"],
                                              strict=False)
    assert [entry["kind"] for entry in entries] == ["entity"]
    assert {row["item_key"]: row["rule"] for row in report["dropped"]} == {
        "conflict": "conflict_requires_decision"}
    assert report["dropped_relations"] == [{"item_key": "gamma",
                                            "rule": "relation_endpoint_not_selected"}]

    with pytest.raises(Exception) as refused:
        adapter.harvest_entries(items, refs, list(items), lines=["# header"], strict=True)
    assert getattr(refused.value, "code", None) == "harvest_unresolved_kind"
