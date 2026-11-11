"""The assistant reads this Workspace instead of describing it from the prompt."""
import json
import uuid

from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.workspace_status import (CAPABILITY_ID, CAPABILITY_VERSION,
                                                WorkspaceStatusCapability, collect,
                                                render_text, section_view)
from catalyst_platform.workbench import CapabilityCatalog
from tests.test_workspace_model_settings import FAKE_KEY, configuration, packet, run


def seed_run(session, *, state='CHAT_COMPLETED', mode='LIVE_CHAT', message='现在系统情况如何',
             input_tokens=523, output_tokens=64, error=None):
    root = session.workspace / '.catalyst' / 'user-results'
    root.mkdir(parents=True, exist_ok=True)
    run_id = 'run_' + uuid.uuid4().hex
    record = {'run_id': run_id, 'task_type': 'basic_chat', 'state': state, 'mode': mode,
              'provider': 'deepseek', 'model': 'deepseek-flash', 'external_calls': 1,
              'chat': {'thread_id': 'initial', 'message': message},
              'budget': {'input_tokens': input_tokens, 'output_tokens': output_tokens,
                         'charged_cny': '0.0001'},
              'error': error, 'result': {'output': {'answer': '此前的一次回答'}}}
    (root / (run_id + '.json')).write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
    return run_id


def seed_event(session, run_id, event_type, **fields):
    path = session.workspace / '.catalyst' / 'traces' / 'runs.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {'event_type': event_type, 'timestamp': '2026-11-11T05:00:00Z',
             'run_id': run_id, **fields}
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + '\n')


def status_tool_name():
    return CapabilityCatalog.internal_key(CAPABILITY_ID, CAPABILITY_VERSION)


def test_status_reads_real_runs_logs_usage_and_config(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'status')
    run_id = seed_run(session, message='PRIVATE-UNRELATED-CHAT')
    seed_event(session, run_id, 'llm.response.received', model='deepseek-flash',
               input_tokens=1000, output_tokens=80,
               cache_hit_input_tokens=750, cache_miss_input_tokens=250)
    seed_event(session, run_id, 'request.failed', error_code='MODEL_SCOPE_UNAVAILABLE')
    (session.workspace / '.catalyst' / 'workspace-settings').mkdir(parents=True, exist_ok=True)
    (session.workspace / '.catalyst' / 'workspace-settings' / 'profile.json').write_text(
        '{"display_name":"本地用户"}', encoding='utf-8')

    result = WorkspaceStatusCapability(session).invoke({}, None)

    assert result.data['runs']['total'] == 1
    latest = result.data['runs']['recent'][0]
    assert latest['run_id'] == run_id and latest['state'] == 'CHAT_COMPLETED'
    assert latest['input_tokens'] == 523
    assert 'PRIVATE-UNRELATED-CHAT' not in json.dumps(result.data)
    assert str(session.workspace) not in json.dumps(result.data, ensure_ascii=False).replace('\\\\', '\\')
    assert result.data['usage']['measured_calls'] == 1
    assert result.data['usage']['cache_hit_rate'] == 0.75
    assert result.data['logs']['recent_failures'] == 1
    profile = next(row for row in result.data['config']['files'] if row['file'].endswith('profile.json'))
    assert profile['present'] is True
    assert 'state_root' not in result.data['workspace']


def test_status_never_returns_the_credential(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'key')
    session.settings = WorkspaceSettings(session.app, transport=lambda *args: (200, packet()))
    session.settings.configure(configuration())
    result = WorkspaceStatusCapability(session).invoke({}, None)
    assert result.data['model']['configured'] is True
    assert FAKE_KEY not in json.dumps(result.data, ensure_ascii=False)


def test_status_sections_do_not_mix_unrequested_evidence(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'section')
    run_id = seed_run(session)
    snapshot = collect(session)
    only_runs = section_view(snapshot, 'runs')
    assert only_runs['section'] == 'runs' and only_runs['runs']['recent'][0]['run_id'] == run_id
    assert set(only_runs) == {'generated_at', 'section', 'runs'}
    only_logs = section_view(snapshot, 'logs')
    assert 'model' not in only_logs and 'runs' not in only_logs


def test_local_info_reports_the_workspace_instead_of_a_brochure(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'local')
    run_id = seed_run(session)
    result = run(session)
    assert result['mode'] == 'LOCAL_INFO' and result['external_calls'] == 0
    answer = result['result']['output']['answer']
    assert 'Catalyst Workplace 本机状态' in answer and run_id in answer
    assert '运行记录：1 条' in answer
    assert '长期职责有 Harness' not in answer
    assert result['local_status']['runs_total'] == 1


def test_model_must_read_status_before_answering_and_the_read_is_verified(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'tool')
    run_id = seed_run(session)
    requests = []

    def transport(url, headers, body):
        request = json.loads(body)
        requests.append(request)
        if len(requests) == 1:
            names = {tool['function']['name'] for tool in request['tools']}
            assert status_tool_name() in names
            assert '必须先调用 workspace_status' in json.dumps(request['messages'], ensure_ascii=False)
            response = packet()
            response['choices'][0]['message'] = {
                'role': 'assistant', 'content': None,
                'tool_calls': [{'id': 'status-call', 'type': 'function',
                                'function': {'name': status_tool_name(), 'arguments': '{"section":"all"}'}}]}
            response['choices'][0]['finish_reason'] = 'tool_calls'
            return 200, response
        tool = next(message for message in request['messages'] if message['role'] == 'tool')
        assert run_id in tool['content'] and 'CHAT_COMPLETED' in tool['content']
        return 200, packet('本机最近一条运行是 ' + run_id + '。')

    session.settings = WorkspaceSettings(session.app, transport=transport)
    session.settings.configure(configuration())
    result = run(session, '现在系统情况如何？')

    assert result['state'] == 'CHAT_COMPLETED' and result['workspace_status_read_verified'] is True
    assert len(requests) == 2
    from catalyst_platform.trace_log import JsonlTraceStore
    events = JsonlTraceStore(session.workspace).inspect_run(result['run_id'])['events']
    assert any(event['event_type'] == 'tool.execution.started'
               and event['capability_id'] == CAPABILITY_ID for event in events)


def test_an_answer_without_the_tool_is_not_presented_as_a_status_read(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'no-read')
    session.settings = WorkspaceSettings(session.app,
                                        transport=lambda *args: (200, packet('据我所知系统运行正常。')))
    session.settings.configure(configuration())
    result = run(session, '系统现在什么状态？')
    assert result['state'] == 'CHAT_COMPLETED'
    assert result['workspace_status_read_verified'] is False


def test_a_foreign_status_binding_stops_before_the_provider(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'collision')
    foreign = WorkspaceUserSession(tmp_path / 'foreign')
    session.app._catalog.register(WorkspaceStatusCapability(foreign),
                                  capability_version=CAPABILITY_VERSION,
                                  execution={'side_effect': 'none'}, metadata={
                                      'component_id': 'workspace-status',
                                      'component_version': '0.1.0',
                                      'llm_visibility': 'explicit',
                                      'model_policy': {'mode': 'workspace_scoped_query', 'max_calls': 1}})
    calls = []
    session.settings = WorkspaceSettings(session.app,
                                        transport=lambda *args: (calls.append(1) or (200, packet())))
    session.settings.configure(configuration())
    result = run(session, '系统现在什么状态？')
    assert result['state'] == 'BLOCKED' and result['error']['code'] == 'STATUS_TOOL_BINDING_CONFLICT'
    assert calls == []


def test_render_text_states_missing_usage_instead_of_zero(tmp_path):
    session = WorkspaceUserSession(tmp_path / 'empty')
    text = render_text(collect(session))
    assert 'Token：本机记录中没有可用的缓存命中数据。' in text
    assert '运行记录：0 条' in text
