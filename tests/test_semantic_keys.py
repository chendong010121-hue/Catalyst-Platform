"""The two local signing keys, and the check that refuses anything they did not sign."""

from __future__ import annotations

import os
import stat

import pytest

from catalyst_platform.semantic_keys import (
    ISSUERS,
    ROLES,
    ensure_key,
    key_path,
    load_key,
    sign,
    verifier,
)
from catalyst_platform.semantic_wiki import SemanticTransitionError


def test_ensure_key_lives_under_the_workspace_and_never_overwrites(tmp_path):
    path = ensure_key(tmp_path, "reviewer")
    assert path == tmp_path / ".catalyst" / "keys" / "reviewer.key"
    assert path == key_path(tmp_path, "reviewer")
    assert path.parent.parent.name == ".catalyst"
    secret = path.read_text(encoding="ascii")
    assert len(secret) == 64

    assert ensure_key(tmp_path, "reviewer") == path
    assert path.read_text(encoding="ascii") == secret


def test_a_created_key_is_private(tmp_path):
    path = ensure_key(tmp_path, "owner")
    if os.name != "posix":
        pytest.skip("POSIX mode bits carry the privacy guarantee")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_an_unknown_role_is_refused(tmp_path):
    with pytest.raises(SemanticTransitionError) as caught:
        key_path(tmp_path, "auditor")
    assert caught.value.code == "unknown_key_role"


def test_sign_then_verify_accepts_only_the_signed_fields(tmp_path):
    for role in ROLES:
        ensure_key(tmp_path, role)
    receipt = sign({"receipt_type": "semantic_evaluation", "candidate_id": "cand_1"},
                   role="reviewer", secret=load_key(tmp_path, "reviewer"))
    verify = verifier(tmp_path)

    assert receipt["issuer_id"] == ISSUERS["reviewer"]
    assert verify(receipt) is True
    assert verify({**receipt, "candidate_id": "cand_2"}) is False
    assert verify({**receipt, "signature": "0" * 64}) is False
    assert verify({**receipt, "issuer_id": "somewhere.else"}) is False
    assert verify({name: value for name, value in receipt.items() if name != "signature"}) is False


def test_a_workspace_without_keys_trusts_nothing(tmp_path):
    verify = verifier(tmp_path)
    assert verify({"issuer_id": ISSUERS["owner"], "signature": "0" * 64}) is False


def test_one_role_cannot_sign_for_the_other(tmp_path):
    ensure_key(tmp_path, "reviewer")
    receipt = sign({"receipt_type": "owner_authority"}, role="reviewer",
                   secret=load_key(tmp_path, "reviewer"))
    assert verifier(tmp_path)(receipt) is True
    assert verifier(tmp_path)({**receipt, "issuer_id": ISSUERS["owner"]}) is False


def test_keys_are_not_interchangeable_between_workspaces(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    ensure_key(one, "reviewer")
    ensure_key(two, "reviewer")
    receipt = sign({"receipt_type": "semantic_evaluation"}, role="reviewer", secret=load_key(one, "reviewer"))
    assert verifier(one)(receipt) is True
    assert verifier(two)(receipt) is False
