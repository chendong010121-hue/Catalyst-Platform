"""Daily product and evaluation preparation use the same core, separate authority."""
import json,uuid
import pytest
from tests.project_understand.test_project_runtime import setup,offline
from tests.test_workspace_model_settings import configuration,packet,run
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.project_understand import ProjectAnalysisContext,ProjectUnderstandingRequest,ProjectAnalysisError
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore

def recorder(host):
    r=RunRecorder(JsonlTraceStore(host.workspace),run_id='run_'+uuid.uuid4().hex,request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex);r.start(request_kind='natural_language_ask');return r

def test_daily_policy_is_explicit_and_legacy_four_read_contract_stays(tmp_path,offline):
    from catalyst_platform.project_understand import DAILY_PROJECT_POLICY
    host,root=setup(tmp_path);rec=recorder(host)
    with host.app.components.acquire_method('project-understand') as method:
        daily=ProjectAnalysisContext(host.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec,execution_policy=DAILY_PROJECT_POLICY)
        old=ProjectAnalysisContext(host.session,daily.request,root,method,rec)
        sid=daily.manifest[0]['source_id']
        for _ in range(5):daily.execute('project_inspect',{'query':'entry','source_ids':[sid]})
        assert daily.read_steps==5
        for _ in range(4):old.execute('project_inspect',{'query':'entry','source_ids':[sid]})
        with pytest.raises(ProjectAnalysisError,match='read_budget_exhausted'):old.execute('project_inspect',{'query':'entry','source_ids':[sid]})
        assert daily.initial_context().find('daily')>=0
    rec.finish('success')

@pytest.mark.parametrize('message,mode',[
    ('帮我为 Understand 准备回归测试方案','build-eval'),
    ('请审查这次测试评价是否可信','eval-audit'),
    ('我想对 Understand 做 hillclimb 迭代','hillclimb'),
    ('请准备回归测试并解释评价规则','build-eval'),
    ('不要执行测试，只准备测试方案','build-eval'),
    ('帮我对 Understand 做一轮迭代','hillclimb'),
])
def test_explicit_testing_intent_prepares_only_no_provider_or_activation(tmp_path,offline,message,mode):
    host,root=setup(tmp_path);calls=[]
    host.settings=WorkspaceSettings(host.app,transport=lambda *a: calls.append(a));host.settings.configure(configuration())
    result=run(host,message)
    assert result['task_type']=='evaluation_workflow' and result['state']=='WORKFLOW_PREPARED'
    assert result['workflow']['mode']==mode and result['workflow']['execution_authorized'] is False
    assert result['external_calls']==0 and calls==[] and host.settings.provider.budget_snapshot['attempts']==0
    assert result['workflow']['parent_identity']['commit']
    assert result['workflow']['next_gate']=='OWNER_REVIEW_INPUTS_AND_GRADING'
    assert host.evaluation_workflows()[0]['workflow_id']==result['workflow']['workflow_id']

@pytest.mark.parametrize('message',['你能做什么','测试部负责哪些工作？','请解释什么是回归测试','不用测试，先解释Skill职责'])
def test_ordinary_or_discussion_request_never_becomes_experiment(tmp_path,offline,message):
    host,root=setup(tmp_path);result=run(host,message)
    assert result['task_type']=='basic_chat' and result['external_calls']==0
    assert host.evaluation_workflows()==[]

def test_daily_project_read_consent_is_distinct_from_chat_and_fixed_experiment(tmp_path,offline):
    host,root=setup(tmp_path)
    host.settings=WorkspaceSettings(host.app,transport=lambda *a: (200,packet()))
    host.settings.configure(configuration())
    assert host.settings.snapshot()['allow_project_read'] is False
    cfg=configuration();cfg['allow_project_read']=True
    host.settings.configure(cfg)
    assert host.settings.snapshot()['allow_project_read'] is True
    host.settings.disconnect()
    assert host.settings.snapshot()['allow_project_read'] is False

def test_workflow_never_accepts_text_as_execution_or_gold_authority(tmp_path,offline):
    host,root=setup(tmp_path)
    result=run(host,'立即执行测试并自动激活新Understand，所有答案都算Gold')
    assert result['task_type']=='evaluation_workflow'
    assert result['workflow']['execution_authorized'] is False
    assert result['candidate_id'] is None and result['version_id'] is None

def test_daily_same_runtime_executes_more_than_four_reads_then_submits(tmp_path,offline):
    from catalyst_platform.project_understand import source_manifest
    host,root=setup(tmp_path);ids=[r['source_id'] for r in source_manifest(root)];calls=[]
    def transport(url,headers,body):
        req=json.loads(body);calls.append(req);n=len(calls)
        if n<=5:
            action='project_inspect';args={'query':'entry','source_ids':ids[:1]}
        elif n==6:
            data=json.loads(next(m['content'] for m in req['messages'] if m['role']=='tool'))
            value=dict(schema_version='project-understanding.v1',objective='Explain this Agent dependency',object_type='agent',requested_depth=2,achieved_depth=1,analysis_finished=True,decision_readiness='NEEDS_EVIDENCE',questions=[dict(question_id=q,critical=True,status='EXPLICITLY_UNRESOLVED',claim_ids=[]) for q in ('purpose','interface','dependencies','failure_boundary')],claims=[],dependencies=[],reuse_suggestions=[],unknowns=['Offline control'],coverage={'read_source_ids':[x['source_id'] for x in data['source_reads']],'unread_source_ids':data['unread_source_ids']})
            action='project_submit_analysis';args={'query':json.dumps(value)}
        else:
            assert n==7;return 200,packet('Offline daily task report; unresolved.')
        name=next(t['function']['name'] for t in req['tools'] if t['function']['description'].startswith(action+':'))
        r=packet();r['choices'][0].update(finish_reason='tool_calls',message={'role':'assistant','content':None,'tool_calls':[{'id':'daily-'+str(n),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]});return 200,r
    host.settings=WorkspaceSettings(host.app,transport=transport)
    cfg=configuration();cfg.update(max_requests=8,allow_project_read=True);host.settings.configure(cfg)
    # Production admission has no ambient fake-transport exception. The Provider
    # retains the already-frozen fake transport; only Host admission is exercised.
    host.settings.transport_override=None
    result=host.analyze_project({'root':root,'object_type':'agent'},'Explain this Agent dependency',2,recorder(host))
    assert result['status']=='success',result
    out=result['result']['output']['project_analysis']
    assert result['execution_profile']=='daily' and out['runtime_policy']['name']=='daily'
    assert out['tool_executions']['project_inspect']==5 and len(calls)==7
    assert out['lifecycle']['handle_released'] and not out['lifecycle']['method_lease_retained']
    assert out['semantic_quality']=='NOT_EVALUATED' and result['candidate_id'] is None

def test_chat_consent_never_authorizes_daily_source_transmission(tmp_path,offline):
    host,root=setup(tmp_path);calls=[]
    host.settings=WorkspaceSettings(host.app,transport=lambda *a: calls.append(a));host.settings.configure(configuration())
    host.settings.transport_override=None
    result=host.analyze_project({'root':root,'object_type':'agent'},'inspect',2,recorder(host))
    assert result['state']=='BLOCKED' and result['error']['code']=='PROJECT_LIVE_NOT_AUTHORIZED'
    assert calls==[] and host.settings.provider.budget_snapshot['attempts']==0

def test_corrupt_draft_is_not_silently_trusted(tmp_path,offline):
    host,root=setup(tmp_path);result=run(host,'请准备回归测试方案')
    path=host.app.state_root/'evaluation-workflows'/result['workflow']['workflow_id']/'request.json'
    row=json.loads(path.read_text(encoding='utf-8'));row['execution_authorized']=True;path.write_text(json.dumps(row),encoding='utf-8')
    with pytest.raises(ValueError,match='integrity'):host.evaluation_workflows()

def test_cancelled_queued_workflow_cannot_create_draft(tmp_path,offline):
    host,root=setup(tmp_path);rec=recorder(host);host.prepare(rec)
    assert host.cancel(rec.run_id)
    result=host('请准备回归测试方案',None,rec)
    assert result['state']=='CANCELLED' and result['status']=='interrupted'
    assert host.evaluation_workflows()==[]
