"""Explicit, one-run model provider configuration for the local Catalyst CLI."""

from __future__ import annotations

import getpass
import json
import math
import os
import warnings
import threading
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Mapping
from urllib.parse import urlsplit

from agent_runtime.contracts import ModelRequest, ModelResponse
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from agent_runtime.providers.openai_compatible import OpenAICompatibleModelProvider
from .llm_controls import ModelControlError, ModelTask, TaskBudget


_DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"
_DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class ModelProviderConfigurationError(ValueError):
    """A safe setup error which is known to occur before any external request."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.category = "configuration"
        self.stage = "provider_configuration"
        self.public_code = code

    @property
    def safe_message(self) -> str:
        return str(self)

    @property
    def safe_details(self) -> dict[str, object]:
        return {
            "provider_id": None,
            "category": self.category,
            "stage": self.stage,
            "status": None,
            "provider_code": None,
            "request_id": None,
            "retryable": False,
        }


class ObservedModelProvider:
    """Count provider attempts for one Runtime without retaining credentials."""

    def __init__(
        self, provider_id: str, model: str, delegate: Any, configuration_source: str,
        *, task: ModelTask | None = None, require_task: bool = False,
        before_request: Callable[[ModelRequest], None] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.model = model
        self.mode = "live"
        self.configuration_source = configuration_source
        self.external_calls = 0
        self.request_count = 0
        self._delegate = delegate
        self._closed = False
        self._require_task = require_task
        self._before_request = before_request
        self._capture_lock = threading.Lock()
        self._capture_records: list[dict[str, Any]] | None = None
        self._capture_owner: int | None = None
        self._capture_count = 0
        self._active_record: dict[str, Any] | None = None
        if task is not None and (task.provider_id, task.model) != (provider_id, model):
            raise ModelProviderConfigurationError('llm_task_identity_mismatch', 'Task provider/model identity must match configuration exactly.')
        self._budget = TaskBudget(task) if task is not None else None
        observer = getattr(delegate, "set_external_call_observer", None)
        if task is not None and not callable(observer):
            raise ModelProviderConfigurationError('llm_transport_unobservable', 'Governed execution requires a dispatch observer.')
        if callable(observer):
            observer(self._record_external_call)

    def _record_external_call(self) -> None:
        if self._budget is not None:
            self._budget.dispatch()
        self.external_calls += 1
        if self._active_record is not None:
            self._active_record['dispatched'] = True

    @contextmanager
    def capture_calls(self) -> Iterator[list[dict[str, Any]]]:
        """Capture neutral calls within this thread, bounded by the task limit.

        Records retain original requests, raw responses (including rejected
        structured output), and raised exceptions; no transport envelopes are
        retained. The scope does not reset the task ledger or authorize retries.
        Only one scope may be active, and requests from other threads are refused.
        """
        if self._budget is None:
            raise ModelControlError('llm_task_required', 'Capture requires an explicit bounded model task.')
        if not self._capture_lock.acquire(blocking=False):
            raise ModelControlError('llm_capture_busy', 'Nested or concurrent capture scopes are forbidden.')
        try:
            if not self._budget.lock.acquire(blocking=False):
                raise ModelControlError('llm_task_busy', 'Capture cannot start during an active request.')
            try:
                records: list[dict[str, Any]] = []
                self._capture_records = records
                self._capture_owner = threading.get_ident()
                self._capture_count = 0
            finally:
                self._budget.lock.release()
            try:
                yield records
            finally:
                self._capture_records = None
                self._capture_owner = None
                self._capture_count = 0
        finally:
            self._capture_lock.release()

    @property
    def budget_snapshot(self) -> dict[str, object]:
        return self._budget.snapshot if self._budget else {}

    @property
    def structured_output_token_limit(self) -> int:
        """Expose the existing task bound without credentials or another ledger."""
        return self._budget.task.max_output_tokens if self._budget else 4096

    @property
    def model_output_token_limit(self) -> int:
        if self._budget is not None and self._budget.task.model_output_token_limit is not None:
            return self._budget.task.model_output_token_limit
        return 8192 if self.provider_id=='deepseek' else 4096

    def cancel(self) -> None:
        """Stop before send or suppress the eventual result; no refund guarantee."""
        if self._budget is not None:
            self._budget.cancelled.set()

    @property
    def cancelled(self) -> bool:
        """Project the existing task's sticky cancellation without resetting it."""
        return bool(self._budget and self._budget.cancelled.is_set())

    @property
    def scope_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Release a governed scope's delegate; never cancel/retry an in-flight send.

        Receipts and budget facts remain. Dropping Python references is not a
        secure-erasure guarantee, and cannot revoke a caller's raw delegate.
        """
        with self.retirement():
            pass

    @contextmanager
    def retirement(self):
        """Fence requests/capture while the owner commits scope replacement.

        A failed commit leaves this scope open. Successful exit releases its
        delegate, so settings can publish a new scope without a busy-close gap.
        """
        if self._closed:
            yield
            return
        if self._budget is None:
            raise ModelControlError('llm_task_required', 'Closing requires a governed model task.')
        if not self._budget.lock.acquire(blocking=False):
            raise ModelControlError('llm_task_busy', 'Model task busy; finish the request before closing.')
        try:
            if not self._capture_lock.acquire(blocking=False):
                raise ModelControlError('llm_capture_busy', 'Capture busy; close after its scope exits.')
            try:
                if self._capture_records is not None:
                    raise ModelControlError('llm_capture_busy', 'Capture busy; close after its scope exits.')
                if self._closed:
                    yield
                    return
                yield
                self._delegate.set_external_call_observer(None)
                self._delegate = None
                self._before_request = None
                self._budget.cancelled.set()
                self._closed = True
            finally:
                self._capture_lock.release()
        finally:
            self._budget.lock.release()

    def request(self, request: ModelRequest) -> ModelResponse:
        if self._closed:
            raise ModelControlError('llm_provider_closed', 'Model provider closed; authorize a new scope.')
        self.request_count += 1
        if self._budget is None:
            if self._require_task:
                raise ModelControlError('llm_task_required', 'An explicit model task and budget are required before live execution.')
            # Legacy direct wrapper/adapter API, used by offline transport tests.
            if self._before_request is not None:
                self._before_request(request)
            return self._delegate.request(request)
        budget = self._budget
        if not budget.lock.acquire(blocking=False):
            raise ModelControlError('llm_task_busy', 'Concurrent requests on one model task are forbidden.')
        prepared_started = False
        record = None
        try:
            if self._closed:
                raise ModelControlError('llm_provider_closed', 'Model provider closed; authorize a new scope.')
            if self._capture_records is not None:
                if self._capture_owner != threading.get_ident():
                    raise ModelControlError('llm_capture_busy', 'Captured requests must run in the capture scope thread.')
                if budget.task.max_requests is not None and self._capture_count >= budget.task.max_requests:
                    raise ModelControlError('llm_capture_limit', 'Capture request limit reached.')
                record = dict(request=request, response=None, error=None, dispatched=False)
                self._capture_count += 1
                self._capture_records.append(record)
                self._active_record = record
            if self._before_request is not None:
                self._before_request(request)
            prepared_started = True
            prepared = budget.prepare(request)
            response = self._delegate.request(prepared)
            if record is not None:
                record['response'] = response
            budget.finish(response, prepared)
            return response
        except BaseException as exc:
            if record is not None:
                record['error'] = exc
            # A hook runs before prepare resets per-request accounting. Calling
            # failed() there would classify the preceding request's dispatch.
            if prepared_started:
                budget.failed()
            raise
        finally:
            self._active_record = None
            budget.lock.release()


class UnavailableModelProvider:
    """A traceable provider boundary used when local setup is incomplete."""

    provider_id = "unconfigured"
    model = None
    mode = "unavailable"
    configuration_source = "none"
    external_calls = 0

    def __init__(self, error: ModelProviderConfigurationError) -> None:
        self.error = error
        self.request_count = 0

    def request(self, _request: ModelRequest) -> ModelResponse:
        self.request_count += 1
        raise self.error


def resolve_api_key(provider_id: str, *, explicit: str | None = None,
                    environment: Mapping[str, str] | None = None,
                    allow_provider_environment: bool = True) -> str:
    """Resolve only the chosen provider; never read files or retry another key.

    Explicit > CATALYST_LLM_API_KEY > DEEPSEEK_API_KEY (DeepSeek only).
    A present but invalid higher-priority value is an error, not fallback.
    """
    env = os.environ if environment is None else environment
    if provider_id not in {'deepseek', 'openai-compatible'}:
        raise ModelProviderConfigurationError('llm_provider_configuration_invalid', 'Unsupported provider identity.')
    if explicit is not None:
        key = explicit
    elif 'CATALYST_LLM_API_KEY' in env:
        key = env['CATALYST_LLM_API_KEY']
    elif provider_id == 'deepseek' and allow_provider_environment:
        key = env.get('DEEPSEEK_API_KEY', '')
    else:
        key = ''
    if not isinstance(key, str) or not key.strip():
        raise ModelProviderConfigurationError('llm_provider_not_configured', 'CATALYST_LLM_API_KEY or an explicitly selected provider credential is required.')
    if any(c in key for c in '\r\n'):
        raise ModelProviderConfigurationError('llm_provider_configuration_invalid', 'API Key must not contain line breaks.')
    return key


def _environment_task() -> ModelTask | None:
    raw = os.environ.get('CATALYST_LLM_TASK_JSON')
    if raw is None:
        return None
    try:
        if len(raw) > 8192:
            raise ValueError()
        return ModelTask(**json.loads(raw))
    except (TypeError, ValueError):
        raise ModelProviderConfigurationError('llm_task_configuration_invalid', 'CATALYST_LLM_TASK_JSON must contain a complete explicit ModelTask declaration.') from None


def configured_model_provider_from_environment(*, task: ModelTask | None = None) -> ObservedModelProvider:
    """Build a supported Provider without sending a request or revealing its key."""

    task = task if task is not None else _environment_task()
    provider_id = os.environ.get("CATALYST_LLM_PROVIDER", task.provider_id if task else "deepseek").strip().lower()
    model = os.environ.get("CATALYST_LLM_MODEL", task.model if task else "").strip()
    base_url = os.environ.get("CATALYST_LLM_BASE_URL", "").strip()
    explicit_provider = task is not None or bool(os.environ.get('CATALYST_LLM_PROVIDER', '').strip())
    # A provider-scoped key is not automatically sent to a custom endpoint.
    provider_environment = explicit_provider and (not base_url or base_url.rstrip('/') == _DEFAULT_DEEPSEEK_BASE_URL)
    api_key = resolve_api_key(provider_id, allow_provider_environment=provider_environment)
    if provider_id not in {"deepseek", "openai-compatible"}:
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "CATALYST_LLM_PROVIDER must be 'deepseek' or 'openai-compatible'.",
        )
    if not api_key.strip():
        raise ModelProviderConfigurationError(
            "llm_provider_not_configured",
            "CATALYST_LLM_API_KEY is required before using the live LLM provider.",
        )
    if provider_id == "openai-compatible" and not model:
        raise ModelProviderConfigurationError(
            "llm_provider_not_configured",
            "CATALYST_LLM_MODEL is required for the selected provider.",
        )
    if provider_id == "openai-compatible" and not base_url:
        raise ModelProviderConfigurationError(
            "llm_provider_not_configured",
            "CATALYST_LLM_BASE_URL is required for openai-compatible providers.",
        )
    timeout = _environment_timeout()
    return configured_model_provider(
        provider_id=provider_id,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        configuration_source="environment",
        task=task,
    )


def configured_model_provider_interactively(
    *,
    provider_id: str = "deepseek",
    input_fn: Callable[[str], str] | None = None,
    secret_input_fn: Callable[[str], str] | None = None,
    task: ModelTask | None = None,
) -> ObservedModelProvider:
    """Collect one-run settings; DeepSeek defaults require only the hidden key prompt."""

    read_text = input_fn or input
    read_secret = secret_input_fn or getpass.getpass
    try:
        task = task if task is not None else _environment_task()
        if not isinstance(provider_id, str):
            provider_id = ""
        provider_id = provider_id.strip().lower()
        if provider_id not in {"deepseek", "openai-compatible"}:
            raise ModelProviderConfigurationError(
                "llm_provider_configuration_invalid",
                "Select 'deepseek' or 'openai-compatible' in --interactive-provider. No request was sent.",
            )

        model_default = os.environ.get("CATALYST_LLM_MODEL", task.model if task else "").strip()
        if not model_default and provider_id == "deepseek":
            model_default = _DEFAULT_DEEPSEEK_MODEL
        model = model_default
        if provider_id == "openai-compatible":
            model_prompt = f"Model ID [{model_default}]: " if model_default else "Model ID: "
            model = read_text(model_prompt).strip() or model_default
        if not model:
            raise ModelProviderConfigurationError(
                "llm_provider_not_configured",
                "Model ID is required for the selected provider. No request was sent.",
            )

        base_default = os.environ.get("CATALYST_LLM_BASE_URL", "").strip()
        if provider_id == "deepseek" and not base_default:
            base_default = _DEFAULT_DEEPSEEK_BASE_URL
        base_url = base_default
        if provider_id == "openai-compatible":
            base_prompt = f"Base URL [{base_default}]: " if base_default else "Base URL: "
            base_url = read_text(base_prompt).strip() or base_default
        if provider_id == "openai-compatible" and not base_url:
            raise ModelProviderConfigurationError(
                "llm_provider_not_configured",
                "Base URL is required for openai-compatible providers. No request was sent.",
            )

        timeout = _environment_timeout()
        _validate_base_url(base_url)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                api_key = read_secret("API Key (hidden, used for this run only): ")
        except getpass.GetPassWarning:
            raise ModelProviderConfigurationError(
                "llm_provider_secure_input_unavailable",
                "Secure hidden key input is unavailable in this terminal. No request was sent.",
            ) from None
        except RuntimeError:
            raise ModelProviderConfigurationError(
                "llm_provider_secure_input_unavailable",
                "Could not open hidden key input. Run this command in an interactive terminal; no request was sent.",
            ) from None
        except (EOFError, KeyboardInterrupt):
            raise ModelProviderConfigurationError(
                "llm_provider_setup_cancelled",
                "Provider setup was cancelled. No request was sent.",
            ) from None

        if not api_key or not api_key.strip():
            raise ModelProviderConfigurationError(
                "llm_provider_setup_cancelled",
                "API Key cannot be empty. Provider setup was cancelled; no request was sent.",
            )

        return configured_model_provider(
            provider_id=provider_id,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
            configuration_source="interactive_once",
            task=task,
        )
    except (EOFError, KeyboardInterrupt):
        raise ModelProviderConfigurationError(
            "llm_provider_setup_cancelled",
            "Provider setup was cancelled. No request was sent.",
        ) from None
    except ModelProviderConfigurationError:
        raise
    except Exception:
        # Prompt libraries and terminal bridges can raise implementation-specific
        # exceptions. Convert them at this boundary without displaying their text.
        raise ModelProviderConfigurationError(
            "llm_provider_setup_failed",
            "Provider setup could not complete. Check the terminal and required settings; no request was sent.",
        ) from None


def configured_model_provider(
    *,
    provider_id: str,
    api_key: str,
    model: str,
    base_url: str,
    timeout: float = 60.0,
    configuration_source: str = "explicit",
    task: ModelTask | None = None,
    transport: Callable[[str, Mapping[str, str], bytes], tuple[int, Any]] | None = None,
    before_request: Callable[[ModelRequest], None] | None = None,
    transport_guard: Callable | None = None,
) -> ObservedModelProvider:
    """Validate and construct one provider from in-memory configuration."""

    provider_id = provider_id.strip().lower()
    if provider_id not in {"deepseek", "openai-compatible"}:
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "CATALYST_LLM_PROVIDER must be 'deepseek' or 'openai-compatible'.",
        )
    if not isinstance(api_key, str) or not api_key.strip():
        raise ModelProviderConfigurationError(
            "llm_provider_not_configured",
            "A non-empty API key is required before using the live LLM provider.",
        )
    if any(character in api_key for character in "\r\n"):
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "API Key must not contain line breaks. No request was sent.",
        )

    model = model.strip()
    if task is not None and (provider_id, model) != (task.provider_id, task.model):
        raise ModelProviderConfigurationError('llm_task_identity_mismatch', 'Task provider/model identity must be explicitly configured and match exactly.')
    if not model and provider_id == "deepseek":
        model = _DEFAULT_DEEPSEEK_MODEL
    if not model:
        raise ModelProviderConfigurationError(
            "llm_provider_not_configured",
            "CATALYST_LLM_MODEL is required for the selected provider.",
        )
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "CATALYST_LLM_TIMEOUT_SECONDS must be a positive finite number.",
        )

    if provider_id == "deepseek":
        base_url = base_url.strip() or _DEFAULT_DEEPSEEK_BASE_URL
    else:
        base_url = base_url.strip()
        if not base_url:
            raise ModelProviderConfigurationError(
                "llm_provider_not_configured",
                "CATALYST_LLM_BASE_URL is required for openai-compatible providers.",
            )
    _validate_base_url(base_url)
    if task is not None and urlsplit(base_url).scheme != 'https':
        raise ModelProviderConfigurationError('llm_transport_insecure', 'Governed external model execution requires HTTPS.')

    try:
        transport_options = {'transport': transport} if transport is not None else {}
        if transport_guard is not None:
            transport_options['transport_guard'] = transport_guard
        if provider_id=='deepseek' and task is not None and task.model_output_token_limit is not None:
            transport_options['model_output_token_limit']=task.model_output_token_limit
        if provider_id == "deepseek":
            delegate = DeepSeekModelProvider(
                api_key=api_key,
                model=model,
                base_url=base_url,
                timeout=float(timeout),
                output_token_limit=task.max_output_tokens if task else 4096,
                **transport_options,
            )
        else:
            delegate = OpenAICompatibleModelProvider(
                api_key=api_key,
                model=model,
                base_url=base_url,
                timeout=float(timeout),
                **transport_options,
            )
    except ValueError:
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "Provider configuration is invalid. Review provider, model, base URL, and timeout.",
        ) from None
    return ObservedModelProvider(
        provider_id, model, delegate, configuration_source=configuration_source,
        task=task, require_task=True, before_request=before_request,
    )


def _environment_timeout() -> float:
    timeout_raw = os.environ.get("CATALYST_LLM_TIMEOUT_SECONDS", "60")
    try:
        timeout = float(timeout_raw)
    except (TypeError, ValueError):
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "CATALYST_LLM_TIMEOUT_SECONDS must be a positive finite number.",
        ) from None
    if not math.isfinite(timeout) or timeout <= 0:
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "CATALYST_LLM_TIMEOUT_SECONDS must be a positive finite number.",
        )
    return timeout


def _validate_base_url(value: str) -> None:
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
            and not any(ord(character) < 32 for character in value)
        )
        # Force port parsing here so malformed ports fail before API-key use.
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ModelProviderConfigurationError(
            "llm_provider_configuration_invalid",
            "CATALYST_LLM_BASE_URL must be a valid HTTP or HTTPS URL without embedded credentials or fragments.",
        )
