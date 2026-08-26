# CATALYST PLATFORM ASSET CENSUS V0.1

> **Stage:** Catalyst Platform Integration V0.1
> **Mode:** READ-ONLY CENSUS RESULT
> **Functional implementation changes:** NONE
> **Case01 / Case02:** PAUSED
> **Purpose:** identify what already exists, where it lives, which responsibilities overlap, and what minimum integration gap remains before further Agent development.

---

## 1. Executive finding

Catalyst already contains most of the architectural pieces needed for a coherent lifecycle, but they are distributed across different branches and evidence surfaces.

The primary integration gap is **not absence of Runtime, Harness, Evaluation, Capability identity, or governance**.

It is:

```text
NO SINGLE MINIMUM ORGANIZATIONAL VISIBILITY LAYER
that lets Construction / Runtime / Evaluation / Harvest
refer back to the same Agent / Capability responsibility and evidence state.
```

Therefore the immediate next stage should consolidate identity/evidence references before adding new execution features.

---

## 2. Existing asset map

### 2.1 `main` — accepted Platform / Runtime baseline

Existing authoritative or evidence-backed assets include:

- `ARCHITECTURE.md` — system purpose, layer ownership, replacement/evolution rules;
- `docs/governance/**` — Minimum Architectural Framework governing baseline;
- `PLATFORM_STANDARD_CORE_V0.1.md` — Platform Standard normative slice;
- `platform_standard/models.py` — CapabilityDescriptor, Invocation, Result, ArtifactRef, TraceEvent;
- `platform_standard/registry.py` — in-memory descriptor registration / lookup for current Standard proof;
- `platform_standard/runtime_adapter.py` — current Standard-to-Runtime binding/translation boundary;
- `platform_standard/validation.py` — Platform contract validation;
- `agent_runtime/**` — accepted replaceable Runtime implementation;
- `enterprise_extensions/**` — Extension-first enterprise semantic evidence;
- active tests / CI / development workflow — implementation and governance evidence.

Existing capability identity surface already includes:

```text
capability id
capability version
name / description
public input schema
public output schema
portable execution declaration
Invocation capability id/version
Result / Artifact / Trace attribution
```

Important limitation:

`InMemoryDescriptorRegistry` explicitly stores Standard descriptors only and is not a production organizational Capability Registry.

---

### 2.2 `platform-harness` — replaceable Harness responsibility and implementation evidence

Existing assets include:

- Harness Capability Architecture Review;
- Minimum Harness Stage / Execution Authorization;
- Environment Infrastructure Stage / Execution Authorization;
- `minimum-harness-v0.1` evidence;
- `harness-v0.2-candidate` execution substrate;
- Harness infrastructure gap review;
- `skills/agent-construction/SKILL.md` replaceable Construction Method candidate.

Already-proven / established Harness responsibilities include:

```text
Session
Workspace boundary
Provider binding
Credential resolution
read / write / command / test
approval / execution policy
preflight
trace
bounded repair
```

Architectural method assets already include:

```text
UNDERSTAND before construction
Capability != Skill
Capability Search before new build
reuse / adapt / reconstruct / build-new ordering
Harness != Runtime
Harness is optional infrastructure
external Harnesses remain admissible
```

Current gap:

`agent-construction` remains a candidate and still requires integration repair so its Responsibility / Runtime Requirement / Evaluation Evidence handoff uses shared Catalyst meaning.

---

### 2.3 `case-01` — governed Agent construction / admission / professional evaluation evidence

Case01 already contains multiple distinct stages rather than one monolithic Agent history:

```text
01-b governed Agent definition
01-c governed local formation
01-d governed Agent admission / binding
01-e governed professional completion
methods
reference
```

Case01 has produced reusable evidence classes including:

- Agent identity / Candidate version / freeze lineage;
- Knowledge Revision identity and binding;
- professional responsibility decomposition;
- obligation / seam evidence;
- source-native evidence binding experiments;
- fail-closed behavior;
- Product Capability Evaluation Contract;
- frozen benchmark / public-private isolation;
- machine evaluation evidence;
- failure attribution;
- Harvest-oriented findings;
- targeted N+1 evolution evidence.

Important integration finding:

Case01 contains both **Agent-governance assets** and **Capability / Evaluation assets** that are valuable beyond BREA, but they currently remain difficult to discover from `main` or Harness without knowing Case01 history.

---

### 2.4 `case-02` — external Agent understanding / decomposition / selective capability harvesting evidence

Case02 is already structurally separated into:

```text
01-a Waku understanding
01-b selective capability harvesting
01-c full Agent evaluation
```

This branch contains reusable evidence for:

- understanding an unfamiliar complete Agent;
- Responsibility-first decomposition;
- capability asset cataloging;
- capability rediscovery from a later need;
- Catalyst-native reconstruction without rereading the original implementation;
- native external evaluation/release evidence reuse;
- memory / state / side-effect / tool-failure evaluation patterns;
- external-source provenance and pinning.

Important integration finding:

Case02 proves that Catalyst can preserve valuable capability independently from the source Agent implementation, but the resulting capability records are still Case-local rather than organization-visible.

---

## 3. Already-existing responsibilities that MUST NOT be rebuilt

The following concepts already exist at sufficient architectural/evidence level to prohibit a second competing implementation without new evidence:

### Runtime execution responsibility

Already owned by Runtime:

```text
execution lifecycle
state / certainty
cancel / timeout
recovery / reconciliation
capability execution mechanics
```

Do not create equivalent execution semantics inside Harness or Evaluation.

### Platform public Capability contract

Already owned by Platform Standard:

```text
stable id/version
public observable promise
Invocation / Result semantics
portable execution boundary
```

Do not create a second Capability identity system merely for Harvest.

### Binding / Conformance responsibility

Already distinct from Platform validation and Runtime execution validation.

Do not fold Binding qualification into Runtime internals.

### Harness execution substrate

Already separately proven on the `platform-harness` branch.

Do not rebuild file/command/test/approval/session infrastructure as part of Construction Method.

### Evaluation principles

Case01 already proves a minimal deterministic Evaluation path with:

```text
frozen target
frozen benchmark identity
public/private isolation
raw evidence
critical gates
failure attribution
Harvest-oriented interpretation
```

Do not create a second generic Evaluation engine during integration.

### Capability decomposition / Harvest concepts

Case02 and Harness Review already establish:

```text
Capability != Skill
Capability may have Record / Knowledge / Skill / Implementation / Evaluation / Lineage forms
Harvest requires evidence
Case-local implementation detail != new Capability identity
```

Do not create a new competing asset ontology.

---

## 4. Duplicated / fragmented reasoning currently visible

The same conceptual work currently appears in several places:

### Understanding / Responsibility

Appears in:

- Case01 Agent definition / professional responsibility work;
- Case02 Waku understanding / decomposition;
- Harness Architecture Review;
- `agent-construction` Skill;
- Evaluation responsibility maps.

**Integration action:** share Responsibility meaning; do not build an Understanding Engine.

### Capability representation

Appears as:

- Platform `CapabilityDescriptor`;
- Case-local capability records / catalogs;
- Harness conceptual Capability Asset Bundle;
- Evaluation PR/FN/SEAM/OBL identities.

**Integration action:** preserve existing authorities and create references between them; do not collapse them into one oversized universal schema.

### Evidence

Appears in:

- Runtime trace/result/artifact;
- contract/conformance tests;
- Case01 Evaluation results;
- Case02 reconstruction/evaluation evidence;
- Harness execution trace / test evidence;
- governance exact-SHA records.

**Integration action:** establish common evidence references / attribution to Agent + Capability identity; do not centralize all evidence bytes into one database.

### Evolution / replacement

Appears in:

- Architecture / Governing Baseline;
- Candidate version lineage;
- Capability implementation replacement rules;
- Harness replaceability;
- Evaluation repair / regression loops;
- Harvest recommendations.

**Integration action:** keep one shared replacement decision model and preserve implementation-specific execution separately.

---

## 5. Confirmed minimum integration gap

Phase I confirms the smallest missing cross-system capability is:

# **Organizational Capability Visibility + Shared Evidence Handoff**

Not a production Registry.

The minimum must let a future Harness or reviewer answer:

```text
1. What Agent responsibility is being served?
2. Which Capability identity / version is relevant?
3. What asset forms already exist?
4. Where is the authoritative implementation / knowledge / Skill / evidence?
5. What evidence currently supports or limits this Capability?
6. Where is it bound / used?
7. What is known to be replaceable?
8. What failed most recently, and which responsibility owned the failure?
```

If those questions are answerable, Catalyst can avoid a large class of duplicate construction without a Registry service.

---

## 6. Health / first-notice truth

Current system status:

```text
DETERMINISTIC FAILURE VISIBILITY
within a Stage / test / Evaluation / Runtime trace
= EXISTS

CROSS-SYSTEM FAILURE ATTRIBUTION
back to the same Capability asset
= PARTIAL / CASE-LOCAL

PROACTIVE CONTINUOUS HEALTH MONITORING
= DOES NOT EXIST
```

Therefore Catalyst currently cannot promise automatic first-notice for every degraded Capability.

The next integration proof should establish **event-driven evidence propagation when an observed failure occurs**:

```text
failure observed
→ Agent + Capability identified
→ owner classified
→ evidence attached / referenced
→ current limitation state visible
```

Only after real operational use demonstrates that delayed discovery is a material problem should background monitoring / health watches be considered.

---

## 7. External knowledge already absorbed without losing Catalyst identity

Existing platform work already uses external systems at different authority levels:

### Mechanism references

- Penguin Harness — Harness boundary / session / workspace / tools / approval / asset-aware construction;
- Codex / DeepSeek Harness — operational repo-development executor evidence;
- Inspect-style methods — frozen tasks, public/private scorer isolation, reproducible structured run concepts;
- Anthropic evaluation methods — task/trial/grader/infrastructure separation;
- LangSmith — run evidence feeding future regression datasets;
- OpenAI testing principles — test at actual responsibility boundary;
- Waku — native Agent mechanisms, state persistence, tool / side-effect evidence and source-Agent decomposition.

### Catalyst-owned meaning retained

Catalyst retains authority over:

```text
Agent governed identity / admission / execution responsibility
Capability semantic identity / public promise
Domain meaning
Enterprise meaning
Stage authorization
Evidence attribution
Lineage / bindings
Harvest / replacement decisions
Platform Standard evolution
```

External systems therefore contribute **HOW / mechanisms / evaluation patterns**, while Catalyst preserves **WHY / responsibility / organizational meaning / evidence / governance / evolution authority**.

This boundary is already present in Harness Architecture Review and Case01 Evaluation authorization; it should become explicit in the integrated Platform reading order.

---

## 8. Phase I verdict

```text
ASSET CENSUS
PASS

DUPLICATE-DEVELOPMENT RISK
REAL

CURRENT CAPABILITY IDENTITY / CONTRACT FOUNDATION
SUFFICIENT

CURRENT ORGANIZATION-WIDE CAPABILITY VISIBILITY
INSUFFICIENT

CURRENT REPLACEABILITY PRINCIPLE
STRONG / EVIDENCE-BACKED AT MULTIPLE BOUNDARIES

CURRENT AUTOMATIC FIRST-NOTICE HEALTH MONITORING
NOT IMPLEMENTED

NEW PRODUCTION REGISTRY REQUIRED NOW
NO

NEXT MINIMUM ACTION
DESIGN PHASE II MINIMAL CAPABILITY ASSET INDEX
+ PHASE III SHARED RESPONSIBILITY/EVIDENCE HANDOFF
```

---

## 9. Stop after census

No functional code, Runtime, Harness Core, Evaluation engine, Case Agent, Registry service, graph DB, or Platform Core object is modified by this census.

The next step requires review of this census before selecting the exact Phase II representation.
