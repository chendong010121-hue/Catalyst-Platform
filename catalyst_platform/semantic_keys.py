"""Local signing keys for the two roles a semantic transition needs.

A review recommends and an owner authorizes: the store checks a signature on both, but
until now only a test fixture could produce one, so no product path could accept a
candidate. Each role gets its own secret under ``<workspace>/.catalyst/keys/``; a
verifier built from those files is what every host now hands to ``SemanticWiki``.

Symmetric keys are enough while both roles run on this machine. If the reviewer ever
becomes a third party, the receipt shape stays and the signature becomes asymmetric.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Callable, Mapping

from .semantic_wiki import SemanticTransitionError

KEY_DIRECTORY = Path(".catalyst") / "keys"
ROLES = ("reviewer", "owner")
ISSUERS = {"reviewer": "local.reviewer", "owner": "local.owner"}


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def key_path(workspace, role: str) -> Path:
    if role not in ROLES:
        raise SemanticTransitionError("unknown_key_role", f"no signing role is named {role!r}")
    return Path(workspace) / KEY_DIRECTORY / f"{role}.key"


def ensure_key(workspace, role: str) -> Path:
    """Create the role's key if it is missing, and never overwrite one that exists."""
    path = key_path(workspace, role)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="ascii")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path


def load_key(workspace, role: str) -> bytes | None:
    path = key_path(workspace, role)
    if not path.is_file():
        return None
    return path.read_text(encoding="ascii").strip().encode("ascii")


def sign(fields: Mapping, *, role: str, secret: bytes) -> dict:
    receipt = {**fields, "issuer_id": ISSUERS[role]}
    receipt["signature"] = hmac.new(secret, _canonical(receipt), hashlib.sha256).hexdigest()
    return receipt


def verifier(workspace) -> Callable[[Mapping], bool]:
    """The check a host installs: the receipt names a local issuer and signs its own fields."""
    keys = {issuer: load_key(workspace, role) for role, issuer in ISSUERS.items()}

    def verify(receipt) -> bool:
        issuer = receipt.get("issuer_id") if isinstance(receipt, Mapping) else None
        secret = keys.get(issuer)
        if not secret:
            return False
        unsigned = {name: value for name, value in receipt.items() if name != "signature"}
        expected = hmac.new(secret, _canonical(unsigned), hashlib.sha256).hexdigest()
        return hmac.compare_digest(str(receipt.get("signature", "")), expected)

    return verify
