"""Source-controlled plugin definitions for the local Catalyst Harness."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from agent_runtime.contracts import CapabilityDescriptor as RuntimeCapabilityDescriptor
from agent_runtime.contracts import Failure, Success

from .plugin_composition import PluginComposer, PluginContext, PluginDefinition, PluginEffect
from .understand_only import UnderstandPort
from .semantic_tool import UnderstandCapabilityAdapter
from .wiki import reads_as_pending


PLUGIN_PROFILE = "default"
EVO_WIKI_PLUGIN_ID = "evo-wiki"
UNDERSTAND_PLUGIN_ID = "understand"
PLUGIN_VERSION = "0.1.0"


def _object_schema(properties: Mapping[str, Any], required: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }


class WikiAssetQueryCapability:
    """Read only product asset descriptions; never enterprise documents or code."""
    id='wiki_assets'
    def __init__(self,assets):self.assets=assets
    def describe(self):
        return RuntimeCapabilityDescriptor(id=self.id,name='Wiki product asset inventory',
          description='查询 Catalyst Wiki 的产品资产与已声明接口依赖。只读元数据，不读取企业原文，不授予执行权限。',
          input_schema=_object_schema({'query':{'type':'string'}},('query',)),
          output_schema={'type':'object'})
    def invoke(self,parameters,context):
        try:return Success(self.assets.query_summary(parameters.get('query')))
        except (ValueError,OSError):return Failure('asset_inventory_unavailable')


class EvoWikiSearchCapability:
    """The existing ``wiki_search@1.0.0`` contract owned by the Evo Wiki plugin."""

    def __init__(self, search: Callable[[str, str | None], dict[str, Any]]) -> None:
        self._search = search

    def describe(self) -> RuntimeCapabilityDescriptor:
        return RuntimeCapabilityDescriptor(
            id="wiki_search",
            name="Source-backed Wiki search",
            description="Resolve sourced Wiki entries to exact local source locators.",
            input_schema=_object_schema({"query": {"type": "string"}}, ("query",)),
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        query = parameters.get("query")
        if not isinstance(query, str) or not query.strip():
            return Failure("query must be a non-empty string")
        enterprise = getattr(context, "enterprise_context", {})
        enterprise_id = enterprise.get("id") if isinstance(enterprise, Mapping) else None
        try:
            result = self._search(query, enterprise_id)
            if result.get("status") == "UNAVAILABLE":
                return Failure("wiki_unavailable")
            self._attach_scoped_project_knowledge(result, query, context, enterprise_id)
            return Success(result)
        except (OSError, ValueError, RuntimeError) as exc:
            return Failure(f"Wiki source resolution failed: {type(exc).__name__}: {exc}")

    @staticmethod
    def _attach_scoped_project_knowledge(
        result: dict[str, Any],
        query: str,
        context: Any,
        enterprise_id: str | None,
    ) -> None:
        services = getattr(context, "plugin_services", {})
        semantic_wiki = services.get("semantic_wiki") if isinstance(services, Mapping) else None
        wiki = getattr(semantic_wiki, "wiki", None)
        if semantic_wiki is None or wiki is None:
            return
        trusted_project_wiki = services.get("project_wiki") if isinstance(services, Mapping) else None
        if (
            not isinstance(enterprise_id, str)
            or trusted_project_wiki is not wiki
            or getattr(wiki, "enterprise_id", None) != enterprise_id
        ):
            result["project_knowledge"] = {
                "status": "DENIED",
                "error_code": "wiki_scope_mismatch",
            }
            return
        try:
            accepted = semantic_wiki.read_knowledge(
                query,
                mode="accepted_enterprise_semantics",
                actor_origin="catalyst_deterministic",
            )
            # What the read saved for review is handed on as review: a pending row goes to
            # its own place, never into the list a consumer reads as the material's facts.
            rows = list(accepted.get("meanings") or ())
            facts = [row for row in rows if not reads_as_pending(row)]
            accepted = {
                **accepted,
                "meanings": facts,
                "meaning_ids": [row["meaning_id"] for row in facts],
                "meaning_count": len(facts),
            }
            result["project_knowledge"] = {
                "source_claims": semantic_wiki.read_knowledge(
                    query,
                    mode="grounded_claims",
                    actor_origin="catalyst_deterministic",
                ),
                "accepted_semantics": accepted,
                "pending_review": [row for row in rows if reads_as_pending(row)],
            }
        except (OSError, ValueError, RuntimeError) as exc:
            result["project_knowledge"] = {
                "status": "UNAVAILABLE",
                "error_code": type(exc).__name__,
            }


class ObservedUnderstandPort:
    """Attribute calls to the installed Understand plugin and reuse UnderstandPort."""

    def __init__(self, port: UnderstandPort | None = None, *, project_catalog=None) -> None:
        self._port = port or UnderstandPort()
        self._project_catalog = project_catalog

    def ensure_project_actions(self):
        """Opt-in registration owned/revoked by this same Understand plugin."""
        catalog=self._project_catalog
        if catalog is None:raise ValueError("project_catalog_not_bound")
        from .project_understand import ACTIONS, ProjectAnalysisCapability
        for action in ACTIONS:
            registered=catalog.by_internal_key(catalog.internal_key(action,"1.0.0"))
            if registered is not None:
                if type(registered.implementation) is not ProjectAnalysisCapability or registered.implementation.action!=action:
                    raise ValueError("project_action_collision")
                continue
            catalog.register(ProjectAnalysisCapability(action), capability_version="1.0.0",
                execution={"side_effect":"none"}, activate=False, metadata={
                    "model_policy":{"mode":"workspace_scoped_query","max_calls":4 if action!="project_submit_analysis" else 1},
                    "llm_visibility":"explicit", "component_id":UNDERSTAND_PLUGIN_ID,"component_version":PLUGIN_VERSION})

    def expand_evidence(self, source_inventory, existing_evidence_refs, request, *, source_root, recorder=None):
        return self._port.expand_evidence(source_inventory,existing_evidence_refs,request,source_root=source_root,recorder=recorder)

    def understand(self, request, *, source_root, recorder=None, semantic_provider=None,
                   verifier_provider=None, source_evidence_scope=None, concepts=None,
                   identity_decisions=None):
        span_id = None
        if recorder is not None:
            span_id = recorder.start_span(
                "plugin.understand.analyze",
                kind="CHAIN",
                attributes={
                    "component_id": UNDERSTAND_PLUGIN_ID,
                    "component_version": PLUGIN_VERSION,
                },
                component_id=UNDERSTAND_PLUGIN_ID,
                component_version=PLUGIN_VERSION,
            )
        try:
            result = self._port.understand(
                request,
                source_root=source_root,
                recorder=recorder,
                **({"semantic_provider": semantic_provider} if semantic_provider is not None else {}),
                **({"verifier_provider": verifier_provider} if verifier_provider is not None else {}),
                **({"source_evidence_scope": source_evidence_scope} if source_evidence_scope is not None else {}),
                **({"concepts": concepts} if concepts is not None else {}),
                **({"identity_decisions": identity_decisions} if identity_decisions is not None else {}),
            )
        except Exception:
            if recorder is not None and span_id is not None:
                recorder.end_span(
                    span_id,
                    status="failure",
                    attributes={"component_id": UNDERSTAND_PLUGIN_ID},
                )
            raise
        if recorder is not None and span_id is not None:
            recorder.end_span(
                span_id,
                status="success" if result.status == "COMPLETE" else "partial",
                attributes={
                    "component_id": UNDERSTAND_PLUGIN_ID,
                    "component_version": PLUGIN_VERSION,
                    "result_type": result.result_type,
                    "result_status": result.status,
                },
            )
        return result


def _apply_evo_wiki(context: PluginContext) -> PluginEffect:
    catalog = context.require("capability.catalog")
    search = context.require("wiki.source_search")
    capability = EvoWikiSearchCapability(search)
    catalog.register(
        capability,
        capability_version="1.0.0",
        execution={"side_effect": "none"},
        metadata={
            "implementation": "catalyst-evo-wiki-plugin-v0.1",
            "model_policy": {"mode": "workspace_scoped_query", "max_calls": 1},
            "llm_visibility": "explicit",
            "component_id": EVO_WIKI_PLUGIN_ID,
            "component_version": PLUGIN_VERSION,
        },
    )
    return PluginEffect(
        services={"evo_wiki.search_tool": capability},
        revoke=lambda: catalog.deactivate("wiki_search", "1.0.0"),
    )


def _apply_understand(context: PluginContext, *, skill_root=None, extraction_mode="single_stage") -> PluginEffect:
    catalog = context.require("capability.catalog")
    catalog.register(UnderstandCapabilityAdapter(), capability_version="1.0.0",
        execution={"side_effect": "possible"}, activate=False, metadata={
            "model_policy": {"mode": "controlled_proposal", "max_calls": 1},
            "llm_visibility": "explicit", "component_id": UNDERSTAND_PLUGIN_ID,
            "component_version": PLUGIN_VERSION,
        })
    from .project_understand import ACTIONS
    def revoke():
        catalog.deactivate("understand", "1.0.0")
        for action in ACTIONS:
            if catalog.by_internal_key(catalog.internal_key(action,"1.0.0")) is not None:catalog.deactivate(action,"1.0.0")
    return PluginEffect(services={"understand.port": ObservedUnderstandPort(UnderstandPort(skill_root=skill_root, extraction_mode=extraction_mode), project_catalog=catalog)}, revoke=revoke)


def create_harness_plugin_composer(
    *,
    capability_catalog: Any,
    wiki_source_search: Callable[[str, str | None], dict[str, Any]],
    understand_skill_root=None,
    understand_extraction_mode="single_stage",
    chat_context_plugin=None,
) -> PluginComposer:
    """Create the one source-controlled plugin profile supported by this Harness."""

    definitions = (
        PluginDefinition(
            plugin_id=EVO_WIKI_PLUGIN_ID,
            version=PLUGIN_VERSION,
            provides=("evo_wiki.search_tool",),
            requires=("capability.catalog", "wiki.source_search"),
            apply=_apply_evo_wiki,
        ),
        PluginDefinition(
            plugin_id=UNDERSTAND_PLUGIN_ID,
            version=PLUGIN_VERSION,
            provides=("understand.port",),
            requires=("capability.catalog",),
            apply=lambda context: _apply_understand(context, skill_root=understand_skill_root, extraction_mode=understand_extraction_mode),
        ),
    )
    if chat_context_plugin is not None:
        definitions += (chat_context_plugin,)
    return PluginComposer(
        definitions=definitions,
        profiles={PLUGIN_PROFILE: tuple(plugin.plugin_id for plugin in definitions)},
        host_services={
            "capability.catalog": capability_catalog,
            "wiki.source_search": wiki_source_search,
        },
    )
