"""PF-02 fake mechanism and pending-owner development controls, never semantic Gold."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from catalyst_platform.llm_provider import configured_model_provider
from catalyst_platform.workbench import CapabilityCatalog, CatalystWorkbench
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.semantic_tool import AdmittedSource, SemanticProposalContext
from catalyst_platform.trace_log import JsonlTraceStore
from tests.test_api_infrastructure_p0 import response, task
from tests.test_p0_admission_identity import _recorder


def canonical(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def fixture_inventory(payload, fault=None):
    """Controlled fake output is external to Subject inputs, not a method answer."""
    rows=[]
    for key,surface,hint,locator in (
        ('finance','财务部','department','line:4'),('voucher','付款凭证','business_object','line:4'),
        ('request','服务申请','business_object','line:4'),('activity','检查付款凭证','activity','line:4'),
        ('field','申请部门','field','line:6'),('role','申请部门','role','line:7')):
        ref=next(r for r in payload['evidence'] if r['locator']==locator and r['s']=='s1')
        rows.append(dict(id='s1_'+key,surface=surface,type_hint=hint,source='s1',
            evidence_refs=[ref['evidence_id']],classification='explicit',uncertainty=None))
    if fault=='missing_voucher':rows=[r for r in rows if r['id']!='s1_voucher']
    if fault=='source':rows[0]['source']='s2'
    if fault=='foreign_evidence':rows[0]['evidence_refs']=['ev_not_admitted']
    if fault=='duplicate':rows.append(rows[0])
    if fault=='unsupported_surface':rows[0]['surface']='无来源的集团'
    if fault=='uncertainty':rows[0].update(type_hint='unknown',uncertainty=None)
    return {'mentions':rows}


def fixture_relations(payload, fault=None):
    inv=json.loads(payload['inventory_raw'])['mentions']
    classes={'explicit':'SOURCE_DIRECT','inferred':'INFERRED','pending':'UNKNOWN'}
    items=[dict(kind='entity',key=r['id'],meaning=r['surface'],evidence_class=classes[r['classification']],
        evidence_refs=r['evidence_refs'],**({'uncertainty':r['uncertainty']} if r['uncertainty'] else {})) for r in inv if r['classification']!='rejected']
    ref=next(r['evidence_id'] for r in payload['evidence'] if r['s']=='s1' and r['locator']=='line:4')
    items.extend([
        dict(kind='relation',key='checks',meaning='财务部检查付款凭证',subject='s1_finance',predicate='检查',object='s1_voucher',evidence_class='SOURCE_DIRECT',evidence_refs=[ref]),
        dict(kind='claim',key='not_approver',meaning='财务部不负责批准服务申请',evidence_class='SOURCE_DIRECT',evidence_refs=[ref]),
        dict(kind='unknown',key='role_mapping',meaning='申请部门角色的具体组织映射未知',evidence_class='UNKNOWN',evidence_refs=[],uncertainty='来源未指定具体部门')])
    relation=next(r for r in items if r['kind']=='relation')
    if fault=='wrong_activity':relation['object']='s1_activity'
    if fault=='reverse':relation.update(subject='s1_voucher',object='s1_finance')
    if fault=='missing_negation':items=[r for r in items if r['key']!='not_approver']
    if fault=='new_entity':items.append(dict(items[0],key='invented_endpoint'))
    if fault=='alter_inventory_entity':items[0]['meaning']='被替换的实体'
    if fault=='no_relations':items=[r for r in items if r['kind']!='relation']
    if fault=='bad_kind':relation['kind']='inference'
    return {'items':items}


class FakeExchange:
    def __init__(self,fault=None):self.fault=fault;self.packets=[];self.inventory_raw=None;self.hook=None;self.source_ids=['s1']
    def __call__(self,url,headers,body):
        packet=json.loads(body);self.packets.append(packet)
        system=packet['messages'][0]['content'];payload=json.loads(packet['messages'][-1]['content']) if packet.get('response_format') else None
        if 'SOURCE_LOCAL_MENTION_INVENTORY_V1' in system:
            if self.fault=='stage1_timeout':raise TimeoutError('OFFLINE_STAGE1_TIMEOUT')
            self.inventory_raw=canonical(fixture_inventory(payload,self.fault))
            data=response(content='{broken' if self.fault=='stage1_json' else self.inventory_raw,usage=self.fault!='stage1_usage')
            if self.fault=='stage1_length':data['choices'][0]['finish_reason']='length'
            if self.hook:self.hook()
        elif 'SOURCE_LOCAL_RELATIONS_V1' in system:
            assert payload['inventory_raw']==self.inventory_raw
            assert hashlib.sha256(self.inventory_raw.encode()).hexdigest()==payload['inventory_manifest']['inventory_sha256']
            if self.fault=='stage2_timeout':raise TimeoutError('OFFLINE_STAGE2_TIMEOUT')
            data=response(content='{broken' if self.fault=='stage2_json' else canonical(fixture_relations(payload,self.fault)),usage=self.fault!='stage2_usage')
            if self.fault=='stage2_length':data['choices'][0]['finish_reason']='length'
        else:
            data=response();data['choices'][0]={'message':{'role':'assistant','content':None,'tool_calls':[{'id':'pf02-selection','type':'function','function':{'name':CapabilityCatalog.internal_key('understand','1.0.0'),'arguments':canonical({'source_ids':self.source_ids})}}]},'finish_reason':'tool_calls'}
        data.update(id='OFFLINE_PF02_'+str(len(self.packets)),model='deepseek-flash',system_fingerprint='OFFLINE_ONLY')
        if 'usage' in data:data['usage']['total_tokens']=data['usage']['prompt_tokens']+data['usage']['completion_tokens']
        return 200,data


def make_case(tmp_path,backend='json',fault=None,max_requests=6):
    source_root=tmp_path/'source';source_root.mkdir(parents=True)
    source=source_root/'departments.txt'
    source.write_text('合成测试，不是企业Gold。\n虚构甲公司设有财务部。\n运营部负责登记。\n财务部负责检查付款凭证，不负责批准服务申请。\n合规部审查受限申请。\n申请单具有申请部门字段。\n申请部门提交申请单后由运营部登记。\n',encoding='utf-8')
    workspace=tmp_path/'workspace'
    app=CatalystWorkbench(workspace,[source_root],understand_extraction_mode='source_local_two_stage')
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    recorder=_recorder(workspace,'pf02-fake');wiki=ProjectWiki(workspace,[source_root],enterprise_id='synthetic',project_id='pf02',backend=backend)
    semantic=SemanticWiki(wiki,recorder=recorder);exchange=FakeExchange(fault)
    provider=configured_model_provider(provider_id='deepseek',api_key='OFFLINE-NON-CREDENTIAL',model='deepseek-flash',base_url='https://api.deepseek.com',transport=exchange,task=task(max_requests=max_requests,input_token_limit=100000,max_output_tokens=1024))
    provider.mode='offline'
    context=SemanticProposalContext(source_root,{'s1':AdmittedSource(source,hashlib.sha256(source.read_bytes()).hexdigest())},semantic,provider,
        {'verified':True,'simulation':True,'permissions':['knowledge.propose'],'readable_scope_ids':[wiki.scope_id]},lambda _:pytest.fail('HARVEST_FORBIDDEN'))
    folder=workspace/'.catalyst/captures/pf02'
    return app,session,provider,context,recorder,wiki,exchange,folder


def capture(case):
    _,session,provider,context,recorder,_,_,folder=case
    return session.capture_execution('理解并提出有来源的语义候选',provider=provider,visible_capabilities=(('understand','1.0.0'),),proposal_context=context,recorder=recorder,artifact_dir=folder)


def development_review(items):
    """Finite P06-A fixture check, independent of Subject; not general NL evaluation."""
    relations=[r for r in items if r['kind']=='relation']
    target=[r for r in relations if r['subject']=='s1_finance' and r['predicate']=='检查' and r['object']=='s1_voucher']
    negative=any(r['kind']=='claim' and r['meaning']=='财务部不负责批准服务申请' for r in items)
    return 'DEV_CONTROL_MATCH_PENDING_OWNER' if len(target)==1 and negative else 'DEV_CONTROL_FAIL'


@pytest.mark.parametrize('backend',['json','sqlite'])
def test_two_actual_extractions_consume_frozen_bytes_and_reach_candidate_consumer(tmp_path,backend):
    from catalyst_platform.understand_wiki import UnderstandWikiAdapter
    case=make_case(tmp_path,backend);_,_,provider,context,recorder,wiki,exchange,folder=case
    result=capture(case);receipt=result.summary()
    assert receipt['status']=='CAPTURED' and len(exchange.packets)==provider.budget_snapshot['attempts']==3
    first=json.loads(exchange.packets[1]['messages'][-1]['content']);second=json.loads(exchange.packets[2]['messages'][-1]['content'])
    assert first['sources']==second['sources'] and first['evidence']==second['evidence']
    assert second['inventory_manifest']['source_payload_sha256']==hashlib.sha256(canonical(first).encode()).hexdigest()
    assert second['inventory_raw']==exchange.inventory_raw
    observation=result.observation();assert development_review(observation['items'])=='DEV_CONTROL_MATCH_PENDING_OWNER'
    raw=result.payload();adapter=UnderstandWikiAdapter(wiki,context.semantic,context.source_root)
    submitted=adapter.submit(raw,declared_scope_id=wiki.scope_id)
    graph=adapter.candidate_graph(submitted['candidate_id'])
    relation=next(n for n in graph['nodes'] if n.get('key')=='checks')
    assert relation['object']=='s1_voucher'
    # Existing Wiki projection deliberately does not establish canonical/item-ID
    # identity for native source-local keys. Read its actual candidate items;
    # never fabricate explicit binding or repair the Wiki consumer to pass.
    assert relation['endpoint_identity_status']=='UNRESOLVED'
    entities=adapter.items(submitted['candidate_id'],kind='entity')['items']
    objects=[n for n in entities if n['key']==relation['object']]
    assert len(objects)==1 and objects[0]['label']=='付款凭证'
    queried=adapter.items(submitted['candidate_id'],kind='relation')['items']
    assert any(r['key']=='checks' and r['object']=='s1_voucher' for r in queried)
    assert wiki.semantic_state()['active_version_id'] is None
    assert not any('accepted_version'==n.get('type') for n in graph['nodes'])
    recorder.finish('success');events=JsonlTraceStore(wiki.workspace).inspect_run(recorder.run_id)['events']
    assert len([e for e in events if e['event_type']=='llm.request.started'])>=3
    assert all('P06-A' not in p['messages'][-1]['content'] and 'required' not in json.loads(p['messages'][-1]['content']) for p in exchange.packets[1:])


@pytest.mark.parametrize('fault,calls',[('missing_voucher',3),('new_entity',3),('alter_inventory_entity',3),('stage1_json',2),('source',2),('foreign_evidence',2),('duplicate',2),('unsupported_surface',2),('uncertainty',2),('stage1_length',2),('stage2_json',3),('stage2_length',3),('bad_kind',3)])
def test_bad_inventory_or_output_stops_without_rebinding_retry_or_harvest(tmp_path,fault,calls):
    case=make_case(tmp_path,fault=fault);result=capture(case)
    assert result.summary()['status']=='OUTPUT_REJECTED'
    assert len(case[6].packets)==calls and case[5].semantic_state()['candidates']=={}
    assert result.summary()['typed_capture'] is False
    with pytest.raises(ValueError):result.payload()


@pytest.mark.parametrize('fault,calls',[('stage1_timeout',2),('stage2_timeout',3),('stage1_usage',2),('stage2_usage',3)])
def test_uncertain_requests_stop_and_preserve_p0_uncertainty(tmp_path,fault,calls):
    case=make_case(tmp_path,fault=fault);result=capture(case)
    assert result.summary()['status']=='MODEL_FAILURE' and len(case[6].packets)==calls
    assert case[2].budget_snapshot['uncertain'] is True
    assert case[5].semantic_state()['candidates']=={}


def test_budget_stops_before_second_extraction(tmp_path):
    case=make_case(tmp_path,max_requests=2);result=capture(case)
    assert len(case[6].packets)==2 and result.summary()['typed_capture'] is False


def test_source_drift_after_inventory_stops_before_second_extraction(tmp_path):
    case=make_case(tmp_path)
    case[6].hook=lambda:next(iter(case[3].sources.values())).path.write_text('CHANGED',encoding='utf-8')
    result=capture(case)
    assert len(case[6].packets)==2 and result.summary()['status']=='OUTPUT_REJECTED'


@pytest.mark.parametrize('fault',['wrong_activity','reverse','missing_negation','no_relations'])
def test_typed_valid_does_not_certify_wrong_business_binding_or_omission(tmp_path,fault):
    case=make_case(tmp_path,fault=fault);result=capture(case)
    assert result.summary()['typed_capture'] is True
    assert development_review(result.observation()['items'])=='DEV_CONTROL_FAIL'
    # The wrong raw response is preserved; consumer must not fix it from source text.
    assert result.summary()['semantic_quality']=='NOT_EVALUATED'


def test_frozen_inventory_sha_and_source_payload_tamper_rejected():
    from catalyst_platform.understand_inventory import freeze_inventory
    payload={'sources':{'s1':{'source_id':'source','source_revision':'a','source_sha256':'a','relative_path':'a.txt'}},'evidence':[{'evidence_id':'ev1','s':'s1','locator':'line:1','quote':'财务部'}],'warnings':[]}
    raw=canonical({'mentions':[dict(id='s1_fin',surface='财务部',type_hint='department',source='s1',evidence_refs=['ev1'],classification='explicit',uncertainty=None)]})
    frozen=freeze_inventory(raw,canonical(payload))
    with pytest.raises(ValueError,match='hash'):replace(frozen,raw=raw+' ').relation_payload(canonical(payload))
    with pytest.raises(ValueError,match='source'):frozen.relation_payload(canonical({**payload,'warnings':['drift']}))


@pytest.mark.parametrize('phase',[1,2])
def test_phase_interruption_freezes_exact_calls_and_never_continues(tmp_path,phase):
    case=make_case(tmp_path)
    exchange=case[6];original=exchange.__call__
    # Special method lookup is on the class, so install on the existing provider
    # transport seam, without replacing Provider/P0 or changing Subject data.
    def interrupt(url,headers,body):
        packet=json.loads(body)
        if packet.get('response_format') and ((phase==1 and len(exchange.packets)==1) or (phase==2 and len(exchange.packets)==2)):
            exchange.packets.append(packet)
            raise KeyboardInterrupt('OFFLINE_INTERRUPT_'+str(phase))
        return original(url,headers,body)
    case[2]._delegate._transport=interrupt
    with pytest.raises(KeyboardInterrupt):capture(case)
    receipt=json.loads((case[7]/'CAPTURE_RECEIPT.json').read_bytes())
    assert receipt['status']=='INTERRUPTED' and len(exchange.packets)==phase+1
    assert receipt['typed_capture'] is False
    with pytest.raises(FileExistsError):capture(case)
    assert len(exchange.packets)==phase+1


def test_inventory_preserves_pending_rejected_and_role_field_identity():
    from catalyst_platform.understand_inventory import freeze_inventory
    payload={'sources':{'s1':{'source_id':'source','source_revision':'a','source_sha256':'a','relative_path':'a.txt'}},'evidence':[{'evidence_id':'ev1','s':'s1','locator':'line:1','quote':'申请部门提交申请，申请部门字段，审批协调尚未知。'}],'warnings':[]}
    rows=[dict(id='s1_role',surface='申请部门',type_hint='role',source='s1',evidence_refs=['ev1'],classification='explicit',uncertainty=None),dict(id='s1_field',surface='申请部门',type_hint='field',source='s1',evidence_refs=['ev1'],classification='explicit',uncertainty=None),dict(id='s1_pending',surface='审批协调',type_hint='unknown',source='s1',evidence_refs=['ev1'],classification='pending',uncertainty='权限尚未确定'),dict(id='s1_rejected',surface='字段',type_hint='field',source='s1',evidence_refs=['ev1'],classification='rejected',uncertainty='非独立业务对象')]
    frozen=freeze_inventory(canonical({'mentions':rows}),canonical(payload))
    assert json.loads(frozen.raw)['mentions']==rows
    assert 'pending' in frozen.raw and 'rejected' in frozen.raw
