"""Zero-API contract tests; exact original engine in two physical locations."""
from pathlib import Path
import hashlib
import json
from decimal import Decimal
import shutil
import socket
import pytest

from catalyst_platform.workspace_ledger import PinnedHostLedgerFactory, LedgerFactory, WorkspaceLedger, HOST_DURABLE
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.workspace_session import WorkspaceUserSession
from tests.test_workspace_model_settings import configuration,packet,run

ORIGINAL=HOST_DURABLE  # Same qualified bytes, now shipped with Product.
QUALIFIED='e8ab364abe523e91144649bae11bdde7b32b4c2812d6c6bdee6d1a1c20444df3'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a,**kw):raise AssertionError('ZERO_API_LEDGER_TEST_NETWORK_DENIED')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket.socket,'connect_ex',deny)


@pytest.fixture(params=['original','relocated'])
def factory(request,tmp_path):
    path=ORIGINAL
    if request.param=='relocated':
        path=tmp_path/'different'/'qualified_engine.py';path.parent.mkdir();shutil.copyfile(ORIGINAL,path)
    return PinnedHostLedgerFactory(path,QUALIFIED)


def session_for(tmp_path,factory,exchange=None):
    session=WorkspaceUserSession(tmp_path/'ui',ledger_factory=factory)
    calls=[]
    def send(*args):calls.append(1);return exchange(*args) if exchange else (200,packet())
    session.settings=WorkspaceSettings(session.app,ledger_factory=factory,transport=send)
    return session,calls


def test_factory_contract_and_no_dispatch_when_configuring(tmp_path,factory):
    session,calls=session_for(tmp_path,factory)
    assert isinstance(factory,LedgerFactory)
    state=session.settings.configure(configuration())
    assert isinstance(session.settings.ledger,WorkspaceLedger)
    assert state['enabled'] and calls==[]
    usage=session.settings.ledger.usage_snapshot()
    assert usage['reserved_requests']==0 and Decimal(usage['reserved_cny'])==0 and usage['settled'] is True


def test_same_workspace_consumer_runs_through_both_locations(tmp_path,factory):
    session,calls=session_for(tmp_path,factory)
    session.settings.configure(configuration())
    result=run(session)
    assert result['state']=='CHAT_COMPLETED' and calls==[1]
    usage=session.settings.ledger.usage_snapshot()
    assert usage['settled'] and usage['reserved_requests']==1
    assert [r['event'] for r in session.settings.ledger.read()]==['RESERVED_BEFORE_SEND','METERED']


def test_fsync_reservation_is_visible_before_original_exchange(tmp_path,factory):
    session,calls=session_for(tmp_path,factory)
    def exchange(url,headers,body):
        rows=session.settings.ledger.read()
        assert rows[-1]['event']=='RESERVED_BEFORE_SEND'
        assert rows[-1]['request_sha256']==hashlib.sha256(body).hexdigest()
        assert not session.settings.ledger.is_settled()
        return 200,packet()
    session.settings.transport_override=exchange
    session.settings.configure(configuration())
    assert run(session)['state']=='CHAT_COMPLETED'


def test_missing_engine_stops_without_dispatch(tmp_path):
    factory=PinnedHostLedgerFactory(tmp_path/'absent.py',QUALIFIED)
    session,calls=session_for(tmp_path,factory)
    with pytest.raises((ValueError,OSError)):session.settings.configure(configuration())
    assert not session.settings.snapshot()['configured'] and calls==[]


def test_changed_engine_rejected_without_executing_it(tmp_path):
    path=tmp_path/'tampered.py';marker=tmp_path/'EXECUTED'
    path.write_text(f"__import__('pathlib').Path({str(marker)!r}).touch()",encoding='utf-8')
    session,calls=session_for(tmp_path,PinnedHostLedgerFactory(path,QUALIFIED))
    with pytest.raises(ValueError,match='identity'):session.settings.configure(configuration())
    assert not marker.exists() and calls==[]


def test_arbitrary_source_with_its_own_hash_is_not_qualified(tmp_path):
    path=tmp_path/'other.py';path.write_text('raise RuntimeError()',encoding='utf-8')
    with pytest.raises(ValueError,match='unqualified'):
        PinnedHostLedgerFactory(path,hashlib.sha256(path.read_bytes()).hexdigest())


def test_pending_timeout_survives_disconnect_and_factory_reopen(tmp_path,factory):
    def timeout(*a):raise TimeoutError('synthetic sent-or-unknown')
    session,calls=session_for(tmp_path,factory,timeout)
    session.settings.configure(configuration())
    assert run(session)['state']=='FAILED' and calls==[1]
    assert session.settings.snapshot()['enabled'] is False
    assert run(session)['state']=='BLOCKED' and calls==[1]
    session.settings.disconnect()
    restarted=WorkspaceSettings(session.app,ledger_factory=factory,transport=lambda *a:(200,packet()))
    with pytest.raises(ValueError):restarted.configure(configuration())
    assert restarted.snapshot()['configured'] is False


@pytest.mark.parametrize('fault',['usage','model','fingerprint'])
def test_settlement_failure_never_retries_or_refunds(tmp_path,factory,fault):
    response=packet()
    if fault=='usage':response['usage']=None
    elif fault=='model':response['model']='unapproved'
    else:response['system_fingerprint']=''
    session,calls=session_for(tmp_path,factory,lambda *a:(200,response))
    session.settings.configure(configuration())
    assert run(session)['state']!='CHAT_COMPLETED' and calls==[1]
    assert session.settings.ledger.usage_snapshot()['settled'] is False
    assert run(session)['state']=='BLOCKED' and calls==[1]


def test_request_cap_is_unchanged(tmp_path,factory):
    session,calls=session_for(tmp_path,factory)
    cfg=configuration();cfg['max_requests']=1
    session.settings.configure(cfg)
    assert run(session)['state']=='CHAT_COMPLETED'
    assert run(session)['state']=='BLOCKED' and calls==[1]


def test_consumer_uses_only_public_contract_not_legacy_rows_or_policy(tmp_path,factory):
    class OpaqueLedger:
        __slots__=('inner',)
        def __init__(self,inner):self.inner=inner
        def reserve_chat(self,*a):return self.inner.reserve_chat(*a)
        def settle(self,*a):return self.inner.settle(*a)
        def fail(self,*a):return self.inner.fail(*a)
        def is_settled(self):return self.inner.is_settled()
        def usage_snapshot(self):return self.inner.usage_snapshot()
    class AlternateFactory:
        def check_prior_scopes(self,root):return factory.check_prior_scopes(root)
        def open_scope(self,root,policy):return OpaqueLedger(factory.open_scope(root,policy))
    session,calls=session_for(tmp_path,AlternateFactory())
    state=session.settings.configure(configuration())
    assert state['enabled']
    assert not hasattr(session.settings.ledger,'read') and not hasattr(session.settings.ledger,'policy')
    assert run(session)['state']=='CHAT_COMPLETED' and calls==[1]
    assert session.settings.snapshot()['reserved_requests']==1


@pytest.mark.parametrize('fault',['policy','partial','hash'])
def test_ledger_corruption_closes_scope_without_second_exchange(tmp_path,factory,fault):
    session,calls=session_for(tmp_path,factory)
    session.settings.configure(configuration())
    assert run(session)['state']=='CHAT_COMPLETED'
    ledger=session.settings.ledger
    if fault=='policy':
        pin=ledger.root/'M6B_POLICY.json'; data=json.loads(pin.read_bytes());data['max_requests']=20
        pin.write_text(json.dumps(data),encoding='utf-8')
    elif fault=='partial':
        with ledger.path.open('ab') as f:f.write(b'partial')
    else:
        raw=ledger.path.read_bytes();ledger.path.write_bytes(raw.replace(b'METERED',b'ALTERED'))
    assert session.settings.snapshot()['enabled'] is False
    assert run(session)['state']=='BLOCKED' and calls==[1]
    with pytest.raises((ValueError,OSError)):session.settings.configure(configuration())


def test_persistent_budget_reservation_is_not_reused_after_small_actual_cost(tmp_path,factory):
    session,calls=session_for(tmp_path,factory)
    cfg=configuration();cfg['budget_cny']='0.073'
    session.settings.configure(cfg)
    assert run(session)['state']=='CHAT_COMPLETED'
    assert session.settings.snapshot()['stop_reason']=='DURABLE_RESERVATION_LIMIT'
    assert run(session)['state']=='BLOCKED' and calls==[1]


def test_host_lock_blocks_reservation_without_partial_write(tmp_path,factory):
    session,_=session_for(tmp_path,factory)
    session.settings.configure(configuration())
    ledger=session.settings.ledger
    host=factory._load()  # Test adapter internals; consumer does not use this.
    with host.Lock(ledger.root/'LEDGER.lock'):
        with pytest.raises(ValueError,match='busy'):ledger.reserve_chat('a'*64,'test-run')
    assert ledger.read()==[]


def test_process_crash_keeps_pre_send_reservation_and_blocks_new_scope(tmp_path,factory):
    import subprocess,sys,os
    session,_=session_for(tmp_path,factory)
    session.settings.configure(configuration())
    ledger=session.settings.ledger
    script="""
import json,os,sys
from pathlib import Path
from catalyst_platform.workspace_ledger import PinnedHostLedgerFactory
root=Path(sys.argv[3]); policy=json.loads((root/'M6B_POLICY.json').read_bytes())
ledger=PinnedHostLedgerFactory(sys.argv[1],sys.argv[2]).open_scope(root,policy)
ledger.reserve_chat('a'*64,'synthetic-crash')
os._exit(9)
"""
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1'}
    child=subprocess.run([sys.executable,'-c',script,str(factory.module_path),QUALIFIED,str(ledger.root)],
                         capture_output=True,text=True,env=env,timeout=15)
    assert child.returncode==9,child.stderr
    assert len(ledger.read())==1 and ledger.read()[0]['event']=='RESERVED_BEFORE_SEND'
    assert not ledger.is_settled()
    with pytest.raises(ValueError):WorkspaceSettings(session.app,ledger_factory=factory).configure(configuration())


def test_missing_policy_cannot_hide_existing_dispatch_ledger(tmp_path,factory):
    session,_=session_for(tmp_path,factory)
    session.settings.configure(configuration())
    ledger=session.settings.ledger
    ledger.reserve_chat('a'*64,'synthetic-unsettled')
    (ledger.root/'M6B_POLICY.json').unlink()  # New fixture only, never a historical scope.
    with pytest.raises(ValueError,match='previous_scope_policy_missing'):
        WorkspaceSettings(session.app,ledger_factory=factory).configure(configuration())


@pytest.mark.parametrize('args',[
    ['--ledger-module','unused.py'],
    ['--ledger-sha256',QUALIFIED],
    ['--ledger-module','unused.py','--ledger-sha256','0'*64],
])
def test_cli_rejects_incomplete_or_unqualified_engine_selection(tmp_path,args):
    import subprocess,sys
    result=subprocess.run([sys.executable,'-m','catalyst_platform.workspace_ui',
                           '--workspace',str(tmp_path/'unused'),*args],
                          capture_output=True,text=True,timeout=15)
    assert result.returncode==2 and not (tmp_path/'unused').exists()


def test_server_propagates_trusted_factory_without_loading_or_dispatch(tmp_path,factory):
    from catalyst_platform.workspace_ui import create_workspace_server
    server=create_workspace_server(tmp_path/'server',port=0,ledger_factory=factory)
    try:
        assert server.run_request.settings.ledger_factory is factory
        assert not server.run_request.settings.snapshot()['configured']
    finally:
        server.server_close()
