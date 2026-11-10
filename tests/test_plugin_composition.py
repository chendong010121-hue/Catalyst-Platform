from __future__ import annotations

import json
import pytest
import uuid
from types import SimpleNamespace

from agent_runtime.contracts import ModelResponse, ModelToolCall, Success

from catalyst_platform.observability import RunRecorder
from catalyst_platform.plugin_composition import (
    PluginCompositionError,
    PluginDefinition,
    PluginEffect,
    PluginComposer,
)
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.understand_only import UnderstandIntent, UnderstandingRequest
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workbench import CapabilityCatalog, CapabilityConflictError, CatalystWorkbench


def _definition(plugin_id, provides, requires=(), *, apply=None):
    default_apply = lambda _context: PluginEffect(
        services={name: object() for name in provides}
    )
    return PluginDefinition(
        plugin_id=plugin_id,
        version="0.1.0",
        provides=tuple(provides),
        requires=tuple(requires),
        apply=apply or default_apply,
    )


def test_composes_declared_services_in_dependency_order_and_unloads_effects():
    events = []
    provider = _definition(
        "provider",
        ("service.provider",),
        apply=lambda _context: PluginEffect(
            services={"service.provider": object()},
            revoke=lambda: events.append("provider"),
        ),
    )

    def apply_consumer(context):
        assert context.require("service.provider") is not None
        return PluginEffect(
            services={"service.consumer": "ready"},
            revoke=lambda: events.append("consumer"),
        )

    consumer = _definition(
        "consumer",
        ("service.consumer",),
        ("service.provider",),
        apply=apply_consumer,
    )
    composer = PluginComposer(
        definitions=(consumer, provider),
        profiles={"default": ("consumer", "provider")},
        host_services={"host.clock": object()},
    )

    composer.compose("default")

    assert composer.active_plugins == ("provider", "consumer")
    assert composer.service("service.consumer") == "ready"
    assert composer.service("host.clock") is not None
    with pytest.raises(PluginCompositionError, match="required by active plugin"):
        composer.unload("provider")

    composer.unload("consumer")
    composer.unload("provider")

    assert events == ["consumer", "provider"]
    assert composer.service("service.consumer") is None
    assert composer.active_plugins == ()


def test_missing_dependencies_are_rejected_before_any_plugin_is_applied():
    calls = []
    plugin = _definition(
        "needs-missing-service",
        ("provided",),
        ("missing",),
        apply=lambda _context: calls.append("applied") or PluginEffect(),
    )
    composer = PluginComposer(
        definitions=(plugin,),
        profiles={"default": ("needs-missing-service",)},
    )

    with pytest.raises(PluginCompositionError, match="missing required service.*missing"):
        composer.compose("default")

    assert calls == []
    assert composer.active_plugins == ()


def test_duplicate_ids_services_profiles_and_repeated_registration_are_rejected():
    duplicate_id = _definition("same", ("one",))
    with pytest.raises(PluginCompositionError, match="duplicate plugin ID"):
        PluginComposer(
            definitions=(duplicate_id, duplicate_id),
            profiles={"default": ("same",)},
        )

    first = _definition("first", ("collision",))
    second = _definition("second", ("collision",))
    composer = PluginComposer(
        definitions=(first, second),
        profiles={"default": ("first", "second")},
    )
    with pytest.raises(PluginCompositionError, match="multiple plugins provide"):
        composer.compose("default")

    composer = PluginComposer(
        definitions=(first,),
        profiles={"default": ("first",)},
    )
    composer.compose("default")
    with pytest.raises(PluginCompositionError, match="already active"):
        composer.compose("default")


def test_partial_compose_failure_revokes_prior_effects_in_reverse_order():
    events = []
    first = _definition(
        "first",
        ("one",),
        apply=lambda _context: PluginEffect(
            services={"one": 1}, revoke=lambda: events.append("first")
        ),
    )

    def fail(_context):
        raise RuntimeError("activation failed")

    second = _definition("second", ("two",), ("one",), apply=fail)
    composer = PluginComposer(
        definitions=(first, second),
        profiles={"default": ("first", "second")},
    )

    with pytest.raises(RuntimeError, match="activation failed"):
        composer.compose("default")

    assert events == ["first"]
    assert composer.active_plugins == ()
    assert composer.service("one") is None


def test_effect_services_must_match_declared_provides_and_unknown_profiles_fail():
    revoked = []
    bad = _definition(
        "bad",
        ("expected",),
        apply=lambda _context: PluginEffect(
            services={"unexpected": object()}, revoke=lambda: revoked.append(True)
        ),
    )
    composer = PluginComposer(
        definitions=(bad,),
        profiles={"default": ("bad",)},
    )

    with pytest.raises(PluginCompositionError, match="do not match declared services"):
        composer.compose("default")
    assert revoked == [True]
    with pytest.raises(PluginCompositionError, match="unknown plugin profile"):
        composer.compose("not-allowed")


class _WikiProvider:
    provider_id = "static-plugin-test"
    model = "fixed"
    mode = "offline"

    def __init__(self, capability_id="wiki_search", arguments=None):
        self.capability_id = capability_id
        self.arguments = arguments or {"query": "plugin source"}
        self.requests = []
        self.tool_result = None

    def request(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            internal_key = CapabilityCatalog.internal_key(self.capability_id, "1.0.0")
            return ModelResponse(
                tool_calls=(
                    ModelToolCall(
                        id="plugin-tool-call",
                        name=internal_key,
                        arguments=json.dumps(self.arguments),
                    ),
                ),
                finish_reason="tool_calls",
            )
        message = next(message for message in reversed(request.messages) if message.role == "tool")
        self.tool_result = json.loads(message.content)
        return ModelResponse(content="fixed answer", finish_reason="stop")


def _recorder(workspace, run_id="plugin-run"):
    store = JsonlTraceStore(workspace)
    recorder = RunRecorder(
        store,
        run_id=run_id,
        request_id=f"request-{run_id}",
        invocation_id=f"invocation-{run_id}",
        trace_id=uuid.uuid4().hex,
    )
    recorder.start(request_kind="ask")
    return recorder, store


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_builtin_plugins_register_through_existing_runtime_and_trace_result_owner(tmp_path, backend):
    workspace = tmp_path / "workspace"
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "rules.md"
    source.write_text("# Plugin source\n\nRule: A plugin source proves bounded retrieval.\n", encoding="utf-8")
    wiki = ProjectWiki(
        workspace,
        [sources],
        enterprise_id="enterprise-one",
        project_id="project-one",
        backend=backend,
    )
    wiki.stage_markdown(source)

    def search(query, enterprise_id):
        assert enterprise_id == "enterprise-one"
        return wiki.search(query)

    app = CatalystWorkbench(workspace=workspace, wiki_roots=[sources], wiki_search_adapter=search)
    app._project_wiki = wiki
    assert app.plugins.active_plugins == ("evo-wiki", "understand")
    assert [item.id for item in app.new_session(domain={}, enterprise={}).discover()].count("wiki_search") == 1
    registration = app._catalog.get("wiki_search", "1.0.0")
    assert registration is not None
    assert registration.metadata["component_id"] == "evo-wiki"
    assert registration.metadata["component_version"] == "0.1.0"
    assert registration.descriptor.execution["side_effect"] == "none"
    assert app.plugins.service("understand.port") is not None
    assert all(item.id != "understand_source" for item in app._catalog.list())

    recorder, store = _recorder(workspace)
    semantic = SemanticWiki(wiki, recorder=recorder)
    captured = app._catalog.runtime_bindings(
        lambda _capability_id: None,
        plugin_services={"semantic_wiki": semantic, "project_wiki": wiki},
    )
    wiki_binding = captured[CapabilityCatalog.internal_key("wiki_search", "1.0.0")]
    writer_binding = captured[CapabilityCatalog.internal_key("write_artifact", "1.0.0")]
    assert wiki_binding._plugin_services["project_wiki"] is wiki
    assert writer_binding._plugin_services == {}
    for binding in captured.values():
        binding.release()
    provider = _WikiProvider()
    run = app.new_session(
        domain={"id": "local"},
        enterprise={"id": "enterprise-one", "allow_remote_writes": False},
    ).ask(
        "Find the plugin source.",
        provider=provider,
        visible_capabilities=(("wiki_search", "1.0.0"),),
        recorder=recorder,
        _plugin_services={"semantic_wiki": semantic, "project_wiki": wiki},
    )
    assert run.result.status == "success"
    assert provider.tool_result["status"] == "FOUND"
    assert "source_claims" in provider.tool_result["project_knowledge"], provider.tool_result
    assert provider.tool_result["project_knowledge"]["source_claims"]["knowledge_status"] in {
        "current",
        "stale",
        "unavailable",
    }
    recorder.finish("success")
    events = store.inspect_run("plugin-run")["events"]
    tool_result = next(event for event in events if event["event_type"] == "tool.result")
    assert tool_result["capability_id"] == "wiki_search"
    assert tool_result["component_id"] == "evo-wiki"
    assert tool_result["component_version"] == "0.1.0"
    assert tool_result["result_sha256"]
    assert any(
        event["event_type"] == "semantic.consumer.queried"
        and event.get("actor_origin") == "catalyst_deterministic"
        for event in events
    )


def test_understand_plugin_returns_candidate_without_writing_wiki_state(tmp_path):
    workspace = tmp_path / "workspace"
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "business.md"
    source.write_text("# Business\n\nOrders belong to the operations team.\n", encoding="utf-8")
    wiki = ProjectWiki(
        workspace,
        [sources],
        enterprise_id="enterprise-one",
        project_id="project-one",
    )
    before = wiki.semantic_state()
    app = CatalystWorkbench(workspace=workspace, wiki_roots=[sources])
    port = app.plugins.service("understand.port")
    assert port is not None
    recorder, store = _recorder(workspace, "understand-plugin-run")

    result = port.understand(
        UnderstandingRequest(
            request_id="understand-plugin-request",
            message="Propose enterprise meanings from the selected source.",
            source_refs=(source,),
            intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
            scope_id=wiki.scope_id,
        ),
        source_root=sources,
        recorder=recorder,
    )

    assert result.semantic_candidate is not None
    assert result.semantic_candidate.persistence_status == "NOT_PERSISTED"
    assert result.wiki_handoff == "HANDOFF_BLOCKED_BY_PRODUCER_SCHEMA"
    assert wiki.semantic_state() == before
    assert "wiki_search" in {item.id for item in app._catalog.list()}
    assert not any(item.id.startswith("understand_") for item in app._catalog.list())
    recorder.finish("success")
    events = store.inspect_run("understand-plugin-run")["events"]
    plugin_span = next(
        event
        for event in events
        if event["event_type"] == "span.started"
        and event.get("span_name") == "plugin.understand.analyze"
    )
    assert plugin_span["component_id"] == "understand"
    assert plugin_span["component_version"] == "0.1.0"


def test_plugin_unload_withdraws_tool_but_preserves_wiki_and_old_ask_path(tmp_path):
    workspace = tmp_path / "workspace"
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "persistent.md"
    source.write_text("# Persistent\n\nRule: Persistent Wiki data stays after plugin stop.\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [sources], enterprise_id="enterprise-one", project_id="project-one")
    staged = wiki.stage_markdown(source)

    app = CatalystWorkbench(
        workspace=workspace,
        wiki_roots=[sources],
        wiki_search_adapter=lambda query, _enterprise_id: wiki.search(query),
    )
    session = app.new_session(domain={"id": "local"}, enterprise={"id": "enterprise-one"})
    denied_provider = _WikiProvider(capability_id="write_artifact")
    denied = session.ask(
        "Try a side-effect capability.",
        provider=denied_provider,
        visible_capabilities=(("write_artifact", "1.0.0"),),
    )
    assert denied.result.error["code"] == "capability_policy_denied"
    assert denied_provider.requests == []
    app.plugins.unload("evo-wiki")

    assert app.plugins.service("evo_wiki.search_tool") is None
    assert app._catalog.get("wiki_search", "1.0.0") is None
    assert all(item.id != "wiki_search" for item in session.discover())
    assert staged["source_id"]
    snapshot = wiki.source_snapshot(staged["source_id"])
    assert "Persistent Wiki data stays" in snapshot["content"]

    unused = _WikiProvider()
    refused = session.ask(
        "Use Wiki search.",
        provider=unused,
        visible_capabilities=(("wiki_search", "1.0.0"),),
    )
    assert refused.result.error["code"] == "capability_not_found"
    assert unused.requests == []

    legacy = _WikiProvider(capability_id="unused")
    legacy.request = lambda _request: ModelResponse(content="legacy path works", finish_reason="stop")
    legacy_run = app.new_session(domain={"id": "local"}, enterprise={"id": "enterprise-one"}).ask(
        "Answer without a plugin tool.",
        provider=legacy,
    )
    assert legacy_run.result.status == "success"
    assert legacy_run.result.output["answer"] == "legacy path works"


def test_plugin_timeout_and_failure_are_settled_by_existing_runtime(tmp_path):
    for error_type in (TimeoutError, RuntimeError):
        workspace = tmp_path / error_type.__name__
        sources = tmp_path / f"sources-{error_type.__name__}"
        sources.mkdir()

        def failing_search(_query, _enterprise_id, error_type=error_type):
            raise error_type("deterministic plugin search failure")

        app = CatalystWorkbench(workspace=workspace, wiki_roots=[sources], wiki_search_adapter=failing_search)
        recorder, store = _recorder(workspace, f"run-{error_type.__name__}")
        provider = _WikiProvider()
        run = app.new_session(domain={"id": "local"}, enterprise={"id": "enterprise-one"}).ask(
            "Query Wiki.",
            provider=provider,
            visible_capabilities=(("wiki_search", "1.0.0"),),
            recorder=recorder,
        )
        assert run.result.status == "failure"
        assert provider.requests
        recorder.finish("failure")
        events = store.inspect_run(f"run-{error_type.__name__}")["events"]
        tool_result = next(event for event in events if event["event_type"] == "tool.result")
        assert tool_result["component_id"] == "evo-wiki"
        assert tool_result["status"] == "failure"


def test_catalog_duplicate_registration_is_idempotent_and_conflicts_fail(tmp_path):
    app = CatalystWorkbench(workspace=tmp_path / "workspace", wiki_roots=[tmp_path])
    capability = app.plugins.service("evo_wiki.search_tool")
    metadata = {
        "implementation": "catalyst-evo-wiki-plugin-v0.1",
        "model_policy": {"mode": "workspace_scoped_query", "max_calls": 1},
        "llm_visibility": "explicit",
        "component_id": "evo-wiki",
        "component_version": "0.1.0",
    }
    assert app._catalog.register(
        capability,
        capability_version="1.0.0",
        execution={"side_effect": "none"},
        metadata=metadata,
    ) == "no-op"

    class DifferentWikiImplementation:
        def describe(self):
            return capability.describe()

        def invoke(self, _parameters, _context):
            return Success({"status": "OTHER"})

    with pytest.raises(CapabilityConflictError):
        app._catalog.register(
            DifferentWikiImplementation(),
            capability_version="1.0.0",
            execution={"side_effect": "none"},
            metadata={**metadata, "component_id": "other-plugin"},
        )


def test_evo_wiki_plugin_does_not_read_another_enterprise_scope(tmp_path):
    workspace = tmp_path / "workspace"
    sources = tmp_path / "sources"
    sources.mkdir()
    wiki = ProjectWiki(workspace, [sources], enterprise_id="enterprise-one", project_id="project-one")
    recorder, _store = _recorder(workspace, "scope-plugin-run")
    semantic = SemanticWiki(wiki, recorder=recorder)
    app = CatalystWorkbench(
        workspace=workspace,
        wiki_roots=[sources],
        wiki_search_adapter=lambda _query, _enterprise_id: {"evidence": []},
    )
    capability = app.plugins.service("evo_wiki.search_tool")

    result = capability.invoke(
        {"query": "private enterprise meaning"},
        SimpleNamespace(
            enterprise_context={"id": "enterprise-two"},
            plugin_services={"semantic_wiki": semantic, "project_wiki": wiki},
        ),
    )

    assert isinstance(result, Success)
    assert result.data["project_knowledge"] == {
        "status": "DENIED",
        "error_code": "wiki_scope_mismatch",
    }


def test_wiki_plugin_unload_withdraws_new_bindings_and_drains_captured_run_lease(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    app = CatalystWorkbench(
        workspace=tmp_path / "workspace",
        wiki_roots=[sources],
        wiki_search_adapter=lambda _query, _enterprise_id: {"status": "FOUND", "evidence": []},
    )
    key = CapabilityCatalog.internal_key("wiki_search", "1.0.0")
    binding = app._catalog.runtime_bindings(lambda _capability_id: None)[key]
    registration = binding.registration
    app.plugins.unload("evo-wiki")

    assert registration._retired is True
    assert registration._closed is False
    assert key not in app._catalog.runtime_bindings(lambda _capability_id: None)
    result = binding.invoke({"query": "bounded"}, SimpleNamespace())
    assert isinstance(result, Success)
    assert result.data["status"] == "FOUND"

    binding.release()
    assert registration._closed is True
