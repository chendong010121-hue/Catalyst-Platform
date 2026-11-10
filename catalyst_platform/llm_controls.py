"""Data and spend accounting for the existing configured model boundary.

Rates and limits are operator declarations, never fetched or inferred. This is
an in-process estimated-spend guard, not a provider billing cap or credential store.
"""
from __future__ import annotations

import json
import math
import threading
import uuid
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation

from agent_runtime.contracts import ModelRequest, ModelResponse


# Conservative input estimate for a vendor tokenizer, per character class instead
# of per byte. Charging every byte two tokens priced CJK text at six tokens per
# character: the one prompt this product has measured (425 input tokens over 1,047
# characters, 0.406 tokens/character) shows that is a 5x overshoot which refuses
# prompts that fit. These rates sit above that measurement and stay content-aware;
# a request whose reported usage still exceeds the declaration is refused at
# settlement (llm_usage_bound_exceeded) and locks the task, so an optimistic
# estimate cannot overrun an authorized input scope.
_CJK_RANGES = ((0x3000, 0x303F), (0x3040, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
               (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF))
_CJK_TOKENS_PER_CHAR = 0.85
_OTHER_TOKENS_PER_CHAR = 0.42
_INPUT_FRAMING_TOKENS = 512


def _is_cjk(character):
    point = ord(character)
    return any(low <= point <= high for low, high in _CJK_RANGES)


def input_token_envelope(text):
    """Conservative token bound for one prepared request; see the rates above."""
    if not isinstance(text, str):
        raise TypeError('input envelope needs the serialized request text')
    cjk = 0
    for character in text:
        if _is_cjk(character):
            cjk += 1
    other = len(text) - cjk
    return math.ceil(cjk * _CJK_TOKENS_PER_CHAR + other * _OTHER_TOKENS_PER_CHAR) + _INPUT_FRAMING_TOKENS


class ModelControlError(ValueError):
    """Safe, content-free local refusal visible through existing R4 error fields."""

    stage = 'model_control'
    retryable = False

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = self.public_code = code
        self.category = (
            'cancelled' if code == 'llm_cancelled' else
            'protocol' if code in {'llm_structured_output_invalid', 'llm_output_truncated'} else
            'invalid_request' if code in {'llm_parameters_unbounded', 'llm_output_format', 'llm_input_limit', 'llm_output_limit'} else
            'budget'
        )

    @property
    def safe_message(self):
        return str(self)

    @property
    def safe_details(self):
        return dict(category=self.category, stage=self.stage, retryable=False)


def _json_object(content):
    """The JSON object a `json_object` answer holds, allowing one quoting layer too many.

    deepseek occasionally sends the answer escaped inside itself (`{\\"items\\": ...}`), which
    `json.loads` refuses although the object is right there: on a live card that cost a
    whole slide (24 cells, six duties) and the card could only say "one unit was refused".
    Reading that layer is a statement about the envelope, not leniency about the content:
    the value still has to be a JSON object, and a cut or a tool-call answer is refused in
    its own branch before this one is reached.
    """
    def reject(_):
        raise ValueError()

    text = content if isinstance(content, str) else ""
    for _ in range(3):
        try:
            value = json.loads(text, parse_constant=reject)
        except ValueError:
            # An object whose quotes arrived escaped: wrap it as a string literal, so the
            # next turn reads the string it decodes to. A cut answer carries raw quotes and
            # fails this wrap too, so it keeps its own refusal.
            value = json.loads('"' + text + '"', parse_constant=reject)
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            raise ValueError()
        text = value
    raise ValueError()


def _money(value, name):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError()
        return result
    except (ValueError, InvalidOperation):
        raise ValueError(f'{name} must be a finite non-negative decimal') from None


@dataclass(frozen=True)
class ModelTask:
    """Explicit provider/model/task and conservative CNY price envelope.

    Reuse ONE configured provider per authorized task to share its ledger. A new
    declaration/provider is a new authorization, not a way to retry uncertain spend.
    Input rates must cover uncached peak pricing and any applicable pricing tier.
    """

    task_id: str
    provider_id: str
    model: str
    max_requests: int | None
    budget_cny: str | None
    input_token_limit: int
    max_output_tokens: int
    input_cny_per_million: str
    output_cny_per_million: str
    cache_hit_cny_per_million: str
    price_reference: str
    model_output_token_limit: int | None = None
    execution_profile: str = 'experiment'

    def __post_init__(self):
        for name in ('task_id', 'model', 'price_reference'):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f'{name} requires a bounded non-empty identifier')
            if any(ord(c) < 32 for c in value):
                raise ValueError(f'{name} must not contain control characters')
        if self.provider_id not in {'deepseek', 'openai-compatible'}:
            raise ValueError('unsupported provider identity')
        if self.execution_profile not in {'daily','experiment'}:
            raise ValueError('invalid execution profile')
        daily=self.execution_profile=='daily'
        if daily and (self.max_requests is not None or self.budget_cny is not None):
            raise ValueError('daily connection uses metering, not experimental cumulative caps')
        for name in (('input_token_limit', 'max_output_tokens') if daily else ('max_requests', 'input_token_limit', 'max_output_tokens')):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f'{name} must be a positive integer')
        limit=self.model_output_token_limit
        if limit is not None and (type(limit) is not int or not 128<=limit<=1_048_576):
            raise ValueError('invalid explicit model output capacity')
        if self.max_output_tokens > (limit if limit is not None else 8192 if self.provider_id == 'deepseek' else 4096):
            raise ValueError('P0 output bound exceeded for declared model capacity')
        for name in (('input_cny_per_million', 'output_cny_per_million', 'cache_hit_cny_per_million') if daily else ('budget_cny', 'input_cny_per_million', 'output_cny_per_million', 'cache_hit_cny_per_million')):
            object.__setattr__(self, name, str(_money(getattr(self, name), name)))
        if max(Decimal(self.input_cny_per_million), Decimal(self.output_cny_per_million)) == 0:
            raise ValueError('configured external models require a nonzero conservative price')


class TaskBudget:
    """Single-task ledger, serialized at the existing Provider wrapper."""

    def __init__(self, task: ModelTask):
        self.task = task
        self.lock = threading.Lock()
        self.cancelled = threading.Event()
        self.attempts = 0
        self.charged = Decimal(0)
        self.uncertain = False
        self.status = 'ready'
        self.request_id = None
        self.input_tokens = self.output_tokens = None
        self.sent = False
        self.settled = False
        self.reserve = (
            task.input_token_limit * max(Decimal(task.input_cny_per_million), Decimal(task.cache_hit_cny_per_million))
            + task.max_output_tokens * Decimal(task.output_cny_per_million)
        ) / Decimal(1000000)

    @property
    def snapshot(self):
        return dict(task_id=self.task.task_id, request_id=self.request_id,
                    attempts=self.attempts, max_requests=self.task.max_requests,
                    charged_cny=str(self.charged), reserved_per_request_cny=str(self.reserve),
                    budget_cny=self.task.budget_cny, uncertain=self.uncertain,
                    last_status=self.status, input_tokens=self.input_tokens,
                    output_tokens=self.output_tokens, price_reference=self.task.price_reference)

    def _cancel_check(self):
        if self.cancelled.is_set():
            self.status = 'cancelled'
            raise ModelControlError('llm_cancelled', 'Model task cancelled; cancellation does not imply a refund.')

    def prepare(self, request: ModelRequest) -> ModelRequest:
        self.sent = self.settled = False
        self.input_tokens = self.output_tokens = None
        self.request_id = uuid.uuid4().hex
        self._cancel_check()
        if self.uncertain:
            raise ModelControlError('llm_usage_uncertain', 'Prior spend is uncertain; reconcile before a new task authorization.')
        if self.task.max_requests is not None and self.attempts >= self.task.max_requests:
            raise ModelControlError('llm_request_limit', 'Model task request limit reached.')
        if self.task.budget_cny is not None and self.charged + self.reserve > Decimal(self.task.budget_cny):
            raise ModelControlError('llm_budget_exhausted', 'Next reservation would exceed the task budget.')
        parameters = dict(request.parameters)
        # One output bound and one completion only. Do not allow generic adapter
        # parameters to create multiple billed completions or override identity.
        allowed = {'max_tokens', 'response_format', 'temperature', 'top_p', 'stop', 'seed'}
        if set(parameters) - allowed:
            raise ModelControlError('llm_parameters_unbounded', 'Parameters outside the bounded task contract are not allowed.')
        limit = parameters.get('max_tokens', self.task.max_output_tokens)
        if type(limit) is not int or not 1 <= limit <= self.task.max_output_tokens:
            raise ModelControlError('llm_output_limit', 'Request output bound exceeds the task limit.')
        parameters['max_tokens'] = limit
        if 'response_format' in parameters and parameters['response_format'] != {'type': 'json_object'}:
            raise ModelControlError('llm_output_format', 'P0 structured output requires JSON object mode.')
        prepared = replace(request, parameters=parameters)
        # Serialized UTF-8 bytes + generous framing allowance, not a vendor
        # tokenizer guarantee. Actual usage above the declaration locks the task.
        envelope = input_token_envelope(json.dumps(asdict(prepared), ensure_ascii=False))
        if envelope > self.task.input_token_limit:
            raise ModelControlError('llm_input_limit', 'Conservative input envelope exceeds the declared input limit.')
        self.status = 'reserved'
        return prepared

    def dispatch(self):
        self._cancel_check()
        if self.sent:
            raise ModelControlError('llm_duplicate_attempt', 'Multiple transport attempts are forbidden.')
        self.sent = True
        self.attempts += 1
        self.charged += self.reserve
        self.status = 'dispatched'

    def failed(self):
        if self.sent and not self.settled:
            self.uncertain = True
            self.status = 'uncertain'
        elif not self.sent:
            self.status = 'rejected_before_dispatch'

    def finish(self, response: ModelResponse, request: ModelRequest):
        usage = response.usage
        if usage is None:
            raise ModelControlError('llm_usage_missing', 'Usage missing; full reservation retained, spend uncertain.')
        self.input_tokens, self.output_tokens = usage.input_tokens, usage.output_tokens
        hit = usage.cache_hit_input_tokens or 0
        cost = ((usage.input_tokens - hit) * Decimal(self.task.input_cny_per_million)
                + hit * Decimal(self.task.cache_hit_cny_per_million)
                + usage.output_tokens * Decimal(self.task.output_cny_per_million)) / Decimal(1000000)
        if usage.input_tokens > self.task.input_token_limit or usage.output_tokens > request.parameters['max_tokens'] or cost > self.reserve:
            self.charged += max(Decimal(0), cost - self.reserve)
            raise ModelControlError('llm_usage_bound_exceeded', 'Reported usage exceeded the reserved bound; task locked for reconciliation.')
        self.charged += cost - self.reserve
        self.settled = True
        self.status = 'metered'
        self._cancel_check()
        if request.parameters.get('response_format') == {'type': 'json_object'}:
            try:
                value = _json_object(response.content)
                if response.finish_reason != 'stop' or response.tool_calls:
                    raise ValueError()
            except (ValueError, TypeError):
                self.status = 'invalid_structured_output'
                if response.finish_reason == 'length':
                    # The window closed before the answer did. That is a different fact
                    # from a malformed answer, and the caller can act on it: the rows the
                    # model finished are whole rows, so the text it reached travels on the
                    # error instead of being dropped with the refusal. Spending is already
                    # settled above, so nothing about the meter changes.
                    truncated = ModelControlError(
                        'llm_output_truncated',
                        'Model output stopped at the output window before the answer was complete.')
                    truncated.partial = response.content if isinstance(response.content, str) else ''
                    raise truncated from None
                raise ModelControlError('llm_structured_output_invalid', 'Expected a complete JSON object; model content was not accepted.') from None
