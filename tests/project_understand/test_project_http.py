"""Project HTTP admission uses Host sources and original monitor receipts only."""
import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


@pytest.fixture
def service(tmp_path):
    from catalyst_platform.workspace_ui import create_workspace_server
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'SKILL.md').write_text('# Fixture method\n', encoding='utf-8')
    server = create_workspace_server(tmp_path / 'workspace', port=0,
        project_sources={'fixture-skill': {'root': root, 'object_type': 'skill'}})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    def get(path):
        with urlopen(base + path, timeout=10) as response:
            return json.load(response)
    csrf = get('/api/config')['csrf_token']
    def post(body, token=csrf, origin=base):
        request = Request(base + '/api/project-analysis', data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json', 'X-Catalyst-CSRF': token, 'Origin': origin})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    yield server, get, post, root
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_sources_are_labels_and_types_without_host_paths(service):
    _, get, _, root = service
    value = get('/api/project-sources')
    assert value == {'items': [{'source_id': 'fixture-skill', 'label': 'fixture-skill', 'object_type': 'skill'}]}
    assert str(root) not in json.dumps(value)


def test_project_admission_refuses_paths_unknown_sources_and_csrf(service):
    _, _, post, _ = service
    valid = {'source_id': 'fixture-skill', 'objective': 'Inspect fixture responsibilities', 'max_depth': 1}
    assert post(valid, token='wrong')[0] == 403
    assert post(valid, origin='https://wrong.invalid')[0] == 403
    for body in ({**valid, 'root': 'C:/'}, {**valid, 'source_id': '../outside'},
                 {**valid, 'source_id': 'unknown'}, {**valid, 'max_depth': True},
                 {**valid, 'max_depth': 3}, {**valid, 'objective': ''}):
        assert post(body)[0] == 400


def test_project_busy_admission_includes_queued_requests(service):
    server, _, post, _ = service
    server.run_request._pending['queued-fixture'] = threading.Event()
    try:
        assert post({'source_id': 'fixture-skill', 'objective': 'Inspect', 'max_depth': 1})[0] == 409
    finally:
        server.run_request._pending.clear()


def test_project_runs_through_original_monitor_and_result_readback(service, monkeypatch):
    server, get, post, root = service
    called = []
    def analyze(spec, objective, max_depth, recorder):
        called.append((spec, objective, max_depth))
        output = {'run_id': recorder.run_id, 'status': 'success', 'task_type': 'project_analysis',
                  'result': {'output': {'answer': 'FIXTURE_ONLY'}}, 'external_calls': 0}
        with server.run_request._control:
            server.run_request._pending.pop(recorder.run_id, None)
        recorder.finish('success', external_calls=0)
        return output
    monkeypatch.setattr(server.run_request, 'analyze_project', analyze, raising=False)
    status, started = post({'source_id': 'fixture-skill', 'objective': 'Inspect fixture', 'max_depth': 1})
    assert status == 202
    for _ in range(100):
        try:
            result = get('/api/runs/' + started['run_id'] + '/result')
            if result.get('task_type') == 'project_analysis':
                break
        except HTTPError:
            pass
        time.sleep(.02)
    assert result['result']['output']['answer'] == 'FIXTURE_ONLY'
    assert called == [({'root': root.resolve(), 'object_type': 'skill'}, 'Inspect fixture', 1)]
    assert any(run['run_id'] == started['run_id'] for run in get('/api/runs'))


def test_default_server_has_no_source_selector_configuration(tmp_path):
    from catalyst_platform.workspace_ui import create_workspace_server
    server = create_workspace_server(tmp_path / 'default', port=0)
    try:
        assert not server.project_sources
    finally:
        server.server_close()


@pytest.fixture
def method_maintenance(tmp_path):
    from catalyst_platform.maintenance import LocalMaintenance
    from catalyst_platform.workbench import CatalystWorkbench
    root = tmp_path / 'method-workspace'
    app = CatalystWorkbench(root, [root / 'inputs'])
    manager = LocalMaintenance(app, run_regression=False)
    yield manager
    app.components.close_loaded()
    app.plugins.close()


def test_fixed_method_review_is_fixture_only_and_restart_bound(method_maintenance):
    manager = method_maintenance
    manager.install_test_parent(target='project-understand')
    old = manager.active_identity('project-understand')
    review = manager.prepare(target='project-understand')
    assert review['target'] == 'project-understand'
    assert review['candidate']['version'] == '0.1.1'
    assert review['evaluation']['semantic_quality'] == 'NOT_EVALUATED'
    assert review['evaluation']['fixture_only'] is True
    assert 'SKILL.md' in review['diff']
    manager.approve(review['review_id'], review['approval_digest'], confirmed=True)
    assert manager.active_identity('project-understand') == old
    assert manager.apply_pending()['status'] == 'APPLIED'
    assert manager.active_identity('project-understand')['version'] == '0.1.1'
    manager.request_rollback(review['review_id'], review['approval_digest'], confirmed=True)
    assert manager.apply_pending()['status'] == 'ROLLED_BACK'
    assert manager.active_identity('project-understand') == old


def test_method_review_refuses_tampering_and_production_promotion(method_maintenance):
    manager = method_maintenance
    review = manager.prepare(target='project-understand')
    manager.run_regression = True
    with pytest.raises(ValueError, match='production_regression_required'):
        manager.approve(review['review_id'], review['approval_digest'], confirmed=True)
    manager.run_regression = False
    stage = manager.root / 'packages' / review['review_id'] / 'SKILL.md'
    stage.write_text(stage.read_text(encoding='utf-8') + '\nchanged', encoding='utf-8')
    with pytest.raises((ValueError, RuntimeError)):
        manager.approve(review['review_id'], review['approval_digest'], confirmed=True)


def test_maintenance_target_is_fixed_allowlist(method_maintenance):
    with pytest.raises(ValueError, match='maintenance_target_not_allowed'):
        method_maintenance.prepare(target='../arbitrary')


def test_method_review_target_is_bound_in_approval_digest(method_maintenance):
    manager = method_maintenance
    review = manager.prepare(target='project-understand')
    review['target'] = 'local_text_stats'
    manager._write(review)
    with pytest.raises(ValueError, match='maintenance_receipt_changed'):
        manager.approve(review['review_id'], review['approval_digest'], confirmed=True)


@pytest.mark.parametrize('applied_target,pending_target', [
    ('project-understand', 'local_text_stats'),
    ('local_text_stats', 'project-understand'),
])
def test_rollback_refuses_another_target_pending_restart(method_maintenance, applied_target, pending_target):
    manager = method_maintenance
    manager.install_test_parent(target=applied_target)
    manager.install_test_parent(target=pending_target)
    applied = manager.prepare(target=applied_target)
    manager.approve(applied['review_id'], applied['approval_digest'], confirmed=True)
    assert manager.apply_pending()['status'] == 'APPLIED'
    pending = manager.prepare(target=pending_target)
    manager.approve(pending['review_id'], pending['approval_digest'], confirmed=True)

    with pytest.raises(ValueError, match='maintenance_restart_pending'):
        manager.request_rollback(applied['review_id'], applied['approval_digest'], confirmed=True)

    rows = {row['review_id']: row for row in manager.items()}
    assert rows[applied['review_id']]['status'] == 'APPLIED'
    assert rows[pending['review_id']]['status'] == 'PENDING_RESTART'
    assert manager.apply_pending()['status'] == 'APPLIED'


def test_method_review_route_accepts_only_fixed_target(service, monkeypatch):
    from catalyst_platform.maintenance import LocalMaintenance
    server, get, _, _ = service
    monkeypatch.setattr(server, 'maintenance', LocalMaintenance(server.run_request.app, run_regression=False))
    csrf = get('/api/config')['csrf_token']
    base = 'http://127.0.0.1:' + str(server.server_port)
    def post(data):
        request = Request(base + '/api/maintenance', data=json.dumps({'action': 'prepare', 'data': data}).encode(),
            headers={'Content-Type': 'application/json', 'X-Catalyst-CSRF': csrf, 'Origin': base})
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    assert post({'target': '../unknown'})[0] == 400
    assert post({'target': 'project-understand', 'path': 'C:/'})[0] == 400
    code, review = post({'target': 'project-understand'})
    assert code == 200 and review['target'] == 'project-understand'
    assert get('/api/maintenance')['method_active'] is None


def test_pending_runtime_keeps_reads_available_but_refuses_all_mutating_posts(service):
    server,get,_,_=service
    base='http://127.0.0.1:'+str(server.server_port)
    csrf=get('/api/config')['csrf_token']
    server.run_request.session._project_pending_handles={'unknown-runtime':{'run_id':'retained-run'}}
    server.run_request.settings.active_run_id='retained-run'
    assert get('/api/project-sources')['items']
    for route,body in [('/api/ask',{'message':'hello','selected_file':None}),('/api/settings',{'action':'disconnect','data':{}}),('/api/maintenance',{'action':'restart','data':{'confirmed':True}}),('/api/project-analysis',{'source_id':'fixture-skill','objective':'inspect','max_depth':1})]:
        request=Request(base+route,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':base,'X-Catalyst-CSRF':csrf})
        with pytest.raises(HTTPError) as caught:urlopen(request,timeout=5)
        assert caught.value.code==409
        assert json.load(caught.value)['error']['code']=='project_runtime_unresolved'
    assert server.run_request.settings.active_run_id=='retained-run'
