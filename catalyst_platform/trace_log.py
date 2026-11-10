"""Readable, append-only local JSONL run traces for the Catalyst CLI."""

from __future__ import annotations

import json
import contextlib
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class TraceStoreError(RuntimeError):
    """A persisted trace cannot be read or written safely."""


def _validate_record(record: Any, line_number: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TraceStoreError(f"invalid trace record at line {line_number}; expected a JSON object")
    required_types = {
        "run_id": str,
        "sequence": int,
        "timestamp": str,
        "event_type": str,
    }
    for field, expected_type in required_types.items():
        value = record.get(field)
        valid = type(value) is expected_type if expected_type is int else isinstance(value, expected_type)
        if not valid:
            raise TraceStoreError(
                f"invalid trace record at line {line_number}; field {field!r} is missing or invalid"
            )
    if record["sequence"] < 0:
        raise TraceStoreError(
            f"invalid trace record at line {line_number}; field 'sequence' must be nonnegative"
        )
    if record["event_type"] == "request.terminal" and not isinstance(
        record.get("terminal_status"), str
    ):
        raise TraceStoreError(
            f"invalid trace record at line {line_number}; terminal status is missing or invalid"
        )
    schema_version = record.get("event_schema_version")
    if schema_version not in (None, "0.9", "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6"):
        raise TraceStoreError(
            f"invalid trace record at line {line_number}; unsupported event schema version"
        )
    if schema_version in ("1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6"):
        for field in (
            "event_id",
            "request_id",
            "invocation_id",
            "trace_id",
            "redaction_policy_version",
        ):
            if not isinstance(record.get(field), str) or not record[field]:
                raise TraceStoreError(
                    f"invalid trace record at line {line_number}; field {field!r} is missing or invalid"
                )
        trace_id = record["trace_id"]
        if len(trace_id) != 32 or any(char not in "0123456789abcdefABCDEF" for char in trace_id):
            raise TraceStoreError(
                f"invalid trace record at line {line_number}; trace_id must be 32 hexadecimal characters"
            )
    return record


def _process_is_alive(process_id: Any) -> bool:
    if type(process_id) is not int or process_id <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        process = kernel32.OpenProcess(0x1000, False, process_id)
        if not process:
            return ctypes.get_last_error() == 5  # Access denied means the PID exists.
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(process, ctypes.byref(exit_code)):
                return False
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(process)
    try:
        os.kill(process_id, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class JsonlTraceStore:
    """Append one UTF-8 JSON object per material event and read by run id."""

    def __init__(self, workspace: Path) -> None:
        self.path = workspace / ".catalyst" / "traces" / "runs.jsonl"
        self._lock = threading.RLock()

    @contextlib.contextmanager
    def _writer_lock(self):
        """Serialize JSONL writes across threads and local processes."""
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock_file:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def append_event(
        self, run_id: str, sequence: int, event: dict[str, Any]
    ) -> Path:
        """Durably append one event so a concurrent reader can see partial runs."""
        if not isinstance(run_id, str) or not run_id:
            raise TraceStoreError("run_id must be a non-empty string")
        if type(sequence) is not int or sequence < 0:
            raise TraceStoreError("event sequence must be a nonnegative integer")
        if not isinstance(event, dict) or not isinstance(event.get("event_type"), str):
            raise TraceStoreError("event must be an object with an event_type")

        record = {
            "event_schema_version": event.get("event_schema_version", "1.0"),
            "run_id": run_id,
            "sequence": sequence,
            "timestamp": event.get("timestamp") or _utc_now(),
            **{key: value for key, value in event.items() if key != "timestamp"},
        }
        try:
            encoded = json.dumps(
                record,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ) + "\n"
        except (TypeError, ValueError) as exc:
            raise TraceStoreError("event is not valid JSON") from exc

        with self._lock, self._writer_lock():
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise TraceStoreError(
                    f"could not persist run event: {type(exc).__name__}"
                ) from exc
        return self.path

    def append_run(self, run_id: str, events: Iterable[dict[str, Any]]) -> Path:
        records = list(events)
        if not records or records[-1].get("event_type") != "request.terminal":
            raise TraceStoreError("a run trace must end with request.terminal")

        with self._lock, self._writer_lock():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                    for sequence, event in enumerate(records):
                        record = {
                            "event_schema_version": "0.9",
                            "run_id": run_id,
                            "sequence": sequence,
                            "timestamp": event.get("timestamp") or _utc_now(),
                            **{key: value for key, value in event.items() if key != "timestamp"},
                        }
                        stream.write(
                            json.dumps(
                                record,
                                ensure_ascii=False,
                                allow_nan=False,
                                separators=(",", ":"),
                            )
                            + "\n"
                        )
                    stream.flush()
                    os.fsync(stream.fileno())
            except (OSError, TypeError, ValueError) as exc:
                raise TraceStoreError(f"could not persist run trace: {type(exc).__name__}") from exc
        return self.path

    def inspect_run(self, run_id: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None

        matches: list[dict[str, Any]] = []
        trailing_partial_record = False
        with self._lock, self._writer_lock():
            try:
                with self.path.open("r", encoding="utf-8") as stream:
                    lines = stream.readlines()
                    for line_number, line in enumerate(lines, start=1):
                        if not line.strip():
                            continue
                        if line_number == len(lines) and not line.endswith("\n"):
                            trailing_partial_record = True
                            continue
                        try:
                            record = _validate_record(json.loads(line), line_number)
                        except json.JSONDecodeError as exc:
                            raise TraceStoreError(
                                f"invalid JSONL at line {line_number}; trace was not changed"
                            ) from exc
                        if record.get("run_id") == run_id:
                            matches.append(record)
            except UnicodeDecodeError as exc:
                raise TraceStoreError("trace file is not valid UTF-8; it was not changed") from exc
            except OSError as exc:
                raise TraceStoreError(f"could not read run trace: {type(exc).__name__}") from exc

        if not matches:
            return None
        matches.sort(key=lambda event: event["sequence"])
        terminal = next(
            (event for event in reversed(matches) if event["event_type"] == "request.terminal"),
            None,
        )
        terminal_status = terminal.get("terminal_status") if terminal else None
        start_record = next(
            (event for event in matches if event["event_type"] == "request.started"),
            None,
        )
        active = bool(
            terminal is None
            and start_record is not None
            and _process_is_alive(start_record.get("owner_process_id"))
        )
        return {
            "run_id": run_id,
            "status": terminal_status or ("running" if active else "incomplete"),
            "terminal_status": terminal_status,
            "trailing_partial_record": trailing_partial_record,
            "trace_path": str(self.path),
            "events": matches,
        }

    def list_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """List recent run identities without exposing event payloads."""
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer from 1 through 1000")
        if not self.path.exists():
            return []
        summaries: dict[str, dict[str, Any]] = {}
        with self._lock, self._writer_lock():
            try:
                with self.path.open("r", encoding="utf-8") as stream:
                    lines = stream.readlines()
                for line_number, line in enumerate(lines, start=1):
                    if not line.strip() or (line_number == len(lines) and not line.endswith("\n")):
                        continue
                    try:
                        record = _validate_record(json.loads(line), line_number)
                    except json.JSONDecodeError as exc:
                        raise TraceStoreError(
                            f"invalid JSONL at line {line_number}; trace was not changed"
                        ) from exc
                    run_id = record["run_id"]
                    summary = summaries.setdefault(
                        run_id,
                        {
                            "run_id": run_id,
                            "request_id": record.get("request_id"),
                            "request_kind": None,
                            "started_at": None,
                            "last_event_at": None,
                            "last_sequence": -1,
                            "terminal_status": None,
                            "owner_process_id": None,
                        },
                    )
                    summary["last_event_at"] = record["timestamp"]
                    summary["last_sequence"] = record["sequence"]
                    if record["event_type"] == "request.started":
                        summary["request_kind"] = record.get("request_kind")
                        summary["started_at"] = record["timestamp"]
                        summary["owner_process_id"] = record.get("owner_process_id")
                    elif record["event_type"] == "request.terminal":
                        summary["terminal_status"] = record.get("terminal_status")
            except UnicodeDecodeError as exc:
                raise TraceStoreError("trace file is not valid UTF-8; it was not changed") from exc
            except OSError as exc:
                raise TraceStoreError(f"could not read run trace: {type(exc).__name__}") from exc

        runs = list(summaries.values())
        for summary in runs:
            status = summary["terminal_status"]
            if status is None:
                status = (
                    "running"
                    if _process_is_alive(summary.get("owner_process_id"))
                    else "incomplete"
                )
            summary["status"] = status
            summary.pop("owner_process_id", None)
        runs.sort(key=lambda item: (item["last_event_at"] or "", item["last_sequence"]), reverse=True)
        return runs[:limit]
