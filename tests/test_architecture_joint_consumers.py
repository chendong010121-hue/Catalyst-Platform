"""Offline architecture proofs: signed TEST-SCOPE Wiki and a static test plugin.

All source text is created here. Test signatures prove software admission only;
they are not business Gold, independent semantic quality, or production Owner
authorization. No Host, Provider credential, external API, or package loader is
used. The third plugin shares the Workbench's existing catalog and Runtime.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from agent_runtime.contracts import CapabilityDescriptor, Failure, ModelResponse, ModelToolCall, Success
from catalyst_platform.plugin_composition import PluginComposer, PluginCompositionError, PluginDefinition, PluginEffect
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workbench import CapabilityCatalog, CatalystWorkbench
from tests.test_p0_admission_identity import (
    _owner_receipt, _recorder, _run, _semantic_receipt, _verifier, _version_receipt,
)


def _signed_fixture(tmp_path, backend):
    """Use public transitions and existing, separate evaluator/Owner test receipts."""
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "synthetic-test-scope.md"
    source.write_text(
        "# Synthetic TEST-SCOPE organization\n"
        "entity: reviewer | Synthetic Reviewer\n"
        "entity: package | Synthetic Package\n"
        "relation: @reviewer | checks | @package\n"
        "claim: review-rule | Synthetic Reviewer checks Synthetic Package\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-joint",
                       project_id="test-scope", backend=backend)

    def operation(label, method, *args, **kwargs):
        return _run(workspace, wiki, f"joint-{backend}-{label}", method, *args, **kwargs)

    proposed = operation("propose", "propose", source, actor_origin="codex_fixture")
    candidate = wiki.semantic_state()["candidates"][proposed["candidate_id"]]
    evaluated = operation("evaluate", "evaluate", candidate["candidate_id"],
                          actor_origin="independent_evaluator")
    assert evaluated["status"] == "pass"
    evaluation_receipt = _semantic_receipt(wiki, candidate)
    recorded = operation("evaluation-receipt", "record_external_evaluation_receipt",
                         receipt=evaluation_receipt, actor_origin="independent_evaluator")
    # A structural pass and a valid evaluator still cannot replace the Owner.
    with pytest.raises(SemanticTransitionError) as denied:
        operation("owner-required", "decide", candidate["candidate_id"],
                  decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="test_reviewed")
    assert denied.value.code == "authority_receipt_required"
    assert wiki.semantic_state()["active_version_id"] is None
    assert wiki.semantic_state()["accepted_versions"] == {}
    accepted = operation("accept", "decide", candidate["candidate_id"],
                         decision="ACCEPTED", actor_origin="manager_acceptance",
                         reason_code="test_reviewed", external_evaluation_id=recorded["evaluation_id"],
                         authority_receipt=_owner_receipt(wiki, candidate))
    version_id = accepted["version_id"]
    assert wiki.semantic_state()["active_version_id"] is None
    operation("activate", "activate", version_id, actor_origin="manager_acceptance",
              authority_receipt=_version_receipt(wiki, version_id, candidate,
                                                 action="ACTIVATE", expected_head=None))
    return workspace, roots, wiki, version_id, recorded["evaluation_id"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_standalone_signed_test_scope_wiki_reader_needs_no_harness_or_runtime(tmp_path, monkeypatch, backend):
    import agent_runtime.runtime as runtime_module
    import catalyst_platform.workbench as workbench_module

    def unavailable(*_args, **_kwargs):
        raise AssertionError("Standalone Wiki must not construct a Harness or Runtime")

    monkeypatch.setattr(CatalystWorkbench, "__init__", unavailable)
    monkeypatch.setattr(runtime_module.Runtime, "__init__", unavailable)
    monkeypatch.setattr(workbench_module, "Runtime", unavailable)
    workspace, roots, original, version_id, evaluation_id = _signed_fixture(tmp_path, backend)
    before = original.semantic_state()
    version = before["accepted_versions"][version_id]
    assert version["authority_class"] == "test_only"
    assert version["external_evaluation_id"] == evaluation_id
    assert "signature" not in version["owner_acceptance_basis"]
    # Reopen persisted state through the standalone store, not an app adapter.
    cold = ProjectWiki(workspace, [roots], enterprise_id="synthetic-joint",
                       project_id="test-scope", backend=backend)
    direct = cold.read_knowledge("reviewer", mode="accepted_enterprise_semantics")
    recorder = _recorder(workspace, f"joint-{backend}-independent-reader")
    reader = SemanticWiki(cold, recorder=recorder, receipt_verifier=_verifier)
    accepted = reader.read_knowledge("reviewer", mode="accepted_enterprise_semantics",
                                     actor_origin="catalyst_deterministic")
    relations = reader.resolve_relations("Synthetic Reviewer", actor_origin="catalyst_deterministic")
    assert direct["version_id"] == accepted["version_id"] == relations["version_id"] == version_id
    assert direct["meaning_ids"] == accepted["meaning_ids"]
    assert accepted["knowledge_status"] == "current"
    assert relations["status"] == "resolved" and len(relations["relations"]) == 1
    relation = relations["relations"][0]
    assert relation["predicate"] == "checks"
    assert relation["object_label"] == "Synthetic Package"
    assert relation["endpoint_status"] == "resolved"
    assert relations["causal_influence_proven"] is False
    source = roots / "synthetic-test-scope.md"
    lines = source.read_text(encoding="utf-8").splitlines()
    evidence = relation["evidence"][0]
    assert evidence["source_revision"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert evidence["line_start"] == evidence["line_end"] == 4
    assert evidence["span_sha256"] == hashlib.sha256(lines[3].encode()).hexdigest()
    assert cold.semantic_state() == before  # Consumer reads do not promote anything.
    other = ProjectWiki(workspace, [roots], enterprise_id="synthetic-other",
                        project_id="test-scope", backend=backend)
    unrelated = other.read_knowledge("reviewer", mode="accepted_enterprise_semantics")
    assert unrelated["version_id"] is None and unrelated["meanings"] == []
    recorder.finish("success", model_calls=0)
    reader.finalize_run(recorder.run_id, "success")
    events = recorder.store.inspect_run(recorder.run_id)["events"]
    assert any(event["event_type"] == "semantic.consumer.queried"
               and event["version_id"] == version_id for event in events)
    assert any(event["event_type"] == "semantic.consumer.meaning_consumed"
               and event["meaning_id"] == relation["meaning_id"] for event in events)


class _ReadOnlyTestPlugin:
    """Third, test-only source reader; no new catalog, runtime, or schema."""
    def __init__(self, wiki):
        self.wiki = wiki
        self.calls = []

    def describe(self):
        return CapabilityDescriptor(
            id="joint_test_read", name="Synthetic TEST-SCOPE source reader",
            description="Read only the test plugin's fixed synthetic enterprise Wiki.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}},
                          "required": ["query"], "additionalProperties": False},
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        enterprise_id = context.enterprise_context.get("id")
        self.calls.append(enterprise_id)
        if enterprise_id != self.wiki.enterprise_id:
            return Failure("joint_test_scope_denied")
        return Success(self.wiki.search(parameters["query"]))


class _ToolProvider:
    """Fixed protocol response only; never calls a model or transport."""
    model = "joint-test-fixed"
    provider_id = "offline-test"
    mode = "offline"

    def __init__(self):
        self.requests = []
        self.tool_result = None

    def request(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            return ModelResponse(tool_calls=(ModelToolCall(
                id="joint-test-call", name=CapabilityCatalog.internal_key("joint_test_read", "1.0.0"),
                arguments=json.dumps({"query": "synthetic plugin"}),
            ),), finish_reason="tool_calls")
        message = next(message for message in reversed(request.messages) if message.role == "tool")
        self.tool_result = json.loads(message.content)
        return ModelResponse(content="Synthetic source read completed.", finish_reason="stop")


def _third_plugin(app, wiki, *, services=True):
    def apply(context):
        catalog = context.require("capability.catalog")
        tool = _ReadOnlyTestPlugin(context.require("joint.test_wiki"))
        catalog.register(tool, capability_version="1.0.0", execution={"side_effect": "none"},
                         metadata={"implementation": "joint-test-only", "component_id": "joint-test-only",
                                   "component_version": "0.1.0", "llm_visibility": "explicit",
                                   "model_policy": {"mode": "workspace_scoped_query", "max_calls": 1}})
        return PluginEffect(services={"joint.test_reader": tool},
                            revoke=lambda: catalog.deactivate("joint_test_read", "1.0.0"))

    definition = PluginDefinition(plugin_id="joint-test-only", version="0.1.0",
                                  provides=("joint.test_reader",),
                                  requires=("capability.catalog", "joint.test_wiki"), apply=apply)
    host = {"capability.catalog": app._catalog}
    if services:
        host["joint.test_wiki"] = wiki
    return PluginComposer(definitions=(definition,), profiles={"test-only": (definition.plugin_id,)},
                          host_services=host), definition


def _plugin_fixture(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "synthetic-plugin.md"
    source.write_text("# Synthetic plugin\nRule: Synthetic plugin reads a bounded source.\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-joint", project_id="plugin-test")
    wiki.stage_markdown(source)
    app = CatalystWorkbench(workspace, [roots], enterprise_source_allowlist={"synthetic-joint": [roots]})
    return app, wiki, source


def test_third_static_plugin_uses_existing_catalog_harness_runtime_and_unloads(tmp_path):
    app, wiki, source = _plugin_fixture(tmp_path)
    before = source.read_bytes()
    composer, _definition = _third_plugin(app, wiki)
    composer.compose("test-only")
    assert app.plugins.active_plugins == ("evo-wiki", "understand")
    assert composer.active_plugins == ("joint-test-only",)
    tool = composer.service("joint.test_reader")
    registration = app._catalog.get("joint_test_read", "1.0.0")
    assert registration.implementation is tool
    assert registration.descriptor.execution["side_effect"] == "none"
    session = app.new_session(domain={"id": "local"}, enterprise={"id": wiki.enterprise_id})
    assert "joint_test_read" in {item.id for item in session.discover()}
    recorder = _recorder(app.workspace, "joint-third-plugin-invoke")
    invoked = session.invoke("joint_test_read", "1.0.0", {"query": "synthetic plugin"}, recorder=recorder)
    assert invoked.result.status == "success"
    recorder.finish("success", model_calls=0)
    events = recorder.store.inspect_run(recorder.run_id)["events"]
    observed = next(event for event in events if event["event_type"] == "tool.result")
    assert observed["component_id"] == "joint-test-only"
    assert observed["capability_id"] == "joint_test_read" and observed["result_sha256"]
    fake = _ToolProvider()
    asked = session.ask("Read synthetic plugin source.", provider=fake,
                        execution_mode="agent",
                        visible_capabilities=(("joint_test_read", "1.0.0"),))
    assert asked.result.status == "success" and fake.tool_result["status"] == "FOUND"
    assert len(fake.requests) == 2 and tool.calls == [wiki.enterprise_id, wiki.enterprise_id]
    assert session.tool_execution_count("joint_test_read") == 2
    missing = session.invoke("joint_test_read", "9.9.9", {"query": "synthetic"})
    assert missing.result.error["code"] == "capability_not_found"
    composer.unload("joint-test-only")
    assert composer.service("joint.test_reader") is None
    assert app._catalog.get("joint_test_read", "1.0.0") is None
    assert "joint_test_read" not in {item.id for item in session.discover()}
    assert session.invoke("joint_test_read", "1.0.0", {"query": "synthetic"}).result.error["code"] == "capability_not_found"
    unused = _ToolProvider()
    assert session.ask("Read again", provider=unused, visible_capabilities=(("joint_test_read", "1.0.0"),)).result.error["code"] == "capability_not_found"
    assert unused.requests == [] and len(tool.calls) == 2
    assert source.read_bytes() == before
    assert wiki.search("synthetic plugin")["status"] == "FOUND"


def test_third_plugin_policy_scope_missing_dependency_and_duplicates_fail_closed(tmp_path):
    app, wiki, _source = _plugin_fixture(tmp_path)
    missing, definition = _third_plugin(app, wiki, services=False)
    with pytest.raises(PluginCompositionError, match="missing required service"):
        missing.compose("test-only")
    assert missing.active_plugins == () and app._catalog.get("joint_test_read", "1.0.0") is None
    with pytest.raises(PluginCompositionError, match="duplicate plugin ID"):
        PluginComposer(definitions=(definition, definition), profiles={"test-only": (definition.plugin_id,)})
    composer, _ = _third_plugin(app, wiki)
    composer.compose("test-only")
    tool = composer.service("joint.test_reader")
    with pytest.raises(PluginCompositionError, match="already active"):
        composer.compose("test-only")
    # Registered read-only tools remain invisible unless this request names them.
    fake = _ToolProvider()
    session = app.new_session(domain={"id": "local"}, enterprise={"id": wiki.enterprise_id})
    denied = session.ask("Read hidden source", provider=fake, visible_capabilities=())
    assert denied.result.status == "failure" and tool.calls == []
    other = app.new_session(domain={"id": "local"}, enterprise={"id": "synthetic-other"})
    denied = other.invoke("joint_test_read", "1.0.0", {"query": "synthetic"})
    assert denied.result.status == "failure" and tool.calls == []
    # A trusted but different enterprise reaches the plugin's own fixed-scope guard.
    app.enterprise_source_allowlist["synthetic-other"] = tuple(wiki.roots)
    refused = other.invoke("joint_test_read", "1.0.0", {"query": "synthetic"})
    assert refused.result.status == "failure" and tool.calls == ["synthetic-other"]
    composer.unload("joint-test-only")
