"""Owner-bound one-shot project scope; fake-only tests."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from types import SimpleNamespace
from pathlib import Path
import pytest
from catalyst_platform.project_understand import digest,source_manifest,validate_live_project_scope,consume_live_project_scope
from catalyst_platform.workbench import CatalystWorkbench

def setup(tmp_path):
    app=CatalystWorkbench(tmp_path/'workspace',[tmp_path/'workspace/inputs'])
    root=tmp_path/'source';root.mkdir();(root/'SKILL.md').write_text('# Public fixture',encoding='utf-8')
    scope={'scope_id':'PROJECT_TEST_01','source_id':'public-skill','source_manifest_sha256':digest(source_manifest(root)),'method_sha256':'a'*64,'objective':'Inspect Skill dependencies','max_depth':2,'provider_id':'deepseek','model':'deepseek-flash','max_requests':4,'budget_cny':'0.387072','max_output_tokens':4096,'input_token_limit':32000,'expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'owner_approval':'EXPLICIT_LOCAL_OWNER','version':1}
    return app,root,scope

def test_scope_source_method_and_request_identity(tmp_path):
    app,root,scope=setup(tmp_path)
    assert validate_live_project_scope(scope,{'root':root,'object_type':'skill'},scope['objective'],2,method_sha256='a'*64)==scope
    for key,value in [('objective','wrong'),('method_sha256','b'*64),('source_manifest_sha256','c'*64),('max_requests',5),('budget_cny','1')]:
        bad={**scope,key:value}
        with pytest.raises(ValueError):validate_live_project_scope(bad,{'root':root,'object_type':'skill'},scope['objective'],2,method_sha256='a'*64)

def test_scope_consumption_is_persistent_one_shot(tmp_path):
    app,root,scope=setup(tmp_path)
    first=consume_live_project_scope(app,scope,'run_1','task_1')
    assert first.is_file()
    with pytest.raises(ValueError,match='already_consumed'):consume_live_project_scope(app,scope,'run_2','task_2')

def test_scope_rejects_changed_source_and_expiry(tmp_path):
    app,root,scope=setup(tmp_path);(root/'SKILL.md').write_text('changed',encoding='utf-8')
    with pytest.raises(ValueError):validate_live_project_scope(scope,{'root':root,'object_type':'skill'},scope['objective'],2,method_sha256='a'*64)
    scope['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError):validate_live_project_scope(scope,{'root':root,'object_type':'skill'},scope['objective'],2,method_sha256='a'*64)



def test_original_session_live_capture_and_one_shot_gate(tmp_path,monkeypatch):
    import json,uuid
    from datetime import datetime,timedelta
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from catalyst_platform.workspace_settings import WorkspaceSettings
    from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION,load_qualification
    from catalyst_platform.observability import RunRecorder
    from catalyst_platform.trace_log import JsonlTraceStore
    from tests.project_understand.test_project_runtime import script
    import catalyst_platform.workspace_settings as settings
    instant=load_qualification(DEFAULT_QUALIFICATION).verified_at+timedelta(seconds=1)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(settings,'datetime',Clock)
    app,root,scope=setup(tmp_path)
    (root/'worker.py').write_text('def run():\n    return "fixture"\n',encoding='utf-8')
    scope.update(objective='Explain this Agent dependency',source_manifest_sha256=digest(source_manifest(root)))
    host=WorkspaceUserSession(tmp_path/'real-session')
    host.app._project_source_roots=(root.resolve(),)
    package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0'
    found=host.app.components.discover(package);host.app.components.admit(package,found['package_sha256']);host.app.components.activate('project-understand','0.1.0')
    scope['method_sha256']=found['package_sha256']
    host._project_live_scope=scope
    calls,original=script(root)
    def send(url,headers,body):
        status,response=original(url,headers,body)
        if len(calls)==3:
            function=response['choices'][0]['message']['tool_calls'][0]['function'];args=json.loads(function['arguments']);value=json.loads(args['query'])
            from catalyst_platform.project_understand import ProjectUnderstandingRequest
            critical=ProjectUnderstandingRequest('test',scope['objective'],'agent',2).critical_questions
            value['questions']=[dict(question_id=q,critical=True,status='SUPPORTED' if i==0 else 'EXPLICITLY_UNRESOLVED',claim_ids=['c1'] if i==0 else []) for i,q in enumerate(critical)]
            args['query']=json.dumps(value);function['arguments']=json.dumps(args)
        return status,response
    host.settings=WorkspaceSettings(host.app,transport=send)
    host.settings.project_live_scope=scope
    config=dict(api_key='OFFLINE-KEY-NOT-REAL',provider_id='deepseek',model='deepseek-flash',max_requests=4,budget_cny='0.387072',max_output_tokens=4096,consent=True)
    bad={**config,'max_requests':5}
    with pytest.raises(ValueError,match='limits_fixed'):host.settings.configure(bad)
    host.settings.configure(config)
    def recorder():
        rec=RunRecorder(JsonlTraceStore(host.workspace),run_id='run_'+uuid.uuid4().hex,request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex);rec.start(request_kind='project_analysis');return rec
    result=host.analyze_project({'root':root,'object_type':'agent'},scope['objective'],2,recorder())
    assert result['status']=='success',result
    assert len(calls)==4
    capture=json.loads(Path(result['live_receipt']['capture_path']).read_text(encoding='utf-8'))
    assert len(capture['records'])==4 and all(c['response'] for c in capture['records'])
    assert 'OFFLINE-KEY-NOT-REAL' not in json.dumps(capture)
    second=host.analyze_project({'root':root,'object_type':'agent'},scope['objective'],2,recorder())
    assert second['status']=='failure' and len(calls)==4
    with pytest.raises(ValueError,match='already_consumed'):host.settings.configure(config)


def test_smaller_followup_scope_cannot_expand_original_reservation(tmp_path):
    app,root,scope=setup(tmp_path)
    scope.update(max_requests=3,budget_cny='0.290304')
    assert validate_live_project_scope(scope,{'root':root,'object_type':'skill'},scope['objective'],2,method_sha256='a'*64)
    with pytest.raises(ValueError):validate_live_project_scope({**scope,'budget_cny':'0.387072'},{'root':root,'object_type':'skill'},scope['objective'],2,method_sha256='a'*64)
