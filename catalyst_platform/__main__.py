"""Command-line entry point for the offline local Catalyst workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

from .file_title import CAPABILITY_ID, CAPABILITY_VERSION, FileTitleCapability
from .components import ComponentError
from .gateway import CatalystGateway
from .monitor import create_monitor_server
from .observability import record_file_tool_event
from .ontology_concepts import concept_projection
from .ontology_types import META_KINDS, Concept, ConceptError, ConceptSet
from .otel_export import OTelExportError, export_run_otlp
from .llm_provider import (
    ModelProviderConfigurationError,
    UnavailableModelProvider,
    configured_model_provider_from_environment,
    configured_model_provider_interactively,
)
from .trace_log import TraceStoreError
from .offline_provider import DeterministicOfflineProvider
from .semantic_wiki import SemanticTransitionError, SemanticWiki
from .understand_only import (
    EvidenceExpansionRequest,
    EvidenceRef,
    SourceRecord,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from .wiki import ProjectWiki, WikiScopeError, WikiSourceIdentityAmbiguous, WikiUnavailable
from .workbench import CatalystWorkbench, WorkbenchError
from .understand_wiki import UnderstandWikiAdapter, UnderstandWikiError


_MAX_EXTERNAL_SUBMISSION_BYTES = 512_000


def _add_workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--wiki-root", required=True, action="append", type=Path)
    parser.add_argument("--wiki-index", type=Path)
    parser.add_argument(
        "--enterprise-access-map",
        type=Path,
        help="local test access map from Enterprise ID to allowed source paths; not production IAM",
    )


def _add_semantic_context(
    parser: argparse.ArgumentParser,
    *,
    actor_origin: str,
    actor_choices: tuple[str, ...] = (
        "codex_fixture", "codex_external", "catalyst_deterministic", "catalyst_model",
        "manager_acceptance", "independent_evaluator",
    ),
    correlation_required: bool = False,
) -> None:
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--wiki-root", required=True, action="append", type=Path)
    parser.add_argument("--enterprise-id", default="local")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    parser.add_argument(
        "--correlation-id",
        required=correlation_required,
        help="opaque local identifier correlating related Run Observability records",
    )
    parser.add_argument(
        "--actor-origin",
        choices=actor_choices,
        default=actor_origin,
    )


def _app(args: argparse.Namespace) -> CatalystWorkbench:
    allowlist = None
    enterprise_access_map = getattr(args, "enterprise_access_map", None)
    if enterprise_access_map is not None:
        map_path = enterprise_access_map.resolve()
        value = json.loads(map_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("--enterprise-access-map must contain a JSON object")
        allowlist = {}
        for enterprise_id, source_paths in value.items():
            if not isinstance(enterprise_id, str) or not isinstance(source_paths, list) or not all(
                isinstance(source_path, str) for source_path in source_paths
            ):
                raise ValueError("each access-map entry must map an Enterprise ID to a string path array")
            allowlist[enterprise_id] = [
                path if (path := Path(source_path)).is_absolute() else map_path.parent / path
                for source_path in source_paths
            ]
    wiki_roots = getattr(args, "wiki_root", None) or [args.workspace]
    project_id = getattr(args, "project_id", None)
    project_wiki = None
    wiki_search_adapter = None
    holder: dict[str, Any] = {}
    if project_id is not None:
        enterprise_id = getattr(args, "enterprise_id", "local")
        scoped_roots = allowlist.get(enterprise_id, ()) if allowlist is not None else wiki_roots
        if scoped_roots:
            project_wiki = ProjectWiki(
                args.workspace,
                scoped_roots,
                enterprise_id=enterprise_id,
                project_id=project_id,
                backend=getattr(args, "wiki_backend", "json"),
            )

            def wiki_search_adapter(query: str, requested_enterprise_id: str | None) -> dict[str, Any]:
                if requested_enterprise_id != enterprise_id or not project_wiki.available:
                    return {"status": "UNAVAILABLE", "scope_id": project_wiki.scope_id, "claims": [], "capabilities": []}
                try:
                    return project_wiki.search(query, capabilities=_wiki_catalog_projection(holder["app"]))
                except WikiUnavailable:
                    return {
                        "status": "UNAVAILABLE",
                        "scope_id": project_wiki.scope_id,
                        "claims": [],
                        "capabilities": [],
                    }

    app = CatalystWorkbench(
        workspace=args.workspace,
        wiki_roots=wiki_roots,
        wiki_index=getattr(args, "wiki_index", None),
        enterprise_source_allowlist=allowlist,
        wiki_search_adapter=wiki_search_adapter,
    )
    holder["app"] = app
    if project_wiki is not None:
        app._project_wiki = project_wiki
    return app


def _register_file_title(
    app: CatalystWorkbench,
    event_sink: Callable[[dict[str, Any]], None],
) -> None:
    capability = FileTitleCapability(workspace=app.workspace, event_sink=event_sink)
    app.register_capability(
        capability.describe(),
        capability_version=CAPABILITY_VERSION,
        execution={"side_effect": "none"},
        implementation=capability,
        metadata={
            "model_policy": {
                "mode": "selected_file_path",
                "path_parameter": "path",
                "max_calls": 1,
            },
            "llm_visibility": "explicit",
        },
    )


def _wiki_catalog_projection(app: CatalystWorkbench) -> list[dict[str, Any]]:
    """Derive discoverable read-only file bindings from the current R5 Catalog."""
    projected = []
    for descriptor in app._catalog.list():
        registration = app._catalog.get(descriptor.id, descriptor.capability_version)
        if registration is None or descriptor.execution.get("side_effect") != "none":
            continue
        metadata = registration.metadata
        model_policy = metadata.get("model_policy")
        if (
            metadata.get("llm_visibility") != "explicit"
            or not isinstance(model_policy, dict)
            or model_policy.get("mode") != "selected_file_path"
            or type(model_policy.get("max_calls")) is not int
            or not 1 <= model_policy["max_calls"] <= 4
            or not isinstance(model_policy.get("path_parameter"), str)
        ):
            continue
        descriptor_json = json.dumps(
            descriptor.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        projected.append(
            {
                "capability_id": descriptor.id,
                "capability_version": descriptor.capability_version,
                "name": descriptor.name,
                "description": descriptor.description,
                "side_effect": "none",
                "descriptor_sha256": hashlib.sha256(descriptor_json).hexdigest(),
                "binding_digest": registration.fingerprint,
            }
        )
    return projected


def _record_knowledge_use(
    recorder,
    claim: dict[str, Any],
    capability_id: str,
    version: str,
    *,
    tool_call_id: str,
    binding_digest: str,
) -> None:
    recorder.event(
        "knowledge.claim.used_for_decision",
        scope_id=claim["scope_id"],
        claim_id=claim["claim_id"],
        source_id=claim["source_id"],
        source_revision=claim["revision"],
        capability_id=capability_id,
        capability_version=version,
        tool_call_id=tool_call_id,
        binding_digest=binding_digest,
        outcome="tool_call_requested",
    )


def _ask_with_app(
    app: CatalystWorkbench,
    *,
    workspace: Path,
    message: str,
    selected_file: Path | None,
    provider: Any,
    visible_capabilities: tuple[tuple[str, str], ...] | None = None,
    domain_id: str = "local",
    enterprise_id: str = "local",
    project_id: str | None = None,
    stage_source: Path | None = None,
    wiki_backend: str = "json",
    offline_deterministic: bool = False,
    recorder=None,
) -> dict[str, Any]:
    tool_events: list[dict[str, Any]] = []
    wiki_state: dict[str, Any] = {}
    semantic_service_holder: dict[str, SemanticWiki] = {}
    session = app.new_session(
        domain={"id": domain_id},
        enterprise={"id": enterprise_id, "allow_remote_writes": False},
    )
    gateway = CatalystGateway(workspace)

    def execute_ask(invocation_id: str, trace_id: str, active_recorder):
        wiki_result = None
        stage_receipt = None
        knowledge_context = None
        request_capabilities = visible_capabilities
        request_provider = provider
        knowledge_decision_observer = None
        request_plugin_services: dict[str, Any] = {}
        if selected_file is not None:
            def capture(event):
                tool_events.append(event)
                record_file_tool_event(active_recorder, event)

            _register_file_title(app, capture)
        if project_id is not None:
            try:
                wiki = getattr(app, "_project_wiki", None) or ProjectWiki(
                    workspace,
                    app._enterprise_roots(enterprise_id),
                    enterprise_id=enterprise_id,
                    project_id=project_id,
                    backend=wiki_backend,
                )
                if selected_file is not None:
                    wiki.validate_selected_file(selected_file)
                if stage_source is not None:
                    stage_receipt = wiki.stage_markdown(stage_source)
                    wiki_state["stage"] = stage_receipt
                    active_recorder.event(
                        "knowledge.source.staged",
                        scope_id=stage_receipt["scope_id"],
                        source_id=stage_receipt["source_id"],
                        source_revision=stage_receipt["revision"],
                        status=stage_receipt["status"],
                        claim_count=stage_receipt["claim_count"],
                    )
                # Construction reconciles only genuinely pending mutations; this read-only
                # consumer itself records its R4 receipt without writing a Wiki transition.
                wiki_reader = SemanticWiki(wiki, recorder=active_recorder)
                semantic_service_holder[active_recorder.run_id] = wiki_reader
                request_plugin_services["semantic_wiki"] = wiki_reader
                request_plugin_services["project_wiki"] = getattr(app, "_project_wiki", None)
                wiki_result = wiki_reader.read_knowledge(
                    message,
                    mode="grounded_claims",
                    capabilities=_wiki_catalog_projection(app),
                    actor_origin="catalyst_deterministic",
                )
                accepted_semantics = wiki_reader.read_knowledge(
                    message,
                    mode="accepted_enterprise_semantics",
                    actor_origin="catalyst_deterministic",
                )
                wiki_result["accepted_semantic_view"] = accepted_semantics
                wiki_result["accepted_semantics"] = [
                    row for row in accepted_semantics["meanings"]
                    if row.get("freshness_status") == "fresh"
                ]
                wiki_state["read_contract"] = {
                    "contract_version": wiki_result["contract_version"],
                    "read_mode": wiki_result["read_mode"],
                    "scope_id": wiki_result["scope_id"],
                    "active_version_id": wiki_result["active_version_id"],
                    "freshness_status": wiki_result["freshness_status"],
                    "knowledge_status": wiki_result["knowledge_status"],
                    "accepted_semantic_status": accepted_semantics["knowledge_status"],
                    "accepted_semantic_freshness": accepted_semantics["freshness_status"],
                }
                wiki_state["search"] = wiki_result
            except WikiSourceIdentityAmbiguous:
                active_recorder.event(
                    "knowledge.source.staging_failed",
                    scope_id=f"enterprise:{enterprise_id}/project:{project_id}",
                    status="DENIED",
                    error_code="wiki_source_identity_ambiguous",
                )
                app.components.close_loaded(active_recorder)
                return app._failure_run(
                    invocation_id=invocation_id,
                    session_id=session.session_id,
                    trace_id=trace_id,
                    code="wiki_source_identity_ambiguous",
                    message=(
                        "Multiple configured Wiki roots contain different Markdown files at the same relative path; "
                        "no source was staged."
                    ),
                    failure_source="project_wiki_source_identity",
                    domain=session.domain,
                    enterprise=session.enterprise,
                )
            except WikiUnavailable:
                active_recorder.event(
                    "knowledge.query.returned",
                    scope_id=f"enterprise:{enterprise_id}/project:{project_id}",
                    query_sha256=hashlib.sha256(message.encode("utf-8")).hexdigest(),
                    status="UNAVAILABLE",
                    source_count=0,
                    claim_count=0,
                    capability_count=0,
                )
                app.components.close_loaded(active_recorder)
                return app._failure_run(
                    invocation_id=invocation_id,
                    session_id=session.session_id,
                    trace_id=trace_id,
                    code="wiki_unavailable",
                    message="The project Wiki is unavailable; no Wiki-dependent binding was selected.",
                    failure_source="project_wiki",
                    domain=session.domain,
                    enterprise=session.enterprise,
                )
            except WikiScopeError:
                active_recorder.event(
                    "knowledge.source.staging_failed" if stage_source is not None else "knowledge.query.returned",
                    scope_id=f"enterprise:{enterprise_id}/project:{project_id}",
                    status="DENIED" if stage_source is not None else "UNKNOWN",
                    error_code="wiki_source_out_of_scope" if stage_source is not None else None,
                )
                app.components.close_loaded(active_recorder)
                return app._failure_run(
                    invocation_id=invocation_id,
                    session_id=session.session_id,
                    trace_id=trace_id,
                    code="wiki_source_out_of_scope",
                    message="The selected source is outside the configured Wiki scope or is not valid UTF-8 Markdown.",
                    failure_source="project_wiki_scope",
                    domain=session.domain,
                    enterprise=session.enterprise,
                )

            active_recorder.event(
                "knowledge.query.returned",
                scope_id=wiki.scope_id,
                query_sha256=hashlib.sha256(message.encode("utf-8")).hexdigest(),
                status=wiki_result["status"],
                applicability_status=wiki_result["applicability_status"],
                source_count=len({item["source_id"] for item in [*wiki_result["claims"], *wiki_result["capabilities"]]}),
                claim_count=len(wiki_result["claims"]),
                capability_count=len(wiki_result["capabilities"]),
                read_mode=wiki_result["read_mode"],
                freshness_status=wiki_result["freshness_status"],
                active_version_id=wiki_result["active_version_id"],
                document_count=wiki_result["document_count"],
            )
            knowledge_context = wiki.format_context(wiki_result)
            allowed_specs = tuple(
                (item["capability_id"], item["capability_version"])
                for item in wiki_result["capabilities"]
                if selected_file is not None and wiki_result.get("applicability_status") != "UNKNOWN"
            )
            if visible_capabilities is not None:
                requested = set(visible_capabilities)
                unknown = requested - set(allowed_specs)
                if unknown:
                    app.components.close_loaded(active_recorder)
                    return app._failure_run(
                        invocation_id=invocation_id,
                        session_id=session.session_id,
                        trace_id=trace_id,
                        code="wiki_binding_not_found",
                        message="The requested exact binding is not a current Wiki-retrieved read-only candidate.",
                        failure_source="project_wiki_discovery",
                        domain=session.domain,
                        enterprise=session.enterprise,
                    )
                allowed_specs = tuple(spec for spec in allowed_specs if spec in requested)
            request_capabilities = allowed_specs

            def observe_knowledge_decision(binding: dict[str, Any]) -> None:
                capability_id = binding.get("capability_id")
                version = binding.get("capability_version")
                tool_call_id = binding.get("tool_call_id")
                binding_digest = binding.get("binding_digest")
                if not all(isinstance(value, str) and value for value in (capability_id, version, tool_call_id, binding_digest)):
                    return
                for claim in wiki_result["claims"]:
                    reference = claim.get("capability_ref") or {}
                    if reference.get("capability_id") == capability_id and reference.get("capability_version") == version:
                        _record_knowledge_use(
                            active_recorder,
                            claim,
                            capability_id,
                            version,
                            tool_call_id=tool_call_id,
                            binding_digest=binding_digest,
                        )
                for claim in wiki_result["capabilities"]:
                    if claim.get("capability_id") == capability_id and claim.get("capability_version") == version:
                        _record_knowledge_use(
                            active_recorder,
                            claim,
                            capability_id,
                            version,
                            tool_call_id=tool_call_id,
                            binding_digest=binding_digest,
                        )

            knowledge_decision_observer = observe_knowledge_decision
        if offline_deterministic:
            request_provider = DeterministicOfflineProvider(
                message=message,
                selected_file=selected_file,
                wiki_result=wiki_result,
            )
        try:
            product_run = session.ask(
                message,
                provider=request_provider,
                selected_file=selected_file,
                knowledge_context=knowledge_context,
                knowledge_decision_observer=knowledge_decision_observer,
                visible_capabilities=request_capabilities,
                invocation_id=invocation_id,
                trace_id=trace_id,
                recorder=active_recorder,
                _plugin_services=request_plugin_services,
            )
            return product_run
        finally:
            app.components.close_loaded(active_recorder)

    run = gateway.ask_natural_language(
        message=message,
        selected_file=selected_file,
        recorder=recorder,
        ask=execute_ask,
        tool_events=tool_events,
    )
    semantic_service = semantic_service_holder.get(run.get("run_id"))
    if semantic_service is not None:
        semantic_service.finalize_run(run["run_id"], run["status"])
    if project_id is not None:
        run["wiki"] = {
            "scope_id": f"enterprise:{enterprise_id}/project:{project_id}",
            "stage": wiki_state.get("stage"),
            "search": wiki_state.get("search"),
            "read_contract": wiki_state.get("read_contract"),
            "status": "UNAVAILABLE" if run["error"] and run["error"].get("code") == "wiki_unavailable" else wiki_state.get("search", {}).get("status", "UNKNOWN"),
        }
    return run


def _context(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    domain = {"id": args.domain_id}
    if args.domain_scope:
        domain["scope"] = args.domain_scope
    enterprise = {
        "id": args.enterprise_id,
        "report_detail": args.report_detail,
        "allow_local_artifacts": args.allow_local_artifacts,
        "allow_remote_writes": False,
    }
    return domain, enterprise


def _emit(value: Any) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, default=str))


def _concept_declarations(args: Any) -> dict[str, tuple[dict[str, Any], ...]]:
    """Read the repeatable declaration flags of ``ontology concepts define``."""
    attributes: list[dict[str, Any]] = []
    for spec in getattr(args, "attribute", None) or ():
        text = spec.strip()
        required = text.endswith("!")
        text = text[:-1].strip() if required else text
        name, _, value_type = text.partition(":")
        attributes.append({"name": name.strip(), "value_type": value_type.strip() or "text",
                           "required": required})
    relations: list[dict[str, Any]] = []
    for spec in getattr(args, "relation", None) or ():
        parts = [piece.strip() for piece in spec.split(":")]
        if len(parts) < 2 or len(parts) > 3 or not all(parts):
            raise ConceptError("concept_declaration_invalid",
                               f"--relation takes PREDICATE:TARGET[:one|many], not {spec!r}")
        relations.append({"predicate": parts[0], "target": parts[1],
                          "cardinality": parts[2] if len(parts) == 3 else "many"})
    metrics: list[dict[str, Any]] = []
    for spec in getattr(args, "metric", None) or ():
        name, _, unit = spec.strip().partition(":")
        metrics.append({"name": name.strip(), "unit": unit.strip()})
    return {
        "attributes": tuple(attributes),
        "relations": tuple(relations),
        "constraints": tuple({"statement": spec.strip(), "severity": "must"}
                             for spec in getattr(args, "constraint", None) or ()),
        "actions": tuple({"name": spec.strip()} for spec in getattr(args, "action", None) or ()),
        "metrics": tuple(metrics),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m catalyst_platform",
        description="Run Catalyst locally through its shared product CLI.",
        epilog=(
            "Component guide: docs/architecture/COMPONENT_RESPONSIBILITY_MAP.md. "
            "The CLI delegates to the Gateway or Workbench; the Agent Runtime executes requests, "
            "the Capability Catalog exposes exact ID/version bindings, ProjectWiki stores source "
            "evidence, SemanticWiki manages Enterprise Ontology candidates, and Run Observability "
            "records executions. Historical stage labels are not component names."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    assets = commands.add_parser('assets', help='register/list product asset metadata, or run the fixed source connection; no model API')
    assets.add_argument('asset_action', choices=('register','list','connect','acceptance'))
    assets.add_argument('--workspace',required=True,type=Path)
    assets.add_argument('--source-root',type=Path)
    assets.add_argument('--backend',choices=('json','sqlite'),default='json')
    assets.add_argument('--query')
    assets.add_argument('--source-id')
    assets.add_argument('--asset-id')
    assets.add_argument('--version')
    assets.add_argument('--enterprise-id',default='local')
    assets.add_argument('--project-id',default='asset-sources')

    wiki = commands.add_parser(
        "wiki",
        help="read local documents into Wiki and project the accepted store as pages; no model API",
    )
    wiki_actions = wiki.add_subparsers(dest="wiki_action", required=True)
    wiki_scan = wiki_actions.add_parser(
        "scan", help="register documents and record how far reading got; never calls a model")
    wiki_scan.add_argument("--workspace", required=True, type=Path)
    wiki_scan.add_argument("--wiki-root", action="append", type=Path)
    wiki_scan.add_argument("--enterprise-id", default="local")
    wiki_scan.add_argument("--project-id", required=True)
    wiki_scan.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    wiki_scan.add_argument("--file", action="append", type=Path,
                           help="one document to register; repeat for several")
    wiki_scan.add_argument("--source-root", type=Path,
                           help="register every supported document under this folder instead")
    wiki_scan.add_argument("--report-out", type=Path, help="write the scan summary here as JSON")
    wiki_pages = wiki_actions.add_parser(
        "pages", help="project accepted meanings into Markdown pages; deterministic and model-free")
    wiki_pages.add_argument("--workspace", required=True, type=Path)
    # Without a root every source looks like its file vanished, and the pages then say
    # evidence cannot be checked. Refuse instead of projecting a Wiki that only looks broken.
    wiki_pages.add_argument("--wiki-root", required=True, action="append", type=Path,
                            help="the folder(s) the sources are read from; required, "
                                 "because a page without it cannot be checked")
    wiki_pages.add_argument("--enterprise-id", default="local")
    wiki_pages.add_argument("--project-id", required=True)
    wiki_pages.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    wiki_pages.add_argument("--root", required=True, type=Path,
                            help="the folder the pages are projected into")
    wiki_pages.add_argument("--check", action="store_true",
                            help="report what would change and write nothing")
    wiki_pages.add_argument("--no-scan", action="store_true",
                            help="skip the mention scan, so pages carry no 出现位置 or 提及 sections")
    wiki_relocate = wiki_actions.add_parser(
        "relocate",
        help="map stale citations onto the text they still cite in the current revision; never calls a model")
    wiki_relocate.add_argument("--workspace", required=True, type=Path)
    wiki_relocate.add_argument("--wiki-root", action="append", type=Path)
    wiki_relocate.add_argument("--enterprise-id", default="local")
    wiki_relocate.add_argument("--project-id", required=True)
    wiki_relocate.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    wiki_relocate.add_argument("--source-id", action="append",
                               help="relocate only this staged source; repeat for several")
    wiki_relocate.add_argument("--check", action="store_true",
                               help="report what would move and write nothing")

    wiki_verify = wiki_actions.add_parser(
        "verify",
        help="check every stored artifact against the index and name orphans; writes nothing")
    wiki_verify.add_argument("--workspace", required=True, type=Path)
    wiki_verify.add_argument("--wiki-root", action="append", type=Path)
    wiki_verify.add_argument("--enterprise-id", default="local")
    wiki_verify.add_argument("--project-id", required=True)
    wiki_verify.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    wiki_verify.add_argument("--report-out", type=Path, help="write the verification report here as JSON")

    wiki_cold = wiki_actions.add_parser(
        "cold-read",
        help="read a copied Wiki and its page tree as a cold reader would; writes nothing")
    wiki_cold.add_argument("--workspace", required=True, type=Path,
                           help="the copied workspace; point it at the copy, never at the original")
    wiki_cold.add_argument("--wiki-root", required=True, action="append", type=Path,
                           help="where the sources live, so a missing or changed source can be reported")
    wiki_cold.add_argument("--enterprise-id", default="local")
    wiki_cold.add_argument("--project-id", required=True)
    wiki_cold.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    wiki_cold.add_argument("--root", required=True, type=Path,
                           help="the page tree that was copied together with the store")
    wiki_cold.add_argument("--report-out", type=Path, help="write the cold-read report here as JSON")


    inspect_file = commands.add_parser(
        "inspect-file",
        help="read a local Markdown or text title and return its exact source evidence",
    )
    inspect_file.add_argument("--workspace", required=True, type=Path)
    inspect_file.add_argument("--file", required=True, type=Path)

    inspect = commands.add_parser("inspect", help="read one persisted Run Observability record by run id")
    inspect.add_argument("--workspace", required=True, type=Path)
    inspect.add_argument("--run-id", required=True)

    export = commands.add_parser(
        "export-otlp",
        help="export one sanitized local run as OpenTelemetry OTLP HTTP spans",
    )
    export.add_argument("--workspace", required=True, type=Path)
    export.add_argument("--run-id", required=True)
    export.add_argument(
        "--endpoint",
        required=True,
        help="complete OTLP HTTP traces URL, for example http://127.0.0.1:4318/v1/traces",
    )

    use = commands.add_parser("use", help="retrieve local source evidence and write one Markdown report")
    _add_workspace(use)
    use.add_argument("--query", required=True)
    use.add_argument("--domain-id", required=True)
    use.add_argument("--domain-scope")
    use.add_argument("--enterprise-id", required=True)
    use.add_argument("--report-detail", choices=("brief", "full"), default="full")
    use.add_argument("--allow-local-artifacts", action="store_true")
    use.add_argument("--output-name", required=True)

    acquire = commands.add_parser("acquire-ripgrep", help="verify local ripgrep and register an exact read-only binding")
    _add_workspace(acquire)

    discover = commands.add_parser("discover", help="search the Capability Catalog for exact capability ID/version bindings")
    _add_workspace(discover)
    discover.add_argument("--query", help="search scoped Wiki capability meaning for relevant exact active bindings")
    discover.add_argument("--project-id", help="enable project-scoped source and capability-meaning discovery")
    discover.add_argument("--enterprise-id", default="local")
    discover.add_argument(
        "--wiki-backend", choices=("json", "sqlite", "unavailable"), default="json"
    )

    invoke = commands.add_parser("invoke", help="invoke one exact Runtime Binding in a new local session")
    _add_workspace(invoke)
    invoke.add_argument("--capability-id", required=True)
    invoke.add_argument("--version", required=True)
    invoke.add_argument("--input-json", required=True)
    invoke.add_argument("--domain-id", required=True)
    invoke.add_argument("--enterprise-id", required=True)
    invoke.add_argument("--allow-local-artifacts", action="store_true")
    invoke.add_argument("--project-id", help="use the project-scoped Wiki adapter for Wiki-backed bindings")
    invoke.add_argument(
        "--wiki-backend", choices=("json", "sqlite", "unavailable"), default="json"
    )

    ask = commands.add_parser(
        "ask",
        help="ask the Workbench to run a natural-language request through the Agent Runtime and verified read-only tools",
    )
    ask.add_argument("--workspace", required=True, type=Path)
    ask.add_argument("--wiki-root", action="append", type=Path)
    ask.add_argument("--enterprise-access-map", type=Path)
    ask.add_argument("--message", required=True)
    ask.add_argument("--file", type=Path, help="explicitly select the one local file the model may read")
    ask.add_argument("--project-id", help="enable project-scoped source evidence and capability context for this request")
    ask.add_argument("--stage-source", type=Path, help="stage one scoped UTF-8 Markdown source as a candidate")
    ask.add_argument(
        "--wiki-backend",
        choices=("json", "sqlite", "unavailable"),
        default="json",
        help="local Wiki store; 'unavailable' exercises the explicit disconnect outcome",
    )
    ask.add_argument(
        "--offline-deterministic",
        action="store_true",
        help="use the local acceptance Provider; it makes no external call and is not a live LLM",
    )
    ask.add_argument(
        "--interactive-provider",
        nargs="?",
        const="deepseek",
        choices=("deepseek", "openai-compatible"),
        metavar="PROVIDER",
        help="use one-run hidden-key setup (defaults to DeepSeek; no key is saved)",
    )
    ask.add_argument("--domain-id", default="local")
    ask.add_argument("--enterprise-id", default="local")

    understand = commands.add_parser(
        "understand",
        help="analyze explicitly selected local sources through the Bounded Source Analysis Port and Run Observability",
    )
    understand.add_argument("--workspace", required=True, type=Path)
    understand.add_argument("--source-root", required=True, type=Path)
    understand.add_argument("--source", required=True, action="append", type=Path)
    understand.add_argument("--message", required=True)
    understand.add_argument("--intent", choices=tuple(item.value for item in UnderstandIntent))
    understand.add_argument("--scope-id")
    understand.add_argument("--depth", choices=("inventory", "targeted", "semantic", "bounded_deep"), default="semantic")
    understand.add_argument("--budget-steps", type=int, default=8)
    understand.add_argument("--producer-items", type=Path, help="local JSON array from the declared semantic producer")
    understand.add_argument("--producer-invocation-id", help="opaque caller-attested Codex invocation identifier")
    understand.add_argument("--producer-model-id", help="model identifier only when observed by the caller")
    understand.add_argument("--concept-set", type=Path,
                            help="read the concept set from this JSON file instead of the starter pack")
    understand.add_argument("--concepts-project-id",
                            help="read the concept set of this ProjectWiki scope; needs --concept-wiki-root")
    understand.add_argument("--concept-wiki-root", action="append", type=Path,
                            help="source root of the ProjectWiki whose concept set is read")
    understand.add_argument("--concepts-enterprise-id", default="local",
                            help="enterprise of the concept set scope (default local)")
    understand.add_argument("--correlation-id", help="link this Run Observability record to a prior Understand preparation run")

    understand_expand = commands.add_parser(
        "understand-expand",
        help="expand evidence only inside a previously inventoried source set through the same Bounded Source Analysis Port and Run Observability",
    )
    understand_expand.add_argument("--workspace", required=True, type=Path)
    understand_expand.add_argument("--source-root", required=True, type=Path)
    understand_expand.add_argument("--prepared-result", required=True, type=Path)
    understand_expand.add_argument("--request", required=True, type=Path)
    understand_expand.add_argument("--scope-id", default="scope_unassigned")
    understand_expand.add_argument("--correlation-id", help="link this Run Observability record to the preparation run")

    monitor = commands.add_parser(
        "monitor",
        help="open the local Run Observability monitor and replay previous Run IDs",
    )
    monitor.add_argument("--workspace", required=True, type=Path)
    monitor.add_argument("--wiki-root", action="append", type=Path)
    monitor.add_argument("--port", type=int, default=8765)
    monitor.add_argument("--mode", choices=("mock", "blocked"), default="mock",
                         help="offline S1 demo (default) or missing-provider refusal; no paid calls")
    monitor.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")

    evolve = commands.add_parser("evolve-understand", help="compare Understand candidates against a local JSON benchmark")
    _add_workspace(evolve)
    evolve.add_argument("--benchmark", required=True, type=Path)
    evolve.add_argument("--activate", action="store_true", help="activate only after a passing local benchmark gate")

    rollback = commands.add_parser("rollback-understand", help="restore a registered Understand implementation")
    _add_workspace(rollback)
    rollback.add_argument("--implementation", required=True)

    component = commands.add_parser(
        "component",
        help="manage the local Component Lifecycle: validate, admit, activate, restore, or deactivate a Tool component",
    )
    component_actions = component.add_subparsers(dest="component_action", required=True)
    component_discover = component_actions.add_parser("discover", help="validate a local component Manifest without importing code")
    component_admit = component_actions.add_parser("admit", help="admit exact source bytes after SHA-256 confirmation")
    component_activate = component_actions.add_parser("activate", help="bind one admitted exact component version")
    component_deactivate = component_actions.add_parser("deactivate", help="withdraw new runs from the active component version")
    component_list = component_actions.add_parser("list", help="list admitted and active component versions")
    for component_parser in (component_discover, component_admit, component_activate, component_deactivate, component_list):
        component_parser.add_argument("--workspace", required=True, type=Path)
    component_discover.add_argument("--source", required=True, type=Path)
    component_admit.add_argument("--source", required=True, type=Path)
    component_admit.add_argument("--expected-sha256", required=True)
    component_activate.add_argument("--component-id", required=True)
    component_activate.add_argument("--version", required=True)
    component_deactivate.add_argument("--component-id", required=True)

    ontology = commands.add_parser(
        "ontology",
        help="manage scoped Enterprise Ontology candidates on the ProjectWiki source-evidence store",
    )
    ontology_actions = ontology.add_subparsers(dest="ontology_action", required=True)
    source = ontology_actions.add_parser("source", help="manage source evidence used by Enterprise Ontology candidates")
    source_actions = source.add_subparsers(dest="source_action", required=True)
    source_stage = source_actions.add_parser("stage", help="record one source revision as ProjectWiki evidence for later review")
    _add_semantic_context(source_stage, actor_origin="codex_fixture")
    source_stage.add_argument("--file", required=True, type=Path)

    candidate = ontology_actions.add_parser("candidate", help="propose, structurally evaluate, or record a local decision for an ontology candidate")
    candidate_actions = candidate.add_subparsers(dest="candidate_action", required=True)
    candidate_propose = candidate_actions.add_parser("propose", help="propose explicit Markdown claims and relations")
    _add_semantic_context(candidate_propose, actor_origin="codex_fixture")
    candidate_propose.add_argument("--file", required=True, type=Path)
    candidate_evaluate = candidate_actions.add_parser("evaluate", help="run structural evidence checks; this is not independent semantic evaluation or acceptance")
    _add_semantic_context(candidate_evaluate, actor_origin="independent_evaluator")
    candidate_evaluate.add_argument("--candidate-id", required=True)
    candidate_evaluate.add_argument("--evaluator-id", default="structural-evaluator-v1")
    candidate_decide = candidate_actions.add_parser("decide", help="record an explicit local manager review disposition")
    _add_semantic_context(candidate_decide, actor_origin="manager_acceptance")
    candidate_decide.add_argument("--candidate-id", required=True)
    candidate_decide.add_argument("--decision", choices=("ACCEPTED", "REJECTED", "DEFERRED", "NEEDS_REVIEW"), required=True)
    candidate_decide.add_argument("--reason-code", required=True)
    candidate_decide.add_argument(
        "--reviewer-report", type=Path,
        help="the independent review this acceptance rests on; its bytes are hashed into the signed receipt")
    candidate_decide.add_argument(
        "--reviewer-disposition", choices=("ACCEPT", "REVISE", "REJECT", "DEFER"), default="ACCEPT")

    ontology_key = ontology_actions.add_parser(
        "key", help="create or inspect the local reviewer and owner signing keys")
    key_actions = ontology_key.add_subparsers(dest="key_action", required=True)
    ontology_key_init = key_actions.add_parser("init", help="create any missing local signing key")
    ontology_key_init.add_argument("--workspace", required=True, type=Path)
    ontology_key_status = key_actions.add_parser("status", help="report which local signing keys exist")
    ontology_key_status.add_argument("--workspace", required=True, type=Path)

    ontology_chain = ontology_actions.add_parser(
        "chain", help="stage, propose, evaluate, approve, activate, and cold-read one material in one command")
    ontology_chain.add_argument("--workspace", required=True, type=Path)
    ontology_chain.add_argument("--file", required=True, type=Path)
    ontology_chain.add_argument("--review", required=True, type=Path,
                                help="the independent review whose bytes are hashed into the signed receipt")
    ontology_chain.add_argument("--query", help="read back only what answers this question instead of every active meaning")
    ontology_chain.add_argument("--wiki-root", action="append", type=Path)
    ontology_chain.add_argument("--enterprise-id", default="synthetic")
    ontology_chain.add_argument("--project-id", default="ontology-chain")
    ontology_chain.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    ontology_chain.add_argument(
        "--reviewer-disposition", choices=("ACCEPT", "REVISE", "REJECT", "DEFER"), default="ACCEPT")
    ontology_chain.add_argument("--limit", type=int, default=100)
    ontology_chain.add_argument("--report-out", type=Path, help="write the chain report here as JSON")

    ontology_review = ontology_actions.add_parser(
        "review", help="seal a candidate and its material for an outside reviewer, then record the answer")
    review_actions = ontology_review.add_subparsers(dest="review_action", required=True)
    review_package = review_actions.add_parser(
        "package", help="write the original material and the candidate as one sealed package")
    review_package.add_argument("--workspace", required=True, type=Path)
    review_package.add_argument("--wiki-root", required=True, action="append", type=Path)
    review_package.add_argument("--enterprise-id", default="local")
    review_package.add_argument("--project-id", required=True)
    review_package.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    review_package.add_argument("--candidate-id", required=True)
    review_package.add_argument("--out", required=True, type=Path)
    review_package.add_argument("--question", help="the question the reviewer answers about this candidate")
    review_submit = review_actions.add_parser(
        "submit", help="record an outside reviewer's answer over a sealed package")
    _add_semantic_context(review_submit, actor_origin="independent_evaluator")
    review_submit.add_argument("--candidate-id", required=True)
    review_submit.add_argument("--package", required=True, type=Path)
    review_submit.add_argument("--response", required=True, type=Path)
    review_submit.add_argument("--evaluator-id", default="external-reviewer")
    review_submit.add_argument("--evaluator-context", default="external_model")
    review_submit.add_argument("--record-only", action="store_true",
                               help="record the review without letting the owner accept")

    version = ontology_actions.add_parser("version", help="diff, activate, or roll back accepted scoped semantic versions")
    version_actions = version.add_subparsers(dest="version_action", required=True)
    version_diff = version_actions.add_parser(
        "diff", help="compare a candidate against its pinned parent, or read what an accepted version changed")
    _add_semantic_context(version_diff, actor_origin="catalyst_deterministic")
    version_target = version_diff.add_mutually_exclusive_group(required=True)
    version_target.add_argument("--candidate-id", help="compare this candidate against its pinned parent")
    version_target.add_argument("--version-id", help="read the comparison an accepted version kept")
    version_activate = version_actions.add_parser("activate", help="activate one already accepted version")
    _add_semantic_context(version_activate, actor_origin="manager_acceptance")
    version_activate.add_argument("--version-id", required=True)
    version_activate.add_argument("--expected-head", help="compare-and-swap active version ID, or 'none' for an empty head")
    version_activate.add_argument("--branch-switch", action="store_true", help="explicitly switch to an accepted sibling/history branch")
    version_activate.add_argument("--sign", action="store_true",
                                  help="sign the version authority receipt from the local owner key")
    version_rollback = version_actions.add_parser("rollback", help="restore a previously accepted semantic version")
    _add_semantic_context(version_rollback, actor_origin="manager_acceptance")
    version_rollback.add_argument("--version-id", required=True)
    version_rollback.add_argument("--expected-head", help="compare-and-swap current active version ID, or 'none'")
    version_rollback.add_argument("--sign", action="store_true",
                                  help="sign the version authority receipt from the local owner key")

    semantic_query = ontology_actions.add_parser("query", help="return the structured scoped Enterprise Ontology projection")
    _add_semantic_context(semantic_query, actor_origin="catalyst_deterministic")
    semantic_query.add_argument("--query", required=True)
    semantic_query.add_argument(
        "--mode",
        choices=("source_discovery", "grounded_claims", "accepted_enterprise_semantics"),
        default="accepted_enterprise_semantics",
        help="select source discovery, grounded claims, or accepted Enterprise Ontology meanings from the shared ProjectWiki contract",
    )
    semantic_wiki = ontology_actions.add_parser("wiki", help="return the human-readable scoped Enterprise Ontology projection")
    _add_semantic_context(semantic_wiki, actor_origin="catalyst_deterministic")
    semantic_wiki.add_argument("--query", required=True)
    semantic_consumption = ontology_actions.add_parser(
        "consumption", help="summarize what consumers asked of the accepted versions and what answered")
    semantic_consumption.add_argument("--workspace", required=True, type=Path)
    semantic_consumption.add_argument("--since", type=int, help="only rows recorded at or after this Unix second")
    semantic_consumption.add_argument("--entries", action="store_true",
                                      help="include every ledger row, not just the per-question summary")
    semantic_score = ontology_actions.add_parser(
        "score", help="score a candidate or an accepted version against the thirteen modelling measures; no model API")
    semantic_score.add_argument("--workspace", required=True, type=Path)
    semantic_score.add_argument("--wiki-root", required=True, action="append", type=Path)
    semantic_score.add_argument("--enterprise-id", default="local")
    semantic_score.add_argument("--project-id", required=True)
    semantic_score.add_argument("--wiki-backend", choices=("json", "sqlite"), default="json")
    semantic_score.add_argument("--candidate-id", help="score this candidate instead of the active version")
    semantic_score.add_argument("--version-id", help="score this accepted version instead of the active one")
    semantic_score.add_argument("--out", type=Path, help="write the full report to this JSON file")
    semantic_score.add_argument("--require-pass", type=int, metavar="N",
                                help="exit 1 unless at least N of the thirteen measures pass")
    semantic_relations = ontology_actions.add_parser("relations", help="resolve an exact active entity and expand its outgoing relations")
    _add_semantic_context(semantic_relations, actor_origin="catalyst_deterministic")
    semantic_relations.add_argument("--entity", required=True)
    semantic_relations.add_argument("--version-id")
    semantic_relations.add_argument("--limit", type=int, default=100)
    semantic_graph = ontology_actions.add_parser("graph", help="return a version-pinned, read-only Enterprise Ontology provenance graph")
    _add_semantic_context(semantic_graph, actor_origin="catalyst_deterministic")
    semantic_graph.add_argument("--version-id")
    semantic_graph.add_argument("--limit", type=int, default=100)
    semantic_inspect = ontology_actions.add_parser("inspect", help="inspect scoped semantic version and transition identities")
    _add_semantic_context(semantic_inspect, actor_origin="catalyst_deterministic")

    concepts = ontology_actions.add_parser(
        "concepts", help="show, define, deprecate or adopt the concept set this scope extracts with")
    concept_actions = concepts.add_subparsers(dest="concept_action", required=True)
    concepts_show = concept_actions.add_parser(
        "show", help="read the scope's concept set with its versions, decisions and retirements")
    _add_semantic_context(concepts_show, actor_origin="catalyst_deterministic")
    concepts_define = concept_actions.add_parser(
        "define", help="add one concept to the scope and publish the version that holds it")
    _add_semantic_context(concepts_define, actor_origin="manager_acceptance")
    concepts_define.add_argument("--concept-id", required=True, help="stable ascii id, e.g. Ward")
    concepts_define.add_argument("--name", required=True, help="the word this scope uses, e.g. 病区")
    concepts_define.add_argument("--meta-kind", required=True,
                                 choices=sorted(META_KINDS), help="which upper kind it is")
    concepts_define.add_argument("--criteria", required=True, help="what belongs to it, in one line")
    concepts_define.add_argument("--alias", action="append", help="another spelling of the same concept")
    concepts_define.add_argument("--attribute", action="append", metavar="NAME[:TYPE][!]",
                                 help="a property of its instances; TYPE is one of text/number/date/"
                                      "boolean/reference, a trailing ! marks it required")
    concepts_define.add_argument("--relation", action="append", metavar="PREDICATE:TARGET[:one|many]",
                                 help="a way this type reaches another concept or upper kind")
    concepts_define.add_argument("--constraint", action="append", metavar="STATEMENT",
                                 help="something its instances must satisfy")
    concepts_define.add_argument("--action", action="append", metavar="NAME",
                                 help="something its instances do")
    concepts_define.add_argument("--metric", action="append", metavar="NAME[:UNIT]",
                                 help="a quantity its instances are measured by")
    concepts_define.add_argument("--reason", required=True, help="one line saying why the scope needs it")
    concepts_deprecate = concept_actions.add_parser(
        "deprecate", help="retire one concept, keeping the spellings it used to answer to")
    _add_semantic_context(concepts_deprecate, actor_origin="manager_acceptance")
    concepts_deprecate.add_argument("--concept-id", required=True)
    concepts_deprecate.add_argument("--replacement", help="the concept that now stands for it")
    concepts_deprecate.add_argument("--reason", required=True)
    concepts_adopt = concept_actions.add_parser(
        "adopt", help="write the starter pack into the scope, so its concepts are its own data")
    _add_semantic_context(concepts_adopt, actor_origin="manager_acceptance")
    concepts_adopt.add_argument("--reason", required=True)

    external = ontology_actions.add_parser("external", help="record external semantic-producer receipts against original ProjectWiki sources")
    external_actions = external.add_subparsers(dest="external_action", required=True)
    external_submit = external_actions.add_parser("submit", help="validate and submit a Codex candidate anchored to an existing source revision")
    _add_semantic_context(
        external_submit,
        actor_origin="codex_external",
        actor_choices=("codex_external",),
        correlation_required=True,
    )
    external_submit.add_argument("--submission", required=True, type=Path)
    external_submit_v2 = external_actions.add_parser("submit-v2", help="validate and submit a typed V2 Codex candidate anchored to an existing source revision")
    _add_semantic_context(
        external_submit_v2,
        actor_origin="codex_external",
        actor_choices=("codex_external",),
        correlation_required=True,
    )
    external_submit_v2.add_argument("--submission", required=True, type=Path)
    external_read = external_actions.add_parser("read-receipt", help="record a Codex-reported source read after checking the staged source revision")
    _add_semantic_context(
        external_read,
        actor_origin="codex_external",
        actor_choices=("codex_external",),
        correlation_required=True,
    )
    external_read.add_argument("--source-id", required=True)
    external_read.add_argument("--source-revision", required=True)

    understand = ontology_actions.add_parser("understand", help="submit or query a candidate-only handoff from the Bounded Source Analysis Port")
    understand_actions = understand.add_subparsers(dest="understand_action", required=True)
    understand_submit = understand_actions.add_parser("submit", help="store one frozen UnderstandingResult as a candidate-only handoff")
    _add_semantic_context(understand_submit, actor_origin="codex_fixture")
    understand_submit.add_argument("--input", required=True, type=Path)
    understand_submit.add_argument("--source-root", required=True, type=Path)
    understand_graph = understand_actions.add_parser("graph", help="read one candidate-only graph projection")
    _add_semantic_context(understand_graph, actor_origin="codex_fixture")
    understand_graph.add_argument("--candidate-id", required=True)
    understand_graph.add_argument("--limit", type=int, default=500)
    understand_active_graph = understand_actions.add_parser("active-graph", help="read the active-only graph with explicit authority and active-version status")
    _add_semantic_context(understand_active_graph, actor_origin="codex_fixture")
    understand_active_graph.add_argument("--limit", type=int, default=100)
    understand_items = understand_actions.add_parser("items", help="read candidate Entity, Relation, Condition, Exception, Claim or UNKNOWN items")
    _add_semantic_context(understand_items, actor_origin="codex_fixture")
    understand_items.add_argument("--candidate-id", required=True)
    understand_items.add_argument("--kind", choices=("all", "entity", "alias", "relation", "condition", "exception", "claim", "unknown", "negative_claim"), default="all")
    understand_items.add_argument("--limit", type=int, default=100)
    understand_items.add_argument("--offset", type=int, default=0, help="zero-based offset into a stable, ID-sorted candidate item list")
    understand_result = understand_actions.add_parser("result", help="read a safe metadata summary; full result remains denied until trusted content authorization exists")
    _add_semantic_context(understand_result, actor_origin="codex_fixture")
    understand_result.add_argument("--candidate-id", required=True)
    understand_relations = understand_actions.add_parser("relations", help="query candidate relations by an exact producer Entity ID or key")
    _add_semantic_context(understand_relations, actor_origin="codex_fixture")
    understand_relations.add_argument("--candidate-id", required=True)
    understand_relations.add_argument("--entity-ref", required=True)
    understand_evidence = understand_actions.add_parser("evidence", help="resolve one original evidence ID to a scoped locator")
    _add_semantic_context(understand_evidence, actor_origin="codex_fixture")
    understand_evidence.add_argument("--candidate-id", required=True)
    understand_evidence.add_argument("--evidence-id", required=True)
    understand_compare = understand_actions.add_parser("compare", help="compare candidate and active authority without inferring a semantic crosswalk")
    _add_semantic_context(understand_compare, actor_origin="codex_fixture")
    understand_compare.add_argument("--candidate-id", required=True)


    ask.add_argument(
        "--capability",
        action="append",
        default=None,
        metavar="ID@VERSION",
        help="explicitly expose one active, read-only exact binding to this ask; repeat to add another",
    )
    return parser


def _parse_capability_specs(values: list[str] | None) -> tuple[tuple[str, str], ...] | None:
    if values is None:
        return None
    parsed = []
    for value in values:
        if not isinstance(value, str) or "@" not in value:
            raise ValueError("--capability must use the exact ID@VERSION form")
        capability_id, version = value.rsplit("@", 1)
        if not capability_id or not version or any(char.isspace() for char in value):
            raise ValueError("--capability must use the exact ID@VERSION form")
        parsed.append((capability_id, version))
    if len(set(parsed)) != len(parsed):
        raise ValueError("--capability cannot repeat the same exact binding")
    return tuple(parsed)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    understand_input_bytes: bytes | None = None
    try:
        if args.command == 'assets':
            from .asset_records import builtin_assets
            if args.asset_action=='connect':
                from .source_connection import build_source_connection,run_source_connection
                if args.source_root is None or not args.query or not args.source_id:
                    raise ValueError('connect requires source-root, query and exact source-id; sources must already be staged')
                wiki=ProjectWiki(args.workspace,[args.source_root],enterprise_id=args.enterprise_id,project_id=args.project_id,backend=args.backend)
                app,service,composer=build_source_connection(args.workspace,wiki)
                try:result=run_source_connection(app,service,args.query,args.source_id)
                finally:composer.close()
            else:
                app=CatalystWorkbench(args.workspace,[args.workspace])
                if args.asset_action=='register':result=app.components.assets.register(builtin_assets())
                elif args.asset_action=='acceptance':result=app.components.assets.acceptance_plan(args.asset_id,args.version)
                else:result={'items':app.components.assets.list()}
            _emit(result)
            return 0
        if args.command in {"inspect-file", "inspect"}:
            gateway = CatalystGateway(args.workspace)
            if args.command == "inspect-file":
                run = gateway.inspect_file(args.file)
                _emit(run)
                return 0 if run["status"] == "success" else 1
            inspected = gateway.inspect_run(args.run_id)
            if inspected is None:
                _emit(
                    {
                        "status": "not_found",
                        "run_id": args.run_id,
                        "trace_path": str(gateway.traces.path),
                    }
                )
                return 2
            _emit(inspected)
            return 0

        if args.command == "export-otlp":
            exported = export_run_otlp(args.workspace, args.run_id, args.endpoint)
            _emit(exported)
            return 0

        if args.command == "understand":
            source_root = args.source_root.expanduser().resolve()
            request_payload = {
                "message": args.message,
                "sources": [Path(item).as_posix() for item in args.source],
                "intent": args.intent,
                "scope_id": args.scope_id,
                "depth": args.depth,
                "budget_steps": args.budget_steps,
            }
            source_refs = tuple(
                item if item.is_absolute() else source_root / item
                for item in args.source
            )
            request_digest = hashlib.sha256(
                json.dumps(request_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            request = UnderstandingRequest(
                request_id=f"req_{request_digest[:20]}",
                message=args.message,
                source_refs=source_refs,
                intent=args.intent,
                scope_id=args.scope_id,
                requested_depth=args.depth,
                budget_steps=args.budget_steps,
            )
            producer_items = None
            producer_items_digest = None
            if args.producer_items is not None:
                raw_items = args.producer_items.read_bytes()
                if len(raw_items) > _MAX_EXTERNAL_SUBMISSION_BYTES:
                    raise ValueError("producer item file exceeds local size limit")
                producer_items_digest = hashlib.sha256(raw_items).hexdigest()
                producer_items = json.loads(raw_items.decode("utf-8"))
                if not isinstance(producer_items, list):
                    raise ValueError("producer item file must contain a JSON array")
                if not args.producer_invocation_id:
                    raise ValueError("--producer-invocation-id is required with --producer-items")
            gateway = CatalystGateway(args.workspace)
            port = UnderstandPort()

            concept_set = None
            if args.concept_set is not None:
                raw_concepts = args.concept_set.read_bytes()
                if len(raw_concepts) > _MAX_EXTERNAL_SUBMISSION_BYTES:
                    raise ValueError("concept set file exceeds local size limit")
                payload = json.loads(raw_concepts.decode("utf-8"))
                # The output of `ontology concepts show` is accepted as written: its set is
                # under scope_concept_set, and nothing else about that projection matters here.
                if isinstance(payload, dict) and isinstance(payload.get("scope_concept_set"), dict):
                    payload = payload["scope_concept_set"]
                concept_set = ConceptSet.from_dict(payload)
            elif args.concepts_project_id is not None:
                if not args.concept_wiki_root:
                    raise ValueError("--concepts-project-id needs --concept-wiki-root")
                concept_set = ProjectWiki(
                    args.workspace, args.concept_wiki_root, enterprise_id=args.concepts_enterprise_id,
                    project_id=args.concepts_project_id).concept_set()
            elif args.concept_wiki_root:
                raise ValueError("--concept-wiki-root needs --concepts-project-id")

            def run_understand(recorder):
                result = port.understand(request, source_root=source_root, recorder=recorder,
                                         **({"concepts": concept_set} if concept_set is not None else {}))
                if producer_items is not None:
                    result = port.attach_producer_items(
                        result,
                        producer_kind="CODEX_EXTERNAL",
                        producer_invocation_id=args.producer_invocation_id,
                        producer_model_id=args.producer_model_id,
                        items=producer_items,
                        recorder=recorder,
                        concepts=concept_set,
                    )
                return result.to_dict()

            outcome = gateway.semantic_operation(
                operation="understand.inspect",
                scope_id=args.scope_id or "scope_unassigned",
                actor_origin="codex_external",
                input_value={
                    "request_sha256": request_digest,
                    "producer_items_sha256": producer_items_digest,
                    "source_count": len(args.source),
                    "intent": args.intent,
                    "depth": args.depth,
                    "budget_steps": args.budget_steps,
                    "caller_kind": "CODEX_CLI",
                    "port_producer_kind": "CODEX_EXTERNAL" if producer_items is not None else "CATALYST_DETERMINISTIC",
                },
                action=run_understand,
                correlation_id=args.correlation_id,
            )
            outcome["producer_kind"] = "CODEX_EXTERNAL" if producer_items is not None else "CATALYST_DETERMINISTIC"
            outcome["codex_internal_reasoning"] = "NOT_OBSERVED_BY_R4"
            _emit(outcome)
            return 0 if outcome["status"] == "success" else 1

        if args.command == "understand-expand":
            prepared_raw = args.prepared_result.read_bytes()
            request_raw = args.request.read_bytes()
            if len(prepared_raw) > _MAX_EXTERNAL_SUBMISSION_BYTES or len(request_raw) > 64 * 1024:
                raise ValueError("prepared result or expansion request exceeds local size limit")
            prepared_value = json.loads(prepared_raw.decode("utf-8"))
            request_value = json.loads(request_raw.decode("utf-8"))
            if not isinstance(prepared_value, dict) or not isinstance(request_value, dict):
                raise ValueError("prepared result and expansion request must be JSON objects")
            prepared_result = prepared_value.get("result", prepared_value)
            if not isinstance(prepared_result, dict):
                raise ValueError("prepared result envelope is invalid")
            source_rows = prepared_result.get("source_inventory")
            evidence_rows = prepared_result.get("evidence_refs")
            if not isinstance(source_rows, list) or not isinstance(evidence_rows, list):
                raise ValueError("prepared result must contain source_inventory and evidence_refs arrays")
            try:
                source_inventory = tuple(SourceRecord(**row) for row in source_rows if isinstance(row, dict))
                existing_evidence = tuple(EvidenceRef(**row) for row in evidence_rows if isinstance(row, dict))
            except TypeError as exc:
                raise ValueError("prepared result has an invalid Understand schema") from exc
            if len(source_inventory) != len(source_rows) or len(existing_evidence) != len(evidence_rows):
                raise ValueError("prepared result contains an invalid inventory or evidence row")
            request_fields = {
                "request_id", "query", "allowed_source_ids", "known_evidence_ids", "locator_hints",
                "max_steps", "max_additional_refs", "max_bytes",
            }
            if set(request_value) - request_fields:
                raise ValueError("expansion request contains unsupported fields")
            request_payload = dict(request_value)
            for name in ("allowed_source_ids", "known_evidence_ids", "locator_hints"):
                items = request_payload.get(name, [])
                if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
                    raise ValueError(f"{name} must be a string array")
                request_payload[name] = tuple(items)
            expansion_request = EvidenceExpansionRequest(**request_payload)
            request_digest = hashlib.sha256(request_raw).hexdigest()
            prepared_digest = hashlib.sha256(prepared_raw).hexdigest()
            gateway = CatalystGateway(args.workspace)
            port = UnderstandPort()

            outcome = gateway.semantic_operation(
                operation="understand.evidence_expand",
                scope_id=args.scope_id,
                actor_origin="codex_external",
                input_value={
                    "prepared_result_sha256": prepared_digest,
                    "expansion_request_sha256": request_digest,
                    "source_count": len(source_inventory),
                    "allowed_source_count": len(expansion_request.allowed_source_ids),
                    "max_steps": expansion_request.max_steps,
                    "max_additional_refs": expansion_request.max_additional_refs,
                    "max_bytes": expansion_request.max_bytes,
                    "caller_kind": "CODEX_CLI",
                    "port_producer_kind": "CATALYST_DETERMINISTIC",
                },
                action=lambda recorder: port.expand_evidence(
                    source_inventory,
                    existing_evidence,
                    expansion_request,
                    source_root=args.source_root,
                    recorder=recorder,
                ).to_dict(),
                correlation_id=args.correlation_id,
            )
            outcome["producer_kind"] = "CATALYST_DETERMINISTIC"
            outcome["codex_internal_reasoning"] = "NOT_OBSERVED_BY_R4"
            _emit(outcome)
            return 0 if outcome["status"] == "success" else 1

        if args.command == "ontology":
            if args.ontology_action == "key":
                from .semantic_keys import ROLES, ensure_key, key_path, load_key
                if args.key_action == "init":
                    rows = [{"role": role, "path": str(ensure_key(args.workspace, role))}
                            for role in ROLES]
                    _emit({"status": "success", "workspace": str(args.workspace), "keys": rows})
                    return 0
                rows = [{"role": role, "present": load_key(args.workspace, role) is not None,
                         "path": str(key_path(args.workspace, role))} for role in ROLES]
                _emit({"status": "success", "workspace": str(args.workspace), "keys": rows})
                return 0
            if args.ontology_action == "chain":
                from .semantic_chain import run_chain
                outcome = run_chain(
                    workspace=args.workspace, source=args.file, review=args.review,
                    query=args.query, enterprise_id=args.enterprise_id, project_id=args.project_id,
                    backend=args.wiki_backend, disposition=args.reviewer_disposition,
                    source_root=args.wiki_root, report_path=args.report_out, limit=args.limit)
                _emit(outcome)
                return 0 if outcome["status"] in {"success", "no_op"} else 1
            if args.ontology_action == "consumption":
                from .consumption import summarize
                outcome = summarize(args.workspace, since=args.since)
                if not args.entries:
                    outcome.pop("entries", None)
                _emit(outcome)
                return 0
            if args.ontology_action == "score":
                from .semantic_score import score_wiki, write_report
                score_wiki_instance = ProjectWiki(
                    args.workspace, args.wiki_root, enterprise_id=args.enterprise_id,
                    project_id=args.project_id, backend=args.wiki_backend)
                outcome = score_wiki(score_wiki_instance, candidate_id=args.candidate_id,
                                     version_id=args.version_id)
                if args.out is not None:
                    outcome["report_path"] = str(write_report(outcome, args.out))
                _emit(outcome)
                if args.require_pass is not None and outcome["passed"] < args.require_pass:
                    return 1
                return 0
            if args.ontology_action == "concepts":
                from . import ontology_concepts as concept_ledger
                concept_wiki = ProjectWiki(
                    args.workspace, args.wiki_root, enterprise_id=args.enterprise_id,
                    project_id=args.project_id, backend=args.wiki_backend)
                if args.concept_action == "show":
                    _emit({"status": "success", "scope_id": concept_wiki.scope_id,
                           **concept_projection(concept_wiki.concept_state())})
                    return 0
                concept = None
                if args.concept_action == "define":
                    # Read the row back the way the ledger will read it, so a malformed flag
                    # fails here with a named code instead of inside the stored version.
                    concept = Concept.from_dict({
                        "concept_id": args.concept_id, "name": args.name,
                        "meta_kind": args.meta_kind, "criteria": args.criteria,
                        "aliases": list(args.alias or ()),
                        **_concept_declarations(args),
                    }, origin=args.actor_origin)
                concept_input = {"concept_action": args.concept_action, "reason": args.reason,
                                 "concept": concept.to_dict() if concept is not None else None,
                                 "concept_id": getattr(args, "concept_id", None),
                                 "replacement": getattr(args, "replacement", None)}

                def run_concept_decision(recorder):
                    def apply(state):
                        if args.concept_action == "define":
                            return concept_ledger.define_concept(
                                state, concept, actor=args.actor_origin, reason=args.reason)
                        if args.concept_action == "deprecate":
                            return concept_ledger.deprecate_concept(
                                state, args.concept_id, actor=args.actor_origin, reason=args.reason,
                                replacement=args.replacement)
                        return concept_ledger.adopt_concept_pack(
                            state, actor=args.actor_origin, reason=args.reason)
                    return concept_wiki.update_concept_state(apply)

                outcome = CatalystGateway(args.workspace).semantic_operation(
                    operation=f"ontology.concept.{args.concept_action}",
                    scope_id=concept_wiki.scope_id,
                    actor_origin=args.actor_origin,
                    input_value=concept_input,
                    action=run_concept_decision,
                    correlation_id=args.correlation_id,
                )
                _emit(outcome)
                return 0 if outcome["status"] == "success" else 1
            if args.ontology_action == "review" and args.review_action == "package":
                from .external_review import write_package
                package_wiki = ProjectWiki(
                    args.workspace, args.wiki_root, enterprise_id=args.enterprise_id,
                    project_id=args.project_id, backend=args.wiki_backend)
                package = write_package(package_wiki, args.candidate_id, args.out, question=args.question)
                _emit({"status": "success", "package": str(args.out),
                       "package_sha256": package["package_sha256"],
                       "candidate_id": package["candidate_id"],
                       "material": package["sources"][0]["relative_path"],
                       "item_count": len(package["items"]),
                       "items": [row["item_key"] for row in package["items"]]})
                return 0
            if args.ontology_action == "source":
                operation = "source.stage"
                input_value = {"file": str(args.file), "project_id": args.project_id}
            elif args.ontology_action == "review" and args.review_action == "submit":
                operation = "review.submit"
                try:
                    review_response_bytes = args.response.read_bytes()
                except OSError as exc:
                    raise ValueError("the review answer could not be read") from exc
                input_value = {
                    "candidate_id": args.candidate_id,
                    "response_sha256": hashlib.sha256(review_response_bytes).hexdigest(),
                    "evaluator_id": args.evaluator_id,
                }
            elif args.ontology_action == "candidate" and args.candidate_action == "propose":
                operation = "candidate.propose"
                input_value = {"file": str(args.file), "project_id": args.project_id}
            elif args.ontology_action == "candidate" and args.candidate_action == "evaluate":
                operation = "candidate.evaluate"
                input_value = {"candidate_id": args.candidate_id, "evaluator_id": args.evaluator_id}
            elif args.ontology_action == "candidate" and args.candidate_action == "decide":
                operation = "candidate.decide"
                input_value = {"candidate_id": args.candidate_id, "decision": args.decision, "reason_code": args.reason_code}
            elif args.ontology_action == "version" and args.version_action == "diff":
                operation = "version.diff"
                input_value = ({"version_id": args.version_id} if args.version_id is not None
                               else {"candidate_id": args.candidate_id})
            elif args.ontology_action == "version" and args.version_action == "activate":
                operation = "version.activate"
                input_value = {"version_id": args.version_id}
                if args.expected_head is not None:
                    input_value["expected_head_version_id"] = None if args.expected_head.casefold() == "none" else args.expected_head
                input_value["branch_switch"] = bool(args.branch_switch)
            elif args.ontology_action == "version" and args.version_action == "rollback":
                operation = "version.rollback"
                input_value = {"version_id": args.version_id}
                if args.expected_head is not None:
                    input_value["expected_head_version_id"] = None if args.expected_head.casefold() == "none" else args.expected_head
            elif args.ontology_action == "query":
                operation = "consumer.query" if args.mode == "accepted_enterprise_semantics" else f"consumer.read.{args.mode}"
                input_value = {"query": args.query, "read_mode": args.mode}
            elif args.ontology_action == "wiki":
                operation = "consumer.wiki"
                input_value = {"query": args.query}
            elif args.ontology_action == "relations":
                operation = "consumer.relations"
                input_value = {"entity": args.entity, "version_id": args.version_id, "limit": args.limit}
            elif args.ontology_action == "graph":
                operation = "consumer.graph"
                input_value = {"version_id": args.version_id, "limit": args.limit}
            elif args.ontology_action == "inspect":
                operation = "semantic.inspect"
                input_value = {"project_id": args.project_id}
            elif args.ontology_action == "external" and args.external_action in {"submit", "submit-v2"}:
                operation = "external.candidate.submit_v2" if args.external_action == "submit-v2" else "external.candidate.submit"
                input_value = {
                    "submission_ref_sha256": hashlib.sha256(
                        str(args.submission.resolve()).encode("utf-8")
                    ).hexdigest()
                }
            elif args.ontology_action == "external" and args.external_action == "read-receipt":
                operation = "external.source_read_receipt"
                input_value = {"source_id": args.source_id, "source_revision": args.source_revision}
            elif args.ontology_action == "understand" and args.understand_action == "submit":
                try:
                    if args.input.stat().st_size > 8 * 1024 * 1024:
                        raise ValueError("Understand handoff input exceeds the 8 MiB local limit")
                    understand_input_bytes = args.input.read_bytes()
                except OSError as exc:
                    raise ValueError("Understand handoff input could not be read") from exc
                if len(understand_input_bytes) > 8 * 1024 * 1024:
                    raise ValueError("Understand handoff input exceeds the 8 MiB local limit")
                input_digest = hashlib.sha256(understand_input_bytes).hexdigest()
                operation = "understand.candidate.submit"
                input_value = {"contract_version": "catalyst.understand_handoff.v1", "input_sha256": input_digest}
            elif args.ontology_action == "understand" and args.understand_action == "graph":
                operation = "understand.graph.candidate"
                input_value = {"candidate_id": args.candidate_id, "limit": args.limit}
            elif args.ontology_action == "understand" and args.understand_action == "active-graph":
                operation = "understand.graph.active"
                input_value = {"limit": args.limit}
            elif args.ontology_action == "understand" and args.understand_action == "items":
                operation = "understand.consumer.items"
                input_value = {"candidate_id": args.candidate_id, "kind": args.kind, "limit": args.limit, "offset": args.offset}
            elif args.ontology_action == "understand" and args.understand_action == "result":
                operation = "understand.consumer.result"
                input_value = {"candidate_id": args.candidate_id}
            elif args.ontology_action == "understand" and args.understand_action == "relations":
                operation = "understand.consumer.relations"
                input_value = {"candidate_id": args.candidate_id, "entity_ref": args.entity_ref}
            elif args.ontology_action == "understand" and args.understand_action == "evidence":
                operation = "understand.evidence.lookup"
                input_value = {"candidate_id": args.candidate_id, "evidence_id": args.evidence_id}
            elif args.ontology_action == "understand" and args.understand_action == "compare":
                operation = "understand.consumer.compare"
                input_value = {"candidate_id": args.candidate_id}
            else:
                raise ValueError("unsupported ontology operation")

            wiki = ProjectWiki(
                args.workspace,
                args.wiki_root,
                enterprise_id=args.enterprise_id,
                project_id=args.project_id,
                backend=args.wiki_backend,
            )
            gateway = CatalystGateway(args.workspace)
            service_holder: dict[str, SemanticWiki] = {}

            def run_semantic(recorder):
                from .semantic_keys import verifier as _key_verifier
                service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=_key_verifier(wiki.workspace))
                service_holder["service"] = service
                actor_origin = args.actor_origin
                if args.ontology_action == "source":
                    return service.stage_source(args.file, actor_origin=actor_origin)
                if args.ontology_action == "review" and args.review_action == "submit":
                    from . import semantic_approval
                    return semantic_approval.approve_external(
                        service, args.candidate_id, package_dir=args.package,
                        response_path=args.response, evaluator_id=args.evaluator_id,
                        evaluator_context=args.evaluator_context, accept=not args.record_only)
                if args.ontology_action == "candidate" and args.candidate_action == "propose":
                    return service.propose(args.file, actor_origin=actor_origin)
                if args.ontology_action == "candidate" and args.candidate_action == "evaluate":
                    return service.evaluate(args.candidate_id, actor_origin=actor_origin, evaluator_id=args.evaluator_id)
                if args.ontology_action == "candidate" and args.candidate_action == "decide":
                    if args.decision == "ACCEPTED" and args.reviewer_report is not None:
                        from . import semantic_approval
                        return semantic_approval.approve(
                            service, args.candidate_id, reviewer_report=args.reviewer_report,
                            disposition=args.reviewer_disposition, reason_code=args.reason_code)
                    return service.decide(args.candidate_id, decision=args.decision, actor_origin=actor_origin, reason_code=args.reason_code)
                if args.ontology_action == "version" and args.version_action == "diff":
                    if args.version_id is not None:
                        return service.accepted_version_diff(args.version_id)
                    return service.diff(args.candidate_id, actor_origin=actor_origin)
                if args.ontology_action == "version" and args.version_action == "activate":
                    if args.sign:
                        from . import semantic_approval
                        head = (None if args.expected_head.casefold() == "none" else args.expected_head
                                ) if args.expected_head is not None else wiki.semantic_state().get("active_version_id")
                        return semantic_approval.activate(service, args.version_id, expected_head=head)
                    activation = {"actor_origin": actor_origin, "allow_branch_switch": bool(args.branch_switch)}
                    if args.expected_head is not None:
                        activation["expected_head_version_id"] = None if args.expected_head.casefold() == "none" else args.expected_head
                    return service.activate(args.version_id, **activation)
                if args.ontology_action == "version" and args.version_action == "rollback":
                    if args.sign:
                        from . import semantic_approval
                        head = (None if args.expected_head.casefold() == "none" else args.expected_head
                                ) if args.expected_head is not None else wiki.semantic_state().get("active_version_id")
                        return semantic_approval.rollback(service, args.version_id, expected_head=head)
                    rollback = {"actor_origin": actor_origin}
                    if args.expected_head is not None:
                        rollback["expected_head_version_id"] = None if args.expected_head.casefold() == "none" else args.expected_head
                    return service.rollback(args.version_id, **rollback)
                if args.ontology_action == "query":
                    return service.read_knowledge(args.query, mode=args.mode, actor_origin=actor_origin)
                if args.ontology_action == "wiki":
                    return service.wiki_projection(args.query, actor_origin=actor_origin)
                if args.ontology_action == "relations":
                    return service.resolve_relations(
                        args.entity, actor_origin=actor_origin, version_id=args.version_id, limit=args.limit,
                    )
                if args.ontology_action == "graph":
                    return service.ontology_graph(
                        actor_origin=actor_origin, version_id=args.version_id, limit=args.limit,
                    )
                if args.ontology_action == "external" and args.external_action == "read-receipt":
                    return service.record_external_source_read(args.source_id, args.source_revision)
                if args.ontology_action == "external" and args.external_action in {"submit", "submit-v2"}:
                    try:
                        if args.submission.stat().st_size > _MAX_EXTERNAL_SUBMISSION_BYTES:
                            service.record_external_submission_error(error_code="submission_too_large")
                            raise SemanticTransitionError(
                                "submission_too_large",
                                "external candidate submission exceeds the local size limit",
                            )
                        with args.submission.open("rb") as stream:
                            raw_submission = stream.read(_MAX_EXTERNAL_SUBMISSION_BYTES + 1)
                    except OSError as exc:
                        service.record_external_submission_error(error_code="submission_unavailable")
                        raise SemanticTransitionError("submission_unavailable", "external submission could not be read") from exc
                    if len(raw_submission) > _MAX_EXTERNAL_SUBMISSION_BYTES:
                        submission_sha256 = hashlib.sha256(raw_submission).hexdigest()
                        service.record_external_submission_error(
                            error_code="submission_too_large",
                            submission_sha256=submission_sha256,
                        )
                        raise SemanticTransitionError(
                            "submission_too_large",
                            "external candidate submission exceeds the local size limit",
                        )
                    submission_sha256 = hashlib.sha256(raw_submission).hexdigest()
                    try:
                        submission = json.loads(raw_submission.decode("utf-8-sig"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        service.record_external_submission_error(
                            error_code="invalid_submission_json",
                            submission_sha256=submission_sha256,
                        )
                        raise SemanticTransitionError("invalid_submission_json", "external submission is not valid UTF-8 JSON") from exc
                    submit = (
                        service.propose_external_submission_v2
                        if args.external_action == "submit-v2"
                        else service.propose_external_submission
                    )
                    return submit(submission, submission_sha256=submission_sha256)
                if args.ontology_action == "understand":
                    if args.understand_action == "submit":
                        if understand_input_bytes is None:
                            raise UnderstandWikiError("understanding_result_unavailable", "Understand result file could not be read")
                        try:
                            frozen_result = json.loads(understand_input_bytes.decode("utf-8-sig"))
                        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                            raise UnderstandWikiError("invalid_understanding_result", "Understand result is not valid UTF-8 JSON") from exc
                        if not isinstance(frozen_result, dict):
                            raise UnderstandWikiError("invalid_understanding_result", "Understand result must be a JSON object")
                        return UnderstandWikiAdapter(wiki, service, args.source_root).submit(
                            frozen_result, declared_scope_id=wiki.scope_id
                        )
                    adapter = UnderstandWikiAdapter(wiki, service, args.wiki_root[0])
                    if args.understand_action == "graph":
                        return adapter.candidate_graph(args.candidate_id, limit=args.limit)
                    if args.understand_action == "active-graph":
                        return adapter.active_graph(limit=args.limit)
                    if args.understand_action == "items":
                        return adapter.items(args.candidate_id, kind=args.kind, limit=args.limit, offset=args.offset)
                    if args.understand_action == "result":
                        return adapter.result(args.candidate_id)
                    if args.understand_action == "relations":
                        return adapter.relations(args.candidate_id, args.entity_ref)
                    if args.understand_action == "evidence":
                        return adapter.evidence(args.candidate_id, args.evidence_id)
                    if args.understand_action == "compare":
                        return adapter.compare_active(args.candidate_id)
                return service.inspect(actor_origin=actor_origin)

            def finalize_semantic(run_id: str, terminal_status: str) -> None:
                service = service_holder.get("service")
                if service is not None:
                    service.finalize_run(run_id, terminal_status)

            outcome = gateway.semantic_operation(
                operation=operation,
                scope_id=wiki.scope_id,
                actor_origin=args.actor_origin,
                input_value=input_value,
                action=run_semantic,
                finalize=finalize_semantic,
                correlation_id=args.correlation_id,
                event_schema_version="1.6" if args.ontology_action == "understand" else None,
            )
            _emit(outcome)
            return 0 if outcome["status"] == "success" else 1

        if args.command == "wiki":
            from .knowledge_intake import SUPPORTED_SOURCE_SUFFIXES, KnowledgeIntakeError, stage_and_scan
            from .wiki_pages import materialize, project, scan_sources

            wiki = ProjectWiki(
                args.workspace,
                args.wiki_root or [args.workspace],
                enterprise_id=args.enterprise_id,
                project_id=args.project_id,
                backend=args.wiki_backend,
            )
            if args.wiki_action == "scan":
                from .knowledge_novelty import assess_novelty, summarize, write_receipt
                from .wiki_mentions import EntityIndex

                if args.source_root is not None and args.file:
                    raise ValueError("choose --file or --source-root, not both")
                selected = [path for path in (args.file or ())]
                # A file this build cannot read is still a file the caller put in the folder:
                # it is reported as refused with its type, never dropped from the answer.
                unsupported: list[dict[str, Any]] = []
                if args.source_root is not None:
                    folder = args.source_root.expanduser().resolve()
                    if not folder.is_dir():
                        raise ValueError("--source-root must be an existing folder")
                    for path in sorted(folder.rglob("*")):
                        if not path.is_file():
                            continue
                        if path.suffix.casefold() not in SUPPORTED_SOURCE_SUFFIXES:
                            unsupported.append({
                                "file": str(path),
                                "status": "refused",
                                "code": "source_type_unsupported",
                                "message": f"unsupported document type {path.suffix or '(no suffix)'}",
                            })
                            continue
                        selected.append(path)
                if not selected:
                    hint = ("; %d file(s) here are of unsupported types" % len(unsupported)) if unsupported else ""
                    raise ValueError("nothing selected: pass --file or a --source-root that holds documents" + hint)
                # Every file is staged before any of them is judged, so an outline can see
                # that its own material is already on the shelf and read whole.
                staged_rows: list[tuple[Path, dict[str, Any] | None, KnowledgeIntakeError | None]] = []
                for path in selected:
                    try:
                        staged_rows.append((path, stage_and_scan(wiki, path), None))
                    except KnowledgeIntakeError as exc:
                        staged_rows.append((path, None, exc))

                index = EntityIndex.build(wiki)
                # A scan answers "what would intake do today", so it re-reads the shelf
                # decision for bytes that never moved — and never offers to pay twice for
                # a revision that already carries a proposal.
                candidates = list((wiki.semantic_state().get("candidates") or {}).values())
                shelf = {
                    str(row.get("relative_path")): str(row.get("content_status") or "NOT_PARSED")
                    for row in wiki.sources()
                    if row.get("status") != "WITHDRAWN"
                }
                rows = list(unsupported)
                verdicts = []
                for path, scanned, error in staged_rows:
                    if scanned is None:
                        rows.append({"file": str(path), "status": "refused",
                                     "code": getattr(error, "code", "intake_failed"),
                                     "message": str(error)})
                        continue
                    extraction = scanned["extraction"]
                    source_id = scanned["source"].get("source_id")
                    name = str(wiki.source_record(source_id).get("relative_path") or "")
                    verdict = assess_novelty(
                        index=index,
                        units=scanned["units"],
                        source_id=source_id,
                        source_revision=scanned["source"].get("revision"),
                        source_name=name,
                        siblings={key: value for key, value in shelf.items() if key != name},
                        revision_changed=scanned["source"].get("status") != "no_op",
                        rejudge=True,
                        already_proposed=any(
                            row.get("source_id") == source_id
                            and row.get("source_revision") == scanned["source"].get("revision")
                            for row in candidates
                        ),
                        dialect_claims=int(scanned["source"].get("claim_count") or 0),
                        truncated=bool(extraction.get("truncated")),
                        unread_locators=max(
                            0,
                            int(extraction.get("locator_count") or 0)
                            - int(extraction.get("unit_count") or 0),
                        ),
                    )
                    receipt = write_receipt(wiki.workspace, verdict)
                    verdicts.append(verdict.to_dict())
                    rows.append({
                        "file": str(path),
                        "status": scanned["source"].get("status"),
                        "source_id": source_id,
                        "revision": scanned["source"].get("revision"),
                        "extraction": extraction.get("status"),
                        "unit_count": scanned["unit_count"],
                        "locator_count": extraction.get("locator_count"),
                        "truncated": bool(extraction.get("truncated")),
                        "part_errors": len(extraction.get("part_errors") or ()),
                        "vision_missing": len(extraction.get("vision_missing") or ()),
                        "tier": verdict.tier,
                        "reason": verdict.reason,
                        "unknown_surfaces": list(verdict.unknown_surfaces[:8]),
                        "prose_density": round(verdict.prose_density, 3),
                        "rule_units": verdict.rule_unit_count,
                        "covered_by": verdict.covered_by,
                        "novelty_receipt": str(receipt),
                    })
                by_extraction: dict[str, int] = {}
                for row in rows:
                    key = str(row.get("extraction") or "refused")
                    by_extraction[key] = by_extraction.get(key, 0) + 1
                outcome = {
                    "status": "success",
                    "scope_id": wiki.scope_id,
                    "model_calls": 0,
                    "files": len(rows),
                    "refused": sum(1 for row in rows if row["status"] == "refused"),
                    "unit_count": sum(int(row.get("unit_count") or 0) for row in rows),
                    "locator_count": sum(int(row.get("locator_count") or 0) for row in rows),
                    "by_extraction": dict(sorted(by_extraction.items())),
                    "novelty": summarize(verdicts),
                    "would_spend": sum(1 for row in verdicts if row.get("spends_money")),
                    "items": rows,
                }
                if args.report_out is not None:
                    args.report_out.parent.mkdir(parents=True, exist_ok=True)
                    args.report_out.write_text(
                        json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    outcome["report_path"] = str(args.report_out)
                _emit(outcome)
                return 0 if outcome["refused"] == 0 else 1

            if args.wiki_action == "verify":
                report = wiki.verify()
                if args.report_out is not None:
                    args.report_out.parent.mkdir(parents=True, exist_ok=True)
                    args.report_out.write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    report = {**report, "report_path": str(args.report_out)}
                _emit(report)
                return 0 if report["status"] in {"OK", "EMPTY"} else 1

            if args.wiki_action == "cold-read":
                from .wiki_cold_read import cold_read

                report = cold_read(
                    workspace=args.workspace,
                    enterprise_id=args.enterprise_id,
                    project_id=args.project_id,
                    roots=args.wiki_root,
                    pages_root=args.root,
                    backend=args.wiki_backend,
                )
                if args.report_out is not None:
                    args.report_out.parent.mkdir(parents=True, exist_ok=True)
                    args.report_out.write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    report = {**report, "report_path": str(args.report_out)}
                _emit(report)
                return 0 if report["status"] in {"OK", "EMPTY"} else 1

            if args.wiki_action == "relocate":
                from .wiki_relocation import relocate

                outcome = relocate(wiki, source_ids=args.source_id, dry_run=args.check)
                outcome.update({"status": "success", "scope_id": wiki.scope_id, "model_calls": 0})
                _emit(outcome)
                return 0

            # The scan runs inside the projection's snapshot window, so a mention cannot
            # come from a store generation the pages were not rendered from.
            pages = project(wiki, root=args.root, scan_store=not args.no_scan)
            outcome = materialize(pages, args.root, dry_run=args.check, identity=pages.identity)
            # A conflict is a publication the tree cannot make without destroying a file the
            # store never wrote; a refused path is one it must not make at all. Neither is a
            # success with a warning attached.
            if outcome["conflicts"]:
                status = "conflict"
            elif outcome["refused"]:
                status = "refused"
            else:
                status = "success"
            outcome.update({
                "status": status,
                "scope_id": wiki.scope_id,
                "identity": pages.identity,
                "model_calls": 0,
                "stats": pages.stats,
                "scanned_sources": pages.stats.get("scanned_sources", []),
            })
            _emit(outcome)
            return 0 if status == "success" else 1

        if args.command == "discover":
            gateway = CatalystGateway(args.workspace)

            def discover_current_capabilities() -> list[dict[str, Any]]:
                app = _app(args)
                _register_file_title(app, lambda _event: None)
                if args.project_id is not None:
                    if not args.query:
                        raise ValueError("--query is required for project Wiki-backed discovery")
                    wiki = getattr(app, "_project_wiki", None) or ProjectWiki(
                        args.workspace,
                        app._enterprise_roots(args.enterprise_id),
                        enterprise_id=args.enterprise_id,
                        project_id=args.project_id,
                        backend=args.wiki_backend,
                    )
                    result = wiki.search(args.query, capabilities=_wiki_catalog_projection(app))
                    discovery_state.update(result)
                    return [
                        {
                            "id": item["capability_id"],
                            "capability_version": item["capability_version"],
                            "name": item["name"],
                            "description": item["meaning"],
                            "execution": {"side_effect": item["side_effect"]},
                        }
                        for item in result["capabilities"]
                    ]
                return [
                    item.to_dict()
                    for item in app.new_session(domain={}, enterprise={}).discover()
                ]

            discovery_state: dict[str, Any] = {}
            discovery = gateway.discover_capabilities(discover_current_capabilities)
            if args.project_id is not None:
                discovery["wiki"] = {
                    "scope_id": f"enterprise:{args.enterprise_id}/project:{args.project_id}",
                    "status": discovery_state.get("status", "UNAVAILABLE" if discovery["status"] != "success" else "UNKNOWN"),
                    "claims": discovery_state.get("claims", []),
                    "capabilities": discovery_state.get("capabilities", []),
                }
            _emit(discovery)
            return 0 if discovery["status"] == "success" else 2

        if args.command == "ask":
            app = _app(args)
            if args.stage_source is not None and args.project_id is None:
                raise ValueError("--stage-source requires --project-id")
            if args.offline_deterministic:
                provider = None
            else:
                try:
                    if args.interactive_provider:
                        if not _secure_interactive_terminal_available():
                            raise ModelProviderConfigurationError(
                                "llm_provider_secure_input_unavailable",
                                "Hidden provider setup requires an interactive terminal. No request was sent.",
                            )
                        provider = configured_model_provider_interactively(
                            provider_id=args.interactive_provider
                        )
                    else:
                        provider = configured_model_provider_from_environment()
                except ModelProviderConfigurationError as exc:
                    provider = UnavailableModelProvider(exc)
            run = _ask_with_app(
                app,
                workspace=args.workspace,
                message=args.message,
                selected_file=args.file,
                provider=provider,
                visible_capabilities=_parse_capability_specs(args.capability),
                domain_id=args.domain_id,
                enterprise_id=args.enterprise_id,
                project_id=args.project_id,
                stage_source=args.stage_source,
                wiki_backend=args.wiki_backend,
                offline_deterministic=args.offline_deterministic,
            )
            _emit(run)
            return 0 if run["status"] == "success" else 1

        if args.command == "component":
            app = CatalystWorkbench(workspace=args.workspace, wiki_roots=[args.workspace])
            gateway = CatalystGateway(args.workspace)
            action = args.component_action
            if action == "discover":
                operation = lambda: app.components.discover(args.source)
            elif action == "admit":
                operation = lambda: app.components.admit(args.source, args.expected_sha256)
            elif action == "activate":
                operation = lambda: app.components.activate(args.component_id, args.version)
            elif action == "deactivate":
                operation = lambda: app.components.deactivate(args.component_id)
            elif action == "list":
                operation = lambda: {"components": app.components.list_components(), "transition": "listed"}
            else:
                raise ValueError("unsupported component lifecycle action")
            try:
                outcome = gateway.component_lifecycle(operation=action, action=operation)
            finally:
                app.components.close_loaded()
            _emit(outcome)
            return 0 if outcome["status"] == "success" else 1

        if args.command == "monitor":
            if not 0 <= args.port <= 65535:
                raise ValueError("--port must be between 0 and 65535")
            workspace = args.workspace.expanduser().resolve()
            from .user_session import LocalUserSession
            user_session = LocalUserSession(workspace, backend=args.wiki_backend, mode=args.mode.upper())
            server = create_monitor_server(workspace, user_session, port=args.port,
                                           input_root=user_session.input_root)
            actual_port = server.server_address[1]
            print(f"Catalyst Run Monitor ({args.mode.upper()}, paid calls disabled) is available at http://127.0.0.1:{actual_port}/", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0

        app = _app(args)
        if args.command == "use":
            domain, enterprise = _context(args)
            run = app.use(
                query=args.query,
                domain=domain,
                enterprise=enterprise,
                output_name=args.output_name,
            )
            _emit(
                {
                    "status": run.result.status,
                    "result_id": run.result.id,
                    "session_id": run.session_id,
                    "artifact_path": run.result.output.get("artifact_path") if isinstance(run.result.output, dict) else None,
                    "trace_path": run.trace_path,
                    "error": run.result.error,
                }
            )
            return 0 if run.result.status == "success" else 1
        if args.command == "acquire-ripgrep":
            receipt = app.acquire_ripgrep()
            _emit(receipt.__dict__)
            return 0
        if args.command == "invoke":
            try:
                parameters = json.loads(args.input_json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"--input-json is invalid JSON: {exc.msg}") from exc
            if not isinstance(parameters, dict):
                raise ValueError("--input-json must contain a JSON object")
            tool_events: list[dict[str, Any]] = []
            gateway = CatalystGateway(args.workspace)
            session = app.new_session(
                domain={"id": args.domain_id},
                enterprise={
                    "id": args.enterprise_id,
                    "allow_local_artifacts": args.allow_local_artifacts,
                    "allow_remote_writes": False,
                },
            )
            def invoke_with_recorder(invocation_id, recorder, trace_id):
                def capture(event):
                    tool_events.append(event)
                    record_file_tool_event(recorder, event)

                _register_file_title(app, capture)
                return session.invoke(
                    args.capability_id,
                    args.version,
                    parameters,
                    invocation_id=invocation_id,
                    recorder=recorder,
                    trace_id=trace_id,
                )

            invocation = gateway.invoke_capability(
                capability_id=args.capability_id,
                capability_version=args.version,
                parameters=parameters,
                invoke=invoke_with_recorder,
                tool_events=tool_events,
            )
            _emit(
                invocation
            )
            return 0 if invocation["status"] == "success" else 1
        if args.command == "evolve-understand":
            benchmark_bytes = args.benchmark.read_bytes()
            benchmark = json.loads(benchmark_bytes.decode("utf-8"))
            if not isinstance(benchmark, list):
                raise ValueError("benchmark file must contain a JSON array")
            gateway = CatalystGateway(args.workspace)
            observed = gateway.workbench_how_operation(
                operation="evolve_understand",
                action=lambda: app.evolve_understand(benchmark=benchmark, activate=args.activate),
                active_before=app.active_understand_implementation(),
                active_reader=app.active_understand_implementation,
                benchmark_sha256=hashlib.sha256(benchmark_bytes).hexdigest(),
                benchmark_case_count=len(benchmark),
                activation_requested=args.activate,
            )
            if observed.get("result") is None:
                _emit({**observed, "error": observed.get("error")})
                return 2
            run = observed["result"]
            _emit({
                "evaluation": run.evaluation.__dict__,
                "candidate_comparison": run.candidate_comparison,
                "active_implementation": run.active_implementation,
                "previous_implementation": run.previous_implementation,
                "report_path": run.report_path,
                "run_id": observed["run_id"],
                "trace_path": observed["trace_path"],
            })
            return 0 if observed["status"] == "success" else 1
        if args.command == "rollback-understand":
            gateway = CatalystGateway(args.workspace)
            observed = gateway.workbench_how_operation(
                operation="rollback_understand",
                action=lambda: app.rollback_understand(args.implementation),
                active_before=app.active_understand_implementation(),
                active_reader=app.active_understand_implementation,
            )
            if observed.get("result") is None:
                _emit({**observed, "error": observed.get("error")})
                return 2
            _emit({
                **observed["result"].__dict__,
                "run_id": observed["run_id"],
                "trace_path": observed["trace_path"],
            })
            return 0
    except (ComponentError, WorkbenchError, TraceStoreError, OTelExportError, OSError, ValueError, json.JSONDecodeError) as exc:
        _emit({"status": "failure", "error": {"type": type(exc).__name__, "message": str(exc)}})
        return 2
    parser.error("unsupported command")
    return 2


def _secure_interactive_terminal_available() -> bool:
    return bool(
        getattr(sys.stdin, "isatty", lambda: False)()
        and getattr(sys.stdout, "isatty", lambda: False)()
    )


if __name__ == "__main__":
    sys.exit(main())
