"""Method-neutral software proof; synthetic payloads are not business Gold."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from agent_runtime.contracts import CapabilityDescriptor, Success
from catalyst_platform.plugin_composition import PluginDefinition, PluginComposer, PluginEffect
from catalyst_platform.workbench import CatalystWorkbench, CapabilityCatalog
from catalyst_platform.llm_provider import configured_model_provider
from tests.test_api_infrastructure_p0 import response, task
from tests.test_p0_admission_identity import _recorder
from tests.test_semantic_capture import capture_case


def method_case(tmp_path, method='reuse', fault=None):
    sources=tmp_path/'sources';sources.mkdir(parents=True)
    (sources/'synthetic.md').write_text('Synthetic qualification only.\n',encoding='utf-8')
    app=CatalystWorkbench(tmp_path/'workspace',[sources],enterprise_source_allowlist={'synthetic':[sources]})
    cap='capture_'+method
    class Tool:
        calls=0
        def describe(self):
            return CapabilityDescriptor(id=cap,name='Synthetic '+method,description='Read-only synthetic qualification method.',
                input_schema={'type':'object','properties':{'query':{'type':'string'}},'required':['query'],'additionalProperties':False},output_schema={'type':'object'})
        def invoke(self,parameters,context):
            self.calls+=1
            assert context.enterprise_context['id']=='synthetic'
            if fault=='schema':return Success(['invalid object output'])
            return Success({'kind':'capability_result' if method=='reuse' else 'virtual_patch_candidate',
                            'payload':{'value':'synthetic','patch':'+virtual only' if method=='rebuild' else None},
                            'authority':'TEST_ONLY','deployed':False})
    tool=Tool()
    def apply(context):
        catalog=context.require('capability.catalog')
        catalog.register(tool,capability_version='1.0.0',execution={'side_effect':'none'},
            metadata={'model_policy':{'mode':'workspace_scoped_query','max_calls':1},'llm_visibility':'explicit'})
        return PluginEffect(services={'test.capture.method':tool},revoke=lambda:catalog.deactivate(cap,'1.0.0'))
    definition=PluginDefinition(plugin_id='test-'+cap,version='0.1.0',provides=('test.capture.method',),requires=('capability.catalog',),apply=apply)
    composer=PluginComposer(definitions=(definition,),profiles={'test':(definition.plugin_id,)},host_services={'capability.catalog':app._catalog})
    composer.compose('test')
    packets=[]
    def transport(url,headers,body):
        packet=json.loads(body);packets.append(packet)
        assert len(packets)==1,'generic capture may not ask the model for a final answer'
        if fault=='timeout':raise TimeoutError('synthetic timeout')
        if fault=='no_tool':return 200,response(content='No method chosen')
        result=response(usage=fault!='usage')
        result['choices'][0]={'message':{'role':'assistant','content':None,'tool_calls':[{'id':'method-call','type':'function','function':{'name':CapabilityCatalog.internal_key('unregistered' if fault=='unknown_tool' else cap,'1.0.0'),'arguments':'{"query":"synthetic"}'}}]},'finish_reason':'tool_calls'}
        return 200,result
    provider=configured_model_provider(provider_id='deepseek',model='deepseek-flash',api_key='OFFLINE-NON-CREDENTIAL',base_url='https://api.deepseek.com',task=task(),transport=transport)
    provider.mode='offline'
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    recorder=_recorder(app.workspace,'generic-'+method)
    folder=app.workspace/'.catalyst/captures/method'
    return session,provider,recorder,folder,packets,tool,composer,cap


@pytest.mark.parametrize('method',['reuse','rebuild'])
def test_method_neutral_capture_uses_original_runtime_and_schema(tmp_path,method):
    session,provider,recorder,folder,packets,tool,composer,cap=method_case(tmp_path,method)
    try:
        result=session.capture_execution('Use the synthetic method.',provider=provider,
            visible_capabilities=((cap,'1.0.0'),),recorder=recorder,artifact_dir=folder)
        receipt=result.summary()
        assert receipt['status']=='CAPTURED' and receipt['runtime_terminal']=='success'
        assert receipt['boundary']=='AFTER_TOOL_BEFORE_FINAL_ANSWER'
        assert receipt['typed_basis']=='CAPABILITY_OUTPUT_SCHEMA' and receipt['semantic_quality']=='NOT_EVALUATED'
        assert receipt['trace']['run_id']==recorder.run_id and receipt['trace']['session_id']
        assert len(packets)==tool.calls==provider.budget_snapshot['attempts']==1
        assert result.payload()['kind']==('capability_result' if method=='reuse' else 'virtual_patch_candidate')
        assert receipt['artifacts']['payload'] and receipt['calls'][0]['response']
        assert not result.payload().get('items') and receipt['candidate_id'] is None
        assert session.tool_execution_count(cap)==1
    finally:composer.unload('test-'+cap)
    assert session.app._catalog.get(cap,'1.0.0') is None


def test_semantic_capture_is_a_thin_wrapper_over_same_entry(tmp_path,monkeypatch):
    session,provider,context,recorder,wiki,calls=capture_case(tmp_path)
    original=session.capture_execution;seen=[]
    def capture(*args,**kwargs):seen.append(kwargs['visible_capabilities']);return original(*args,**kwargs)
    monkeypatch.setattr(session,'capture_execution',capture)
    result=session.capture_enterprise_semantics('形成候选',provider=provider,proposal_context=context,
        recorder=recorder,artifact_dir=wiki.workspace/'.catalyst/captures/semantic')
    assert seen==[(('understand','1.0.0'),)]
    assert result.summary()['typed_basis']=='UNDERSTAND_TYPED_VALIDATOR'
    assert result.payload()['semantic_candidate']['items'] and result.observation()['items']
    assert len(calls)==2 and wiki.semantic_state()['candidates']=={}


@pytest.mark.parametrize('fault,status',[('timeout','MODEL_FAILURE'),('usage','MODEL_FAILURE'),('no_tool','NOT_EXECUTED'),('schema','EXECUTION_FAILURE'),('unknown_tool','EXECUTION_FAILURE')])
def test_generic_failures_never_gain_valid_payload_or_send_again(tmp_path,fault,status):
    session,provider,recorder,folder,packets,tool,composer,cap=method_case(tmp_path,fault=fault)
    result=session.capture_execution('Run test method.',provider=provider,visible_capabilities=((cap,'1.0.0'),),recorder=recorder,artifact_dir=folder)
    receipt=result.summary()
    assert receipt['status']==status and not receipt['typed_capture'] and len(packets)==1
    if fault in ('timeout','usage'):assert provider.budget_snapshot['uncertain']
    assert receipt['artifacts']['runtime_result'] and receipt['calls']
    if fault=='unknown_tool':
        assert tool.calls==0 and receipt['boundary']=='NO_METHOD_EXECUTION'
        assert receipt['execution_attempted'] is False
    if fault=='schema':assert tool.calls==1 and receipt['execution_attempted'] is True
    if fault!='timeout':assert receipt['calls'][0]['response']
    with pytest.raises(ValueError):result.payload()
    composer.unload('test-'+cap)


@pytest.mark.parametrize('fault',['outside','source_parent','source_child','reuse','case_alias','dotdot'])
def test_generic_path_scope_checks_before_dispatch(tmp_path,fault):
    session,provider,recorder,folder,packets,tool,composer,cap=method_case(tmp_path)
    if fault=='outside':folder=tmp_path/'outside'
    elif fault=='source_parent':session.app.enterprise_source_allowlist['synthetic']=(tmp_path,)
    elif fault=='source_child':session.app.enterprise_source_allowlist['synthetic']=(folder/'calls',)
    elif fault=='reuse':folder.mkdir(parents=True)
    elif fault=='case_alias':session.app.enterprise_source_allowlist['synthetic']=(Path(str(folder).upper()),)
    elif fault=='dotdot':folder=folder/'../../../../../outside'
    with pytest.raises((ValueError,OSError)):
        session.capture_execution('Run',provider=provider,visible_capabilities=((cap,'1.0.0'),),recorder=recorder,artifact_dir=folder)
    assert packets==[] and tool.calls==0
    composer.unload('test-'+cap)


def test_payload_tampering_and_interruption_are_not_success(tmp_path,monkeypatch):
    session,provider,recorder,folder,packets,tool,composer,cap=method_case(tmp_path)
    result=session.capture_execution('Run',provider=provider,visible_capabilities=((cap,'1.0.0'),),recorder=recorder,artifact_dir=folder)
    (folder/result.summary()['artifacts']['payload']['path']).write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='hash'):result.payload()
    composer.unload('test-'+cap)


def test_interruption_preserves_partial_calls_and_blocks_scope_reuse(tmp_path,monkeypatch):
    session,provider,recorder,folder,packets,tool,composer,cap=method_case(tmp_path)
    original=session.ask
    def interrupt(*args,**kwargs):original(*args,**kwargs);raise KeyboardInterrupt('test interruption')
    monkeypatch.setattr(session,'ask',interrupt)
    with pytest.raises(KeyboardInterrupt):
        session.capture_execution('Run',provider=provider,visible_capabilities=((cap,'1.0.0'),),recorder=recorder,artifact_dir=folder)
    receipt=json.loads((folder/'CAPTURE_RECEIPT.json').read_bytes())
    assert receipt['status']=='INTERRUPTED' and receipt['calls'][0]['response']
    with pytest.raises(FileExistsError):
        session.capture_execution('Run',provider=provider,visible_capabilities=((cap,'1.0.0'),),recorder=recorder,artifact_dir=folder)
    assert len(packets)==1
    composer.unload('test-'+cap)
