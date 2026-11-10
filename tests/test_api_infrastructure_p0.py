"""Offline controls at the existing factory/transport seam; no live requests."""
import json
import threading
from pathlib import Path
from dataclasses import replace
from decimal import Decimal

import pytest

from agent_runtime.contracts import Message, ModelRequest
from agent_runtime.errors import ModelProviderError
from catalyst_platform import llm_provider as lp


def task(**changes):
    from catalyst_platform.llm_controls import ModelTask
    values = dict(task_id='synthetic-task', provider_id='deepseek', model='deepseek-flash',
                  max_requests=2, budget_cny='1', input_token_limit=16000, max_output_tokens=4096,
                  input_cny_per_million='2', output_cny_per_million='4',
                  cache_hit_cny_per_million='0.2', price_reference='synthetic-offline-rate')
    return ModelTask(**(values | changes))


def response(usage=True, content='{"ok":true}'):
    value = {'choices': [{'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}]}
    if usage:
        value['usage'] = {'prompt_tokens': 100, 'completion_tokens': 20,
                          'prompt_cache_hit_tokens': 40, 'prompt_cache_miss_tokens': 60}
    return value


def provider(monkeypatch, declaration=None, transport=None):
    from agent_runtime.providers.deepseek import DeepSeekModelProvider
    seen = []
    def send(url, headers, body):
        seen.append(json.loads(body))
        return transport(url, headers, body) if transport else (200, response())
    monkeypatch.setattr(lp, 'DeepSeekModelProvider', lambda **kw: DeepSeekModelProvider(**kw, transport=send))
    value = lp.configured_model_provider(provider_id='deepseek', model='deepseek-flash',
                                        api_key='offline-dummy', base_url='', task=declaration)
    return value, seen


REQUEST = ModelRequest(messages=[Message('user', 'Return JSON for a synthetic example.')],
                       parameters={'response_format': {'type': 'json_object'}})


def test_configured_provider_requires_explicit_budget_before_send(monkeypatch):
    p, seen = provider(monkeypatch)
    with pytest.raises(ValueError, match='task'):
        p.request(REQUEST)
    assert seen == [] and p.external_calls == 0


def test_explicit_task_exact_model_and_cache_cost(monkeypatch):
    p, seen = provider(monkeypatch, task())
    assert json.loads(p.request(REQUEST).content) == {'ok': True}
    assert seen[0]['model'] == 'deepseek-flash'
    assert seen[0]['thinking'] == {'type': 'disabled'}
    assert seen[0]['max_tokens'] == 4096
    assert seen[0]['response_format'] == {'type': 'json_object'}
    assert p.budget_snapshot['attempts'] == 1
    assert Decimal(p.budget_snapshot['charged_cny']) == Decimal('0.000208')
    assert p.budget_snapshot['last_status'] == 'metered'


@pytest.mark.parametrize('change', [{'model': 'expensive-other'}, {'provider_id': 'openai-compatible'}])
def test_task_identity_never_falls_back(monkeypatch, change):
    with pytest.raises(ValueError, match='identity'):
        provider(monkeypatch, task(**change))


def test_budget_and_request_limits_precede_dispatch(monkeypatch):
    p, seen = provider(monkeypatch, task(budget_cny='0.001'))
    with pytest.raises(ValueError, match='budget'):
        p.request(REQUEST)
    assert seen == []
    p, seen = provider(monkeypatch, task(max_requests=1))
    p.request(REQUEST)
    with pytest.raises(ValueError, match='request limit'):
        p.request(REQUEST)
    assert len(seen) == 1


@pytest.mark.parametrize('mode', ['usage_missing', 'timeout', 'http', 'malformed'])
def test_unknown_spend_retains_reserve_and_prevents_retry(monkeypatch, mode):
    def transport(*_):
        if mode == 'timeout':
            raise TimeoutError('secret response must not leak')
        if mode == 'http':
            return 429, {'error': {'message': 'secret', 'code': 'rate_limit_exceeded'}}
        if mode == 'malformed':
            return 200, {'choices': 'invalid'}
        return 200, response(usage=False)
    p, seen = provider(monkeypatch, task(), transport)
    with pytest.raises((ValueError, ModelProviderError)):
        p.request(REQUEST)
    snapshot = p.budget_snapshot
    assert snapshot['attempts'] == 1 and snapshot['uncertain'] is True
    assert Decimal(snapshot['charged_cny']) == Decimal('0.048384')
    with pytest.raises(ValueError, match='uncertain'):
        p.request(REQUEST)
    assert len(seen) == 1


def test_cancel_before_and_during_request_does_not_mean_refund(monkeypatch):
    p, seen = provider(monkeypatch, task())
    p.cancel()
    with pytest.raises(ValueError, match='cancel'):
        p.request(REQUEST)
    assert seen == []
    p, seen = provider(monkeypatch, task(), lambda *_: (p.cancel(), (200, response()))[1])
    with pytest.raises(ValueError, match='cancel'):
        p.request(REQUEST)
    assert len(seen) == 1
    assert Decimal(p.budget_snapshot['charged_cny']) > 0


def test_invalid_json_rejected_after_usage_accounted(monkeypatch):
    p, seen = provider(monkeypatch, task(), lambda *_: (200, response(content='not json')))
    with pytest.raises(ValueError, match='JSON') as caught:
        p.request(REQUEST)
    assert caught.value.category == 'protocol'
    assert len(seen) == 1 and Decimal(p.budget_snapshot['charged_cny']) > 0


@pytest.mark.parametrize('parameters', [{'max_tokens': 4097}, {'max_tokens': True}, {'max_completion_tokens': 4097}])
def test_output_bound_cannot_be_overridden(monkeypatch, parameters):
    p, seen = provider(monkeypatch, task())
    with pytest.raises(ValueError):
        p.request(replace(REQUEST, parameters=parameters))
    assert seen == []


def test_input_bound_and_usage_overrun_fail_closed(monkeypatch):
    p, seen = provider(monkeypatch, task(input_token_limit=1))
    with pytest.raises(ValueError, match='input'):
        p.request(REQUEST)
    assert seen == []
    def overrun(*_):
        result = response()
        result['usage']['completion_tokens'] = 5000
        return 200, result
    p, seen = provider(monkeypatch, task(), overrun)
    with pytest.raises(ValueError, match='bound'):
        p.request(REQUEST)
    assert p.budget_snapshot['uncertain']


def test_credential_priority_is_explicit_generic_then_selected_provider():
    resolve = lp.resolve_api_key
    env = {'CATALYST_LLM_API_KEY': 'generic-dummy', 'DEEPSEEK_API_KEY': 'deepseek-dummy', 'OPENAI_API_KEY': 'unrelated'}
    assert resolve('deepseek', explicit='explicit-dummy', environment=env) == 'explicit-dummy'
    assert resolve('deepseek', environment=env) == 'generic-dummy'
    assert resolve('deepseek', environment={'DEEPSEEK_API_KEY': 'deepseek-dummy'}) == 'deepseek-dummy'
    for args in [dict(provider_id='openai-compatible', environment={'DEEPSEEK_API_KEY': 'dummy'}),
                 dict(provider_id='deepseek', explicit='', environment=env),
                 dict(provider_id='deepseek', environment=env | {'CATALYST_LLM_API_KEY': ''})]:
        with pytest.raises(ValueError):
            resolve(**args)


def test_environment_standard_key_requires_explicit_provider_and_official_endpoint(monkeypatch):
    for name in ('CATALYST_LLM_API_KEY', 'CATALYST_LLM_PROVIDER', 'CATALYST_LLM_BASE_URL', 'CATALYST_LLM_TASK_JSON'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'offline-dummy')
    with pytest.raises(ValueError):
        lp.configured_model_provider_from_environment()
    monkeypatch.setenv('CATALYST_LLM_PROVIDER', 'deepseek')
    assert lp.configured_model_provider_from_environment().provider_id == 'deepseek'
    monkeypatch.setenv('CATALYST_LLM_BASE_URL', 'https://unrelated.example')
    with pytest.raises(ValueError):
        lp.configured_model_provider_from_environment()


@pytest.mark.parametrize('change', [{'budget_cny': 'NaN'}, {'input_cny_per_million': '-1'},
                                  {'max_requests': True}, {'price_reference': ''}, {'max_output_tokens': 0}])
def test_invalid_task_configuration_is_rejected(change):
    with pytest.raises(ValueError):
        task(**change)


@pytest.mark.parametrize('version', ['1.4', '1.5', '1.6'])
@pytest.mark.parametrize('failure', [False, True])
def test_r4_budget_identity_usage_and_errors_are_schema_valid(tmp_path, monkeypatch, version, failure):
    from jsonschema import Draft202012Validator
    from catalyst_platform.observability import ObservedModelProvider, RunRecorder
    from catalyst_platform.trace_log import JsonlTraceStore
    p, seen = provider(monkeypatch, task(), lambda *_: (200, response(usage=not failure)))
    store = JsonlTraceStore(tmp_path)
    recorder = RunRecorder(store, run_id='p0-budget', request_id='user-request', invocation_id='inv-p0',
                           trace_id='a' * 32, event_schema_version=version)
    recorder.start(request_kind='offline_p0')
    traced = ObservedModelProvider(p, recorder, invocation_id='inv-p0')
    if failure:
        with pytest.raises(ValueError):
            traced.request(REQUEST)
    else:
        traced.request(REQUEST)
    recorder.finish(status='failure' if failure else 'success', model_calls=1)
    events = store.inspect_run('p0-budget')['events']
    attrs = next(e['attributes'] for e in events if e['event_type'] == 'span.ended' and 'catalyst.llm.task_id' in e['attributes'])
    assert attrs['catalyst.llm.task_id'] == 'synthetic-task'
    assert attrs['catalyst.llm.attempts'] == 1
    assert attrs['catalyst.llm.request_id'] == p.budget_snapshot['request_id']
    assert attrs['catalyst.llm.uncertain'] is failure
    assert Decimal(attrs['catalyst.llm.charged_cny']) > 0
    schema = json.loads((Path(__file__).parents[1] / f'schemas/run_event_v{version.replace(".", "_")}.schema.json').read_text(encoding='utf-8'))
    for event in events:
        Draft202012Validator(schema).validate(event)
    raw = store.path.read_text(encoding='utf-8')
    assert 'offline-dummy' not in raw and 'synthetic example' not in raw


def test_concurrent_task_requests_cannot_double_spend(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def transport(*_):
        entered.set()
        assert release.wait(5)
        return 200, response()
    p, seen = provider(monkeypatch, task(max_requests=1), transport)
    results = []
    worker = threading.Thread(target=lambda: results.append(p.request(REQUEST)))
    worker.start()
    try:
        assert entered.wait(5)
        with pytest.raises(ValueError, match='Concurrent'):
            p.request(REQUEST)
    finally:
        release.set()
        worker.join(5)
    assert len(seen) == len(results) == 1


def test_environment_task_declaration_uses_existing_factory(monkeypatch):
    from dataclasses import asdict
    monkeypatch.setenv('CATALYST_LLM_TASK_JSON', json.dumps(asdict(task())))
    monkeypatch.setenv('CATALYST_LLM_API_KEY', 'offline-dummy')
    for name in ('CATALYST_LLM_PROVIDER', 'CATALYST_LLM_MODEL', 'CATALYST_LLM_BASE_URL'):
        monkeypatch.delenv(name, raising=False)
    configured = lp.configured_model_provider_from_environment()
    assert configured.model == task().model
    assert configured.budget_snapshot['budget_cny'] == '1'
    monkeypatch.setenv('CATALYST_LLM_MODEL', 'expensive-other')
    with pytest.raises(ValueError, match='identity'):
        lp.configured_model_provider_from_environment()


@pytest.mark.parametrize('backend', ['json', 'sqlite'])
def test_understand_plugin_uses_same_governed_provider_and_preserves_admission(tmp_path, monkeypatch, backend):
    from catalyst_platform.workbench import CatalystWorkbench
    from catalyst_platform.wiki import ProjectWiki
    from catalyst_platform.semantic_wiki import SemanticWiki, SemanticTransitionError
    from tests.test_p0_admission_identity import _recorder
    roots = tmp_path / 'sources'
    roots.mkdir()
    source = roots / 'org.txt'
    source.write_text('市场部负责客户线索。', encoding='utf-8')
    def transport(_url, _headers, raw):
        # Deterministic fixture builds a candidate from the real evidence IDs.
        payload = json.loads(json.loads(raw)['messages'][-1]['content'])
        evidence_id = payload['evidence'][0]['evidence_id']
        candidate = {'items': [dict(kind='entity', key='marketing', meaning='市场部',
                                    evidence_class='SOURCE_DIRECT', evidence_refs=[evidence_id])]}
        return 200, response(content=json.dumps(candidate, ensure_ascii=False))
    p, seen = provider(monkeypatch, task(input_token_limit=32000), transport)
    wiki = ProjectWiki(tmp_path / 'workspace', [roots], enterprise_id='synthetic', project_id='p0', backend=backend)
    recorder = _recorder(tmp_path / 'workspace', 'governed-understand')
    semantic = SemanticWiki(wiki, recorder=recorder)
    app = CatalystWorkbench(tmp_path / 'workspace', [roots])
    session = app.new_session(domain={'id': 'local'}, enterprise={'id': 'synthetic'})
    result = session.propose_enterprise_semantics(
        '整理企业本体', source_refs=[source], source_root=roots, semantic=semantic, provider=p,
        actor_context={'verified': True, 'simulation': True, 'permissions': ['knowledge.propose'], 'readable_scope_ids': [wiki.scope_id]},
        harvest=lambda result: [i.item_id for i in result.semantic_candidate.items if i.kind == 'entity'],
    )
    candidate_id = result['proposal']['candidate_id']
    assert len(seen) == 1 and p.budget_snapshot['attempts'] == 1
    assert wiki.semantic_state()['candidates'][candidate_id]['proposer_origin'] == 'catalyst_model'
    assert semantic.evaluate(candidate_id, actor_origin='independent_evaluator')['status'] == 'pass'
    with pytest.raises(SemanticTransitionError, match='verified external semantic evaluation'):
        semantic.decide(candidate_id, decision='ACCEPTED', actor_origin='manager_acceptance', reason_code='reviewed')
    assert wiki.semantic_state()['active_version_id'] is None


@pytest.mark.parametrize('usage', [None, {'prompt_tokens': True, 'completion_tokens': 1},
                                   {'prompt_tokens': 10, 'completion_tokens': -1}])
def test_openai_compatible_missing_or_invalid_usage_cannot_be_zero_cost(monkeypatch, usage):
    from agent_runtime.providers.openai_compatible import OpenAICompatibleModelProvider
    calls = []
    def transport(*_):
        calls.append(1)
        body = response(usage=False)
        if usage is not None:
            body['usage'] = usage
        return 200, body
    monkeypatch.setattr(lp, 'OpenAICompatibleModelProvider', lambda **kw: OpenAICompatibleModelProvider(**kw, transport=transport))
    p = lp.configured_model_provider(provider_id='openai-compatible', model='fixed-model', api_key='offline-dummy',
                                    base_url='https://provider.example', task=task(provider_id='openai-compatible', model='fixed-model'))
    with pytest.raises((ValueError, ModelProviderError)) as caught:
        p.request(REQUEST)
    if usage is not None:
        assert isinstance(caught.value, ModelProviderError) and caught.value.category == 'protocol'
    assert calls == [1] and p.budget_snapshot['uncertain']
    assert Decimal(p.budget_snapshot['charged_cny']) > 0


def test_url_transport_disables_implicit_redirect_and_keeps_timeout(monkeypatch):
    from agent_runtime.providers import _http
    import urllib.request
    captured = {}
    class Opener:
        def open(self, request, timeout):
            captured['timeout'] = timeout
            return 'synthetic-response'
    def build(handler):
        captured['handler'] = handler
        return Opener()
    monkeypatch.setattr(urllib.request, 'build_opener', build)
    request = urllib.request.Request('https://original.example', data=b'{}')
    assert _http.open_single_attempt(request, timeout=3) == 'synthetic-response'
    assert captured['timeout'] == 3
    assert captured['handler'].redirect_request(request, None, 302, 'redirect', {}, 'https://other.example') is None


@pytest.mark.parametrize('provider_kind', ['deepseek', 'openai-compatible'])
def test_adapters_use_single_attempt_transport(monkeypatch, provider_kind):
    import io
    from agent_runtime.providers import deepseek, openai_compatible
    module = deepseek if provider_kind == 'deepseek' else openai_compatible
    captured = []
    class FakeResponse(io.BytesIO):
        status = 200
        headers = {}
        def getcode(self):
            return 200
    def opener(request, *, timeout):
        captured.append(timeout)
        return FakeResponse(json.dumps(response()).encode())
    monkeypatch.setattr(module, 'open_single_attempt', opener)
    cls = module.DeepSeekModelProvider if provider_kind == 'deepseek' else module.OpenAICompatibleModelProvider
    p = cls(api_key='offline-dummy', model='fixed-model', base_url='https://provider.example', timeout=3)
    p.request(REQUEST)
    assert captured == [3]


@pytest.mark.parametrize('provider_kind', ['deepseek', 'openai-compatible'])
@pytest.mark.parametrize('status', [101, 302, 307])
def test_non_success_http_status_is_never_a_model_result(provider_kind, status):
    from agent_runtime.providers.deepseek import DeepSeekModelProvider
    from agent_runtime.providers.openai_compatible import OpenAICompatibleModelProvider
    cls = DeepSeekModelProvider if provider_kind == 'deepseek' else OpenAICompatibleModelProvider
    p = cls(api_key='offline-dummy', model='fixed-model', base_url='https://provider.example',
            transport=lambda *_: (status, response()))
    with pytest.raises(ModelProviderError) as caught:
        p.request(REQUEST)
    assert caught.value.category == 'protocol'
    assert caught.value.status == status
