"""Catalyst Platform V0.1 pre-merge test campaign.

Deterministic tests cover Catalyst-owned boundaries. Comparative external claims are
represented as decision fixtures and are separately reviewed against official external
project documentation; this module does not pretend to execute external providers.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from agent_runtime.contracts import (
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Goal,
    ModelResponse,
    Success,
)
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.runtime import Runtime
from examples.fakes import AllowAllPolicy, FakeCapability, InMemoryStateStore, ScriptedModelProvider
from examples.platform_standard_reference import (
    compose_report_artifact_mapper,
    compose_report_descriptor,
    make_report_invocation,
    make_stack,
    reference_runtime_factory,
)
from platform_standard.models import CapabilityDescriptor
from platform_standard.registry import InMemoryDescriptorRegistry
from platform_standard.runtime_adapter import AdapterConfigurationError, RuntimeAdapter

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json"
SKILL = ROOT / "platform-harness" / "skills" / "agent-construction" / "SKILL.md"
DELIVERY = ROOT / "CATALYST_PLATFORM_INTEGRATION_V0.1_FINAL_DELIVERY.md"
CASE01 = ROOT / "CATALYST_CASE01_CONSTRUCTION_DECISION_DRY_RUN_V0.1.json"
COMPOSE = ROOT / "CATALYST_CONSTRUCTION_DECISION_PROOF_COMPOSE_REPORT_V0.1.json"
FIXED = ROOT / "CATALYST_TEST_DECISION_FIXED_WORKFLOW_V0.1.json"
TRUE_AGENT = ROOT / "CATALYST_TEST_DECISION_TRUE_AGENT_V0.1.json"
WAKU = ROOT / "CATALYST_TEST_DECISION_WAKU_REUSE_V0.1.json"
MCP = ROOT / "CATALYST_TEST_DECISION_MCP_INTAKE_V0.1.json"
MULTI = ROOT / "CATALYST_TEST_DECISION_MULTI_AGENT_SIMPLIFICATION_V0.1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def assert_decision(decision: dict) -> None:
    for key in ("need", "responsibility", "capability_search", "solution", "proof", "governance"):
        assert key in decision, key
    assert decision["need"]["purpose_or_required_outcome"]
    assert decision["responsibility"]["responsibilities"]
    assert "reused_capability_refs" in decision["capability_search"]
    assert "missing_or_unproven_capability_needs" in decision["capability_search"]
    assert decision["solution"]["selected_solution_form"]
    assert decision["proof"]["evidence_requirements"]
    assert decision["governance"]["stop_condition"]
    forbidden = {"input_schema", "output_schema", "execution", "health", "score", "harvest_verdict"}
    assert not (forbidden & set(walk_keys(decision)))


class AlternateComposeReportCapability:
    """Different HOW, same direct-binding public contract."""

    def describe(self):
        d = compose_report_descriptor()
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Alternative Compose Report",
            description="Replaceable implementation of the same public Capability.",
            input_schema=d.input_schema,
            output_schema=d.output_schema,
        )

    def invoke(self, parameters, context):
        title = parameters["title"]
        sections = parameters.get("sections", [])
        text = "\n\n".join([f"# {title}", *sections]).strip()
        return Success(
            {
                "report_text": text,
                "artifact_uri": f"file:///outputs/alt_{title.replace(' ', '_')}.md",
            }
        )


class RaisingComposeReportCapability:
    """Conforming binding whose execution certainty becomes unresolved."""

    def describe(self):
        d = compose_report_descriptor()
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Raising Compose Report",
            description="Raises during invocation to exercise unresolved execution semantics.",
            input_schema=d.input_schema,
            output_schema=d.output_schema,
        )

    def invoke(self, parameters, context):
        raise RuntimeError("execution outcome not safely classifiable as terminal capability failure")


class WrongButConformingComposeReportCapability:
    """Contract-valid output that is intentionally wrong at product-quality level."""

    def describe(self):
        d = compose_report_descriptor()
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Wrong But Conforming",
            description="Contract-valid but semantically wrong product output.",
            input_schema=d.input_schema,
            output_schema=d.output_schema,
        )

    def invoke(self, parameters, context):
        return Success({"report_text": "WRONG", "artifact_uri": "file:///outputs/wrong.md"})


class AlternateProvider:
    """Independent ModelProvider implementation with the same public seam."""

    def __init__(self):
        self.responses = [
            ModelResponse(content='{"kind":"act","capability_id":"add","parameters":{"a":20,"b":22}}'),
            ModelResponse(content='{"kind":"complete","reason":"42 obtained"}'),
        ]
        self.cursor = 0

    def request(self, request):
        response = self.responses[self.cursor]
        self.cursor += 1
        return response


def registry_with(impl):
    registry = InMemoryDescriptorRegistry()
    registry.register(compose_report_descriptor())
    adapter = RuntimeAdapter(
        registry,
        {("compose_report", "1.0.0"): impl},
        runtime_factory=reference_runtime_factory,
        artifact_mappers={("compose_report", "1.0.0"): compose_report_artifact_mapper},
    )
    return registry, adapter


# ---------------------------------------------------------------------------
# WAVE A — SELF AUDIT
# ---------------------------------------------------------------------------

def test_sa01_architecture_boundaries():
    index = load(INDEX)
    skill = SKILL.read_text(encoding="utf-8")
    adapter_source = (ROOT / "platform_standard" / "runtime_adapter.py").read_text(encoding="utf-8")
    assert "navigation index" in index["purpose"].lower()
    assert "not a Capability contract" in index["purpose"]
    assert "It carries NO business/domain semantics." in adapter_source
    for marker in (
        "It is NOT:",
        "Runtime execution semantics",
        "Evaluation, Admission, or Harvest authority",
        "Capability Search before construction",
        "Emit Runtime requirements, do not absorb Runtime",
        "Emit Evaluation evidence requirements, do not absorb Evaluation",
    ):
        assert marker in skill


def test_sa02_duplicate_responsibility():
    index = load(INDEX)
    allowed = {
        "summary", "authority_ref", "capability_ref", "asset_refs", "evidence_refs",
        "lineage_refs", "realization_or_binding_refs", "known_limits_ref",
        "domain_or_enterprise_binding_refs",
    }
    for entry in index["entries"]:
        assert set(entry).issubset(allowed)
        assert not ({"input_schema", "output_schema", "execution", "health", "score", "status"} & set(entry))
    for path in (
        ROOT / "capability_registry_service",
        ROOT / "evaluation_engine",
        ROOT / "harvest_engine",
        ROOT / "construction_engine",
        ROOT / "capability_search_service",
    ):
        assert not path.exists()


def test_sa03_replaceability():
    # Capability HOW replacement.
    _, adapter = registry_with(AlternateComposeReportCapability())
    invocation = make_report_invocation(
        {"title": "Replacement", "sections": ["same WHAT"]},
        invocation_id="inv_rt_impl",
        trace_id="tr_rt_impl",
    )
    result = adapter.execute(invocation)
    assert result.status == "success"
    assert result.output["report_text"].startswith("# Replacement")
    assert result.artifacts[0].producer.capability_id == "compose_report"

    # ModelProvider replacement at the public provider seam.
    providers = [
        ScriptedModelProvider([
            '{"kind":"act","capability_id":"add","parameters":{"a":20,"b":22}}',
            '{"kind":"complete","reason":"42 obtained"}',
        ]),
        AlternateProvider(),
    ]
    for provider in providers:
        runtime = Runtime(
            reasoner=LLMReasoner(provider),
            capabilities={"add": FakeCapability()},
            policy=AllowAllPolicy(),
            state_store=InMemoryStateStore(),
        )
        final = runtime.start(Goal("得到数字 42"))
        assert final.history[0].observation.data == 42


def test_sa04_false_claims():
    delivery = DELIVERY.read_text(encoding="utf-8")
    for claim in (
        "production Registry service",
        "continuous Capability health monitoring",
        "automatic replacement / migration",
        "Evaluation engine",
        "Case01 product completeness",
        "WAKU-A01 admission as Platform Capability",
    ):
        assert claim in delivery


# ---------------------------------------------------------------------------
# WAVE B — INTERNAL CONTROLLED TESTS
# ---------------------------------------------------------------------------

def test_it01_simple_reuse():
    decision = load(COMPOSE)
    assert_decision(decision)
    assert decision["solution"]["selected_solution_form"] == "Deterministic implementation"
    assert decision["capability_search"]["reused_capability_refs"] == [{"id": "compose_report", "version": "1.0.0"}]
    assert decision["capability_search"]["missing_or_unproven_capability_needs"] == []


def test_it02_fixed_workflow():
    decision = load(FIXED)
    assert_decision(decision)
    assert decision["solution"]["selected_solution_form"] == "Workflow"
    assert decision["responsibility"]["material_task_characteristics"]["path_predictability"] == "HIGH"
    assert "Agent" in decision["proof"]["not_required_now"]


def test_it03_true_agent():
    decision = load(TRUE_AGENT)
    assert_decision(decision)
    assert decision["solution"]["selected_solution_form"] == "Agent"
    assert decision["responsibility"]["material_task_characteristics"]["path_predictability"] == "LOW"
    assert "observation" in decision["solution"]["short_rationale"].lower()


def test_it04_case01():
    decision = load(CASE01)
    assert_decision(decision)
    assert decision["solution"]["selected_solution_form"] == "UNDECIDED_PENDING_MISSING_CAPABILITY_PROOF"
    assert decision["capability_search"]["missing_or_unproven_capability_needs"]
    assert "Multi-Agent" in decision["proof"]["not_required_now"]


def test_it05_waku_harvest_reuse():
    index = load(INDEX)
    decision = load(WAKU)
    assert_decision(decision)
    harvested = next(e for e in index["entries"] if "Retrieval-gated memory" in e["summary"])
    assert "capability_ref" not in harvested
    assert "WAKU-A01" in harvested["authority_ref"]["anchor"]
    assert "Agent" not in decision["solution"]["selected_solution_form"]
    assert "original Waku Agent runtime" in decision["proof"]["not_required_now"]


def test_it06_failure_attribution_matrix():
    # A — missing Capability: Adapter resolution failure.
    _, adapter = make_stack()
    from platform_standard.models import Invocation
    missing = adapter.execute(
        Invocation(
            id="inv_missing_matrix",
            capability_id="not_registered",
            capability_version="1.0.0",
            input={},
            context={"extensions": {}},
            trace_id="tr_missing_matrix",
        )
    )
    assert missing.status == "failure"
    assert missing.error["code"] == "capability_not_found"

    # B — contract mismatch: Binding/Conformance failure before execution.
    class BadInput:
        def describe(self):
            return RuntimeCapabilityDescriptor(
                id="compose_report",
                name="bad",
                description="bad",
                input_schema={"type": "string"},
                output_schema={"type": "object"},
            )
        def invoke(self, parameters, context):
            return Success({})

    registry = InMemoryDescriptorRegistry()
    registry.register(compose_report_descriptor())
    try:
        RuntimeAdapter(
            registry,
            {("compose_report", "1.0.0"): BadInput()},
            runtime_factory=reference_runtime_factory,
        )
    except AdapterConfigurationError:
        pass
    else:
        raise AssertionError("binding mismatch must fail before execution")

    # C — Runtime certainty failure is unresolved, not Capability failure.
    _, unresolved_adapter = registry_with(RaisingComposeReportCapability())
    unresolved = unresolved_adapter.execute(
        make_report_invocation(
            {"title": "Uncertain", "sections": []},
            invocation_id="inv_unresolved_matrix",
            trace_id="tr_unresolved_matrix",
        )
    )
    assert unresolved.status == "unresolved"
    assert unresolved.error["code"] == "runtime_outcome_uncertain"

    # D — Runtime success does not prove product quality.
    _, wrong_adapter = registry_with(WrongButConformingComposeReportCapability())
    wrong = wrong_adapter.execute(
        make_report_invocation(
            {"title": "Expected", "sections": []},
            invocation_id="inv_wrong_product",
            trace_id="tr_wrong_product",
        )
    )
    assert wrong.status == "success"
    assert wrong.output["report_text"] != "# Expected"


# ---------------------------------------------------------------------------
# WAVE C — EXTERNAL HETEROGENEOUS TESTS
# ---------------------------------------------------------------------------

def test_et01_waku_agent_disposable():
    decision = load(WAKU)
    assert decision["solution"]["selected_solution_form"] == "Deterministic implementation / Skill"
    assert "original Waku Agent runtime" in decision["proof"]["not_required_now"]


def test_et02_langgraph_workflow_bias_check():
    decision = load(FIXED)
    assert decision["solution"]["selected_solution_form"] == "Workflow"
    assert decision["solution"]["selected_pattern_if_useful"] == "fixed sequential orchestration"


def test_et03_mcp_boundary():
    decision = load(MCP)
    assert_decision(decision)
    assert decision["solution"]["selected_solution_form"] == "Service / Adapter"
    assert decision["capability_search"]["reused_capability_refs"] == []
    assert "Capability per MCP tool" in decision["proof"]["not_required_now"]


def test_et04_simple_skill_is_allowed():
    skill = SKILL.read_text(encoding="utf-8")
    assert "bounded procedure → Skill or deterministic implementation" in skill
    assert "Do not add an Agent loop because several steps exist." in skill


def test_et05_multi_agent_not_inherited():
    decision = load(MULTI)
    assert_decision(decision)
    assert decision["solution"]["selected_solution_form"] == "Workflow + Skills"
    assert "Multi-Agent" in decision["proof"]["not_required_now"]


# ---------------------------------------------------------------------------
# WAVE D — REPLACEMENT / FAILURE
# ---------------------------------------------------------------------------

def _execute_decision(decision: dict):
    cap = next(
        ref for ref in decision["capability_search"]["reused_capability_refs"]
        if ref["id"] == "compose_report"
    )
    assert cap == {"id": "compose_report", "version": "1.0.0"}
    _, adapter = make_stack()
    return adapter.execute(
        make_report_invocation(
            {"title": "Harness Swap", "sections": ["decision semantics only"]},
            invocation_id="inv_harness_swap",
            trace_id="tr_harness_swap",
        )
    )


def test_rt01_harness_facing_decision_replacement():
    original = load(COMPOSE)
    alternate = copy.deepcopy(original)
    alternate["status"] = "ALTERNATE_HARNESS_TEST_ONLY"
    alternate["solution"]["short_rationale"] = "Different producer, same bounded decision semantics."
    for decision in (original, alternate):
        assert_decision(decision)
        result = _execute_decision(decision)
        assert result.status == "success"


def test_rt02_model_provider_replacement():
    provider = AlternateProvider()
    runtime = Runtime(
        reasoner=LLMReasoner(provider),
        capabilities={"add": FakeCapability()},
        policy=AllowAllPolicy(),
        state_store=InMemoryStateStore(),
    )
    final = runtime.start(Goal("得到数字 42"))
    assert final.history[0].observation.data == 42
    assert provider.cursor == 2


def test_rt03_capability_implementation_replacement():
    _, adapter = registry_with(AlternateComposeReportCapability())
    result = adapter.execute(
        make_report_invocation(
            {"title": "Replace HOW", "sections": ["keep WHAT"]},
            invocation_id="inv_replace_how",
            trace_id="tr_replace_how",
        )
    )
    assert result.status == "success"
    assert result.artifacts[0].producer.capability_id == "compose_report"
    assert tuple(CapabilityDescriptor.__dataclass_fields__) == (
        "standard_version", "kind", "id", "extensions", "name", "description",
        "capability_version", "input_schema", "output_schema", "execution",
    )


def test_rt04_original_agent_absence():
    index = load(INDEX)
    harvested = next(e for e in index["entries"] if "Retrieval-gated memory" in e["summary"])
    assert harvested["authority_ref"]["anchor"] == "WAKU-A01"
    assert not (ROOT / "waku-agent").exists()
    assert not (ROOT / "waku_agent").exists()


def main():
    tests = [
        ("SA-01 architecture boundaries", test_sa01_architecture_boundaries),
        ("SA-02 duplicate responsibility", test_sa02_duplicate_responsibility),
        ("SA-03 replaceability", test_sa03_replaceability),
        ("SA-04 false claims", test_sa04_false_claims),
        ("IT-01 simple reuse", test_it01_simple_reuse),
        ("IT-02 fixed workflow", test_it02_fixed_workflow),
        ("IT-03 true agent", test_it03_true_agent),
        ("IT-04 Case01", test_it04_case01),
        ("IT-05 Waku harvest reuse", test_it05_waku_harvest_reuse),
        ("IT-06 failure attribution matrix", test_it06_failure_attribution_matrix),
        ("ET-01 Waku external Agent", test_et01_waku_agent_disposable),
        ("ET-02 LangGraph workflow bias", test_et02_langgraph_workflow_bias_check),
        ("ET-03 MCP boundary", test_et03_mcp_boundary),
        ("ET-04 simple Skill", test_et04_simple_skill_is_allowed),
        ("ET-05 Multi-Agent simplification", test_et05_multi_agent_not_inherited),
        ("RT-01 Harness-facing replacement", test_rt01_harness_facing_decision_replacement),
        ("RT-02 ModelProvider replacement", test_rt02_model_provider_replacement),
        ("RT-03 implementation replacement", test_rt03_capability_implementation_replacement),
        ("RT-04 original Agent absence", test_rt04_original_agent_absence),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"FAILED: {name} -> {type(exc).__name__}: {exc}")
    if failed:
        print(f"\n{len(failed)} TEST(S) FAILED: {failed}")
        raise SystemExit(1)
    print("\nALL CATALYST PLATFORM V0.1 PRE-MERGE TESTS PASSED")


if __name__ == "__main__":
    main()
