"""Browser boundary for ordinary model connection; never a live API call."""
import json
import threading
from tests.test_workspace_settings_http import service


def test_connect_http_has_no_experiment_fields_and_keeps_csrf_gate(service):
    server,calls,get,post=service
    payload={'action':'connection','data':dict(provider_id='deepseek',model='deepseek-flash',
        api_key='OFFLINE-CONNECTION-KEY',remember=False)}
    assert post(payload,csrf='wrong')[0]==403
    code,state=post(payload)
    assert code==200 and state['enabled'] and state['connection_mode']=='daily'
    assert state['budget']['max_requests'] is None and state['budget']['budget_cny'] is None
    assert not state['allow_project_read'] and not state['allow_asset_read']
    assert 'OFFLINE-CONNECTION-KEY' not in json.dumps(state) and not calls
    assert post({'action':'connection','data':dict(payload['data'],max_requests=999)})[0]==400


def test_connect_rejects_pending_without_reading_saved_key(service):
    server,calls,get,post=service
    server.run_request._pending['queued']=threading.Event()
    try:
        assert post({'action':'connection','data':dict(provider_id='deepseek',model='deepseek-flash',use_saved=True,remember=False)})[0]==400
    finally:server.run_request._pending.clear()
    assert not calls and server.run_request.settings.provider is None
