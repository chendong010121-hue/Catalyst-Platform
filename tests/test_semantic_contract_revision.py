"""A refused model answer must name its defects, and one bounded revision must repair them.

The three defects reproduced here are the ones the first live run produced: an
UNKNOWN item without uncertainty, and an item citing an evidence ID that was
never supplied. The last test proves the defect travels to the model (the only
actor that can repair it) as a rule slug and item keys, never as source text.
"""
from types import SimpleNamespace

import json
import pytest

from agent_runtime.contracts import Failure, ModelResponse
from catalyst_platform.semantic_tool import UnderstandCapabilityAdapter
from catalyst_platform.understand_only import (
    SemanticContractError,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

ORG_TEXT = '市场部负责客户线索。\n审批流程未在本页说明。'


class ContractFixtureProvider:
    """Deterministic protocol fixture; it answers, it never judges semantic quality."""

    model = 'contract-fixture'

    def __init__(self, items):
        self.build = items
        self.calls = 0
        self.system_prompts = []

    def request(self, request):
        self.calls += 1
        self.system_prompts.append(request.messages[0].content)
        evidence = json.loads(request.messages[-1].content)['evidence']
        return ModelResponse(
            content=json.dumps({'items': self.build(evidence, self.calls)}, ensure_ascii=False),
            finish_reason='stop',
        )


def _entity(evidence, key='marketing'):
    return {'kind': 'entity', 'key': key, 'meaning': '市场部',
            'evidence_class': 'SOURCE_DIRECT', 'evidence_refs': [evidence[0]['evidence_id']]}


def _unknown(**overrides):
    item = {'kind': 'unknown', 'key': 'approval_status', 'meaning': '审批状态未在本页说明',
            'evidence_class': 'UNKNOWN', 'evidence_refs': []}
    item.update(overrides)
    return item


def _propose(tmp_path, provider, *, revision=None, request_id='contract-request'):
    source = tmp_path / 'org.txt'
    source.write_text(ORG_TEXT, encoding='utf-8')
    return UnderstandPort().understand(
        UnderstandingRequest(request_id, '形成企业本体', source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, revision=revision),
        source_root=tmp_path, semantic_provider=provider,
    )


def test_unknown_without_uncertainty_is_dropped_and_counted_by_rule(tmp_path):
    provider = ContractFixtureProvider(lambda evidence, call: [_entity(evidence), _unknown()])
    result = _propose(tmp_path, provider)
    # The row breaks its own contract; the card still answers, and the row is named.
    assert result.producer_attribution['dropped_invalid_items'] == {'uncertainty_required': 1}
    drops = result.producer_attribution['dropped_invalid_item_keys']
    assert [row['item_key'] for row in drops] == ['approval_status']
    # The row is gone; the harness's own reader unknowns are not this row.
    assert 'approval_status' not in {item.key for item in result.semantic_candidate.items}
    assert 'marketing' in {item.key for item in result.semantic_candidate.items}
    # The count is data the caller can act on, and it carries no source text.
    assert '市场部' not in str(drops) and '审批流程' not in str(drops)


def test_an_absence_statement_stands_in_for_the_missing_uncertainty(tmp_path):
    def build(evidence, call):
        return [_entity(evidence),
                _unknown(scope_refs=[evidence[0]['evidence_id']],
                         observed_absence='本页只写职责，没有写审批权限')]

    result = _propose(tmp_path, ContractFixtureProvider(build))
    [unknown] = [item for item in result.semantic_candidate.items
                 if item.kind == 'unknown' and item.key == 'approval_status']
    # The absence text is copied verbatim into the uncertainty slot, not paraphrased.
    assert unknown.uncertainty == '本页只写职责，没有写审批权限'
    assert result.producer_attribution['uncertainty_from_absence'] == 1


def test_a_field_the_contract_does_not_define_is_dropped_and_named(tmp_path):
    def build(evidence, call):
        return [_entity(evidence),
                _unknown(evidence_class_note=None,
                         uncertainty='本页没有写审批权限')]

    result = _propose(tmp_path, ContractFixtureProvider(build))
    # The row declares no scope and no gap, so what is left is a question about this run:
    # it is kept whole in run evidence rather than on the card.
    [unknown] = [item for item in result.run_diagnostics
                 if item['key'] == 'approval_status']
    assert result.run_diagnostics
    assert all(item['reason'] for item in result.run_diagnostics)
    # The undefined field is gone from the row, and the receipt says which one went.
    assert 'evidence_class_note' not in unknown
    assert result.producer_attribution['dropped_item_fields'] == {'evidence_class_note': 1}
    assert result.producer_attribution['dropped_field_items'] == [
        {'item_key': 'approval_status', 'fields': ['evidence_class_note']}]


def test_an_unknown_without_an_evidence_refs_key_is_accepted_and_counted(tmp_path):
    def build(evidence, call):
        absence = _unknown(scope_refs=[evidence[0]['evidence_id']],
                           observed_absence='本页没有写审批权限')
        absence.pop('evidence_refs')
        return [_entity(evidence), absence]

    result = _propose(tmp_path, ContractFixtureProvider(build))
    [unknown] = [item for item in result.semantic_candidate.items
                 if item.kind == 'unknown' and item.key == 'approval_status']
    # The absence cites the rows it searched; it owns no evidence row of its own.
    assert unknown.evidence_refs == ()
    assert result.producer_attribution['evidence_refs_empty'] == 1


def test_evidence_ref_never_supplied_drops_the_row_and_names_the_rule(tmp_path):
    invented = 'ev_58ea65f661057c2a45be56f1'
    provider = ContractFixtureProvider(lambda evidence, call: [
        _entity(evidence), _unknown(uncertainty='the page does not state approval authority',
                                   evidence_refs=[invented])])
    result = _propose(tmp_path, provider)
    assert result.producer_attribution['dropped_invalid_items'] == {'evidence_ref_not_supplied': 1}
    drops = result.producer_attribution['dropped_invalid_item_keys']
    assert [row['item_key'] for row in drops] == ['approval_status']
    # Nothing citing evidence the answer never received survives into the candidate.
    assert all(invented not in item.evidence_refs for item in result.semantic_candidate.items)
    assert invented not in str(drops)


def test_contract_drops_are_named_and_a_revision_turn_is_honoured(tmp_path):
    def build(evidence, call):
        if call == 1:  # The refused answer: the very two defects the live run produced.
            return [_entity(evidence), _unknown(), _unknown(key='branch_scope', meaning='分公司范围未说明')]
        return [_entity(evidence), _unknown(uncertainty='the page does not state approval authority'),
                _unknown(key='branch_scope', meaning='分公司范围未说明', uncertainty='branch scope is not on this page')]

    provider = ContractFixtureProvider(build)
    first = _propose(tmp_path, provider)
    # The same two defects the live run produced: dropped and counted, not fatal.
    assert first.producer_attribution['dropped_invalid_items'] == {'uncertainty_required': 2}
    kept = {item.key for item in first.semantic_candidate.items}
    assert 'approval_status' not in kept and 'branch_scope' not in kept
    assert 'marketing' in kept

    revision = {'attempt': 1, 'findings': [{'rule': 'uncertainty_required',
                                            'item_keys': ['approval_status', 'branch_scope']}]}
    repaired = tmp_path / 'repaired'
    repaired.mkdir()
    result = _propose(repaired, provider, revision=revision)
    assert provider.calls == 2
    prompt = provider.system_prompts[1]
    assert 'Revision turn' in prompt and 'uncertainty_required' in prompt
    assert 'approval_status' in prompt and 'branch_scope' in prompt
    assert 'Return the complete JSON object for this evidence again' in prompt
    assert result.revision == revision
    keys = {item.key for item in result.semantic_candidate.items}
    # The revision answers the shape defect it was told about - an uncertainty and no
    # undefined field - so the two rows are no longer dropped for it. They still declare
    # no scope or gap, so they stay run evidence: a revision does not make an absence
    # about the material that was never about it.
    assert keys == {'marketing'}
    assert result.producer_attribution['dropped_invalid_items'] == {}
    assert {'approval_status', 'branch_scope'} <= {row['key'] for row in result.run_diagnostics}


def test_over_capacity_refusal_reaches_the_agent_with_both_counts():
    from catalyst_platform.understand_only import SemanticCapacityError

    def refuse(source_ids):
        raise SemanticCapacityError(128, 135)

    context = SimpleNamespace(plugin_services={"understand.execute": refuse}, raise_if_cancelled=lambda: None)
    observation = UnderstandCapabilityAdapter().invoke({"source_ids": ["s1"]}, context)
    assert isinstance(observation, Failure)
    assert observation.error == "understand_proposal_failed:semantic_capacity_exceeded items=135 limit=128"


def test_contract_violation_reaches_the_agent_as_rule_and_item_keys():
    def refuse(source_ids):
        raise SemanticContractError('uncertainty_required', ['approval_status', 'branch_scope'])

    context = SimpleNamespace(plugin_services={'understand.execute': refuse}, raise_if_cancelled=lambda: None)
    observation = UnderstandCapabilityAdapter().invoke({'source_ids': ['s1']}, context)
    assert isinstance(observation, Failure)
    assert observation.error == (
        'understand_proposal_failed:semantic_item_contract_violation:'
        'uncertainty_required items=approval_status,branch_scope'
    )
