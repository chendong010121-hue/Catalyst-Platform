"""Enterprise Extension Pilot v0.1 — acceptance tests EE-1 .. EE-12.

Run:  python tests/test_enterprise_extension_pilot.py
(from the repository root; the file inserts the repo root on sys.path).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enterprise_extensions.identity import (
    EnterpriseIdentity,
    EnterpriseIdentityError,
    attribute_trace,
    execute_with_enterprise_identity,
    parse_enterprise_identity,
)
from examples.platform_standard_reference import make_stack
from platform_standard.models import Invocation, TraceEvent
from platform_standard.validation import PlatformValidator

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _invocation_with_identity(identity_payload, *, extra_extensions=None):
    extensions = {}
    if identity_payload is not None:
        extensions["enterprise.identity"] = {
            "version": "0.1",
            "required": False,
            "payload": identity_payload,
        }
    if extra_extensions:
        extensions.update(extra_extensions)
    return Invocation(
        id="inv_e",
        capability_id="compose_report",
        capability_version="1.0.0",
        input={"title": "T", "sections": ["S"]},
        context={"extensions": {}},
        extensions=extensions,
        trace_id="tr_e",
    )


def _run_identity_case(identity: EnterpriseIdentity):
    """Full reference path via the unified handler."""
    registry, adapter = make_stack()
    invocation = _invocation_with_identity(identity.to_extension()["enterprise.identity"]["payload"])
    result, events = execute_with_enterprise_identity(adapter, invocation)
    return result, events


# ---------------------------------------------------------------------------
# EE-1 .. EE-4 payload validation
# ---------------------------------------------------------------------------

def test_ee1_valid_enterprise_identity_accepted():
    identity = parse_enterprise_identity(
        _invocation_with_identity({"organization_id": "org_alpha", "user_id": "user_001", "project_id": "project_a"})
    )
    assert identity == EnterpriseIdentity("org_alpha", "user_001", "project_a")


def test_ee2_missing_organization_id_rejected():
    try:
        parse_enterprise_identity(_invocation_with_identity({"user_id": "user_001"}))
    except EnterpriseIdentityError:
        pass
    else:
        raise AssertionError("missing organization_id must be rejected")


def test_ee3_missing_user_id_rejected():
    try:
        parse_enterprise_identity(_invocation_with_identity({"organization_id": "org_alpha"}))
    except EnterpriseIdentityError:
        pass
    else:
        raise AssertionError("missing user_id must be rejected")


def test_ee4_invalid_optional_project_id_rejected():
    try:
        parse_enterprise_identity(
            _invocation_with_identity({"organization_id": "org_alpha", "user_id": "u1", "project_id": ""})
        )
    except EnterpriseIdentityError:
        pass
    else:
        raise AssertionError("empty project_id must be rejected")
    try:
        parse_enterprise_identity(
            _invocation_with_identity({"organization_id": "org_alpha", "user_id": "u1", "project_id": 123})
        )
    except EnterpriseIdentityError:
        pass
    else:
        raise AssertionError("non-string project_id must be rejected")


# ---------------------------------------------------------------------------
# EE-5 / EE-6 preservation + trace attribution
# ---------------------------------------------------------------------------

def test_ee5_identity_preserved_through_reference_path():
    identity = EnterpriseIdentity("org_alpha", "user_001", "project_a")
    registry, adapter = make_stack()
    invocation = _invocation_with_identity(identity.to_extension()["enterprise.identity"]["payload"])
    # original identity parsed from the Invocation BEFORE execution
    original = parse_enterprise_identity(invocation)
    result, events = execute_with_enterprise_identity(adapter, invocation)
    # 1. Invocation identity not lost / not changed
    assert parse_enterprise_identity(invocation) == original == identity
    # 2. Result returned normally
    assert result.status == "success"
    assert result.output["report_text"].startswith("# T")
    # 3. returned attributed Trace contains the same identity
    assert events
    for event in events:
        ext = event.extensions["enterprise.identity"]
        assert ext["version"] == "0.1"
        assert ext["payload"] == {
            "organization_id": "org_alpha",
            "user_id": "user_001",
            "project_id": "project_a",
        }


def test_ee6_identity_visible_in_trace_attribution():
    identity = EnterpriseIdentity("org_beta", "user_927", "project_z")
    _result, events = _run_identity_case(identity)
    assert events
    for event in events:
        ext = event.extensions.get("enterprise.identity")
        assert ext is not None
        assert ext["payload"]["organization_id"] == "org_beta"
        assert ext["payload"]["user_id"] == "user_927"
        assert ext["payload"]["project_id"] == "project_z"


# ---------------------------------------------------------------------------
# EE-7 / EE-8 Org A / Org B execute correctly
# ---------------------------------------------------------------------------

def test_ee7_org_a_executes_correctly():
    identity = EnterpriseIdentity("org_alpha", "user_001", "project_a")
    result, _ = _run_identity_case(identity)
    assert result.status == "success"
    assert len(result.artifacts) == 1


def test_ee8_org_b_executes_correctly():
    identity = EnterpriseIdentity("org_beta", "user_927", "project_z")
    result, events = _run_identity_case(identity)
    assert result.status == "success"
    # attribution matches Org B
    payload = events[0].extensions["enterprise.identity"]["payload"]
    assert payload == {"organization_id": "org_beta", "user_id": "user_927", "project_id": "project_z"}


# ---------------------------------------------------------------------------
# EE-9 switching identity changes no Core schema
# ---------------------------------------------------------------------------

def test_ee9_switching_identity_no_core_schema_change():
    models_path = os.path.join(_REPO_ROOT, "platform_standard", "models.py")
    content = open(models_path, encoding="utf-8").read()
    assert "organization_id" not in content
    assert "user_id" not in content
    assert "project_id" not in content
    # functional: both Org A and Org B use the same Core / Adapter / Runtime
    test_ee7_org_a_executes_correctly()
    test_ee8_org_b_executes_correctly()


# ---------------------------------------------------------------------------
# EE-10 unknown optional enterprise extension preserves Core behavior
# ---------------------------------------------------------------------------

def test_ee10_unknown_optional_extension_preserves_core_behavior():
    invocation = _invocation_with_identity(
        None,
        extra_extensions={
            "enterprise.unknown_future_extension": {
                "version": "1",
                "required": False,
                "payload": {"some_future_meaning": True},
            }
        },
    )
    validator = PlatformValidator()
    validator.validate_invocation(invocation)  # Core accepts optional unknown
    assert parse_enterprise_identity(invocation) is None  # no identity -> no error
    registry, adapter = make_stack()
    result, events = execute_with_enterprise_identity(adapter, invocation)
    assert result.status == "success"
    # no identity -> no attribution injected
    assert all("enterprise.identity" not in e.extensions for e in events)
    # unknown extension preserved unchanged
    assert invocation.extensions["enterprise.unknown_future_extension"]["payload"]["some_future_meaning"] is True


# ---------------------------------------------------------------------------
# EE-11 agent_runtime /** ZERO DIFF (structural proxy)
# ---------------------------------------------------------------------------

def test_ee11_enterprise_layer_does_not_import_agent_runtime():
    pkg = os.path.join(_REPO_ROOT, "enterprise_extensions")
    for name in os.listdir(pkg):
        if not name.endswith(".py"):
            continue
        content = open(os.path.join(pkg, name), encoding="utf-8").read()
        assert "from agent_runtime" not in content and "import agent_runtime" not in content, name


# ---------------------------------------------------------------------------
# EE-12 existing PS-1..PS-14 + AR-1..AR-7 regression PASS
# ---------------------------------------------------------------------------

def test_ee12_ps_ar_regression_passes():
    import tests.test_platform_standard_core as ps

    ps.main()  # runs PS-1..PS-14 + AR-1..AR-7; raises SystemExit(1) on failure


# ---------------------------------------------------------------------------
# ER-1 .. ER-5 audit-repair regressions
# ---------------------------------------------------------------------------

def test_er1_supported_identity_version_accepted():
    identity = parse_enterprise_identity(
        _invocation_with_identity({"organization_id": "org_alpha", "user_id": "user_001"})
    )
    assert identity == EnterpriseIdentity("org_alpha", "user_001")


def test_er2_unsupported_identity_version_rejected():
    for version in ("0.2", "999"):
        invocation = Invocation(
            id="inv_v", capability_id="compose_report", capability_version="1.0.0",
            input={"title": "T", "sections": []}, context={"extensions": {}},
            extensions={"enterprise.identity": {"version": version, "required": False,
                                                "payload": {"organization_id": "o", "user_id": "u"}}},
            trace_id="tr_v",
        )
        try:
            parse_enterprise_identity(invocation)
        except EnterpriseIdentityError:
            pass
        else:
            raise AssertionError(f"version {version!r} must be rejected (only '0.1' supported)")


def test_er3_reference_handler_preserves_identity_end_to_end():
    identity = EnterpriseIdentity("org_beta", "user_927", "project_z")
    registry, adapter = make_stack()
    invocation = _invocation_with_identity(identity.to_extension()["enterprise.identity"]["payload"])
    result, events = execute_with_enterprise_identity(adapter, invocation)
    assert result.status == "success"
    assert parse_enterprise_identity(invocation) == identity
    assert events
    for event in events:
        ext = event.extensions["enterprise.identity"]
        assert ext["payload"]["organization_id"] == "org_beta"
        assert ext["payload"]["user_id"] == "user_927"


def test_er4_identical_trace_identity_accepted():
    identity = EnterpriseIdentity("org_alpha", "user_001")
    base = TraceEvent(id="e1", trace_id="t", event_type="invocation.completed", timestamp="x", subject_id="s")
    attributed = attribute_trace((base,), identity)
    assert len(attributed) == 1
    assert attributed[0].extensions["enterprise.identity"]["payload"]["organization_id"] == "org_alpha"
    # identical pre-existing identity -> preserved unchanged, no error
    pre = TraceEvent(id="e2", trace_id="t", event_type="invocation.started", timestamp="x", subject_id="s",
                     extensions=dict(identity.to_extension()))
    attributed2 = attribute_trace((pre,), identity)
    assert attributed2[0] is pre


def test_er5_conflicting_trace_identity_rejected():
    identity = EnterpriseIdentity("org_alpha", "user_001")
    other = EnterpriseIdentity("org_beta", "user_927")
    pre = TraceEvent(id="e3", trace_id="t", event_type="invocation.started", timestamp="x", subject_id="s",
                     extensions=dict(other.to_extension()))
    try:
        attribute_trace((pre,), identity)
    except EnterpriseIdentityError:
        pass
    else:
        raise AssertionError("conflicting trace identity must fail closed")


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [
        ("EE-1 valid enterprise.identity accepted", test_ee1_valid_enterprise_identity_accepted),
        ("EE-2 missing organization_id rejected", test_ee2_missing_organization_id_rejected),
        ("EE-3 missing user_id rejected", test_ee3_missing_user_id_rejected),
        ("EE-4 invalid optional project_id rejected", test_ee4_invalid_optional_project_id_rejected),
        ("EE-5 identity preserved through reference path", test_ee5_identity_preserved_through_reference_path),
        ("EE-6 identity visible in trace attribution", test_ee6_identity_visible_in_trace_attribution),
        ("EE-7 Org A executes correctly", test_ee7_org_a_executes_correctly),
        ("EE-8 Org B executes correctly", test_ee8_org_b_executes_correctly),
        ("EE-9 switching identity no Core schema change", test_ee9_switching_identity_no_core_schema_change),
        ("EE-10 unknown optional extension preserved", test_ee10_unknown_optional_extension_preserves_core_behavior),
        ("EE-11 no agent_runtime import in enterprise layer", test_ee11_enterprise_layer_does_not_import_agent_runtime),
        ("EE-12 PS+AR regression PASS", test_ee12_ps_ar_regression_passes),
        ("ER-1 supported identity version accepted", test_er1_supported_identity_version_accepted),
        ("ER-2 unsupported identity version rejected", test_er2_unsupported_identity_version_rejected),
        ("ER-3 reference handler preserves identity end-to-end", test_er3_reference_handler_preserves_identity_end_to_end),
        ("ER-4 identical trace identity accepted", test_er4_identical_trace_identity_accepted),
        ("ER-5 conflicting trace identity rejected", test_er5_conflicting_trace_identity_rejected),
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
    print("\nALL ENTERPRISE EXTENSION PILOT TESTS PASSED (EE-1..EE-12 + ER-1..ER-5)")


if __name__ == "__main__":
    main()
