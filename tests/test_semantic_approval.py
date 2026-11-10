"""A candidate becomes live only through a signed review and a signed owner acceptance."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from catalyst_platform import semantic_approval
from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_keys import ensure_key, load_key, verifier
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
        if name == "approve":
            result = semantic_approval.approve(service, *args, **kwargs)
        elif name == "signed_activate":
            result = semantic_approval.activate(service, *args, **kwargs)
        else:
            result = getattr(service, name)(*args, **kwargs)
        recorder.finish("success", model_calls=0)
        service.finalize_run(run_id, "success")
        return result
    except BaseException as exc:
        if not recorder.is_finished:
            recorder.finish("failure", model_calls=0, error_owner="semantic_wiki")
            service.finalize_run(run_id, "failure")
        raise exc


def _workspace(tmp_path, backend="json"):
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "responsibility.md"
    source.write_text(SOURCE, encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="ent", project_id="proj", backend=backend)
    ensure_key(wiki.workspace, "reviewer")
    ensure_key(wiki.workspace, "owner")
    return wiki, source


def _candidate(wiki: ProjectWiki, source: Path):
    workspace = wiki.workspace
    proposed = _operation(workspace, wiki, "run_approve_propose", "propose", source,
                          actor_origin="codex_fixture")
    evaluation = _operation(workspace, wiki, "run_approve_eval", "evaluate",
                            proposed["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "pass"
    return proposed


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_a_signed_review_and_owner_acceptance_make_a_candidate_live(tmp_path, backend):
    wiki, source = _workspace(tmp_path, backend)
    workspace = wiki.workspace
    proposed = _candidate(wiki, source)
    report = tmp_path / "review.md"
    report.write_text("# review\nACCEPT: names sit in the evidence and the meanings restate it\n", encoding="utf-8")

    accepted = _operation(workspace, wiki, "run_approve_decide", "approve",
                          proposed["candidate_id"], reviewer_report=report)
    assert accepted["status"] == "accepted"

    activated = _operation(workspace, wiki, "run_approve_activate", "signed_activate",
                           accepted["version_id"], expected_head=None)
    assert activated["active_version_id"] == accepted["version_id"]

    state = wiki.semantic_state()
    basis = state["decisions"][accepted["decision_id"]]["owner_acceptance_basis"]
    assert basis["authority_class"] == "organization_owner"
    assert basis["issuer_id"] == "local.owner"
    external = state["candidates"][proposed["candidate_id"]]["external_evaluations"]
    reviewed = list(external.values())[0]
    assert reviewed["issuer_id"] == "local.reviewer"
    assert reviewed["report_sha256"] == hashlib.sha256(report.read_bytes()).hexdigest()
    assert state["active_version_id"] == accepted["version_id"]


def test_a_review_that_does_not_accept_refuses_the_decision(tmp_path):
    wiki, source = _workspace(tmp_path)
    workspace = wiki.workspace
    proposed = _candidate(wiki, source)
    report = tmp_path / "review.md"
    report.write_text("# review\nREVISE: the relation states more than the source does\n", encoding="utf-8")

    refused = _operation(workspace, wiki, "run_refuse", "approve", proposed["candidate_id"],
                         reviewer_report=report, disposition="REVISE")

    assert refused["status"] == "refused"
    assert refused["reason"] == "external_semantic_evaluation_not_accept"
    state = wiki.semantic_state()
    assert state["candidates"][proposed["candidate_id"]]["status"] != "ACCEPTED"
    assert state["active_version_id"] is None


def test_the_chain_refuses_an_acceptance_without_a_signed_receipt(tmp_path):
    wiki, source = _workspace(tmp_path)
    workspace = wiki.workspace
    proposed = _candidate(wiki, source)

    with pytest.raises(SemanticTransitionError) as caught:
        _operation(workspace, wiki, "run_unsigned", "decide", proposed["candidate_id"],
                   decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="unsigned")

    assert caught.value.code == "external_semantic_evaluation_required"
    assert wiki.semantic_state()["active_version_id"] is None


def test_a_missing_report_or_key_stops_the_approval(tmp_path):
    wiki, source = _workspace(tmp_path)
    workspace = wiki.workspace
    proposed = _candidate(wiki, source)

    with pytest.raises(SemanticTransitionError) as caught:
        _operation(workspace, wiki, "run_missing_report", "approve", proposed["candidate_id"],
                   reviewer_report=tmp_path / "absent.md")
    assert caught.value.code == "reviewer_report_missing"

    bare = ProjectWiki(tmp_path / "bare", [tmp_path / "sources"], enterprise_id="ent", project_id="proj")
    candidate = wiki.semantic_state()["candidates"][proposed["candidate_id"]]
    with pytest.raises(SemanticTransitionError) as caught:
        semantic_approval.owner_receipt(bare.workspace, candidate, action="ACCEPT", decision="ACCEPTED")
    assert caught.value.code == "owner_key_missing"


def test_activation_is_bound_to_the_head_it_was_signed_for(tmp_path):
    wiki, source = _workspace(tmp_path)
    workspace = wiki.workspace
    proposed = _candidate(wiki, source)
    report = tmp_path / "review.md"
    report.write_text("# review\nACCEPT\n", encoding="utf-8")
    accepted = _operation(workspace, wiki, "run_head_decide", "approve",
                          proposed["candidate_id"], reviewer_report=report)

    recorder, service = _service(workspace, wiki, "run_head_activate")
    with pytest.raises(SemanticTransitionError) as caught:
        semantic_approval.activate(service, accepted["version_id"], expected_head="version_not_the_head")
    assert caught.value.code == "expected_head_mismatch"
    assert wiki.semantic_state()["active_version_id"] is None

    activated = semantic_approval.activate(service, accepted["version_id"], expected_head=None)
    assert activated["active_version_id"] == accepted["version_id"]
    assert wiki.semantic_state()["active_version_id"] == accepted["version_id"]
    assert load_key(workspace, "owner") is not None
