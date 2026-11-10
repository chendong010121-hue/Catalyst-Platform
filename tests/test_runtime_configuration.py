"""Portable runtime and scope lifetime; synthetic data and no network."""
import gc
import hashlib
import inspect
import json
import socket
import weakref
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_runtime.contracts import Message, ModelRequest
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from tests.test_workspace_model_settings import configuration, packet, run


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('RUNTIME_CONFIGURATION_ZERO_API')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)


def qualification(tmp_path, **changes):
    value = dict(schema_version=1, provider_id='deepseek', model='deepseek-flash',
        base_url='https://api.deepseek.com', served_models=['deepseek-flash','DeepSeek-V4.1-Flash-1017','deepseek-v4.1-flash-1017'],
        price_reference='https://api-docs.deepseek.com/zh-cn/quick_start/pricing/',
        verified_at='2026-10-26T00:00:00Z', valid_until='2026-10-27T00:00:00Z',
        input_cny_per_million='2', output_cny_per_million='8', cache_hit_cny_per_million='0.04',
        input_token_limit=32000, max_output_tokens=4096)
    value.update(changes)
    path = tmp_path / 'qualification.json'
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.fixture
def clock(monkeypatch):
    import catalyst_platform.workspace_settings as module
    class Clock(datetime):
        instant = datetime(2026,10,26,12,tzinfo=timezone.utc)
        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)
    monkeypatch.setattr(module, 'datetime', Clock)
    return Clock


def controlled(tmp_path, path):
    assert 'qualification_path' in inspect.signature(WorkspaceSettings).parameters
    session = WorkspaceUserSession(tmp_path / 'workspace')
    calls = []
    def send(*args):
        calls.append(1)
        return 200, packet()
    session.settings = WorkspaceSettings(session.app, transport=send, qualification_path=path)
    return session, calls


def test_default_ledger_is_packaged_exact_qualified_bytes():
    from catalyst_platform.workspace_ledger import HOST_DURABLE, HOST_DURABLE_SHA
    root = Path(__file__).resolve().parents[1]
    assert HOST_DURABLE.resolve().is_relative_to(root)
    assert hashlib.sha256(HOST_DURABLE.read_bytes()).hexdigest() == HOST_DURABLE_SHA


def test_next_day_qualification_needs_no_python_edit(tmp_path, clock):
    path = qualification(tmp_path)
    session, calls = controlled(tmp_path, path)
    state = session.settings.configure(configuration())
    assert calls == [] and state['enabled']
    assert state['qualification_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert session.settings.ledger.policy['qualification_sha256'] == state['qualification_sha256']
    assert run(session)['state'] == 'CHAT_COMPLETED' and calls == [1]


def test_qualified_rates_feed_both_original_budgets(tmp_path, clock):
    path = qualification(tmp_path, input_cny_per_million='3', output_cny_per_million='9')
    session, calls = controlled(tmp_path, path)
    state = session.settings.configure(configuration())
    assert state['budget']['reserved_per_request_cny'] == '0.105216'
    assert session.settings.ledger.policy['reserve_cny'] == '0.105216'
    assert calls == []


@pytest.mark.parametrize('changes', [
    {'provider_id':'other'}, {'model':'deepseek-v4-pro'}, {'base_url':'https://elsewhere.invalid'},
    {'price_reference':'https://untrusted.invalid'}, {'input_cny_per_million':'NaN'},
    {'output_cny_per_million':'-1'}, {'cache_hit_cny_per_million':'3'},
    {'input_token_limit':200000}, {'max_output_tokens':8192},
    {'valid_until':'2026-10-28T00:00:00Z'}, {'valid_until':'2026-10-26T00:00:00Z'},
    {'api_key':'NOT_A_CREDENTIAL_STORE'}, {'served_models':[]},
])
def test_invalid_qualification_refuses_before_scope_or_transport(tmp_path,clock,changes):
    session,calls=controlled(tmp_path,qualification(tmp_path,**changes))
    with pytest.raises(ValueError):session.settings.configure(configuration())
    assert session.settings.provider is None and calls == []
    assert not list(session.settings.root.glob('scopes/*/M6B_POLICY.json'))


@pytest.mark.parametrize('instant', [datetime(2026,10,25,12,tzinfo=timezone.utc),datetime(2026,10,27,0,tzinfo=timezone.utc)])
def test_future_and_expired_qualification_are_not_authorization(tmp_path,clock,instant):
    clock.instant=instant
    session,calls=controlled(tmp_path,qualification(tmp_path))
    with pytest.raises(ValueError):session.settings.configure(configuration())
    assert calls == []


def test_expiry_between_requests_stops_without_reservation(tmp_path,clock):
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    assert run(session)['state']=='CHAT_COMPLETED'
    clock.instant=datetime(2026,10,27,0,tzinfo=timezone.utc)
    assert not session.settings.snapshot()['enabled']
    assert run(session)['state']=='BLOCKED' and calls==[1]
    assert session.settings.ledger.usage_snapshot()['reserved_requests']==1


def test_direct_provider_cannot_bypass_qualification_expiry(tmp_path,clock):
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    provider=session.settings.provider
    clock.instant=datetime(2026,10,27,0,tzinfo=timezone.utc)
    with pytest.raises(ValueError):provider.request(ModelRequest(messages=[Message('user','offline')]))
    assert calls==[] and session.settings.ledger.usage_snapshot()['reserved_requests']==0


def test_scope_identity_does_not_follow_replaced_qualification(tmp_path,clock):
    path=qualification(tmp_path)
    session,calls=controlled(tmp_path,path)
    session.settings.configure(configuration())
    policy=session.settings.ledger.policy.copy()
    path.write_text(path.read_text()+'\n',encoding='utf-8')
    assert not session.settings.snapshot()['enabled']
    assert run(session)['state']=='BLOCKED' and calls==[]
    assert session.settings.ledger.policy==policy


def test_missing_or_duplicate_qualification_does_not_break_local_help(tmp_path,clock):
    path=tmp_path/'missing.json'
    session,calls=controlled(tmp_path,path)
    assert run(session)['mode']=='LOCAL_INFO' and calls==[]
    with pytest.raises(ValueError):session.settings.configure(configuration())
    path.write_text('{"schema_version":1,"schema_version":1}',encoding='utf-8')
    with pytest.raises(ValueError):session.settings.configure(configuration())
    assert session.settings.provider is None


def test_completed_workspace_run_releases_runtime_handle(tmp_path,clock):
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    result=run(session)
    assert result['state']=='CHAT_COMPLETED'
    assert session.session._handles=={}
    assert session.settings.provider is not None


@pytest.mark.parametrize('operation',['disconnect','reauthorize'])
def test_released_scope_closes_old_delegate_and_preserves_ledger(tmp_path,clock,operation):
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    old=session.settings.provider
    delegate=weakref.ref(old._delegate)
    assert run(session)['state']=='CHAT_COMPLETED'
    ledger=session.settings.ledger
    raw=ledger.path.read_bytes()
    if operation=='disconnect':session.settings.disconnect()
    else:session.settings.configure(configuration())
    assert old.scope_closed and old._delegate is None
    with pytest.raises(Exception,match='closed'):old.request(ModelRequest(messages=[Message('user','no reuse')]))
    gc.collect()
    assert delegate() is None and ledger.path.read_bytes()==raw and calls==[1]


def test_close_refuses_an_inflight_original_request():
    from tests.test_controlled_provider_capture import configured
    provider,_=configured()
    assert hasattr(provider,'close')
    provider._budget.lock.acquire()
    try:
        with pytest.raises(Exception,match='busy'):provider.close()
        assert provider._delegate is not None and not provider.scope_closed
    finally:provider._budget.lock.release()
    provider.close();provider.close()
    assert provider.scope_closed and provider._delegate is None


def test_served_model_declaration_cannot_admit_pro(tmp_path,clock):
    session,calls=controlled(tmp_path,qualification(tmp_path,served_models=['deepseek-flash','deepseek-v4-pro']))
    with pytest.raises(ValueError):session.settings.configure(configuration())
    assert calls==[]


def test_failed_preferences_write_closes_unpublished_provider(tmp_path,clock,monkeypatch):
    import catalyst_platform.workspace_settings as module
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    original=session.settings.provider
    created=[]
    factory=module.configured_model_provider
    def build(**kwargs):
        provider=factory(**kwargs);created.append(provider);return provider
    def fail(*args,**kwargs):raise OSError('synthetic write failure')
    monkeypatch.setattr(module,'configured_model_provider',build)
    monkeypatch.setattr(session.app,'_atomic_json',fail)
    with pytest.raises(OSError):session.settings.configure(configuration())
    assert created[0].scope_closed and created[0]._delegate is None
    assert session.settings.provider is original and not original.scope_closed and calls==[]


def test_pending_handle_is_preserved_for_existing_reconciliation(tmp_path):
    # Qualify through the actual Runtime owner, not an untyped private tuple.
    from tests.test_provider_lifecycle import pending_session
    session,result,capability=pending_session(tmp_path)
    handle=session._handles[result.session_id]
    assert not session.release_completed_session(result.session_id)
    assert session._handles[result.session_id] is handle
    assert capability.invoke_count==1


def test_capture_scope_cannot_be_closed_under_consumer():
    from tests.test_controlled_provider_capture import configured
    provider,_=configured()
    with provider.capture_calls():
        with pytest.raises(Exception,match='Capture busy'):provider.close()
        assert not provider.scope_closed
    provider.close()
    assert provider.scope_closed


def test_original_legacy_resume_does_not_opt_in_to_release(tmp_path):
    from tests.test_controlled_provider_capture import configured
    from catalyst_platform.workbench import CatalystWorkbench
    provider,calls=configured(content='ordinary fake answer')
    session=CatalystWorkbench(tmp_path/'legacy',[tmp_path]).new_session(domain={'id':'local'},enterprise={'id':'test'})
    result=session.ask('offline',provider=provider,execution_mode='agent',visible_capabilities=())
    assert result.session_id in session._handles
    count=len(calls)
    resumed=session.resume(result.session_id)
    assert resumed.result.status==result.result.status and len(calls)==count


@pytest.mark.parametrize('busy',['capture','request'])
def test_busy_old_scope_keeps_preferences_and_closes_unpublished_candidate(tmp_path,clock,monkeypatch,busy):
    from contextlib import nullcontext
    import catalyst_platform.workspace_settings as module
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    old=session.settings.provider
    original_preferences=session.settings.config_path.read_bytes()
    built=[];factory=module.configured_model_provider
    def build(**kwargs):
        provider=factory(**kwargs);built.append(provider);return provider
    monkeypatch.setattr(module,'configured_model_provider',build)
    if busy=='request':old._budget.lock.acquire()
    try:
        with old.capture_calls() if busy=='capture' else nullcontext():
            with pytest.raises(Exception,match='busy'):session.settings.configure(configuration())
    finally:
        if busy=='request':old._budget.lock.release()
    assert session.settings.config_path.read_bytes()==original_preferences
    assert session.settings.provider is old and not old.scope_closed
    assert built[0].scope_closed and calls==[]


@pytest.mark.parametrize('change',['expiry','file'])
def test_qualification_rechecked_after_durable_reservation(tmp_path,clock,monkeypatch,change):
    path=qualification(tmp_path)
    session,calls=controlled(tmp_path,path)
    session.settings.configure(configuration())
    ledger=session.settings.ledger;reserve=ledger.reserve_chat
    def reserve_and_change(*args):
        row=reserve(*args)
        if change=='expiry':clock.instant=datetime(2026,10,27,0,tzinfo=timezone.utc)
        else:path.write_text(path.read_text()+'\n',encoding='utf-8')
        return row
    monkeypatch.setattr(ledger,'reserve_chat',reserve_and_change)
    assert run(session)['state']!='CHAT_COMPLETED' and calls==[]
    assert ledger.usage_snapshot()['reserved_requests']==1 and not ledger.is_settled()


@pytest.mark.parametrize('bad',[{'max_output_tokens':127},{'input_cny_per_million':'1e999999'}])
def test_unusable_declarations_are_normalized_before_scope(tmp_path,clock,bad):
    session,calls=controlled(tmp_path,qualification(tmp_path,**bad))
    with pytest.raises(ValueError,match='model_qualification_invalid'):session.settings.configure(configuration())
    assert calls==[] and session.settings.provider is None


def test_minimum_128_output_is_usable(tmp_path,clock):
    session,calls=controlled(tmp_path,qualification(tmp_path,max_output_tokens=128))
    cfg=configuration();cfg['max_output_tokens']=128
    assert session.settings.configure(cfg)['enabled']
    assert run(session)['state']=='CHAT_COMPLETED' and calls==[1]


def test_disconnect_releases_key_reference_even_when_ledger_is_corrupt(tmp_path,clock):
    session,calls=controlled(tmp_path,qualification(tmp_path))
    session.settings.configure(configuration())
    provider=session.settings.provider;ledger=session.settings.ledger
    ledger.path.write_bytes(b'partial fixture')
    state=session.settings.disconnect()
    assert provider.scope_closed and session.settings.provider is None
    assert state['stop_reason']=='LEDGER_UNREADABLE_STOP' and not state['enabled']
    assert ledger.path.read_bytes()==b'partial fixture' and calls==[]
