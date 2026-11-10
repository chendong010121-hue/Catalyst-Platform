"""Bounded experimental contract consumer, NOT a production composition engine.

Only synthetic, independently bound source references are supported. Does not
extract business truth, approve semantics, install packages or schedule Agents.
"""
from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from agent_runtime.contracts import CapabilityDescriptor, Failure, Success
from catalyst_platform.plugin_composition import PluginComposer, PluginDefinition, PluginEffect


class ContractRefused(ValueError):
    pass


REFERENCE_FIELDS = ('scope_id', 'source_id', 'source_revision', 'object_type', 'object_id', 'evidence_class', 'locator', 'span_sha256')
REFERENCE_SCHEMA = {'type': 'object', 'properties': {key: {'type': 'string'} for key in REFERENCE_FIELDS},
                    'required': list(REFERENCE_FIELDS), 'additionalProperties': False}


def bind_receipt_reference(upstream, expected):
    """One explicit field mapping against an independently supplied TEST expectation.

    Callers cannot insert expected constraints through an upstream payload.
    Matching proves only this fixture's declared identity, not business entailment.
    """
    if not isinstance(upstream, Mapping) or 'source_ref' not in upstream or set(upstream) - {'source_ref', 'query'}:
        raise ContractRefused('UPSTREAM_SHAPE')
    ref = upstream['source_ref']
    for value in (ref, expected):
        if not isinstance(value, Mapping) or set(value) != set(REFERENCE_FIELDS) or any(
                not isinstance(value[key], str) or not value[key] for key in REFERENCE_FIELDS):
            raise ContractRefused('REFERENCE_SHAPE')
    if ref['evidence_class'] != 'SOURCE_EXPLICIT' or expected['evidence_class'] != 'SOURCE_EXPLICIT':
        raise ContractRefused('REVIEW_REQUIRED')
    for field, code in (('scope_id', 'SCOPE_MISMATCH'), ('source_id', 'SOURCE_MISMATCH'),
                        ('source_revision', 'REVISION_MISMATCH'), ('object_type', 'OBJECT_TYPE_MISMATCH'),
                        ('object_id', 'OBJECT_ID_MISMATCH'), ('locator', 'LOCATOR_MISMATCH'),
                        ('span_sha256', 'SPAN_HASH_MISMATCH')):
        if ref[field] != expected[field]:
            raise ContractRefused(code)
    if ref['object_type'] != 'payment_receipt':
        raise ContractRefused('OBJECT_TYPE_MISMATCH')
    return {'receipt_ref': deepcopy(dict(ref))}


@dataclass(frozen=True)
class WikiServiceBinding:
    """Test-only typed service profile: identity separate from implementation."""
    implementation: object
    interface_version: str = '1'

    def validate_for_consumer(self):
        if self.interface_version != '1':
            raise ContractRefused('SERVICE_CONTRACT_VERSION')
        if (not all(callable(getattr(self.implementation, name, None)) for name in ('search', 'source_snapshot'))
                or not all(isinstance(getattr(self.implementation, name, None), str)
                           and getattr(self.implementation, name) for name in ('scope_id', 'enterprise_id'))):
            raise ContractRefused('SERVICE_INTERFACE_MISSING')
        return self.implementation


class _SourceAction:
    """Two concrete action adapters over existing Wiki/Capability interfaces."""
    def __init__(self, wiki, expectation, stage):
        self.wiki, self.expectation, self.stage = wiki, deepcopy(expectation), stage
        self.calls = 0
        self.closed = False

    @property
    def id(self):
        return 'pilot_reference_lookup' if self.stage == 'lookup' else 'pilot_evidence_read'

    def describe(self):
        name = 'query' if self.stage == 'lookup' else 'receipt_ref'
        schema = {'type': 'string'} if name == 'query' else REFERENCE_SCHEMA
        output_fields = ({'source_ref': REFERENCE_SCHEMA} if self.stage == 'lookup' else {
            'source_id': {'type': 'string'}, 'source_revision': {'type': 'string'},
            'content': {'type': 'string'}, 'authority': {'type': 'string'},
            'business_quality': {'type': 'string'}, 'evidence_ref': REFERENCE_SCHEMA})
        return CapabilityDescriptor(id=self.id, name=self.id,
            description='Synthetic TEST-only source-reference composition proof; no business authority.',
            input_schema={'type': 'object', 'properties': {name: schema}, 'required': [name], 'additionalProperties': False},
            output_schema={'type': 'object', 'properties': output_fields,
                           'required': list(output_fields), 'additionalProperties': False})

    def close(self):
        self.closed = True

    def invoke(self, parameters, context):
        self.calls += 1
        if self.closed:
            return Failure('ACTION_CLOSED')
        if context.enterprise_context.get('id') != self.wiki.enterprise_id:
            return Failure('SCOPE_MISMATCH')
        try:
            if self.stage == 'lookup':
                found = self.wiki.search(parameters['query'])
                if (found['status'] != 'FOUND' or found['source_id'] != self.expectation['source_id']
                        or found['source_revision'] != self.expectation['source_revision']):
                    raise ContractRefused('SOURCE_NOT_MATCHED')
                return Success({'source_ref': deepcopy(self.expectation)})
            # Consumer rechecks identity; bypassing the explicit mapper cannot bypass this check.
            ref = bind_receipt_reference({'source_ref': parameters['receipt_ref']}, self.expectation)['receipt_ref']
            snap = self.wiki.source_snapshot(ref['source_id'])
            if snap['current_revision'] != ref['source_revision']:
                raise ContractRefused('SOURCE_CHANGED')
            match = re.fullmatch(r'line:([1-9][0-9]*)', ref['locator'])
            lines = snap['content'].splitlines()
            if (not match or int(match.group(1)) > len(lines)
                    or hashlib.sha256(lines[int(match.group(1))-1].encode('utf-8')).hexdigest() != ref['span_sha256']):
                raise ContractRefused('SOURCE_SPAN_MISMATCH')
            return Success({'source_id': ref['source_id'], 'source_revision': ref['source_revision'],
                            'content': snap['content'], 'authority': 'SYNTHETIC_SOURCE_ONLY',
                            'business_quality': 'NOT_EVALUATED', 'evidence_ref': deepcopy(ref)})
        except (ValueError, OSError) as exc:
            return Failure(str(exc))


def compose_pilot(app, service, expectation):
    """Use original PluginComposer/Catalog; no second registry, runtime or scheduler.

    The service supplies a read contract, not invoke(). Only action adapters are
    model-callable. Everything here lives outside the production entry paths.
    """
    wiki = service.validate_for_consumer()
    if expectation.get('scope_id') != wiki.scope_id:
        raise ContractRefused('SERVICE_SCOPE_MISMATCH')
    tools = []
    releases = []

    def provide(_context):
        return PluginEffect(services={'pilot.wiki.read': service}, revoke=lambda: releases.append('service'))

    def actions(context):
        store = context.require('pilot.wiki.read').validate_for_consumer()
        catalog = context.require('pilot.catalog')
        try:
            for stage in ('lookup', 'read'):
                tool = _SourceAction(store, expectation, stage)
                app.register_capability(tool.describe(), capability_version='1.0.0', execution={'side_effect': 'none'},
                    implementation=tool, metadata={'component_id': 'composition-contract-test', 'component_version': '0.1.0',
                        'llm_visibility': 'explicit', 'model_policy': {'mode': 'workspace_scoped_query', 'max_calls': 1}})
                tools.append(tool)
        except BaseException:
            # compose cannot revoke an effect that apply has not yet returned.
            # Retire only this attempt's successfully registered implementations.
            for tool in reversed(tools):
                catalog.deactivate(tool.id, '1.0.0')
            raise
        def revoke():
            for tool in reversed(tools):
                catalog.deactivate(tool.id, '1.0.0')
            releases.append('actions')
        return PluginEffect(services={'pilot.source.actions': tuple(tools)}, revoke=revoke)

    definitions = (
        PluginDefinition('pilot-wiki', '0.1.0', ('pilot.wiki.read',), (), provide),
        PluginDefinition('pilot-actions', '0.1.0', ('pilot.source.actions',), ('pilot.wiki.read', 'pilot.catalog'), actions))
    composer = PluginComposer(definitions=definitions, profiles={'test': ('pilot-actions', 'pilot-wiki')},
                              host_services={'pilot.catalog': app._catalog})
    composer.compose('test')
    return composer, tools, releases
