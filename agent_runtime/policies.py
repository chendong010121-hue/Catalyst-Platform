"""生产级安全 Policy：有限的 loop guard。

Runtime 的生产组合必须包含至少一个有限循环护栏（如 StepLimitPolicy），
否则 Reasoner 永远 Act + Policy 永远 Continue 会导致无限模型调用。
"""

from __future__ import annotations

from typing import Sequence

from .contracts import (
    Action,
    Allow,
    Continue,
    PolicyVerdict,
    State,
    StepRecord,
    Stop,
    Termination,
)


def _require_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


class StepLimitPolicy:
    """达到最大 step 数时强制停止。只依据持久 history 判断。"""

    def __init__(self, max_steps: int) -> None:
        _require_positive_int("max_steps", max_steps)
        self._max_steps = max_steps

    def check_action(self, action: Action, state: State) -> PolicyVerdict:
        return Allow()

    def should_stop(self, state: State, history: Sequence[StepRecord]) -> Termination:
        if len(history) >= self._max_steps:
            return Stop("step limit reached")
        return Continue()


class TokenBudgetPolicy:
    """累计历史中的模型 token 用量，达到预算后强制停止。"""

    def __init__(self, max_tokens: int) -> None:
        _require_positive_int("max_tokens", max_tokens)
        self._max_tokens = max_tokens

    def check_action(self, action: Action, state: State) -> PolicyVerdict:
        return Allow()

    def should_stop(self, state: State, history: Sequence[StepRecord]) -> Termination:
        total = sum(
            step.model_call.usage.total_tokens
            for step in history
            if step.model_call is not None and step.model_call.usage is not None
        )
        if total >= self._max_tokens:
            return Stop("token budget reached")
        return Continue()
