"""Internal method assembly seam; admission and Runtime authority stay in Harness.

The two adapters prepare prompt context and request-scoped tool dependencies only.
They do not activate bindings, change policy, accept candidates or run a loop.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from .semantic_tool import SemanticProposalContext, candidate_summary
from .project_understand import ProjectAnalysisContext, EXACT_ACTIONS


@dataclass(frozen=True)
class _PreparedMethod:
    prompt_suffix: str = ""
    plugin_services: dict = None
    native_batch: bool = False

    def __post_init__(self):
        if self.plugin_services is None:
            object.__setattr__(self, "plugin_services", {})


class _ProjectMethodAdapter:
    @staticmethod
    def prepare(session, recorder, provider, context):
        return _PreparedMethod("\n" + context.initial_context(), {"project.analysis": context}, True)


class _SemanticMethodAdapter:
    @staticmethod
    def prepare(session, recorder, provider, proposal_context):
        def authorize():
            proposal_context.validate(session, recorder, provider)
        def execute(source_ids):
            authorize()
            if (not isinstance(source_ids, list) or not source_ids or len(source_ids) != len(set(source_ids))
                    or any(key not in proposal_context.sources for key in source_ids)):
                raise ValueError("source IDs must be an explicit subset of the admitted original manifest")
            output = session.propose_enterprise_semantics(
                "请理解企业资料并形成组织语义 Ontology 候选。",
                source_refs=[proposal_context.sources[key].path for key in source_ids],
                source_root=proposal_context.source_root, semantic=proposal_context.semantic,
                provider=provider, actor_context=proposal_context.actor_context, harvest=proposal_context.harvest,
                source_evidence_scope={Path(proposal_context.sources[key].path).resolve().relative_to(proposal_context.source_root).as_posix():
                    proposal_context.sources[key].locators for key in source_ids},
                _capture=proposal_context.capture, revision=proposal_context.revision,
                verifier_provider=proposal_context.verifier_provider)
            return output if proposal_context.capture is not None else candidate_summary(output)
        return _PreparedMethod(
            "\nHost-admitted original source IDs: " + json.dumps(list(proposal_context.sources), ensure_ascii=False),
            {"understand.execute": execute})


def prepare_method(session, recorder, provider, allowed, proposal_context, project_context, capture):
    """Assemble admitted context using the original typed input contracts.

    Harness must still validate context, activate/check bindings and enforce policy
    before calling this function. These guards also fail closed for direct use.
    """
    if project_context is not None:
        if not isinstance(project_context, ProjectAnalysisContext) or allowed != EXACT_ACTIONS or proposal_context is not None or capture is not None:
            raise ValueError("project context requires only the exact project action profile")
        return _ProjectMethodAdapter.prepare(session, recorder, provider, project_context)
    if any(name in {x[0] for x in EXACT_ACTIONS} for name, _version in allowed):
        raise ValueError("project Host context is required")
    if ("understand", "1.0.0") in allowed:
        if not isinstance(proposal_context, SemanticProposalContext):
            raise ValueError("Host SemanticProposalContext is required")
        return _SemanticMethodAdapter.prepare(session, recorder, provider, proposal_context)
    return _PreparedMethod()


def validate_capture_context(session, recorder, provider, allowed, proposal_context):
    """Keep semantic capture admission with its typed method contract."""
    semantic = ("understand", "1.0.0") in allowed
    if semantic:
        if allowed != (("understand", "1.0.0"),) or not isinstance(proposal_context, SemanticProposalContext):
            raise ValueError("semantic capture requires only Understand and its admitted context")
        if proposal_context.capture is not None:
            raise ValueError("capture context already bound")
        proposal_context.validate(session, recorder, provider)
    elif proposal_context is not None:
        raise ValueError("proposal context is only applicable to Understand")
    return semantic
