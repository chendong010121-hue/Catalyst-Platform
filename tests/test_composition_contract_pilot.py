"""Synthetic TEST-ONLY consumer proof; not production Rebuild or semantic evaluation."""
from copy import deepcopy
import pytest
from examples.composition_contract_pilot import bind_receipt_reference, ContractRefused


def expected():
    return {'scope_id':'enterprise:synthetic/project:pilot','source_id':'source-test',
            'source_revision':'a'*64,'object_type':'payment_receipt','object_id':'receipt-test',
            'evidence_class':'SOURCE_EXPLICIT','locator':'line:2','span_sha256':'c'*64}


def test_explicit_mapping_keeps_input_and_returns_only_bound_fields():
    upstream={'source_ref':expected(),'query':'synthetic only'}
    before=deepcopy(upstream)
    result=bind_receipt_reference(upstream,expected())
    assert upstream==before
    assert result=={'receipt_ref':expected()}
    assert result['receipt_ref'] is not upstream['source_ref']


@pytest.mark.parametrize('field,value,code',[
    ('scope_id','enterprise:other','SCOPE_MISMATCH'),
    ('source_id','source-other','SOURCE_MISMATCH'),
    ('source_revision','b'*64,'REVISION_MISMATCH'),
    ('object_type','service_application','OBJECT_TYPE_MISMATCH'),
    ('object_id','application-test','OBJECT_ID_MISMATCH'),
    ('evidence_class','UNKNOWN','REVIEW_REQUIRED'),
    ('evidence_class','SOURCE_INFERRED','REVIEW_REQUIRED'),
])
def test_shape_compatible_wrong_identity_never_binds(field,value,code):
    ref=expected();ref[field]=value
    with pytest.raises(ContractRefused,match=code):
        bind_receipt_reference({'source_ref':ref},expected())


@pytest.mark.parametrize('ref',[{},None,{'source_id':'source-test'}, {**expected(),'owner_approved':True}])
def test_incomplete_or_added_authority_fields_refused(ref):
    with pytest.raises(ContractRefused,match='REFERENCE_SHAPE'):
        bind_receipt_reference({'source_ref':ref},expected())


def test_untrusted_caller_cannot_supply_the_expected_mapping():
    upstream={'source_ref':expected(),'expected':{**expected(),'object_type':'service_application'}}
    with pytest.raises(ContractRefused,match='UPSTREAM_SHAPE'):
        bind_receipt_reference(upstream,expected())


def test_unknown_requirement_is_not_laundered_by_explicit_caller_data():
    need=expected();need['evidence_class']='UNKNOWN'
    with pytest.raises(ContractRefused,match='REVIEW_REQUIRED'):
        bind_receipt_reference({'source_ref':expected()},need)

import hashlib
import json
import socket
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workbench import CatalystWorkbench
from catalyst_platform.plugin_composition import PluginCompositionError
from examples.composition_contract_pilot import WikiServiceBinding, compose_pilot
from tests.test_p0_admission_identity import _recorder


def fixture(tmp_path, backend):
    sources=tmp_path/'sources';sources.mkdir()
    source=sources/'receipt.md'
    source.write_text('# Synthetic receipt\nRule: Payment receipt receipt-test covers synthetic payment only.\n',encoding='utf-8')
    wiki=ProjectWiki(tmp_path/'store',[sources],enterprise_id='synthetic',project_id='pilot',backend=backend)
    staged=wiki.stage_markdown(source)
    need={**expected(),'scope_id':wiki.scope_id,'source_id':staged['source_id'],'source_revision':staged['revision'],
          'span_sha256':hashlib.sha256(source.read_text(encoding='utf-8').splitlines()[1].encode('utf-8')).hexdigest()}
    app=CatalystWorkbench(tmp_path/'app',[sources],enterprise_source_allowlist={'synthetic':[sources]})
    return app,wiki,need,source


def invoke(session,cap,parameters,label):
    recorder=_recorder(session.app.workspace,label)
    run=session.invoke(cap,'1.0.0',parameters,recorder=recorder)
    before=recorder.store.inspect_run(recorder.run_id)['events']
    recorder.finish(run.result.status,model_calls=sum(e['event_type']=='llm.request.started' for e in before),external_calls=0)
    trace=recorder.store.inspect_run(recorder.run_id)
    return run.result,trace


@pytest.mark.parametrize('backend',['json','sqlite'])
def test_same_consumer_two_real_storage_adapters_and_two_runtime_actions(tmp_path,backend):
    app,wiki,need,source=fixture(tmp_path,backend)
    composer,tools,releases=compose_pilot(app,WikiServiceBinding(wiki),need)
    semantic_before=wiki.semantic_state()
    source_before=source.read_bytes()
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    try:
        first,t1=invoke(session,'pilot_reference_lookup',{'query':'Payment receipt'},'lookup-'+backend)
        assert first.status=='success',first.to_dict()
        params=bind_receipt_reference(first.output,need)
        second,t2=invoke(session,'pilot_evidence_read',params,'read-'+backend)
        assert second.status=='success',second.to_dict()
        assert second.output['content']==source_before.decode()
        assert second.output['business_quality']=='NOT_EVALUATED'
        for trace,cap in [(t1,'pilot_reference_lookup'),(t2,'pilot_evidence_read')]:
            starts=[e for e in trace['events'] if e['event_type']=='tool.execution.started']
            assert len(starts)==1 and starts[0]['capability_id']==cap
            assert any(e['event_type']=='authorization.decided' for e in trace['events'])
            model_events=[e for e in trace['events'] if e['event_type']=='llm.request.started']
        assert model_events and all(e['provider_id']=='local-single-tool-provider' for e in model_events)
        assert [t.calls for t in tools]==[1,1]
        assert composer.active_plugins==('pilot-wiki','pilot-actions')
        assert not hasattr(composer.service('pilot.wiki.read'),'invoke')
    finally:
        composer.close()
    assert releases==['actions','service'] and all(t.closed for t in tools)
    receipt={'kind':'SYNTHETIC_OFFLINE_CONTRACT_PROOF_NOT_MODEL_OUTPUT','backend':backend,
             'source_revision':need['source_revision'],'reference_sha256':hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest(),
             'lookup':first.to_dict(),'read':second.to_dict(),'r4_lookup':t1,'r4_read':t2,
             'release_order':releases,'semantic_quality':'NOT_EVALUATED','external_api_requests':0}
    (tmp_path/'COMPOSITION_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    assert source.read_bytes()==source_before and wiki.semantic_state()==semantic_before
    assert wiki.search('Payment receipt')['status']=='FOUND'
    refused=session.invoke('pilot_evidence_read','1.0.0',{'receipt_ref':need})
    assert refused.result.error['code']=='capability_not_found'


@pytest.mark.parametrize('bad_service',[WikiServiceBinding(object()),WikiServiceBinding(object(),'2')])
def test_incompatible_service_rejected_before_action_registration(tmp_path,bad_service):
    app,wiki,need,source=fixture(tmp_path,'json')
    with pytest.raises(ContractRefused):compose_pilot(app,bad_service,need)
    assert app._catalog.get('pilot_reference_lookup','1.0.0') is None


def test_cross_scope_service_cannot_be_assembled(tmp_path):
    app,wiki,need,_=fixture(tmp_path,'json')
    with pytest.raises(ContractRefused,match='SERVICE_SCOPE_MISMATCH'):
        compose_pilot(app,WikiServiceBinding(wiki),{**need,'scope_id':'enterprise:other'})


@pytest.mark.parametrize('fault',['wrong_object','unknown','wrong_revision','wrong_scope','extra_authority','missing_reference'])
def test_bypassing_mapper_still_refused_by_actual_consumer(tmp_path,fault):
    app,wiki,need,_=fixture(tmp_path,'json')
    composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    ref=deepcopy(need)
    if fault=='wrong_object':ref['object_type']='service_application'
    elif fault=='unknown':ref['evidence_class']='UNKNOWN'
    elif fault=='wrong_revision':ref['source_revision']='b'*64
    elif fault=='wrong_scope':ref['scope_id']='other'
    elif fault=='extra_authority':ref['owner_approved']=True
    elif fault=='missing_reference':ref.pop('object_id')
    try:
        result,trace=invoke(session,'pilot_evidence_read',{'receipt_ref':ref},'deny-'+fault)
        assert result.status=='failure'
        assert not any(e['event_type']=='semantic.version.activated' for e in trace['events'])
        assert wiki.semantic_state()['active_version_id'] is None
    finally:composer.close()


def test_current_source_change_is_detected_at_consumption(tmp_path):
    app,wiki,need,source=fixture(tmp_path,'sqlite')
    composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
    source.write_text('Changed synthetic source.\n',encoding='utf-8')
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    try:
        result,_=invoke(session,'pilot_evidence_read',{'receipt_ref':need},'source-change')
        assert result.status=='failure' and 'SOURCE_CHANGED' in str(result.to_dict())
    finally:composer.close()


def test_original_runtime_scope_policy_denies_before_tool(tmp_path):
    app,wiki,need,_=fixture(tmp_path,'json')
    composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
    session=app.new_session(domain={'id':'local'},enterprise={'id':'not-authorized'})
    try:
        result,trace=invoke(session,'pilot_evidence_read',{'receipt_ref':need},'scope-deny')
        assert result.status=='failure' and tools[1].calls==0
        assert any(e['event_type']=='tool.execution.denied' for e in trace['events'])
    finally:composer.close()


def test_failure_registering_second_action_does_not_leave_first_visible(tmp_path,monkeypatch):
    app,wiki,need,_=fixture(tmp_path,'json')
    original=app.register_capability
    def register(descriptor,**kwargs):
        if descriptor.id=='pilot_evidence_read':raise RuntimeError('synthetic registration failure')
        return original(descriptor,**kwargs)
    monkeypatch.setattr(app,'register_capability',register)
    with pytest.raises(RuntimeError,match='synthetic registration failure'):
        compose_pilot(app,WikiServiceBinding(wiki),need)
    assert app._catalog.get('pilot_reference_lookup','1.0.0') is None


@pytest.fixture(autouse=True)
def offline_network_fence(monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('OFFLINE_CONTRACT_PILOT_NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket.socket,'connect_ex',forbidden)


def test_json_sqlite_replacement_preserves_the_same_consumer_payload(tmp_path):
    outputs=[]
    for backend in ('json','sqlite'):
        base=tmp_path/backend;base.mkdir()
        app,wiki,need,source=fixture(base,backend)
        composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
        try:
            session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
            first,_=invoke(session,'pilot_reference_lookup',{'query':'Payment receipt'},'replace-lookup-'+backend)
            params=bind_receipt_reference(first.output,need)
            second,_=invoke(session,'pilot_evidence_read',params,'replace-read-'+backend)
            assert first.status==second.status=='success'
            outputs.append((first.output,second.output))
        finally:composer.close()
    assert outputs[0]==outputs[1]


def test_service_with_methods_but_without_scoped_identity_is_rejected():
    class IncompleteService:
        def search(self,query):return {}
        def source_snapshot(self,source_id):return {}
    with pytest.raises(ContractRefused,match='SERVICE_INTERFACE_MISSING'):
        WikiServiceBinding(IncompleteService()).validate_for_consumer()


def test_common_descriptor_preserves_typed_profiles_and_non_executable_agent():
    from pathlib import Path
    draft=json.loads((Path(__file__).resolve().parents[1]/'examples/composition_contract_v0.json').read_text(encoding='utf-8'))
    assert draft['status']=='DRAFT_NOT_INSTALLABLE_NOT_PLATFORM_STANDARD'
    assert {r['kind'] for r in draft['records']}=={'service','action','method','agent'}
    assert len({r['asset_ref'] for r in draft['records']})==4
    assert all(r['scope_authority']=='DESCRIPTOR_DOES_NOT_GRANT_EXECUTION_OR_EGRESS' for r in draft['records'])
    agent=next(r for r in draft['records'] if r['kind']=='agent')
    assert agent['qualification']==agent['implementation_ref']=='NOT_IMPLEMENTED'
    assert draft['recipe']['automatic_activation'] is False
    assert draft['harvest']['runtime_package_created'] is False


def test_declared_source_span_must_match_the_actual_read_content(tmp_path):
    app,wiki,need,_=fixture(tmp_path,'json')
    need['span_sha256']='f'*64
    composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    try:
        result,_=invoke(session,'pilot_evidence_read',{'receipt_ref':need},'bad-span')
        assert result.status=='failure' and 'SOURCE_SPAN_MISMATCH' in str(result.to_dict())
    finally:composer.close()


def test_original_runtime_rejects_action_output_schema_violation(tmp_path,monkeypatch):
    from agent_runtime.contracts import Success
    app,wiki,need,_=fixture(tmp_path,'json')
    composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
    monkeypatch.setattr(tools[0],'invoke',lambda parameters,context:Success({'source_ref':'not-a-reference'}))
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    try:
        result,_=invoke(session,'pilot_reference_lookup',{'query':'Payment receipt'},'invalid-output')
        assert result.status=='failure'
    finally:composer.close()


def test_r4_distinguishes_local_provider_protocol_turns_from_paid_dispatch(tmp_path):
    app,wiki,need,_=fixture(tmp_path,'json')
    composer,tools,_=compose_pilot(app,WikiServiceBinding(wiki),need)
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    try:
        result,trace=invoke(session,'pilot_reference_lookup',{'query':'Payment receipt'},'local-provider-accounting')
        starts=[e for e in trace['events'] if e['event_type']=='llm.request.started']
        terminal=next(e for e in trace['events'] if e['event_type']=='request.terminal')
        assert starts and terminal.get('model_calls')==len(starts)
        assert terminal.get('external_calls')==0
    finally:composer.close()
