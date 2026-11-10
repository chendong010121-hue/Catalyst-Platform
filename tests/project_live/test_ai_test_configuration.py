import json
import pytest
from tests.project_live.test_project_acceptance import configured,qualification_clock
from tests.project_understand.test_project_runtime import offline
from tests.project_live.test_daily_workflow_boundary import recorder
from tests.test_workspace_model_settings import configuration,packet

@pytest.mark.parametrize('fault',[None,'unknown_source','grant','timeout','length'])
def test_ai_prepares_only_review_card_via_original_harness(tmp_path,offline,fault):
    host,root,_,flow=configured(tmp_path);calls=[]
    def send(url,headers,body):
        calls.append(json.loads(body))
        if fault=='timeout':raise TimeoutError('OFFLINE_UNKNOWN')
        value=dict(source_id='agent' if fault!='unknown_source' else 'not-admitted',objective='Explain this Agent dependency',max_depth=2,max_requests=5,max_output_tokens=2048,evaluation_mode='mechanical_plus_independent_review')
        if fault=='grant':value['confirmed']=True
        result=packet(json.dumps(value))
        if fault=='length':result['choices'][0]['finish_reason']='length'
        return 200,result
    host.settings.transport_override=send;host.settings.configure(configuration())
    rec=recorder(host);host.prepare(rec)
    result=flow.propose('Prepare a test for the admitted Agent',rec)
    assert len(calls)==1
    text=json.dumps(calls)
    assert 'def main' not in text and str(root) not in text
    assert host.settings.provider.budget_snapshot['attempts']==0
    plans=flow.plans();assert len(plans)==1 and plans[0]['model_requests']==1
    if fault is None:
        assert result['state']=='TEST_CARD_PREPARED'
        rows=flow.items();assert len(rows)==1 and rows[0]['state']=='PREPARED'
        assert rows[0]['model_requests']==0 and rows[0]['prepared_by']=='LLM'
    else:
        assert result['status']=='failure' and not flow.items()
        assert plans[0]['state']==('UNRESOLVED' if fault=='timeout' else 'FAILED')
        if fault=='timeout':
            fresh=flow.prepare('agent','inspect',1)
            with pytest.raises(ValueError,match='prior_plan_requires_reconciliation'):
                flow.validate(fresh['test_id'],fresh['card_sha256'])

@pytest.mark.parametrize('phase',['initialization','prepared'])
def test_cancelled_ai_plan_closes_scope_and_cannot_leave_executable_card(tmp_path,offline,monkeypatch,phase):
    host,root,_,flow=configured(tmp_path);calls=[]
    def send(*_):
        calls.append(1)
        return 200,packet(json.dumps(dict(source_id='agent',objective='Explain this Agent dependency',max_depth=2,
            max_requests=5,max_output_tokens=2048,evaluation_mode='mechanical_plus_independent_review')))
    host.settings.transport_override=send;host.settings.configure(configuration())
    rec=recorder(host);host.prepare(rec)
    if phase=='initialization':
        original=host.settings.configure_test_connection
        def connect(*args):
            result=original(*args);host.cancel(rec.run_id);return result
        monkeypatch.setattr(host.settings,'configure_test_connection',connect)
    else:
        original=flow.prepare
        def prepare(*args,**kwargs):
            row=original(*args,**kwargs);host.cancel(rec.run_id);return row
        monkeypatch.setattr(flow,'prepare',prepare)
    result=flow.propose('Prepare an Agent test',rec)
    assert result['state']=='CANCELLED' and rec.is_finished
    assert len(calls)==(0 if phase=='initialization' else 1)
    assert not host.settings.active_run_id
    assert all(row['state']!='PREPARED' for row in flow.items())


def test_plan_evidence_write_failure_preserves_block_and_cleans_control(tmp_path,offline,monkeypatch):
    host,root,_,flow=configured(tmp_path)
    host.settings.transport_override=lambda *_:(200,packet(json.dumps(dict(source_id='agent',objective='Explain this Agent dependency',
        max_depth=2,max_requests=5,max_output_tokens=2048,evaluation_mode='mechanical_plus_independent_review'))))
    host.settings.configure(configuration());rec=recorder(host);host.prepare(rec)
    original=host.app._atomic_json
    def write(path,value,**kw):
        if path.name=='requests-responses.json':raise OSError('OFFLINE_WRITE_FAILURE')
        return original(path,value,**kw)
    monkeypatch.setattr(host.app,'_atomic_json',write)
    with pytest.raises(OSError,match='OFFLINE_WRITE_FAILURE'):flow.propose('Prepare Agent test',rec)
    assert rec.is_finished and not host.settings.active_run_id
    assert rec.run_id not in host._pending and not host._capture_providers
    assert flow.plans()[0]['state']=='RUNNING'
    row=flow.items()[0]
    with pytest.raises(ValueError,match='prior_plan_requires_reconciliation'):flow.validate(row['test_id'],row['card_sha256'])
