# Catalyst Platform

**Governed capability architecture for preserving organizational ability across replaceable AI implementations.**

> **Current product state:** **Minimum Operational V1**  
> **Operating mode after this release:** controlled real use; planned platform expansion is stopped.  
> **Start here:** [`CATALYST_OPERATIONAL_BASELINE_V1.md`](CATALYST_OPERATIONAL_BASELINE_V1.md)

Catalyst is built around one durable idea:

> **Preserve capability, not implementation privilege.**

Models, providers, Agents, Skills, Workflows, Harnesses, adapters, implementations, and the current Runtime may change. The organizational value above them — capability meaning, contracts, domain and enterprise meaning, evidence, evaluation knowledge, known limits, and evolution lineage — should survive when justified by evidence.

## What Catalyst is

Catalyst is a small capability-first operating architecture. It currently provides enough proven structure to:

```text
REAL NEED
→ RESPONSIBILITY / CAPABILITY NEED
→ DISCOVER EXISTING VALUE
→ REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD ONLY THE GAP
→ SELECT THE SIMPLEST VALID SOLUTION FORM
→ EXECUTE WHEN APPLICABLE
→ PRESERVE EVIDENCE
→ EVALUATE / ATTRIBUTE
→ REPAIR / REBUILD / REPLACE / ADOPT / RETIRE AS EVIDENCE JUSTIFIES
→ HARVEST DURABLE VALUE
→ REUSE
```

It is **not** a production-complete enterprise control plane, a universal Agent framework, or a feature race to own every RAG, Workflow, MCP, memory, policy, monitoring, or multi-agent mechanism.

## Current implementation map

```text
Catalyst Platform
├── ARCHITECTURE.md                 durable architecture semantics
├── PLATFORM_STANDARD_CORE_V0.1.md  current public contract slice
├── CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json
│                                    tiny navigation surface
├── platform_standard/              stable public coordination boundary
├── agent_runtime/                  one replaceable Runtime implementation
├── platform-harness/               replaceable Harness-side methods
├── enterprise_extensions/          current Extension evidence
├── assets/                         current harvested organizational assets
├── evidence/                       accepted execution/evaluation evidence
├── examples/                       reference execution + regression proofs
├── tests/                          Platform/Extension contract evidence
└── docs/                           governance, philosophy, and history map
```

`agent_runtime/**` is deliberately retained as the name of the current Runtime implementation. **It is not the identity of the product.** The product/repository identity is **Catalyst Platform**; any GitHub slug migration is administrative and must not force a Runtime/module rename.

## Quick start

Python 3.12 is the current CI reference.

```bash
python -m examples.run_minimal_loop
python -m examples.test_catalyst_operational_v1
python tests/test_platform_standard_core.py
python tests/test_capability_contract_conformance_pilot.py
python tests/test_enterprise_extension_pilot.py
```

The complete active regression loop is defined by:

```text
.github/workflows/ci.yml
```

## Current operating methods

The current replaceable Harness-side method set is intentionally small:

- [`agent-construction`](platform-harness/skills/agent-construction/SKILL.md) — understand the real need, search Capability value first, choose the simplest justified solution form.
- [`capability-benchmark-design`](platform-harness/skills/capability-benchmark-design/SKILL.md) — design user-capability benchmarks that distinguish desired behavior from shortcuts.
- [`capability-evaluation`](platform-harness/skills/capability-evaluation/SKILL.md) — run frozen capability cases, preserve evidence, and attribute failure to the owning layer.
- [`capability-optimization`](platform-harness/skills/capability-optimization/SKILL.md) — make evidence-governed repair/rebuild/replace/adopt decisions while preserving durable Capability value.

No Engine or Service is implied by these Skills.

## Authority / reading order

Different questions have different authorities. Do not turn one convenience document into a universal source of truth.

1. **Current whole-platform state / what to use now** → [`CATALYST_OPERATIONAL_BASELINE_V1.md`](CATALYST_OPERATIONAL_BASELINE_V1.md)
2. **Purpose, layers, boundaries, replacement rules** → [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. **Stable governing principles** → [`docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md`](docs/governance/MINIMUM_ARCHITECTURAL_FRAMEWORK_GOVERNING_BASELINE_V1_1_PART_A.md)
4. **Platform Standard Core v0.1 contract** → [`PLATFORM_STANDARD_CORE_V0.1.md`](PLATFORM_STANDARD_CORE_V0.1.md)
5. **Development/release workflow** → [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md)
6. **Accepted code truth** → GitHub `main` + active tests + CI
7. **Closed stages / old experiments / Case history** → [`docs/history/README.md`](docs/history/README.md)

A historical Stage Spec, Handoff, audit report, or Case branch does **not** define current implementation authorization merely because it exists.

## Operational rule

After Minimum Operational V1:

> **STOP planned platform pre-development.**

New platform work must come from real use or a concrete failure:

```text
USE
→ OBSERVE
→ ATTRIBUTE
→ identify the responsible boundary
→ search existing internal/external capability knowledge
→ make the smallest justified change
→ evaluate against the same responsibility/evidence boundary
→ preserve useful learning
→ USE AGAIN
```

Do not add a Registry, graph, monitoring layer, Workflow Engine, memory platform, Authority/Policy system, second Runtime, or new Core concept because it would make the architecture look more complete.
