"""Run Observability: versioned, privacy-first observations written at execution time."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from .trace_log import JsonlTraceStore


# R4 event protocol compatibility name; responsibility is documented as Run Observability.
EVENT_SCHEMA_VERSION = "1.4"
SUPPORTED_WRITE_EVENT_SCHEMA_VERSIONS = {"1.4", "1.5", "1.6"}
REDACTION_POLICY_VERSION = "allowlisted-content-v2"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    try:
        payload = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    except (TypeError, ValueError):
        payload = str(value).encode("utf-8", "replace")
    return hashlib.sha256(payload).hexdigest()


def _source_identity() -> tuple[str | None, bool | None]:
    """Return the Git source revision and whether product source files are dirty."""
    repository = Path(__file__).resolve().parents[1]
    try:
        revision = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=2,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=2,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    if len(revision) != 40 or any(char not in "0123456789abcdefABCDEF" for char in revision):
        return None, None
    source_prefixes = (
        "agent_runtime/",
        "catalyst_platform/",
        "platform_standard/",
        "schemas/",
        "requirements",
        "pyproject.toml",
        "setup.py",
    )
    source_dirty = False
    for line in status.splitlines():
        path = line[3:].replace("\\", "/").strip(' "')
        if any(path.startswith(prefix) for prefix in source_prefixes):
            source_dirty = True
            break
    return f"git:{revision.lower()}", source_dirty


_HASH_FIELDS = {
    "answer": "answer_sha256",
    "arguments": "arguments_sha256",
    "error_message": "error_message_sha256",
    "content": "content_sha256",
    "exception_message": "exception_message_sha256",
    "input": "input_sha256",
    "message": "message_sha256",
    "native_trace_path": "native_trace_ref_sha256",
    "output": "output_sha256",
    "path": "path_sha256",
    "prompt": "prompt_sha256",
    "selected_file": "selected_file_sha256",
    "source_path": "source_path_sha256",
    "title": "title_sha256",
    "excerpt": "excerpt_sha256",
    "raw_body": "raw_body_sha256",
}
_DROP_FIELDS = {
    "api_key",
    "authorization",
    "bearer_token",
    "credential",
    "credentials",
    "password",
    "secret",
    "token_value",
}
_SECRET_VALUE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}\b|\bbearer\s+\S+|"
    r"\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*\S+)"
)

_EVENT_FIELDS: dict[str, set[str]] = {
    "request.started": {"request_kind", "input_sha256", "owner_process_id", "source_revision_ref", "source_worktree_dirty", "actor", "component", "selected_file", "capability_id", "capability_version"},
    "span.started": {"span_id", "parent_span_id", "span_name", "span_kind", "openinference.span.kind", "attributes", "model_call_id", "provider_id", "model", "configuration_source", "request_attempt", "tool_choice", "exposed_tools", "exposed_tool_count", "tool_call_id", "execution_id", "capability_internal_id", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "span.ended": {"span_id", "status", "duration_ms", "attributes"},
    "session.bound": {"runtime_session_id"},
    "request.terminal": {"terminal_status", "duration_ms", "model_calls", "provider_requests", "external_calls", "error_owner", "error_type", "token_usage", "session_id", "native_trace_path"},
    "request.interrupted": {"error_type", "effect_certainty"},
    "request.failed": {"error_type", "error_message"},
    "capability.invoke.requested": {"capability_id", "capability_version", "arguments_sha256"},
    "result.emitted": {"result_id", "status", "result_sha256", "source_sha256", "source_line", "extraction_method", "error_code", "source_evidence"},
    "capabilities.discovery.failed": {"error_type", "error_message"},
    "capabilities.discovered": {"capability_count", "catalog_scope", "authorization", "catalog_sha256", "capabilities", "invocation_routes"},
    "component.lifecycle.changed": {"action", "transition", "component_id", "resource_type", "component_version", "capability_id", "capability_version", "previous_version", "active_version", "source_sha256", "manifest_sha256", "package_sha256", "llm_visibility", "active", "in_flight_policy", "cleanup_status"},
    "component.lifecycle.failed": {"action", "error_code", "error_type"},
    "component.binding.failed": {"capability_id", "capability_version", "error_type", "error_code"},
    "component.cleanup.failed": {"component_id", "component_version", "capability_id", "capability_version", "error_type"},
    "agent.decision": {"model_call_id", "parent_span_id", "decision_type", "model_call_present", "tool_calls", "input_tokens", "output_tokens", "finish_reason"},
    "assistant.final_answer": {"model_call_id", "parent_span_id", "answer", "answer_status"},
    "binding.resolved": {"model_call_id", "parent_span_id", "tool_call_id", "capability_internal_id", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "binding.resolution_failed": {"model_call_id", "tool_call_id", "capability_internal_id", "error_code"},
    "tool.call.requested": {"model_call_id", "parent_span_id", "tool_call_id", "tool_name", "arguments_sha256", "capability_internal_id", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "authorization.decided": {"model_call_id", "parent_span_id", "tool_call_id", "decision", "reason_sha256", "capability_internal_id", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "tool.execution.started": {"span_id", "model_call_id", "parent_span_id", "tool_call_id", "execution_id", "capability_internal_id", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "tool.execution.denied": {"model_call_id", "parent_span_id", "tool_call_id", "capability_internal_id", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "tool.execution.unresolved": {"span_id", "model_call_id", "tool_call_id", "execution_id", "capability_internal_id", "status", "error_type", "effect_certainty", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "tool.result": {"span_id", "model_call_id", "parent_span_id", "tool_call_id", "execution_id", "capability_internal_id", "status", "result_sha256", "effect_certainty", "error_code", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "llm.request.started": {"model_call_id", "span_id", "provider_id", "model", "configuration_source", "request_attempt", "tool_choice", "exposed_tools", "exposed_tool_count"},
    "llm.request.failed": {"model_call_id", "span_id", "provider_id", "model", "error_type", "error_code", "error_category", "error_stage", "http_status", "provider_request_id", "retryable"},
    "llm.response.received": {"model_call_id", "span_id", "provider_id", "model", "response_sha256", "finish_reason", "input_tokens", "output_tokens", "cache_hit_input_tokens", "cache_miss_input_tokens", "tool_calls", "response_received"},
    "source.read.started": {"timestamp", "tool_id", "tool_version", "source_path", "requested_path", "source", "title", "error_code", "error_message"},
    "source.read.completed": {"timestamp", "tool_id", "tool_version", "source_path", "requested_path", "source", "title", "error_code", "error_message"},
    "source.read.failed": {"timestamp", "tool_id", "tool_version", "source_path", "requested_path", "source", "title", "error_code", "error_message"},
    "knowledge.source.staged": {"scope_id", "source_id", "source_revision", "status", "claim_count"},
    "semantic.external.action": {"action", "producer_origin", "evidence_level", "source_id", "source_revision", "submission_sha256", "candidate_id", "item_count", "internal_reasoning_status", "producer_usage_status", "correlation_id", "status", "error_code"},
    "understand.candidate.received": {"scope_id", "candidate_id", "submission_sha256", "producer_origin", "producer_version", "producer_identity_status", "source_manifest_sha256", "evidence_manifest_sha256", "parent_active_version_id", "active_version_id", "active_authority_class", "active_semantics_status", "source_count", "evidence_count", "item_count", "mapping_status", "status", "error_code"},
    "understand.graph.projected": {"scope_id", "candidate_id", "graph_sha256", "view", "active_version_id", "active_authority_class", "active_semantics_status", "node_count", "edge_count", "source_count", "warning_count", "status"},
    "understand.consumer.queried": {"scope_id", "candidate_id", "query_kind", "query_sha256", "result_count", "result_ids_sha256", "identity_status", "active_version_id", "active_authority_class", "active_semantics_status", "status"},
    "understand.evidence.resolved": {"scope_id", "candidate_id", "evidence_id", "source_id", "source_revision", "locator_kind", "span_sha256", "resolution_status", "active_version_id", "active_authority_class", "active_semantics_status"},
    "knowledge.source.staging_failed": {"scope_id", "status", "error_code"},
    "knowledge.query.returned": {"scope_id", "query_sha256", "status", "applicability_status", "source_count", "claim_count", "capability_count", "read_mode", "freshness_status", "active_version_id", "document_count"},
    "knowledge.document.discovered": {"scope_id", "read_mode", "document_id", "source_id", "source_revision", "current_revision", "revision_status", "freshness_status", "status", "actor_origin"},
    "knowledge.claim.retrieved": {"scope_id", "claim_id", "source_id", "source_revision", "claim_status", "line_start", "line_end", "span_sha256", "capability_id", "capability_version", "read_mode", "freshness_status", "authority"},
    "knowledge.claim.used_for_decision": {"scope_id", "claim_id", "source_id", "source_revision", "capability_id", "capability_version", "tool_call_id", "binding_digest", "outcome"},
    "semantic.transition.started": {"scope_id", "transition_id", "operation", "status", "actor_origin"},
    "semantic.transition.failed": {"scope_id", "transition_id", "operation", "status", "error_code", "actor_origin", "candidate_id", "version_id", "source_id", "source_revision", "expected_head_version_id", "branch_switch"},
    "semantic.transition.recovered": {"scope_id", "transition_id", "operation", "status", "actor_origin", "from_version_id", "to_version_id"},
    "semantic.source.staged": {"scope_id", "transition_id", "source_id", "source_revision", "status", "meaning_count", "actor_origin"},
    "semantic.candidate.proposed": {"scope_id", "transition_id", "candidate_id", "parent_version_id", "source_id", "source_revision", "meaning_count", "meaning_ids_sha256", "actor_origin", "status"},
    "semantic.candidate.evidence": {"scope_id", "candidate_id", "meaning_id", "canonical_id", "source_id", "source_revision", "line_start", "line_end", "span_sha256", "actor_origin"},
    "semantic.candidate.evaluated": {"scope_id", "transition_id", "candidate_id", "evaluation_id", "evaluator_id", "evaluation_type", "source_id", "source_revision", "status", "finding_count", "finding_codes", "finding_ids_sha256", "actor_origin"},
    "semantic.candidate.external_evaluation.received": {"scope_id", "transition_id", "candidate_id", "source_id", "source_revision", "evaluation_id", "evaluation_type", "evaluator_id", "recommendation", "authority_status", "candidate_sha256", "receipt_id", "receipt_authority_class", "rubric_sha256", "report_sha256", "finding_count", "finding_ids_sha256", "internal_reasoning_status", "external_usage_status", "actor_origin", "status"},
    "semantic.candidate.decided": {"scope_id", "transition_id", "candidate_id", "evaluation_id", "external_evaluation_id", "decision_id", "decision", "version_id", "source_id", "source_revision", "reason_code", "authority_receipt_id", "authority_class", "authority_issuer_id", "actor_origin", "status"},
    "semantic.version.accepted": {"scope_id", "transition_id", "candidate_id", "decision_id", "external_evaluation_id", "authority_receipt_id", "authority_class", "authority_issuer_id", "version_id", "parent_version_id", "source_id", "source_revision", "meaning_count", "actor_origin", "status"},
    "semantic.version.activated": {"scope_id", "transition_id", "candidate_id", "source_id", "source_revision", "version_id", "active_version_id", "from_version_id", "to_version_id", "expected_head_version_id", "branch_switch", "authority_receipt_id", "authority_class", "authority_issuer_id", "status", "actor_origin"},
    "semantic.version.rolled_back": {"scope_id", "transition_id", "candidate_id", "source_id", "source_revision", "version_id", "active_version_id", "from_version_id", "to_version_id", "expected_head_version_id", "authority_receipt_id", "authority_class", "authority_issuer_id", "status", "actor_origin"},
    "semantic.version.diffed": {"scope_id", "transition_id", "candidate_id", "parent_version_id", "source_id", "source_revision", "added_count", "changed_count", "removed_count", "evidence_added_count", "evidence_removed_count", "status", "actor_origin"},
    "semantic.consumer.queried": {"scope_id", "transition_id", "version_id", "active_version_id", "query_sha256", "meaning_count", "meaning_ids_sha256", "document_count", "document_ids_sha256", "claim_count", "claim_ids_sha256", "stale_meaning_count", "read_mode", "freshness_status", "knowledge_status", "status", "actor_origin"},
    "semantic.consumer.meaning_consumed": {"scope_id", "version_id", "meaning_id", "canonical_id", "source_id", "source_revision", "claim_id", "line_start", "line_end", "span_sha256", "freshness_status", "actor_origin", "status"},
    "semantic.state.inspected": {"scope_id", "transition_id", "version_id", "candidate_count", "candidate_ids_sha256", "accepted_version_count", "accepted_version_ids_sha256", "meaning_count", "meaning_ids_sha256", "status", "actor_origin"},
    "how.operation.started": {"operation", "change_domain", "active_before", "candidate_implementation", "baseline_implementation", "benchmark_sha256", "benchmark_case_count", "activation_requested"},
    "how.evaluation.completed": {"operation", "change_domain", "candidate_implementation", "baseline_implementation", "benchmark_sha256", "benchmark_case_count", "evaluation_status", "evaluator_id", "evaluation_sha256", "candidate_score", "baseline_score", "activation_decision", "active_before", "active_after"},
    "how.rollback.completed": {"operation", "change_domain", "from_implementation", "to_implementation", "status", "active_before", "active_after", "receipt_sha256"},
    "how.operation.failed": {"operation", "change_domain", "active_before", "active_after", "candidate_implementation", "baseline_implementation", "error_type", "error_code"},
}

_NESTED_EVENT_FIELDS: dict[str, set[str]] = {
    "attributes": {
        "openinference.span.kind", "llm.system", "llm.model_name", "catalyst.configuration_source",
        "tool.name", "tool.call_id", "catalyst.execution_id", "catalyst.binding_digest",
        "catalyst.capability_version", "model_call_id", "tool_call_id", "execution_id",
        "capability_internal_id", "status", "result_sha256", "effect_certainty", "capability_id",
        "capability_version", "binding_digest", "side_effect", "implementation_class",
        "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256",
        "error.type", "catalyst.error.code", "llm.token_count.prompt", "llm.token_count.completion",
        "llm.finish_reason", "usage.input_tokens", "usage.output_tokens",
        "catalyst.llm.task_id", "catalyst.llm.request_id", "catalyst.llm.attempts",
        "catalyst.llm.max_requests", "catalyst.llm.charged_cny", "catalyst.llm.reserved_per_request_cny",
        "catalyst.llm.budget_cny", "catalyst.llm.uncertain", "catalyst.llm.last_status",
        "catalyst.llm.input_tokens", "catalyst.llm.output_tokens", "catalyst.llm.price_reference",
    },
    "tool_calls": {"tool_call_id", "tool_name", "arguments_sha256"},
    "exposed_tools": {"tool_name", "parameters_schema_sha256", "capability_id", "capability_version", "binding_digest", "side_effect", "implementation_class", "component_id", "component_version", "manifest_sha256", "source_sha256", "package_sha256"},
    "capabilities": {"id", "capability_version", "descriptor_sha256", "side_effect"},
    "invocation_routes": {"capability_id", "capability_version", "command"},
    "token_usage": {"input_tokens", "output_tokens"},
    "source_evidence": {"sha256", "line", "extraction_method"},
    "source": {"path", "source_id", "sha256", "byte_length", "line", "extraction_method"},
}


def _safe_scalar(key: str, value: Any) -> Any:
    if value is None or type(value) in (bool, int, float):
        return value
    if not isinstance(value, str) or _SECRET_VALUE.search(value):
        return None
    redacted = redact_fields({key: value})
    return next(iter(redacted.values())) if redacted else None


def _sanitize_nested(field: str, value: Any) -> Any:
    allowed = _NESTED_EVENT_FIELDS[field]

    def project(item: Any) -> Any:
        if isinstance(item, Mapping):
            safe = {}
            for key, raw in item.items():
                name = str(key)
                normalized = name.casefold()
                if name not in allowed or normalized in _DROP_FIELDS:
                    continue
                if isinstance(raw, (Mapping, list, tuple)):
                    continue
                candidate = _safe_scalar(normalized, raw)
                if candidate is not None or raw is None:
                    safe[name] = candidate
            return safe
        if isinstance(item, (list, tuple)):
            return [project(child) for child in item if isinstance(child, Mapping)]
        return None

    return project(value)


def _sanitize_event_fields(event_type: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    allowed = _EVENT_FIELDS.get(event_type)
    if allowed is None:
        raise ValueError(f"unsupported run event type: {event_type}")
    safe: dict[str, Any] = {}
    for field, value in fields.items():
        if field not in allowed:
            continue
        if field in _NESTED_EVENT_FIELDS:
            safe[field] = _sanitize_nested(field, value)
        elif isinstance(value, (Mapping, list, tuple)):
            continue
        else:
            candidate = _safe_scalar(field, value)
            if candidate is not None or value is None:
                safe[field] = candidate
    return safe


def redact_fields(value: Any, *, schema: bool = False) -> Any:
    """Hash content-bearing fields and remove credential-bearing fields recursively."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.casefold()
            if normalized in _DROP_FIELDS or normalized.endswith(".api_key") or any(
                marker in normalized for marker in ("password", "credential", "secret")
            ):
                continue
            if normalized == "parameters":
                result["parameters_sha256"] = _digest(item)
                continue
            if schema or normalized in {"input_schema", "output_schema"}:
                result[key] = redact_fields(item, schema=True)
                continue
            if normalized in _HASH_FIELDS and item is not None:
                result[_HASH_FIELDS[normalized]] = _digest(item)
            elif normalized.endswith("_path") and item is not None:
                result[f"{key[:-5]}_path_sha256"] = _digest(item)
            else:
                result[key] = redact_fields(item)
        return result
    if isinstance(value, (list, tuple)):
        return [redact_fields(item, schema=schema) for item in value]
    return value


def record_file_tool_event(recorder: "RunRecorder", event: Mapping[str, Any]) -> None:
    """Project a file reader's live callbacks into safe source lifecycle events."""
    mapped = {
        "tool.started": "source.read.started",
        "tool.completed": "source.read.completed",
        "tool.failed": "source.read.failed",
    }.get(event.get("event_type"))
    if mapped is None:
        return
    recorder.event(
        mapped,
        timestamp=event.get("timestamp"),
        tool_id=event.get("tool_id"),
        tool_version=event.get("tool_version"),
        source_path=event.get("source_path"),
        requested_path=event.get("requested_path"),
        source=event.get("source"),
        title=event.get("title"),
        error_code=event.get("error_code"),
        error_message=event.get("message"),
    )


class RunRecorder:
    """Append run events for Runtime hooks, monitor/replay consumers, and optional OTLP export."""

    def __init__(
        self,
        store: JsonlTraceStore,
        *,
        run_id: str,
        request_id: str,
        invocation_id: str,
        trace_id: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        event_schema_version: str = EVENT_SCHEMA_VERSION,
    ) -> None:
        self.store = store
        self.run_id = run_id
        self.request_id = request_id
        self.invocation_id = invocation_id
        self.trace_id = trace_id or uuid.uuid4().hex
        self.session_id = session_id
        if event_schema_version not in SUPPORTED_WRITE_EVENT_SCHEMA_VERSIONS:
            raise ValueError("unsupported run event schema version for new records")
        self.event_schema_version = event_schema_version
        if correlation_id is not None and (
            not isinstance(correlation_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", correlation_id) is None
        ):
            raise ValueError("correlation_id must be an opaque local identifier")
        self.correlation_id = correlation_id
        self.root_span_id = uuid.uuid4().hex[:16]
        self._sequence = 0
        self._started = False
        self._finished = False
        self._span_starts: dict[str, float] = {}
        self._model_spans: dict[str, str] = {}
        self._next_model_parent_span_id: str | None = None

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def is_started(self) -> bool:
        return self._started

    def _append(self, event_type: str, **fields: Any) -> dict[str, Any]:
        if self._finished:
            raise RuntimeError("cannot append to a finished run")
        safe_fields = _sanitize_event_fields(event_type, fields)
        event = redact_fields(
            {
                "event_id": uuid.uuid4().hex,
                "event_type": event_type,
                "redaction_policy_version": REDACTION_POLICY_VERSION,
                "timestamp": _utc_now(),
                "request_id": self.request_id,
                "invocation_id": self.invocation_id,
                "trace_id": self.trace_id,
                "session_id": self.session_id,
                "run_id": self.run_id,
                "sequence": self._sequence,
                "event_schema_version": self.event_schema_version,
                **({"correlation_id": self.correlation_id} if self.correlation_id else {}),
                **safe_fields,
            }
        )
        self.store.append_event(self.run_id, self._sequence, event)
        self._sequence += 1
        return event

    def start(self, *, request_kind: str, input_sha256: str | None = None, **fields: Any) -> None:
        if self._started:
            raise RuntimeError("run has already started")
        self._started = True
        source_revision_ref, source_worktree_dirty = _source_identity()
        self._append(
            "request.started",
            request_kind=request_kind,
            input_sha256=input_sha256,
            owner_process_id=os.getpid(),
            source_revision_ref=source_revision_ref,
            source_worktree_dirty=source_worktree_dirty,
            **fields,
        )
        self._span_starts[self.root_span_id] = time.perf_counter()
        self._append(
            "span.started",
            span_id=self.root_span_id,
            parent_span_id=None,
            span_name="catalyst.run",
            span_kind="CHAIN",
            **{"openinference.span.kind": "CHAIN"},
        )

    def bind_session(self, session_id: str) -> None:
        """Attach the concrete Runtime session after the run has been created."""
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string")
        if not self._started or self._finished:
            raise RuntimeError("an active run is required to bind a session")
        if self.session_id is not None and self.session_id != session_id:
            raise RuntimeError("run is already bound to another session")
        if self.session_id is None:
            self.session_id = session_id
            self.event("session.bound", runtime_session_id=session_id)

    def register_model_span(self, model_call_id: str, span_id: str) -> None:
        self._model_spans[model_call_id] = span_id

    def model_span_id(self, model_call_id: str | None) -> str | None:
        return self._model_spans.get(model_call_id) if model_call_id else None

    def set_next_model_parent_span(self, span_id: str) -> None:
        self._next_model_parent_span_id = span_id

    def consume_next_model_parent_span(self) -> str | None:
        span_id = self._next_model_parent_span_id
        self._next_model_parent_span_id = None
        return span_id

    def event(self, event_type: str, **fields: Any) -> dict[str, Any]:
        if not self._started:
            raise RuntimeError("run must start before events are recorded")
        return self._append(event_type, **fields)

    def start_span(
        self,
        name: str,
        *,
        kind: str,
        parent_span_id: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        **fields: Any,
    ) -> str:
        if not self._started:
            raise RuntimeError("run must start before spans are recorded")
        span_id = uuid.uuid4().hex[:16]
        self._span_starts[span_id] = time.perf_counter()
        safe_attributes = dict(attributes or {})
        safe_attributes.setdefault("openinference.span.kind", kind)
        self._append(
            "span.started",
            span_id=span_id,
            parent_span_id=parent_span_id or self.root_span_id,
            span_name=name,
            span_kind=kind,
            attributes=safe_attributes,
            **fields,
        )
        return span_id

    def end_span(
        self,
        span_id: str,
        *,
        status: str,
        attributes: Mapping[str, Any] | None = None,
        **fields: Any,
    ) -> None:
        started = self._span_starts.pop(span_id, None)
        if started is None:
            raise ValueError(f"unknown or already ended span: {span_id}")
        self._append(
            "span.ended",
            span_id=span_id,
            status=status,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            attributes=dict(attributes or {}),
            **fields,
        )

    def finish(self, status: str, **fields: Any) -> None:
        if not self._started:
            raise RuntimeError("run must start before it can finish")
        if self._finished:
            raise RuntimeError("run has already finished")
        for span_id in list(self._span_starts):
            if span_id != self.root_span_id:
                self.end_span(span_id, status="incomplete")
        self.end_span(self.root_span_id, status=status)
        self._append(
            "request.terminal",
            terminal_status=status,
            **fields,
        )
        self._finished = True


class RuntimeObservationBridge:
    """Translate Agent Runtime facts into the compatible Run Observability event contract."""

    def __init__(
        self,
        recorder: RunRecorder,
        invocation_id: str,
        binding_resolver,
        *,
        tool_call_observer: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self.recorder = recorder
        self.invocation_id = invocation_id
        self.binding_resolver = binding_resolver
        self.tool_call_observer = tool_call_observer
        self.execution_spans: dict[str, str] = {}

    def __call__(self, fact: Mapping[str, Any]) -> None:
        event_type = fact["event_type"]
        step_index = fact.get("step_index")
        model_call_id = (
            f"{self.invocation_id}:llm:{step_index}"
            if step_index is not None
            else None
        )
        internal_id = fact.get("capability_internal_id")
        binding = self.binding_resolver(internal_id) if internal_id else None
        binding_fields = dict(binding or {})
        model_span_id = self.recorder.model_span_id(model_call_id)

        if event_type == "reasoning.completed":
            self.recorder.event(
                "agent.decision",
                model_call_id=model_call_id,
                parent_span_id=model_span_id or self.recorder.root_span_id,
                decision_type=fact.get("decision_type"),
                model_call_present=fact.get("model_call_present"),
                tool_calls=fact.get("tool_calls", []),
                input_tokens=fact.get("input_tokens"),
                output_tokens=fact.get("output_tokens"),
                finish_reason=fact.get("finish_reason"),
            )
            if fact.get("answer") is not None:
                self.recorder.event(
                    "assistant.final_answer",
                    model_call_id=model_call_id,
                    parent_span_id=model_span_id or self.recorder.root_span_id,
                    answer=fact.get("answer"),
                    answer_status="submitted",
                )
        elif event_type == "tool.requested":
            if binding:
                self.recorder.event(
                    "binding.resolved",
                    model_call_id=model_call_id,
                    parent_span_id=model_span_id or self.recorder.root_span_id,
                    tool_call_id=fact.get("tool_call_id"),
                    capability_internal_id=internal_id,
                    **binding_fields,
                )
            else:
                self.recorder.event(
                    "binding.resolution_failed",
                    model_call_id=model_call_id,
                    tool_call_id=fact.get("tool_call_id"),
                    capability_internal_id=internal_id,
                    error_code="binding_not_found",
                )
            self.recorder.event(
                "tool.call.requested",
                model_call_id=model_call_id,
                parent_span_id=model_span_id or self.recorder.root_span_id,
                tool_call_id=fact.get("tool_call_id"),
                tool_name=internal_id,
                arguments_sha256=fact.get("arguments_sha256"),
                **binding_fields,
            )
            if self.tool_call_observer is not None and binding:
                self.tool_call_observer(
                    {
                        "model_call_id": model_call_id,
                        "tool_call_id": fact.get("tool_call_id"),
                        **binding_fields,
                    }
                )
        elif event_type == "authorization.decided":
            self.recorder.event(
                "authorization.decided",
                model_call_id=model_call_id,
                parent_span_id=model_span_id or self.recorder.root_span_id,
                tool_call_id=fact.get("tool_call_id"),
                decision=fact.get("decision"),
                reason_sha256=fact.get("reason_sha256"),
                **binding_fields,
            )
        elif event_type == "capability.execution.started":
            execution_id = fact["execution_id"]
            span_id = self.recorder.start_span(
                "capability.execute",
                kind="TOOL",
                parent_span_id=model_span_id or self.recorder.root_span_id,
                attributes={
                    "openinference.span.kind": "TOOL",
                    "tool.name": (binding_fields.get("capability_id") or internal_id),
                    "tool.call_id": fact.get("tool_call_id"),
                    "catalyst.execution_id": execution_id,
                    "catalyst.binding_digest": binding_fields.get("binding_digest"),
                    "catalyst.capability_version": binding_fields.get("capability_version"),
                },
                model_call_id=model_call_id,
                tool_call_id=fact.get("tool_call_id"),
                execution_id=execution_id,
                capability_internal_id=internal_id,
                **binding_fields,
            )
            self.execution_spans[execution_id] = span_id
            self.recorder.event(
                "tool.execution.started",
                span_id=span_id,
                model_call_id=model_call_id,
                parent_span_id=model_span_id or self.recorder.root_span_id,
                tool_call_id=fact.get("tool_call_id"),
                execution_id=execution_id,
                capability_internal_id=internal_id,
                **binding_fields,
            )
        elif event_type == "capability.execution.completed":
            execution_id = fact["execution_id"]
            span_id = self.execution_spans.pop(execution_id, None)
            fields = {
                "model_call_id": model_call_id,
                "tool_call_id": fact.get("tool_call_id"),
                "execution_id": execution_id,
                "capability_internal_id": internal_id,
                "status": fact.get("status"),
                "result_sha256": fact.get("result_sha256"),
                "effect_certainty": fact.get("effect_certainty"),
                **binding_fields,
            }
            if span_id is not None:
                self.recorder.end_span(
                    span_id,
                    status=fact.get("status", "unknown"),
                    attributes=fields,
                )
            self.recorder.event("tool.result", span_id=span_id, **fields)
            if span_id is not None:
                self.recorder.set_next_model_parent_span(span_id)
        elif event_type == "capability.execution.unresolved":
            execution_id = fact["execution_id"]
            span_id = self.execution_spans.pop(execution_id, None)
            fields = {
                "model_call_id": model_call_id,
                "tool_call_id": fact.get("tool_call_id"),
                "execution_id": execution_id,
                "capability_internal_id": internal_id,
                "status": "unresolved",
                "error_type": fact.get("error_type"),
                "effect_certainty": fact.get("effect_certainty", "unknown"),
                **binding_fields,
            }
            if span_id is not None:
                self.recorder.end_span(span_id, status="incomplete", attributes=fields)
            self.recorder.event("tool.execution.unresolved", span_id=span_id, **fields)
        elif event_type == "capability.execution.denied":
            self.recorder.event(
                "tool.execution.denied",
                model_call_id=model_call_id,
                parent_span_id=model_span_id or self.recorder.root_span_id,
                tool_call_id=fact.get("tool_call_id"),
                capability_internal_id=internal_id,
                **binding_fields,
            )
            self.recorder.event(
                "tool.result",
                model_call_id=model_call_id,
                parent_span_id=model_span_id or self.recorder.root_span_id,
                tool_call_id=fact.get("tool_call_id"),
                capability_internal_id=internal_id,
                status="denied",
                effect_certainty="confirmed_not_executed",
                error_code="authorization_denied",
                **binding_fields,
            )


class ObservedModelProvider:
    """Record provider attempts and responses around the real request boundary."""

    def __init__(
        self,
        delegate: Any,
        recorder: RunRecorder,
        *,
        invocation_id: str,
        tool_identity_resolver=None,
    ) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._invocation_id = invocation_id
        self._tool_identity_resolver = tool_identity_resolver or (lambda _name: None)
        self._request_number = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def _budget_attributes(self) -> dict[str, Any]:
        snapshot = getattr(self._delegate, 'budget_snapshot', {})
        if not isinstance(snapshot, Mapping):
            return {}
        return {f'catalyst.llm.{key}': value for key, value in snapshot.items()
                if f'catalyst.llm.{key}' in _NESTED_EVENT_FIELDS['attributes']}

    def request(self, request: Any) -> Any:
        self._request_number += 1
        model_call_id = f"{self._invocation_id}:llm:{self._request_number - 1}"
        provider_id = getattr(self._delegate, "provider_id", type(self._delegate).__name__)
        model = getattr(self._delegate, "model", None)
        configuration_source = getattr(self._delegate, "configuration_source", None)
        exposed_tools = []
        for tool in getattr(request, "tools", ()):
            tool_name = getattr(tool, "name", None)
            parameters = getattr(tool, "parameters", None)
            if isinstance(tool, Mapping):
                tool_name = tool.get("name", tool_name)
                parameters = tool.get("parameters", parameters)
            identity = self._tool_identity_resolver(tool_name) if isinstance(tool_name, str) else None
            exposed_tools.append(
                {
                    "tool_name": tool_name,
                    "parameters_schema_sha256": _digest(parameters),
                    **dict(identity or {}),
                }
            )
        span_id = self._recorder.start_span(
            "llm.request",
            kind="LLM",
            parent_span_id=(
                self._recorder.consume_next_model_parent_span()
                or self._recorder.root_span_id
            ),
            attributes={
                "openinference.span.kind": "LLM",
                "llm.system": str(provider_id),
                "llm.model_name": model,
                "catalyst.configuration_source": configuration_source,
            },
            model_call_id=model_call_id,
            provider_id=str(provider_id),
            model=model,
            configuration_source=configuration_source,
        )
        self._recorder.register_model_span(model_call_id, span_id)
        self._recorder.event(
            "llm.request.started",
            model_call_id=model_call_id,
            span_id=span_id,
            provider_id=str(provider_id),
            model=model,
            configuration_source=configuration_source,
            request_attempt=self._request_number,
            tool_choice=getattr(request, "tool_choice", None),
            exposed_tools=exposed_tools,
            exposed_tool_count=len(exposed_tools),
        )
        try:
            response = self._delegate.request(request)
        except Exception as exc:
            error_fields = {
                "model_call_id": model_call_id,
                "span_id": span_id,
                "provider_id": str(provider_id),
                "model": model,
                "error_type": type(exc).__name__,
                # An event's error_code is a string in the event contract: a raised exception
                # that carries no public code is still a failed provider request, and saying so
                # beats a null that no reader (and no schema check) can read.
                "error_code": (getattr(exc, "public_code", None) or getattr(exc, "code", None)
                               or "PROVIDER_REQUEST_FAILED"),
                "error_category": getattr(exc, "category", None),
                "error_stage": getattr(exc, "stage", "provider_request"),
                "http_status": getattr(exc, "status", None),
                "provider_request_id": getattr(exc, "request_id", None),
                "retryable": bool(getattr(exc, "retryable", False)),
            }
            self._recorder.event("llm.request.failed", **error_fields)
            self._recorder.end_span(
                span_id,
                status="error",
                attributes={
                    "error.type": type(exc).__name__,
                    "catalyst.error.code": error_fields["error_code"],
                    **self._budget_attributes(),
                },
            )
            raise

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        cache_hit_input_tokens = getattr(usage, "cache_hit_input_tokens", None)
        cache_miss_input_tokens = getattr(usage, "cache_miss_input_tokens", None)
        cache_usage_fields = {}
        if cache_hit_input_tokens is not None and cache_miss_input_tokens is not None:
            cache_usage_fields = {
                "cache_hit_input_tokens": cache_hit_input_tokens,
                "cache_miss_input_tokens": cache_miss_input_tokens,
            }
        calls = []
        for call in getattr(response, "tool_calls", ()):
            calls.append(
                {
                    "tool_call_id": getattr(call, "id", None),
                    "tool_name": getattr(call, "name", None),
                    "arguments_sha256": _digest(getattr(call, "arguments", "")),
                }
            )
        content = getattr(response, "content", None)
        self._recorder.event(
            "llm.response.received",
            model_call_id=model_call_id,
            span_id=span_id,
            provider_id=str(provider_id),
            model=model,
            response_sha256=_digest(content) if content is not None else None,
            finish_reason=getattr(response, "finish_reason", None),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            **cache_usage_fields,
            tool_calls=calls,
            response_received=True,
        )
        self._recorder.end_span(
            span_id,
            status="success",
            attributes={
                "llm.token_count.prompt": input_tokens,
                "llm.token_count.completion": output_tokens,
                "llm.finish_reason": getattr(response, "finish_reason", None),
                **self._budget_attributes(),
            },
        )
        return response
