"""Zero-paid scope/control checks; all model responses are explicit fixtures."""
import hashlib
import json
import uuid
from pathlib import Path

import pytest

from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore

FAKE_KEY = 'OFFLINE-TEST-KEY-DO-NOT-USE'


def configuration(**changes):
    return dict(api_key=FAKE_KEY, provider_id='deepseek', model='deepseek-flash',
                max_requests=2, budget_cny='1', max_output_tokens=1024, consent=True, **changes)


def packet(content='我是 Catalyst，本轮只提供基础文本对话。', **changes):
    result = dict(id='fixture-provider-response', model='deepseek-flash', system_fingerprint='fixture-only',
                  choices=[dict(index=0, message=dict(role='assistant', content=content), finish_reason='stop')],
                  usage=dict(prompt_tokens=100, completion_tokens=20, total_tokens=120))
    result.update(changes)
    return result


@pytest.fixture
def local(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'workspace')
    calls = []
    def send(url, headers, body):
        calls.append(json.loads(body))
        return 200, packet()
    session.settings = WorkspaceSettings(session.app, transport=send)
    return session, calls


def run(session, message='你能做什么？'):
    r = RunRecorder(JsonlTraceStore(session.workspace), run_id='run_' + uuid.uuid4().hex,
                    request_id='req_' + uuid.uuid4().hex, invocation_id='inv_' + uuid.uuid4().hex,
                    trace_id=uuid.uuid4().hex)
    r.start(request_kind='natural_language_ask')
    return session(message, None, r)


def test_no_key_returns_grounded_local_info_without_provider(local):
    session, calls = local
    result = run(session)
    assert result['mode'] == 'LOCAL_INFO' and result['external_calls'] == 0
    assert 'Catalyst' in result['result']['output']['answer'] and calls == []


def test_configuring_does_not_dispatch_or_persist_key(local):
    session, calls = local
    state = session.settings.configure(configuration())
    assert state['enabled'] and not state['model_verified_by_api'] and calls == []
    assert FAKE_KEY not in json.dumps(state)
    assert all(FAKE_KEY not in p.read_text(encoding='utf-8') for p in session.settings.root.rglob('*.json'))


def test_actual_harness_chat_context_scope_and_receipt(local):
    session, calls = local
    session.settings.configure(configuration())
    result = run(session)
    assert result['state'] == 'CHAT_COMPLETED' and 'Catalyst' in result['result']['output']['answer']
    assert len(calls) == 1 and calls[0]['model'] == 'deepseek-flash'
    assert calls[0]['thinking'] == {'type': 'disabled'} and not calls[0].get('tools')
    assert 'Catalyst Workspace' in str(calls[0]['messages'])
    assert result['external_calls'] == 0  # injected transport is not network
    rows = session.settings.ledger.read()
    assert [r['event'] for r in rows] == ['RESERVED_BEFORE_SEND', 'METERED']
    assert rows[0]['run_id'] == result['run_id']


def test_feedback_history_and_explicit_clear(local):
    session, calls = local
    session.settings.configure(configuration())
    run(session, '第一条非敏感测试消息')
    run(session, '继续介绍')
    assert '第一条非敏感测试消息' in str(calls[1]['messages'])
    assert len(session.settings.history) == 4
    session.settings.history = []
    assert session.settings.snapshot()['history_turns'] == 0


def test_daily_chat_reopens_with_context_and_preserves_earlier_turns(local):
    session, calls = local
    connection = dict(api_key=FAKE_KEY, provider_id='deepseek', model='deepseek-flash', remember=False)
    session.settings.connect(connection)
    first = run(session, '我的演示项目叫青桐')
    assert first['mode'] == 'LIVE_CHAT'
    assert '本轮回答由 Host 通过 DeepSeek 模型 API 生成' in str(calls[-1]['messages'])
    assert first['chat']['thread_id'] == 'initial'
    transport = session.settings.transport_override
    session.settings = WorkspaceSettings(session.app, transport=transport)
    session.settings.connect(connection)
    second = run(session, '我刚才说的项目叫什么？')
    assert second['mode'] == 'LIVE_CHAT'
    assert '我的演示项目叫青桐' in str(calls[-1]['messages'])
    assert [row['run_id'] for row in session.settings.chat.recent()] == [first['run_id'], second['run_id']]
    session.settings.chat.new_thread()
    session.settings.history = []
    third = run(session, '你好')
    assert third['chat']['thread_id'] != first['chat']['thread_id']
    assert '青桐' not in str(calls[-1]['messages'])
    assert len(session.settings.chat.recent()) == 3


@pytest.mark.parametrize('field,value', [('consent',False),('model','deepseek-v3'),
    ('provider_id','other'),('max_requests',0),('budget_cny','0.001'),('max_output_tokens',10000)])
def test_invalid_scopes_do_not_dispatch(local, field, value):
    session, calls = local
    cfg=configuration();cfg[field]=value
    with pytest.raises(ValueError): session.settings.configure(cfg)
    assert calls == []


def test_request_limit_stops_without_retry(local):
    session, calls = local
    cfg=configuration();cfg['max_requests']=1
    session.settings.configure(cfg)
    assert run(session)['state'] == 'CHAT_COMPLETED'
    assert run(session)['state'] == 'BLOCKED'
    assert len(calls) == 1


def test_persistent_reservation_precedes_transport(local):
    session, _ = local
    def send(url, headers, body):
        rows=session.settings.ledger.read()
        assert rows[-1]['event']=='RESERVED_BEFORE_SEND'
        assert rows[-1]['request_sha256']==hashlib.sha256(body).hexdigest()
        return 200, packet()
    session.settings.transport_override=send
    session.settings.configure(configuration())
    assert run(session)['state']=='CHAT_COMPLETED'


def test_timeout_and_restart_keep_scope_blocked(local):
    session, calls = local
    def timeout(*args):
        calls.append('sent');raise TimeoutError('fixture')
    session.settings.transport_override=timeout
    session.settings.configure(configuration())
    assert run(session)['state']!='CHAT_COMPLETED'
    assert run(session)['state']=='BLOCKED' and calls==['sent']
    session.settings.disconnect()
    with pytest.raises(ValueError):session.settings.configure(configuration())
    restarted=WorkspaceSettings(session.app,transport=timeout)
    with pytest.raises(ValueError):restarted.configure(configuration())


def test_bad_usage_stops_and_never_silently_zeroes_cost(local):
    session, calls=local
    def send(*args):calls.append('sent');return 200,packet(usage=None)
    session.settings.transport_override=send
    session.settings.configure(configuration())
    assert run(session)['state']!='CHAT_COMPLETED'
    assert not session.settings.ledger.is_settled()
    assert session.settings.provider.budget_snapshot['uncertain'] is True


def test_profile_persists_without_auth_or_model_claims(local):
    session, calls=local
    state=session.settings.update_profile({'display_name':'小陈','workspace_name':'研发工作区'})
    assert state['profile']['display_name']=='小陈' and not state['configured']
    assert WorkspaceSettings(session.app).profile['workspace_name']=='研发工作区'
    with pytest.raises(ValueError):session.settings.update_profile({'display_name':'x','workspace_name':'x','api_key':FAKE_KEY})


def test_two_scopes_reuse_original_ledger_without_overwriting(local):
    session,_=local
    session.settings.configure(configuration());first=session.settings.ledger.path
    run(session)
    session.settings.configure(configuration());second=session.settings.ledger.path
    assert first!=second and first.exists() and not second.exists()


def test_preference_write_failure_never_activates_new_scope(local, monkeypatch):
    session, calls=local
    session.settings.configure(configuration())
    original=session.settings.provider
    def fail(*args, **kwargs):raise OSError('offline-disk-failure')
    monkeypatch.setattr(session.app,'_atomic_json',fail)
    with pytest.raises(OSError):session.settings.configure(configuration())
    assert session.settings.provider is original and calls==[]


def test_cancelled_queued_request_cannot_dispatch(local):
    import threading
    session,calls=local
    session.settings.configure(configuration())
    r=RunRecorder(JsonlTraceStore(session.workspace),run_id='run_'+uuid.uuid4().hex,
        request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex,trace_id=uuid.uuid4().hex)
    r.start(request_kind='natural_language_ask')
    session.prepare(r)
    session._execution.acquire()
    output=[]
    thread=threading.Thread(target=lambda:output.append(session('queued',None,r)))
    thread.start()
    assert session.cancel(r.run_id)
    session._execution.release();thread.join(timeout=10)
    assert not thread.is_alive() and output[0]['state']=='CANCELLED' and calls==[]


def test_blocked_host_never_configures_or_sends(tmp_path):
    session=WorkspaceUserSession(tmp_path/'blocked',mode='BLOCKED')
    with pytest.raises(ValueError,match='live_disabled_by_host'):session.settings.configure(configuration())
    assert run(session)['state']=='BLOCKED'


def test_snapshot_projects_cancel_and_durable_reservations(local):
    session,calls=local
    cfg=configuration();cfg['budget_cny']='0.10';cfg['max_output_tokens']=2048
    session.settings.configure(cfg);run(session)
    state=session.settings.snapshot()
    assert not state['enabled'] and state['stop_reason']=='DURABLE_RESERVATION_LIMIT'
    session.settings.configure(configuration());session.settings.provider.cancel()
    assert not session.settings.snapshot()['enabled']
    assert session.settings.snapshot()['stop_reason']=='SCOPE_CANCELLED_REAUTHORIZE'


def test_non_numeric_budget_is_normalized(local):
    session,calls=local
    cfg=configuration();cfg['budget_cny']='invalid'
    with pytest.raises(ValueError,match='budget_value_invalid'):session.settings.configure(cfg)
    assert calls==[]


def test_completed_runtime_and_trace_never_persist_credential(local):
    session,_=local
    session.settings.configure(configuration());run(session)
    for p in session.workspace.rglob('*'):
        if p.is_file() and p.suffix in {'.json','.jsonl'}:
            assert FAKE_KEY not in p.read_text(encoding='utf-8')


def test_http_error_is_stopped_without_retry_or_secret_echo(local):
    session,calls=local
    def unauthorized(*args):
        calls.append('sent');return 401,{'error':{'message':'invalid key '+FAKE_KEY,'type':'authentication_error'}}
    session.settings.transport_override=unauthorized
    session.settings.configure(configuration())
    result=run(session)
    assert result['state']!='CHAT_COMPLETED' and len(calls)==1
    assert FAKE_KEY not in json.dumps(result)
    assert not session.settings.snapshot()['enabled']


def test_original_http_adapter_bounds_success_response(monkeypatch):
    from agent_runtime.providers.deepseek import DeepSeekModelProvider
    from agent_runtime.errors import ModelProviderError
    import agent_runtime.providers.deepseek as module
    class HugeResponse:
        status=200
        headers={}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):
            assert n==4*1024*1024+1
            return b' '*n
    monkeypatch.setattr(module,'open_single_attempt',lambda *args,**kwargs:HugeResponse())
    provider=DeepSeekModelProvider(FAKE_KEY)
    with pytest.raises(ModelProviderError):provider._urllib_transport('https://api.deepseek.com/chat/completions',{},b'{}')
