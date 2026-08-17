"""Platform Standard Core v0.1 — acceptance tests PS-1 .. PS-14.

Run:  python tests/test_platform_standard_core.py
(from the repository root; the file inserts the repo root on sys.path).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runtime.contracts import CapabilityDescriptor as RuntimeCapabilityDescriptor

from examples.platform_standard_reference import (
    ComposeReportCapability,
    CountWordsCapability,
    compose_report_descriptor,
    count_words_descriptor,
    make_report_invocation,
    make_stack,
)
from platform_standard.extensions import Extension
from platform_standard.models import (
    ArtifactRef,
    CapabilityDescriptor,
    Invocation,
    Producer,
    Result,
    TraceEvent,
)
from platform_standard.registry import (
    DuplicateDescriptorError,
    InMemoryDescriptorRegistry,
)
from platform_standard.runtime_adapter import RuntimeAdapter
from platform_standard.validation import PlatformValidator, ValidationError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _assert_raises_validation_error(fn):
    try:
        fn()
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")


# ---------------------------------------------------------------------------
# PS-1 / PS-2 Capability contract
# ---------------------------------------------------------------------------

def test_ps1_valid_capability_accepted():
    PlatformValidator().validate_capability(compose_report_descriptor())
    PlatformValidator().validate_capability(count_words_descriptor())


def test_ps2_malformed_capability_rejected():
    v = PlatformValidator()
    # empty name -> reject
    _assert_raises_validation_error(
        lambda: v.validate_capability(
            CapabilityDescriptor(
                id="x", name="", description="d", capability_version="1.0.0",
                input_schema={}, output_schema={}, execution={"side_effect": "none"},
            )
        )
    )
    # missing execution.side_effect -> reject
    _assert_raises_validation_error(
        lambda: v.validate_capability(
            CapabilityDescriptor(
                id="y", name="N", description="d", capability_version="1.0.0",
                input_schema={}, output_schema={}, execution={},
            )
        )
    )
    # invalid side_effect -> reject
    _assert_raises_validation_error(
        lambda: v.validate_capability(
            CapabilityDescriptor(
                id="z", name="N", description="d", capability_version="1.0.0",
                input_schema={}, output_schema={}, execution={"side_effect": "always"},
            )
        )
    )
    # missing id -> reject
    _assert_raises_validation_error(
        lambda: v.validate_capability(
            CapabilityDescriptor(
                id="", name="N", description="d", capability_version="1.0.0",
                input_schema={}, output_schema={}, execution={"side_effect": "none"},
            )
        )
    )


# ---------------------------------------------------------------------------
# PS-3 / PS-4 / PS-5 Invocation + Extension
# ---------------------------------------------------------------------------

def test_ps3_valid_invocation_accepted():
    inv = Invocation(
        id="inv_1", capability_id="compose_report", capability_version="1.0.0",
        input={"title": "T"}, context={"extensions": {}}, trace_id="tr_1",
    )
    PlatformValidator().validate_invocation(inv)


def test_ps4_unknown_required_extension_rejected():
    inv = Invocation(
        id="inv_2", capability_id="compose_report", capability_version="1.0.0",
        input={}, context={"extensions": {}}, trace_id="tr_2",
        extensions={"enterprise.identity": {"version": "1", "required": True, "payload": {"user_ref": "u1"}}},
    )
    _assert_raises_validation_error(lambda: PlatformValidator().validate_invocation(inv))


def test_ps5_unknown_optional_extension_preserved():
    ext = {"enterprise.identity": {"version": "1", "required": False, "payload": {"user_ref": "u1"}}}
    inv = Invocation(
        id="inv_3", capability_id="compose_report", capability_version="1.0.0",
        input={}, context={"extensions": {}}, trace_id="tr_3", extensions=ext,
    )
    PlatformValidator().validate_invocation(inv)  # no error
    assert inv.extensions == ext  # preserved unchanged


# ---------------------------------------------------------------------------
# PS-6 / PS-7 / PS-8 Result contract
# ---------------------------------------------------------------------------

def test_ps6_success_result_validates():
    r = Result(id="r1", invocation_id="inv_1", status="success", output={"ok": True}, artifacts=(), error=None)
    PlatformValidator().validate_result(r)


def test_ps7_failure_result_validates():
    r = Result(id="r1", invocation_id="inv_1", status="failure", output=None, artifacts=(), error={"code": "capability_failed", "message": "boom"})
    PlatformValidator().validate_result(r)


def test_ps8_unresolved_result_implies_no_safe_retry():
    r = Result(
        id="r1", invocation_id="inv_1", status="unresolved", output=None, artifacts=(),
        error={"code": "runtime_outcome_uncertain", "message": "outcome unknown"},
    )
    PlatformValidator().validate_result(r)
    data = r.to_dict()
    assert "safe_to_retry" not in data
    assert "did_not_execute" not in data
    # unresolved must not be success with null error
    _assert_raises_validation_error(
        lambda: PlatformValidator().validate_result(
            Result(id="r2", invocation_id="inv_1", status="unresolved", output=None, artifacts=(), error=None)
        )
    )


# ---------------------------------------------------------------------------
# PS-9 ArtifactRef / PS-10 Trace Event
# ---------------------------------------------------------------------------

def test_ps9_artifact_ref_validates():
    a = ArtifactRef(
        id="a1", artifact_type="report", artifact_version="1", uri="file:///outputs/report.md",
        producer=Producer(capability_id="compose_report", invocation_id="inv_1"),
    )
    PlatformValidator().validate_artifact_ref(a)
    # missing producer -> reject
    _assert_raises_validation_error(
        lambda: PlatformValidator().validate_artifact_ref(
            ArtifactRef(id="a2", artifact_type="report", artifact_version="1", uri="u", producer=Producer())
        )
    )


def test_ps10_trace_event_validates():
    e = TraceEvent(
        id="e1", trace_id="tr_1", event_type="invocation.completed",
        timestamp="2026-08-17T10:00:00Z", subject_id="inv_1",
    )
    PlatformValidator().validate_trace_event(e)
    _assert_raises_validation_error(
        lambda: PlatformValidator().validate_trace_event(
            TraceEvent(id="e2", trace_id="tr_1", event_type="unknown.type", timestamp="t", subject_id="s")
        )
    )


# ---------------------------------------------------------------------------
# PS-11 registry duplicate
# ---------------------------------------------------------------------------

def test_ps11_duplicate_descriptor_rejected():
    reg = InMemoryDescriptorRegistry()
    reg.register(compose_report_descriptor())
    try:
        reg.register(compose_report_descriptor())
    except DuplicateDescriptorError:
        pass
    else:
        raise AssertionError("duplicate (id, version) must be rejected")
    assert len(reg.list()) == 1


# ---------------------------------------------------------------------------
# PS-12 vertical slice
# ---------------------------------------------------------------------------

def test_ps12_vertical_slice_passes():
    registry, adapter = make_stack()
    validator = PlatformValidator()
    invocation = make_report_invocation(
        {"title": "T", "sections": ["S1", "S2"]},
        invocation_id="inv_vs", trace_id="tr_vs",
    )
    result = adapter.execute(invocation)

    assert result.status == "success"
    assert result.output["report_text"].startswith("# T")
    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.artifact_type == "report"
    assert artifact.uri.startswith("file:///outputs/report_T.md")
    assert artifact.producer.capability_id == "compose_report"
    assert artifact.producer.invocation_id == "inv_vs"

    # all Standard objects validate
    validator.validate_result(result)
    validator.validate_artifact_ref(artifact)
    event_types = [e.event_type for e in adapter.trace_events()]
    assert "invocation.started" in event_types
    assert "invocation.completed" in event_types
    assert "artifact.created" in event_types
    for e in adapter.trace_events():
        validator.validate_trace_event(e)
    assert registry.get("compose_report", "1.0.0") is not None


# ---------------------------------------------------------------------------
# PS-13 second Capability portability (no Core/Runtime/AgentCore change)
# ---------------------------------------------------------------------------

def test_ps13_second_capability_portable():
    registry = InMemoryDescriptorRegistry()
    registry.register(compose_report_descriptor())
    registry.register(count_words_descriptor())
    adapter = RuntimeAdapter(
        registry,
        bindings={
            ("compose_report", "1.0.0"): ComposeReportCapability(),
            ("count_words", "1.0.0"): CountWordsCapability(),
        },
    )
    validator = PlatformValidator()

    inv = Invocation(
        id="inv_cw", capability_id="count_words", capability_version="1.0.0",
        input={"text": "alpha beta gamma"}, context={"extensions": {}}, trace_id="tr_cw",
    )
    result = adapter.execute(inv)
    assert result.status == "success"
    assert result.output == {"word_count": 3}
    assert result.artifacts == ()  # a capability MAY return zero artifacts
    validator.validate_result(result)
    # first capability still works on the same stack
    first = adapter.execute(make_report_invocation({"title": "X", "sections": []}, invocation_id="inv_r", trace_id="tr_r"))
    assert first.status == "success"
    assert len(first.artifacts) == 1


# ---------------------------------------------------------------------------
# PS-14 uncertain Runtime outcome -> unresolved
# ---------------------------------------------------------------------------

class RaisingCapability:
    """Raises after a possible side effect: execution certainty is not closed."""

    def describe(self):
        return RuntimeCapabilityDescriptor(
            id="boom", name="Boom", description="raises after possible side effect",
            input_schema={"type": "object"}, output_schema={},
        )

    def invoke(self, parameters, context):
        raise RuntimeError("boom after possible side effect")


def test_ps14_uncertain_runtime_outcome_maps_to_unresolved():
    registry = InMemoryDescriptorRegistry()
    registry.register(
        CapabilityDescriptor(
            id="boom", name="Boom", description="raises", capability_version="1.0.0",
            input_schema={"type": "object"}, output_schema={"type": "object"},
            execution={"side_effect": "possible"},
        )
    )
    adapter = RuntimeAdapter(registry, {("boom", "1.0.0"): RaisingCapability()})
    inv = Invocation(
        id="inv_b", capability_id="boom", capability_version="1.0.0",
        input={}, context={"extensions": {}}, trace_id="tr_b",
    )
    result = adapter.execute(inv)
    assert result.status == "unresolved"
    assert result.error is not None
    assert result.error["code"] == "runtime_outcome_uncertain"
    data = result.to_dict()
    assert "safe_to_retry" not in data
    assert "did_not_execute" not in data
    PlatformValidator().validate_result(result)
    event_types = [e.event_type for e in adapter.trace_events()]
    assert "invocation.started" in event_types
    assert "invocation.unresolved" in event_types


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        ("PS-1 valid Capability accepted", test_ps1_valid_capability_accepted),
        ("PS-2 malformed Capability rejected", test_ps2_malformed_capability_rejected),
        ("PS-3 valid Invocation accepted", test_ps3_valid_invocation_accepted),
        ("PS-4 unknown required Extension rejected", test_ps4_unknown_required_extension_rejected),
        ("PS-5 unknown optional Extension preserved", test_ps5_unknown_optional_extension_preserved),
        ("PS-6 success Result validates", test_ps6_success_result_validates),
        ("PS-7 failure Result validates", test_ps7_failure_result_validates),
        ("PS-8 unresolved implies no safe retry", test_ps8_unresolved_result_implies_no_safe_retry),
        ("PS-9 ArtifactRef validates", test_ps9_artifact_ref_validates),
        ("PS-10 Trace Event validates", test_ps10_trace_event_validates),
        ("PS-11 duplicate descriptor rejected", test_ps11_duplicate_descriptor_rejected),
        ("PS-12 vertical slice passes", test_ps12_vertical_slice_passes),
        ("PS-13 second Capability portable", test_ps13_second_capability_portable),
        ("PS-14 uncertain outcome -> unresolved", test_ps14_uncertain_runtime_outcome_maps_to_unresolved),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except AssertionError as exc:
            failed.append(name)
            print(f"FAILED: {name} -> {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"ERROR : {name} -> {type(exc).__name__}: {exc}")

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        raise SystemExit(1)
    print("\nALL PLATFORM STANDARD CORE v0.1 TESTS PASSED (PS-1..PS-14)")


if __name__ == "__main__":
    main()
