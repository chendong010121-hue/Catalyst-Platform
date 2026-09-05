from __future__ import annotations

import pytest

from agent_runtime.contracts import (
    Failure,
    NativeToolsV2Call,
    SourceIdentity,
    SourceObservationProvenance,
    Success,
)
from agent_runtime.native_tools_v2 import _tool_result_text
from agent_runtime.snapshot import snapshot_observation
from agent_runtime.source_provenance import SourceObservationLedger


def test_successful_source_observation_produces_machine_derived_provenance():
    ledger = SourceObservationLedger(SourceIdentity("waku", "rev-1"))

    observation = ledger.observe("src/main.py", lambda: {"ok": True})

    assert isinstance(observation, Success)
    assert isinstance(observation.provenance, SourceObservationProvenance)
    assert observation.provenance.source_id == "waku"
    assert observation.provenance.source_revision == "rev-1"
    assert observation.provenance.locator == "src/main.py"


def test_unobserved_locator_cannot_be_projected_as_observed_evidence():
    ledger = SourceObservationLedger(SourceIdentity("waku", "rev-1"))
    ledger.observe("src/main.py", lambda: {"ok": True})

    with pytest.raises(KeyError):
        ledger.provenance_for("src/secret.py")


def test_observation_provenance_keeps_the_ledger_source_identity():
    identity = SourceIdentity("waku", "rev-1")
    ledger = SourceObservationLedger(identity)
    observation = ledger.observe("src/main.py", lambda: "source")

    assert ledger.source_identity == identity
    assert observation.provenance.source_id == identity.source_id
    assert observation.provenance.source_revision == identity.revision


def test_failed_source_observation_does_not_enter_the_ledger():
    ledger = SourceObservationLedger(SourceIdentity("waku", "rev-1"))

    result = ledger.observe("src/missing.py", lambda: Failure("not found"))

    assert result == Failure("not found")
    with pytest.raises(KeyError):
        ledger.provenance_for("src/missing.py")


def test_model_visible_tool_context_carries_admitted_provenance():
    ledger = SourceObservationLedger(SourceIdentity("waku", "rev-1"))
    observation = ledger.observe("src/main.py", lambda: {"ok": True})
    call = NativeToolsV2Call(
        tool_call_id="call-1",
        name="inspect",
        arguments="{}",
        status="settled",
        execution_id="execution-1",
        observation=observation,
    )

    rendered = _tool_result_text(call)

    assert '"ok": true' in rendered
    assert '"source_id": "waku"' in rendered
    assert '"source_revision": "rev-1"' in rendered
    assert '"locator": "src/main.py"' in rendered


def test_snapshot_preserves_durable_source_provenance():
    ledger = SourceObservationLedger(SourceIdentity("waku", "rev-1"))
    observation = ledger.observe("src/main.py", lambda: {"ok": True})

    snapshotted = snapshot_observation(observation)

    assert snapshotted == observation
    assert snapshotted is not observation


def test_observations_without_provenance_keep_existing_tool_result_shape():
    call = NativeToolsV2Call(
        tool_call_id="call-1",
        name="inspect",
        arguments="{}",
        status="settled",
        execution_id="execution-1",
        observation=Success(42),
    )

    assert _tool_result_text(call) == "42"
