"""Execution-control infrastructure：cooperative cancellation + deadline/timeout。

只放 runtime-only control objects（token/source/context/registry/runner）。任何
threading.Event / clock / timer handle / CancellationToken / ExecutionContext
都绝不能进入 SessionSnapshot / PendingExecution / StepRecord / snapshot_value。

依赖边界：不依赖 Reasoner / ModelProvider / Policy / SessionSnapshot / StateStore。
"""

from __future__ import annotations

import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as _futures_wait
from dataclasses import dataclass
from typing import Callable, Protocol

from .errors import (
    CapabilityContractError,
    CapabilityTimeoutUncertainError,
    ExecutionCancelled,
)
from .contracts import Failure
from .snapshot import snapshot_observation

Clock = Callable[[], float]


# ---------------------------------------------------------------------------
# 配置 / deadline
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionTimeoutConfig:
    """execution runtime 超时/取消配置（runtime policy，不是 agent-visible tool argument）。"""

    timeout_seconds: float | None = None
    cancellation_grace_seconds: float = 0.5

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None:
            if isinstance(self.timeout_seconds, bool) or not isinstance(
                self.timeout_seconds, (int, float)
            ):
                raise ValueError("timeout_seconds must be None or a finite number")
            if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be finite and > 0")
        if isinstance(self.cancellation_grace_seconds, bool) or not isinstance(
            self.cancellation_grace_seconds, (int, float)
        ):
            raise ValueError("cancellation_grace_seconds must be a finite number")
        if (
            not math.isfinite(self.cancellation_grace_seconds)
            or self.cancellation_grace_seconds < 0
        ):
            raise ValueError("cancellation_grace_seconds must be finite and >= 0")


@dataclass(frozen=True)
class ExecutionDeadline:
    """monotonic deadline；不是 durable fact。"""

    monotonic_deadline: float | None

    def remaining_seconds(self, now: float) -> float | None:
        if self.monotonic_deadline is None:
            return None
        return max(0.0, self.monotonic_deadline - now)

    def exceeded(self, now: float) -> bool:
        return self.monotonic_deadline is not None and now >= self.monotonic_deadline


# ---------------------------------------------------------------------------
# Cancellation token / source
# ---------------------------------------------------------------------------

class CancellationToken:
    """Capability 的只读 view。

    携带本 execution 的 process-local provenance marker；raise_if_cancelled()
    抛出携带该 marker 的 ExecutionCancelled，供 runner 校验取消的 provenance。
    """

    def __init__(self, event: threading.Event, marker: object) -> None:
        self._event = event
        self._marker = marker

    def is_cancel_requested(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise ExecutionCancelled(self._marker)


class CancellationSource:
    """Harness 侧：可 request_cancel 的写侧；与 token 分离。

    每个 source 持有一个私有 marker；只有本 source 的 token 抛出的
    ExecutionCancelled 携带该 marker，才被视为 confirmed cooperative cancellation。
    """

    def __init__(self) -> None:
        self._event = threading.Event()
        self._marker = object()
        self.token = CancellationToken(self._event, self._marker)

    def request_cancel(self) -> None:
        self._event.set()

    def is_cancel_requested(self) -> bool:
        return self._event.is_set()

    def is_proven_cancellation(self, exc) -> bool:
        """exc 是否由本 source 的 token 产生（provenance marker 精确匹配）。"""
        return isinstance(exc, ExecutionCancelled) and exc.marker is self._marker


# ---------------------------------------------------------------------------
# ExecutionContext（runtime-only）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionContext:
    """一次 live execution 的 runtime control context（绝不 durable）。"""

    execution_id: str
    cancellation_token: CancellationToken
    deadline: ExecutionDeadline | None = None
    clock: Clock = time.monotonic

    def is_cancel_requested(self) -> bool:
        return self.cancellation_token.is_cancel_requested()

    def raise_if_cancelled(self) -> None:
        self.cancellation_token.raise_if_cancelled()

    def deadline_exceeded(self) -> bool:
        return self.deadline is not None and self.deadline.exceeded(self.clock())

    def remaining_seconds(self) -> float | None:
        if self.deadline is None:
            return None
        return self.deadline.remaining_seconds(self.clock())


# ---------------------------------------------------------------------------
# Active execution registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CancelRequestResult:
    session_id: str
    execution_id: str | None
    requested: bool


@dataclass
class _ActiveExecution:
    execution_id: str
    source: CancellationSource


class ActiveExecutionRegistry:
    """runtime-local、thread-safe 的 live execution registry。

    只用于定位 live cancellation source；不进入 durable Session。single-writer
    假设下，一个 session_id 至多一个 active execution。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict[str, _ActiveExecution] = {}

    def register(self, session_id: str, execution_id: str, source: CancellationSource) -> None:
        with self._lock:
            if session_id in self._active:
                raise RuntimeError(
                    f"session {session_id!r} already has an active execution"
                )
            self._active[session_id] = _ActiveExecution(execution_id, source)

    def remove(self, session_id: str, execution_id: str) -> None:
        with self._lock:
            entry = self._active.get(session_id)
            # identity 匹配，防止旧 cleanup 误删新 execution registration
            if entry is not None and entry.execution_id == execution_id:
                del self._active[session_id]

    def get(self, session_id: str) -> str | None:
        """返回当前 active execution_id，无则 None（供测试/诊断，不泄露 CancellationSource）。"""
        with self._lock:
            entry = self._active.get(session_id)
            return entry.execution_id if entry is not None else None

    def request_cancel(self, session_id: str) -> CancelRequestResult:
        with self._lock:
            entry = self._active.get(session_id)
            if entry is None:
                return CancelRequestResult(
                    session_id=session_id, execution_id=None, requested=False
                )
            entry.source.request_cancel()
            return CancelRequestResult(
                session_id=session_id, execution_id=entry.execution_id, requested=True
            )


# ---------------------------------------------------------------------------
# Late completion evidence registry
# ---------------------------------------------------------------------------

# quiescent 但 outcome 仍不确定（late ordinary exception / spurious cancel / invalid return）的哨兵
_UNCERTAIN_EVIDENCE = object()


class LateCompletionEvidenceRegistry:
    """runtime-local、thread-safe 的 late completion evidence registry。

    timeout uncertain 后，worker 的 future 完成时记录其结果，使 reconciliation 与
    "本地已知的 authoritative late outcome" 保持一致，不能矛盾。不 durable。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._evidence: dict[tuple[str, str], object] = {}

    def record_observation(self, session_id: str, execution_id: str, observation) -> None:
        # record 侧防御性快照：不持有 caller 的 mutable data 引用
        with self._lock:
            self._evidence[(session_id, execution_id)] = snapshot_observation(observation)

    def record_uncertain(self, session_id: str, execution_id: str) -> None:
        with self._lock:
            self._evidence[(session_id, execution_id)] = _UNCERTAIN_EVIDENCE

    def remove(self, session_id: str, execution_id: str) -> None:
        """reconciliation 成功 commit 后，移除 exact identity 的 evidence。"""
        with self._lock:
            self._evidence.pop((session_id, execution_id), None)

    def get_authoritative_observation(self, session_id: str, execution_id: str):
        """返回本地已知的 authoritative late Observation（Success/Failure），否则 None。

        None 表示：无 late evidence，或 late outcome 仍 uncertain（quiescent 但未知）。
        read 侧防御性快照：caller 改动返回的 observation 不影响 registry 内部事实。
        """
        with self._lock:
            value = self._evidence.get((session_id, execution_id))
        if value is None or value is _UNCERTAIN_EVIDENCE:
            return None
        return snapshot_observation(value)


class ExecutionControlPlane:
    """Runtime-local execution control state，由单个 Runtime 组合根拥有。

    把 ActiveExecutionRegistry 与 LateCompletionEvidenceRegistry 聚合成一个
    runtime-local 服务，供 Runtime.cancel / Runtime.reconcile / CapabilityExecutor /
    ThreadedExecutionRunner 共同查询同一份 active/evidence 状态。

    它不是 StateStore namespace 身份、不是多 Runtime 协调器、不是分布式所有权
    服务，也不是 process-wide singleton。

    active_registry / evidence_registry 可注入（测试用 spy），默认新建。
    """

    def __init__(
        self,
        active_registry: ActiveExecutionRegistry | None = None,
        evidence_registry: LateCompletionEvidenceRegistry | None = None,
    ) -> None:
        self.active = active_registry if active_registry is not None else ActiveExecutionRegistry()
        self.evidence = evidence_registry if evidence_registry is not None else LateCompletionEvidenceRegistry()


# ---------------------------------------------------------------------------
# ExecutionRunner
# ---------------------------------------------------------------------------

def _invoke(capability, parameters, context: ExecutionContext):
    """worker 入口：进入 capability body 前先做 pre-invoke cancellation check。"""
    context.raise_if_cancelled()
    return capability.invoke(parameters, context)


class ExecutionRunner(Protocol):
    def run(
        self,
        capability,
        parameters,
        *,
        execution_id: str,
        session_id: str,
        timeout_seconds: float | None,
        grace_seconds: float,
    ):
        """执行一次 capability；返回 Observation 或抛 ExecutionCancelled /
        CapabilityTimeoutUncertainError / 普通异常。"""
        ...


class ThreadedExecutionRunner:
    """默认 runner。

    - timeout_seconds is None：owner 线程内联执行（cooperative cancel 仍通过 token 生效）。
    - timeout_seconds > 0：提交到 worker thread，deadline 到达时 request cancel，
      再等待 grace period；仍未确认 quiesce → CapabilityTimeoutUncertainError。

    只有 owner（AgentCore/Runtime）写 Session；worker / done callback 只做 runtime-local
    cleanup（registry 移除），绝不 commit。

    Registry 语义：active entry 表示"该 execution 仍可能改变现实"。timeout uncertain
    时 worker 明确可能仍 live，因此 entry 保留；只有 future.done()（实际完成）后才移除。
    """

    def __init__(
        self,
        control_plane: ExecutionControlPlane | None = None,
        clock: Clock = time.monotonic,
        max_workers: int = 4,
    ) -> None:
        self._control_plane = control_plane
        self._registry = control_plane.active if control_plane is not None else None
        self._evidence = control_plane.evidence if control_plane is not None else None
        self._clock = clock
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="cap-exec"
        )

    @staticmethod
    def _reject_spurious_cancelled(source: CancellationSource, exc: ExecutionCancelled) -> None:
        """ExecutionCancelled 只有携带本 source 的 provenance marker 才合法。

        否则 capability 伪造了 infrastructure cancellation signal → contract violation
        （unresolved，不是取消结算）。post-hoc request_cancel 不能 retroactively
        合法化更早产生的 unproven exception。
        """
        if not source.is_proven_cancellation(exc):
            raise CapabilityContractError(
                "capability raised unproven ExecutionCancelled "
                "(not produced by this token's raise_if_cancelled)"
            ) from None

    def _on_uncertain_done(self, session_id: str, execution_id: str, source: CancellationSource, future) -> None:
        """timeout-uncertain 的 future 完成回调：先发布 evidence，再移除 active（identity-safe）。

        关键顺序（Invariant I2）：必须 **先 publish evidence，后 remove active**，
        否则 reconcile 可能观察到 active=None 且 evidence=None 的 visibility hole，
        从而错误接受 ConfirmedNotExecuted。

        late outcome 分类（与 normal cooperative cancellation 语义一致）：
        - 返回 Success/Failure           → authoritative observation
        - 抛 proven ExecutionCancelled（本 token raise_if_cancelled）→ authoritative Failure("execution cancelled")
        - 抛 unproven/spurious ExecutionCancelled → uncertain（与 immediate path 语义一致）
        - 抛普通异常 / invalid return    → uncertain（quiescent 但 outcome 未知）
        """
        if self._evidence is not None:
            try:
                result = future.result()
            except ExecutionCancelled as exc:
                if source.is_proven_cancellation(exc):
                    self._evidence.record_observation(
                        session_id, execution_id, Failure("execution cancelled")
                    )
                else:
                    self._evidence.record_uncertain(session_id, execution_id)
            except Exception:  # noqa: BLE001
                self._evidence.record_uncertain(session_id, execution_id)
            else:
                try:
                    canonical = snapshot_observation(result)
                except CapabilityContractError:
                    self._evidence.record_uncertain(session_id, execution_id)
                else:
                    self._evidence.record_observation(session_id, execution_id, canonical)
        if self._registry is not None:
            self._registry.remove(session_id, execution_id)

    def run(
        self,
        capability,
        parameters,
        *,
        execution_id: str,
        session_id: str,
        timeout_seconds: float | None,
        grace_seconds: float,
    ):
        source = CancellationSource()
        now = self._clock()
        deadline = ExecutionDeadline(now + timeout_seconds if timeout_seconds is not None else None)
        context = ExecutionContext(
            execution_id=execution_id,
            cancellation_token=source.token,
            deadline=deadline,
            clock=self._clock,
        )
        if self._registry is not None:
            self._registry.register(session_id, execution_id, source)

        if timeout_seconds is None:
            # 无 deadline：内联执行，cooperative cancel 通过 token 生效；结束即 quiescent
            try:
                result = _invoke(capability, parameters, context)
            except ExecutionCancelled as exc:
                self._reject_spurious_cancelled(source, exc)
                raise
            finally:
                if self._registry is not None:
                    self._registry.remove(session_id, execution_id)
            return result

        # deadline enforcement：worker thread + wait
        try:
            future = self._pool.submit(_invoke, capability, parameters, context)
        except BaseException:
            # submit 失败：Future 尚未存在，worker 未启动 → 清除 false-live registry entry
            if self._registry is not None:
                self._registry.remove(session_id, execution_id)
            raise

        done, _ = _futures_wait([future], timeout=timeout_seconds)
        if future not in done:
            source.request_cancel()
            done, _ = _futures_wait([future], timeout=grace_seconds)

        if future in done:
            # execution 已 quiescent：拿到 authoritative result（成功/异常/confirmed cancel）
            try:
                result = future.result()
            except ExecutionCancelled as exc:
                self._reject_spurious_cancelled(source, exc)
                raise
            finally:
                if self._registry is not None:
                    self._registry.remove(session_id, execution_id)
            return result

        # future 未 done：execution 仍 live。保留 registry，仅在未来真正完成后 publish evidence + cleanup。
        future.add_done_callback(
            lambda _f, sid=session_id, eid=execution_id, src=source: self._on_uncertain_done(sid, eid, src, _f)
        )
        raise CapabilityTimeoutUncertainError(
            session_id=session_id, execution_id=execution_id
        )
