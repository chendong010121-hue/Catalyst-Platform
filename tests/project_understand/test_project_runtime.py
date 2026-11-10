"""Explicit fake transport over ORIGINAL Runtime/P0, not semantic-quality proof."""
from datetime import datetime,timedelta
from pathlib import Path
import json,re,socket,uuid
import pytest
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.model_qualification import load_qualification,DEFAULT_QUALIFICATION
from catalyst_platform.project_understand import run_project_analysis,ProjectUnderstandingRequest,source_manifest,ProjectAnalysisError
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore
from tests.test_workspace_model_settings import configuration,packet

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import catalyst_platform.workspace_settings as settings
    instant=load_qualification(DEFAULT_QUALIFICATION).verified_at+timedelta(seconds=1)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(settings,'datetime',Clock)
    def deny(*a,**k):raise AssertionError('PROJECT_ZERO_NETWORK')
    monkeypatch.setattr(socket.socket,'connect',deny)

def setup(tmp_path):
    session=WorkspaceUserSession(tmp_path/'workspace')
    package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0'
    c=session.app.components.discover(package)
    session.app.components.admit(package,c['package_sha256']);session.app.components.activate('project-understand','0.1.0')
    root=session.workspace/'project-inputs'/'sample';root.mkdir(parents=True)
    (root/'agent.py').write_text('from worker import run\ndef main():\n    return run()\n',encoding='utf-8')
    (root/'worker.py').write_text('def run():\n    return "fixture"\n',encoding='utf-8')
    return session,root

def script(root,*,no_submit=False):
    calls=[];source_ids=[s['source_id'] for s in source_manifest(root)]
    def exchange(url,headers,body):
        request=json.loads(body);calls.append(request)
        def tool(action,args):
            name=next(t['function']['name'] for t in request['tools'] if t['function']['description'].startswith(action+':'))
            r=packet();r['choices'][0].update(finish_reason='tool_calls',message={'role':'assistant','content':None,'tool_calls':[{'id':'fixture-'+str(len(calls)),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]});return 200,r
        if len(calls)==1:
            assert 'def main()' not in json.dumps(request)
            return tool('project_inspect',{'query':'entry','source_ids':source_ids[:1]})
        if no_submit:return 200,packet('No actual submission')
        if len(calls)==2:return tool('project_expand_evidence',{'query':'dependency','source_ids':source_ids[1:]})
        if len(calls)==3:
            previous=[json.loads(m['content']) for m in request['messages'] if m['role']=='tool']
            # Tool Runtime envelopes vary; recursively locate actual evidence, not Gold.
            def find(x):
                if isinstance(x,dict):
                    if 'evidence' in x and 'source_reads' in x:return x
                    for v in x.values():
                        r=find(v)
                        if r:return r
                if isinstance(x,list):
                    for v in x:
                        r=find(v)
                        if r:return r
            observed=find(previous[-1]);assert observed
            e=observed['evidence'][0]
            value=dict(schema_version='project-understanding.v1',objective='Explain this Agent dependency',object_type='agent',requested_depth=2,achieved_depth=1,analysis_finished=True,decision_readiness='NEEDS_EVIDENCE',
                questions=[dict(question_id='entry',critical=True,status='SUPPORTED',claim_ids=['c1']),dict(question_id='dynamic',critical=True,status='EXPLICITLY_UNRESOLVED',claim_ids=[])],
                claims=[dict(claim_id='c1',text=e['quote'],evidence_ids=[e['evidence_id']],conditions=[],exceptions=[],support_mode='SOURCE_DIRECT')],dependencies=['worker'],reuse_suggestions=[],unknowns=['Runtime not observed'],coverage=dict(read_source_ids=source_ids,unread_source_ids=[]))
            return tool('project_submit_analysis',{'query':json.dumps(value)})
        return 200,packet('Offline fixture: pending independent review')
    return calls,exchange

def execute(session,root,transport):
    session.settings=WorkspaceSettings(session.app,transport=transport)
    config=configuration();config['max_requests']=6;session.settings.configure(config)
    recorder=RunRecorder(JsonlTraceStore(session.workspace),run_id="run_"+uuid.uuid4().hex,request_id="req_"+uuid.uuid4().hex,invocation_id="inv_"+uuid.uuid4().hex);recorder.start(request_kind='project_analysis')
    request=ProjectUnderstandingRequest(recorder.request_id,'Explain this Agent dependency','agent',2,('entry','dynamic'))
    try:
        result=run_project_analysis(session.session,request,root,provider=session.settings.provider,recorder=recorder)
    except Exception:
        recorder.finish('failure');raise
    recorder.finish('success')
    return result

def test_original_runtime_performs_progressive_analysis(tmp_path):
    session,root=setup(tmp_path);calls,transport=script(root)
    out=execute(session,root,transport)
    assert out['tool_executions']=={'project_inspect':1,'project_expand_evidence':1,'project_submit_analysis':1}
    assert out['analysis']['decision_readiness']=='NEEDS_EVIDENCE'
    assert out['method']['version']=='0.1.0' and len(out['evidence'])>0
    assert out['semantic_quality']=='NOT_EVALUATED' and len(calls)==4
    rows=session.settings.ledger.read()
    assert sum(r['event']=='RESERVED_BEFORE_SEND' for r in rows)==4
    events=JsonlTraceStore(session.workspace).inspect_run(out['run_id'])['events']
    assert any(e['event_type']=='tool.execution.started' and e.get('capability_id')=='project_expand_evidence' for e in events)

def test_answer_without_submission_is_not_analysis_success(tmp_path):
    session,root=setup(tmp_path);calls,transport=script(root,no_submit=True)
    with pytest.raises(ProjectAnalysisError,match='not_submitted'):execute(session,root,transport)
    assert len(calls)==2


def test_project_tools_are_opt_in_and_owned_by_existing_plugin(tmp_path):
    from catalyst_platform.project_understand import ACTIONS
    session,root=setup(tmp_path)
    catalog=session.app._catalog
    assert not set(ACTIONS)&{d.id for d in catalog.registry.list()}
    calls,transport=script(root)
    execute(session,root,transport)
    assert set(ACTIONS)<={d.id for d in catalog.registry.list()}
    session.app.plugins.unload('understand')
    assert all(not catalog.is_active(action,'1.0.0') for action in ACTIONS)
    assert session.app.plugins.service('understand.port') is None
