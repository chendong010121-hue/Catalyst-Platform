"""Offline HTTP product acceptance; no network model or enterprise authority."""
import base64
import json
import threading
import time
import urllib.request
import urllib.error
from contextlib import contextmanager
import pytest
from catalyst_platform.monitor import _read_saved_result, create_monitor_server


def test_result_read_retries_a_transient_file_lock(tmp_path, monkeypatch):
    path = tmp_path / "result.json"
    path.write_text('{"state":"FINISHED"}', encoding="utf-8")
    read_text = type(path).read_text
    attempts = []

    def read(candidate, *args, **kwargs):
        if candidate == path:
            attempts.append(candidate)
            if len(attempts) == 1:
                raise PermissionError("temporarily locked")
        return read_text(candidate, *args, **kwargs)

    monkeypatch.setattr(type(path), "read_text", read)
    assert _read_saved_result(path) == {"state": "FINISHED"}
    assert len(attempts) == 2

@contextmanager
def serving(workspace, runner, inputs):
    server = create_monitor_server(workspace, runner, port=0, input_root=inputs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield server, base
    finally:
        server.shutdown(); server.server_close(); thread.join(5)

def request(base, route, body=None, token=None, origin=None):
    headers = {}
    if body is not None: headers['Content-Type'] = 'application/json'
    if token: headers['X-Catalyst-CSRF'] = token
    if origin: headers['Origin'] = origin
    req = urllib.request.Request(base + route, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)

def token(base):
    return request(base, '/api/config')['csrf_token']

def upload(base, csrf, name='org.txt', content='市场部负责客户线索。'.encode()):
    return request(base, '/api/uploads', {'name':name,'data_base64':base64.b64encode(content).decode()}, csrf)['selected_file']

def result(base, run):
    for _ in range(200):
        try: return request(base, f'/api/runs/{run}/result')
        except urllib.error.HTTPError as exc:
            if exc.code != 404: raise
        time.sleep(.02)
    raise AssertionError('run has no durable result')

def test_controlled_upload_result_restart(tmp_path):
    def runner(message, source, recorder):
        recorder.finish('success')
        return {'run_id':recorder.run_id,'status':'success','result':{'output':{'answer':'MOCK result'}}}
    with serving(tmp_path, runner, tmp_path/'inputs') as (_, base):
        csrf = token(base)
        source = upload(base, csrf)
        run = request(base, '/api/ask', {'message':'整理企业本体','selected_file':source}, csrf)['run_id']
        assert result(base, run)['result']['output']['answer'] == 'MOCK result'
    with serving(tmp_path, runner, tmp_path/'inputs') as (_, base):
        assert result(base, run)['status'] == 'success'

@pytest.mark.parametrize('attack', ['csrf','origin','path','extension','traversal','oversize'])
def test_local_input_boundary(tmp_path, attack):
    with serving(tmp_path, lambda *a: {}, tmp_path/'inputs') as (_, base):
        csrf=token(base)
        with pytest.raises(urllib.error.HTTPError) as blocked:
            if attack=='csrf': request(base,'/api/ask',{'message':'x'})
            elif attack=='origin': request(base,'/api/ask',{'message':'x'},csrf,'https://evil.example')
            elif attack=='path': request(base,'/api/ask',{'message':'x','selected_file':str(tmp_path/'private.txt')},csrf)
            elif attack=='extension': upload(base,csrf,'run.py')
            elif attack=='traversal': upload(base,csrf,'../org.txt')
            else: upload(base,csrf,content=b'x'*1_100_000)
        assert blocked.value.code in (400,403,413)

@pytest.mark.parametrize('backend', ['json','sqlite'])
def test_harness_candidate_and_gate(tmp_path, backend):
    from catalyst_platform.user_session import LocalUserSession, DEMO_TEXT
    runner=LocalUserSession(tmp_path, backend=backend, mode='MOCK')
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base)
        source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        output=result(base,run)
        assert output['state']=='WAITING_FOR_REVIEW', output
        assert output['mode']=='MOCK'
        assert output['candidate_id']
        assert output['error']['code']=='external_semantic_evaluation_required'
        assert output['version_id'] is None
        events=request(base,f'/api/runs/{run}')['events']
        assert any(e.get('span_name')=='plugin.understand.analyze' for e in events)
        assert any(e['event_type']=='semantic.candidate.proposed' for e in events)
        assert any(e.get('session_id')==runner.session_id for e in events)
    restored=LocalUserSession(tmp_path,backend=backend,mode='MOCK')
    assert restored.session_id==runner.session_id
    with serving(tmp_path,restored,restored.input_root) as (_,base):
        assert result(base,run)['candidate_id']==output['candidate_id']

@pytest.mark.parametrize('mode,message,code', [('BLOCKED','整理企业本体','BLOCKED_CREDENTIAL'),('MOCK','安装未知插件','UNSUPPORTED')])
def test_no_implicit_paid_or_unsupported_path(tmp_path,mode,message,code):
    from catalyst_platform.user_session import LocalUserSession
    runner=LocalUserSession(tmp_path,mode=mode)
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        run=request(base,'/api/ask',{'message':message},token(base))['run_id']
        out=result(base,run)
        assert out['error']['code']==code
        assert out['external_calls']==0


def test_cancel_real_pending_understand(tmp_path):
    from catalyst_platform.user_session import LocalUserSession, OrganizationDemoProvider, DEMO_TEXT
    entered=threading.Event(); release=threading.Event()
    class Slow(OrganizationDemoProvider):
        def request(self,request):
            entered.set(); release.wait(5)
            return super().request(request)
    runner=LocalUserSession(tmp_path,provider=Slow())
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base); source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        assert entered.wait(5)
        try:
            assert request(base,'/api/cancel',{'run_id':run},csrf)['accepted']
        finally: release.set()
        out=result(base,run)
        assert out['state']=='CANCELLED'
        assert out['candidate_id'] is None
        assert request(base,f'/api/runs/{run}')['status']=='interrupted'
        exported=request(base,f'/api/runs/{run}/export')
        assert exported['state']=='CANCELLED'
        assert exported['session_id']==runner.session_id
        assert DEMO_TEXT not in json.dumps(exported,ensure_ascii=False)
        assert not request(base,'/api/cancel',{'run_id':run},csrf)['accepted']


def test_invalid_model_visible_and_exported(tmp_path):
    from catalyst_platform.user_session import LocalUserSession, DEMO_TEXT
    from agent_runtime.contracts import ModelResponse
    class Invalid:
        model='MOCK-invalid'
        def request(self,request): return ModelResponse(content='{broken',finish_reason='stop')
    runner=LocalUserSession(tmp_path,provider=Invalid())
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base); source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        out=result(base,run)
        assert out['state']=='FAILED' and out['error']['code']=='MODEL_OUTPUT_INVALID'
        export=request(base,f'/api/runs/{run}/export')
        assert export['state']=='FAILED'
        assert any(e.get('error_code')=='MODEL_OUTPUT_INVALID' for e in export['events'])


def test_product_page_exposes_real_controls(tmp_path):
    from catalyst_platform.user_session import LocalUserSession
    runner=LocalUserSession(tmp_path)
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        page=urllib.request.urlopen(base).read().decode()
        assert 'type="file"' in page
        assert '/api/cancel' in page and '/export' in page
        assert 'MOCK' in page
        assert request(base,'/api/demo')['text']

@pytest.mark.parametrize('backend', ['json','sqlite'])
@pytest.mark.parametrize('extension', ['md','pptx'])
def test_real_document_reading_through_http(tmp_path,backend,extension):
    from pathlib import Path
    from catalyst_platform.user_session import LocalUserSession,DEMO_TEXT
    runner=LocalUserSession(tmp_path,backend=backend)
    content=(Path(__file__).parent/'fixtures/stage1/organization-v1.pptx').read_bytes() if extension=='pptx' else DEMO_TEXT.encode()
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base);source=upload(base,csrf,'demo.'+extension,content)
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        out=result(base,run)
        assert out['state']=='WAITING_FOR_REVIEW',out
        refs=out['proposal']['understanding']['evidence_refs']
        if extension=='pptx':
            assert any('table:' in row['locator'] for row in refs)
            assert any('NEEDS_VISION' in row for row in out['proposal']['understanding']['source_warnings'])
        export=request(base,f'/api/runs/{run}/export')
        assert export['candidate_id']==out['candidate_id']
        assert any(e['event_type']=='semantic.candidate.evaluated' for e in export['events'])


def test_p0_budget_denial_through_http(tmp_path,monkeypatch):
    from catalyst_platform.user_session import LocalUserSession,DEMO_TEXT
    from tests.test_api_infrastructure_p0 import provider,task
    guarded,sent=provider(monkeypatch,task(input_token_limit=200000,budget_cny='0.001'))
    runner=LocalUserSession(tmp_path,provider=guarded)
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base);source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        assert result(base,run)['error']['code']=='BUDGET_EXHAUSTED'
        assert not sent
        events=request(base,f'/api/runs/{run}/export')['events']
        assert any(e.get('error_code')=='BUDGET_EXHAUSTED' for e in events)
        assert any(e.get('attributes',{}).get('catalyst.llm.budget_cny')=='0.001' for e in events)


def test_inactive_plugin_and_duplicate_evaluation_are_not_successful_admission(tmp_path):
    from catalyst_platform.user_session import LocalUserSession,DEMO_TEXT
    from catalyst_platform.harness_plugins import UNDERSTAND_PLUGIN_ID
    runner=LocalUserSession(tmp_path)
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base);source=upload(base,csrf,content=DEMO_TEXT.encode())
        def submit():
            run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
            return result(base,run)
        first=submit();second=submit()
        assert first['version_id'] is second['version_id'] is None
        assert second['evaluation']['status'] in ('needs_review','pass')
        assert second['error'] and second['state']=='WAITING_FOR_REVIEW'
        runner.app.plugins.unload(UNDERSTAND_PLUGIN_ID)
        denied=submit()
        assert denied['error']['code']=='HARNESS_DENIED'
        assert denied['candidate_id'] is None


def test_restart_unfinished_does_not_show_success(tmp_path):
    from catalyst_platform.user_session import LocalUserSession
    from catalyst_platform.observability import RunRecorder
    from catalyst_platform.trace_log import JsonlTraceStore
    import uuid
    runner=LocalUserSession(tmp_path)
    run='run_'+uuid.uuid4().hex
    recorder=RunRecorder(JsonlTraceStore(tmp_path),run_id=run,request_id='req-crash',invocation_id='inv-crash',trace_id=uuid.uuid4().hex)
    recorder.start(request_kind='crash-probe')
    runner.app._atomic_json(runner.app.state_root/'user-results'/(run+'.json'),{'state':'COMPLETED','status':'success'})
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        out=result(base,run)
        assert out['state']=='INCOMPLETE'
        assert out['status']!='success'


def test_workspace_lease_prevents_two_writers(tmp_path):
    with serving(tmp_path,lambda *a:{},tmp_path/'inputs'):
        with pytest.raises(RuntimeError,match='already'):
            create_monitor_server(tmp_path,lambda *a:{},port=0,input_root=tmp_path/'inputs')

@pytest.mark.parametrize('backend',['json','sqlite'])
def test_separate_process_restart_keeps_session_and_candidate(tmp_path,backend):
    import subprocess,sys,os
    from catalyst_platform.user_session import DEMO_TEXT
    def launch():
        child=subprocess.Popen([sys.executable,'-u','-m','catalyst_platform','monitor','--workspace',str(tmp_path),
                                '--mode','mock','--wiki-backend',backend,'--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               text=True,encoding='utf-8',env={**os.environ,'PYTHONUTF8':'1'})
        line=child.stdout.readline()
        assert 'http://127.0.0.1:' in line,line
        return child,line.split('http://',1)[1].strip().rstrip('/')
    child,address=launch();base='http://'+address
    try:
        csrf=token(base);source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        before=result(base,run);trace=request(base,f'/api/runs/{run}/export')
    finally:
        child.terminate();child.wait(10)
    child,address=launch();base='http://'+address
    try:
        after=result(base,run)
        assert before==after
        assert trace==request(base,f'/api/runs/{run}/export')
        assert token(base)
        assert after['candidate_id'] and after['version_id'] is None
        from catalyst_platform.wiki import ProjectWiki
        cold=ProjectWiki(tmp_path,[tmp_path/'inputs'],enterprise_id='synthetic',project_id='local-ui-demo',backend=backend)
        assert after['candidate_id'] in cold.semantic_state()['candidates']
        assert cold.semantic_state()['active_version_id'] is None
    finally:
        child.terminate();child.wait(10)


def test_evaluation_rejection_is_visible_without_activation(tmp_path,monkeypatch):
    from catalyst_platform.user_session import LocalUserSession,DEMO_TEXT
    from catalyst_platform.semantic_wiki import SemanticWiki,SemanticTransitionError
    original=SemanticWiki.evaluate
    def reject(self,*args,**kwargs):
        original(self,*args,**kwargs)
        raise SemanticTransitionError('evaluation_rejected','offline independent rejection injection')
    monkeypatch.setattr(SemanticWiki,'evaluate',reject)
    runner=LocalUserSession(tmp_path)
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base);source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        out=result(base,run)
        assert out['state']=='FAILED'
        assert out['error']['code']=='EVALUATION_REJECTED'
        assert out['candidate_id'] and out['version_id'] is None
        events=request(base,f'/api/runs/{run}/export')['events']
        assert not any(e['event_type']=='semantic.version.activated' for e in events)
        assert any(e.get('error_code')=='EVALUATION_REJECTED' for e in events)


def test_history_presents_review_not_activation_success(tmp_path):
    from catalyst_platform.user_session import LocalUserSession,DEMO_TEXT
    runner=LocalUserSession(tmp_path)
    with serving(tmp_path,runner,runner.input_root) as (_,base):
        csrf=token(base);source=upload(base,csrf,content=DEMO_TEXT.encode())
        run=request(base,'/api/ask',{'message':'整理企业本体','selected_file':source},csrf)['run_id']
        result(base,run)
        row=next(r for r in request(base,'/api/runs') if r['run_id']==run)
        assert row['status']=='WAITING_FOR_REVIEW'
        assert row['session_id']==runner.session_id
