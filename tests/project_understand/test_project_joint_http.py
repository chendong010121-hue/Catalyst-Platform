"""Actual HTTP -> Workspace -> Runtime/P0/R4; fake transport, no quality claim."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION, load_qualification
from catalyst_platform.project_understand import ProjectUnderstandingRequest, digest, source_manifest
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workspace_ui import create_workspace_server
from tests.project_understand.test_project_runtime import script
from tests.test_workspace_model_settings import configuration


@pytest.fixture(autouse=True)
def loopback_only_and_pinned_clock(monkeypatch):
    import catalyst_platform.workspace_settings as settings
    instant = load_qualification(DEFAULT_QUALIFICATION).verified_at + timedelta(seconds=1)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(settings, 'datetime', Clock)
    original_connect = socket.socket.connect
    def connect(sock, address):
        if not isinstance(address, tuple) or address[0] != '127.0.0.1':
            raise AssertionError('PROJECT_JOINT_EXTERNAL_NETWORK_DENIED')
        return original_connect(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', connect)


def test_actual_project_http_runtime_p0_r4_joint_readback(tmp_path):
    root = tmp_path / 'host-admitted-source'
    root.mkdir()
    (root / 'agent.py').write_text('from worker import run\ndef main():\n    return run()\n', encoding='utf-8')
    (root / 'worker.py').write_text('def run():\n    return "joint HTTP fixture"\n', encoding='utf-8')
    manifest = source_manifest(root)
    original_bytes = {p.name: p.read_bytes() for p in root.iterdir()}
    objective = 'Explain this Agent dependency'
    calls, original_transport = script(root)
    critical = ProjectUnderstandingRequest('fixture-contract', objective, 'agent', 2).critical_questions
    def transport(url, headers, body):
        # Reuse the explicit Runtime fixture and cover the actual session's
        # default critical set. Only the first source-backed claim is supported.
        status, response = original_transport(url, headers, body)
        if len(calls) == 3:
            function = response['choices'][0]['message']['tool_calls'][0]['function']
            args = json.loads(function['arguments'])
            analysis = json.loads(args['query'])
            analysis['questions'] = [dict(question_id=q, critical=True,
                status='SUPPORTED' if i == 0 else 'EXPLICITLY_UNRESOLVED',
                claim_ids=['c1'] if i == 0 else []) for i, q in enumerate(critical)]
            args['query'] = json.dumps(analysis)
            function['arguments'] = json.dumps(args)
        return status, response

    server = create_workspace_server(tmp_path / 'workspace', port=0,
        project_sources={'joint-agent': {'root': root, 'object_type': 'agent'}})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    base = 'http://127.0.0.1:' + str(server.server_port)
    session = server.run_request
    try:
        # Lifecycle registration is independent Host setup, never triggered by
        # the browser source ID or an uploaded Python entry.
        package = Path(__file__).resolve().parents[2] / 'examples/project_methods/project-understand/0.1.0'
        candidate = session.app.components.discover(package)
        session.app.components.admit(package, candidate['package_sha256'])
        session.app.components.activate('project-understand', '0.1.0')
        session.settings.transport_override = transport
        config = configuration()
        config['max_requests'] = 6
        session.settings.configure(config)
        wiki = ProjectWiki(session.workspace, [session.input_root], enterprise_id='synthetic',
            project_id='local-ui-demo', backend='json')
        wiki_before = wiki.semantic_state()
        thread.start()
        def get(path):
            with urlopen(base + path, timeout=10) as response:
                return json.load(response)
        csrf = get('/api/config')['csrf_token']
        request = Request(base + '/api/project-analysis',
            data=json.dumps({'source_id': 'joint-agent', 'objective': objective, 'max_depth': 2}).encode(),
            headers={'Content-Type': 'application/json', 'X-Catalyst-CSRF': csrf, 'Origin': base})
        with urlopen(request, timeout=10) as response:
            assert response.status == 202
            started = json.load(response)
        result = None
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                result = get('/api/runs/' + started['run_id'] + '/result')
                break
            except HTTPError as error:
                assert error.code in (404,409)
                time.sleep(.02)
        assert result is not None
        assert result['status'] == 'success', result
        assert result['state'] == 'PROJECT_ANALYZED' and result['task_type'] == 'project_analysis'
        assert result['external_calls'] == 0 and result['candidate_id'] is None and result['version_id'] is None
        analysis = result['result']['output']['project_analysis']
        assert analysis['tool_executions'] == {'project_inspect': 1, 'project_expand_evidence': 1, 'project_submit_analysis': 1}
        assert analysis['runtime_status'] == 'success'
        assert analysis['method']['package_sha256'] == candidate['package_sha256']
        assert analysis['source_manifest_sha256'] == digest(manifest)
        assert analysis['analysis']['decision_readiness'] == 'NEEDS_EVIDENCE'
        assert {q['question_id'] for q in analysis['analysis']['questions']} == set(critical)
        assert analysis['semantic_quality'] == 'NOT_EVALUATED' and len(calls) == 4
        assert result['lifecycle']['handle_released'] is True
        assert result['lifecycle']['method_lease_retained'] is False

        inspected = get('/api/runs/' + started['run_id'])
        assert inspected['terminal_status'] == 'success'
        events = inspected['events']
        executed = {e.get('capability_id') for e in events if e['event_type'] == 'tool.execution.started'}
        assert executed == set(analysis['tool_executions'])
        assert sum(e['event_type'] == 'llm.response.received' for e in events) == 4
        assert any(e['event_type'] == 'span.started' and e.get('span_name') == 'project.request.admitted' for e in events)
        rows = session.settings.ledger.read()
        assert sum(r['event'] == 'RESERVED_BEFORE_SEND' for r in rows) == 4
        assert sum(r['event'] == 'METERED' for r in rows) == 4
        assert {r['run_id'] for r in rows if r['event'] == 'RESERVED_BEFORE_SEND'} == {started['run_id']}
        assert session.settings.ledger.is_settled()
        assert session.settings.provider.budget_snapshot['attempts'] == 4
        assert wiki.semantic_state() == wiki_before
        assert {p.name: p.read_bytes() for p in root.iterdir()} == original_bytes
        persisted = session.app.state_root / 'user-results' / (started['run_id'] + '.json')
        assert json.loads(persisted.read_text(encoding='utf-8')) == result
        assert hashlib.sha256(persisted.read_bytes()).hexdigest()
    finally:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()
        session.app.components.close_loaded()
        session.app.plugins.close()
