from pathlib import Path

from catalyst_platform.understand_only import SemanticContractError, UnderstandPort, UnderstandingRequest

import json
import pytest
from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import route_understand_request, UnderstandIntent


def test_natural_ontology_request_routes_to_semantic_candidate():
    route = route_understand_request('把公司部门职责材料整理成组织语义，形成 Ontology 并保存到 Evo Ontology Wiki。')
    assert route.intent is UnderstandIntent.KNOWLEDGE_PROPOSE


class SemanticFixtureProvider:
    """Deterministic protocol fixture, never a real semantic quality evaluator."""
    model = 'test-semantic-fixture'
    def __init__(self, invalid=False):
        self.calls = 0
        self.invalid = invalid
    def request(self, request):
        self.calls += 1
        payload = json.loads(request.messages[-1].content)
        evidence = payload['evidence']
        assert any('市场部负责客户线索' in row['quote'] for row in evidence)
        return ModelResponse(content=json.dumps({'items': [
            {'kind': 'entity', 'key': 'marketing', 'meaning': '市场部',
             'evidence_class': 'SOURCE_DIRECT', 'evidence_refs': ['invented'] if self.invalid else [evidence[0]['evidence_id']]},
            {'kind': 'unknown', 'key': 'approval', 'meaning': '审批权未知', 'evidence_class': 'UNKNOWN', 'evidence_refs': [], 'uncertainty': 'source does not specify approval authority'},
        ]}, ensure_ascii=False), finish_reason='stop')


def test_explicit_provider_extracts_typed_output_without_losing_source(tmp_path):
    source = tmp_path / 'org.txt'
    source.write_text('市场部负责客户线索。\n运营部负责合同复核。', encoding='utf-8')
    provider = SemanticFixtureProvider()
    result = UnderstandPort().understand(
        UnderstandingRequest('semantic-request', '形成企业本体', source_refs=(source,), intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider,
    )
    assert provider.calls == 1
    assert len(result.evidence_refs) == 2
    assert result.extracted_facts[0].key == 'marketing'
    # The fixture's absence has no scope, so it is run evidence: the card keeps what the
    # source said and the diagnostic travels beside it.
    assert result.unknowns == ()
    assert 'approval' in {row['key'] for row in result.run_diagnostics}
    assert result.producer_attribution['producer_model_id'] == provider.model


def test_semantic_provider_cannot_invent_evidence(tmp_path):
    source = tmp_path / 'org.md'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    result = UnderstandPort().understand(
        UnderstandingRequest('bad-evidence', '形成企业本体', source_refs=(source,), intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=SemanticFixtureProvider(invalid=True),
    )
    # The invented citation costs that row, never the card; nothing carries it further.
    assert result.producer_attribution['dropped_invalid_items'] == {'evidence_ref_not_supplied': 1}
    assert [row['item_key'] for row in result.producer_attribution['dropped_invalid_item_keys']] == ['marketing']
    assert result.extracted_facts == ()
    assert all('invented' not in item.evidence_refs for item in result.semantic_candidate.items)


def test_mechanical_methods_are_not_discoverable_skills_but_preserve_receipts(tmp_path):
    root = Path(__file__).resolve().parents[1] / 'platform-harness' / 'skills'
    names = ('understand-source-inventory', 'understand-document', 'understand-evidence-coverage')
    for name in names:
        assert not (root / name / 'SKILL.md').exists()
        assert (root / '_methods' / f'{name}.md').is_file()
    source = tmp_path / 'source.md'
    source.write_text('公司市场部负责客户线索。', encoding='utf-8')
    result = UnderstandPort().understand(
        UnderstandingRequest('method-proof', 'read source', source_refs=(source,)), source_root=tmp_path,
    )
    assert result.evidence_refs
    assert {s.skill_id for s in result.selected_skills} == set(names)
    assert all(s.instructions and s.skill_sha256 for s in result.selected_skills)


def test_harness_native_document_proposal_preserves_identity_and_gate(tmp_path):
    from catalyst_platform.workbench import CatalystWorkbench
    from catalyst_platform.wiki import ProjectWiki
    from catalyst_platform.semantic_wiki import SemanticWiki, SemanticTransitionError
    from tests.test_p0_admission_identity import _recorder
    roots = tmp_path / 'sources'
    roots.mkdir()
    source = roots / 'org.txt'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    wiki = ProjectWiki(tmp_path / 'workspace', [roots], enterprise_id='synthetic', project_id='stage1')
    recorder = _recorder(tmp_path / 'workspace', 'native-proposal')
    semantic = SemanticWiki(wiki, recorder=recorder)
    app = CatalystWorkbench(tmp_path / 'workspace', [roots])
    session = app.new_session(domain={'id': 'local'}, enterprise={'id': 'synthetic'})
    result = session.propose_enterprise_semantics(
        '整理企业本体', source_refs=[source], source_root=roots,
        semantic=semantic, provider=SemanticFixtureProvider(),
        actor_context={'verified': True, 'simulation': True, 'permissions': ['knowledge.propose'], 'readable_scope_ids': [wiki.scope_id]},
        harvest=lambda result: [i.item_id for i in result.semantic_candidate.items if i.kind == 'entity'],
    )
    candidate = wiki.semantic_state()['candidates'][result['proposal']['candidate_id']]
    assert candidate['proposer_origin'] == 'catalyst_model'
    assert candidate['entries'][0]['evidence_class'] == 'inferred'
    assert semantic.evaluate(candidate['candidate_id'], actor_origin='independent_evaluator')['status'] == 'pass'
    with pytest.raises(SemanticTransitionError, match='verified external semantic evaluation'):
        semantic.decide(candidate['candidate_id'], decision='ACCEPTED', actor_origin='manager_acceptance', reason_code='reviewed')
    assert wiki.semantic_state()['active_version_id'] is None


class OrganizationFixtureProvider:
    """Known synthetic input protocol fixture; no general language understanding claim."""
    model = 'deterministic-organization-fixture'

    def request(self, request):
        """Answers the rows it was given: one call now covers one slide, not the deck."""
        assert request.parameters == {'max_tokens': 4096, 'response_format': {'type': 'json_object'}}
        evidence = json.loads(request.messages[-1].content)['evidence']
        def find(marker):
            return next((r for r in evidence if marker in r['quote']), None)
        market, operations, condition = find('市场部'), find('运营部'), find('十万元')
        def item(kind, key, meaning, ref, **extra):
            return dict(kind=kind, key=key, meaning=meaning, evidence_class='SOURCE_DIRECT', evidence_refs=[ref['evidence_id']], **extra)
        items = []
        if market:
            items.append(item('entity', 'marketing', '市场部', market))
            items.append(item('claim', 'marketing_duty', '市场部负责客户线索登记', market))
            # Both ends are known to the merged candidate, so the edge is stated where
            # the sentence naming them sits.
            items.append(item('relation', 'handoff', '市场部向运营部移交复核', market,
                              subject='marketing', predicate='移交复核', object='operations'))
        if operations:
            items.append(item('entity', 'operations', '运营部', operations))
        if condition:
            items.append(item('condition', 'review_threshold', '超过十万元由运营主管复核', condition))
        items.append(dict(kind='unknown', key='authority', meaning='实际审批权限未知', evidence_class='UNKNOWN', evidence_refs=[], uncertainty='材料没有说明正式审批权限'))
        return ModelResponse(content=json.dumps({'items': items}, ensure_ascii=False), finish_reason='stop')


@pytest.mark.parametrize('backend', ['json', 'sqlite'])
@pytest.mark.parametrize('extension', ['txt', 'md', 'pptx'])
def test_stage1_document_loop_test_scope(tmp_path, backend, extension):
    import hashlib
    import shutil
    import subprocess
    import sys
    from jsonschema import Draft202012Validator
    from catalyst_platform.workbench import CatalystWorkbench
    from catalyst_platform.wiki import ProjectWiki
    from catalyst_platform.semantic_wiki import SemanticWiki, SemanticTransitionError
    from catalyst_platform.trace_log import JsonlTraceStore
    from tests.test_p0_admission_identity import (_recorder, _verifier, _semantic_receipt,
                                                 _owner_receipt, _version_receipt, _signed)
    roots = tmp_path / 'sources'
    roots.mkdir()
    source = roots / ('organization.' + extension)
    if extension == 'pptx':
        shutil.copyfile(Path(__file__).parent / 'fixtures/stage1/organization-v1.pptx', source)
    else:
        source.write_text('市场部负责客户线索登记，运营部负责合同复核。市场部向运营部移交复核材料。\n客户立项由市场部发起；超过十万元由运营主管复核。', encoding='utf-8')
    workspace = tmp_path / 'workspace'
    wiki = ProjectWiki(workspace, [roots], enterprise_id='synthetic', project_id='stage1', backend=backend)
    recorder = _recorder(workspace, 'stage1-document-loop')
    semantic = SemanticWiki(wiki, recorder=recorder, receipt_verifier=_verifier)
    app = CatalystWorkbench(workspace, [roots])
    session = app.new_session(domain={'id': 'local'}, enterprise={'id': 'synthetic'})
    actor = dict(verified=True, simulation=True, permissions=['knowledge.propose'], readable_scope_ids=[wiki.scope_id])
    output = session.propose_enterprise_semantics(
        '将企业资料整理成组织语义，形成 Ontology 并保存', source_refs=[source], source_root=roots,
        semantic=semantic, provider=OrganizationFixtureProvider(), actor_context=actor,
        harvest=lambda result: [i.item_id for i in result.semantic_candidate.items if i.kind != 'unknown'],
    )
    # The fixture's only absence carries no scope, so it is run evidence: the candidate
    # holds what the source said, the diagnostic travels beside it, and nothing is omitted
    # from a harvest because nothing unqualified was ever a candidate.
    assert output['understanding']['run_diagnostics']
    assert output['understanding']['unknowns'] == []
    assert output['omitted_item_ids'] == []
    assert output['understanding']['wiki_handoff'] == 'CANDIDATE_PROPOSED_ONLY'
    if extension == 'pptx':
        locators = [r['locator'] for r in output['understanding']['evidence_refs']]
        assert any('table:' in r for r in locators)
        assert any('slide3.xml' in r for r in locators)
        assert any('NEEDS_VISION' in r for r in output['understanding']['source_warnings'])
    candidate_id = output['proposal']['candidate_id']
    candidate = wiki.semantic_state()['candidates'][candidate_id]
    assert candidate['proposer_origin'] == 'catalyst_model'
    assert all(e['evidence_class'] == 'inferred' for e in candidate['entries'])
    assert semantic.evaluate(candidate_id, actor_origin='independent_evaluator')['status'] == 'pass'
    with pytest.raises(SemanticTransitionError) as missing:
        semantic.decide(candidate_id, decision='ACCEPTED', actor_origin='manager_acceptance', reason_code='reviewed')
    assert missing.value.code == 'external_semantic_evaluation_required'
    # Independent TEST evaluator checks protocol and source bindings, not real model semantics.
    projection = Path(output['projection_path']).read_text(encoding='utf-8').splitlines()
    package = json.loads(projection[1])
    import base64
    assert base64.b64decode(package['originals'][0]['bytes_base64']) == source.read_bytes()
    assert package['originals'][0]['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert any('市场部向运营部移交复核材料' in ref['quote'] for ref in output['understanding']['evidence_refs'])
    assert {e['kind'] for e in candidate['entries']} == {'entity', 'claim', 'condition', 'relation'}
    report = {'kind': 'TEST_SCOPE_PROTOCOL_EVALUATION', 'candidate': candidate_id,
              'source_digest_verified': True, 'selected_count': len(candidate['entries']),
              'semantic_quality': 'NOT_PROVEN', 'fixture_relation': 'synthetic_not_business_authority'}
    (workspace / 'protocol-evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    receipt = _semantic_receipt(wiki, candidate)
    receipt.pop('signature')
    receipt['report_sha256'] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    receipt = _signed(receipt, 'test-evaluator')
    semantic.record_external_evaluation_receipt(receipt=receipt, actor_origin='independent_evaluator')
    with pytest.raises(SemanticTransitionError) as missing_owner:
        semantic.decide(candidate_id, decision='ACCEPTED', actor_origin='manager_acceptance', reason_code='reviewed')
    assert missing_owner.value.code == 'authority_receipt_required'
    accepted = semantic.decide(candidate_id, decision='ACCEPTED', actor_origin='manager_acceptance',
                               reason_code='reviewed', authority_receipt=_owner_receipt(wiki, candidate))
    version = accepted['version_id']
    semantic.activate(version, actor_origin='manager_acceptance',
                      authority_receipt=_version_receipt(wiki, version, candidate, action='ACTIVATE', expected_head=None))
    assert semantic.query('市场部', actor_origin='catalyst_deterministic')
    relation_query = semantic.resolve_relations('市场部', actor_origin='catalyst_deterministic')
    assert relation_query['version_id'] == version and len(relation_query['relations']) == 1
    assert relation_query['relations'][0]['endpoint_status'] == 'resolved'
    # A different document with the same producer keys is not identity proof.
    other = roots / ('other.' + extension)
    shutil.copyfile(source, other)
    other_output = session.propose_enterprise_semantics(
        '整理企业本体', source_refs=[other], source_root=roots, semantic=semantic,
        provider=OrganizationFixtureProvider(), actor_context=actor,
        harvest=lambda result: [i.item_id for i in result.semantic_candidate.items if i.kind != 'unknown'],
    )
    reviewed = semantic.evaluate(other_output['proposal']['candidate_id'], actor_origin='independent_evaluator')
    assert reviewed['status'] == 'needs_review'
    assert any(f['code'] == 'producer_entity_key_not_identity_evidence' for f in reviewed['findings'])
    assert wiki.semantic_state()['active_version_id'] == version
    recorder.finish(status='success', model_calls=2)
    semantic.finalize_run(recorder.run_id, 'success')
    script = '''import json,sys
from catalyst_platform.wiki import ProjectWiki
w=ProjectWiki(sys.argv[1],[sys.argv[2]],enterprise_id='synthetic',project_id='stage1',backend=sys.argv[3])
s=w.semantic_state();v=s['accepted_versions'][s['active_version_id']]
print(json.dumps({'id':s['active_version_id'],'authority':v['authority_class'],'meanings':v['meanings']},ensure_ascii=False))'''
    cold = json.loads(subprocess.check_output([sys.executable, '-c', script, str(workspace), str(roots), backend], encoding='utf-8'))
    assert cold['id'] == version and cold['authority'] == 'test_only'
    relations = [r for r in cold['meanings'].values() if r['kind'] == 'relation']
    assert len(relations) == 1 and relations[0]['canonical_subject_id'] and relations[0]['canonical_object_id']
    trace = JsonlTraceStore(workspace).inspect_run(recorder.run_id)
    calls = [e['model_call_id'] for e in trace['events'] if e['event_type'] == 'llm.request.started']
    # Two proposals were made on this recorder; each extraction call covers one unit of
    # evidence, so a three-slide deck is three calls per proposal.
    units_per_proposal = 3 if extension == 'pptx' else 1
    assert len(calls) == len(set(calls)) == 2 * units_per_proposal
    types = {e['event_type'] for e in trace['events']}
    assert {'semantic.candidate.proposed', 'semantic.candidate.external_evaluation.received', 'semantic.version.activated'} <= types
    assert any(e.get('span_name') == 'plugin.understand.analyze' for e in trace['events'])
    schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/run_event_v1_5.schema.json').read_text(encoding='utf-8'))
    errors = [str(error) for e in trace['events'] for error in Draft202012Validator(schema).iter_errors(e)]
    assert not errors



@pytest.mark.parametrize('failure', ['unexpected_property', 'duplicate_key', 'source_changed', 'truncated'])
def test_structured_extractor_rejects_unsafe_output(tmp_path, failure):
    source = tmp_path / 'org.md'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    class InvalidProvider(SemanticFixtureProvider):
        def request(self, request):
            response = super().request(request)
            data = json.loads(response.content)
            if failure == 'unexpected_property':
                data['items'][0]['activation_authorized'] = True
            elif failure == 'duplicate_key':
                data['items'].append(data['items'][0])
            elif failure == 'source_changed':
                source.write_text('changed', encoding='utf-8')
            return ModelResponse(content=json.dumps(data), finish_reason='length' if failure == 'truncated' else 'stop')
    with pytest.raises(ValueError):
        UnderstandPort().understand(UnderstandingRequest('unsafe', '整理企业本体', source_refs=(source,)), source_root=tmp_path, semantic_provider=InvalidProvider())


@pytest.mark.parametrize('which,failure', [('unknown', 'unknown_without_reason'), ('entity', 'inferred_without_reason')])
def test_an_item_that_breaks_its_own_contract_is_dropped_not_the_card(tmp_path, which, failure):
    """An item with no reason for being inferred or unknown costs that row, not the answer."""
    source = tmp_path / 'org.md'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    class BareProvider(SemanticFixtureProvider):
        def request(self, request):
            data = json.loads(super().request(request).content)
            if failure == 'unknown_without_reason':
                data['items'][1].pop('uncertainty')
                self.dropped_meaning = data['items'][1]['meaning']
            else:
                data['items'][0]['evidence_class'] = 'INFERRED'
                data['items'][0]['uncertainty'] = ''
                self.dropped_meaning = data['items'][0]['meaning']
            return ModelResponse(content=json.dumps(data, ensure_ascii=False), finish_reason='stop')
    provider = BareProvider()
    result = UnderstandPort().understand(UnderstandingRequest('bare', '整理企业本体', source_refs=(source,)),
        source_root=tmp_path, semantic_provider=provider)
    assert result.producer_attribution['dropped_invalid_items'] == {'uncertainty_required': 1}
    assert not any(item.meaning == provider.dropped_meaning for item in result.semantic_candidate.items)
    if which == 'unknown':
        # The sound row beside the dropped one is untouched.
        assert 'marketing' in {item.key for item in result.semantic_candidate.items}


def test_structured_extractor_drops_a_relation_whose_end_is_not_declared(tmp_path):
    source = tmp_path / 'org.md'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    class DanglingProvider(SemanticFixtureProvider):
        def request(self, request):
            data = json.loads(super().request(request).content)
            refs = [json.loads(request.messages[-1].content)['evidence'][0]['evidence_id']]
            data['items'].append(dict(kind='relation', key='relation', meaning='关系', subject='marketing',
                predicate='to', object='absent', evidence_class='SOURCE_DIRECT', evidence_refs=refs))
            return ModelResponse(content=json.dumps(data, ensure_ascii=False), finish_reason='stop')
    result = UnderstandPort().understand(UnderstandingRequest('unsafe', '整理企业本体', source_refs=(source,)),
        source_root=tmp_path, semantic_provider=DanglingProvider())
    assert result.producer_attribution['dropped_relation_count'] == 1
    assert result.producer_attribution['dropped_relations'] == [{'item_key': 'relation', 'rule': 'relation_endpoint_not_declared'}]
    assert 'relation' not in {item.key for item in result.semantic_candidate.items}
    assert 'marketing' in {item.key for item in result.semantic_candidate.items}

@pytest.mark.parametrize('failure', ['permission', 'scope', 'unverified', 'plugin_unloaded', 'harvest_conflict', 'harvest_unknown'])
def test_harness_semantic_boundaries(tmp_path, failure):
    from catalyst_platform.workbench import CatalystWorkbench
    from catalyst_platform.wiki import ProjectWiki
    from catalyst_platform.semantic_wiki import SemanticWiki
    from tests.test_p0_admission_identity import _recorder
    roots = tmp_path / 'sources'
    roots.mkdir()
    source = roots / 'org.txt'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    workspace = tmp_path / 'workspace'
    wiki = ProjectWiki(workspace, [roots], enterprise_id='synthetic', project_id='stage1')
    semantic = SemanticWiki(wiki, recorder=_recorder(workspace, 'denied-semantic'))
    app = CatalystWorkbench(workspace, [roots])
    session = app.new_session(domain={'id': 'local'}, enterprise={'id': 'synthetic'})
    actor = dict(verified=True, simulation=True, permissions=['knowledge.propose'], readable_scope_ids=[wiki.scope_id])
    if failure == 'permission': actor['permissions'] = []
    if failure == 'scope': actor['readable_scope_ids'] = ['other']
    if failure == 'unverified': actor['verified'] = False
    if failure == 'plugin_unloaded': app.plugins.unload('understand')
    class BoundaryProvider(SemanticFixtureProvider):
        def request(self, request):
            response = super().request(request)
            data = json.loads(response.content)
            if failure == 'harvest_conflict':
                data['items'][0]['evidence_class'] = 'CONFLICT'
            if failure == 'harvest_unknown':
                data['items'][0]['evidence_class'] = 'UNKNOWN'
            return ModelResponse(content=json.dumps(data), finish_reason='stop')
    provider = BoundaryProvider()
    with pytest.raises((ValueError, RuntimeError)):
        session.propose_enterprise_semantics('整理企业本体', source_refs=[source], source_root=roots,
            semantic=semantic, provider=provider, actor_context=actor,
            harvest=lambda result: [i.item_id for i in result.semantic_candidate.items if i.kind == 'entity'])
    assert wiki.semantic_state()['candidates'] == {}
    assert wiki.semantic_state()['active_version_id'] is None
    if failure not in {'harvest_conflict', 'harvest_unknown'}:
        assert provider.calls == 0


def test_live_semantic_extraction_prompt_has_no_prefilled_business_instances(tmp_path):
    from catalyst_platform.understand_only import UnderstandPort, UnderstandingRequest, UnderstandIntent

    source = tmp_path / "source.txt"
    source.write_text("组织单元甲按流程条件乙处理事项丙。", encoding="utf-8")

    class CaptureRequest:
        model = "offline-capture"

        def request(self, request):
            self.captured = request
            raise RuntimeError("request captured before transport")

    provider = CaptureRequest()
    try:
        UnderstandPort().understand(
            UnderstandingRequest(
                "blind-prompt-integrity",
                "请阅读我提供的企业资料，理解其中描述的业务内容，识别有意义的业务对象、属性、关系、规则及其依据，并建立一份结构化的企业知识模型。请区分资料明确陈述、合理推断和无法确定的信息。不要补造原文没有提供的事实。",
                source_refs=(source,),
                intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
            ),
            source_root=tmp_path,
            semantic_provider=provider,
        )
    except RuntimeError as exc:
        assert str(exc) == "request captured before transport"
    else:
        raise AssertionError("offline provider should stop before model transport")

    system_message = provider.captured.messages[0].content
    assert "marketing" not in system_message
    assert "operations" not in system_message
    assert "reports_to" not in system_message
    assert all(field in system_message for field in ("subject", "predicate", "object"))
