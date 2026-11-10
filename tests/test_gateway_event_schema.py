"""The operations that carry an owner receipt run under an event schema that can hold one."""
import pytest

from catalyst_platform.gateway import CatalystGateway


@pytest.mark.parametrize("operation, expected", [
    ("candidate.decide", "1.5"),
    ("version.activate", "1.5"),
    ("version.rollback", "1.5"),
    ("review.submit", "1.5"),
    ("consumer.relations", "1.5"),
    ("understand.candidate.publish", "1.6"),
    ("candidate.evaluate", None),
])
def test_an_operation_gets_the_event_schema_its_transition_needs(tmp_path, operation, expected):
    gateway = CatalystGateway(tmp_path)
    outcome = gateway.semantic_operation(
        operation=operation, scope_id="scope_test", actor_origin="manager_acceptance",
        input_value={"probe": True},
        action=lambda recorder: {"schema": recorder.event_schema_version},
    )
    assert outcome["status"] == "success"
    recorded = outcome["result"]["schema"]
    if expected is None:
        assert recorded != "1.5"
    else:
        assert recorded == expected
