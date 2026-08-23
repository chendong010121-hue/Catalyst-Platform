"""D2 — Case-local BREA execution capability adapter (Stage Spec §10 / §13).

Adapts the read-only BREA Candidate runner to the Runtime Capability protocol and
provides the Platform Capability Descriptor used ONLY for execution routing.

Agent identity (case-01.brea @ 0.1-candidate) is deliberately separate from the
execution routing identity (case-01.brea.execute @ 0.1) — P-D2-02.
"""
from __future__ import annotations

import sys
from pathlib import Path

CASE_ROOT = Path(r"E:\试验场地\Agent Harness\case-01")
CANDIDATE = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
if str(CANDIDATE) not in sys.path:
    sys.path.insert(0, str(CANDIDATE))

from agent_runtime.contracts import (  # noqa: E402
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Success,
)
from platform_standard.models import (  # noqa: E402
    ArtifactRef,
    CapabilityDescriptor,
    Producer,
)

from brea.runner import answer as brea_answer  # noqa: E402

AGENT_ID = "case-01.brea"
AGENT_VERSION = "0.1-candidate"
EXECUTION_CAPABILITY_ID = "case-01.brea.execute"
EXECUTION_CAPABILITY_VERSION = "0.1"

BREA_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "request_id": {"type": "string"},
        "question": {"type": "string"},
        "project_context": {"type": "object"},
        "regulation_context": {"type": "object"},
        "enterprise_context": {"type": "object"},
    },
    "required": ["request_id", "question", "project_context", "regulation_context", "enterprise_context"],
    "additionalProperties": False,
}
BREA_OUTPUT_SCHEMA = {"type": "object"}


def platform_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id=EXECUTION_CAPABILITY_ID,
        name="BREA Execute (routing only)",
        description="Platform execution-routing descriptor for the admitted BREA Agent. "
                    "Not the Agent identity source.",
        capability_version=EXECUTION_CAPABILITY_VERSION,
        input_schema=BREA_INPUT_SCHEMA,
        output_schema=BREA_OUTPUT_SCHEMA,
        execution={"side_effect": "none"},
    )


class BREAExecutionCapability:
    """Runtime Capability protocol adapter for the read-only BREA Candidate runner."""

    def describe(self) -> RuntimeCapabilityDescriptor:
        # Runtime CapabilityDescriptor.id must be a portable model-tool name
        # (^[A-Za-z0-9_-]{1,64}$). The Runtime-facing id is adapter-local: the
        # RuntimeAdapter rewrites it to its own internal key and routes by
        # (platform capability_id, capability_version). The Platform routing
        # identity stays `case-01.brea.execute @ 0.1` (binding record).
        return RuntimeCapabilityDescriptor(
            id="case_01_brea_execute",
            name="BREA Execute (routing only)",
            description="Execution-routing capability for the admitted BREA Agent.",
            input_schema=BREA_INPUT_SCHEMA,
            output_schema=BREA_OUTPUT_SCHEMA,
        )

    def invoke(self, parameters, context):
        result = brea_answer(
            request_id=parameters["request_id"],
            question=parameters["question"],
            project_context=parameters.get("project_context", {}),
            regulation_context=parameters.get("regulation_context", {}),
            enterprise_context=parameters.get("enterprise_context", {}),
        )
        return Success(result.to_dict())


def brea_artifact_mapper(output, invocation):
    """Case-local mapper: BREA evidence items -> Standard ArtifactRefs (producer links execution id + invocation id)."""
    refs = []
    items = (output or {}).get("evidence_items", [])
    for index, item in enumerate(items[:10]):
        refs.append(
            ArtifactRef(
                id=f"brea-ev-{invocation.id}-{index}",
                artifact_type="regulation_evidence",
                artifact_version="1",
                uri=f"case-evidence://{item.get('source_identity', '')}#{item.get('locator', '')}",
                producer=Producer(
                    capability_id=EXECUTION_CAPABILITY_ID,
                    invocation_id=invocation.id,
                ),
            )
        )
    return tuple(refs)
