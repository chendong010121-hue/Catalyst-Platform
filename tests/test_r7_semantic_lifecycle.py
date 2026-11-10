"""Bounded R7 semantic lifecycle over the existing ProjectWiki authority."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki, WikiUnavailable
from p0_test_authority import authorize_test_operation, trusted_test_operation, verify_test_receipt


def _recorder(workspace: Path, run_id: str, *, event_schema_version="1.4") -> RunRecorder:
    recorder = RunRecorder(
        JsonlTraceStore(workspace),
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        event_schema_version=event_schema_version,
    )
    recorder.start(request_kind="semantic_test", actor="local_cli_user", component="CatalystGateway")
    return recorder


def _operation(workspace: Path, run_id: str, wiki: ProjectWiki, name: str, *args, **kwargs):
    needs_test_authority = name in {"activate", "rollback"} or (
        name == "decide" and kwargs.get("decision") == "ACCEPTED"
    )
    recorder = _recorder(workspace, run_id, event_schema_version="1.5" if needs_test_authority else "1.4")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    try:
        authorized_kwargs = authorize_test_operation(service, name, args, kwargs)
        result = getattr(service, name)(*args, **authorized_kwargs)
        recorder.finish("success", model_calls=0)
        service.finalize_run(run_id, "success")
        return result
    except BaseException as exc:
        if not recorder.is_finished:
            recorder.event(
                "semantic.transition.failed",
                operation=name,
                status="failure",
                error_code=getattr(exc, "code", "unexpected_error"),
                actor_origin=kwargs.get("actor_origin", "catalyst_deterministic"),
                scope_id=wiki.scope_id,
            )
            recorder.finish("failure", model_calls=0, error_owner="semantic_wiki")
            service.finalize_run(run_id, "failure")
        raise


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_candidate_acceptance_activation_projection_and_rollback_share_one_identity(tmp_path, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "responsibility.md"
    source.write_text(
        "# Quality review\n"
        "Rule: Reviewer checks the package before release\n"
        "relation: reviewer | performs | quality_review\n"
        "condition: quality_review_ready | Package is ready for review\n",
        encoding="utf-8",
    )
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj", backend=backend)

    first = _operation(
        workspace, f"run_{backend}_propose1", wiki, "propose", source, actor_origin="codex_fixture"
    )
    evaluation = _operation(
        workspace, f"run_{backend}_eval1", wiki, "evaluate", first["candidate_id"],
        actor_origin="independent_evaluator",
    )
    assert evaluation["status"] == "pass"

    accepted = _operation(
        workspace, f"run_{backend}_accept1", wiki, "decide", first["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="local_reviewed",
    )
    assert accepted["status"] == "accepted"
    assert wiki.semantic_state()["active_version_id"] is None

    activated = _operation(
        workspace, f"run_{backend}_activate1", wiki, "activate", accepted["version_id"],
        actor_origin="manager_acceptance",
    )
    assert activated["active_version_id"] == accepted["version_id"]
    human = _operation(
        workspace, f"run_{backend}_wiki1", wiki, "wiki_projection", "quality review",
        actor_origin="catalyst_deterministic",
    )
    machine = _operation(
        workspace, f"run_{backend}_ontology1", wiki, "ontology_projection", "quality review",
        actor_origin="catalyst_deterministic",
    )
    assert human["version_id"] == machine["version_id"] == accepted["version_id"]
    assert human["meaning_ids"] == machine["meaning_ids"]
    assert set(machine["meaning_ids"]) == set(first["meaning_ids"])

    source.write_text(source.read_text(encoding="utf-8") + "exception: quality_review_hotfix | Emergency hotfix is deferred to a follow-up review\n", encoding="utf-8")
    second = _operation(
        workspace, f"run_{backend}_propose2", wiki, "propose", source, actor_origin="codex_fixture"
    )
    diff = _operation(
        workspace, f"run_{backend}_diff2", wiki, "diff", second["candidate_id"],
        actor_origin="catalyst_deterministic",
    )
    assert diff["added_meaning_ids"]
    evaluation2 = _operation(
        workspace, f"run_{backend}_eval2", wiki, "evaluate", second["candidate_id"],
        actor_origin="independent_evaluator",
    )
    assert evaluation2["status"] == "pass"
    accepted2 = _operation(
        workspace, f"run_{backend}_accept2", wiki, "decide", second["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_revision",
    )
    _operation(
        workspace, f"run_{backend}_activate2", wiki, "activate", accepted2["version_id"],
        actor_origin="manager_acceptance",
    )
    rolled_back = _operation(
        workspace, f"run_{backend}_rollback", wiki, "rollback", accepted["version_id"],
        actor_origin="manager_acceptance",
    )
    assert rolled_back["active_version_id"] == accepted["version_id"]

    cold_wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj", backend=backend)
    cold = _operation(
        workspace, f"run_{backend}_cold_query", cold_wiki, "ontology_projection", "quality review",
        actor_origin="catalyst_deterministic",
    )
    assert cold["version_id"] == accepted["version_id"]
    assert set(cold["meaning_ids"]) == set(first["meaning_ids"])

    trace = JsonlTraceStore(workspace).inspect_run(f"run_{backend}_rollback")
    assert trace is not None and trace["terminal_status"] == "success"
    assert [event["event_type"] for event in trace["events"] if event["event_type"].startswith("semantic.")]
    assert all(event["run_id"] == f"run_{backend}_rollback" for event in trace["events"])


def test_self_approval_changed_source_and_conflict_fail_closed(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "rules.md"
    source.write_text("Rule: Reviewer signs before release\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")

    candidate = _operation(
        workspace, "run_candidate", wiki, "propose", source, actor_origin="codex_fixture"
    )
    _operation(
        workspace, "run_eval", wiki, "evaluate", candidate["candidate_id"],
        actor_origin="independent_evaluator",
    )
    with pytest.raises(SemanticTransitionError, match="separate"):
        _operation(
            workspace, "run_self_approve", wiki, "decide", candidate["candidate_id"],
            decision="ACCEPTED", actor_origin="codex_fixture", reason_code="self",
        )

    source.write_text("Rule: Reviewer may skip signing before release\n", encoding="utf-8")
    with pytest.raises(SemanticTransitionError, match="source revision"):
        _operation(
            workspace, "run_stale_accept", wiki, "decide", candidate["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="stale",
        )
    assert wiki.semantic_state()["active_version_id"] is None


def test_semantic_trace_unknown_fields_are_dropped_and_inputs_are_not_recorded(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "private.md"
    source.write_text("Rule: Credential redaction fixture\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    _operation(workspace, "run_privacy", wiki, "propose", source, actor_origin="codex_fixture")
    trace_text = JsonlTraceStore(workspace).path.read_text(encoding="utf-8")
    assert str(source) not in trace_text
    assert "Credential redaction fixture" not in trace_text
    assert "private.md" not in trace_text
    events = [json.loads(line) for line in trace_text.splitlines()]
    semantic = [event for event in events if event["event_type"].startswith("semantic.")]
    assert semantic
    assert all("raw_content" not in event and "arbitrary" not in event for event in semantic)


def _cold_cli(repo: Path, args: list[str]) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_cli_cold_process_lifecycle_and_v13_trace_schema(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "quality.md"
    source.write_text(
        "# Quality review\n"
        "Rule: Reviewer checks the package before release\n"
        "relation: reviewer | performs | quality_review\n"
        "Condition: quality_review_ready | Package is ready for review\n",
        encoding="utf-8",
    )
    common = [
        "--workspace", str(workspace), "--wiki-root", str(roots),
        "--enterprise-id", "ent", "--project-id", "proj",
    ]

    code, staged = _cold_cli(repo, ["ontology", "source", "stage", *common, "--file", str(source)])
    assert code == 0 and staged["status"] == "success", staged
    code, proposal = _cold_cli(repo, ["ontology", "candidate", "propose", *common, "--file", str(source)])
    assert code == 0 and proposal["result"]["status"] == "proposed", proposal
    candidate_id = proposal["result"]["candidate_id"]

    code, evaluated = _cold_cli(repo, ["ontology", "candidate", "evaluate", *common, "--candidate-id", candidate_id])
    assert code == 0 and evaluated["result"]["status"] == "pass", evaluated
    code, denied_accept = _cold_cli(repo, [
        "ontology", "candidate", "decide", *common,
        "--candidate-id", candidate_id, "--decision", "ACCEPTED", "--reason-code", "reviewed_fixture",
    ])
    assert code == 1 and denied_accept["error"]["code"] == "external_semantic_evaluation_required", denied_accept
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    authorized_accept = trusted_test_operation(
        workspace, wiki, "run_test_only_accept", "decide", candidate_id,
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_fixture",
    )
    accepted = {"run_id": authorized_accept["run_id"], "result": authorized_accept["result"]}
    version_id = accepted["result"]["version_id"]

    code, unknown = _cold_cli(repo, ["ontology", "query", *common, "--query", "reviewer"])
    assert code == 0 and unknown["result"]["status"] == "unknown", unknown
    code, denied_activation = _cold_cli(repo, ["ontology", "version", "activate", *common, "--version-id", version_id])
    assert code == 1 and denied_activation["error"]["code"] == "authority_receipt_required", denied_activation
    authorized_activation = trusted_test_operation(
        workspace, wiki, "run_test_only_activate", "activate", version_id,
        actor_origin="manager_acceptance", expected_head_version_id=None,
    )
    activated = {"run_id": authorized_activation["run_id"], "result": authorized_activation["result"]}
    assert activated["result"]["active_version_id"] == version_id
    code, machine = _cold_cli(repo, ["ontology", "query", *common, "--query", "reviewer"])
    assert code == 0 and machine["result"]["status"] == "success", machine
    code, human = _cold_cli(repo, ["ontology", "wiki", *common, "--query", "reviewer"])
    assert code == 0 and human["result"]["meaning_ids"] == machine["result"]["meaning_ids"], human

    trace_store = JsonlTraceStore(workspace)
    validators = {}
    for version in ("1.4", "1.5"):
        schema_name = f"run_event_v{version.replace('.', '_')}.schema.json"
        schema = json.loads((repo / "schemas" / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validators[version] = Draft202012Validator(schema)
    for run in (staged, proposal, evaluated, accepted, unknown, activated, machine, human):
        replay = trace_store.inspect_run(run["run_id"])
        assert replay is not None and replay["terminal_status"] == "success"
        for event in replay["events"]:
            validator = validators[event["event_schema_version"]]
            assert not list(validator.iter_errors(event)), (run["run_id"], event)
    consumed_run = trace_store.inspect_run(machine["run_id"])
    assert consumed_run is not None
    consumed_ids = {
        event["meaning_id"] for event in consumed_run["events"]
        if event["event_type"] == "semantic.consumer.meaning_consumed"
    }
    assert consumed_ids == set(machine["result"]["meaning_ids"])
    assert consumed_run["events"][-1]["event_type"] == "request.terminal"


def test_cli_missing_source_fails_with_terminal_trace_without_path_disclosure(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    missing = roots / "missing-private-name.md"
    args = [
        "ontology", "candidate", "propose", "--workspace", str(workspace),
        "--wiki-root", str(roots), "--enterprise-id", "ent", "--project-id", "proj",
        "--file", str(missing),
    ]
    code, outcome = _cold_cli(repo, args)
    assert code == 1 and outcome["status"] == "failure", outcome
    trace = JsonlTraceStore(workspace).inspect_run(outcome["run_id"])
    assert trace is not None and trace["terminal_status"] == "failure"
    text = JsonlTraceStore(workspace).path.read_text(encoding="utf-8")
    assert str(missing) not in text
    assert "missing-private-name.md" not in text
    assert any(event["event_type"] == "semantic.transition.failed" for event in trace["events"])


def test_json_and_sqlite_generate_the_same_semantic_id_lineage(tmp_path):
    identities = {}
    for backend in ("json", "sqlite"):
        workspace = tmp_path / backend / "workspace"
        roots = tmp_path / backend / "sources"
        roots.mkdir(parents=True)
        source = roots / "same.md"
        source.write_text(
            "Rule: Reviewer checks package before release\n"
            "relation: reviewer | performs | quality_review\n",
            encoding="utf-8",
        )
        wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="same", backend=backend)
        candidate = _operation(workspace, f"run_{backend}_propose", wiki, "propose", source, actor_origin="codex_fixture")
        evaluation = _operation(workspace, f"run_{backend}_evaluate", wiki, "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
        decision = _operation(workspace, f"run_{backend}_decide", wiki, "decide", candidate["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="approved_fixture")
        identities[backend] = (
            candidate["candidate_id"], tuple(candidate["meaning_ids"]), evaluation["evaluation_id"],
            decision["decision_id"], decision["version_id"],
        )
    assert identities["json"] == identities["sqlite"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_reproposing_same_source_revision_after_activation_is_no_op(tmp_path, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "stable.md"
    source.write_text("Rule: The reviewer checks the release package\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="stable", backend=backend)

    first = _operation(workspace, f"run_{backend}_first", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, f"run_{backend}_evaluate", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    accepted = _operation(
        workspace, f"run_{backend}_accept", wiki, "decide", first["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed",
    )
    _operation(workspace, f"run_{backend}_activate", wiki, "activate", accepted["version_id"], actor_origin="manager_acceptance")

    repeated = _operation(workspace, f"run_{backend}_repeat", wiki, "propose", source, actor_origin="codex_fixture")

    assert repeated["status"] == "no_op"
    assert repeated["candidate_id"] == first["candidate_id"]
    assert wiki.semantic_state()["active_version_id"] == accepted["version_id"]
    trace = JsonlTraceStore(workspace).inspect_run(f"run_{backend}_repeat")
    proposal_events = [event for event in trace["events"] if event["event_type"] == "semantic.candidate.proposed"]
    assert len(proposal_events) == 1 and proposal_events[0]["status"] == "no_op"


def test_failed_noop_proposal_does_not_delete_the_existing_candidate(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "repeat.md"
    source.write_text("Rule: Stable repeated statement\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first = _operation(workspace, "run_noop_first", wiki, "propose", source, actor_origin="codex_fixture")

    recorder = _recorder(workspace, "run_noop_failed")
    service = SemanticWiki(wiki, recorder=recorder)
    repeated = service.propose(source, actor_origin="codex_fixture")
    assert repeated["status"] == "no_op"
    recorder.finish("failure", model_calls=0, error_owner="simulated_terminal_failure")
    service.finalize_run(recorder.run_id, "failure")

    assert first["candidate_id"] in wiki.semantic_state()["candidates"]


def test_failed_repeated_evaluation_preserves_the_existing_evaluation(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "repeat_eval.md"
    source.write_text("Rule: Stable evaluation candidate\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    candidate = _operation(workspace, "run_eval_first_propose", wiki, "propose", source, actor_origin="codex_fixture")
    first = _operation(workspace, "run_eval_first", wiki, "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")

    recorder = _recorder(workspace, "run_eval_repeat_failed")
    service = SemanticWiki(wiki, recorder=recorder)
    repeated = service.evaluate(candidate["candidate_id"], actor_origin="independent_evaluator")
    assert repeated["evaluation_id"] == first["evaluation_id"]
    recorder.finish("failure", model_calls=0, error_owner="simulated_terminal_failure")
    service.finalize_run(recorder.run_id, "failure")

    state = wiki.semantic_state()
    assert first["evaluation_id"] in state["evaluations"]
    assert state["candidates"][candidate["candidate_id"]]["latest_evaluation_id"] == first["evaluation_id"]


def test_failed_repeated_acceptance_preserves_existing_accepted_version(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "repeat_accept.md"
    source.write_text("Rule: Stable accepted candidate\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    candidate = _operation(workspace, "run_accept_first_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_accept_first_eval", wiki, "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
    first = _operation(workspace, "run_accept_first", wiki, "decide", candidate["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")

    recorder = _recorder(workspace, "run_accept_repeat_failed", event_schema_version="1.5")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    kwargs = {"decision": "ACCEPTED", "actor_origin": "manager_acceptance", "reason_code": "reviewed"}
    authorized_kwargs = authorize_test_operation(service, "decide", (candidate["candidate_id"],), kwargs)
    repeated = service.decide(candidate["candidate_id"], **authorized_kwargs)
    assert repeated["decision_id"] == first["decision_id"]
    recorder.finish("failure", model_calls=0, error_owner="simulated_terminal_failure")
    service.finalize_run(recorder.run_id, "failure")

    state = wiki.semantic_state()
    assert first["decision_id"] in state["decisions"]
    assert first["version_id"] in state["accepted_versions"]


def test_conflicting_relation_is_flagged_and_cannot_replace_active_meaning(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "handoff.md"
    source.write_text("relation: reviewer | may_skip | no\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first = _operation(workspace, "run_first_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_first_eval", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    accepted = _operation(workspace, "run_first_decide", wiki, "decide", first["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    _operation(workspace, "run_first_activate", wiki, "activate", accepted["version_id"], actor_origin="manager_acceptance")

    source.write_text("relation: reviewer | may_skip | yes\n", encoding="utf-8")
    second = _operation(workspace, "run_second_propose", wiki, "propose", source, actor_origin="codex_fixture")
    evaluation = _operation(workspace, "run_second_eval", wiki, "evaluate", second["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "needs_review"
    assert any(item["code"] == "active_meaning_conflict" for item in evaluation["findings"])
    with pytest.raises(SemanticTransitionError, match="cannot be accepted"):
        _operation(workspace, "run_second_accept", wiki, "decide", second["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    rejected = _operation(workspace, "run_second_reject", wiki, "decide", second["candidate_id"], decision="REJECTED", actor_origin="manager_acceptance", reason_code="conflict_rejected")
    assert rejected["status"] == "rejected"
    assert wiki.semantic_state()["active_version_id"] == accepted["version_id"]


def test_explicit_condition_key_conflict_requires_review_and_preserves_active_version(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "condition.md"
    source.write_text("Condition: source_link_required | Reviewer must include a source link\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first = _operation(workspace, "run_condition_first", wiki, "propose", source, actor_origin="codex_fixture")
    first_entry = wiki.semantic_state()["candidates"][first["candidate_id"]]["entries"][0]
    assert first_entry["key"] == "source_link_required"
    _operation(workspace, "run_condition_first_eval", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    accepted = _operation(
        workspace, "run_condition_first_accept", wiki, "decide", first["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed",
    )
    _operation(workspace, "run_condition_first_activate", wiki, "activate", accepted["version_id"], actor_origin="manager_acceptance")

    source.write_text("Condition: source_link_required | Reviewer may omit a source link\n", encoding="utf-8")
    second = _operation(workspace, "run_condition_second", wiki, "propose", source, actor_origin="codex_fixture")
    assert second["meaning_ids"] == first["meaning_ids"]
    evaluation = _operation(
        workspace, "run_condition_second_eval", wiki, "evaluate", second["candidate_id"],
        actor_origin="independent_evaluator",
    )
    assert evaluation["status"] == "needs_review"
    assert any(item["code"] == "active_meaning_conflict" for item in evaluation["findings"])
    with pytest.raises(SemanticTransitionError, match="cannot be accepted"):
        _operation(
            workspace, "run_condition_second_accept", wiki, "decide", second["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="must_review",
        )
    assert wiki.semantic_state()["active_version_id"] == accepted["version_id"]


def test_explicit_claim_marker_creates_a_source_anchored_meaning(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "claim.md"
    source.write_text("Claim: A reviewer records the evidence source\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")

    proposed = _operation(workspace, "run_explicit_claim", wiki, "propose", source, actor_origin="codex_fixture")

    assert proposed["status"] == "proposed"
    entry = wiki.semantic_state()["candidates"][proposed["candidate_id"]]["entries"][0]
    assert entry["kind"] == "claim"
    assert entry["meaning"] == "A reviewer records the evidence source"
    assert entry["source_id"] == proposed["source_id"]
    assert entry["line_start"] == entry["line_end"] == 1
    assert entry["claim_id"] is None


def test_malformed_explicit_relation_is_not_silently_dropped(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "malformed.md"
    source.write_text("Rule: A valid statement\nrelation: reviewer | performs\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")

    with pytest.raises(SemanticTransitionError, match="relation marker") as failure:
        _operation(workspace, "run_malformed_relation", wiki, "propose", source, actor_origin="codex_fixture")
    assert failure.value.code == "invalid_marker"
    assert wiki.semantic_state()["candidates"] == {}


def test_same_meaning_from_multiple_sources_retains_each_source_evidence(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_a = roots / "source_a.md"
    source_b = roots / "source_b.md"
    source_a.write_text("Condition: review_gate | Reviewer must keep a source link\n", encoding="utf-8")
    source_b.write_text("Condition: review_gate | Reviewer must keep a source link\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")

    first = _operation(workspace, "run_source_a_propose", wiki, "propose", source_a, actor_origin="codex_fixture")
    _operation(workspace, "run_source_a_eval", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    accepted_a = _operation(workspace, "run_source_a_accept", wiki, "decide", first["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="source_a_reviewed")
    _operation(workspace, "run_source_a_activate", wiki, "activate", accepted_a["version_id"], actor_origin="manager_acceptance")

    second = _operation(workspace, "run_source_b_propose", wiki, "propose", source_b, actor_origin="codex_fixture")
    meaning_id = first["meaning_ids"][0]
    assert second["meaning_ids"] == [meaning_id]
    _operation(workspace, "run_source_b_eval", wiki, "evaluate", second["candidate_id"], actor_origin="independent_evaluator")
    diff_add = _operation(workspace, "run_source_b_diff", wiki, "diff", second["candidate_id"], actor_origin="catalyst_deterministic")
    assert diff_add["evidence_added_meaning_ids"] == [meaning_id]
    event_schema_path = Path(__file__).parents[1] / "schemas" / "run_event_v1_4.schema.json"
    event_schema = json.loads(event_schema_path.read_text(encoding="utf-8"))
    diff_trace = JsonlTraceStore(workspace).inspect_run("run_source_b_diff")
    diff_event = next(event for event in diff_trace["events"] if event["event_type"] == "semantic.version.diffed")
    Draft202012Validator(event_schema).validate(diff_event)
    assert event_schema["$id"].endswith("run-event-v1.4.schema.json")
    assert diff_event["evidence_added_count"] == 1
    assert diff_event["evidence_removed_count"] == 0
    accepted_b = _operation(workspace, "run_source_b_accept", wiki, "decide", second["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="source_b_reviewed")
    _operation(workspace, "run_source_b_activate", wiki, "activate", accepted_b["version_id"], actor_origin="manager_acceptance")
    both_sources = _operation(workspace, "run_both_sources_query", wiki, "query", "review_gate", actor_origin="catalyst_deterministic")
    meaning = both_sources["meanings"][0]
    assert {item["source_id"] for item in meaning["evidence"]} == {first["source_id"], second["source_id"]}
    consume_trace = JsonlTraceStore(workspace).inspect_run("run_both_sources_query")
    consumed_sources = {
        event["source_id"] for event in consume_trace["events"]
        if event["event_type"] == "semantic.consumer.meaning_consumed" and event["meaning_id"] == meaning_id
    }
    assert consumed_sources == {first["source_id"], second["source_id"]}

    source_b.write_text("Rule: Source B now contains a separate bookkeeping note\n", encoding="utf-8")
    third = _operation(workspace, "run_source_b_update_propose", wiki, "propose", source_b, actor_origin="codex_fixture")
    _operation(workspace, "run_source_b_update_eval", wiki, "evaluate", third["candidate_id"], actor_origin="independent_evaluator")
    diff_remove = _operation(workspace, "run_source_b_update_diff", wiki, "diff", third["candidate_id"], actor_origin="catalyst_deterministic")
    assert diff_remove["removed_meaning_ids"] == []
    assert diff_remove["evidence_removed_meaning_ids"] == [meaning_id]
    remove_trace = JsonlTraceStore(workspace).inspect_run("run_source_b_update_diff")
    remove_event = next(event for event in remove_trace["events"] if event["event_type"] == "semantic.version.diffed")
    Draft202012Validator(event_schema).validate(remove_event)
    assert remove_event["evidence_added_count"] == 0
    assert remove_event["evidence_removed_count"] == 1
    accepted_c = _operation(workspace, "run_source_b_update_accept", wiki, "decide", third["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="source_b_updated")
    _operation(workspace, "run_source_b_update_activate", wiki, "activate", accepted_c["version_id"], actor_origin="manager_acceptance")
    remaining = _operation(workspace, "run_source_a_remains_query", wiki, "query", "review_gate", actor_origin="catalyst_deterministic")
    assert remaining["meaning_ids"] == [meaning_id]
    assert [item["source_id"] for item in remaining["meanings"][0]["evidence"]] == [first["source_id"]]


def test_corrupt_semantic_evidence_and_active_pointer_fail_closed(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "state.md"
    source.write_text("Claim: A review requires a source link\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    candidate = _operation(workspace, "run_state_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_state_evaluate", wiki, "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
    accepted = _operation(workspace, "run_state_accept", wiki, "decide", candidate["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    _operation(workspace, "run_state_activate", wiki, "activate", accepted["version_id"], actor_origin="manager_acceptance")

    store_path = workspace / ".catalyst" / "wiki" / "ent" / "proj" / "wiki.json"
    document = json.loads(store_path.read_text(encoding="utf-8"))
    semantic = document["semantic"]
    descriptor = semantic["accepted_versions"][semantic["active_version_id"]]["meanings"]["_artifact"]
    meanings_path = store_path.parent / descriptor["path"]
    original = meanings_path.read_bytes()
    meanings = [json.loads(line) for line in original.decode("utf-8").splitlines() if line.strip()]
    meanings[0]["evidence"][0]["span_sha256"] = "bad-hash"
    meanings_path.write_text(chr(10).join(json.dumps(row) for row in meanings) + chr(10), encoding="utf-8")

    reopened = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    with pytest.raises(WikiUnavailable, match="does not match its recorded digest"):
        reopened.semantic_state()

    meanings_path.write_bytes(original)
    semantic["active_version_id"] = "version_missing"
    store_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(WikiUnavailable, match="semantic state is unreadable"):
        ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj").semantic_state()


def test_failed_activation_is_recovered_to_previous_version_from_cold_process(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "version.md"
    source.write_text("Rule: First reviewed instruction\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first = _operation(workspace, "run_v1_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_v1_eval", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    v1 = _operation(workspace, "run_v1_accept", wiki, "decide", first["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    _operation(workspace, "run_v1_activate", wiki, "activate", v1["version_id"], actor_origin="manager_acceptance")

    source.write_text("Rule: Second reviewed instruction\n", encoding="utf-8")
    second = _operation(workspace, "run_v2_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_v2_eval", wiki, "evaluate", second["candidate_id"], actor_origin="independent_evaluator")
    v2 = _operation(workspace, "run_v2_accept", wiki, "decide", second["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")

    failed_recorder = _recorder(workspace, "run_crashed_activation", event_schema_version="1.5")
    failed_service = SemanticWiki(wiki, recorder=failed_recorder, receipt_verifier=verify_test_receipt)
    activation_kwargs = {"actor_origin": "manager_acceptance"}
    activation_kwargs = authorize_test_operation(failed_service, "activate", (v2["version_id"],), activation_kwargs)
    failed_service.activate(v2["version_id"], **activation_kwargs)
    failed_recorder.finish("failure", model_calls=0, error_owner="simulated_process_stop")
    # Deliberately skip finalize_run to model process loss after pointer change.
    assert wiki.semantic_state()["active_version_id"] == v2["version_id"]

    recovery_recorder = _recorder(workspace, "run_recovery_inspect")
    recovered = SemanticWiki(wiki, recorder=recovery_recorder)
    assert wiki.semantic_state()["active_version_id"] == v1["version_id"]
    assert any(
        event["event_type"] == "semantic.transition.recovered" and event["status"] == "recovered_rollback"
        for event in JsonlTraceStore(workspace).inspect_run("run_recovery_inspect")["events"]
    )
    recovery_recorder.finish("success", model_calls=0)
    recovered.finalize_run("run_recovery_inspect", "success")


def test_failed_active_pointer_write_preserves_previous_version_and_failure_trace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "write_failure.md"
    source.write_text("Rule: First accepted rule\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first = _operation(workspace, "run_write_v1_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_write_v1_eval", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    v1 = _operation(workspace, "run_write_v1_accept", wiki, "decide", first["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    _operation(workspace, "run_write_v1_activate", wiki, "activate", v1["version_id"], actor_origin="manager_acceptance")

    source.write_text("Rule: Second accepted rule\n", encoding="utf-8")
    second = _operation(workspace, "run_write_v2_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_write_v2_eval", wiki, "evaluate", second["candidate_id"], actor_origin="independent_evaluator")
    v2 = _operation(workspace, "run_write_v2_accept", wiki, "decide", second["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")

    recorder = _recorder(workspace, "run_write_failed_activation", event_schema_version="1.5")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    original_save = wiki._store.save
    calls = 0

    def fail_pointer_write(value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("controlled local write failure")
        return original_save(value)

    monkeypatch.setattr(wiki._store, "save", fail_pointer_write)
    with pytest.raises(Exception):
        activation_kwargs = authorize_test_operation(
            service, "activate", (v2["version_id"],), {"actor_origin": "manager_acceptance"}
        )
        service.activate(v2["version_id"], **activation_kwargs)
    monkeypatch.undo()
    recorder.event(
        "semantic.transition.failed", operation="version.activate", status="failure",
        error_code="controlled_write_failure", actor_origin="manager_acceptance",
        scope_id=wiki.scope_id, version_id=v2["version_id"],
    )
    recorder.finish("failure", model_calls=0, error_owner="wiki_store")
    service.finalize_run(recorder.run_id, "failure")

    assert wiki.semantic_state()["active_version_id"] == v1["version_id"]
    trace = JsonlTraceStore(workspace).inspect_run("run_write_failed_activation")
    assert trace is not None and trace["terminal_status"] == "failure"
    assert any(event["event_type"] == "semantic.transition.failed" for event in trace["events"])


def test_missing_transition_trace_recovers_active_pointer_without_claiming_old_run_success(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "trace_loss.md"
    source.write_text("Rule: Original bounded rule\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first = _operation(workspace, "run_trace_v1_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_trace_v1_evaluate", wiki, "evaluate", first["candidate_id"], actor_origin="independent_evaluator")
    v1 = _operation(workspace, "run_trace_v1_accept", wiki, "decide", first["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    _operation(workspace, "run_trace_v1_activate", wiki, "activate", v1["version_id"], actor_origin="manager_acceptance")

    source.write_text("Rule: Candidate rule after pointer change\n", encoding="utf-8")
    second = _operation(workspace, "run_trace_v2_propose", wiki, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_trace_v2_evaluate", wiki, "evaluate", second["candidate_id"], actor_origin="independent_evaluator")
    v2 = _operation(workspace, "run_trace_v2_accept", wiki, "decide", second["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    failed_recorder = _recorder(workspace, "run_trace_missing_activation", event_schema_version="1.5")
    failed_service = SemanticWiki(wiki, recorder=failed_recorder, receipt_verifier=verify_test_receipt)
    activation_kwargs = authorize_test_operation(
        failed_service, "activate", (v2["version_id"],), {"actor_origin": "manager_acceptance"}
    )
    failed_service.activate(v2["version_id"], **activation_kwargs)
    failed_recorder.finish("failure", model_calls=0, error_owner="simulated_trace_loss")
    assert wiki.semantic_state()["active_version_id"] == v2["version_id"]

    JsonlTraceStore(workspace).path.unlink()
    recovery = _operation(workspace, "run_trace_missing_recovery", wiki, "inspect", actor_origin="catalyst_deterministic")

    assert recovery["active_version_id"] == v1["version_id"]
    replay = JsonlTraceStore(workspace).inspect_run("run_trace_missing_recovery")
    assert replay is not None and replay["terminal_status"] == "success"
    recovered = [event for event in replay["events"] if event["event_type"] == "semantic.transition.recovered"]
    assert len(recovered) == 1 and recovered[0]["status"] == "recovered_rollback"
    assert JsonlTraceStore(workspace).inspect_run("run_trace_missing_activation") is None


def test_semantic_state_isolated_by_project_scope(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "scope.md"
    source.write_text("Rule: Project Alpha review duty\n", encoding="utf-8")
    alpha = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="alpha")
    proposal = _operation(workspace, "run_alpha_propose", alpha, "propose", source, actor_origin="codex_fixture")
    _operation(workspace, "run_alpha_eval", alpha, "evaluate", proposal["candidate_id"], actor_origin="independent_evaluator")
    accepted = _operation(workspace, "run_alpha_accept", alpha, "decide", proposal["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    _operation(workspace, "run_alpha_activate", alpha, "activate", accepted["version_id"], actor_origin="manager_acceptance")
    beta = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="beta")
    result = _operation(workspace, "run_beta_query", beta, "ontology_projection", "review duty", actor_origin="catalyst_deterministic")
    assert result["status"] == "unknown"
    assert result["version_id"] is None

def _accept_one_version(workspace, roots, prefix):
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    source = roots / f"{prefix}.md"
    source.write_text("Rule: A review requires a source link\n", encoding="utf-8")
    candidate = _operation(workspace, f"run_{prefix}_propose", wiki, "propose", source,
                           actor_origin="codex_fixture")
    _operation(workspace, f"run_{prefix}_evaluate", wiki, "evaluate", candidate["candidate_id"],
               actor_origin="independent_evaluator")
    accepted = _operation(workspace, f"run_{prefix}_accept", wiki, "decide", candidate["candidate_id"],
                          decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed")
    return wiki, candidate, accepted


def test_acceptance_keeps_the_comparison_the_reviewer_approved(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    wiki, candidate, accepted = _accept_one_version(workspace, roots, "recorded")

    state = wiki.semantic_state()
    entries = [entry["meaning_id"] for entry in state["candidates"][candidate["candidate_id"]]["entries"]]
    stored = state["accepted_versions"][accepted["version_id"]]["diff"]

    assert stored["added_meaning_ids"] == sorted(entries)
    assert stored["removed_meaning_ids"] == []
    assert stored["carried_meaning_ids"] == []

    read = _operation(workspace, "run_recorded_diff_read", wiki, "accepted_version_diff",
                      accepted["version_id"])
    assert read["source"] == "stored"
    assert read["added_meaning_ids"] == stored["added_meaning_ids"]

    code, payload = _cold_cli(Path(__file__).resolve().parents[1], [
        "ontology", "version", "diff",
        "--workspace", str(workspace), "--wiki-root", str(roots),
        "--enterprise-id", "ent", "--project-id", "proj",
        "--version-id", accepted["version_id"],
    ])
    assert code == 0, payload
    assert payload["result"]["source"] == "stored"
    assert payload["result"]["added_meaning_ids"] == stored["added_meaning_ids"]


def test_a_version_accepted_before_diffs_were_kept_is_compared_on_read(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    wiki, _, accepted = _accept_one_version(workspace, roots, "legacy")

    store_path = workspace / ".catalyst" / "wiki" / "ent" / "proj" / "wiki.json"
    document = json.loads(store_path.read_text(encoding="utf-8"))
    stored = document["semantic"]["accepted_versions"][accepted["version_id"]].pop("diff")
    store_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    reopened = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    read = _operation(workspace, "run_legacy_diff_read", reopened, "accepted_version_diff",
                      accepted["version_id"])

    assert read["source"] == "computed"
    assert read["added_meaning_ids"] == stored["added_meaning_ids"]


def test_a_broken_stored_diff_fails_closed(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    _, _, accepted = _accept_one_version(workspace, roots, "damaged")

    store_path = workspace / ".catalyst" / "wiki" / "ent" / "proj" / "wiki.json"
    document = json.loads(store_path.read_text(encoding="utf-8"))
    document["semantic"]["accepted_versions"][accepted["version_id"]]["diff"]["added_meaning_ids"] = "not-a-list"
    store_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    reopened = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    with pytest.raises(WikiUnavailable, match="semantic state is unreadable"):
        reopened.semantic_state()

