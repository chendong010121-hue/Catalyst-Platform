"""R6 scoped Wiki consumption through the existing Catalyst product path."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agent_runtime.contracts import ModelResponse, ModelToolCall
import catalyst_platform.__main__ as cli
from catalyst_platform.trace_log import JsonlTraceStore, TraceStoreError
from catalyst_platform.wiki import ProjectWiki, WikiScopeError, WikiUnavailable


_EVENT_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "schemas" / "run_event_v1_4.schema.json").read_text(encoding="utf-8")
)
Draft202012Validator.check_schema(_EVENT_SCHEMA)
_EVENT_VALIDATOR = Draft202012Validator(_EVENT_SCHEMA)


def test_trace_reader_preserves_v11_and_requires_v12_common_identity_fields(tmp_path):
    legacy_workspace = tmp_path / "legacy"
    legacy_store = JsonlTraceStore(legacy_workspace)
    run_id = "run_legacy_v11"
    common = {
        "event_schema_version": "1.1",
        "run_id": run_id,
        "request_id": "req_legacy",
        "invocation_id": "inv_legacy",
        "trace_id": "a" * 32,
        "redaction_policy_version": "allowlisted-content-v1",
        "timestamp": "2026-10-17T00:00:00.000Z",
    }
    records = [
        {**common, "sequence": 0, "event_id": "event_start", "event_type": "request.started"},
        {
            **common,
            "sequence": 1,
            "event_id": "event_terminal",
            "event_type": "request.terminal",
            "terminal_status": "success",
        },
    ]
    legacy_store.path.parent.mkdir(parents=True, exist_ok=True)
    legacy_store.path.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    replay = legacy_store.inspect_run(run_id)
    assert replay is not None
    assert replay["terminal_status"] == "success"

    invalid_store = JsonlTraceStore(tmp_path / "missing_identity")
    invalid_store.path.parent.mkdir(parents=True, exist_ok=True)
    invalid_store.path.write_text(
        json.dumps({
            "event_schema_version": "1.2", "run_id": "run_invalid_v12", "sequence": 0,
            "timestamp": "2026-10-17T00:00:00.000Z", "event_type": "span.started",
            "event_id": "event_invalid",
        }) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TraceStoreError, match="request_id"):
        invalid_store.inspect_run("run_invalid_v12")


def test_markdown_code_examples_are_not_promoted_to_wiki_candidate_claims(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "guide.md"
    source.write_text(
        "# Guide\n\n```md\n# Example only\nRule: This is sample text, not an organization rule.\n```\n\n"
        "~~~text\nException: This example is not an active exception.\n~~~\n\n"
        "Rule: Read only the file selected by the user.\n"
        "Condition: The selected file must be a Markdown document.\n",
        encoding="utf-8",
    )
    wiki = ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="enterprise-one", project_id="guide")

    staged = wiki.stage_markdown(source)
    history = wiki.claim_history(staged["source_id"])

    assert [(claim["kind"], claim["meaning"], claim["line_start"]) for claim in history] == [
        ("rule", "Read only the file selected by the user.", 12),
        ("condition", "The selected file must be a Markdown document.", 13),
    ]


def test_existing_wiki_search_binding_uses_project_adapter_and_reports_unavailable(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "alpha.md"
    source.write_text("# Alpha\n\nRule: Keep this candidate inside project Alpha.\n", encoding="utf-8")
    code, run, _provider = _run_ask(monkeypatch, capsys, workspace, source, "--stage-source", str(source))
    assert code == 0, run

    common = [
        "invoke", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--project-id", "project-alpha", "--enterprise-id", "local",
        "--capability-id", "wiki_search", "--version", "1.0.0",
        "--input-json", json.dumps({"query": "project Alpha candidate"}),
        "--domain-id", "local",
    ]
    code, searched = _cli_json(capsys, [*common, "--wiki-backend", "json"])
    assert code == 0, searched
    assert any(claim["source_id"] == run["wiki"]["stage"]["source_id"] for claim in searched["result"]["output"]["claims"])
    success_trace = _cold_inspect(workspace, searched["run_id"], capsys)
    assert any(event["event_type"] == "tool.result" and event.get("capability_id") == "wiki_search" for event in success_trace["events"])

    code, unavailable = _cli_json(capsys, [*common, "--wiki-backend", "unavailable"])
    assert code == 1
    assert unavailable["status"] == "failure"
    assert unavailable["error"]["code"] == "wiki_unavailable"
    unavailable_trace = _cold_inspect(workspace, unavailable["run_id"], capsys)
    assert unavailable_trace["terminal_status"] == "failure"


def test_existing_wiki_search_binding_reports_unavailable_when_store_is_unreadable(tmp_path, capsys):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    wiki = ProjectWiki(
        workspace,
        [roots],
        enterprise_id="local",
        project_id="project-alpha",
    )
    wiki._store.path.parent.mkdir(parents=True, exist_ok=True)
    wiki._store.path.write_text("{corrupt", encoding="utf-8")
    code, run = _cli_json(capsys, [
        "invoke", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--project-id", "project-alpha", "--wiki-backend", "json",
        "--capability-id", "wiki_search", "--version", "1.0.0",
        "--input-json", json.dumps({"query": "project-local source"}),
        "--domain-id", "local", "--enterprise-id", "local",
    ])

    assert code == 1
    assert run["status"] == "failure", run
    assert run["error"]["code"] == "wiki_unavailable"
    trace = _cold_inspect(workspace, run["run_id"], capsys)
    assert trace["terminal_status"] == "failure"
    tool_result = next(event for event in trace["events"] if event["event_type"] == "tool.result")
    assert tool_result["status"] == "failure"


class CapturingProvider:
    provider_id = "r6-capturing-provider"
    model = "offline-contract-test"
    mode = "offline"
    external_calls = 0

    def __init__(self, selected_file: Path):
        self.selected_file = selected_file.resolve()
        self.requests = []
        self.request_count = 0

    def request(self, request):
        self.requests.append(request)
        self.request_count += 1
        if request.tools and self.request_count == 1:
            assert len(request.tools) == 1
            return ModelResponse(
                tool_calls=(
                    ModelToolCall(
                        id="r6-call-file-title",
                        name=request.tools[0].name,
                        arguments=json.dumps({"path": str(self.selected_file)}),
                    ),
                ),
                finish_reason="tool_calls",
            )
        if any(message.role == "tool" for message in request.messages):
            return ModelResponse(
                content="The selected document title is Project Alpha Source.",
                finish_reason="stop",
            )
        return ModelResponse(content="The local Wiki resolved a read-only file capability.", finish_reason="stop")


class LocalStatsProvider:
    provider_id = "r6-local-stats-test-provider"
    model = "offline-contract-test"
    mode = "offline"
    external_calls = 0

    def __init__(self, selected_file: Path):
        self.selected_file = selected_file.resolve()
        self.request_count = 0
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        self.request_count += 1
        if self.request_count == 1:
            tool = next(tool for tool in request.tools if "Count lines, words" in tool.description)
            return ModelResponse(
                tool_calls=(ModelToolCall(
                    id="r6-local-stats-call",
                    name=tool.name,
                    arguments=json.dumps({"path": str(self.selected_file)}),
                ),),
                finish_reason="tool_calls",
            )
        tool_message = next(message for message in reversed(request.messages) if message.role == "tool")
        result = json.loads(tool_message.content)
        return ModelResponse(content=f"The selected file contains {result['word_count']} words.", finish_reason="stop")


def _cold_inspect(workspace: Path, run_id: str, capsys) -> dict:
    code = cli.main(["inspect", "--workspace", str(workspace), "--run-id", run_id])
    assert code == 0
    return json.loads(capsys.readouterr().out)


def _run_ask(monkeypatch, capsys, workspace: Path, source: Path, *extra: str):
    provider = CapturingProvider(source)
    monkeypatch.setattr(cli, "configured_model_provider_from_environment", lambda: provider)
    args = [
        "ask", "--workspace", str(workspace), "--wiki-root", str(source.parent),
        "--message", "Which heading names this document?", "--file", str(source),
        "--project-id", "project-alpha",
    ]
    args.extend(extra)
    code = cli.main(args)
    output = json.loads(capsys.readouterr().out)
    return code, output, provider


def _cli_json(capsys, args: list[str]):
    code = cli.main(args)
    output = capsys.readouterr()
    return code, json.loads(output.out) if output.out.strip() else {"stderr": output.err}


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_r6_cli_stages_scoped_source_resolves_active_binding_and_cold_replays(tmp_path, monkeypatch, capsys, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "alpha.md"
    source.write_text(
        "# Project Alpha Source\n\nRule: Read only the selected Markdown heading.\n"
        "Exception: Do not read a different path or infer its contents.\n",
        encoding="utf-8",
    )
    code, output, provider = _run_ask(
        monkeypatch, capsys, workspace, source,
        "--stage-source", str(source), "--wiki-backend", backend,
    )

    assert code == 0, output
    assert output["status"] == "success"
    assert output["result"]["output"]["answer"] == "The selected document title is Project Alpha Source."
    assert provider.request_count == 2
    assert len(provider.requests[0].tools) == 1
    assert "read_file_title" not in provider.requests[0].tools[0].name
    assert "Markdown H1" in provider.requests[0].tools[0].description
    assert "Read only the selected Markdown heading." in " ".join(
        message.content for message in provider.requests[0].messages
    )
    inspected = _cold_inspect(workspace, output["run_id"], capsys)
    events = inspected["events"]
    for event in events:
        _EVENT_VALIDATOR.validate(event)
    staged = next(event for event in events if event["event_type"] == "knowledge.source.staged")
    found = next(event for event in events if event["event_type"] == "knowledge.query.returned")
    consumed = next(event for event in events if event["event_type"] == "knowledge.claim.used_for_decision")
    binding = next(event for event in events if event["event_type"] == "binding.resolved")
    call = next(event for event in events if event["event_type"] == "tool.call.requested")
    authorization = next(event for event in events if event["event_type"] == "authorization.decided")
    execution = next(event for event in events if event["event_type"] == "tool.execution.started")
    assert staged["status"] == "staged"
    assert staged["claim_count"] >= 2
    retrieved_claims = {event["claim_id"] for event in events if event["event_type"] == "knowledge.claim.retrieved"}
    used_claims = {event["claim_id"] for event in events if event["event_type"] == "knowledge.claim.used_for_decision"}
    assert retrieved_claims
    assert used_claims <= retrieved_claims
    assert consumed["claim_id"] in retrieved_claims
    assert consumed["capability_id"] == binding["capability_id"] == "read_file_title"
    assert consumed["capability_version"] == binding["capability_version"] == "1.0.0"
    assert binding["sequence"] < call["sequence"] < consumed["sequence"] < authorization["sequence"] < execution["sequence"]
    assert consumed["tool_call_id"] == call["tool_call_id"] == binding["tool_call_id"]
    assert consumed["binding_digest"] == call["binding_digest"] == binding["binding_digest"]
    assert consumed["outcome"] == "tool_call_requested"
    assert inspected["terminal_status"] == "success"
    raw_trace = Path(output["trace_path"]).read_text(encoding="utf-8")
    assert "Do not read a different path" not in raw_trace
    assert str(source) not in raw_trace

    code, repeated, _ = _run_ask(
        monkeypatch, capsys, workspace, source,
        "--stage-source", str(source), "--wiki-backend", backend,
    )
    assert code == 0, repeated
    assert repeated["wiki"]["stage"]["status"] == "no_op"
    assert repeated["wiki"]["stage"]["source_id"] == staged["source_id"]
    assert repeated["wiki"]["stage"]["claim_ids"] == output["wiki"]["stage"]["claim_ids"]


@pytest.mark.parametrize(
    "query",
    ["what can process files?", "how do I identify a note's heading?"],
)
def test_project_discovery_uses_wiki_meaning_and_current_catalog_without_ids(tmp_path, capsys, query):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "wiki"
    roots.mkdir()
    args = [
        "discover", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--project-id", "project-alpha", "--query", query,
    ]
    assert cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "success"
    assert result["authorization"] == "not_evaluated_until_invocation"
    assert result["wiki"]["status"] == "FOUND"
    assert result["wiki"]["capabilities"]
    assert all(item["capability_id"] != "ripgrep_search" for item in result["wiki"]["capabilities"])
    selected = result["wiki"]["capabilities"][0]
    assert selected["capability_id"] == "read_file_title"
    assert selected["capability_version"] == "1.0.0"
    assert "Markdown" in selected["meaning"]
    assert result["capabilities"][0]["id"] == selected["capability_id"]
    inspected = _cold_inspect(workspace, result["run_id"], capsys)
    discovery_event = next(event for event in inspected["events"] if event["event_type"] == "capabilities.discovered")
    assert discovery_event["capabilities"][0]["id"] == selected["capability_id"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_real_cli_offline_deterministic_provider_runs_without_durable_source_memory(tmp_path, capsys, monkeypatch, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "offline.md"
    source.write_text("# Offline Evidence\nRule: Read a selected Markdown heading.\n", encoding="utf-8")
    monkeypatch.setattr(
        cli, "configured_model_provider_from_environment",
        lambda: (_ for _ in ()).throw(AssertionError("offline mode must not inspect Provider configuration")),
    )
    code, run = _cli_json(capsys, [
        "ask", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--message", "Which heading names this document?", "--file", str(source),
        "--project-id", "project-alpha", "--offline-deterministic", "--wiki-backend", backend,
    ])
    assert code == 0, run
    assert run["status"] == "success"
    assert run["result"]["output"]["answer"] == "The selected document title is Offline Evidence."
    assert run["result"]["output"]["tool_results"][0]["capability_id"] == "read_file_title"
    assert run["wiki"]["stage"] is None
    assert not (workspace / ".catalyst" / "wiki").exists()
    trace = _cold_inspect(workspace, run["run_id"], capsys)
    terminal = next(event for event in trace["events"] if event["event_type"] == "request.terminal")
    assert terminal["external_calls"] == 0


def test_wiki_disconnect_is_explicit_and_does_not_disable_r0_entry(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "disconnected.md"
    source.write_text("# Still readable by R0\n", encoding="utf-8")
    provider = CapturingProvider(source)
    monkeypatch.setattr(cli, "configured_model_provider_from_environment", lambda: provider)
    code = cli.main([
        "ask", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--message", "read the title", "--file", str(source),
        "--project-id", "project-alpha", "--wiki-backend", "unavailable",
    ])
    run = json.loads(capsys.readouterr().out)
    assert code == 1
    assert run["status"] == "failure"
    assert run["error"]["code"] == "wiki_unavailable"
    assert run["wiki"]["status"] == "UNAVAILABLE"
    inspected = _cold_inspect(workspace, run["run_id"], capsys)
    assert any(
        event["event_type"] == "knowledge.query.returned" and event["status"] == "UNAVAILABLE"
        for event in inspected["events"]
    )
    assert not any(event["event_type"] == "tool.call.requested" for event in inspected["events"])

    r0_code = cli.main(["inspect-file", "--workspace", str(workspace), "--file", str(source)])
    r0_result = json.loads(capsys.readouterr().out)
    assert r0_code == 0
    assert r0_result["result"]["output"]["title"] == "Still readable by R0"


def test_source_condition_change_changes_real_call_to_unknown_without_tool_execution(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "condition.md"
    source.write_text(
        "# Scoped reader\nRule: Read a selected Markdown heading.\n"
        "Exception: Do not read any different file.\n",
        encoding="utf-8",
    )
    success_provider = CapturingProvider(source)
    monkeypatch.setattr(cli, "configured_model_provider_from_environment", lambda: success_provider)
    base_args = [
        "ask", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--message", "Which heading names this document?", "--file", str(source),
        "--project-id", "project-alpha",
    ]
    assert cli.main([*base_args, "--stage-source", str(source)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "success"
    assert first["result"]["output"]["tool_results"][0]["status"] == "success"

    source.write_text(
        "# Scoped reader\nRule: Read a selected Markdown heading.\n"
        "Exception: Owner approval required; applicability is unknown until confirmed.\n",
        encoding="utf-8",
    )
    assert cli.main([*base_args, "--stage-source", str(source), "--offline-deterministic"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["status"] == "success"
    assert second["wiki"]["search"]["applicability_status"] == "UNKNOWN"
    assert second["result"]["output"]["tool_results"] == []
    assert "no file was read" in second["result"]["output"]["answer"].casefold()
    inspected = _cold_inspect(workspace, second["run_id"], capsys)
    event_types = [event["event_type"] for event in inspected["events"]]
    query_event = next(event for event in inspected["events"] if event["event_type"] == "knowledge.query.returned")
    assert query_event["applicability_status"] == "UNKNOWN"
    assert "tool.call.requested" not in event_types
    assert "source.read.started" not in event_types


def test_wiki_capability_projection_tracks_r5_component_deactivation_and_restore(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "wiki"
    roots.mkdir()
    source = roots / "measure.txt"
    source.write_text("one two three\nfour five\n", encoding="utf-8")
    product_root = Path(__file__).resolve().parents[1]
    package_v1 = shutil.copytree(
        product_root / "examples" / "local_components" / "local_text_stats" / "1.0.0",
        tmp_path / "local-text-stats-v1",
    )
    package_v2 = shutil.copytree(
        product_root / "examples" / "local_components" / "local_text_stats" / "2.0.0",
        tmp_path / "local-text-stats-v2",
    )

    def component(*args):
        return _cli_json(capsys, ["component", *args, "--workspace", str(workspace)])

    code, discovered_v1 = component("discover", "--source", str(package_v1))
    assert code == 0, discovered_v1
    code, discovered_v2 = component("discover", "--source", str(package_v2))
    assert code == 0, discovered_v2
    for package, discovered in ((package_v1, discovered_v1), (package_v2, discovered_v2)):
        code, admitted = component(
            "admit", "--source", str(package), "--expected-sha256", discovered["package_sha256"]
        )
        assert code == 0, admitted
    code, active_v2 = component("activate", "--component-id", "local_text_stats", "--version", "2.0.0")
    assert code == 0, active_v2

    def wiki_discover(query: str):
        return _cli_json(capsys, [
            "discover", "--workspace", str(workspace), "--wiki-root", str(roots),
            "--project-id", "project-alpha", "--query", query,
        ])

    code, v2_view = wiki_discover("how many words are in this selected file?")
    assert code == 0, v2_view
    assert any(item["capability_id"] == "local_text_stats" and item["capability_version"] == "2.0.0" for item in v2_view["wiki"]["capabilities"])

    code, deactivated = component("deactivate", "--component-id", "local_text_stats")
    assert code == 0, deactivated
    code, inactive_view = wiki_discover("how many words are in this selected file?")
    assert code == 0, inactive_view
    assert not any(item["capability_id"] == "local_text_stats" for item in inactive_view["wiki"]["capabilities"])

    stale_provider = LocalStatsProvider(source)
    monkeypatch.setattr(cli, "configured_model_provider_from_environment", lambda: stale_provider)
    code, stale_attempt = _cli_json(capsys, [
        "ask", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--message", "how many words are in this selected file?", "--file", str(source),
        "--project-id", "project-alpha", "--capability", "local_text_stats@2.0.0",
    ])
    assert code == 1
    assert stale_attempt["error"]["code"] == "wiki_binding_not_found"
    assert stale_provider.request_count == 0

    code, active_v1 = component("activate", "--component-id", "local_text_stats", "--version", "1.0.0")
    assert code == 0, active_v1
    code, v1_view = wiki_discover("how many words are in this selected file?")
    assert code == 0, v1_view
    assert any(item["capability_id"] == "local_text_stats" and item["capability_version"] == "1.0.0" for item in v1_view["wiki"]["capabilities"])

    provider = LocalStatsProvider(source)
    monkeypatch.setattr(cli, "configured_model_provider_from_environment", lambda: provider)
    code, used = _cli_json(capsys, [
        "ask", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--message", "how many words are in this selected file?", "--file", str(source),
        "--project-id", "project-alpha", "--capability", "local_text_stats@1.0.0",
    ])
    assert code == 0, used
    assert used["result"]["output"]["tool_results"][0]["capability_id"] == "local_text_stats"
    assert used["result"]["output"]["tool_results"][0]["capability_version"] == "1.0.0"
    trace = _cold_inspect(workspace, used["run_id"], capsys)
    binding = next(event for event in trace["events"] if event["event_type"] == "binding.resolved")
    assert binding["component_id"] == "local_text_stats"
    assert binding["component_version"] == "1.0.0"
    assert any(
        event["event_type"] == "knowledge.claim.used_for_decision"
        and event["capability_id"] == "local_text_stats"
        and event["capability_version"] == "1.0.0"
        for event in trace["events"]
    )


def test_project_scope_repeat_noop_update_stales_only_old_source_claims(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    source_a = roots / "alpha.md"
    source_b = roots / "beta.md"
    source_a.write_text("# Alpha\nRule: Alpha files use a chosen heading.\nException: ALPHAONLYSECRET must never leave Alpha.\n", encoding="utf-8")
    source_b.write_text("# Beta\nRule: Beta files use a document label.\nException: Never read outside Beta.\n", encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="enterprise-one", project_id="project-alpha")

    first = wiki.stage_markdown(source_a)
    repeated = wiki.stage_markdown(source_a)
    assert first["status"] == "staged"
    assert repeated["status"] == "no_op"
    assert repeated["source_id"] == first["source_id"]
    assert repeated["revision"] == first["revision"]

    wiki_beta = ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="enterprise-one", project_id="project-beta")
    beta_stage = wiki_beta.stage_markdown(source_b)
    assert beta_stage["source_id"] != first["source_id"]
    assert wiki_beta.search("ALPHAONLYSECRET")["claims"] == []
    other_enterprise = ProjectWiki(
        tmp_path / "workspace", [roots], enterprise_id="enterprise-two", project_id="project-alpha"
    )
    assert other_enterprise.search("ALPHAONLYSECRET")["claims"] == []
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\nRule: private scope.\n", encoding="utf-8")
    with pytest.raises(WikiScopeError, match="configured Wiki roots"):
        wiki.stage_markdown(outside)

    source_a.write_text(
        "# Alpha\nRule: Alpha files require an approved label before reading.\n"
        "Exception: Owner approval required; applicability is unknown until confirmed.\n",
        encoding="utf-8",
    )
    changed = wiki.stage_markdown(source_a)
    assert changed["status"] == "updated"
    assert changed["revision"] != first["revision"]
    results = wiki.search("approved label Alpha")
    assert results["claims"]
    assert all(claim["revision"] == changed["revision"] for claim in results["claims"])
    assert all(claim["status"] != "STALE" for claim in results["claims"])
    assert results["applicability_status"] == "UNKNOWN"
    history = wiki.claim_history(first["source_id"])
    assert any(claim["revision"] == first["revision"] and claim["status"] == "STALE" for claim in history)
    assert beta_stage["source_id"] not in {claim["source_id"] for claim in history}


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_r6_wiki_backend_contract_is_explicitly_unavailable_when_disconnected(tmp_path, backend):
    wiki = ProjectWiki(
        tmp_path / "workspace", [tmp_path], enterprise_id="enterprise-one",
        project_id="project-alpha", backend=backend, available=False,
    )
    with pytest.raises(WikiUnavailable):
        wiki.search("read file heading")


def test_json_and_sqlite_backends_preserve_semantic_source_and_claim_identity(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "capability.md"
    source.write_text("# Local reader\nRule: Read a selected Markdown heading.\nException: The user must select one file.\n", encoding="utf-8")
    results = []
    for backend in ("json", "sqlite"):
        wiki = ProjectWiki(
            tmp_path / "workspace", [roots], enterprise_id="enterprise-one",
            project_id="project-alpha", backend=backend,
        )
        wiki.stage_markdown(source)
        results.append(wiki.search("which capability reads a selected document heading?"))
    assert results[0]["source_id"] == results[1]["source_id"]
    assert {claim["claim_id"] for claim in results[0]["claims"]} == {
        claim["claim_id"] for claim in results[1]["claims"]
    }
    assert results[0]["source_revision"] == results[1]["source_revision"]
