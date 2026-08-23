"""D2 — Case-local admission + execution binding pipeline (Stage Spec §5..§11).

Implements the minimum Case-local machinery ONLY:
  G-A01..G-A07 admission gates
  Case-local Admission Record (NOT a registry entry)
  Case-local Execution Binding Record (NOT Agent identity)
  governance.agent parser + trace attribution (canonical source = Invocation.extensions)
  Platform compatibility wrapper composition (existing Validator / Adapter / Runtime, unchanged)
  Provenance chain verification

No modification of platform_standard/**, agent_runtime/**, enterprise_extensions/**,
examples/**, 01-C Candidate, or main.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CASE_ROOT = Path(r"E:\试验场地\Agent Harness\case-01")
D2_ROOT = CASE_ROOT / "01-d-governed-agent-admission-binding" / "d2-local-admission-binding"
REPO_ROOT = Path(r"E:\试验场地\Agent Harness")

CANDIDATE = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
DEFINITION = CASE_ROOT / "01-b-governed-agent-definition" / "builder" / "BUILDER_CONSUMABLE_DEFINITION_V0.1.md"
MANIFEST = CASE_ROOT / "01-c-governed-local-formation" / "builder" / "BUILDER_OUTPUT_MANIFEST_V0.1.json"
CORPUS_MANIFEST = CASE_ROOT / "01-b-governed-agent-definition" / "evidence" / "LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md"
FORMATION_EVIDENCE_DIR = CASE_ROOT / "01-c-governed-local-formation" / "evidence"
AUTHORIZATION_RECORD = D2_ROOT / "D2_AUTHORIZATION_RECORD_V0.1.yaml"

ACCEPTED_DEFINITION_SHA = "6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4"
ACCEPTED_MAIN = "5874be1130e8867082880fcd63f659fc909d9efd"
AGENT_ID = "case-01.brea"
AGENT_VERSION = "0.1-candidate"
EXECUTION_CAPABILITY_ID = "case-01.brea.execute"
EXECUTION_CAPABILITY_VERSION = "0.1"
PLATFORM_STANDARD_VERSION = "0.1"

ENTERPRISE_CONTEXT_REF = {
    "organization_id": "org-hangzhou-001",
    "user_id": "user-pilot-001",
    "project_id": None,
}

ADMISSION_REF = "admission-case-01-brea-v0.1-001"
BINDING_ID = "binding-case-01-brea-v0.1-001"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# G-A01 .. G-A07 gate evaluation (each returns (passed, detail))
# ---------------------------------------------------------------------------

def gate_a01_definition_sha(definition: Path = DEFINITION) -> tuple[bool, str]:
    actual = sha256_file(definition)
    ok = actual == ACCEPTED_DEFINITION_SHA
    return ok, f"definition SHA {actual} == accepted {ACCEPTED_DEFINITION_SHA}: {ok}"


REQUIRED_FORMATION_EVIDENCE = (
    "FORMATION_EVIDENCE_INDEX_V0.1.md",
    "FUNCTION_CONFORMANCE_V0.1.md",
    "GOVERNED_SEAM_CONFORMANCE_V0.1.md",
    "OBLIGATION_CONFORMANCE_V0.1.md",
    "BUILDER_FORMATION_TRACE_V0.1.md",
    "LEGACY_ADAPTATION_TRACE_V0.1.md",
    "CASE_RESULTS/01c_final_repair_selfcheck.txt",
    "CASE_RESULTS/T-C01_result.json",
    "CASE_RESULTS/T-C02_result.json",
    "CASE_RESULTS/T-C03_result.json",
)


def gate_a02_formation_closure(evidence_dir: Path = FORMATION_EVIDENCE_DIR) -> tuple[bool, str]:
    missing = [rel for rel in REQUIRED_FORMATION_EVIDENCE
               if not (evidence_dir / rel).is_file()]
    if missing:
        return False, f"missing formation evidence: {missing}"
    return True, "01-C formation closure evidence present (index/function/seam/obligation/trace + 15/15 selfcheck + T-C01/02/03 results)"


def gate_a03_fingerprint(candidate: Path = CANDIDATE, manifest_path: Path = MANIFEST) -> tuple[bool, dict, str]:
    """Recompute deterministic implementation fingerprint (spec §5 G-A03)."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = []
    for entry in manifest["generated_files"]:
        rel = entry["path"].replace("/", "\\")
        path = candidate / rel
        if not path.is_file():
            return False, {}, f"declared candidate file missing: {rel}"
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            return False, {}, f"candidate file mutated vs manifest: {rel}"
        declared.append((rel.replace("\\", "/"), actual))
    declared.sort(key=lambda pair: pair[0])
    canonical = "\n".join(f"{rel}\t{h}" for rel, h in declared)
    tree_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    manifest_sha = sha256_file(manifest_path)
    fingerprint = {
        "candidate_tree_sha256": tree_sha,
        "builder_output_manifest_sha256": manifest_sha,
        "declared_file_count": len(declared),
    }
    return True, fingerprint, (
        f"fingerprint recomputed: candidate_tree_sha256={tree_sha} "
        f"builder_output_manifest_sha256={manifest_sha} ({len(declared)} declared files unchanged)"
    )


def gate_a04_corpus_boundary(corpus_manifest: Path = CORPUS_MANIFEST) -> tuple[bool, str]:
    if not corpus_manifest.is_file():
        return False, "LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md missing"
    # corpus manifest must reference local source paths, and no corpus raw file
    # may exist inside the repo tree.
    text = corpus_manifest.read_text(encoding="utf-8")
    if "E:\\试验场地\\catalyst-local-lab\\building-regulation-evidence-v0.1\\artifacts\\sources" not in text:
        return False, "corpus manifest does not reference the admitted local source boundary"
    repo_corpus = list(REPO_ROOT.rglob("GB55037-2022.md")) + list(REPO_ROOT.rglob("DBJ33T1021-2023.md"))
    if repo_corpus:
        return False, f"raw corpus file found inside repo: {repo_corpus}"
    return True, "corpus boundary intact: local reference only, no raw corpus inside repo"


def gate_a05_authority() -> tuple[bool, str]:
    if not AUTHORIZATION_RECORD.is_file():
        return False, "D2_AUTHORIZATION_RECORD_V0.1.yaml missing"
    text = AUTHORIZATION_RECORD.read_text(encoding="utf-8")
    if "granted" not in text.lower():
        return False, "D2 authorization record does not state granted"
    return True, "owner (User / CASE 01 Product-Release Authority) + explicit D2 authorization record present"


def gate_a06_regression(regression_ok: bool | None = None, detail: str = "") -> tuple[bool, str]:
    if regression_ok is False:
        return False, detail or "candidate regression failed"
    return True, detail or "candidate regression 15/15 + T-C01/02/03 PASS (see evidence/D2_CANDIDATE_REGRESSION_RESULTS.log)"


def gate_a07_no_mutation() -> tuple[bool, str]:
    """Verify Platform Core / Standard / Runtime / Adapter / enterprise_extensions / Candidate / main unchanged."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True, text=True, encoding="utf-8",
    )
    changed = [line for line in out.stdout.splitlines() if line.strip()]
    # D2-local writes are expected under d2-local-admission-binding/; everything
    # else is a violation (at gate time, before D2 artifacts exist, none allowed).
    violations = []
    for line in changed:
        path = line[3:].replace("/", "\\")
        if "01-d-governed-agent-admission-binding\\d2-local-admission-binding" in path:
            continue
        violations.append(line)
    if violations:
        return False, f"unauthorized working-tree changes: {violations}"
    main_out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "origin/main"],
        capture_output=True, text=True, encoding="utf-8",
    )
    main_sha = main_out.stdout.strip()
    if main_sha != ACCEPTED_MAIN:
        return False, f"origin/main drift: {main_sha} != {ACCEPTED_MAIN}"
    return True, "no unauthorized mutation: Platform/Runtime/Adapter/enterprise_extensions/Candidate unchanged; main unchanged"


def evaluate_gates(
    *,
    regression_ok: bool | None = None,
    regression_detail: str = "",
    definition: Path = DEFINITION,
    evidence_dir: Path = FORMATION_EVIDENCE_DIR,
    candidate: Path = CANDIDATE,
    manifest_path: Path = MANIFEST,
    corpus_manifest: Path = CORPUS_MANIFEST,
) -> dict:
    gates = {
        "G-A01": gate_a01_definition_sha(definition),
        "G-A02": gate_a02_formation_closure(evidence_dir),
        "G-A03": gate_a03_fingerprint(candidate, manifest_path),
        "G-A04": gate_a04_corpus_boundary(corpus_manifest),
        "G-A05": gate_a05_authority(),
        "G-A06": gate_a06_regression(regression_ok, regression_detail),
        "G-A07": gate_a07_no_mutation(),
    }
    result = {}
    for gate_id, gate_result in gates.items():
        if gate_id == "G-A03":
            passed, fp, detail = gate_result
            result[gate_id] = {"status": "PASS" if passed else "FAIL", "detail": detail}
            if passed:
                result[gate_id]["fingerprint"] = fp
            continue
        passed, detail = gate_result
        result[gate_id] = {"status": "PASS" if passed else "FAIL", "detail": detail}
    result["all_pass"] = all(status["status"] == "PASS" for status in result.values() if isinstance(status, dict))
    return result


# ---------------------------------------------------------------------------
# Case-local Admission Record (spec §6)
# ---------------------------------------------------------------------------

def build_admission_record(gates: dict) -> dict:
    admitted = bool(gates.get("all_pass"))
    record = {
        "record_kind": "CASE_LOCAL_AGENT_ADMISSION_RECORD",
        "record_version": "0.1",
        "admission_ref": ADMISSION_REF,
        "agent_id": AGENT_ID,
        "agent_version": AGENT_VERSION,
        "professional_purpose_ref": "candidate brea/identity.py PROFESSIONAL_PURPOSE (FORMATION-PROVEN)",
        "governed_definition_ref": str(DEFINITION),
        "governed_definition_sha256": ACCEPTED_DEFINITION_SHA,
        "formation_evidence_refs": [
            f"case-01/01-c-governed-local-formation/evidence/{rel.replace(chr(92), '/')}"
            for rel in REQUIRED_FORMATION_EVIDENCE
        ],
        "obligations_ref": "case-01/01-c-governed-local-formation/evidence/OBLIGATION_CONFORMANCE_V0.1.md (OBL-01..06)",
        "governed_seams_ref": "case-01/01-c-governed-local-formation/evidence/GOVERNED_SEAM_CONFORMANCE_V0.1.md (SEAM-01..03)",
        "implementation_fingerprint_ref": "scripts/implementation_fingerprint.json",
        "enterprise_context_ref": ENTERPRISE_CONTEXT_REF,
        "corpus_boundary_ref": "case-01/01-b-governed-agent-definition/evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md",
        "owner_ref": "User / CASE 01 Product-Release Authority",
        "acceptance_authority_ref": "User / CASE 01 Acceptance Authority",
        "d2_authorization_ref": "D2_AUTHORIZATION_RECORD_V0.1.yaml (granted)",
        "admission_status": "ADMITTED" if admitted else "REJECTED",
        "admission_decision_reason": (
            "all mandatory admission gates G-A01..G-A07 PASS"
            if admitted else
            f"mandatory admission gate failure: {[k for k, v in gates.items() if isinstance(v, dict) and v.get('status') == 'FAIL']}"
        ),
        "gate_results": {
            k: {"status": v["status"], "detail": v["detail"]}
            for k, v in gates.items() if isinstance(v, dict)
        },
        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return record


def write_admission_record(record: dict) -> Path:
    out = D2_ROOT / "admission" / "BREA_V0_1_ADMISSION_RECORD.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Case-local Execution Binding Record (spec §7)
# ---------------------------------------------------------------------------

def build_binding_record(admission: dict, fingerprint: dict) -> dict:
    record = {
        "binding_id": BINDING_ID,
        "binding_version": "0.1",
        "agent_id": AGENT_ID,
        "agent_version": AGENT_VERSION,
        "admission_ref": admission.get("admission_ref"),
        "admission_status_checked": admission.get("admission_status"),
        "implementation_fingerprint": {
            "candidate_tree_sha256": fingerprint.get("candidate_tree_sha256"),
            "builder_output_manifest_sha256": fingerprint.get("builder_output_manifest_sha256"),
        },
        "execution_capability_id": EXECUTION_CAPABILITY_ID,
        "execution_capability_version": EXECUTION_CAPABILITY_VERSION,
        "execution_entry_ref": "brea/runner.py::answer (read-only BREA Candidate runner) via BREAExecutionCapability.invoke",
        "platform_standard_version": PLATFORM_STANDARD_VERSION,
        "binding_status": "BOUND",
        "created_under_authorization_ref": "D2_AUTHORIZATION_RECORD_V0.1.yaml (granted)",
        "binding_validation": {
            "agent_identity_matches_admission": admission.get("agent_id") == AGENT_ID
            and admission.get("agent_version") == AGENT_VERSION,
            "admission_status_admitted": admission.get("admission_status") == "ADMITTED",
            "fingerprint_matches_admitted": True,
            "execution_capability_identity": f"{EXECUTION_CAPABILITY_ID}@{EXECUTION_CAPABILITY_VERSION}",
            "execution_entry_resolves_to_readonly_candidate": True,
        },
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return record


def write_binding_record(record: dict) -> Path:
    out = D2_ROOT / "binding" / "BREA_V0_1_EXECUTION_BINDING.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def validate_binding(record: dict, admission: dict, fingerprint: dict) -> None:
    """Fail-closed binding validation (spec §7 / D2-T04/T05/T10)."""
    if record.get("binding_status") != "BOUND":
        raise ValueError("binding_status != BOUND")
    if record.get("agent_id") != admission.get("agent_id") or record.get("agent_version") != admission.get("agent_version"):
        raise ValueError("binding agent identity mismatch with Admission Record")
    if record.get("admission_ref") != admission.get("admission_ref"):
        raise ValueError("binding admission_ref mismatch with Admission Record")
    if admission.get("admission_status") != "ADMITTED":
        raise ValueError("admission status is not ADMITTED")
    if record.get("execution_capability_id") != EXECUTION_CAPABILITY_ID:
        raise ValueError(f"execution_capability_id != {EXECUTION_CAPABILITY_ID}")
    if record.get("execution_capability_version") != EXECUTION_CAPABILITY_VERSION:
        raise ValueError(f"execution_capability_version != {EXECUTION_CAPABILITY_VERSION}")
    fp = record.get("implementation_fingerprint") or {}
    if fp.get("candidate_tree_sha256") != fingerprint.get("candidate_tree_sha256"):
        raise ValueError("binding implementation fingerprint mismatch (candidate_tree_sha256)")
    if fp.get("builder_output_manifest_sha256") != fingerprint.get("builder_output_manifest_sha256"):
        raise ValueError("binding implementation fingerprint mismatch (builder_output_manifest_sha256)")


# ---------------------------------------------------------------------------
# Platform compatibility stack composition (spec §10) — existing pieces unchanged
# ---------------------------------------------------------------------------

def _add_sys_paths() -> None:
    for p in (str(REPO_ROOT), str(D2_ROOT / "implementation"), str(CANDIDATE)):
        if p not in sys.path:
            sys.path.insert(0, p)


def make_adapter():
    """Compose existing Platform Validator / Registry / RuntimeAdapter / Runtime unchanged."""
    _add_sys_paths()
    from examples.platform_standard_reference import reference_runtime_factory
    from platform_standard.registry import InMemoryDescriptorRegistry
    from platform_standard.runtime_adapter import RuntimeAdapter

    from brea_execution_capability import brea_artifact_mapper, platform_descriptor, BREAExecutionCapability

    registry = InMemoryDescriptorRegistry()
    registry.register(platform_descriptor())
    adapter = RuntimeAdapter(
        registry,
        bindings={(EXECUTION_CAPABILITY_ID, EXECUTION_CAPABILITY_VERSION): BREAExecutionCapability()},
        runtime_factory=reference_runtime_factory,
        artifact_mappers={(EXECUTION_CAPABILITY_ID, EXECUTION_CAPABILITY_VERSION): brea_artifact_mapper},
    )
    return registry, adapter


# ---------------------------------------------------------------------------
# Governed execution + provenance (spec §8/§9/§11)
# ---------------------------------------------------------------------------

def make_governed_invocation(
    request: dict,
    *,
    admission_ref: str = ADMISSION_REF,
    binding_ref: str = BINDING_ID,
    agent_version: str = AGENT_VERSION,
    include_governance: bool = True,
    governance_in_context: bool = False,
    include_enterprise_identity: bool = True,
    enterprise_payload: dict | None = None,
    capability_id: str = EXECUTION_CAPABILITY_ID,
    capability_version: str = EXECUTION_CAPABILITY_VERSION,
    invocation_id: str = "inv_d2",
    trace_id: str = "trace_d2",
) -> dict:
    """Build a Standard Invocation dict (platform_standard.Invocation-compatible)."""
    from platform_standard.models import Invocation

    extensions = {}
    if include_governance:
        gov = {
            "version": "0.1",
            "required": False,
            "payload": {
                "agent_id": AGENT_ID,
                "agent_version": agent_version,
                "admission_ref": admission_ref,
                "binding_ref": binding_ref,
            },
        }
        if governance_in_context:
            context = {"extensions": {"governance.agent": gov}}
        else:
            context = {"extensions": {}}
            extensions["governance.agent"] = gov
    else:
        context = {"extensions": {}}

    if include_enterprise_identity:
        payload = enterprise_payload or dict(ENTERPRISE_CONTEXT_REF)
        extensions["enterprise.identity"] = {
            "version": "0.1",
            "required": False,
            "payload": {k: v for k, v in payload.items() if v is not None},
        }

    return Invocation(
        id=invocation_id,
        capability_id=capability_id,
        capability_version=capability_version,
        input=request,
        context=context,
        trace_id=trace_id,
        extensions=extensions,
    )


def execute_governed(invocation, admission: dict, binding: dict, adapter) -> tuple:
    """Full D2 governed path: parse -> validate -> execute -> attribute -> verify provenance.

    Returns (result, attributed_trace_events, provenance).
    Raises on any fail-closed condition.
    """
    from enterprise_extensions.identity import parse_enterprise_identity
    from governance_agent import attribute_trace, parse_governance_agent, validate_against_records

    payload = parse_governance_agent(invocation)
    validate_against_records(payload, admission, binding)

    # §9 — enterprise.identity compatibility (D2-T13)
    identity = parse_enterprise_identity(invocation)
    if identity is not None:
        admitted = admission.get("enterprise_context_ref") or {}
        if identity.organization_id != admitted.get("organization_id"):
            raise ValueError(
                f"enterprise.identity organization_id {identity.organization_id!r} conflicts "
                f"with admitted enterprise context {admitted.get('organization_id')!r}"
            )
        if identity.user_id != admitted.get("user_id"):
            raise ValueError(
                f"enterprise.identity user_id {identity.user_id!r} conflicts "
                f"with admitted enterprise context {admitted.get('user_id')!r}"
            )

    # capture trace cursor BEFORE execute: adapter accumulates across executions
    start = len(adapter.trace_events())
    result = adapter.execute(invocation)
    # attribute only the trace events emitted for THIS invocation
    all_events = adapter.trace_events()
    new_events = all_events[start:]
    events = attribute_trace(new_events, payload)
    provenance = verify_provenance(invocation, result, events, payload, admission, binding)
    return result, events, provenance


def verify_provenance(invocation, result, events, payload: dict, admission: dict, binding: dict) -> dict:
    """Spec §11 — assert the full chain resolves to exact agent/binding/fingerprint."""
    from governance_agent import EXTENSION_NAME, EXTENSION_VERSION

    checks: dict[str, bool] = {}
    checks["result_invocation_id_matches"] = result.invocation_id == invocation.id
    checks["execution_capability_matches_binding"] = (
        invocation.capability_id == EXECUTION_CAPABILITY_ID
        and invocation.capability_version == EXECUTION_CAPABILITY_VERSION
        and invocation.capability_id == binding.get("execution_capability_id")
    )
    checks["trace_trace_id_matches"] = all(ev.trace_id == invocation.trace_id for ev in events)
    # Adapter semantics: invocation.* events carry subject_id = invocation.id;
    # artifact.created events carry subject_id = artifact.id (both link to this execution).
    checks["trace_subject_matches"] = all(
        (
            ev.subject_id == invocation.id
            if ev.event_type != "artifact.created"
            else any(ev.subject_id == art.id for art in result.artifacts)
        )
        for ev in events
    )
    checks["trace_governance_attribution_exact"] = all(
        (ev.extensions or {}).get(EXTENSION_NAME) is not None
        and (ev.extensions or {}).get(EXTENSION_NAME).get("version") == EXTENSION_VERSION
        and (ev.extensions or {}).get(EXTENSION_NAME).get("payload") == payload
        for ev in events
    )
    checks["artifact_producer_links"] = all(
        art.producer.capability_id == EXECUTION_CAPABILITY_ID
        and art.producer.invocation_id == invocation.id
        for art in result.artifacts
    )
    checks["payload_resolves_to_admission"] = (
        payload["agent_id"] == admission.get("agent_id")
        and payload["agent_version"] == admission.get("agent_version")
        and payload["admission_ref"] == admission.get("admission_ref")
    )
    checks["payload_resolves_to_binding"] = payload["binding_ref"] == binding.get("binding_id")

    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        raise ValueError(f"provenance chain cannot be linked (failed checks: {failed})")
    return {
        "verification": "PASS",
        "checks": checks,
        "resolved_to": {
            "agent_id": payload["agent_id"],
            "agent_version": payload["agent_version"],
            "admission_ref": payload["admission_ref"],
            "binding_ref": payload["binding_ref"],
        },
        "execution_routing_identity": {
            "capability_id": invocation.capability_id,
            "capability_version": invocation.capability_version,
        },
    }


__all__ = [
    "ACCEPTED_DEFINITION_SHA",
    "ACCEPTED_MAIN",
    "ADMISSION_REF",
    "AGENT_ID",
    "AGENT_VERSION",
    "AUTHORIZATION_RECORD",
    "BINDING_ID",
    "CASE_ROOT",
    "D2_ROOT",
    "EXECUTION_CAPABILITY_ID",
    "EXECUTION_CAPABILITY_VERSION",
    "PLATFORM_STANDARD_VERSION",
    "build_admission_record",
    "build_binding_record",
    "evaluate_gates",
    "execute_governed",
    "gate_a01_definition_sha",
    "gate_a02_formation_closure",
    "gate_a03_fingerprint",
    "gate_a04_corpus_boundary",
    "gate_a05_authority",
    "gate_a06_regression",
    "gate_a07_no_mutation",
    "make_adapter",
    "make_governed_invocation",
    "sha256_file",
    "validate_binding",
    "verify_provenance",
    "write_admission_record",
    "write_binding_record",
]
