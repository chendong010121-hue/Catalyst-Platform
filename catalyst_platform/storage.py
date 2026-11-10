"""Small JSON-backed StateStore adapter for local Catalyst sessions.

The codec accepts only JSON values and dataclasses declared by
``agent_runtime.contracts.values``. It never imports a type named by a session
file and never deserializes executable objects.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from agent_runtime.contracts import SessionSnapshot
from agent_runtime.snapshot import validate_session_snapshot
from agent_runtime.contracts import values as contract_values


class StateSerializationError(ValueError):
    """A session contains data outside the supported durable JSON contract."""


_SAFE_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,96}\Z")
_CONTRACT_TYPES = {
    name: item
    for name, item in vars(contract_values).items()
    if isinstance(item, type)
    and item.__module__ == contract_values.__name__
    and dataclasses.is_dataclass(item)
}


def _encode(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, tuple):
        return {"$tuple": [_encode(item) for item in value]}
    if isinstance(value, list):
        return {"$list": [_encode(item) for item in value]}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise StateSerializationError("session maps must use string keys")
        return {"$map": {key: _encode(item) for key, item in value.items()}}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        type_name = type(value).__name__
        if _CONTRACT_TYPES.get(type_name) is not type(value):
            raise StateSerializationError(
                f"unsupported session value type: {type(value).__module__}.{type_name}"
            )
        return {
            "$type": type_name,
            "$fields": {
                field.name: _encode(getattr(value, field.name))
                for field in dataclasses.fields(value)
            },
        }
    raise StateSerializationError(f"unsupported session value type: {type(value).__name__}")


def _decode(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        raise StateSerializationError("unwrapped lists are invalid in a session file")
    if not isinstance(value, dict):
        raise StateSerializationError("invalid session value")
    if set(value) == {"$tuple"} and isinstance(value["$tuple"], list):
        return tuple(_decode(item) for item in value["$tuple"])
    if set(value) == {"$list"} and isinstance(value["$list"], list):
        return [_decode(item) for item in value["$list"]]
    if set(value) == {"$map"} and isinstance(value["$map"], dict):
        return {key: _decode(item) for key, item in value["$map"].items()}
    if set(value) == {"$type", "$fields"}:
        type_name = value["$type"]
        fields = value["$fields"]
        cls = _CONTRACT_TYPES.get(type_name)
        if cls is None or not isinstance(fields, dict):
            raise StateSerializationError("unknown or malformed contract value")
        return cls(**{key: _decode(item) for key, item in fields.items()})
    raise StateSerializationError("unknown tagged value in session file")


_LONG_PATH_PREFIX = "\\\\?\\"


def _os_path(path: Path) -> str:
    """The path as Windows must receive it to open past its 260-character limit.

    A session file sits at whatever depth its workspace chose (a platform evaluation
    case is five directories deep already), and the temporary file adds another 40
    characters, so the readable layout can outrun ``MAX_PATH``. The extended-length
    form lifts that limit and changes nothing on disk; every other platform, and every
    short path, gets the plain path. The Wiki store carries the same helper.
    """
    text = os.fspath(path)
    if os.name != "nt" or len(text) < 240 or text.startswith(_LONG_PATH_PREFIX):
        return text
    resolved = os.fspath(path.resolve())
    return resolved if resolved.startswith(_LONG_PATH_PREFIX) else _LONG_PATH_PREFIX + resolved


class JsonFileStateStore:
    """Atomic per-session StateStore using a restricted JSON value codec."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory).resolve()
        self._lock = threading.RLock()

    def _path(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not _SAFE_SESSION_ID.fullmatch(session_id):
            raise ValueError("session_id contains unsupported path characters")
        return self.directory / f"{session_id}.json"

    def load(self, session_id: str) -> SessionSnapshot:
        path = self._path(session_id)
        with self._lock:
            with open(_os_path(path), encoding="utf-8") as stream:
                raw = json.loads(stream.read())
            if not isinstance(raw, dict) or raw.get("store_version") != 1:
                raise StateSerializationError("unsupported session store version")
            snapshot = _decode(raw.get("snapshot"))
            return validate_session_snapshot(snapshot, expected_session_id=session_id)

    def commit(self, snapshot: SessionSnapshot) -> None:
        canonical = validate_session_snapshot(snapshot)
        path = self._path(canonical.session_id)
        payload = json.dumps(
            {"store_version": 1, "snapshot": _encode(canonical)},
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            temporary = self.directory / f".{canonical.session_id}.{uuid.uuid4().hex}.tmp"
            try:
                with open(_os_path(temporary), "x", encoding="utf-8", newline="\n") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(_os_path(temporary), _os_path(path))
            finally:
                try:
                    os.unlink(_os_path(temporary))
                except OSError:
                    pass
