import json
import pytest
from catalyst_platform.project_acceptance import ProjectAcceptance
from catalyst_platform.workbench import CapabilityCatalog
from tests.project_live.test_project_acceptance import configured, qualification_clock
from tests.project_understand.test_project_runtime import offline
from tests.project_live.test_daily_workflow_boundary import recorder
from tests.test_workspace_model_settings import packet as response

@pytest.mark.parametrize('extension',['md','pptx'])
@pytest.mark.parametrize('backend',['json','sqlite'])
@pytest.mark.parametrize('fault',[None,'typed','no_tool','timeout','partial'])
def test_semantic_card_uses_original_capture_and_stops_before_harvest(tmp_path,offline,backend,fault,extension):
    host,root,_,_=configured(tmp_path)
    host.backend=backend
    docs=tmp_path/'documents';docs.mkdir()
    if extension=='md':
        (docs/'departments.md').write_text('服务组负责工单登记。\n',encoding='utf-8')
    else:
        import shutil
        from pathlib import Path
        shutil.copyfile(Path(__file__).parents[1]/'fixtures/stage1/organization-v1.pptx',docs/'organization.pptx')
    if fault=='partial':(docs/'unread.md').write_text('另一份合成资料。',encoding='utf-8')
    calls=[]
    def transport(url,headers,body):
        p=json.loads(body);calls.append(p)
        if p.get('response_format'):
            if fault=='timeout':raise TimeoutError('OFFLINE')
            evidence=json.loads(p['messages'][-1]['content'])['evidence']
            row=dict(kind='inference' if fault=='typed' else 'entity',key='team',meaning=evidence[0]['quote'],evidence_class='SOURCE_DIRECT',evidence_refs=[evidence[0]['evidence_id']])
            return 200,response(content=json.dumps({'items':[row]},ensure_ascii=False))
        if fault=='no_tool':return 200,response(content='No tool selected')
        result=response()
        result['choices'][0]={'message':{'role':'assistant','content':None,'tool_calls':[{'id':'selection','type':'function','function':{'name':CapabilityCatalog.internal_key('understand','1.0.0'),'arguments':json.dumps({'source_ids':[source_id]})}}]},'finish_reason':'tool_calls'}
        return 200,result
    host.settings.transport_override=transport
    # Reconfigure only fake local connection; no credentials read or real network.
    from tests.test_workspace_model_settings import configuration
    host.settings.configure(configuration())
    flow=ProjectAcceptance(host,{'documents':dict(root=docs,object_type='enterprise_documents',task_kind='enterprise_semantics',review_questions=['PRIVATE_REVIEW_ONLY_NOT_MODEL_CONTEXT'])})
    card=flow.prepare('documents','理解组织职责，形成有来源的候选',1,limits={'max_requests':4,'max_output_tokens':1024})
    source_id=card['card']['sources'][0]['source_id']
    rec=recorder(host);host.prepare(rec)
    result=flow.execute(card['test_id'],card['card_sha256'],rec)
    receipt=result['capture']
    assert receipt['status']=={None:'CAPTURED','typed':'OUTPUT_REJECTED','no_tool':'NOT_EXECUTED','timeout':'MODEL_FAILURE','partial':'CAPTURED'}[fault]
    assert result['state']=={None:'CAPTURED','typed':'OUTPUT_REJECTED','no_tool':'NOT_EXECUTED','timeout':'MODEL_FAILURE','partial':'PARTIAL_SOURCE_COVERAGE'}[fault]
    # One selection call, then one extraction call per evidence unit (a slide): the
    # refusal faults stop at the first extraction call, a contract fault is seen after
    # every unit has answered.
    units=1 if extension=='md' else 3
    assert len(calls)==(1 if fault=='no_tool' else 2 if fault=='timeout' else 1+units)
    assert 'PRIVATE_REVIEW_ONLY_NOT_MODEL_CONTEXT' not in json.dumps(calls)
    assert card['card']['storage_backend']==backend
    assert result['execution_profile']=='experiment'
    assert result['external_calls']==0 and result['mode']=='OFFLINE_FAKE'
    if fault is None:assert result['observation']['items']
    final=flow.get(card['test_id'])
    assert final['semantic_quality']=='NOT_EVALUATED'
    if fault=='partial':
        assert result['status']=='failure' and result['state']=='PARTIAL_SOURCE_COVERAGE'
        assert len(result['source_coverage']['unread'])==1
    assert receipt['candidate_id'] is None and receipt['version_id'] is None
    assert receipt['boundary'] in {'BEFORE_HARVEST','NO_METHOD_EXECUTION'}
    assert host.settings.provider.budget_snapshot['attempts']==0
    assert final['budget']['attempts']==len(calls)
    assert final['state']==('UNRESOLVED' if fault=='timeout' else 'FINISHED' if fault is None else 'FAILED')


def test_semantic_source_and_method_identity_change_blocks_dispatch(tmp_path,offline):
    host,_,calls,_=configured(tmp_path)
    docs=tmp_path/'docs';docs.mkdir();(docs/'a.txt').write_text('synthetic',encoding='utf-8')
    flow=ProjectAcceptance(host,{'docs':dict(root=docs,object_type='enterprise_documents',task_kind='enterprise_semantics')})
    card=flow.prepare('docs','inspect',1)
    (docs/'a.txt').write_text('changed',encoding='utf-8')
    rec=recorder(host);host.prepare(rec)
    with pytest.raises(ValueError,match='test_inputs_or_qualification_changed'):
        flow.execute(card['test_id'],card['card_sha256'],rec)
    assert calls==[]


def test_cancel_during_semantic_snapshot_never_dispatches(tmp_path,offline,monkeypatch):
    from catalyst_platform import semantic_acceptance as adapter
    host,_,calls,_=configured(tmp_path)
    docs=tmp_path/'docs';docs.mkdir();(docs/'a.txt').write_text('服务组负责登记。',encoding='utf-8')
    flow=ProjectAcceptance(host,{'docs':dict(root=docs,object_type='enterprise_documents',task_kind='enterprise_semantics')})
    card=flow.prepare('docs','理解组织职责，形成有来源的候选',1)
    rec=recorder(host);host.prepare(rec)
    original=adapter.snapshot
    def snapshot(*args):
        result=original(*args)
        assert host.cancel(rec.run_id)
        return result
    monkeypatch.setattr(adapter,'snapshot',snapshot)
    with pytest.raises(ValueError,match='test_cancelled'):
        flow.execute(card['test_id'],card['card_sha256'],rec)
    assert calls==[]

@pytest.mark.parametrize('filename',['credentials.md','.env.txt','broken.pptx'])
def test_unsafe_or_unreadable_semantic_source_blocks_before_dispatch(tmp_path,offline,filename):
    host,_,calls,_=configured(tmp_path)
    docs=tmp_path/'docs';docs.mkdir();(docs/filename).write_text('not a presentation',encoding='utf-8')
    flow=ProjectAcceptance(host,{'docs':dict(root=docs,object_type='enterprise_documents',task_kind='enterprise_semantics')})
    with pytest.raises(ValueError):flow.prepare('docs','理解组织职责，形成有来源的候选',1)
    assert calls==[]


def test_custom_method_change_invalidates_semantic_card(tmp_path,offline):
    import shutil
    from pathlib import Path
    from catalyst_platform.understand_only import _SKILL_ROOT
    host,_,calls,_=configured(tmp_path)
    docs=tmp_path/'docs';docs.mkdir();(docs/'a.txt').write_text('服务组负责登记。',encoding='utf-8')
    method=tmp_path/'method';shutil.copytree(_SKILL_ROOT,method)
    flow=ProjectAcceptance(host,{'docs':dict(root=docs,object_type='enterprise_documents',task_kind='enterprise_semantics',method_root=method)})
    card=flow.prepare('docs','理解组织职责，形成有来源的候选',1)
    file=method/'understand-enterprise-semantics/SKILL.md'
    file.write_bytes(file.read_bytes()+b'\nchanged')
    rec=recorder(host);host.prepare(rec)
    with pytest.raises(ValueError,match='test_inputs_or_qualification_changed'):
        flow.execute(card['test_id'],card['card_sha256'],rec)
    assert calls==[]

def test_a_project_card_asks_for_a_longer_read_window_than_a_daily_turn(tmp_path, offline, monkeypatch):
    """One extraction writes a whole candidate; a daily chat turn does not need 180s."""
    # The scope assembly imports the factory from workspace_settings at call time.
    import catalyst_platform.workspace_settings as settings_module
    seen = []
    real = settings_module.configured_model_provider

    def record(**kwargs):
        seen.append(kwargs['timeout'])
        return real(**kwargs)

    monkeypatch.setattr(settings_module, 'configured_model_provider', record)
    host, flow, card = _semantic_flow(tmp_path)          # the daily connection: 45s
    rec = recorder(host)
    host.prepare(rec)
    flow.execute(card['test_id'], card['card_sha256'], rec, verifier_provider=_Verifier())
    assert seen[0] == 45 and seen[-1] == 180


class _Verifier:
    """A separate model with its own context; only its request shape matters here."""

    structured_output_token_limit = 16384

    def __init__(self, verdict='REVIEWABLE', findings=()):
        from agent_runtime.contracts import ModelResponse
        self._response = ModelResponse
        self.verdict = verdict
        self.findings = list(findings)
        self.calls = []

    def request(self, request):
        self.calls.append(request)
        return self._response(content=json.dumps({'verdict': self.verdict, 'findings': self.findings},
                                                 ensure_ascii=False), finish_reason='stop')


def _semantic_flow(tmp_path):
    from tests.test_workspace_model_settings import configuration
    host, root, _, _ = configured(tmp_path)
    docs = tmp_path / 'documents'
    docs.mkdir()
    (docs / 'departments.md').write_text('服务组负责工单登记。\n', encoding='utf-8')
    holder = {}

    def transport(url, headers, body):
        p = json.loads(body)
        if p.get('response_format'):
            evidence = json.loads(p['messages'][-1]['content'])['evidence']
            row = dict(kind='entity', key='team', meaning=evidence[0]['quote'],
                       evidence_class='SOURCE_DIRECT', evidence_refs=[evidence[0]['evidence_id']])
            return 200, response(content=json.dumps({'items': [row]}, ensure_ascii=False))
        result = response()
        result['choices'][0] = {'message': {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'selection', 'type': 'function', 'function': {
                'name': CapabilityCatalog.internal_key('understand', '1.0.0'),
                'arguments': json.dumps({'source_ids': [holder['source_id']]})}}]}, 'finish_reason': 'tool_calls'}
        return 200, result

    host.settings.transport_override = transport
    host.settings.configure(configuration())
    flow = ProjectAcceptance(host, {'documents': dict(root=docs, object_type='enterprise_documents',
        task_kind='enterprise_semantics', review_questions=['PRIVATE_REVIEW_ONLY_NOT_MODEL_CONTEXT'])})
    card = flow.prepare('documents', '理解组织职责，形成有来源的候选', 1,
                        limits={'max_requests': 4, 'max_output_tokens': 1024})
    holder['source_id'] = card['card']['sources'][0]['source_id']
    return host, flow, card


def test_a_supplied_verifier_reads_the_candidate_and_keeps_it_reachable(tmp_path, offline):
    """The card hands the port a second model; a REVIEWABLE verdict leaves the capture intact."""
    from catalyst_platform.understand_only import _verifier_instruction
    host, flow, card = _semantic_flow(tmp_path)
    verifier = _Verifier()
    rec = recorder(host)
    host.prepare(rec)
    result = flow.execute(card['test_id'], card['card_sha256'], rec, verifier_provider=verifier)
    assert result['capture']['status'] == 'CAPTURED'
    assert len(verifier.calls) == 1
    request = verifier.calls[0]
    # The verifier sees the shipped method, the goal and the candidate's own quotes.
    assert request.messages[0].content.strip() == _verifier_instruction().strip()
    payload = json.loads(request.messages[1].content)
    # The payload carries the goal, the items, what the extraction already knows it lost,
    # its local advisories and the batch it is - and, beside the items, the rows the run
    # could not establish: they are not statements, so the reviewer reads them apart from
    # the rows it is asked to judge.
    assert set(payload) == {'goal', 'item_count', 'items', 'integrity', 'advisories',
                            'local_checks', 'batch', 'run_diagnostics'}
    assert payload['items'][0]['item_key'] == 'team'
    assert payload['items'][0]['quotes'][0]['quote'] == '服务组负责工单登记。'
    # No extraction method, no generation prompt, no review questions.
    assert 'PRIVATE_REVIEW_ONLY_NOT_MODEL_CONTEXT' not in request.messages[1].content
    attribution = [json.loads(path.read_text(encoding='utf-8'))
                   for path in host.app.state_root.rglob('understanding.json')]
    assert attribution and attribution[0]['producer_attribution']['independent_verification']['verdict'] == 'REVIEWABLE'


def test_a_refused_candidate_stops_the_card_and_carries_its_findings(tmp_path, offline):
    """A REJECT verdict becomes a typed capability failure; the card never reaches Harvest."""
    from catalyst_platform.understand_only import SemanticVerificationError, revision_from_findings
    host, flow, card = _semantic_flow(tmp_path)
    findings = [{'id': 'f1', 'severity': 'hard_stop', 'item_keys': ['team'],
                 'reason': 'quote does not name a team'}]
    verifier = _Verifier('REJECT', findings=findings)
    rec = recorder(host)
    host.prepare(rec)
    result = flow.execute(card['test_id'], card['card_sha256'], rec, verifier_provider=verifier)
    assert result['status'] == 'failure' and result['state'] == 'OUTPUT_REJECTED'
    assert result['capture']['failure_type'] == 'SemanticVerificationError'
    assert result['capture']['boundary'] in {'BEFORE_HARVEST', 'NO_METHOD_EXECUTION'}
    assert result['capture']['candidate_id'] is None
    assert len(verifier.calls) == 1
    # The same findings are what a bounded revision entry carries.
    revision = revision_from_findings(findings)
    assert revision['findings'] == [{'rule': 'independent review: hard_stop f1', 'item_keys': ['team'],
                                     'locators': []}]
    # A finding's reason quotes the source, so it never travels in an error string.
    error = SemanticVerificationError('REJECT', findings)
    assert 'quote does not name a team' not in str(error) and error.item_keys == ('team',)
    assert flow.get(card['test_id'])['state'] == 'FAILED'
