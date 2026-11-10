"""Original-file admission and bounded-output tests; all inputs are synthetic."""
from dataclasses import replace
import hashlib
import json

import pytest
from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import UnderstandPort, UnderstandingRequest
from tests.test_agent_understand_binding import setup_case


def test_scoped_original_units_exclude_host_metadata_without_keyword_deletion(tmp_path):
    from catalyst_platform.semantic_tool import AdmittedSource
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path)
    source = next(iter(proposal.sources.values())).path
    source.write_text('服务组负责工单登记，这是合法业务任务说明。\nCASE_INPUT: test preparation metadata\n服务组保留来源证据。\n', encoding='utf-8')
    proposal = replace(proposal, sources={'document': AdmittedSource(source,
        hashlib.sha256(source.read_bytes()).hexdigest(), locators=('line:1', 'line:3'))})
    run = session.ask('形成可审查候选', provider=provider, execution_mode='agent',
        visible_capabilities=[('understand','1.0.0')], proposal_context=proposal, recorder=recorder)
    assert run.result.status == 'success'
    request = next(r for r in provider.requests if r.parameters.get('response_format'))
    evidence = json.loads(request.messages[-1].content)['evidence']
    assert {row['locator'] for row in evidence} == {'line:1','line:3'}
    assert any('合法业务任务说明' in row['quote'] for row in evidence)
    assert 'CASE_INPUT' not in request.messages[-1].content
    payload=json.loads(request.messages[-1].content)
    assert all(payload['sources'][row['s']]['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest() for row in evidence)
    assert set(evidence[0]) == {'evidence_id','s','locator','quote'}
    assert all(len(row['s']) <= 12 for row in evidence)
    assert all(payload['sources'][row['s']]['source_id'] for row in evidence)


def test_unknown_source_unit_locator_refuses_instead_of_silent_partial(tmp_path):
    from catalyst_platform.semantic_tool import AdmittedSource
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path)
    src = next(iter(proposal.sources.values()))
    proposal = replace(proposal, sources={'document': AdmittedSource(src.path, src.sha256, locators=('line:999',))})
    run = session.ask('形成候选', provider=provider, execution_mode='agent',
        visible_capabilities=[('understand','1.0.0')], proposal_context=proposal, recorder=recorder)
    assert run.result.status == 'failure'
    assert provider.stages == ['selection']
    assert wiki.semantic_state()['candidates'] == {}


def test_exact_original_locator_is_selected_before_reader_unit_cap(tmp_path):
    from catalyst_platform.semantic_tool import AdmittedSource
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path)
    src=next(iter(proposal.sources.values()))
    src.path.write_text('\n'.join(['资料占位行']*599+['服务组负责工单登记。'])+'\n',encoding='utf-8')
    proposal=replace(proposal,sources={'document':AdmittedSource(src.path,
        hashlib.sha256(src.path.read_bytes()).hexdigest(),locators=('line:600',))})
    run=session.ask('形成候选',provider=provider,execution_mode='agent',
        visible_capabilities=[('understand','1.0.0')],proposal_context=proposal,recorder=recorder)
    assert run.result.status=='success'
    extraction=next(r for r in provider.requests if r.parameters.get('response_format'))
    assert [r['locator'] for r in json.loads(extraction.messages[-1].content)['evidence']]==['line:600']


def test_unscoped_over_capacity_never_silently_produces_complete_candidate(tmp_path):
    source=tmp_path/'large.txt'; source.write_text('事项'*2501,encoding='utf-8')
    class NeverCall:
        def request(self,_):
            pytest.fail('Partial source content must be refused before extraction request')
    with pytest.raises(ValueError,match='bound|partial'):
        UnderstandPort().understand(UnderstandingRequest('large','企业本体',source_refs=(source,),
            intent='KNOWLEDGE_PROPOSE',requested_depth='semantic',budget_steps=16),source_root=tmp_path,semantic_provider=NeverCall())


def test_port_uses_the_existing_model_task_output_limit(tmp_path, monkeypatch):
    from tests.test_api_infrastructure_p0 import provider, task, response
    observed = []
    def transport(_url, _headers, body):
        payload = json.loads(body); observed.append(payload)
        evidence = json.loads(payload['messages'][-1]['content'])['evidence']
        items = [dict(kind='entity', key='team', meaning='服务组', evidence_class='SOURCE_DIRECT', evidence_refs=[evidence[0]['evidence_id']])]
        return 200, response(content=json.dumps({'items':items}, ensure_ascii=False))
    p, _ = provider(monkeypatch, task(max_output_tokens=1024, input_token_limit=20000), transport)
    source = tmp_path/'source.txt'; source.write_text('服务组负责工单登记。', encoding='utf-8')
    result = UnderstandPort().understand(UnderstandingRequest('capacity', '企业本体', source_refs=(source,),
        intent='KNOWLEDGE_PROPOSE', requested_depth='semantic', budget_steps=16), source_root=tmp_path, semantic_provider=p)
    assert result.semantic_candidate
    assert observed[0]['max_tokens'] == 1024
    assert p.budget_snapshot['attempts'] == 1


@pytest.mark.parametrize('bad_endpoint', [True, False])
def test_relation_requires_entities_and_never_rewrites_claims(tmp_path, bad_endpoint):
    source = tmp_path/'source.md'; source.write_text('服务组向支持组移交工单。', encoding='utf-8')
    class Producer:
        def request(self, request):
            evidence = json.loads(request.messages[-1].content)['evidence']; refs=[evidence[0]['evidence_id']]
            names={'a':'服务组','b':'支持组','duty':'服务组向支持组移交工单','link':'服务组向支持组移交工单'}
            def row(kind,key,**kw):
                return dict(kind=kind,key=key,meaning=names[key],evidence_class='SOURCE_DIRECT',evidence_refs=refs,**kw)
            self.raw = json.dumps({'items':[row('entity','a'),row('entity','b'),row('claim','duty'),
                row('relation','link',subject='a',predicate='hands_to',object='duty' if bad_endpoint else 'b')]})
            return ModelResponse(content=self.raw, finish_reason='stop')
    p = Producer()
    req=UnderstandingRequest('endpoint', '企业本体', source_refs=(source,), intent='KNOWLEDGE_PROPOSE', requested_depth='semantic', budget_steps=16)
    result=UnderstandPort().understand(req,source_root=tmp_path,semantic_provider=p)
    relations={i.key:i for i in result.semantic_candidate.items if i.kind=='relation'}
    claims={i.key:i for i in result.semantic_candidate.items if i.kind=='claim'}
    if bad_endpoint:
        # The edge is dropped and counted; the claim it pointed at stays as written.
        assert relations=={}
        assert result.producer_attribution['dropped_relations']==[{'item_key':'link','rule':'relation_endpoint_not_declared'}]
        assert claims['duty'].meaning=='服务组向支持组移交工单'
        assert json.loads(p.raw)['items'][-1]['object']=='duty'
    else:
        assert relations['link'].object=='b'
        assert result.producer_attribution['dropped_relation_count']==0


def test_the_card_never_reads_its_own_derived_package_as_a_source(tmp_path):
    """The proposal folder the product writes back into the materials root is not material.

    A second card over the same folder otherwise reads the first card's derived package as
    if the Owner had supplied it, and the storage step becomes evidence for itself.
    """
    materials = tmp_path / 'materials'
    (materials / '.catalyst-proposals').mkdir(parents=True)
    (materials / 'deck.md').write_text('服务组负责工单登记。\n', encoding='utf-8')
    (materials / '.catalyst-proposals' / 'derived.md').write_text('服务组负责派工审批。\n', encoding='utf-8')

    class Producer:
        def request(self, request):
            evidence = json.loads(request.messages[-1].content)['evidence']
            return ModelResponse(content=json.dumps({'items': [
                dict(kind='entity', key='team', meaning='服务组', evidence_class='SOURCE_DIRECT',
                     evidence_refs=[evidence[0]['evidence_id']])]}, ensure_ascii=False),
                finish_reason='stop')

    result = UnderstandPort().understand(
        UnderstandingRequest('derived-folder', '企业本体', source_refs=(materials,),
                             intent='KNOWLEDGE_PROPOSE', requested_depth='semantic', budget_steps=16),
        source_root=materials.parent, semantic_provider=Producer())
    assert {ref.relative_path for ref in result.evidence_refs} == {'materials/deck.md'}
    assert '派工审批' not in ' '.join(ref.quote for ref in result.evidence_refs)
