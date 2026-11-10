"""Explicit, workspace-local DeepSeek connection."""

import base64
import hashlib
import json
import os
import stat
from pathlib import Path

from agent_runtime.providers.deepseek import DeepSeekModelProvider

from .windows_dpapi import WindowsDPAPI


class DesktopConnection:
    max_output_tokens = 2048
    max_requests = 4

    def __init__(self, workspace, *, transport=None, protector=None):
        workspace = Path(workspace).resolve()
        self.path = workspace / ".catalyst" / "workspace-settings" / "deepseek-credential.dpapi.json"
        self.entropy = hashlib.sha256(("catalyst:deepseek:https://api.deepseek.com:" + str(workspace)).encode()).digest()
        self.protector = protector or WindowsDPAPI()
        self.transport = transport
        self.provider = None
        self.verified = False

    @property
    def mode(self):
        if self.provider is None:
            return "UNCONFIGURED"
        return "SCRIPTED_TRANSPORT" if self.transport is not None else "DEEPSEEK_API"

    def _require_safe_path(self):
        for path in (self.path, *self.path.parents):
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("credential_path_link_not_allowed")

    def _available(self):
        try:
            self._require_safe_path()
            return self.protector.supported and self.path.is_file()
        except (ValueError, OSError):
            return False

    def status(self):
        return {
            "can_remember": self.protector.supported,
            "has_saved_key": self._available(),
            "model": "deepseek-v4-flash",
            "model_verified": self.verified,
            "max_requests": self.max_requests,
            "max_output_tokens": self.max_output_tokens,
        }

    def configure(self, data):
        action = data.get("action") if isinstance(data, dict) else None
        if action == "disconnect" and set(data) == {"action"}:
            self.provider = None
            self.verified = False
            return
        if action == "forget" and set(data) == {"action"}:
            self._require_safe_path()
            self.path.unlink(missing_ok=True)
            self.provider = None
            self.verified = False
            return
        if action == "use_saved" and set(data) == {"action"}:
            key = self._load()
        elif action == "connect" and set(data) == {"action", "api_key", "remember"} and type(data["remember"]) is bool:
            key = data["api_key"]
            self._validate_key(key)
            if data["remember"]:
                self._save(key)
        else:
            raise ValueError("invalid_connection_request")
        self.provider = DeepSeekModelProvider(
            api_key=key, model="deepseek-v4-flash", transport=self.transport, output_token_limit=self.max_output_tokens,
        )
        self.verified = False

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, str) or not 8 <= len(key) <= 512 or any(not 33 <= ord(c) <= 126 for c in key):
            raise ValueError("api_key_format_invalid")

    def _save(self, key):
        self._require_safe_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._require_safe_path()
        ciphertext = self.protector.protect(key.encode("ascii"), self.entropy)
        value = {
            "schema": 1, "provider": "deepseek", "endpoint": "https://api.deepseek.com",
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        temporary = self.path.with_suffix(".tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(value, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def _load(self):
        try:
            if not self._available() or self.path.stat().st_size > 16384:
                raise ValueError
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if (set(value) != {"schema", "provider", "endpoint", "ciphertext"} or value["schema"] != 1
                    or value["provider"] != "deepseek" or value["endpoint"] != "https://api.deepseek.com"):
                raise ValueError
            key = self.protector.unprotect(base64.b64decode(value["ciphertext"], validate=True), self.entropy).decode("ascii")
            self._validate_key(key)
            return key
        except (ValueError, OSError, TypeError, KeyError):
            raise ValueError("saved_credential_unavailable") from None
