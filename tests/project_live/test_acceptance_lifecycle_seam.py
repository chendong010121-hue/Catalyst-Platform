import inspect
import pytest
from catalyst_platform.project_acceptance import ProjectAcceptance
from tests.project_live.test_project_acceptance import configured, qualification_clock
from tests.project_understand.test_project_runtime import offline
from tests.project_live.test_daily_workflow_boundary import recorder


def test_acceptance_uses_session_lifecycle_seam():
    code = inspect.getsource(ProjectAcceptance)
    for private in ('._execution', '._control', '._pending', '._recorders', '._capture_providers'):
        assert private not in code


def test_execute_evidence_failure_releases_registration_and_retains_subject(tmp_path, offline, monkeypatch):
    host, root, calls, flow = configured(tmp_path)
    row = flow.prepare('agent', 'Explain this Agent dependency', 2)
    rec = recorder(host)
    host.prepare(rec)
    original = host.app._atomic_json
    def fail_capture(path, *args, **kwargs):
        if path.name == 'requests-responses.json':
            raise OSError('evidence unavailable')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(host.app, '_atomic_json', fail_capture)
    with pytest.raises(OSError, match='evidence unavailable'):
        flow.execute(row['test_id'], row['card_sha256'], rec)
    assert rec.run_id not in host._pending
    assert rec.run_id not in host._recorders
    assert rec.run_id not in host._capture_providers
    assert host.settings.active_run_id is None
    assert row['test_id'] in flow.retained
    assert flow.get(row['test_id'])['state'] != 'FINISHED'

@pytest.mark.parametrize('failure_file', ['started.json', 'record.json'])
def test_admission_write_failure_closes_child_before_dispatch(tmp_path, offline, monkeypatch, failure_file):
    from catalyst_platform.workspace_session import WorkspaceUserSession
    host, root, calls, flow = configured(tmp_path)
    row = flow.prepare('agent', 'Explain this Agent dependency', 2)
    rec = recorder(host)
    host.prepare(rec)
    children = []
    original_connect = host.settings.configure_test_connection
    def connection(*args, **kwargs):
        settings = original_connect(*args, **kwargs)
        children.append(settings)
        return settings
    monkeypatch.setattr(host.settings, 'configure_test_connection', connection)
    original = host.app._atomic_json
    def fail_admission(path, *args, **kwargs):
        if path.name == failure_file:
            raise OSError('admission evidence unavailable')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(host.app, '_atomic_json', fail_admission)
    with pytest.raises(OSError, match='admission evidence unavailable'):
        flow.execute(row['test_id'], row['card_sha256'], rec)
    assert not calls
    assert children and children[0].provider is None
    assert rec.run_id not in host._pending
    assert rec.run_id not in host._recorders
    assert host.settings.active_run_id is None
