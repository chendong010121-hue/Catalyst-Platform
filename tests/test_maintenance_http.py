import json
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest


@pytest.fixture
def service(tmp_path,monkeypatch):
    import catalyst_platform.workspace_ui as ui
    from catalyst_platform.maintenance import LocalMaintenance
    monkeypatch.setattr(ui,'LocalMaintenance',lambda app:LocalMaintenance(app,run_regression=False))
    server=ui.create_workspace_server(tmp_path/'workspace',port=0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    def get(path):
        with urlopen(base+path,timeout=10) as r:return json.load(r)
    csrf=get('/api/config')['csrf_token']
    def post(data,token=csrf,origin=base):
        req=Request(base+'/api/maintenance',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','X-Catalyst-CSRF':token,'Origin':origin})
        try:
            with urlopen(req,timeout=40) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    yield server,get,post
    if thread.is_alive():server.shutdown()
    server.server_close();thread.join(timeout=5)


def test_original_knowledge_review_is_still_separate_and_readonly(service):
    server,get,post=service
    assert get('/api/reviews')['items']==[]
    assert get('/api/maintenance')['items']==[]
    assert post({'action':'prepare','data':{}},token='wrong')[0]==403
    assert post({'action':'prepare','data':{}},origin='https://wrong.invalid')[0]==403
    assert post({'action':'prepare','data':{'path':'not-allowed'}})[0]==400


def test_review_api_prepares_approves_but_does_not_activate(service):
    server,get,post=service
    code,review=post({'action':'prepare','data':{}})
    assert code==200 and review['status']=='VALIDATED'
    body={'review_id':review['review_id'],'approval_digest':review['approval_digest'],'confirmed':True}
    assert post({'action':'approve','data':body})[0]==200
    assert server.maintenance.active_identity() is None
    assert get('/api/maintenance')['items'][0]['status']=='PENDING_RESTART'
    assert get('/api/reviews')['items']==[]


def test_busy_and_uncertain_scope_refuse_restart(service,monkeypatch):
    server,get,post=service
    server.run_request._execution.acquire()
    try:assert post({'action':'restart','data':{'confirmed':True}})[0]==409
    finally:server.run_request._execution.release()
    def uncertain(*args):raise ValueError('fixture_unsettled_scope')
    monkeypatch.setattr(server.run_request.settings.ledger_factory,'check_prior_scopes',uncertain)
    assert post({'action':'restart','data':{'confirmed':True}})[0]==400
    assert not server.restart_requested


def test_restart_requires_explicit_local_confirmation(service):
    server,get,post=service
    assert post({'action':'restart','data':{'confirmed':False}})[0]==400
    assert not server.restart_requested


def test_queued_task_blocks_restart_even_before_execution(service):
    server,get,post=service
    server.run_request._pending['queued-test']=threading.Event()
    try:
        code,value=post({'action':'restart','data':{'confirmed':True}})
        assert code==400 and not server.restart_requested
    finally:server.run_request._pending.clear()


def test_real_cold_server_creation_consumes_only_approved_update(tmp_path,monkeypatch):
    import catalyst_platform.workspace_ui as ui
    from catalyst_platform.maintenance import LocalMaintenance
    monkeypatch.setattr(ui,'LocalMaintenance',lambda app:LocalMaintenance(app,run_regression=False))
    workspace=tmp_path/'cold'
    first=ui.create_workspace_server(workspace,port=0)
    try:
        review=first.maintenance.prepare()
        first.maintenance.approve(review['review_id'],review['approval_digest'],confirmed=True)
        assert first.maintenance.active_identity() is None
    finally:first.server_close()
    second=ui.create_workspace_server(workspace,port=0)
    try:
        assert second.maintenance.active_identity()['version']=='2.0.0'
        assert second.maintenance.items()[0]['status']=='APPLIED'
    finally:second.server_close();second.run_request.app.components.close_loaded()


def test_recovery_required_prevents_normal_server_start(tmp_path,monkeypatch):
    import catalyst_platform.workspace_ui as ui
    from catalyst_platform.maintenance import LocalMaintenance
    monkeypatch.setattr(ui,'LocalMaintenance',lambda app:LocalMaintenance(app,run_regression=False))
    workspace=tmp_path/'blocked-recovery'
    first=ui.create_workspace_server(workspace,port=0)
    try:
        row=first.maintenance.prepare();row['status']='RECOVERY_REQUIRED';first.maintenance._write(row)
    finally:first.server_close()
    with pytest.raises(ValueError,match='recovery_required'):ui.create_workspace_server(workspace,port=0)


def test_unavailable_optional_maintenance_engine_does_not_block_empty_local_browsing(tmp_path,monkeypatch):
    import catalyst_platform.maintenance as module
    from catalyst_platform.workspace_ui import create_workspace_server
    def missing():raise OSError('fixture missing engine')
    monkeypatch.setattr(module,'load_host_ledger',missing)
    server=create_workspace_server(tmp_path/'browse',port=0)
    try:
        assert server.maintenance.items()==[]
        assert not server.run_request.settings.snapshot()['configured']
    finally:server.server_close()


def test_old_keepalive_connection_cannot_serve_old_csrf_after_restart(service):
    import http.client
    server,get,post=service
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    try:
        connection.request('GET','/api/config');response=connection.getresponse();old=json.loads(response.read())
        assert old['csrf_token']
        server.restart_requested=True
        connection.request('GET','/api/config');response=connection.getresponse();response.read()
        assert response.status==503
    finally:connection.close();server.restart_requested=False
