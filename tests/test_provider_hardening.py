"""Provider configuration and failure classification stay safe and actionable."""

from __future__ import annotations

import json

import pytest

from agent_runtime.contracts import Message, ModelRequest
from agent_runtime.errors import ModelProviderError
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from agent_runtime.providers.openai_compatible import OpenAICompatibleModelProvider
from catalyst_platform import llm_provider


_REQUEST = ModelRequest(messages=[Message("user", "hello")])


@pytest.mark.parametrize(
    ("status", "provider_code", "category", "retryable"),
    [
        (400, "invalid_request_error", "invalid_request", False),
        (401, "invalid_api_key", "authentication", False),
        (402, "insufficient_quota", "billing", False),
        (403, "permission_denied", "permission", False),
        (404, "model_not_found", "not_found", False),
        (408, "timeout", "timeout", True),
        (429, "rate_limit_exceeded", "rate_limit", True),
        (429, "insufficient_quota", "billing", False),
        (500, "server_error", "provider_unavailable", True),
        (503, "overloaded", "provider_unavailable", True),
    ],
)
def test_deepseek_errors_are_classified_without_echoing_provider_body(
    status: int, provider_code: str, category: str, retryable: bool
):
    secret = "sk-private-provider-message"
    body = {
        "error": {
            "message": f"{secret}: vendor-specific diagnostic that may contain prompt data",
            "code": provider_code,
            "request_id": "req_deepseek_123",
        }
    }
    provider = DeepSeekModelProvider(
        api_key="sk-api-key-never-log",
        transport=lambda _url, _headers, _body: (status, body),
    )

    with pytest.raises(ModelProviderError) as caught:
        provider.request(_REQUEST)

    error = caught.value
    assert error.status == status
    assert error.code == provider_code
    assert error.category == category
    assert error.retryable is retryable
    assert error.request_id == "req_deepseek_123"
    assert secret not in str(error)
    assert "sk-api-key-never-log" not in str(error)
    assert "prompt data" not in str(error)


def test_openai_compatible_provider_preserves_safe_request_id_and_suppresses_raw_body():
    secret_detail = "provider body may echo user input: do-not-log-this"
    provider = OpenAICompatibleModelProvider(
        api_key="sk-private-api-key",
        model="example-model",
        base_url="https://provider.example/v1",
        transport=lambda _url, _headers, _body: (
            401,
            {"error": {"message": secret_detail, "code": "invalid_api_key"}},
            {"x-request-id": "req_safe_456"},
        ),
    )

    with pytest.raises(ModelProviderError) as caught:
        provider.request(_REQUEST)

    error = caught.value
    assert error.category == "authentication"
    assert error.provider_id == "openai-compatible"
    assert error.status == 401
    assert error.code == "invalid_api_key"
    assert error.request_id == "req_safe_456"
    assert secret_detail not in str(error)
    assert "sk-private-api-key" not in str(error)


@pytest.mark.parametrize(
    ("provider_cls", "provider_kwargs", "category"),
    [
        (DeepSeekModelProvider, {}, "timeout"),
        (
            OpenAICompatibleModelProvider,
            {"model": "example-model", "base_url": "https://provider.example/v1"},
            "timeout",
        ),
    ],
)
def test_transport_failure_is_safe_and_remains_single_attempt(
    provider_cls, provider_kwargs, category
):
    seen = []

    def transport(_url, _headers, _body):
        seen.append(1)
        raise TimeoutError("timeout with a secret-looking value sk-never-echo")

    provider = provider_cls(
        api_key="sk-never-echo",
        transport=transport,
        **provider_kwargs,
    )

    with pytest.raises(ModelProviderError) as caught:
        provider.request(_REQUEST)

    assert caught.value.category == category
    assert caught.value.retryable is True
    assert "sk-never-echo" not in str(caught.value)
    assert "secret-looking" not in str(caught.value)
    assert len(seen) == 1


def test_invalid_provider_request_id_is_not_persisted():
    provider = DeepSeekModelProvider(
        api_key="sk-private",
        transport=lambda _url, _headers, _body: (
            401,
            {"error": {"code": "invalid_api_key"}},
            {"x-request-id": "req-safe\r\nAuthorization: Bearer injected"},
        ),
    )

    with pytest.raises(ModelProviderError) as caught:
        provider.request(_REQUEST)

    assert caught.value.request_id is None
    assert "injected" not in str(caught.value)


def test_provider_does_not_record_exact_credential_echoed_as_code_or_request_id():
    key = "custom-provider-secret-8291"
    provider = DeepSeekModelProvider(
        api_key=key,
        transport=lambda _url, _headers, _body: (
            401,
            {"error": {"code": key, "request_id": key}},
        ),
    )

    with pytest.raises(ModelProviderError) as caught:
        provider.request(_REQUEST)

    assert caught.value.code is None
    assert caught.value.request_id is None
    assert key not in str(caught.value)


@pytest.mark.parametrize(
    "provider_factory",
    [
        lambda transport: DeepSeekModelProvider(api_key="sk-private", transport=transport),
        lambda transport: OpenAICompatibleModelProvider(
            api_key="sk-private",
            model="example-model",
            base_url="https://provider.example/v1",
            transport=transport,
        ),
    ],
)
def test_malformed_success_response_is_protocol_error_without_echoing_body(provider_factory):
    private = "sk-private-response-content"
    provider = provider_factory(
        lambda _url, _headers, _body: (
            200,
            {"choices": [{"message": {"role": private, "content": private}}]},
        )
    )

    with pytest.raises(ModelProviderError) as caught:
        provider.request(_REQUEST)

    assert caught.value.category == "protocol"
    assert private not in str(caught.value)


def test_interactive_configuration_is_one_run_only_and_never_calls_provider(
    monkeypatch,
):
    secret = "sk-interactive-only"
    monkeypatch.delenv("CATALYST_LLM_API_KEY", raising=False)
    provider = llm_provider.configured_model_provider_interactively(
        secret_input_fn=lambda _prompt: secret,
    )

    assert provider.provider_id == "deepseek"
    assert provider.model == "deepseek-flash"
    assert provider.request_count == 0
    assert provider.external_calls == 0
    assert "CATALYST_LLM_API_KEY" not in __import__("os").environ
    assert secret not in repr(provider)


def test_interactive_openai_compatible_requires_only_model_url_and_hidden_key():
    values = iter(["example-model", "https://provider.example/v1"])
    provider = llm_provider.configured_model_provider_interactively(
        provider_id="openai-compatible",
        input_fn=lambda _prompt: next(values),
        secret_input_fn=lambda _prompt: "sk-one-run-only",
    )

    assert provider.provider_id == "openai-compatible"
    assert provider.model == "example-model"
    assert provider._delegate.base_url == "https://provider.example/v1"
    assert provider.configuration_source == "interactive_once"
    assert "sk-one-run-only" not in repr(provider)


def test_environment_configuration_uses_current_deepseek_default_model(monkeypatch):
    monkeypatch.setenv("CATALYST_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("CATALYST_LLM_API_KEY", "sk-environment-only")
    monkeypatch.delenv("CATALYST_LLM_MODEL", raising=False)
    monkeypatch.delenv("CATALYST_LLM_BASE_URL", raising=False)

    provider = llm_provider.configured_model_provider_from_environment()

    assert provider.model == "deepseek-flash"
    assert provider.request_count == 0
    assert provider.external_calls == 0


def test_interactive_configuration_fails_before_secret_prompt_for_invalid_provider(
    monkeypatch,
):
    secret_prompted = []
    monkeypatch.setattr(
        llm_provider.getpass,
        "getpass",
        lambda _prompt: secret_prompted.append(True) or "sk-never-used",
    )

    with pytest.raises(llm_provider.ModelProviderConfigurationError) as caught:
        llm_provider.configured_model_provider_interactively(
            provider_id="unsupported-provider",
            secret_input_fn=lambda _prompt: secret_prompted.append(True) or "sk-never-used",
        )

    assert caught.value.code == "llm_provider_configuration_invalid"
    assert "deepseek" in str(caught.value)
    assert not secret_prompted


def test_interactive_configuration_reports_cancel_without_key_or_external_call(
    monkeypatch,
):
    with pytest.raises(llm_provider.ModelProviderConfigurationError) as caught:
        llm_provider.configured_model_provider_interactively(
            secret_input_fn=lambda _prompt: "",
        )

    assert caught.value.code == "llm_provider_setup_cancelled"
    assert "API Key cannot be empty" in str(caught.value)


def test_interactive_configuration_catches_unexpected_prompt_runtime_error():
    with pytest.raises(llm_provider.ModelProviderConfigurationError) as caught:
        llm_provider.configured_model_provider_interactively(
            secret_input_fn=lambda _prompt: (_ for _ in ()).throw(RuntimeError("private detail")),
        )

    assert caught.value.code == "llm_provider_secure_input_unavailable"
    assert "private detail" not in str(caught.value)


def test_cli_uses_interactive_provider_for_an_ask_without_persisting_key(
    tmp_path, monkeypatch, capsys
):
    import catalyst_platform.__main__ as cli
    from agent_runtime.contracts import ModelResponse

    class OneAnswerProvider:
        provider_id = "deepseek"
        model = "test-model"
        mode = "live"
        configuration_source = "interactive_once"
        request_count = 0
        external_calls = 0

        def request(self, _request):
            self.request_count += 1
            self.external_calls += 1
            return ModelResponse(content="The answer is 42.", finish_reason="stop")

    provider = OneAnswerProvider()
    monkeypatch.setattr(cli, "_secure_interactive_terminal_available", lambda: True)
    configured = []
    monkeypatch.setattr(
        cli,
        "configured_model_provider_interactively",
        lambda **kwargs: configured.append(kwargs) or provider,
    )
    code = cli.main(
        [
            "ask",
            "--interactive-provider",
            "--workspace",
            str(tmp_path / "workspace"),
            "--message",
            "What is 6 times 7?",
        ]
    )
    response = json.loads(capsys.readouterr().out)

    assert code == 0
    assert response["status"] == "success"
    assert response["result"]["output"]["answer"] == "The answer is 42."
    assert configured == [{"provider_id": "deepseek"}]
    inspected = cli.CatalystGateway(tmp_path / "workspace").inspect_run(response["run_id"])
    assert inspected is not None
    started = next(event for event in inspected["events"] if event["event_type"] == "llm.request.started")
    assert started["configuration_source"] == "interactive_once"
    assert inspected["events"][-1]["external_calls"] == 1


def test_cli_refuses_interactive_key_input_without_a_tty_and_persists_failure(
    tmp_path, monkeypatch, capsys
):
    import catalyst_platform.__main__ as cli

    monkeypatch.setattr(cli, "_secure_interactive_terminal_available", lambda: False)
    monkeypatch.setattr(
        cli,
        "configured_model_provider_interactively",
        lambda **_kwargs: pytest.fail("must not request a key without a secure terminal"),
    )
    code = cli.main(
        [
            "ask",
            "--interactive-provider",
            "--workspace",
            str(tmp_path / "workspace"),
            "--message",
            "Answer this simple question.",
        ]
    )
    response = json.loads(capsys.readouterr().out)

    assert code == 1
    assert response["status"] == "failure"
    assert response["error"]["code"] == "llm_provider_secure_input_unavailable"
    assert response["error"]["details"]["stage"] == "provider_configuration"
    inspected = cli.CatalystGateway(tmp_path / "workspace").inspect_run(response["run_id"])
    assert inspected is not None
    failed = next(event for event in inspected["events"] if event["event_type"] == "llm.request.failed")
    assert failed["error_stage"] == "provider_configuration"
    terminal = inspected["events"][-1]
    assert terminal["external_calls"] == 0


def test_provider_configuration_rejects_header_injection_and_bad_timeout(monkeypatch):
    monkeypatch.setenv("CATALYST_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("CATALYST_LLM_API_KEY", "sk-safe\r\nX-Injected: yes")
    with pytest.raises(llm_provider.ModelProviderConfigurationError) as bad_key:
        llm_provider.configured_model_provider_from_environment()
    assert bad_key.value.code == "llm_provider_configuration_invalid"
    assert "sk-safe" not in str(bad_key.value)

    monkeypatch.setenv("CATALYST_LLM_API_KEY", "sk-safe")
    monkeypatch.setenv("CATALYST_LLM_TIMEOUT_SECONDS", "nan")
    with pytest.raises(llm_provider.ModelProviderConfigurationError) as bad_timeout:
        llm_provider.configured_model_provider_from_environment()
    assert bad_timeout.value.code == "llm_provider_configuration_invalid"
    assert "finite" in str(bad_timeout.value)


def test_external_call_count_starts_at_transport_boundary_not_provider_entry():
    calls = []
    delegate = DeepSeekModelProvider(
        api_key="test-key",
        transport=lambda _url, _headers, _body: calls.append("transport")
        or (_ for _ in ()).throw(TimeoutError("offline test")),
    )
    provider = llm_provider.ObservedModelProvider(
        "deepseek", "deepseek-flash", delegate, "test"
    )

    with pytest.raises(ModelProviderError):
        provider.request(
            ModelRequest(
                messages=[Message("user", "hello")],
                parameters={"unsupported": True},
            )
        )
    assert provider.request_count == 1
    assert provider.external_calls == 0
    assert not calls

    with pytest.raises(ModelProviderError):
        provider.request(_REQUEST)
    assert provider.request_count == 2
    assert provider.external_calls == 1
    assert calls == ["transport"]


def test_r3_trace_exposes_safe_provider_diagnostics_without_raw_error_body(
    tmp_path, monkeypatch, capsys
):
    import catalyst_platform.__main__ as cli
    class FailedProvider:
        provider_id = "openai-compatible"
        model = "test-model"
        mode = "live"
        request_count = 0
        external_calls = 0

        def request(self, _request):
            self.request_count += 1
            self.external_calls += 1
            raise ModelProviderError(
                "Authentication failed. Check the API key.",
                status=401,
                code="invalid_api_key",
                request_id="req-safe-trace-1",
                provider_id=self.provider_id,
                category="authentication",
                retryable=False,
            )

    provider = FailedProvider()
    monkeypatch.setattr(cli, "configured_model_provider_from_environment", lambda: provider)
    monkeypatch.setattr(cli, "configured_model_provider_interactively", lambda: provider)
    code = cli.main(
        [
            "ask",
            "--workspace",
            str(tmp_path / "workspace"),
            "--message",
            "Answer this simple question.",
        ]
    )
    response = json.loads(capsys.readouterr().out)

    assert code == 1
    assert response["status"] == "failure"
    assert response["error"]["code"] == "llm_provider_authentication"
    assert response["error"]["details"]["request_id"] == "req-safe-trace-1"
    assert response["error"]["details"]["status"] == 401
    assert "Check the API key" in response["error"]["message"]
    inspected = cli.CatalystGateway(tmp_path / "workspace").inspect_run(response["run_id"])
    assert inspected is not None
    failed = next(event for event in inspected["events"] if event["event_type"] == "llm.request.failed")
    assert failed["error_category"] == "authentication"
    assert failed["http_status"] == 401
    assert failed["provider_request_id"] == "req-safe-trace-1"
    assert "sk-private-api-key" not in json.dumps(inspected)


def test_cli_adds_an_explicit_interactive_provider_option():
    parser = __import__("catalyst_platform.__main__", fromlist=["_build_parser"])._build_parser()
    ask_parser = next(
        action
        for action in parser._actions
        if action.dest == "command"
    ).choices["ask"]
    args = parser.parse_args(
        ["ask", "--interactive-provider", "--workspace", ".", "--message", "hello"]
    )
    assert args.interactive_provider == "deepseek"
    alternate = parser.parse_args(
        [
            "ask",
            "--interactive-provider",
            "openai-compatible",
            "--workspace",
            ".",
            "--message",
            "hello",
        ]
    )
    assert alternate.interactive_provider == "openai-compatible"


def test_deepseek_semantic_request_emits_json_mode_and_preserves_cache_usage():
    captured = {}
    body = {"choices": [{"message": {"role": "assistant", "content": '{"items":[]}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 23, "completion_tokens": 7,
                      "prompt_cache_hit_tokens": 5, "prompt_cache_miss_tokens": 18,
                      "prompt_tokens_details": {"cached_tokens": 5}}}
    def transport(url, _headers, raw):
        captured['url'] = url
        captured['body'] = json.loads(raw)
        return 200, body
    provider = DeepSeekModelProvider(api_key='test-secret', timeout=4, transport=transport)
    request = ModelRequest(messages=[Message('system', 'Return JSON {"items":[]}'), Message('user', '{}')],
                           parameters={'max_tokens': 4096, 'response_format': {'type': 'json_object'}})
    response = provider.request(request)
    assert captured['url'] == 'https://api.deepseek.com/chat/completions'
    assert captured['body']['model'] == 'deepseek-flash'
    assert captured['body']['thinking'] == {'type': 'disabled'}
    assert captured['body']['response_format'] == {'type': 'json_object'}
    assert captured['body']['max_tokens'] == 4096
    assert response.usage.input_tokens == 23 and response.usage.output_tokens == 7
    assert response.usage.cache_hit_input_tokens == 5
    assert response.usage.cache_miss_input_tokens == 18


def test_deepseek_rejects_unapproved_request_parameters_before_transport():
    calls = []
    provider = DeepSeekModelProvider(api_key='test-secret', transport=lambda *_: calls.append(1))
    request = ModelRequest(messages=[Message('user', 'hello')], parameters={'temperature': 0.2})
    with pytest.raises(ModelProviderError, match='unsupported request parameters'):
        provider.request(request)
    assert calls == []


def test_live_model_trace_records_prompt_cache_accounting(tmp_path):
    from catalyst_platform.observability import ObservedModelProvider as TraceProvider
    from catalyst_platform.observability import RunRecorder
    from catalyst_platform.trace_log import JsonlTraceStore
    response_body = {"choices": [{"message": {"role": "assistant", "content": '{"items":[]}'}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 23, "completion_tokens": 7,
                               "prompt_cache_hit_tokens": 5, "prompt_cache_miss_tokens": 18}}
    transport_calls = []
    def transport(_url, _headers, _raw):
        transport_calls.append(1)
        return 200, response_body
    base = DeepSeekModelProvider(api_key='test-secret', timeout=4, transport=transport)
    configured = llm_provider.ObservedModelProvider('deepseek', 'deepseek-flash', base, 'test')
    trace_store = JsonlTraceStore(tmp_path)
    recorder = RunRecorder(trace_store, run_id='cache-accounting', request_id='request-cache',
                           invocation_id='inv-cache', trace_id='a' * 32, event_schema_version='1.5')
    recorder.start(request_kind='test', actor='test_client', component='test')
    traced = TraceProvider(configured, recorder, invocation_id='extraction-call')
    traced.request(ModelRequest(messages=[Message('system', 'JSON output'), Message('user', '{}')],
                                parameters={'max_tokens': 4096, 'response_format': {'type': 'json_object'}}))
    events = trace_store.inspect_run('cache-accounting')['events']
    response_event = next(event for event in events if event['event_type'] == 'llm.response.received')
    assert response_event['input_tokens'] == 23 and response_event['output_tokens'] == 7
    assert response_event['cache_hit_input_tokens'] == 5
    assert response_event['cache_miss_input_tokens'] == 18
    assert len(transport_calls) == configured.external_calls == 1
    recorder.finish(status='success', model_calls=1)
