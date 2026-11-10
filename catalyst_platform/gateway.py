"""Compose the local product entry points with Platform Standard and Agent Runtime."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from agent_runtime.policies import StepLimitPolicy
from agent_runtime.runtime import Runtime
from platform_standard.models import Invocation
from platform_standard.registry import InMemoryDescriptorRegistry
from platform_standard.runtime_adapter import RuntimeAdapter

from .file_title import CAPABILITY_ID, CAPABILITY_VERSION, FileTitleCapability, descriptor
from .observability import RunRecorder, RuntimeObservationBridge, record_file_tool_event
from .storage import JsonFileStateStore
from .trace_log import JsonlTraceStore


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _safe_error_code(value: Any, fallback: str = "how_operation_failed") -> str:
    if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", value):
        return value
    return fallback


class CatalystGateway:
    """Compose local product requests with Platform Standard and the existing Agent Runtime."""

    def __init__(self, workspace: Path | str) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.state_root = self.workspace / ".catalyst" / "r0"
        self.traces = JsonlTraceStore(self.workspace)

    def inspect_file(self, file_path: Path | str) -> dict[str, Any]:
        run_id = _id("run")
        invocation_id = _id("inv")
        trace_id = uuid.uuid4().hex
        selected_path = Path(file_path).expanduser().resolve()
        input_json = json.dumps(
            {"path": str(selected_path)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        recorder = RunRecorder(
            self.traces,
            run_id=run_id,
            request_id=invocation_id,
            invocation_id=invocation_id,
            trace_id=trace_id,
        )
        recorder.start(
            request_kind="file_title_inspection",
            input_sha256=hashlib.sha256(input_json).hexdigest(),
            actor="local_cli_user",
            component="CatalystGateway",
            selected_file=str(selected_path),
        )
        started_at = time.perf_counter()
        tool_events: list[dict[str, Any]] = []

        def record_tool_event(event: dict[str, Any]) -> None:
            tool_events.append(event)
            record_file_tool_event(recorder, event)

        capability = FileTitleCapability(
            workspace=self.workspace,
            event_sink=record_tool_event,
        )
        registry = InMemoryDescriptorRegistry()
        registry.register(descriptor())

        def runtime_factory(capabilities, reasoner):
            capability_digest = hashlib.sha256(
                json.dumps(descriptor().to_dict(), sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            bridge = RuntimeObservationBridge(
                recorder,
                invocation_id,
                lambda key: (
                    {
                        "capability_id": CAPABILITY_ID,
                        "capability_version": CAPABILITY_VERSION,
                        "binding_digest": capability_digest,
                        "side_effect": "none",
                        "implementation_class": "catalyst_platform.file_title.FileTitleCapability",
                    }
                    if key == f"cap_{hashlib.sha1(f'{CAPABILITY_ID}@{CAPABILITY_VERSION}'.encode()).hexdigest()[:12]}"
                    else None
                ),
            )
            return Runtime(
                reasoner,
                capabilities,
                StepLimitPolicy(max_steps=2),
                JsonFileStateStore(self.state_root / "runtime-sessions"),
                observation_sink=bridge,
            )

        adapter = RuntimeAdapter(
            registry,
            bindings={(CAPABILITY_ID, CAPABILITY_VERSION): capability},
            runtime_factory=runtime_factory,
        )
        invocation = Invocation(
            id=invocation_id,
            capability_id=CAPABILITY_ID,
            capability_version=CAPABILITY_VERSION,
            input={"path": str(selected_path)},
            context={"extensions": {}},
            trace_id=trace_id,
        )
        try:
            result = adapter.execute(invocation)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            error = self._error(result.status, result.error, tool_events)
            output = result.output if isinstance(result.output, dict) else None
            source = output.get("source") if output else None
            result_bytes = json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            recorder.event(
                "result.emitted",
                result_id=result.id,
                status=result.status,
                result_sha256=hashlib.sha256(result_bytes).hexdigest(),
                source_sha256=source.get("sha256") if isinstance(source, dict) else None,
                source_line=source.get("line") if isinstance(source, dict) else None,
                extraction_method=source.get("extraction_method") if isinstance(source, dict) else None,
                error_code=error.get("code") if error else None,
            )
            recorder.finish(
                result.status,
                duration_ms=duration_ms,
                model_calls=0,
                error_owner="file_title_tool" if error else None,
            )
        except BaseException as exc:
            if not recorder.is_finished:
                if isinstance(exc, KeyboardInterrupt):
                    recorder.event("request.interrupted", error_type=type(exc).__name__, effect_certainty="unknown")
                    recorder.finish("interrupted")
                else:
                    recorder.event("request.failed", error_type=type(exc).__name__, error_message=str(exc))
                    recorder.finish("failure", error_type=type(exc).__name__)
            raise
        trace_path = self.traces.path
        return {
            "run_id": run_id,
            "status": result.status,
            "result": result.to_dict(),
            "error": error,
            "trace_path": str(trace_path),
        }

    def inspect_run(self, run_id: str) -> dict[str, Any] | None:
        return self.traces.inspect_run(run_id)

    def semantic_operation(
        self,
        *,
        operation: str,
        scope_id: str,
        actor_origin: str,
        input_value: Mapping[str, Any],
        action: Callable[[RunRecorder], Any],
        finalize: Callable[[str, str], None] | None = None,
        correlation_id: str | None = None,
        event_schema_version: str | None = None,
    ) -> dict[str, Any]:
        """Run one local semantic operation through the shared R4 RunRecorder."""
        run_id = _id("run")
        request_id = _id("req")
        invocation_id = _id("inv")
        trace_id = uuid.uuid4().hex
        # Understand Wiki handoff events were added in R4 v1.6. Keep the
        # historical default for every existing operation, while ensuring
        # callers using the Understand port directly get a schema that can
        # represent its event vocabulary.
        effective_event_schema_version = event_schema_version
        if effective_event_schema_version is None:
            if operation.startswith("understand."):
                effective_event_schema_version = "1.6"
            elif operation in {"consumer.relations", "consumer.graph"}:
                effective_event_schema_version = "1.5"
            elif operation in {"candidate.decide", "version.activate", "version.rollback", "review.submit"}:
                # An authorized decision or version change carries the owner receipt
                # fields R4 1.5 added; without them the transition refuses to run.
                effective_event_schema_version = "1.5"
        recorder = RunRecorder(
            self.traces,
            run_id=run_id,
            request_id=request_id,
            invocation_id=invocation_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            **({"event_schema_version": effective_event_schema_version} if effective_event_schema_version is not None else {}),
        )
        input_bytes = json.dumps(
            input_value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        started_at = time.perf_counter()
        recorder.start(
            request_kind=f"semantic_{operation.replace('.', '_')}",
            input_sha256=hashlib.sha256(input_bytes).hexdigest(),
            actor="local_cli_user",
            component="CatalystGateway",
        )
        try:
            result = action(recorder)
            result_bytes = json.dumps(
                result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False
            ).encode("utf-8")
            recorder.event(
                "result.emitted",
                status="success",
                result_sha256=hashlib.sha256(result_bytes).hexdigest(),
            )
            recorder.finish(
                "success",
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                model_calls=0,
                error_owner=None,
            )
            if finalize is not None:
                finalize(run_id, "success")
            return {
                "run_id": run_id,
                "status": "success",
                "operation": operation,
                "scope_id": scope_id,
                "actor_origin": actor_origin,
                "result": result,
                "correlation_id": correlation_id,
                "trace_path": str(self.traces.path),
            }
        except BaseException as exc:
            terminal_status = "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failure"
            safe_error_code = _safe_error_code(
                getattr(exc, "code", "semantic_operation_failed"),
                "semantic_operation_failed",
            )
            if not recorder.is_finished:
                if terminal_status == "interrupted":
                    recorder.event("request.interrupted", error_type=type(exc).__name__, effect_certainty="none")
                else:
                    recorder.event(
                        "semantic.transition.failed",
                        operation=operation,
                        status="failure",
                        error_code=safe_error_code,
                        actor_origin=actor_origin,
                        scope_id=scope_id,
                        candidate_id=input_value.get("candidate_id") if isinstance(input_value.get("candidate_id"), str) else None,
                        version_id=input_value.get("version_id") if isinstance(input_value.get("version_id"), str) else None,
                        source_id=input_value.get("source_id") if isinstance(input_value.get("source_id"), str) else None,
                        source_revision=input_value.get("source_revision") if isinstance(input_value.get("source_revision"), str) else None,
                        expected_head_version_id=input_value.get("expected_head_version_id"),
                        branch_switch=input_value.get("branch_switch") if isinstance(input_value.get("branch_switch"), bool) else None,
                    )
                    recorder.event("request.failed", error_type=type(exc).__name__, error_message="semantic operation failed")
                    recorder.event("result.emitted", status="failure", error_code=safe_error_code)
                recorder.finish(
                    terminal_status,
                    duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                    model_calls=0,
                    error_owner="semantic_wiki",
                    error_type=type(exc).__name__,
                )
            if finalize is not None:
                finalize(run_id, terminal_status)
            return {
                "run_id": run_id,
                "status": "failure" if terminal_status != "interrupted" else "interrupted",
                "operation": operation,
                "scope_id": scope_id,
                "actor_origin": actor_origin,
                "correlation_id": correlation_id,
                "error": {"code": safe_error_code, "type": type(exc).__name__},
                "trace_path": str(self.traces.path),
            }

    def workbench_how_operation(
        self,
        *,
        operation: str,
        action: Callable[[], Any],
        active_before: str,
        active_reader: Callable[[], str] | None = None,
        benchmark_sha256: str | None = None,
        benchmark_case_count: int | None = None,
        activation_requested: bool = False,
    ) -> dict[str, Any]:
        """Record one existing Workbench HOW comparison or rollback as an R4 Run.

        The wrapper observes the Workbench operation; it does not choose a
        candidate, alter its evaluator, or own the active implementation state.
        """
        if operation not in {"evolve_understand", "rollback_understand"}:
            raise ValueError("unsupported Workbench HOW operation")
        if not isinstance(active_before, str) or not active_before:
            raise ValueError("active_before must identify the current HOW implementation")
        if benchmark_sha256 is not None and (
            len(benchmark_sha256) != 64 or any(char not in "0123456789abcdef" for char in benchmark_sha256)
        ):
            raise ValueError("benchmark_sha256 must be a lowercase SHA-256 digest")

        run_id = _id("run")
        request_id = _id("req")
        invocation_id = _id("inv")
        started_at = time.perf_counter()
        recorder = RunRecorder(
            self.traces,
            run_id=run_id,
            request_id=request_id,
            invocation_id=invocation_id,
            trace_id=uuid.uuid4().hex,
            event_schema_version="1.5",
        )
        safe_input = {
            "operation": operation,
            "active_before": active_before,
            "benchmark_sha256": benchmark_sha256,
            "benchmark_case_count": benchmark_case_count,
            "activation_requested": bool(activation_requested),
        }
        input_sha256 = hashlib.sha256(
            json.dumps(safe_input, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        recorder.start(
            request_kind=f"workbench_{operation}",
            input_sha256=input_sha256,
            actor="local_cli_user",
            component="CatalystGateway",
        )
        recorder.start_span(
            "workbench.how",
            kind="CHAIN",
        )
        candidate_implementation = "ripgrep_search@1.0.0" if operation == "evolve_understand" else None
        recorder.event(
            "how.operation.started",
            operation=operation,
            change_domain="implementation/how",
            active_before=active_before,
            candidate_implementation=candidate_implementation,
            baseline_implementation=active_before,
            benchmark_sha256=benchmark_sha256,
            benchmark_case_count=benchmark_case_count,
            activation_requested=bool(activation_requested),
        )

        def read_active_safely() -> tuple[str | None, bool]:
            if active_reader is None:
                return None, False
            try:
                return active_reader(), False
            except Exception:
                return None, True

        try:
            result = action()
        except BaseException as exc:
            active_after, _active_read_failed = read_active_safely()
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                recorder.event("request.interrupted", error_type=type(exc).__name__, effect_certainty="unknown")
                recorder.finish(
                    "interrupted",
                    duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                    model_calls=0,
                    error_owner="workbench",
                    error_type=type(exc).__name__,
                )
                raise
            error_code = _safe_error_code(getattr(exc, "code", None))
            recorder.event(
                "how.operation.failed",
                operation=operation,
                change_domain="implementation/how",
                active_before=active_before,
                active_after=active_after,
                candidate_implementation=candidate_implementation,
                baseline_implementation=active_before,
                error_type=type(exc).__name__,
                error_code=error_code,
            )
            recorder.event("result.emitted", status="failure", error_code="how_operation_failed")
            recorder.finish(
                "failure",
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                model_calls=0,
                error_owner="workbench",
                error_type=type(exc).__name__,
            )
            return {
                "run_id": run_id,
                "status": "failure",
                "error": {"type": type(exc).__name__, "code": error_code},
                "trace_path": str(self.traces.path),
            }

        active_after, active_read_failed = read_active_safely()
        if active_read_failed:
            recorder.event(
                "how.operation.failed",
                operation=operation,
                change_domain="implementation/how",
                active_before=active_before,
                active_after=None,
                candidate_implementation="ripgrep_search@1.0.0" if operation == "evolve_understand" else None,
                baseline_implementation=active_before,
                error_type="ActiveStateReadError",
                error_code="active_state_read_failed",
            )
            recorder.event("result.emitted", status="failure", error_code="active_state_read_failed")
            recorder.finish(
                "failure",
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                model_calls=0,
                error_owner="gateway",
                error_type="ActiveStateReadError",
            )
            return {
                "run_id": run_id,
                "status": "failure",
                "error": {"type": "ActiveStateReadError", "code": "active_state_read_failed"},
                "trace_path": str(self.traces.path),
            }
        if operation == "evolve_understand":
            evaluation = result.evaluation
            scores = dict(evaluation.scores)
            baseline_score = scores.get(active_before)
            candidate_score = scores.get("ripgrep_search@1.0.0")
            evaluation_status = str(evaluation.status)
            if active_after != active_before:
                activation_decision = "activated"
            elif not activation_requested:
                activation_decision = "not_requested"
            elif evaluation_status != "pass":
                activation_decision = "evaluation_failed"
            else:
                activation_decision = "candidate_not_better"
            safe_evaluation = {
                "evaluation_status": evaluation_status,
                "evaluator_id": str(evaluation.evaluator),
                "candidate_implementation": candidate_implementation,
                "baseline_implementation": active_before,
                "candidate_score": candidate_score,
                "baseline_score": baseline_score,
                "benchmark_sha256": benchmark_sha256,
                "benchmark_case_count": benchmark_case_count,
                "activation_decision": activation_decision,
                "active_before": active_before,
                "active_after": active_after,
            }
            evaluation_sha256 = hashlib.sha256(
                json.dumps(safe_evaluation, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
            recorder.event(
                "how.evaluation.completed",
                operation=operation,
                change_domain="implementation/how",
                candidate_implementation=candidate_implementation,
                baseline_implementation=active_before,
                benchmark_sha256=benchmark_sha256,
                benchmark_case_count=benchmark_case_count,
                evaluation_status=evaluation_status,
                evaluator_id=str(evaluation.evaluator),
                evaluation_sha256=evaluation_sha256,
                candidate_score=candidate_score,
                baseline_score=baseline_score,
                activation_decision=activation_decision,
                active_before=active_before,
                active_after=active_after,
            )
            terminal_status = "success" if evaluation_status == "pass" else "failure"
            recorder.event(
                "result.emitted",
                status=terminal_status,
                result_sha256=evaluation_sha256,
                **({"error_code": "how_evaluation_failed"} if terminal_status != "success" else {}),
            )
            recorder.finish(
                terminal_status,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                model_calls=0,
                **(
                    {"error_owner": "workbench_evaluator", "error_type": "EvaluationFailed"}
                    if terminal_status != "success"
                    else {}
                ),
            )
            return {
                "run_id": run_id,
                "status": terminal_status,
                "result": result,
                "trace_path": str(self.traces.path),
            }

        receipt_status = str(getattr(result, "status", "unknown"))
        to_implementation = str(getattr(result, "implementation", "unknown"))
        receipt_sha256 = hashlib.sha256(
            json.dumps(
                {"from": active_before, "to": to_implementation, "status": receipt_status},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        recorder.event(
            "how.rollback.completed",
            operation=operation,
            change_domain="implementation/how",
            from_implementation=active_before,
            to_implementation=to_implementation,
            status=receipt_status,
            active_before=active_before,
            active_after=active_after,
            receipt_sha256=receipt_sha256,
        )
        recorder.event("result.emitted", status="success", result_sha256=receipt_sha256)
        recorder.finish(
            "success",
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
            model_calls=0,
            error_owner=None,
        )
        return {
            "run_id": run_id,
            "status": "success",
            "result": result,
            "trace_path": str(self.traces.path),
        }

    def invoke_capability(
        self,
        *,
        capability_id: str,
        capability_version: str,
        parameters: dict[str, Any],
        invoke: Callable[[str, RunRecorder, str], Any],
        tool_events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run one Workbench invocation and append its correlated local observation."""
        run_id = _id("run")
        request_id = _id("req")
        invocation_id = _id("inv")
        started_at = time.perf_counter()
        input_json = json.dumps(
            parameters,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

        trace_id = uuid.uuid4().hex
        recorder = RunRecorder(
            self.traces,
            run_id=run_id,
            request_id=request_id,
            invocation_id=invocation_id,
            trace_id=trace_id,
        )
        recorder.start(
            request_kind="capability_invocation",
            input_sha256=hashlib.sha256(input_json).hexdigest(),
            actor="local_cli_user",
            component="CatalystGateway",
            capability_id=capability_id,
            capability_version=capability_version,
        )
        recorder.event(
            "capability.invoke.requested",
            capability_id=capability_id,
            capability_version=capability_version,
            arguments_sha256=hashlib.sha256(input_json).hexdigest(),
        )
        try:
            run = invoke(invocation_id, recorder, trace_id)
        except BaseException as exc:
            if not recorder.is_finished:
                if isinstance(exc, KeyboardInterrupt):
                    recorder.event("request.interrupted", error_type=type(exc).__name__, effect_certainty="unknown")
                    recorder.finish("interrupted")
                else:
                    recorder.event("request.failed", error_type=type(exc).__name__, error_message=str(exc))
                    recorder.finish("failure", error_type=type(exc).__name__)
            raise
        result = run.result.to_dict()
        status = run.result.status
        trace_path = self.traces.path
        native_trace_path = str(run.trace_path) if run.trace_path is not None else None
        provider = dict(run.trace.get("provider", {}))
        capability_calls = list(run.trace.get("capability_calls", []))
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        output = result.get("output")
        source = output.get("source") if isinstance(output, dict) else None
        result_bytes = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        recorder.event(
            "result.emitted",
            result_id=result.get("id"),
            status=status,
            result_sha256=hashlib.sha256(result_bytes).hexdigest(),
            source_sha256=source.get("sha256") if isinstance(source, dict) else None,
            source_line=source.get("line") if isinstance(source, dict) else None,
            extraction_method=source.get("extraction_method") if isinstance(source, dict) else None,
            error_code=(result.get("error") or {}).get("code") if isinstance(result.get("error"), dict) else None,
        )
        recorder.finish(
            status,
            duration_ms=duration_ms,
            error_owner=run.trace.get("failure_source"),
            model_calls=0 if provider.get("mode") == "offline" else None,
            provider_requests=provider.get("requests", 0),
            external_calls=provider.get("external_calls", 0),
            native_trace_path=native_trace_path,
        )
        persisted_trace_path = self.traces.path
        return {
            "run_id": run_id,
            "status": status,
            "result": result,
            "error": result.get("error"),
            "trace_path": str(persisted_trace_path),
            "execution_trace_path": native_trace_path,
        }

    def ask_natural_language(
        self,
        *,
        message: str,
        selected_file: Path | str | None,
        ask: Callable[[str, str, RunRecorder], Any],
        tool_events: list[dict[str, Any]] | None = None,
        recorder: RunRecorder | None = None,
    ) -> dict[str, Any]:
        """Route one natural-language ask through the Workbench and persist its event timeline."""
        selected_path = Path(selected_file).expanduser().resolve() if selected_file is not None else None
        input_json = json.dumps(
            {"message": message, "selected_file": str(selected_path) if selected_path else None},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if recorder is None:
            run_id = _id("run")
            request_id = _id("req")
            invocation_id = _id("inv")
            trace_id = uuid.uuid4().hex
            recorder = RunRecorder(
                self.traces,
                run_id=run_id,
                request_id=request_id,
                invocation_id=invocation_id,
                trace_id=trace_id,
            )
        else:
            run_id = recorder.run_id
            request_id = recorder.request_id
            invocation_id = recorder.invocation_id
            trace_id = recorder.trace_id
        if not recorder.is_started:
            recorder.start(
                request_kind="natural_language_ask",
                input_sha256=hashlib.sha256(input_json).hexdigest(),
                actor="local_cli_user",
                component="CatalystGateway",
                selected_file=str(selected_path) if selected_path else None,
            )
        started_at = time.perf_counter()
        try:
            run = ask(invocation_id, trace_id, recorder)
        except BaseException as exc:
            if not recorder.is_finished:
                if isinstance(exc, KeyboardInterrupt):
                    recorder.event("request.interrupted", error_type=type(exc).__name__, effect_certainty="unknown")
                    recorder.finish("interrupted")
                else:
                    recorder.event("request.failed", error_type=type(exc).__name__, error_message=str(exc))
                    recorder.finish("failure", error_type=type(exc).__name__)
            raise
        result = run.result.to_dict()
        status = run.result.status
        provider = dict(run.trace.get("provider", {}))
        native_trace_path = str(run.trace_path) if run.trace_path is not None else None
        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        output = result.get("output")
        source = None
        if isinstance(output, dict):
            tool_results = output.get("tool_results", [])
            if isinstance(tool_results, list):
                source = next(
                    (
                        item.get("output", {}).get("source")
                        for item in reversed(tool_results)
                        if isinstance(item, dict)
                        and isinstance(item.get("output"), dict)
                        and isinstance(item["output"].get("source"), dict)
                    ),
                    None,
                )
        result_bytes = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        source_summary = None
        if isinstance(source, dict):
            source_summary = {
                "sha256": source.get("sha256"),
                "line": source.get("line"),
                "extraction_method": source.get("extraction_method"),
            }
        recorder.event(
            "result.emitted",
            result_id=result.get("id"),
            status=status,
            result_sha256=hashlib.sha256(result_bytes).hexdigest(),
            source_evidence=source_summary,
            error_code=(result.get("error") or {}).get("code") if isinstance(result.get("error"), dict) else None,
        )
        recorder.finish(
            status,
            duration_ms=duration_ms,
            error_owner=run.trace.get("failure_source"),
            model_calls=run.trace.get("model_calls", 0),
            provider_requests=provider.get("requests", 0),
            external_calls=provider.get("external_calls", 0),
            token_usage=run.trace.get("token_usage"),
            session_id=run.session_id,
            native_trace_path=native_trace_path,
        )
        persisted_trace_path = self.traces.path
        return {
            "run_id": run_id,
            "request_id": request_id,
            "status": status,
            "result": result,
            "error": result.get("error"),
            "trace_path": str(persisted_trace_path),
            "execution_trace_path": native_trace_path,
        }

    def discover_capabilities(
        self, discover: Callable[[], list[dict[str, Any]]]
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        run_id = _id("run")
        request_id = _id("req")
        recorder = RunRecorder(
            self.traces,
            run_id=run_id,
            request_id=request_id,
            invocation_id=_id("inv"),
        )
        recorder.start(
            request_kind="capability_discovery",
            actor="local_cli_user",
            component="CatalystGateway",
        )
        try:
            capabilities = discover()
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            result_id = _id("res")
            recorder.event(
                "capabilities.discovery.failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            recorder.event(
                "result.emitted",
                result_id=result_id,
                status="failure",
                error_code="capability_catalog_failed",
            )
            recorder.finish(
                "failure",
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                error_owner="capability_catalog",
                model_calls=0,
            )
            trace_path = self.traces.path
            return {
                "run_id": run_id,
                "status": "failure",
                "error": error,
                "trace_path": str(trace_path),
            }

        ordered_capabilities = sorted(
            capabilities, key=lambda item: (item["id"], item["capability_version"])
        )
        invocation_routes = [
            {
                "capability_id": item["id"],
                "capability_version": item["capability_version"],
                "command": "invoke",
            }
            for item in ordered_capabilities
        ]
        catalog_snapshot = {
            "capabilities": ordered_capabilities,
            "invocation_routes": invocation_routes,
        }
        canonical_catalog = json.dumps(
            catalog_snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        catalog_sha256 = hashlib.sha256(canonical_catalog).hexdigest()
        capability_event_summaries = []
        for item in ordered_capabilities:
            descriptor_bytes = json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            execution = item.get("execution", {})
            capability_event_summaries.append(
                {
                    "id": item["id"],
                    "capability_version": item["capability_version"],
                    "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
                    "side_effect": execution.get("side_effect") if isinstance(execution, dict) else None,
                }
            )
        result_id = _id("res")
        recorder.event(
            "capabilities.discovered",
            capability_count=len(ordered_capabilities),
            catalog_scope="local_registered_product_bindings",
            authorization="not_evaluated_until_invocation",
            catalog_sha256=catalog_sha256,
            capabilities=capability_event_summaries,
            invocation_routes=invocation_routes,
        )
        recorder.event(
            "result.emitted",
            result_id=result_id,
            status="success",
            result_sha256=catalog_sha256,
        )
        recorder.finish(
            "success",
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
            model_calls=0,
        )
        trace_path = self.traces.path
        return {
            "run_id": run_id,
            "status": "success",
            "catalog_scope": "local_registered_product_bindings",
            "authorization": "not_evaluated_until_invocation",
            "capabilities": ordered_capabilities,
            "invocation_routes": invocation_routes,
            "catalog_sha256": catalog_sha256,
            "trace_path": str(trace_path),
        }

    def component_lifecycle(
        self,
        *,
        operation: str,
        action: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        """Record a bounded component catalog transition without storing package contents."""
        started_at = time.perf_counter()
        run_id = _id("run")
        request_id = _id("req")
        invocation_id = _id("inv")
        trace_id = uuid.uuid4().hex
        recorder = RunRecorder(
            self.traces,
            run_id=run_id,
            request_id=request_id,
            invocation_id=invocation_id,
            trace_id=trace_id,
        )
        recorder.start(
            request_kind="component_lifecycle",
            actor="local_cli_user",
            component="CatalystGateway",
        )
        try:
            details = action()
        except Exception as exc:
            recorder.event(
                "component.lifecycle.failed",
                action=operation,
                error_code="component_operation_failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            recorder.event(
                "result.emitted",
                status="failure",
                error_code="component_operation_failed",
            )
            recorder.finish(
                "failure",
                duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
                error_owner="component_lifecycle",
                model_calls=0,
            )
            return {
                "run_id": run_id,
                "status": "failure",
                "error": {"code": "component_operation_failed", "type": type(exc).__name__, "message": str(exc)},
                "trace_path": str(self.traces.path),
            }

        component = details.get("component", {}) if isinstance(details, dict) else {}
        transition = details.get("transition") if isinstance(details, dict) else None
        if not isinstance(transition, str):
            transition = "validated" if operation == "discover" else operation
        fields = {
            "transition": transition,
            "component_id": component.get("component_id"),
            "resource_type": component.get("resource_type", "tool"),
            "component_version": (
                component.get("component_version")
                or component.get("version")
                or details.get("previous_version")
            ),
            "capability_id": component.get("capability_id"),
            "capability_version": component.get("capability_version"),
            "previous_version": details.get("previous_version") if isinstance(details, dict) else None,
            "active_version": component.get("active_version"),
            "source_sha256": details.get("source_sha256") if isinstance(details, dict) else None,
            "manifest_sha256": details.get("manifest_sha256") if isinstance(details, dict) else None,
            "package_sha256": details.get("package_sha256") if isinstance(details, dict) else None,
            "llm_visibility": component.get("llm_visibility", "explicit"),
            "active": bool(component.get("active_version")),
            "in_flight_policy": "existing_runs_drain",
            "cleanup_status": details.get("cleanup_status") if isinstance(details, dict) else None,
        }
        recorder.event("component.lifecycle.changed", action=operation, **fields)
        result_digest = hashlib.sha256(
            json.dumps(details, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        recorder.event("result.emitted", status="success", result_sha256=result_digest)
        recorder.finish(
            "success",
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
            model_calls=0,
            error_owner=None,
        )
        return {
            "run_id": run_id,
            "status": "success",
            **details,
            "trace_path": str(self.traces.path),
        }

    @staticmethod
    def _error(
        status: str,
        standard_error: dict[str, Any] | None,
        tool_events: list[dict[str, Any]],
    ) -> dict[str, str] | None:
        if status == "success":
            return None
        tool_failure = next(
            (event for event in reversed(tool_events) if event["event_type"] == "tool.failed"),
            None,
        )
        if tool_failure is not None:
            return {
                "code": tool_failure["error_code"],
                "message": tool_failure["message"],
            }
        if standard_error is not None:
            return {
                "code": str(standard_error.get("code", "execution_failed")),
                "message": str(standard_error.get("message", "Execution failed.")),
            }
        return {"code": "execution_failed", "message": "Execution failed."}
