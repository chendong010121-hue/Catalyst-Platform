"""Capability lifecycle projection: one vocabulary over three existing owners."""
import copy
import pytest

from catalyst_platform import capability_state as cs


def component_row(*versions, active=None):
    return {
        "component_id": "project-understand",
        "resource_type": "method_data",
        "active_version": active,
        "versions": [dict(item, admitted=True) for item in versions],
    }


def version(version_id, **extra):
    return {
        "version": version_id,
        "capability_id": "understand",
        "capability_version": "1.0.0",
        "package_sha256": "a" * 64,
        "manifest_sha256": "b" * 64,
        "source_sha256": "c" * 64,
        **extra,
    }


def semantic_state(*, candidates=None, accepted=None, active=None):
    return {
        "schema_version": 1,
        "candidates": {k: dict(v) for k, v in (candidates or {}).items()},
        "evaluations": {},
        "decisions": {},
        "accepted_versions": {k: dict(v) for k, v in (accepted or {}).items()},
        "active_version_id": active,
        "transitions": [],
    }


def test_active_component_version_projects_active_with_digests():
    rows = [component_row(version("1.0.0"), active="1.0.0")]
    (projection,) = cs.project_components(rows)
    assert projection.state == cs.ACTIVE
    assert projection.subject == "project-understand@1.0.0"
    assert {item.kind for item in projection.evidence} == {"component_version", "package_sha256", "manifest_sha256", "source_sha256"}


def test_admitted_but_inactive_component_version_is_not_active():
    rows = [component_row(version("1.0.0"), active="2.0.0")]
    (projection,) = cs.project_components(rows)
    assert projection.state == cs.ADMITTED


def test_list_components_shape_with_per_version_active_flag_is_supported():
    """``list_components`` reports activation per version, not only as a pointer."""
    rows = [{
        "component_id": "project-understand",
        "active_version": "1.0.0",
        "versions": [dict(version("1.0.0"), admitted=True, active=True)],
    }]
    (projection,) = cs.project_components(rows)
    assert projection.state == cs.ACTIVE


def test_component_version_without_admission_is_unknown_not_active():
    rows = [{"component_id": "x", "versions": [{"version": "1.0.0", "active": True}]}]
    (projection,) = cs.project_components(rows)
    assert projection.state == cs.UNKNOWN
    assert projection.reason == "version is not admitted"


def test_component_load_failure_stays_admitted_and_says_why():
    rows = [component_row(version("1.0.0", load_error_type="ImportError"), active="1.0.0")]
    (projection,) = cs.project_components(rows)
    assert projection.state == cs.ADMITTED
    assert projection.reason == "module_load_failed:ImportError"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("PROPOSED", cs.PROPOSED),
        ("EVALUATED", cs.EVALUATED),
        ("NEEDS_REVIEW", cs.NEEDS_REVIEW),
        ("ACCEPTED", cs.ADMITTED),
        ("REJECTED", cs.REJECTED),
        ("DEFERRED", cs.NEEDS_REVIEW),
    ],
)
def test_semantic_candidate_status_mapping(status, expected):
    projection = cs.project_semantic_candidate("candidate-1", {"status": status, "source_id": "s", "source_revision": "r1"})
    assert projection.state == expected
    assert projection.raw_state == status


def test_unknown_candidate_status_is_unknown():
    projection = cs.project_semantic_candidate("candidate-1", {"status": "ARCHIVED"})
    assert projection.state == cs.UNKNOWN
    assert "outside the known vocabulary" in projection.reason


def test_semantic_version_active_and_accepted_are_distinguished():
    state = semantic_state(accepted={"v1": {"decision_id": "d1"}, "v2": {"decision_id": "d2"}}, active="v2")
    first = cs.project_semantic_version("v1", state)
    second = cs.project_semantic_version("v2", state)
    assert (first.state, first.reason) == (cs.ADMITTED, "accepted_but_not_active")
    assert second.state == cs.ACTIVE


def test_missing_semantic_version_is_unknown():
    projection = cs.project_semantic_version("nope", semantic_state())
    assert projection.state == cs.UNKNOWN


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("VALIDATED", cs.EVALUATED),
        ("PENDING_RESTART", cs.ADMITTED),
        ("APPLYING", cs.ADMITTED),
        ("ROLLBACK_PENDING", cs.ACTIVE),
        ("APPLIED", cs.ACTIVE),
        ("ROLLED_BACK", cs.DEPRECATED),
        ("VALIDATION_FAILED", cs.REJECTED),
        ("REJECTED", cs.REJECTED),
        ("FAILED", cs.REJECTED),
        ("FAILED_ROLLED_BACK", cs.REJECTED),
        ("RECOVERY_REQUIRED", cs.NEEDS_REVIEW),
    ],
)
def test_maintenance_status_mapping(status, expected):
    projection = cs.project_maintenance({"review_id": "r-1", "status": status, "confirmed_by": "LOCAL_WORKSPACE_USER"})
    assert projection.state == expected
    assert projection.raw_state == status


def test_unknown_maintenance_status_is_unknown():
    projection = cs.project_maintenance({"review_id": "r-1", "status": "SOMETHING_NEW"})
    assert projection.state == cs.UNKNOWN


def test_no_current_owner_can_produce_retired():
    """Today nothing records a retirement decision; that gap is reported, not invented."""
    projections = cs.project_snapshot(
        components=[component_row(version("1.0.0"), active="1.0.0")],
        semantic_state=semantic_state(
            candidates={"c1": {"status": "ACCEPTED"}, "c2": {"status": "REJECTED"}},
            accepted={"v1": {"decision_id": "d1"}},
            active="v1",
        ),
        maintenance=[{"review_id": "r1", "status": "APPLIED"}, {"review_id": "r2", "status": "ROLLED_BACK"}],
    )
    assert projections
    assert cs.RETIRED not in {item.state for item in projections}
    assert all(item.kind != "retirement_decision" for item in projections for item in item.evidence)


def test_transition_vocabulary_allows_and_refuses():
    assert cs.can_transition(cs.ADMITTED, cs.ACTIVE)
    assert cs.can_transition(cs.ACTIVE, cs.DEPRECATED)
    assert not cs.can_transition(cs.PROPOSED, cs.ACTIVE)
    assert not cs.can_transition(cs.RETIRED, cs.ACTIVE)
    assert cs.TRANSITIONS[cs.REJECTED] == ()


def test_credible_transition_requires_named_evidence():
    assert cs.missing_evidence(cs.ADMITTED, cs.ACTIVE) == ("activation_record",)
    assert cs.missing_evidence(cs.ACTIVE, cs.RETIRED) == ("retirement_decision",)
    with pytest.raises(ValueError):
        cs.missing_evidence(cs.PROPOSED, cs.ACTIVE)


def test_comparison_verdict_drives_one_review_action():
    assert cs.compare_action(cs.SAME) == cs.REPLACE
    assert cs.compare_action(cs.SUPERSEDES) == cs.REPLACE
    assert cs.compare_action(cs.SIMILAR) == cs.EVALUATE_IN_DEVELOPMENT
    assert cs.compare_action(cs.COMPLEMENTARY) == cs.KEEP_BOTH
    assert cs.compare_action(cs.DISTINCT) == cs.KEEP_BOTH
    assert cs.compare_action(cs.COMPARISON_UNKNOWN) == cs.NEEDS_HUMAN_REVIEW
    with pytest.raises(ValueError):
        cs.compare_action("ALMOST_SAME")


def test_projection_is_deterministic_and_does_not_mutate_input():
    rows = [component_row(version("1.0.0"), active="1.0.0")]
    state = semantic_state(candidates={"c1": {"status": "PROPOSED"}}, accepted={"v1": {"decision_id": "d1"}})
    before = copy.deepcopy((rows, state))
    first = [item.to_dict() for item in cs.project_snapshot(components=rows, semantic_state=state)]
    second = [item.to_dict() for item in cs.project_snapshot(components=rows, semantic_state=state)]
    assert first == second
    assert (rows, state) == before


def test_state_counts_include_unknown_instead_of_hiding_it():
    projections = cs.project_snapshot(
        components=[component_row(version("1.0.0"), active="1.0.0")],
        semantic_state=semantic_state(candidates={"c1": {"status": "ARCHIVED"}}),
    )
    counts = cs.state_counts(projections)
    assert counts[cs.ACTIVE] == 1
    assert counts[cs.UNKNOWN] == 1
