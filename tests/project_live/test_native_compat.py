"""Protocol wiring qualification; every response here is offline replay/control."""
from pathlib import Path
import json,uuid
import pytest
from catalyst_platform.project_understand import ProjectAnalysisContext,ProjectUnderstandingRequest,EXACT_ACTIONS
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore
from tests.project_understand.test_project_runtime import setup,offline
from tests.test_workspace_model_settings import configuration,packet

def run_batch(tmp_path,mode='success'):
    session,root=setup(tmp_path);ids=[r['source_id'] for r in __import__('catalyst_platform.project_understand',fromlist=['source_manifest']).source_manifest(root)]
    calls=[]
    def transport(url,headers,body):
        request=json.loads(body);calls.append(request)
        if len(calls)==1:
            def tool(action,params,n):
                name=next(t['function']['name'] for t in request['tools'] if t['function']['description'].startswith(action+':'))
                return {'id':'batch-'+str(n),'type':'function','function':{'name':name,'arguments':json.dumps(params)}}
            params={'query':'entry','source_ids':ids[:1] if mode!='denied' else ['NOT_ADMITTED']}
            first=tool('project_inspect',params,1)
            if mode=='malformed':first['function']['arguments']='{broken'
            second=tool('project_expand_evidence',{'query':'dependency','source_ids':ids[1:]},2)
            response=packet();response['choices'][0].update(finish_reason='tool_calls',message={'role':'assistant','content':'offline batch','tool_calls':[first,second]});return 200,response
        assert len(calls)==2
        messages=[m for m in request['messages'] if m['role']=='tool']
        assert [m['tool_call_id'] for m in messages]==['batch-1','batch-2']
        return 200,packet('Offline batch completed; no analysis submitted',**({'choices':[{'index':0,'message':{'role':'assistant','content':'truncated'},'finish_reason':'length'}]} if mode=='truncated' else {}))
    session.settings=WorkspaceSettings(session.app,transport=transport);config=configuration();config['max_requests']=2;session.settings.configure(config)
    rec=RunRecorder(JsonlTraceStore(session.workspace),run_id='run_'+uuid.uuid4().hex,request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex);rec.start(request_kind='project_analysis')
    with session.app.components.acquire_method('project-understand') as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'Explain this Agent dependency','agent',2),root,method,rec)
        run=session.session.ask(ctx.request.objective,provider=session.settings.provider,execution_mode='agent',visible_capabilities=EXACT_ACTIONS,recorder=rec,project_context=ctx)
    rec.finish(run.result.status)
    return session,run,calls,JsonlTraceStore(session.workspace).inspect_run(rec.run_id)['events']

def test_project_batch_executes_each_action_once_with_original_r4_and_usage(tmp_path,offline):
    session,run,calls,events=run_batch(tmp_path)
    assert run.result.status=='success',run.result.error
    assert session.session.tool_execution_count('project_inspect')==1
    assert session.session.tool_execution_count('project_expand_evidence')==1
    assert len(calls)==2 and run.trace['model_calls']==2
    assert run.trace['token_usage']=={'input_tokens':200,'output_tokens':40}
    starts=[e for e in events if e['event_type']=='tool.execution.started']
    assert [e['capability_id'] for e in starts]==['project_inspect','project_expand_evidence']
    assert [e['tool_call_id'] for e in starts]==['batch-1','batch-2']
    assert len({e['model_call_id'] for e in starts})==1
    assert starts[0]['model_call_id'].endswith(':llm:0')
    assert any(e['event_type']=='assistant.final_answer' for e in events)
    trace_calls=[e for e in run.trace['harness_events'] if e['event_type']=='tool.call']
    assert [e['tool_call_id'] for e in trace_calls]==['batch-1','batch-2']
    assert session.session.release_completed_run(run.session_id)

@pytest.mark.parametrize('mode',['denied','malformed'])
def test_batch_failure_stops_later_siblings_without_another_model_send(tmp_path,offline,mode):
    session,run,calls,events=run_batch(tmp_path,mode)
    assert run.result.status=='failure'
    assert session.session.tool_execution_count('project_expand_evidence')==0
    assert len(calls)==1
    if mode=='malformed':
        assert session.session.tool_execution_count('project_inspect')==0
        assert run.result.error['code']=='native_tools_protocol_error'
    else:assert run.result.error['code']=='capability_failed'


def test_exact_frozen_real_two_call_response_replays_through_product(tmp_path,offline):
    from catalyst_platform.workspace_session import WorkspaceUserSession
    root=Path(__file__).resolve().parents[3]/'sources/penguin'
    if not root.exists():pytest.skip('Explicit fixed public source corpus absent; no substitute')
    original=json.loads((Path(__file__).resolve().parents[1]/'fixtures/project_tools/first_live_response.json').read_text(encoding='utf-8'))['response']
    calls=[]
    def transport(url,headers,body):
        request=json.loads(body);calls.append(request)
        if len(calls)==1:
            r=packet();r['choices'][0].update(finish_reason=original['finish_reason'],message={'role':'assistant','content':original['content'],'tool_calls':[{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':c['arguments']}} for c in original['tool_calls']]})
            return 200,r
        return 200,packet('Frozen-response replay only; no analysis submitted')
    host=WorkspaceUserSession(tmp_path/'workspace');host.app._project_source_roots=(root.resolve(),)
    package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0';c=host.app.components.discover(package);host.app.components.admit(package,c['package_sha256']);host.app.components.activate('project-understand','0.1.0')
    host.settings=WorkspaceSettings(host.app,transport=transport);config=configuration();config['max_requests']=2;host.settings.configure(config)
    rec=RunRecorder(JsonlTraceStore(host.workspace),run_id='run_'+uuid.uuid4().hex,request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex);rec.start(request_kind='frozen_response_replay')
    with host.app.components.acquire_method('project-understand') as method:
        ctx=ProjectAnalysisContext(host.session,ProjectUnderstandingRequest(rec.request_id,'分析这个 Skill 的适用范围、方法步骤、依赖和限制；列出可复用边界与尚缺证据，不运行源码。','skill',2),root,method,rec)
        run=host.session.ask(ctx.request.objective,provider=host.settings.provider,execution_mode='agent',visible_capabilities=EXACT_ACTIONS,recorder=rec,project_context=ctx)
    rec.finish(run.result.status)
    assert host.session.tool_execution_count('project_inspect')==1
    assert host.session.tool_execution_count('project_expand_evidence')==1
    assert ctx.result is None
    assert len(calls)==2 and run.result.status=='success',run.result.error
    actions=[e for e in run.trace['harness_events'] if e['event_type']=='tool.call']
    assert [e['tool_call_id'] for e in actions]==[c['id'] for c in original['tool_calls']]
    assert len(ctx.source_reads)==4


def test_received_but_invalid_final_response_is_counted_and_attributed(tmp_path,offline):
    session,run,calls,events=run_batch(tmp_path,'truncated')
    assert run.result.status=='failure' and run.result.error['code']=='native_tools_protocol_error'
    assert len(calls)==2 and run.trace['model_calls']==2
    assert run.trace['token_usage']=={'input_tokens':200,'output_tokens':40}
    assert len([e for e in events if e['event_type']=='llm.response.received'])==2


def test_policy_deny_keeps_original_call_identity_without_execution(tmp_path,offline,monkeypatch):
    import catalyst_platform.workbench as workbench
    from agent_runtime.contracts import Deny
    original=workbench._ReadOnlyAskPolicy.check_action
    denied_id=workbench.CapabilityCatalog.internal_key('project_inspect','1.0.0')
    def policy(self,action,state):
        if action.capability_id==denied_id:return Deny('Explicit offline policy deny')
        return original(self,action,state)
    monkeypatch.setattr(workbench._ReadOnlyAskPolicy,'check_action',policy)
    session,run,calls,events=run_batch(tmp_path)
    assert run.result.status=='failure' and run.result.error['code']=='permission_denied'
    assert len(calls)==1 and session.session.tool_execution_count('project_inspect')==0 and session.session.tool_execution_count('project_expand_evidence')==0
    actions=[e for e in run.trace['harness_events'] if e['event_type']=='tool.call']
    assert len(actions)==1 and actions[0]['tool_call_id']=='batch-1'
    assert actions[0]['model_call_id'].endswith(':llm:0')
    denial=next(e for e in events if e['event_type']=='tool.execution.denied')
    assert denial['tool_call_id']=='batch-1' and denial['model_call_id'].endswith(':llm:0')
