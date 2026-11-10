"""Daily connection and experiment isolation, synthetic transport only."""
import json
import pytest
from tests.project_understand.test_project_runtime import offline
from tests.test_workspace_model_settings import packet, run, configuration
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.llm_controls import ModelTask


def connect(host):
    return host.settings.connect(dict(provider_id='deepseek',model='deepseek-flash',
        api_key='OFFLINE-SYNTHETIC-KEY',remember=False))


def test_daily_has_no_cumulative_experiment_cap(tmp_path,offline):
    host=WorkspaceUserSession(tmp_path/'daily');calls=[]
    host.settings.transport_override=lambda *args:(calls.append(1) or (200,packet()))
    state=connect(host)
    assert state['connection_mode']=='daily' and state['enabled']
    assert state['budget']['max_requests'] is None and state['budget']['budget_cny'] is None
    for _ in range(25):
        assert run(host)['state']=='CHAT_COMPLETED'
    assert len(calls)==25
    assert host.settings.snapshot()['budget']['attempts']==25
    assert len(host.settings.ledger.read())==50


def test_test_scope_reuses_connection_but_not_limits_or_ledger(tmp_path,offline):
    host=WorkspaceUserSession(tmp_path/'daily');host.settings.transport_override=lambda *_:(200,packet())
    connect(host);parent=host.settings.provider
    child=WorkspaceUserSession(tmp_path/'test')
    child.settings=host.settings.configure_test_connection(child.app,dict(max_requests=1,budget_cny='1',max_output_tokens=1024))
    assert child.settings.provider is not parent
    assert run(child)['state']=='CHAT_COMPLETED'
    assert run(child)['state']=='BLOCKED'
    assert parent.budget_snapshot['attempts']==0
    assert run(host)['state']=='CHAT_COMPLETED'


def test_uncertain_daily_cannot_be_reset_by_connect_or_restart(tmp_path,offline):
    host=WorkspaceUserSession(tmp_path/'daily')
    host.settings.transport_override=lambda *_:(200,packet(usage=None))
    connect(host)
    assert run(host)['state']!='CHAT_COMPLETED'
    assert host.settings.provider.budget_snapshot['uncertain']
    with pytest.raises(ValueError):connect(host)
    restarted=WorkspaceUserSession(host.workspace)
    with pytest.raises(ValueError):connect(restarted)


def test_task_requires_explicit_daily_profile_for_absent_caps():
    with pytest.raises(ValueError):
        ModelTask('task','deepseek','deepseek-flash',None,None,32000,1024,'2','8','0.04','OFFLINE')


def test_daily_connection_cannot_grant_sources_or_override_experiment_limits(tmp_path,offline):
    host=WorkspaceUserSession(tmp_path/'daily');host.settings.transport_override=lambda *_:(200,packet())
    data=dict(provider_id='deepseek',model='deepseek-flash',api_key='OFFLINE-SYNTHETIC-KEY',remember=False)
    for extra in ({'max_requests':999},{'allow_project_read':True},{'budget_cny':None}):
        with pytest.raises(ValueError):host.settings.connect(dict(data,**extra))
    connect(host)
    assert not host.settings.allow_project_read and not host.settings.allow_asset_read
    assert all('OFFLINE-SYNTHETIC-KEY' not in p.read_text(encoding='utf8') for p in host.settings.root.rglob('*.json'))
