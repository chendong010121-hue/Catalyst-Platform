"""Offline capture at the existing governed provider interface."""
import json
import threading

import pytest

from agent_runtime.contracts import Message, ModelRequest
from catalyst_platform.llm_controls import ModelControlError, ModelTask
from catalyst_platform.llm_provider import configured_model_provider


def configured(provider_id='deepseek', *, content='{}', before_request=None,
               max_requests=2, transport=None):
    sent = []

    def offline(url, headers, body):
        sent.append(json.loads(body))
        return 200, dict(id='offline', choices=[dict(index=0, message=dict(
            role='assistant', content=content), finish_reason='stop')],
            usage=dict(prompt_tokens=10, completion_tokens=2, total_tokens=12))

    task = ModelTask('offline', provider_id, 'offline-model', max_requests, '1',
                     10000, 100, '1', '1', '1', 'offline-declaration')
    provider = configured_model_provider(
        provider_id=provider_id, api_key='offline-placeholder', model=task.model,
        base_url='https://offline.invalid', task=task,
        transport=transport or offline, before_request=before_request)
    return provider, sent


def request(**parameters):
    return ModelRequest(messages=(Message(role='user', content='offline'),),
                        parameters=parameters)


@pytest.mark.parametrize('provider_id', ['deepseek', 'openai-compatible'])
def test_original_request_and_raw_response_share_existing_budget(provider_id):
    observed = []
    provider, sent = configured(provider_id, before_request=observed.append)
    original = request(response_format={'type': 'json_object'})
    with provider.capture_calls() as calls:
        response = provider.request(original)
    assert observed == [original]
    assert calls == [dict(request=original, response=response, error=None, dispatched=True)]
    assert calls[0]['request'] is original
    assert sent[0]['max_tokens'] == 100
    assert 'max_tokens' not in original.parameters
    assert provider.external_calls == provider.budget_snapshot['attempts'] == 1
    assert set(calls[0]) == {'request', 'response', 'error', 'dispatched'}


def test_invalid_json_response_captured_before_validation_and_cleanup():
    provider, _ = configured(content='invalid JSON')
    with pytest.raises(ModelControlError) as caught:
        with provider.capture_calls() as calls:
            provider.request(request(response_format={'type': 'json_object'}))
    assert calls[0]['response'].content == 'invalid JSON'
    assert calls[0]['error'] is caught.value
    assert calls[0]['dispatched'] is True
    with provider.capture_calls() as next_calls:
        pass
    assert next_calls == []


def test_hook_is_under_budget_lock_and_its_error_prevents_dispatch():
    failure = RuntimeError('host refusal')
    def refuse(original):
        assert provider._budget.lock.locked()
        assert 'max_tokens' not in original.parameters
        raise failure
    provider, sent = configured(before_request=refuse)
    with provider.capture_calls() as calls, pytest.raises(RuntimeError) as caught:
        provider.request(request())
    assert caught.value is failure
    assert calls[0]['error'] is failure
    assert calls[0]['response'] is None
    assert calls[0]['dispatched'] is False
    assert sent == []


def test_prepare_rejection_and_transport_error_are_distinct():
    provider, sent = configured()
    with provider.capture_calls() as calls, pytest.raises(ModelControlError):
        provider.request(request(n=2))
    assert calls[0]['dispatched'] is False
    assert sent == []

    def broken(*args):
        raise TimeoutError('offline')
    provider, _ = configured(transport=broken)
    with provider.capture_calls() as calls, pytest.raises(Exception):
        provider.request(request())
    assert calls[0]['dispatched'] is True
    assert calls[0]['response'] is None
    assert calls[0]['error'] is not None
    assert provider.budget_snapshot['uncertain'] is True
    with pytest.raises(ModelControlError) as caught:
        provider.request(request())
    assert caught.value.code == 'llm_usage_uncertain'
    assert provider.external_calls == 1


def test_capture_bound_nested_concurrent_and_shared_ledger():
    provider, sent = configured(max_requests=1)
    with provider.capture_calls() as calls:
        with pytest.raises(ModelControlError):
            with provider.capture_calls():
                pass
        failures = []
        def concurrent_scope():
            try:
                with provider.capture_calls():
                    pass
            except ModelControlError as exc:
                failures.append(exc)
        thread = threading.Thread(target=concurrent_scope)
        thread.start()
        thread.join(timeout=2)
        assert len(failures) == 1
        provider.request(request())
        with pytest.raises(ModelControlError):
            provider.request(request())
        assert len(calls) == 1
    with provider.capture_calls() as next_calls, pytest.raises(ModelControlError) as caught:
        provider.request(request())
    assert caught.value.code == 'llm_request_limit'
    assert next_calls[0]['dispatched'] is False
    assert len(sent) == 1


def test_before_hook_failure_after_success_does_not_invent_uncertainty():
    seen = []
    def guard(original):
        if seen:
            raise RuntimeError('offline host refusal')
        seen.append(original)
    provider, _ = configured(before_request=guard)
    with provider.capture_calls() as calls:
        provider.request(request())
        with pytest.raises(RuntimeError):
            provider.request(request())
    assert [call['dispatched'] for call in calls] == [True, False]
    assert provider.budget_snapshot['uncertain'] is False


def test_cancelled_task_stays_blocked_with_capture():
    provider, sent = configured()
    provider.cancel()
    with provider.capture_calls() as calls, pytest.raises(ModelControlError) as caught:
        provider.request(request())
    assert caught.value.code == 'llm_cancelled'
    assert calls[0]['dispatched'] is False
    assert calls[0]['response'] is None
    assert sent == []


def test_caller_cannot_extend_capture_bound_by_clearing_records():
    provider, sent = configured(max_requests=1)
    with provider.capture_calls() as calls:
        with pytest.raises(ModelControlError):
            provider.request(request(n=2))
        calls.clear()
        with pytest.raises(ModelControlError) as caught:
            provider.request(request())
    assert caught.value.code == 'llm_capture_limit'
    assert sent == []


def test_foreign_thread_request_cannot_enter_active_capture():
    provider, sent = configured()
    failures = []
    def foreign_request():
        try:
            provider.request(request())
        except ModelControlError as exc:
            failures.append(exc)
    with provider.capture_calls() as calls:
        thread = threading.Thread(target=foreign_request)
        thread.start()
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert len(failures) == 1
        assert failures[0].code == 'llm_capture_busy'
        assert calls == []
        provider.request(request())
    assert len(calls) == len(sent) == 1
