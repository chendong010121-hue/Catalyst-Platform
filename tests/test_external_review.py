"""A sealed package goes out, an answer comes back, and the receipt binds both."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from catalyst_platform import external_review, semantic_approval
from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_keys import ensure_key, verifier
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki

SOURCE = (
    "# Quality review\n"
    "Rule: Reviewer checks the package before release\n"
    "relation: reviewer | performs | quality_review\n"
    "condition: quality_review_ready | Package is ready for review\n"
)


def _recorder(workspace: Path, run_id: str) -> RunRecorder:
    recorder = RunRecorder(
        JsonlTraceStore(workspace),
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        event_schema_version="1.5",
    )
    recorder.start(request_kind="semantic_test", actor="local_cli_user", component="CatalystGateway")
    return recorder


def _service(workspace: Path, wiki: ProjectWiki, run_id: str):
    recorder = _recorder(workspace, run_id)
    return recorder, SemanticWiki(wiki, recorder=recorder, receipt_verifier=verifier(wiki.workspace))


def _operation(workspace: Path, wiki: ProjectWiki, run_id: str, name: str, *args, **kwargs):
    recorder, service = _service(workspace, wiki, run_id)
    try:
        if name == "submit":
            result = semantic_approval.approve_external(service, *args, **kwargs)
        else:
            result = getattr(service, name)(*args, **kwargs)
        recorder.finish("success", model_calls=0)
        service.finalize_run(run_id, "success")
        return result
    except BaseException:
        if not recorder.is_finished:
            recorder.finish("failure", model_calls=0, error_owner="semantic_wiki")
            service.finalize_run(run_id, "failure")
        raise


def _workspace(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "responsibility.md"
    source.write_text(SOURCE, encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="ent", project_id="proj")
    ensure_key(wiki.workspace, "reviewer")
    ensure_key(wiki.workspace, "owner")
    return wiki, source


def _candidate(wiki, source):
    workspace = wiki.workspace
    proposed = _operation(workspace, wiki, "run_review_propose", "propose", source,
                          actor_origin="codex_fixture")
    evaluation = _operation(workspace, wiki, "run_review_eval", "evaluate",
                            proposed["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "pass"
    return proposed["candidate_id"]


def _answer(tmp_path, verdict="REVIEWABLE", findings=()):
    path = tmp_path / "answer.json"
    path.write_text(json.dumps({"verdict": verdict, "findings": list(findings)}, ensure_ascii=False),
                    encoding="utf-8")
    return path


def test_the_package_carries_the_material_the_items_and_their_quotes(tmp_path):
    wiki, source = _workspace(tmp_path)
    candidate_id = _candidate(wiki, source)
    out = tmp_path / "package"

    package = external_review.write_package(wiki, candidate_id, out, question="does it hold?")

    bundled = out / package["sources"][0]["bundle_file"]
    assert bundled.read_text(encoding="utf-8") == SOURCE
    assert package["question"] == "does it hold?"
    assert package["candidate_id"] == candidate_id
    entries = wiki.semantic_state()["candidates"][candidate_id]["entries"]
    assert [row["item_key"] for row in package["items"]] == [row["key"] for row in entries]
    lines = SOURCE.splitlines()
    for row in package["items"]:
        [evidence] = row["evidence"]
        assert evidence["quote"] == lines[evidence["line_start"] - 1]
        assert evidence["span_sha256"]
    assert external_review.load_package(out)["package_sha256"] == package["package_sha256"]


def test_a_package_that_changed_after_it_was_written_is_refused(tmp_path):
    wiki, source = _workspace(tmp_path)
    candidate_id = _candidate(wiki, source)
    out = tmp_path / "package"
    package = external_review.write_package(wiki, candidate_id, out)  # noqa: F841
    forged = json.loads((out / "package.json").read_text(encoding="utf-8"))
    forged["items"][0]["meaning"] = "something the material never said"
    (out / "package.json").write_text(json.dumps(forged, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SemanticTransitionError) as caught:
        external_review.load_package(out)
    assert caught.value.code == "review_package_tampered"

    fresh = external_review.write_package(wiki, candidate_id, tmp_path / "again")
    bundled = tmp_path / "again" / fresh["sources"][0]["bundle_file"]
    bundled.write_text(SOURCE + "Rule: added after sealing\n", encoding="utf-8")
    with pytest.raises(SemanticTransitionError) as caught:
        external_review.load_package(tmp_path / "again")
    assert caught.value.code == "review_package_source_changed"


def test_an_external_acceptance_records_what_was_sent_and_what_came_back(tmp_path):
    wiki, source = _workspace(tmp_path)
    candidate_id = _candidate(wiki, source)
    package = external_review.write_package(wiki, candidate_id, tmp_path / "package")
    answer = _answer(tmp_path)

    accepted = _operation(wiki.workspace, wiki, "run_review_submit", "submit", candidate_id,
                          package_dir=tmp_path / "package", response_path=answer,
                          evaluator_id="codex", evaluator_context="external_model")

    assert accepted["status"] == "accepted"
    candidate = wiki.semantic_state()["candidates"][candidate_id]
    evaluation = list(candidate["external_evaluations"].values())[0]
    assert evaluation["evaluator_id"] == "codex"
    assert evaluation["issuer_id"] == "local.reviewer"
    assert evaluation["review_package_sha256"] == package["package_sha256"]
    assert evaluation["evaluator_context"] == "external_model"
    assert evaluation["report_sha256"] == hashlib.sha256(answer.read_bytes()).hexdigest()


def test_an_external_revise_is_recorded_and_refuses_the_decision(tmp_path):
    wiki, source = _workspace(tmp_path)
    candidate_id = _candidate(wiki, source)
    external_review.write_package(wiki, candidate_id, tmp_path / "package")
    answer = _answer(tmp_path, "REVISE", [{"id": "f1", "severity": "major",
                                           "item_keys": ["reviewer performs quality_review"],
                                           "reason": "the relation adds a verb the line does not carry"}])

    refused = _operation(wiki.workspace, wiki, "run_review_revise", "submit", candidate_id,
                         package_dir=tmp_path / "package", response_path=answer,
                         evaluator_id="codex")

    assert refused["status"] == "refused"
    assert refused["reason"] == "external_semantic_evaluation_not_accept"
    state = wiki.semantic_state()
    assert state["candidates"][candidate_id]["status"] != "ACCEPTED"
    evaluation = list(state["candidates"][candidate_id]["external_evaluations"].values())[0]
    assert evaluation["disposition"] == "REVISE"
    assert evaluation["finding_count"] == 1


def test_a_package_written_for_another_candidate_is_refused(tmp_path):
    wiki, source = _workspace(tmp_path)
    candidate_id = _candidate(wiki, source)
    external_review.write_package(wiki, candidate_id, tmp_path / "package")
    source.write_text(SOURCE + "exception: quality_review_hotfix | Hotfix goes to review\n", encoding="utf-8")
    other = _candidate(wiki, source)

    with pytest.raises(SemanticTransitionError) as caught:
        _operation(wiki.workspace, wiki, "run_review_mismatch", "submit", other,
                   package_dir=tmp_path / "package", response_path=_answer(tmp_path))
    assert caught.value.code == "review_package_binding_mismatch"


def test_an_answer_without_a_verdict_is_refused(tmp_path):
    answer = tmp_path / "answer.json"
    answer.write_text(json.dumps({"verdict": "PROBABLY", "findings": []}), encoding="utf-8")
    with pytest.raises(SemanticTransitionError) as caught:
        external_review.read_response(answer)
    assert caught.value.code == "review_response_invalid"
