"""Thin host-authorized binding to the existing Understand proposal path.

No model client, loop, evaluator, store or authority is owned here. The host
admits original file identities; model arguments can only select those IDs.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Callable

from agent_runtime.contracts import CapabilityDescriptor, Success, Failure

from .understand_only import stored_evidence_class


@dataclass(frozen=True)
class AdmittedSource:
    path: Path
    sha256: str
    role: str = 'ORIGINAL_SOURCE'
    locators: tuple[str, ...] | None = None

    def __post_init__(self):
        object.__setattr__(self, 'path', Path(self.path).resolve())
        if self.locators is not None:
            object.__setattr__(self, 'locators', tuple(self.locators))


@dataclass(frozen=True)
class SemanticProposalContext:
    source_root: Path
    sources: Mapping[str, AdmittedSource]
    semantic: Any
    provider: Any
    actor_context: Mapping[str, Any]
    harvest: Callable
    capture: Any = None  # Trusted per-request product state; never a tool argument.
    revision: Mapping[str, Any] | None = None  # Findings from a refused answer, for one bounded repair.
    verifier_provider: Any = None  # A separate model that reads the candidate in its own context.

    def __post_init__(self):
        object.__setattr__(self, 'source_root', Path(self.source_root).resolve())
        object.__setattr__(self, 'sources', MappingProxyType(dict(self.sources)))
        actor = json.loads(json.dumps(dict(self.actor_context)))
        # Tuple values prevent mutation through a retained host list.
        actor = {k: tuple(v) if isinstance(v, list) else v for k, v in actor.items()}
        object.__setattr__(self, 'actor_context', MappingProxyType(actor))

    def validate(self, session, recorder, provider):
        from .llm_provider import ObservedModelProvider
        if self.capture is not None:
            from .semantic_capture import _CaptureBoundary
            if not isinstance(self.capture, _CaptureBoundary):
                raise ValueError("invalid product capture context")
        if getattr(provider, 'mode', None) != 'offline' and (
                not isinstance(provider, ObservedModelProvider) or not provider.budget_snapshot):
            raise ValueError('Live proposal calls require the existing governed P0 ModelTask provider')
        actor, wiki = self.actor_context, self.semantic.wiki
        if (actor.get('verified') is not True or actor.get('simulation') is not True
                or 'knowledge.propose' not in actor.get('permissions', ())
                or wiki.scope_id not in actor.get('readable_scope_ids', ())):
            raise ValueError('trusted TEST-SCOPE proposal permission and exact scope required')
        if (wiki.workspace != session.app.workspace or wiki.enterprise_id != session.enterprise.get('id')
                or self.semantic.recorder is not recorder or recorder is None):
            raise ValueError('proposal must share this Harness workspace, enterprise and Run recorder')
        if self.provider is not provider:
            raise ValueError('Agent and extraction must share the host Provider and budget ledger')
        if not any(self.source_root == r or self.source_root.is_relative_to(r) for r in session.app.wiki_roots):
            raise ValueError('source root outside Harness roots')
        allowed = session.app._enterprise_roots(session.enterprise.get('id'))
        if not self.sources or len(self.sources) > 16 or not callable(self.harvest):
            raise ValueError('bounded host source manifest and harvest function required')
        for key, source in self.sources.items():
            if not isinstance(key, str) or not key or len(key) > 128 or not isinstance(source, AdmittedSource):
                raise ValueError('invalid host source identity')
            path = Path(source.path).resolve(strict=True)
            if source.role != 'ORIGINAL_SOURCE' or not path.is_file() or not path.is_relative_to(self.source_root):
                raise ValueError('only explicitly admitted original sources may enter Understand')
            if not any(path == r or path.is_relative_to(r) for r in allowed):
                raise ValueError('source outside Enterprise allowlist')
            if hashlib.sha256(path.read_bytes()).hexdigest() != source.sha256:
                raise ValueError('source identity changed after host admission')


class UnderstandCapabilityAdapter:
    """Model-visible schema; all executable dependencies are request-scoped Host state."""
    def describe(self):
        return CapabilityDescriptor(id='understand', name='Propose enterprise semantic candidates',
            description='Understand enterprise semantics from host-admitted source IDs; return evidence-bound candidates for independent review, never approve or activate them.',
            input_schema={'type': 'object', 'properties': {'source_ids': {'type': 'array', 'items': {'type': 'string'}}},
                          'required': ['source_ids'], 'additionalProperties': False}, output_schema={'type': 'object'})

    def invoke(self, parameters, context):
        execute = getattr(context, 'plugin_services', {}).get('understand.execute')
        if not callable(execute):
            return Failure('understand_host_authorization_missing')
        try:
            context.raise_if_cancelled()
            result = execute(parameters['source_ids'])
            context.raise_if_cancelled()
            return Success(result)
        except Exception as exc:
            # No arbitrary exception string: it may contain source text or secrets.
            # A contract violation names a rule slug and model-chosen item keys instead,
            # which is exactly what a bounded revision needs and contains no source text.
            keys = [key for key in getattr(exc, 'item_keys', ()) if isinstance(key, str)][:8]
            detail = ':' + str(exc.rule) if getattr(exc, 'rule', None) else ''
            if keys:
                detail += ' items=' + ','.join(keys)
            elif getattr(exc, 'received', None) is not None and getattr(exc, 'limit', None) is not None:
                # A refused whole answer is actionable only with both numbers.
                detail += f' items={exc.received} limit={exc.limit}'
                if getattr(exc, 'segment', None):
                    detail += ' segment=' + str(exc.segment)
            return Failure('understand_proposal_failed:' + str(getattr(exc, 'public_code', type(exc).__name__)) + detail)


def candidate_summary(output):
    raw = output['understanding']
    items = raw['semantic_candidate']['items']
    preview = [{k: row[k] for k in ('item_id', 'kind', 'key', 'meaning', 'evidence_class', 'evidence_refs', 'uncertainty', 'subject', 'predicate', 'object') if k in row}
               for row in items]
    for row in preview:
        # The candidate view states the class storage will carry, not just the one the
        # producer declared: harvest stores a model meaning as inferred.
        row['stored_evidence_class'] = stored_evidence_class(row.get('kind'))
    result = dict(status='EVALUATION_PENDING', authority='CANDIDATE_ONLY',
                  owner_status='OWNER_REVIEW_PENDING', candidate_id=output['proposal']['candidate_id'],
                  version_id=None, preview=preview, evidence_ids=[r['evidence_id'] for r in raw['evidence_refs']],
                  selected_item_ids=output['selected_item_ids'], omitted_item_ids=output['omitted_item_ids'])
    # A relation dropped for its own rule is not silent: the count and the keys travel
    # with the candidate so the run receipt can show what the answer lost.
    attribution = raw.get('producer_attribution') or {}
    if attribution.get('dropped_relation_count'):
        result.update(dropped_relation_count=attribution['dropped_relation_count'],
                      dropped_relations=attribution.get('dropped_relations', []))
    # A refused extraction unit is not silent either: the page the answer lost and the
    # reason travel with the candidate, so partial coverage is visible before harvest.
    if attribution.get('refused_units'):
        result.update(refused_units=attribution['refused_units'])
    if len(json.dumps(result, ensure_ascii=False).encode('utf-8')) > 64 * 1024:
        # Persisted proposal is intact; the model-facing preview reports its bound.
        result.pop('preview')
        result.update(preview_status='BOUNDED_METADATA_ONLY', item_count=len(items))
    return result
