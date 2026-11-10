from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from agent_runtime.contracts import CapabilityDescriptor as RuntimeCapabilityDescriptor
from platform_standard.validation import ValidationError

from catalyst_platform.workbench import CapabilityConflictError, CatalystWorkbench


class _UncertainCapability:
    def __init__(self):
        self.invoke_count = 0

    def describe(self):
        return RuntimeCapabilityDescriptor(
            id="uncertain_test",
            name="Uncertain test",
            description="raises after an invocation attempt",
            input_schema={"type": "object"},
            output_schema={
                "type": "object",
                "properties": {"accepted": {"type": "boolean"}},
                "required": ["accepted"],
                "additionalProperties": False,
            },
        )

    def invoke(self, parameters, context):
        self.invoke_count += 1
        raise RuntimeError("fixture cannot establish the external outcome")


def _make_wiki(tmp_path: Path) -> tuple[Path, Path]:
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    source = wiki / "operating-model.md"
    source.write_text(
        "# Catalyst operating model\n\n"
        "Catalyst is an Organization-AI Capability Operating Model.\n"
        "Stable WHAT / Replaceable HOW keeps responsibility durable while its implementation can change.\n"
        "Domain and Enterprise are parallel semantic dimensions.\n",
        encoding="utf-8",
    )
    return wiki, source


def _contexts(report_detail: str = "full", allow_local_artifacts: bool = True):
    return (
        {"id": "software-engineering", "scope": "source-grounded product work"},
        {
            "id": "enterprise-a",
            "report_detail": report_detail,
            "allow_local_artifacts": allow_local_artifacts,
            "allow_remote_writes": False,
        },
    )


def test_use_writes_a_source_grounded_result_and_end_to_end_trace(tmp_path: Path):
    wiki, source = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    domain, enterprise = _contexts()

    run = app.use(
        query="How should Catalyst keep responsibilities stable while implementations change?",
        domain=domain,
        enterprise=enterprise,
        output_name="catalyst-brief.md",
    )

    assert run.result.status == "success"
    assert len(run.result.artifacts) == 1
    artifact_path = run.artifact_paths[0]
    assert artifact_path.is_file()
    report = artifact_path.read_text(encoding="utf-8")
    assert "Stable WHAT / Replaceable HOW" in report
    assert str(source.resolve()) in report
    assert run.trace["domain"]["id"] == "software-engineering"
    assert run.trace["enterprise"]["id"] == "enterprise-a"
    assert run.trace["selected_evidence"]
    assert run.trace["selected_evidence"][0]["source_path"] == str(source.resolve())
    assert run.result.output["artifact_sha256"] == hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    assert run.trace["provider"]["mode"] == "offline"
    assert run.trace["agent_loop_count"] == 1
    event_names = [event["event"] for event in run.trace["events"]]
    assert "knowledge.retrieved" in event_names
    assert "capability.bound" in event_names
    assert "knowledge.consumed_for_decision" in event_names
    assert "artifact.created" in event_names
    assert event_names[-1] == "run.completed"
    assert [call["capability_id"] for call in run.trace["capability_calls"]] == [
        "wiki_search",
        "compose_report",
        "write_artifact",
    ]
    original_bytes = artifact_path.read_bytes()
    overwrite_attempt = app.use(
        query="Which semantic dimensions remain parallel?",
        domain=domain,
        enterprise=enterprise,
        output_name="catalyst-brief.md",
    )
    assert overwrite_attempt.result.status == "failure"
    assert artifact_path.read_bytes() == original_bytes


def test_wiki_index_summary_without_resolved_source_cannot_support_a_result(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    index = wiki / "index.json"
    index.write_text(
        json.dumps({"entries": [{"summary": "secretwort-771 controls an imaginary decision."}]}),
        encoding="utf-8",
    )
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki], wiki_index=index)

    run = app.use(
        query="secretwort-771",
        domain={"id": "software-engineering"},
        enterprise={"id": "enterprise-a", "allow_local_artifacts": True, "allow_remote_writes": False},
        output_name="unsupported.md",
    )

    assert run.result.status == "failure"
    assert run.result.error["code"] == "insufficient_evidence"
    assert not (tmp_path / "artifacts" / "unsupported.md").exists()


def test_malformed_wiki_index_is_attributed_as_a_known_retrieval_failure(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    index = wiki / "index.json"
    index.write_text("{broken", encoding="utf-8")
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki], wiki_index=index)

    run = app.use(
        query="Catalyst operating model",
        domain={"id": "software-engineering"},
        enterprise={"id": "enterprise-a", "allow_local_artifacts": True, "allow_remote_writes": False},
        output_name="malformed-index.md",
    )

    assert run.result.status == "failure"
    assert run.trace["failure_source"] == "wiki_search"
    assert run.trace["native_runtime"]["pending_execution_id"] is None


def test_enterprise_extension_changes_result_without_collapsing_domain(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    domain, full_enterprise = _contexts("full")
    _, brief_enterprise = _contexts("brief")

    full = app.use(
        query="What does Catalyst keep stable?",
        domain=domain,
        enterprise=full_enterprise,
        output_name="full.md",
    )
    brief = app.use(
        query="What does Catalyst keep stable?",
        domain=domain,
        enterprise=brief_enterprise,
        output_name="brief.md",
    )

    assert full.result.status == brief.result.status == "success"
    assert full.trace["domain"] == brief.trace["domain"]
    assert full.trace["enterprise"]["report_detail"] != brief.trace["enterprise"]["report_detail"]
    assert full.result.output["report_text"] != brief.result.output["report_text"]


def test_enterprise_source_allowlist_precedes_retrieval_and_rejects_unknown_scope(tmp_path: Path):
    wiki = tmp_path / "wiki"
    tenant_a = wiki / "enterprise-a.md"
    tenant_b = wiki / "enterprise-b.md"
    wiki.mkdir()
    tenant_a.write_text(
        "# Catalyst policy\n\nEnterprise A report_detail is brief; A-only marker: amber-431.\n",
        encoding="utf-8",
    )
    tenant_b.write_text(
        "# Catalyst policy\n\nEnterprise B report_detail is full; B-only marker: cobalt-927.\n",
        encoding="utf-8",
    )
    app = CatalystWorkbench(
        workspace=tmp_path,
        wiki_roots=[wiki],
        enterprise_source_allowlist={
            "enterprise-a": [tenant_a],
            "enterprise-b": [tenant_b],
        },
    )

    domain, enterprise_a = _contexts()
    result_a = app.use(
        query="Catalyst policy marker",
        domain=domain,
        enterprise=enterprise_a,
        output_name="tenant-a.md",
    )
    assert result_a.result.status == "success"
    report_a = result_a.artifact_paths[0].read_text(encoding="utf-8")
    assert "amber-431" in report_a
    assert "cobalt-927" not in report_a
    assert all(row["source_path"] != str(tenant_b.resolve()) for row in result_a.trace["selected_evidence"])
    assert "amber-431" not in json.dumps(result_a.trace, ensure_ascii=False)

    app.acquire_ripgrep()
    search_a = app.new_session(domain=domain, enterprise=enterprise_a).invoke(
        "ripgrep_search",
        "1.0.0",
        {"query": "cobalt-927"},
        invocation_id="tenant-a-rg-001",
    )
    assert search_a.result.status == "success"
    assert search_a.result.output["matches"] == []

    result_b = app.use(
        query="Catalyst policy marker",
        domain=domain,
        enterprise={
            "id": "enterprise-b",
            "report_detail": "full",
            "allow_local_artifacts": True,
            "allow_remote_writes": False,
        },
        output_name="tenant-b.md",
    )
    report_b = result_b.artifact_paths[0].read_text(encoding="utf-8")
    assert result_b.result.status == "success"
    assert "cobalt-927" in report_b
    assert "amber-431" not in report_b

    denied = app.use(
        query="Catalyst policy marker",
        domain=domain,
        enterprise={"id": "unregistered-enterprise", "allow_local_artifacts": True, "allow_remote_writes": False},
        output_name="unregistered.md",
    )
    assert denied.result.status == "failure"
    assert denied.result.error["code"] == "permission_denied"
    assert denied.trace["failure_source"] == "enterprise_policy"
    assert all(call["status"] == "denied" for call in denied.trace["capability_calls"])
    assert "knowledge.retrieved" not in [event["event"] for event in denied.trace["events"]]
    assert not (tmp_path / "artifacts" / "unregistered.md").exists()


def test_acquired_ripgrep_is_exactly_bound_noop_on_repeat_and_available_in_new_session(tmp_path: Path):
    wiki, source = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])

    first = app.acquire_ripgrep()
    second = app.acquire_ripgrep()

    assert first.status == "registered"
    assert first.license == "MIT OR Unlicense"
    assert second.status == "no-op"
    assert first.capability_id == second.capability_id == "ripgrep_search"
    assert first.executable_sha256 == second.executable_sha256

    fresh_app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    session = fresh_app.new_session(domain={"id": "software-engineering"}, enterprise={"id": "enterprise-a"})
    discovered = {(item.id, item.capability_version) for item in session.discover()}
    assert ("ripgrep_search", first.version) in discovered

    result = session.invoke(
        "ripgrep_search",
        first.version,
        {"query": "Stable WHAT / Replaceable HOW"},
        invocation_id="acquire-use-001",
    )
    assert result.result.status == "success"
    assert result.result.output["matches"][0]["source_path"] == str(source.resolve())


def test_failed_external_rebinding_leaves_the_catalog_unchanged(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    app.capability_manifest.parent.mkdir(parents=True, exist_ok=True)
    app.capability_manifest.write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "external": {"ripgrep_search": {"binding_version": "9.9.9", "identity": "different"}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CapabilityConflictError, match="already acquired"):
        app.acquire_ripgrep()

    assert "ripgrep_search" not in {item.id for item in app.new_session(domain={}, enterprise={}).discover()}
    assert json.loads(app.capability_manifest.read_text(encoding="utf-8"))["external"]["ripgrep_search"]["identity"] == "different"


def test_same_descriptor_version_cannot_silently_rebind_to_another_implementation(tmp_path: Path):
    class BoundValue:
        def __init__(self, value):
            self.value = value

        def describe(self):
            return RuntimeCapabilityDescriptor(
                id="exact_test",
                name="Exact test",
                description="exact version binding identity fixture",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )

        def invoke(self, parameters, context):
            from agent_runtime.contracts import Success

            return Success({"value": self.value})

    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    first = BoundValue("first")
    second = BoundValue("second")
    app.register_capability(
        first.describe(), capability_version="1.0.0", execution={"side_effect": "none"}, implementation=first
    )

    with pytest.raises(CapabilityConflictError, match="different identity"):
        app.register_capability(
            second.describe(), capability_version="1.0.0", execution={"side_effect": "none"}, implementation=second
        )


def test_duplicate_tool_invocation_is_noop_and_does_not_execute_twice(tmp_path: Path):
    wiki, source = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    app.acquire_ripgrep()
    session = app.new_session(
        domain={"id": "software-engineering"},
        enterprise={
            "id": "enterprise-a",
            "allow_local_artifacts": True,
            "allow_remote_writes": False,
        },
    )
    parameters = {"query": "Organization-AI Capability Operating Model"}

    first = session.invoke("ripgrep_search", "1.0.0", parameters, invocation_id="same-call")
    duplicate = session.invoke("ripgrep_search", "1.0.0", parameters, invocation_id="same-call")

    assert first.result.status == "success"
    assert not first.deduplicated
    assert duplicate.deduplicated
    assert duplicate.result.id == first.result.id
    assert session.tool_execution_count("ripgrep_search") == 1
    conflict = session.invoke(
        "ripgrep_search",
        "1.0.0",
        {"query": "different query"},
        invocation_id="same-call",
    )
    assert conflict.result.error["code"] == "idempotency_conflict"
    assert conflict.trace_path is not None and conflict.trace_path.is_file()
    assert session.tool_execution_count("ripgrep_search") == 1


def test_unknown_side_effect_is_rejected_before_any_capability_binding(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    descriptor = RuntimeCapabilityDescriptor(
        id="unsafe_probe",
        name="Unsafe probe",
        description="must never be called",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )

    with pytest.raises(ValidationError):
        app.register_capability(
            descriptor,
            capability_version="1.0.0",
            execution={"side_effect": "unknown"},
            implementation=object(),
        )


def test_native_runtime_unsupported_input_schema_is_rejected_at_registration(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    descriptor = RuntimeCapabilityDescriptor(
        id="unsupported_schema",
        name="Unsupported schema",
        description="Native Runtime does not silently ignore minLength",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 1}},
        },
        output_schema={"type": "object"},
    )

    with pytest.raises(CapabilityConflictError, match="Native Runtime input schema"):
        app.register_capability(
            descriptor,
            capability_version="1.0.0",
            execution={"side_effect": "none"},
            implementation=object(),
        )


def test_enterprise_permission_denial_creates_no_artifact(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    domain, enterprise = _contexts(allow_local_artifacts=False)

    run = app.use(
        query="What is Catalyst?",
        domain=domain,
        enterprise=enterprise,
        output_name="denied.md",
    )

    assert run.result.status == "failure"
    assert run.result.error["code"] == "permission_denied"
    assert run.trace["failure_source"] == "enterprise_policy"
    assert not (tmp_path / "artifacts" / "denied.md").exists()


def test_evolve_understand_uses_independent_evaluation_then_activates_and_rolls_back(tmp_path: Path):
    wiki, source = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    app.acquire_ripgrep()

    evolution = app.evolve_understand(
        benchmark=[
            {
                "query": "Domain and Enterprise are parallel semantic dimensions.",
                "expected_source": str(source.resolve()),
                "expected_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "expected_text": "Domain and Enterprise are parallel semantic dimensions.",
            }
        ],
        activate=True,
    )

    assert evolution.evaluation.status == "pass"
    assert evolution.evaluation.evaluator == "independent_reference_checker"
    assert evolution.candidate_comparison
    assert evolution.active_implementation == "ripgrep_search@1.0.0"
    assert evolution.previous_implementation != evolution.active_implementation
    assert json.loads(evolution.report_path.read_text(encoding="utf-8"))["activation_status"] == "activated"

    rollback = app.rollback_understand(evolution.previous_implementation)
    assert rollback.status == "rolled_back"
    assert app.active_understand_implementation() == evolution.previous_implementation
    rollback_records = list(app.evolution_dir.glob("rollback-*.json"))
    assert len(rollback_records) == 1
    assert json.loads(rollback_records[0].read_text(encoding="utf-8"))["status"] == "rolled_back"


def test_failed_evolution_keeps_previous_implementation_active(tmp_path: Path):
    wiki, source = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    app.acquire_ripgrep()
    previous = app.active_understand_implementation()

    evolution = app.evolve_understand(
        benchmark=[
            {
                "query": "Domain and Enterprise are parallel semantic dimensions.",
                "expected_source": str(source.resolve()),
                "expected_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "expected_text": "a line absent from the source",
            }
        ]
    )

    assert evolution.evaluation.status == "fail"
    assert evolution.active_implementation == previous
    assert app.active_understand_implementation() == previous


def test_evolution_rejects_a_source_changed_after_the_oracle_was_frozen(tmp_path: Path):
    wiki, source = _make_wiki(tmp_path)
    frozen_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    app.acquire_ripgrep()
    previous = app.active_understand_implementation()
    source.write_text(source.read_text(encoding="utf-8") + "Changed after the oracle was frozen.\n", encoding="utf-8")

    evolution = app.evolve_understand(
        benchmark=[
            {
                "query": "Domain and Enterprise are parallel semantic dimensions.",
                "expected_source": str(source.resolve()),
                "expected_source_sha256": frozen_hash,
                "expected_text": "Domain and Enterprise are parallel semantic dimensions.",
            }
        ],
        activate=True,
    )

    assert evolution.evaluation.status == "fail"
    assert evolution.active_implementation == previous
    candidate_case = evolution.candidate_comparison[1]["cases"][0]
    assert candidate_case["source_pin_matches"] is False


def test_unresolved_capability_outcome_is_not_replayed_and_can_be_reconciled(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    capability = _UncertainCapability()
    app.register_capability(
        capability.describe(),
        capability_version="1.0.0",
        execution={"side_effect": "possible"},
        implementation=capability,
    )
    session = app.new_session(
        domain={"id": "software-engineering"},
        enterprise={
            "id": "enterprise-a",
            "allow_local_artifacts": True,
            "allow_remote_writes": False,
            "allow_possible_side_effects": True,
            "allowed_capabilities": ["uncertain_test"],
        },
    )

    run = session.invoke("uncertain_test", "1.0.0", {}, invocation_id="uncertain-001")

    assert run.result.status == "unresolved"
    assert run.session_id
    assert run.execution_id
    assert capability.invoke_count == 1
    assert session.resume(run.session_id).result.status == "unresolved"
    assert capability.invoke_count == 1

    with pytest.raises(ValueError, match="outside the exact capability output schema"):
        session.reconcile(
            run.session_id,
            run.execution_id,
            resolution={"kind": "confirmed_executed", "observation": {"unexpected": True}},
            note="invalid test evidence",
        )
    assert session.resume(run.session_id).result.status == "unresolved"

    reconciled = session.reconcile(
        run.session_id,
        run.execution_id,
        resolution={"kind": "confirmed_executed", "observation": {"accepted": True}},
        note="verified from the local capability fixture",
    )
    assert reconciled.pending_execution is None
    assert capability.invoke_count == 1
    reconciliation_records = list(app.trace_dir.glob("reconciliation-*.json"))
    assert len(reconciliation_records) == 1
    assert json.loads(reconciliation_records[0].read_text(encoding="utf-8"))["status"] == "committed"


def test_preflight_capability_not_found_failure_is_persisted_as_trace(tmp_path: Path):
    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])

    run = app.new_session(domain={}, enterprise={"id": "enterprise-a"}).invoke(
        "not_registered", "1.0.0", {}, invocation_id="missing-001"
    )

    assert run.result.status == "failure"
    assert run.result.error["code"] == "capability_not_found"
    assert run.trace_path is not None and run.trace_path.is_file()


def test_capability_success_outside_declared_output_schema_is_a_failure(tmp_path: Path):
    class WrongOutput:
        def describe(self):
            return RuntimeCapabilityDescriptor(
                id="wrong_output",
                name="Wrong output",
                description="returns data outside the declared output schema",
                input_schema={"type": "object"},
                output_schema={
                    "type": "object",
                    "properties": {"count": {"type": "integer"}},
                    "required": ["count"],
                    "additionalProperties": False,
                },
            )

        def invoke(self, parameters, context):
            from agent_runtime.contracts import Success

            return Success({"count": "not an integer"})

    wiki, _ = _make_wiki(tmp_path)
    app = CatalystWorkbench(workspace=tmp_path, wiki_roots=[wiki])
    capability = WrongOutput()
    app.register_capability(
        capability.describe(),
        capability_version="1.0.0",
        execution={"side_effect": "none"},
        implementation=capability,
    )

    result = app.new_session(domain={}, enterprise={"id": "enterprise-a"}).invoke(
        "wrong_output", "1.0.0", {}, invocation_id="wrong-output-001"
    )

    assert result.result.status == "failure"
    assert result.result.error["code"] == "capability_failed"
    assert "outside its schema" in result.result.error["message"]


def test_cli_use_produces_machine_readable_result_and_trace(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "cli-workspace"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "catalyst_platform",
            "use",
            "--workspace",
            str(workspace),
            "--wiki-root",
            str(repo_root),
            "--wiki-index",
            str(repo_root / "CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json"),
            "--query",
            "Create a report from structured input",
            "--domain-id",
            "software-engineering",
            "--enterprise-id",
            "local-demo",
            "--allow-local-artifacts",
            "--output-name",
            "cli-result.md",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "success"
    artifact = Path(payload["artifact_path"])
    assert artifact.is_file()
    assert "platform_standard_reference.py" in artifact.read_text(encoding="utf-8")
    assert Path(payload["trace_path"]).is_file()


def test_cli_enterprise_source_map_blocks_cross_tenant_read_before_artifact_creation(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    wiki = tmp_path / "scoped-wiki"
    wiki.mkdir()
    source_a = wiki / "a.md"
    source_b = wiki / "b.md"
    source_a.write_text("# Enterprise A\nA-only material.\n", encoding="utf-8")
    source_b.write_text("# Enterprise B\nB-only secret marker: cobalt-928.\n", encoding="utf-8")
    access_map = tmp_path / "enterprise-access.json"
    access_map.write_text(
        json.dumps({"enterprise-a": [str(source_a)], "enterprise-b": [str(source_b)]}),
        encoding="utf-8",
    )
    workspace = tmp_path / "cli-workspace"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "catalyst_platform",
            "use",
            "--workspace",
            str(workspace),
            "--wiki-root",
            str(wiki),
            "--enterprise-access-map",
            str(access_map),
            "--query",
            "cobalt-928",
            "--domain-id",
            "engineering",
            "--enterprise-id",
            "enterprise-a",
            "--allow-local-artifacts",
            "--output-name",
            "cross-tenant.md",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "failure"
    assert payload["error"]["code"] == "insufficient_evidence"
    assert not (workspace / "artifacts" / "cross-tenant.md").exists()
