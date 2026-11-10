"""The five promises of the one-command chain, checked on a real workspace."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_chain import run_chain
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki

MATERIAL = (
    "# Quality review\n"
    "Rule: Reviewer checks the package before release\n"
    "relation: reviewer | performs | quality_review\n"
)


def _material(tmp_path, text=MATERIAL) -> Path:
    sources = tmp_path / "sources"
    sources.mkdir(exist_ok=True)
    path = sources / "responsibility.md"
    path.write_text(text, encoding="utf-8")
    return path


def _review(tmp_path, text="# review\nACCEPT: every name sits in the evidence\n") -> Path:
    path = tmp_path / "review.md"
    path.write_text(text, encoding="utf-8")
    return path


def _chain(tmp_path, material, review, **kwargs):
    return run_chain(workspace=tmp_path / "workspace", source=material, review=review, **kwargs)


def _cold(tmp_path, run_id: str):
    workspace = (tmp_path / "workspace").resolve()
    wiki = ProjectWiki(workspace, [tmp_path / "sources"], enterprise_id="synthetic",
                       project_id="ontology-chain")
    recorder = RunRecorder(
        JsonlTraceStore(workspace), run_id=run_id, request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest())
    recorder.start(request_kind="chain_test", actor="local_cli_user", component="CatalystGateway")
    return wiki, SemanticWiki(wiki, recorder=recorder)


def test_one_command_reaches_an_active_version_and_reads_it_back(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path)
    report_path = tmp_path / "chain.json"

    report = _chain(tmp_path, material, review, report_path=report_path)

    assert report["status"] == "success"
    assert report["active_version_id"] == report["version_id"]
    assert [row["step"] for row in report["steps"]] == [
        "source.stage", "candidate.propose", "candidate.evaluate",
        "candidate.approve", "version.activate", "ontology.query"]
    assert all(row["run_id"] for row in report["steps"])
    assert report["signing_keys"] == {"reviewer": "created", "owner": "created"}
    assert report["read"]["matches_active_version"] is True
    assert report["read"]["meaning_count"] >= 2
    assert json.loads(report_path.read_text(encoding="utf-8"))["version_id"] == report["version_id"]


def test_every_read_meaning_carries_a_locator_and_the_source_text(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path)
    report = _chain(tmp_path, material, review)
    lines = material.read_text(encoding="utf-8").splitlines()

    for meaning in report["read"]["meanings"]:
        assert meaning["meaning_id"]
        assert meaning["evidence"], meaning
        for evidence in meaning["evidence"]:
            assert evidence["source_id"] and evidence["source_revision"]
            assert evidence["line_start"] >= 1
            span = "\n".join(lines[evidence["line_start"] - 1:evidence["line_end"]])
            assert evidence["quote"] == span
            assert evidence["quote_matches_span"] is True


def test_a_repeat_run_is_a_no_op(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path)

    first = _chain(tmp_path, material, review)
    second = _chain(tmp_path, material, review)

    assert first["status"] == "success"
    assert second["status"] == "no_op"
    assert second["version_id"] == first["version_id"]
    state = _cold(tmp_path, "run_inspect")[0].semantic_state()
    assert len(state["accepted_versions"]) == 1
    assert state["active_version_id"] == first["version_id"]


def test_a_changed_source_leaves_the_old_version_readable_and_stale(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path)
    first = _chain(tmp_path, material, review)

    material.write_text(
        MATERIAL + "condition: quality_review_ready | Package is ready for review\n",
        encoding="utf-8")
    second = _chain(tmp_path, material, review)

    assert second["status"] == "success"
    assert second["version_id"] != first["version_id"]
    assert second["read"]["version_id"] == second["version_id"]

    wiki, service = _cold(tmp_path, "run_old_version")
    old = service.read_knowledge("quality review", mode="accepted_enterprise_semantics",
                                 actor_origin="catalyst_deterministic",
                                 version_id=first["version_id"], include_all_active=True)
    assert old["version_id"] == first["version_id"]
    assert {row["freshness_status"] for row in old["meanings"]} == {"stale"}
    assert old["knowledge_status"] == "needs_reconciliation"

    state = wiki.semantic_state()
    assert len(state["accepted_versions"]) == 2
    newest = state["candidates"][state["accepted_versions"][second["version_id"]]["candidate_id"]]
    assert newest["parent_version_id"] == first["version_id"]


def test_the_cold_read_never_returns_a_candidate_that_was_not_accepted(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path)
    report = _chain(tmp_path, material, review)
    state = _cold(tmp_path, "run_cold_state")[0].semantic_state()
    active_meanings = set(state["accepted_versions"][report["version_id"]]["meanings"])

    assert {row["meaning_id"] for row in report["read"]["meanings"]} <= active_meanings
    assert report["read"]["version_id"] == state["active_version_id"]


def test_a_review_that_does_not_accept_publishes_nothing(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path, "# review\nREVISE: the relation overstates it\n")

    report = _chain(tmp_path, material, review, disposition="REVISE")

    assert report["status"] == "refused"
    assert report["blocked"]["reason"] == "external_semantic_evaluation_not_accept"
    state = _cold(tmp_path, "run_refused_state")[0].semantic_state()
    assert state["active_version_id"] is None
    assert state["accepted_versions"] == {}


def test_the_chain_signs_with_the_machine_keys_not_test_ones(tmp_path):
    material, review = _material(tmp_path), _review(tmp_path)
    report = _chain(tmp_path, material, review)
    state = _cold(tmp_path, "run_receipts")[0].semantic_state()

    candidate = state["candidates"][report["candidate_id"]]
    review_receipt = list(candidate["external_evaluations"].values())[0]
    decision = state["decisions"][candidate["latest_decision_id"]]
    assert review_receipt["issuer_id"] == "local.reviewer"
    assert review_receipt["authority_class"] == "independent_evaluator"
    assert review_receipt["report_sha256"] == hashlib.sha256(review.read_bytes()).hexdigest()
    assert decision["owner_acceptance_basis"]["issuer_id"] == "local.owner"
    assert decision["owner_acceptance_basis"]["authority_class"] == "organization_owner"


def test_a_missing_review_stops_before_anything_is_staged(tmp_path):
    material = _material(tmp_path)
    with pytest.raises(SemanticTransitionError) as caught:
        _chain(tmp_path, material, tmp_path / "absent.md")
    assert caught.value.code == "reviewer_report_missing"
    assert not (tmp_path / "workspace" / ".catalyst" / "wiki").exists()
