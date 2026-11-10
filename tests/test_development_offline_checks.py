import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from catalyst_platform.workbench import CatalystWorkbench
from catalyst_platform import evaluation_workflow


def test_existing_evaluation_can_execute_two_distinct_bounded_product_entries(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    assert callable(getattr(evaluation_workflow, 'offline_profiles', None))
    assert {p['id'] for p in evaluation_workflow.offline_profiles()} == {'file_title', 'ontology', 'file_title_comparison'}
    for profile in ('file_title', 'ontology'):
        receipt = evaluation_workflow.run_offline_check(app, profile)
        root = Path(receipt['artifact_root'])
        assert receipt['status'] == 'COMPLETED'
        assert receipt['model_requests'] == 0
        assert receipt['business_semantics'] == 'NOT_EVALUATED'
        assert receipt['owner_admission'] is False
        assert receipt['cases'] and all(row['task_success'] for row in receipt['cases'])
        assert json.loads((root / 'metadata.json').read_text(encoding='utf8'))['entry_identity']['function'] == (
            'file_title_entry' if profile == 'file_title' else 'ontology_entry')
        assert (root / 'manifest.json').is_file()
    assert not list((tmp_path / 'workspace').rglob('M6B_POLICY.json'))


def test_unknown_offline_profile_does_not_create_a_run(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    with pytest.raises(ValueError, match='offline_profile_invalid'):
        evaluation_workflow.run_offline_check(app, '../../secret')
    assert not (app.workspace / 'd').exists()


def test_offline_artifact_parent_cannot_escape_workspace(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    outside = tmp_path / 'outside'
    outside.mkdir()
    try:
        (app.workspace / 'd').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Host does not permit directory symlinks')
    with pytest.raises(ValueError, match='offline_workspace_path_invalid'):
        evaluation_workflow.run_offline_check(app, 'file_title')
    assert not list(outside.iterdir())


def test_offline_comparison_uses_existing_gate_and_cannot_promote(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    result = evaluation_workflow.run_offline_check(app, 'file_title_comparison')
    assert result['comparison']['accept'] is True
    assert result['comparison']['owner_admission'] is False
    assert result['reference_promoted'] is False
    assert result['model_requests'] == 0
    assert result['scope'] == 'SYNTHETIC_FAULT_INJECTED_COMPARISON_ONLY'
    assert (Path(result['artifact_root']) / 'p' / 'manifest.json').exists()
    assert (Path(result['artifact_root']) / 'c' / 'manifest.json').exists()


def test_development_http_requires_csrf_and_uses_fixed_offline_profiles(tmp_path):
    from catalyst_platform.workspace_ui import create_workspace_server
    server = create_workspace_server(tmp_path / 'ui', port=0, mode='BLOCKED')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    payload = json.dumps({'profile': 'ontology'}).encode()
    try:
        with urlopen(base + '/api/development-offline') as response:
            assert len(json.load(response)['profiles']) == 3
        request = Request(base + '/api/development-offline', payload, {'Content-Type': 'application/json'})
        with pytest.raises(HTTPError) as blocked:
            urlopen(request)
        assert blocked.value.code == 403
        assert not (server.run_request.app.workspace / 'd').exists()
        request.add_header('X-Catalyst-CSRF', server.local_csrf_token)
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        assert result['profile'] == 'ontology' and result['model_requests'] == 0
        assert result['business_semantics'] == 'NOT_EVALUATED'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
