"""Synthetic lifecycle proofs; no credentials, remote APIs or business truth."""
import gc
import json
import socket
import threading
import weakref
from dataclasses import replace
from datetime import datetime, timezone, timedelta

import pytest

from agent_runtime.contracts import Complete, Fail, Blocked, Continue, Goal, ReasoningResult, ModelRequest, ModelResponse, Message, StepRecord
from agent_runtime.errors import CapabilityContractError, SessionConsistencyError
from catalyst_platform.llm_controls import ModelControlError
from catalyst_platform.workbench import CatalystWorkbench, WorkbenchError
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from tests.test_workspace_model_settings import configuration, packet, run
from tests.test_unified_platform import _UncertainCapability


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **kw):raise AssertionError('ZERO_API_LIFECYCLE_NETWORK_DENIED')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket.socket,'connect_ex',deny)


class LocalProvider:
    provider_id='synthetic-lifecycle-provider'
    mode='offline'
    def __init__(self):self.calls=0
    def request(self,request):
        self.calls+=1
        return ModelResponse(content='synthetic completed answer',finish_reason='stop')


def harness(tmp_path):
    source=tmp_path/'sources';source.mkdir()
    app=CatalystWorkbench(workspace=tmp_path/'product',wiki_roots=[source])
    return app.new_session(domain={},enterprise={})


def ask(session,provider):
    return session.ask('synthetic task',provider=provider,execution_mode='agent',visible_capabilities=())


@pytest.fixture
def workspace(tmp_path):
    session=WorkspaceUserSession(tmp_path/'workspace')
    calls=[]
    def fake(*args):calls.append(1);return 200,packet()
    session.settings=WorkspaceSettings(session.app,transport=fake)
    session.settings.configure(configuration())
    return session,calls


def pending_session(tmp_path):
    source=tmp_path/'sources';source.mkdir()
    app=CatalystWorkbench(workspace=tmp_path/'pending',wiki_roots=[source])
    capability=_UncertainCapability()
    app.register_capability(capability.describe(),capability_version='1.0.0',
        execution={'side_effect':'possible'},implementation=capability)
    session=app.new_session(domain={},enterprise={'id':'synthetic',
        'allow_possible_side_effects':True,'allowed_capabilities':['uncertain_test']})
    result=session.invoke('uncertain_test','1.0.0',{},invocation_id='synthetic-pending')
    assert result.result.status=='unresolved'
    return session,result,capability


def test_generic_harness_release_is_explicit_and_does_not_revoke_shared_provider(tmp_path):
    session=harness(tmp_path);provider=LocalProvider()
    first=ask(session,provider)
    assert first.session_id in session._handles  # Generic Host behavior unchanged.
    assert session._handles[first.session_id][0].can_release_session(first.session_id)
    before=(first.trace_path.read_bytes(),(session.app.session_dir/(first.session_id+'.json')).read_bytes())
    assert session.release_completed_run(first.session_id) is True
    assert session.release_completed_run(first.session_id) is False
    assert first.session_id not in session._handles
    assert before==(first.trace_path.read_bytes(),(session.app.session_dir/(first.session_id+'.json')).read_bytes())
    with pytest.raises(WorkbenchError):session.resume(first.session_id)
    assert provider.calls==1
    assert ask(session,provider).result.status=='success' and provider.calls==2


def test_release_drops_runtime_reference_and_provider_can_be_collected(tmp_path):
    session=harness(tmp_path);provider=LocalProvider();pinned=weakref.ref(provider)
    result=ask(session,provider);runtime_ref=weakref.ref(session._handles[result.session_id][0])
    assert session.release_completed_run(result.session_id)
    del provider
    gc.collect()
    assert runtime_ref() is None and pinned() is None
    assert result.trace_path.is_file()


def test_pending_release_refused_resume_no_replay_and_reconcile_still_works(tmp_path):
    session,result,capability=pending_session(tmp_path)
    runtime=session._handles[result.session_id][0]
    assert not runtime.can_release_session(result.session_id)
    assert session.release_completed_run(result.session_id) is False
    assert session.resume(result.session_id).result.status=='unresolved' and capability.invoke_count==1
    snapshot=session.reconcile(result.session_id,result.execution_id,
        resolution={'kind':'confirmed_executed','observation':{'accepted':True}},note='synthetic independent confirmation')
    assert snapshot.pending_execution is None and capability.invoke_count==1
    session.resume(result.session_id)
    assert capability.invoke_count==1 and session.release_completed_run(result.session_id)


@pytest.mark.parametrize('fault',['json','identity','terminal_plus_pending'])
def test_invalid_snapshot_never_discards_handle(tmp_path,monkeypatch,fault):
    if fault=='terminal_plus_pending':
        session,result,_=pending_session(tmp_path)
    else:
        session=harness(tmp_path);result=ask(session,LocalProvider())
    runtime,store,*_=session._handles[result.session_id]
    snapshot=store.load(result.session_id)
    original_load=store.load
    state_path=session.app.session_dir/(result.session_id+'.json')
    frozen=state_path.read_bytes()
    if fault=='json':
        (session.app.session_dir/(result.session_id+'.json')).write_text('{',encoding='utf-8')
    else:
        corrupt=replace(snapshot,session_id='other-session') if fault=='identity' else replace(
            snapshot,history=(*snapshot.history,StepRecord(index=len(snapshot.history),decision=Complete('synthetic'))))
        monkeypatch.setattr(store,'load',lambda _sid:corrupt)
    with pytest.raises((ValueError,CapabilityContractError,SessionConsistencyError)):
        session.release_completed_run(result.session_id)
    assert session._handles[result.session_id][0] is runtime
    state_path.write_bytes(frozen)  # Restore only this new synthetic fault fixture.
    monkeypatch.setattr(store,'load',original_load)
    assert session.release_completed_run(result.session_id)==(snapshot.pending_execution is None)


def test_local_active_execution_prevents_release(tmp_path,monkeypatch):
    session=harness(tmp_path);result=ask(session,LocalProvider())
    runtime=session._handles[result.session_id][0]
    monkeypatch.setattr(runtime.control_plane.active,'get',lambda sid:'synthetic-live-execution')
    assert not runtime.can_release_session(result.session_id)
    assert session.release_completed_run(result.session_id) is False


def test_resume_busy_handle_cannot_be_released(tmp_path):
    entered=threading.Event();proceed=threading.Event();outputs=[]
    class Recovering(LocalProvider):
        def request(self,request):
            self.calls+=1
            if self.calls==1:raise RuntimeError('synthetic pre-response failure')
            entered.set();assert proceed.wait(5)
            return ModelResponse(content='recovered',finish_reason='stop')
    session=harness(tmp_path);provider=Recovering();result=ask(session,provider)
    assert not session._handles[result.session_id][0].can_release_session(result.session_id)
    assert session.release_completed_run(result.session_id) is False
    worker=threading.Thread(target=lambda:outputs.append(session.resume(result.session_id)))
    worker.start()
    try:
        assert entered.wait(5)
        with pytest.raises(WorkbenchError,match='busy'):session.release_completed_run(result.session_id)
        assert result.session_id in session._handles
    finally:
        proceed.set();worker.join(timeout=5)
    assert not worker.is_alive() and outputs[0].result.status=='success'
    assert provider.calls==2 and session.release_completed_run(result.session_id)


def test_reconcile_busy_handle_cannot_be_released(tmp_path,monkeypatch):
    session,result,capability=pending_session(tmp_path)
    runtime=session._handles[result.session_id][0]
    original=runtime.reconcile;entered=threading.Event();proceed=threading.Event();outputs=[]
    def gated(*args):
        entered.set();assert proceed.wait(5)
        return original(*args)
    monkeypatch.setattr(runtime,'reconcile',gated)
    worker=threading.Thread(target=lambda:outputs.append(session.reconcile(result.session_id,result.execution_id,
        resolution={'kind':'confirmed_executed','observation':{'accepted':True}})))
    worker.start()
    try:
        assert entered.wait(5)
        with pytest.raises(WorkbenchError,match='busy'):session.release_completed_run(result.session_id)
    finally:
        proceed.set();worker.join(timeout=5)
    assert not worker.is_alive() and outputs[0].pending_execution is None and capability.invoke_count==1


def test_resume_does_not_hold_global_handle_map_lock_against_another_run(tmp_path):
    entered=threading.Event();proceed=threading.Event();other_done=threading.Event();outputs=[]
    class Recovering(LocalProvider):
        def request(self,request):
            self.calls+=1
            if self.calls==1:raise RuntimeError('synthetic initial failure')
            entered.set();assert proceed.wait(5)
            return ModelResponse(content='synthetic recovered',finish_reason='stop')
    session=harness(tmp_path);result=ask(session,Recovering())
    resumed=threading.Thread(target=lambda:outputs.append(session.resume(result.session_id)))
    def other():
        outputs.append(ask(session,LocalProvider()));other_done.set()
    another=threading.Thread(target=other)
    resumed.start()
    try:
        assert entered.wait(3)
        another.start()
        assert other_done.wait(2), 'Unrelated run publication blocked by another session handle'
    finally:
        proceed.set();resumed.join(timeout=5)
        if another.ident is not None:another.join(timeout=5)
    assert len(outputs)==2 and not resumed.is_alive() and not another.is_alive()


def test_workspace_finishes_and_releases_only_its_terminal_handle(workspace):
    session,calls=workspace
    result=run(session)
    assert result['state']=='CHAT_COMPLETED' and calls==[1]
    assert result['lifecycle']['handle_released'] is True
    assert result['session_id'] not in session.session._handles
    assert session.settings.provider is not None  # Current authorized scope still reusable.
    assert run(session)['state']=='CHAT_COMPLETED' and calls==[1,1]


@pytest.mark.parametrize('fault',['release','cleanup_event'])
def test_cleanup_failure_never_rewrites_primary_result(workspace,monkeypatch,fault):
    session,calls=workspace
    if fault=='release':
        def fail(*args):raise OSError('synthetic cleanup failure')
        monkeypatch.setattr(session.session,'release_completed_run',fail,raising=False)
    else:
        from catalyst_platform.observability import RunRecorder
        original=RunRecorder.start_span
        def start(self,name,**fields):
            if name=='session.handle.release':raise OSError('synthetic cleanup observation failure')
            return original(self,name,**fields)
        monkeypatch.setattr(RunRecorder,'start_span',start)
    result=run(session)
    assert result['state']=='CHAT_COMPLETED' and result['status']=='success' and calls==[1]
    assert result['result']['output']['answer']
    assert result['lifecycle']['release_error_type' if fault=='release' else 'observation_error_type']=='OSError'
    assert (result['session_id'] in session.session._handles)==(fault=='release')


@pytest.mark.parametrize('ledger_fault',[False,True])
def test_disconnect_revokes_old_alias_even_when_ledger_read_fails(workspace,monkeypatch,ledger_fault):
    session,calls=workspace;old=session.settings.provider;ledger=session.settings.ledger
    policy=(ledger.root/'M6B_POLICY.json').read_bytes()
    if ledger_fault:
        def fail():raise OSError('synthetic ledger failure')
        monkeypatch.setattr(ledger,'is_settled',fail)
    state=session.settings.disconnect()
    assert old.cancelled and session.settings.provider is None and not state['enabled']
    assert session.settings.ledger is ledger and (ledger.root/'M6B_POLICY.json').read_bytes()==policy
    with pytest.raises(ModelControlError) as failure:old.request(ModelRequest(messages=[Message('user','old alias')]))
    assert failure.value.code=='llm_provider_closed' and old.scope_closed and calls==[]


def test_replaced_scope_revoked_only_after_preference_commit(workspace,monkeypatch):
    session,calls=workspace;old=session.settings.provider
    original=session.app._atomic_json
    def save(*args,**kwargs):
        assert not old.cancelled
        return original(*args,**kwargs)
    monkeypatch.setattr(session.app,'_atomic_json',save)
    session.settings.configure(configuration())
    assert old.cancelled and session.settings.provider is not old and calls==[]
    with pytest.raises(ModelControlError):old.request(ModelRequest(messages=[Message('user','revoked')]))


def test_failed_preference_save_does_not_revoke_previous_scope(workspace,monkeypatch):
    session,calls=workspace;old=session.settings.provider
    def fail(*args,**kwargs):raise OSError('synthetic write failure')
    monkeypatch.setattr(session.app,'_atomic_json',fail)
    with pytest.raises(OSError):session.settings.configure(configuration())
    assert session.settings.provider is old and not old.cancelled and calls==[]


def test_active_scope_cannot_be_disconnected(workspace):
    session,_=workspace;old=session.settings.provider
    session.settings.active_run_id='synthetic-active'
    with pytest.raises(ValueError,match='model_request_in_progress'):session.settings.disconnect()
    assert session.settings.provider is old and not old.cancelled


def test_completed_workspace_provider_collectable_after_disconnect(workspace):
    session,_=workspace;reference=weakref.ref(session.settings.provider)
    result=run(session)
    assert result['lifecycle']['handle_released']
    session.settings.disconnect();gc.collect()
    assert reference() is None
    assert session.settings.task is not None and session.settings.ledger is not None


def test_expired_price_still_refused_without_creating_provider(tmp_path,monkeypatch):
    from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION
    value=json.loads(DEFAULT_QUALIFICATION.read_bytes())
    value.update(verified_at='2000-01-01T00:00:00Z',valid_until='2000-01-01T01:00:00Z')
    path=tmp_path/'synthetic-expired.json';path.write_text(json.dumps(value),encoding='utf-8')
    settings=WorkspaceUserSession(tmp_path/'expired',qualification_path=path).settings
    with pytest.raises(ValueError,match='official_price_refresh_required'):settings.configure(configuration())
    assert settings.provider is None and settings.ledger is None


def test_compatibility_release_names_share_runtime_gate(tmp_path,monkeypatch):
    session=harness(tmp_path);result=ask(session,LocalProvider())
    runtime=session._handles[result.session_id][0]
    monkeypatch.setattr(runtime.control_plane.active,'get',lambda sid:'synthetic-live-execution')
    assert session.release_completed_session(result.session_id) is False
    assert session.release_completed_run(result.session_id) is False
    assert result.session_id in session._handles


def test_uncertain_scope_keeps_handle_and_ledger_after_disconnect(workspace,monkeypatch):
    session,calls=workspace;old=session.settings.provider;ledger=session.settings.ledger
    def fail(*args):raise ValueError('synthetic uncertain usage')
    monkeypatch.setattr(ledger,'settle',fail)
    result=run(session)
    assert result['state']!='CHAT_COMPLETED' and calls==[1]
    assert not result['lifecycle']['handle_released']
    assert result['session_id'] in session.session._handles and old.budget_snapshot['uncertain']
    frozen=ledger.path.read_bytes();scope=session.settings.task.task_id
    session.settings.disconnect()
    assert old.cancelled and session.settings.task.task_id==scope
    assert ledger.path.read_bytes()==frozen and session.settings.ledger is ledger
    with pytest.raises(ValueError):session.settings.configure(configuration())
    with pytest.raises(ModelControlError):old.request(ModelRequest(messages=[Message('user','no replay')]))
    assert calls==[1]


def test_cleanup_error_preserves_original_default_transport_attempt_and_r4(tmp_path,monkeypatch):
    import agent_runtime.providers.deepseek as module
    from catalyst_platform.trace_log import JsonlTraceStore
    session=WorkspaceUserSession(tmp_path/'default');calls=[]
    class FakeResponse:
        status=200;headers={}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,bound):return json.dumps(packet()).encode()
    def opener(*args,**kwargs):calls.append(1);return FakeResponse()
    monkeypatch.setattr(module,'open_single_attempt',opener)
    def fail(*args):raise OSError('synthetic release failure')
    monkeypatch.setattr(session.session,'release_completed_run',fail)
    session.settings.configure(configuration())
    result=run(session)
    assert result['state']=='CHAT_COMPLETED' and calls==[1] and result['external_calls']==1
    trace=JsonlTraceStore(session.workspace).inspect_run(result['run_id'])
    started=next(e for e in trace['events'] if e['event_type']=='span.started' and e['span_name']=='session.handle.release')
    ended=next(e for e in trace['events'] if e['event_type']=='span.ended' and e['span_id']==started['span_id'])
    assert ended['attributes']['error.type']=='OSError' and ended['attributes']['status']=='release_failed'
    assert 'OFFLINE-TEST-KEY-DO-NOT-USE' not in json.dumps(trace)


@pytest.mark.parametrize('decision',[Complete('synthetic done'),Fail('synthetic failed'),Blocked('synthetic owner review')])
def test_runtime_release_qualification_covers_terminal_decisions_only(tmp_path,decision):
    from agent_runtime.runtime import Runtime
    from catalyst_platform.storage import JsonFileStateStore
    class Reasoner:
        def decide(self,*args):return ReasoningResult(decision)
    class Policy:
        def should_stop(self,*args):return Continue()
    runtime=Runtime(Reasoner(),{},Policy(),JsonFileStateStore(tmp_path/'state'))
    snapshot=runtime.create(Goal('synthetic lifecycle qualification'))
    assert not runtime.can_release_session(snapshot.session_id)
    runtime.run(snapshot.session_id)
    assert runtime.can_release_session(snapshot.session_id)
