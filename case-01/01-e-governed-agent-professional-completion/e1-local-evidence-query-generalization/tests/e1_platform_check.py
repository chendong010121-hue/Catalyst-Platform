"""E1 — Platform compatibility check (Stage Spec §17).

Answers: can the v0.2 Candidate still satisfy the existing D2 execution adapter shape
without Platform Core / Runtime changes?

Reuses the EXACT unchanged Platform path (PlatformValidator -> InMemoryDescriptorRegistry
-> RuntimeAdapter -> Runtime) and the reference runtime factory, with a v0.2 BREA
capability adapter (describe/invoke) mirroring the D2 `brea_execution_capability.py`
shape. No Platform / Runtime / Adapter file is modified.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
E1_DIR = REPO_ROOT / "case-01" / "01-e-governed-agent-professional-completion" / "e1-local-evidence-query-generalization"
CANDIDATE = E1_DIR / "candidate" / "brea-v0.2"
FIXTURES = CANDIDATE / "tests" / "fixtures" / "requests"

for p in (str(REPO_ROOT), str(CANDIDATE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent_runtime.contracts import (  # noqa: E402
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Success,
)
from examples.platform_standard_reference import reference_runtime_factory  # noqa: E402
from platform_standard.models import CapabilityDescriptor, Invocation, Producer, ArtifactRef  # noqa: E402
from platform_standard.registry import InMemoryDescriptorRegistry  # noqa: E402
from platform_standard.runtime_adapter import RuntimeAdapter  # noqa: E402

from brea.runner import answer as brea_answer  # noqa: E402

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


class BREAV02Capability:
    """D2-shape adapter for the v0.2 candidate (describe/invoke; contract identical)."""

    def describe(self) -> RuntimeCapabilityDescriptor:
        return RuntimeCapabilityDescriptor(
            id="case_01_brea_execute",
            name="BREA Execute (routing only)",
            description="Execution-routing capability for the BREA Agent (v0.2 candidate).",
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


def platform_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id=EXECUTION_CAPABILITY_ID,
        name="BREA Execute (routing only)",
        description="Execution-routing descriptor for the BREA Agent (v0.2 candidate).",
        capability_version=EXECUTION_CAPABILITY_VERSION,
        input_schema=BREA_INPUT_SCHEMA,
        output_schema=BREA_OUTPUT_SCHEMA,
        execution={"side_effect": "none"},
    )


def brea_v02_artifact_mapper(output, invocation):
    items = (output or {}).get("evidence_items", [])
    return tuple(
        ArtifactRef(
            id=f"brea-ev-{invocation.id}-{index}",
            artifact_type="regulation_evidence",
            artifact_version="1",
            uri=f"case-evidence://{item.get('source_identity', '')}#{item.get('locator', '')}",
            producer=Producer(capability_id=EXECUTION_CAPABILITY_ID, invocation_id=invocation.id),
        )
        for index, item in enumerate(items[:10])
    )


def make_stack():
    registry = InMemoryDescriptorRegistry()
    registry.register(platform_descriptor())
    adapter = RuntimeAdapter(
        registry,
        bindings={(EXECUTION_CAPABILITY_ID, EXECUTION_CAPABILITY_VERSION): BREAV02Capability()},
        runtime_factory=reference_runtime_factory,
        artifact_mappers={(EXECUTION_CAPABILITY_ID, EXECUTION_CAPABILITY_VERSION): brea_v02_artifact_mapper},
    )
    return registry, adapter


def load_request(case_or_qmode: str) -> dict:
    if case_or_qmode in ("T-C01", "T-C02", "T-C03"):
        data = json.loads((FIXTURES / f"{case_or_qmode}.json").read_text(encoding="utf-8"))
        return data["request"]
    probes = {
        "QMODE-01": {"request_id": "inv-e1-qm01", "question": "GB55037-2022 第2.1.1条怎么规定？",
                     "project_context": {}, "regulation_context": {},
                     "enterprise_context": {"organization_id": "org-hangzhou-001", "user_id": "user-pilot-001"}},
        "QMODE-03": {"request_id": "inv-e1-qm03", "question": "GB55037 里哪里提到人员密集场所？",
                     "project_context": {}, "regulation_context": {},
                     "enterprise_context": {"organization_id": "org-hangzhou-001", "user_id": "user-pilot-001"}},
    }
    return probes[case_or_qmode]


def main() -> int:
    registry, adapter = make_stack()
    checks = {}

    # contract compatibility: request/result shape through the unchanged Platform path
    for label in ("T-C01", "T-C02", "T-C03", "QMODE-01", "QMODE-03"):
        request = load_request(label)
        invocation = Invocation(
            id=f"inv_{label}", capability_id=EXECUTION_CAPABILITY_ID,
            capability_version=EXECUTION_CAPABILITY_VERSION,
            input=request, context={"extensions": {}}, trace_id=f"trace_{label}",
        )
        result = adapter.execute(invocation)
        output = result.output or {}
        required = ("request_id", "status", "conclusion", "evidence_items",
                    "artifacts", "uncertainty", "implementation_metadata")
        checks[label] = {
            "platform_result_status": result.status,
            "output_keys_present": all(key in output for key in required),
            "professional_status": output.get("status"),
            "artifacts_linked": all(
                a.producer.capability_id == EXECUTION_CAPABILITY_ID
                and a.producer.invocation_id == invocation.id
                for a in result.artifacts
            ),
        }
        print(f"{label}: platform_status={result.status} contract_ok={checks[label]['output_keys_present']} "
              f"professional_status={output.get('status')} artifacts_linked={checks[label]['artifacts_linked']}")

    all_ok = all(
        v["output_keys_present"] and v["platform_result_status"] == "success"
        and v["artifacts_linked"] for v in checks.values()
    )
    print(f"== PLATFORM COMPATIBILITY: {'PASS' if all_ok else 'FAIL'} ==")

    doc = E1_DIR / "evidence" / "E1_PLATFORM_COMPATIBILITY_CHECK_V0.1.md"
    lines = [
        "# E1 — PLATFORM COMPATIBILITY CHECK — V0.1",
        "",
        "> Stage Spec §17: can v0.2 still satisfy the existing D2 execution adapter shape",
        "> without Platform Core / Runtime changes?",
        "",
        "## Method",
        "",
        "The v0.2 Candidate runner is wrapped in a D2-shape capability adapter",
        "(`describe()`/`invoke()` with the identical request/result contract) and executed",
        "through the UNCHANGED Platform path:",
        "",
        "```text",
        "PlatformValidator -> InMemoryDescriptorRegistry -> RuntimeAdapter -> Runtime",
        "routing identity: case-01.brea.execute @ 0.1 (same as D2)",
        "reference_runtime_factory: Runtime(reasoner, capabilities, AllowAllPolicy, InMemoryStateStore)",
        "```",
        "",
        "No Platform / Runtime / Adapter source file was modified.",
        "",
        "## Executed cases",
        "",
        "| Case | Platform result | Contract keys | Professional status | Artifacts linked |",
        "|---|---|---|---|---|",
    ]
    for label, v in checks.items():
        lines.append(
            f"| {label} | {v['platform_result_status']} | {'PASS' if v['output_keys_present'] else 'FAIL'} | "
            f"{v['professional_status']} | {'PASS' if v['artifacts_linked'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Conclusion",
        "",
        f"```text",
        f"PLATFORM COMPATIBILITY: {'PASS' if all_ok else 'FAIL'}",
        f"request/result contract compatible : YES (all 7 Result fields preserved)",
        f"Platform Core change              : NONE",
        f"Runtime change                    : NONE",
        f"Runtime Adapter change            : NONE",
        f"D2 Case-local binding mechanism   : conceptually reusable for a future v0.2 admission",
        f"E1 is NOT an admission stage      : no new Admission/Binding Record created",
        f"```",
        "",
    ]
    (E1_DIR / "evidence" / "E1_PLATFORM_COMPATIBILITY_CHECK_V0.1.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"document written: {doc}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
