"""Offline capacity and complete-path controls, not model quality results."""
import json
from pathlib import Path
import uuid
import pytest
from catalyst_platform.project_understand import ProjectAnalysisContext, ProjectUnderstandingRequest, EXACT_ACTIONS, run_project_analysis
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore
from tests.test_workspace_model_settings import configuration, packet
from tests.project_understand.test_project_runtime import offline

OBJECTIVE='分析这个 Skill 的适用范围、方法步骤、依赖和限制；列出可复用边界与尚缺证据，不运行源码。'

def prepare(tmp_path):
    root=Path(__file__).resolve().parents[3]/'sources/penguin'
    if not root.exists():pytest.skip('Fixed public corpus unavailable; no substitute')
    host=WorkspaceUserSession(tmp_path/'workspace');host.app._project_source_roots=(root.resolve(),)
    package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0'
    found=host.app.components.discover(package);host.app.components.admit(package,found['package_sha256']);host.app.components.activate('project-understand','0.1.0')
    rec=RunRecorder(JsonlTraceStore(host.workspace),run_id='run_'+uuid.uuid4().hex,request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex);rec.start(request_kind='offline_capacity_preflight')
    return host,root,rec

def test_repeat_inspect_references_prior_evidence_without_retransmitting_quotes(tmp_path,offline):
    host,root,rec=prepare(tmp_path)
    with host.app.components.acquire_method('project-understand') as method:
        ctx=ProjectAnalysisContext(host.session,ProjectUnderstandingRequest(rec.request_id,OBJECTIVE,'skill',2),root,method,rec)
        sid=next(r['source_id'] for r in ctx.manifest if r['relative_path'].endswith('agent-initialization/SKILL.md'))
        first=ctx.disclose(ctx.execute('project_inspect',{'source_ids':[sid],'query':'purpose'}))
        second=ctx.disclose(ctx.execute('project_inspect',{'source_ids':[sid],'query':'different question'}))
        assert first['evidence']
        assert second['evidence']==[]
        assert set(second['reused_evidence_ids'])=={e['evidence_id'] for e in first['evidence']}
        assert 'project_expand_evidence' in second['next_action_hint']
        assert all(e in ctx.evidence for e in first['evidence'])
        assert ctx.source_reads and second['source_reads']==first['source_reads']
    rec.finish('success')

@pytest.mark.parametrize('with_claim,input_limit',[(False,32000),(True,32000),(True,64000)],ids=['unresolved-control','source-claim-capacity-probe','owner-64000-source-claim'])
def test_real_two_turn_replay_then_controlled_submission_and_final_under_same_p0(tmp_path,offline,monkeypatch,with_claim,input_limit):
    host,root,rec=prepare(tmp_path)
    request=ProjectUnderstandingRequest(rec.request_id,OBJECTIVE,'skill',2)
    original=json.loads((Path(__file__).resolve().parents[1]/'fixtures/project_tools/context_growth_responses.json').read_text(encoding='utf-8'))['responses']
    calls=[]
    def transport(url,headers,body):
        wire=json.loads(body);calls.append(wire)
        # Actual Provider sends only after existing P0 check; no raised limits.
        if len(calls)<=2:
            response=original[len(calls)-1];r=packet();r['choices'][0].update(finish_reason=response['finish_reason'],message={'role':'assistant','content':response['content'],'tool_calls':[{'id':c['id'],'type':'function','function':{'name':c['name'],'arguments':c['arguments']}} for c in response['tool_calls']]});return 200,r
        if len(calls)==3:
            observed=[json.loads(m['content']) for m in wire['messages'] if m['role']=='tool']
            refs={e['evidence_id']:e for x in observed for e in x.get('evidence',[])}
            assert refs
            # This is a deliberately unresolved software control, not a synthetic semantic success.
            value=dict(schema_version='project-understanding.v1',objective=OBJECTIVE,object_type='skill',requested_depth=2,achieved_depth=1,analysis_finished=True,decision_readiness='NEEDS_EVIDENCE',questions=[dict(question_id=q,critical=True,status='EXPLICITLY_UNRESOLVED',claim_ids=[]) for q in request.critical_questions],claims=[],dependencies=[],reuse_suggestions=[],unknowns=['Offline control; no semantic judgement'],coverage={'read_source_ids':observed[-1]['source_reads'] and [x['source_id'] for x in observed[-1]['source_reads']],'unread_source_ids':observed[-1]['unread_source_ids']})
            if with_claim:
                value['claims']=[dict(claim_id='offline-source-quote-'+str(i),text=e['quote'],evidence_ids=[e['evidence_id']],conditions=[],exceptions=[],support_mode='SOURCE_DIRECT') for i,e in enumerate(list(refs.values())[:(4 if input_limit==64000 else 1)])]
            name=next(t['function']['name'] for t in wire['tools'] if t['function']['description'].startswith('project_submit_analysis:'))
            r=packet();r['choices'][0].update(finish_reason='tool_calls',message={'role':'assistant','content':None,'tool_calls':[{'id':'offline-submit','type':'function','function':{'name':name,'arguments':json.dumps({'query':json.dumps(value,ensure_ascii=False)},ensure_ascii=False)}}]});return 200,r
        assert len(calls)==4
        return 200,packet('Offline submission completed; independent review pending.')
    extra={}
    if input_limit==64000:
        from tests.project_live.test_capacity_scope import qualification
        extra['qualification_path']=qualification(tmp_path,64000)
    host.settings=WorkspaceSettings(host.app,transport=transport,**extra);config=configuration();config.update(max_requests=4,max_output_tokens=4096)
    if input_limit==64000:
        from catalyst_platform.project_understand import digest,source_manifest
        from datetime import datetime,timedelta,timezone
        from catalyst_platform.components import discover_local_component
        package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0'
        scope=dict(version=1,scope_id='OFFLINE_OWNER_64000',source_id='fixed-public-skill',source_manifest_sha256=digest(source_manifest(root)),method_sha256=discover_local_component(package).package_sha256,objective=OBJECTIVE,max_depth=2,provider_id='deepseek',model='deepseek-flash',max_requests=4,budget_cny='0.643072',max_output_tokens=4096,input_token_limit=64000,expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),owner_approval='EXPLICIT_LOCAL_OWNER')
        host._project_live_scope=scope;host.settings.project_live_scope=scope;config['budget_cny']='0.643072'
    host.settings.configure(config)
    from catalyst_platform.llm_controls import TaskBudget
    from dataclasses import asdict
    original_prepare=TaskBudget.prepare
    def audit_prepare(self,request):
        try:return original_prepare(self,request)
        finally:
            (tmp_path/('model-request-'+str(len(calls)+1)+'.json')).write_text(json.dumps(asdict(request),ensure_ascii=False),encoding='utf-8')
    monkeypatch.setattr(TaskBudget,'prepare',audit_prepare)
    if with_claim and input_limit==32000:
        from catalyst_platform.llm_controls import input_token_envelope
        from catalyst_platform.project_understand import ProjectAnalysisError
        audited=lambda: input_token_envelope((tmp_path/'model-request-4.json').read_text(encoding='utf-8'))
        try:
            run_project_analysis(host.session,request,root,provider=host.settings.provider,recorder=rec)
        except ProjectAnalysisError as failed:
            # A refusal must come from the declared input limit, not from a size accident.
            assert failed.value.code=='llm_input_limit'
            assert len(calls)==3  # Fourth request refused before transport, not retried.
            assert host.settings.provider.budget_snapshot['attempts']==3
            assert failed.value.lifecycle=={'handle_released':False,'method_lease_retained':True}
            assert audited()>32000
            rec.finish('failure')
            return
        # Admitted only when the request actually fits the same declared limit.
        assert len(calls)==4
        assert audited()<=32000
        rec.finish('success')
        return
    if input_limit==64000:
        outer=host.analyze_project({'root':root,'object_type':'skill'},OBJECTIVE,2,rec)
        assert outer['status']=='success',outer
        out=outer['result']['output']['project_analysis']
        capture=json.loads(Path(outer['live_receipt']['capture_path']).read_text(encoding='utf-8'))
        assert len(capture['records'])==4 and all(r['dispatched'] for r in capture['records'])
        assert 'OFFLINE-TEST-KEY' not in json.dumps(capture)
        assert host.settings.task.input_token_limit==64000
    else:
        out=run_project_analysis(host.session,request,root,provider=host.settings.provider,recorder=rec);rec.finish('success')
    assert len(calls)==4
    assert out['lifecycle']['handle_released'] and not out['lifecycle']['method_lease_retained']
    assert out['tool_executions']=={'project_inspect':4,'project_expand_evidence':0,'project_submit_analysis':1}
    assert out['semantic_quality']=='NOT_EVALUATED' and out['evaluation_status']=='PENDING_INDEPENDENT_REVIEW'
    assert out['analysis']['decision_readiness']=='NEEDS_EVIDENCE'
    assert len(out['source_reads'])==2 and len(out['source_manifest'])==5
    rows=host.settings.ledger.read();assert sum(r['event']=='RESERVED_BEFORE_SEND' for r in rows)==4
    from catalyst_platform.project_understand_evaluation import project_grader
    gold={'basis':'INDEPENDENT_SOURCE_IDENTITY_ONLY','sources':[dict(source_id=r['source_id'],sha256=r['sha256'],text=(root/r['relative_path']).read_text(encoding='utf-8-sig')) for r in out['source_manifest']],'critical_question_ids':list(request.critical_questions)}
    grade=project_grader(out,gold)
    assert grade['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'
    assert grade['dimensions']['SOURCE_IDENTITY']['status']=='PASS'
    assert grade['dimensions']['COVERAGE_INTEGRITY']['status']=='PASS'
    assert grade['dimensions']['QUESTION_CLOSURE']['status']=='FAIL'
    assert grade['semantic_status']=='NOT_EVALUATED' and grade['formal_owner_admission'] is False
    (tmp_path/'CONTROL_RESULT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    (tmp_path/'CONTROL_GRADE.json').write_text(json.dumps(grade,ensure_ascii=False,indent=2),encoding='utf-8')
