"""One reviewed card, fresh original session/P0, fake transport only."""
import json
import pytest
from tests.project_understand.test_project_runtime import setup,offline,script
from tests.project_live.test_daily_workflow_boundary import recorder
from tests.test_workspace_model_settings import configuration

@pytest.fixture(autouse=True)
def qualification_clock(offline,monkeypatch):
    import catalyst_platform.workspace_settings as settings
    import catalyst_platform.project_acceptance as acceptance
    monkeypatch.setattr(acceptance,'datetime',settings.datetime)

def configured(tmp_path):
    from catalyst_platform.project_acceptance import ProjectAcceptance
    host,root=setup(tmp_path);calls,original=script(root)
    def transport(*args):
        result=original(*args)
        if len(calls)==3:
            function=result[1]['choices'][0]['message']['tool_calls'][0]['function']
            params=json.loads(function['arguments']);value=json.loads(params['query'])
            value['questions']=[dict(question_id=q,critical=True,status='EXPLICITLY_UNRESOLVED',claim_ids=[])
                for q in ('purpose','interface','dependencies','failure_boundary')]
            params['query']=json.dumps(value);function['arguments']=json.dumps(params)
        return result
    host.settings.transport_override=transport
    host.settings.configure(configuration())
    flow=ProjectAcceptance(host,{'agent':{'root':root,'object_type':'agent'}})
    return host,root,calls,flow

def test_card_calculates_limits_without_key_or_paid_request(tmp_path,offline):
    from catalyst_platform.project_acceptance import ProjectAcceptance
    host,root=setup(tmp_path)
    flow=ProjectAcceptance(host,{'agent':{'root':root,'object_type':'agent'}})
    row=flow.prepare('agent','Explain this Agent dependency',2)
    assert row['card']['max_requests']==8
    assert row['card']['budget_cny']=='0.774144'
    assert row['state']=='PREPARED' and row['card']['formal_writes'] is False
    assert host.settings.provider is None

def test_confirmed_card_uses_isolated_ledger_without_retyping_key(tmp_path,offline):
    host,root,calls,flow=configured(tmp_path)
    daily_provider=host.settings.provider;daily_task=host.settings.task.task_id
    row=flow.prepare('agent','Explain this Agent dependency',2)
    rec=recorder(host);host.prepare(rec)
    result=flow.execute(row['test_id'],row['card_sha256'],rec)
    assert result['status']=='success',result
    assert len(calls)==4
    assert host.settings.provider is daily_provider
    assert host.settings.task.task_id==daily_task and daily_provider.budget_snapshot['attempts']==0
    final=flow.get(row['test_id'])
    assert final['state']=='FINISHED'
    assert final['model_requests']==4 and final['semantic_quality']=='NOT_EVALUATED'
    assert final['task_id']!=daily_task
    assert (flow.directory(row['test_id'])/'requests-responses.json').exists()
    assert final['mechanical_evaluation']['dimensions']['SOURCE_IDENTITY']['status']=='PASS'
    with pytest.raises(ValueError,match='test_already_consumed'):
        flow.execute(row['test_id'],row['card_sha256'],recorder(host))
    assert len(calls)==4
    assert 'OFFLINE-TEST-KEY' not in json.dumps(flow.items())

@pytest.mark.parametrize('mutation',['digest','source','cancel','disconnect','permissions'])
def test_blocked_cards_never_dispatch(tmp_path,offline,mutation):
    host,root,calls,flow=configured(tmp_path)
    row=flow.prepare('agent','Explain this Agent dependency',2)
    rec=recorder(host);host.prepare(rec);sha=row['card_sha256']
    if mutation=='digest':sha='0'*64
    if mutation=='source':(root/'agent.py').write_text('changed',encoding='utf-8')
    if mutation=='cancel':host.cancel(rec.run_id)
    if mutation=='disconnect':host.settings.disconnect()
    if mutation=='permissions':
        row['card']['formal_writes']=True
        # File alteration is rejected by stored record integrity checks.
        host.app._atomic_json(flow.directory(row['test_id'])/'record.json',row)
    with pytest.raises(ValueError):flow.execute(row['test_id'],sha,rec)
    assert calls==[]

def test_settings_connection_is_cleared_and_not_a_scope_authority(tmp_path,offline):
    host,root,calls,flow=configured(tmp_path)
    host.settings.disconnect()
    with pytest.raises(ValueError,match='model_connection_unavailable'):
        host.settings.configure_test_connection(host.app,{'max_requests':8,'budget_cny':'1','max_output_tokens':4096})
    assert calls==[]

def test_uncertain_model_send_is_not_retried_and_blocks_new_tests(tmp_path,offline):
    from catalyst_platform.project_acceptance import ProjectAcceptance
    host,root=setup(tmp_path);calls=[]
    def timeout(*args):
        calls.append('attempt');raise TimeoutError('OFFLINE simulated uncertain transport')
    host.settings.transport_override=timeout;host.settings.configure(configuration())
    flow=ProjectAcceptance(host,{'agent':{'root':root,'object_type':'agent'}})
    card=flow.prepare('agent','inspect',1);rec=recorder(host);host.prepare(rec)
    result=flow.execute(card['test_id'],card['card_sha256'],rec)
    assert result['status']=='failure' and len(calls)==1
    row=flow.get(card['test_id'])
    assert row['state']=='UNRESOLVED' and row['budget']['uncertain']
    fresh=flow.prepare('agent','inspect',1)
    with pytest.raises(ValueError,match='prior_test_requires_reconciliation'):
        flow.execute(fresh['test_id'],fresh['card_sha256'],recorder(host))
    restarted=ProjectAcceptance(host,flow.sources)
    with pytest.raises(ValueError,match='prior_test_requires_reconciliation'):
        restarted.validate(fresh['test_id'],fresh['card_sha256'])
    assert len(calls)==1 and host.settings.provider.budget_snapshot['attempts']==0

def test_prepared_card_qualification_drift_is_not_silently_refreshed(tmp_path,offline):
    host,root,calls,flow=configured(tmp_path)
    row=flow.prepare('agent','inspect',1)
    flow.sources['agent']['object_type']='skill'
    with pytest.raises(ValueError,match='test_inputs_or_qualification_changed'):
        flow.validate(row['test_id'],row['card_sha256'])
    assert calls==[]

def test_settled_daily_limit_does_not_require_new_key_for_new_test(tmp_path,offline):
    from agent_runtime.contracts import ModelRequest,Message
    from tests.test_workspace_model_settings import packet
    from catalyst_platform.workspace_settings import WorkspaceSettings
    host,root=setup(tmp_path);calls=[]
    def transport(*args):calls.append(1);return 200,packet()
    host.settings.transport_override=transport
    conf=configuration();conf['max_requests']=1;host.settings.configure(conf)
    original=host.settings.provider
    original.request(ModelRequest(messages=(Message(role='user',content='offline'),)))
    state=host.settings.snapshot()
    assert state['stop_reason']=='REQUEST_LIMIT' and not state['enabled']
    assert state['test_connection_available']
    child=host.settings.configure_test_connection(host.app,dict(max_requests=8,budget_cny='0.774144',max_output_tokens=4096))
    assert child.provider.budget_snapshot['attempts']==0 and original.budget_snapshot['attempts']==1
    assert child.task.task_id!=host.settings.task.task_id and len(calls)==1
    child.disconnect()

def test_source_changed_between_confirmation_and_runtime_never_reaches_provider(tmp_path,offline,monkeypatch):
    host,root,calls,flow=configured(tmp_path)
    row=flow.prepare('agent','Explain this Agent dependency',2)
    original=host.settings.configure_test_connection
    def changed_after_confirmation(*args,**kwargs):
        settings=original(*args,**kwargs)
        (root/'agent.py').write_text('NEW_UNAPPROVED_SOURCE = True\n',encoding='utf-8')
        return settings
    monkeypatch.setattr(host.settings,'configure_test_connection',changed_after_confirmation)
    rec=recorder(host);host.prepare(rec)
    result=flow.execute(row['test_id'],row['card_sha256'],rec)
    assert calls==[], 'A source changed after card validation was sent to the Provider'
    assert result['status']=='failure'
    assert result['error']['code']=='project_approved_source_changed'
