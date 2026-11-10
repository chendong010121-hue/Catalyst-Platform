"""Public transport seam tests. Synthetic only; socket connects are forbidden."""
import json
import socket
import threading

import pytest

from agent_runtime.contracts import Message, ModelRequest
from agent_runtime.errors import ModelProviderError
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from agent_runtime.providers.openai_compatible import OpenAICompatibleModelProvider
from catalyst_platform.llm_controls import ModelTask, ModelControlError
from catalyst_platform.llm_provider import configured_model_provider, ModelProviderConfigurationError
from tests.test_workspace_model_settings import packet


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def deny(*a,**kw):raise AssertionError('ZERO_API_TRANSPORT_SEAM_NETWORK_DENIED')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket.socket,'connect_ex',deny)


@pytest.fixture(params=['deepseek','openai-compatible'])
def adapter(request):
    def build(transport,guard=None):
        options=dict(api_key='SYNTHETIC-NOT-A-REAL-KEY',model='deepseek-flash',
                     base_url='https://api.deepseek.com',transport=transport)
        if guard is not None:options['transport_guard']=guard
        cls=DeepSeekModelProvider if request.param=='deepseek' else OpenAICompatibleModelProvider
        return cls(**options)
    return build


def request():return ModelRequest(messages=[Message('user','offline contract sample')])


def test_legacy_transport_without_guard_is_unchanged(adapter):
    calls=[]
    provider=adapter(lambda *args:(calls.append(args) or (200,packet())))
    assert provider.request(request()).content and len(calls)==1


@pytest.mark.parametrize('envelope_size',[2,3])
def test_guard_surrounds_exact_original_transport(adapter,envelope_size):
    events=[]; captured={}
    raw=(200,packet(),{'x-request-id':'synthetic'})[:envelope_size]
    def transport(url,headers,body):
        events.append('send');captured.update(url=url,headers=dict(headers),body=body)
        return raw
    def guard(send,url,headers,body):
        events.append('reserve')
        with pytest.raises(TypeError):headers['Authorization']='changed'
        result=send()
        assert result is raw and captured==dict(url=url,headers=dict(headers),body=body)
        events.append('settle');return result
    provider=adapter(transport,guard)
    provider.set_external_call_observer(lambda:events.append('protocol_attempt'))
    assert provider.request(request()).content
    assert events==['protocol_attempt','reserve','send','settle']


def test_refused_reservation_never_touches_transport(adapter):
    calls=[]
    def guard(*args):raise ValueError('synthetic reservation rejected')
    with pytest.raises(ModelProviderError):adapter(lambda *a:calls.append(a),guard).request(request())
    assert calls==[]


@pytest.mark.parametrize('fault',['no_send','replace_result','swallow_error','swallow_duplicate','retry_error'])
def test_guard_cannot_invent_success_or_repeat_send(adapter,fault):
    calls=[]
    def transport(*args):
        calls.append(args)
        if fault in {'swallow_error','retry_error'}:raise TimeoutError('synthetic timeout')
        return 200,packet()
    def guard(send,*args):
        if fault=='no_send':return 200,packet()
        if fault=='replace_result':send();return 200,packet()
        if fault=='swallow_error':
            try:send()
            except TimeoutError:pass
            return 200,packet()
        if fault=='swallow_duplicate':
            result=send()
            try:send()
            except ModelProviderError:pass
            return result
        try:send()
        except TimeoutError:pass
        return send()
    with pytest.raises(ModelProviderError) as failure:adapter(transport,guard).request(request())
    assert failure.value.category=='protocol'
    assert len(calls)==(0 if fault=='no_send' else 1)


@pytest.mark.parametrize('exit_kind',['return','exception','base_exception'])
def test_saved_send_expires_on_every_guard_exit(adapter,exit_kind):
    captured=[];calls=[]
    class SyntheticStop(BaseException):pass
    def guard(send,*args):
        captured.append(send)
        if exit_kind=='exception':raise ValueError('fixture')
        if exit_kind=='base_exception':raise SyntheticStop()
        return send()
    provider=adapter(lambda *a:(calls.append(a) or (200,packet())),guard)
    if exit_kind=='return':provider.request(request())
    else:
        with pytest.raises(SyntheticStop if exit_kind=='base_exception' else ModelProviderError):
            provider.request(request())
    before=len(calls)
    with pytest.raises(ModelProviderError):captured[0]()
    assert len(calls)==before


def test_send_from_foreign_thread_is_rejected_and_sticky(adapter):
    calls=[];errors=[]
    def guard(send,*args):
        def foreign():
            try:send()
            except ModelProviderError as exc:errors.append(exc)
        worker=threading.Thread(target=foreign);worker.start();worker.join(timeout=3)
        assert not worker.is_alive() and len(errors)==1
        return 200,packet()
    with pytest.raises(ModelProviderError):adapter(lambda *a:calls.append(a),guard).request(request())
    assert calls==[]


def task(provider='deepseek'):
    return ModelTask('transport-seam-fixture',provider,'deepseek-flash',2,'1',32000,1024,
                     '2','8','0.04','synthetic offline declared rates')


@pytest.mark.parametrize('provider_id',['deepseek','openai-compatible'])
def test_configured_provider_capture_and_p0_keep_same_guard_path(provider_id):
    calls=[];events=[]
    def transport(*args):calls.append(args);return 200,packet()
    def guard(send,*args):events.append('before');result=send();events.append('after');return result
    provider=configured_model_provider(provider_id=provider_id,api_key='SYNTHETIC-KEY',model='deepseek-flash',
        base_url='https://api.deepseek.com',task=task(provider_id),transport=transport,transport_guard=guard)
    with provider.capture_calls() as records:
        response=provider.request(request())
    assert len(calls)==1 and events==['before','after']
    assert len(records)==1 and records[0]['response'] is response and records[0]['dispatched']
    assert provider.external_calls==1  # Existing protocol observer, not a real API call.
    assert provider.budget_snapshot['attempts']==1 and not provider.budget_snapshot['uncertain']
    provider.cancel()
    with pytest.raises(ModelControlError):provider.request(request())
    assert len(calls)==1


def test_invalid_guard_rejected_during_configuration():
    with pytest.raises(ModelProviderConfigurationError):
        configured_model_provider(provider_id='deepseek',api_key='SYNTHETIC-KEY',model='deepseek-flash',
            base_url='https://api.deepseek.com',task=task(),transport_guard=object())


def test_workspace_assembles_guard_without_access_to_private_provider(tmp_path,monkeypatch):
    import catalyst_platform.workspace_settings as settings_module
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from catalyst_platform.workspace_settings import WorkspaceSettings
    from tests.test_workspace_model_settings import configuration,run
    calls=[];assembled=[]
    class PublicProvider:
        """Expose only the interface already used by Harness and Settings."""
        def __init__(self,inner):self.inner=inner
        def __getattr__(self,name):
            if name.startswith('_'):raise AssertionError('PRIVATE_PROVIDER_ACCESS_FORBIDDEN')
            return getattr(self.inner,name)
    original=settings_module.configured_model_provider
    def build(**kwargs):
        assert callable(kwargs.get('transport_guard'))
        assembled.append(kwargs)
        return PublicProvider(original(**kwargs))
    monkeypatch.setattr(settings_module,'configured_model_provider',build)
    session=WorkspaceUserSession(tmp_path/'workspace')
    def fake(url,headers,body):
        calls.append(1)
        rows=session.settings.ledger.read()
        assert rows[-1]['event']=='RESERVED_BEFORE_SEND'
        return 200,packet()
    session.settings=WorkspaceSettings(session.app,transport=fake)
    session.settings.configure(configuration())
    result=run(session)
    assert result['state']=='CHAT_COMPLETED' and calls==[1] and len(assembled)==1
    assert result['external_calls']==0


@pytest.mark.parametrize('fault',['success','timeout','http','bad_usage'])
def test_workspace_default_http_path_uses_original_adapter_with_guard(tmp_path,monkeypatch,fault):
    import agent_runtime.providers.deepseek as deepseek_module
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from tests.test_workspace_model_settings import configuration,run
    events=[]
    session=WorkspaceUserSession(tmp_path/'workspace')
    class FakeHTTPResponse:
        status=200
        headers={'x-request-id':'synthetic-http'}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,bound):
            assert bound==4*1024*1024+1
            return json.dumps(packet(usage=None) if fault=='bad_usage' else packet()).encode()
    def offline_opener(req,*,timeout):
        assert timeout==45 and req.full_url=='https://api.deepseek.com/chat/completions'
        rows=session.settings.ledger.read()
        assert rows[-1]['event']=='RESERVED_BEFORE_SEND'
        assert not session.settings.ledger.is_settled()
        import hashlib
        assert rows[-1]['request_sha256']==hashlib.sha256(req.data).hexdigest()
        events.append('original-http-method-entered')
        if fault=='timeout':raise TimeoutError('synthetic timeout')
        if fault=='http':
            import io,urllib.error
            raise urllib.error.HTTPError(req.full_url,401,'synthetic',{},io.BytesIO(b'{}'))
        return FakeHTTPResponse()
    monkeypatch.setattr(deepseek_module,'open_single_attempt',offline_opener)
    session.settings.configure(configuration())
    result=run(session)
    assert events==['original-http-method-entered'] and result['external_calls']==1
    # This counts the default transport branch; the socket fence proves no real API.
    rows=session.settings.ledger.read()
    assert rows[0]['run_id']==result['run_id']
    from catalyst_platform.trace_log import JsonlTraceStore
    trace=JsonlTraceStore(session.workspace).inspect_run(result['run_id'])
    event_types={event['event_type'] for event in trace['events']}
    assert 'llm.request.started' in event_types and 'result.emitted' in event_types
    assert 'OFFLINE-TEST-KEY-DO-NOT-USE' not in json.dumps(trace)
    if fault=='success':
        assert result['state']=='CHAT_COMPLETED' and rows[-1]['event']=='METERED'
        assert 'llm.response.received' in event_types
        assert session.settings.snapshot()['last_model_receipt']['provider_request_id']=='fixture-provider-response'
    else:
        assert result['state']!='CHAT_COMPLETED' and rows[-1]['event']=='FAILED_STOP'
        assert not session.settings.snapshot()['enabled']
        run(session)
        assert len(events)==1


def test_p0_rejects_before_guard_or_transport():
    calls=[]
    def guard(send,*args):calls.append('guard');return send()
    provider=configured_model_provider(provider_id='deepseek',api_key='SYNTHETIC-KEY',model='deepseek-flash',
        base_url='https://api.deepseek.com',task=task(),transport=lambda *a:calls.append('transport'),
        transport_guard=guard)
    with pytest.raises(ModelControlError):
        provider.request(ModelRequest(messages=[Message('user','fixture')],parameters={'max_tokens':8192}))
    assert calls==[] and provider.external_calls==0


def test_transport_override_is_frozen_at_scope_assembly(tmp_path):
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from catalyst_platform.workspace_settings import WorkspaceSettings
    from tests.test_workspace_model_settings import configuration,run
    session=WorkspaceUserSession(tmp_path/'workspace');calls=[]
    session.settings=WorkspaceSettings(session.app,transport=lambda *a:(calls.append('authorized') or (200,packet())))
    session.settings.configure(configuration())
    session.settings.transport_override=lambda *a:(calls.append('later-change') or (200,packet()))
    assert run(session)['state']=='CHAT_COMPLETED' and calls==['authorized']
