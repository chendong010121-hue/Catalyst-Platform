"""Platform Standard Core v0.1 — reference vertical slice (compose_report).

Runs the complete Standard -> Adapter -> Existing Runtime -> Standard Result
path with at least one ArtifactRef and minimal Trace events.
"""

from __future__ import annotations

from platform_standard.validation import PlatformValidator

from .platform_standard_reference import make_report_invocation, make_stack


def main() -> None:
    registry, adapter = make_stack()
    validator = PlatformValidator()

    invocation = make_report_invocation(
        {
            "title": "Q1 Business Review",
            "sections": ["Revenue grew 12%.", "Operating costs stayed flat.", "Margins improved to 34%."],
        },
        invocation_id="inv_001",
        trace_id="trace_001",
    )
    validator.validate_invocation(invocation)

    result = adapter.execute(invocation)

    print("=== Standard Result ===")
    print(f"status     : {result.status}")
    print(f"output     : {result.output}")
    print("artifacts  :")
    for artifact in result.artifacts:
        print(f"  - type={artifact.artifact_type} version={artifact.artifact_version} uri={artifact.uri}")
        print(f"    producer(capability_id={artifact.producer.capability_id}, invocation_id={artifact.producer.invocation_id})")
    print("=== Minimal Trace ===")
    for event in adapter.trace_events():
        print(f"  - {event.event_type}  subject={event.subject_id}  trace={event.trace_id}")

    # all Standard objects validate
    validator.validate_result(result)
    for artifact in result.artifacts:
        validator.validate_artifact_ref(artifact)
    for event in adapter.trace_events():
        validator.validate_trace_event(event)

    assert result.status == "success"
    assert result.output["report_text"].startswith("# Q1 Business Review")
    assert len(result.artifacts) >= 1
    event_types = [e.event_type for e in adapter.trace_events()]
    assert "invocation.started" in event_types
    assert "invocation.completed" in event_types
    assert "artifact.created" in event_types

    print("\nVERTICAL SLICE PASS")


if __name__ == "__main__":
    main()
