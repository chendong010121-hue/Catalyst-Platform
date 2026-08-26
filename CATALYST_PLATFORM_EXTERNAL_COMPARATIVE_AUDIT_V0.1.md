# CATALYST PLATFORM — EXTERNAL COMPARATIVE AUDIT V0.1

> **Status:** RESEARCH / COMPARATIVE REVIEW
> **Implementation Authorization:** NO
> **Stage:** Catalyst Platform Integration V0.1
> **Purpose:** compare Catalyst's purpose, lifecycle, integration phases and proposed abstractions with mature external systems before authorizing any further integration implementation.
> **Decision rule:** reuse mature machinery where possible; adapt only where Catalyst purpose differs; build new only where the responsibility is genuinely Catalyst-specific and no simpler existing mechanism is sufficient.

---

## 0. Audit question

For every planned Catalyst addition ask:

```text
1. Does this responsibility already exist in Catalyst?
2. Does a mature external system already solve the mechanism well?
3. Can the external mechanism be reused directly without importing its ontology/authority?
4. If adaptation is required, what Catalyst-specific semantic difference requires it?
5. If new construction is proposed, why can neither existing Catalyst assets nor external mechanisms satisfy it?
6. Is the proposed owner/layer correct?
7. What is the minimum proof?
8. What is the STOP condition?
```

Allowed classifications:

```text
DIRECTLY LEARN / REUSE
ADAPT
CATALYST-SPECIFIC NEW BUILD
DO NOT BUILD
```

---

# 1. Overall finding

Catalyst should NOT become a new implementation of:

```text
Backstage
OpenTelemetry
LangSmith
Inspect AI
OpenAI Agents SDK
Anthropic agent patterns
MCP
Kubernetes control plane
```

These systems already provide mature solutions for important mechanism classes.

Catalyst's value is in combining selected mechanisms under a different organizational purpose:

```text
real need
→ responsibility
→ reusable Capability identity
→ choose the simplest valid solution form
→ governed construction / binding / execution
→ evidence / evaluation
→ preserve / replace / reuse organizational value
```

The defensible Catalyst-specific surface is therefore semantic/governance glue around reusable organizational capability, not another generic execution/evaluation/catalog framework.

---

# 2. Purpose-level comparison

## 2.1 Backstage — organizational visibility and discoverability

Backstage Software Catalog solves a mature problem very close to Catalyst's current visibility gap:

```text
software is distributed across repositories/tools
→ teams cannot find what exists / who owns it / what it depends on
→ source-controlled metadata is harvested into a searchable catalog
```

Relevant mature ideas:

- metadata remains near source code;
- the catalog references/ingests authoritative sources rather than replacing them;
- components/APIs/resources remain distinct entity kinds;
- relations allow ecosystem-level visibility;
- source owners maintain metadata through normal Git workflows;
- the catalog provides discovery/search, not implementation ownership.

### Classification for Catalyst

```text
DIRECTLY LEARN:
- repository-native metadata references
- authoritative-source ingestion rather than evidence duplication
- discovery/search separated from source ownership
- explicit relations
- lightweight entity status / metadata

ADAPT:
- catalog subject is Capability + its asset forms/evidence/bindings,
  not merely software Component/API/Resource
- Catalyst must preserve semantic Capability identity across Skill/Workflow/Agent/Service forms

DO NOT BUILD NOW:
- centralized catalog backend
- catalog REST service
- UI portal
- plugin ecosystem
- generalized entity graph
```

Implication: Phase II should begin as a repository-native Capability Asset Index, structurally inspired by catalog/source-of-truth patterns, not as a production Registry service.

---

## 2.2 OpenTelemetry — evidence transport and observability

OpenTelemetry already standardizes vendor-neutral generation/collection/export of:

```text
traces
metrics
logs
baggage/context
```

Relevant mature idea:

```text
instrument once at meaningful boundaries
→ preserve contextual correlation
→ export to replaceable observability backends
```

### Classification for Catalyst

```text
DIRECTLY LEARN:
- separate trace/log/metric signals
- context correlation across execution boundaries
- vendor-neutral telemetry semantics
- instrumentation is separate from analysis/alerting backend

ADAPT LATER IF JUSTIFIED:
- attach Catalyst Capability / solution identity as trace context/attributes
- use operational telemetry as one evidence source

DO NOT BUILD NOW:
- Catalyst-specific tracing protocol
- custom metrics/log transport
- observability backend
- continuous monitoring service before real operational need
```

Implication: Catalyst should not invent a competing observability system. Current TraceEvent can remain minimal; future production monitoring should preferentially interoperate with standard telemetry mechanisms.

---

# 3. Construction / solution-form comparison

## 3.1 Anthropic — simplest solution first, workflow vs agent distinction

Anthropic's production guidance distinguishes:

```text
Workflow
= predefined code path

Agent
= model dynamically directs process/tool use
```

and recommends increasing complexity only when simpler approaches fail.

Common patterns include:

```text
prompt chaining
routing
parallelization
orchestrator-workers
evaluator-optimizer
agent loop
```

They are composable implementation patterns rather than a required ontology.

### Classification for Catalyst

```text
DIRECTLY LEARN:
- simplest solution first
- workflow vs adaptive agent distinction
- composable reference patterns
- complexity must earn its cost

ADAPT:
- Catalyst starts from Capability responsibility and existing organizational assets before selecting a pattern
- solution form may also be Skill / service / deterministic implementation, not only workflow vs agent

DO NOT BUILD:
- Pattern Registry as Platform ontology
- mandatory Agent abstraction
- framework-specific construction architecture
```

Implication: the repaired Stage Spec's solution-form neutrality is supported by mature external practice.

---

## 3.2 MCP — keep context/resources/tools as replaceable integration primitives

MCP distinguishes server primitives such as:

```text
Prompts   — user-controlled
Resources — application-controlled context
Tools     — model-controlled actions
```

### Classification for Catalyst

```text
DIRECTLY LEARN:
- distinguish information/context from executable actions
- preserve control/authority semantics at tool boundaries
- use protocols/adapters for interoperability rather than hardwiring vendors

ADAPT IF A REAL CASE REQUIRES MCP:
- expose a Capability implementation through MCP while Catalyst retains Capability identity/evidence/governance

DO NOT BUILD NOW:
- Catalyst-native MCP clone
- universal tool protocol
- MCP as Platform Core requirement
```

Implication: external interoperability protocols should be Adapter-level options, not Catalyst ontology.

---

# 4. Evaluation / health comparison

## 4.1 Inspect AI — reproducible evaluation execution machinery

Inspect provides mature concepts for:

```text
Task / dataset
Agent/Solver
Scorer
Sandbox
Evaluation log
```

and preserves detailed evaluation logs for later analysis.

### Classification for Catalyst

```text
DIRECTLY LEARN / REUSE WHEN USEFUL:
- frozen evaluation identities
- structured run logs
- scorer separation
- sandboxed execution
- evaluator implementation can remain external

ADAPT:
- Catalyst evaluation output must map evidence back to Capability responsibility / known limits / Harvest decisions

DO NOT BUILD:
- second generic evaluation runner merely to own these mechanics
```

---

## 4.2 Anthropic eval guidance — evaluation by responsibility and failure source

Useful mature distinctions include:

```text
task
trial
trajectory
outcome
grader
evaluation harness
agent harness
```

and the need to distinguish benchmark/evaluator/infrastructure failures from Agent failures.

### Classification

```text
DIRECTLY LEARN:
- failure-source separation
- trajectory only when needed
- capability/regression evaluation distinction
- repeated trials for nondeterministic systems

ADAPT:
- evaluation is not the terminal product; it feeds Catalyst Capability evidence / reuse / replacement decisions
```

---

## 4.3 LangSmith — offline ↔ online evidence feedback loop

LangSmith separates:

```text
offline evaluation
→ curated datasets / reference outputs

online evaluation
→ production runs / traces / threads
```

and supports the loop:

```text
production trace / feedback
→ interesting failure
→ dataset example
→ offline regression
→ validate fix
→ redeploy
```

### Classification for Catalyst

```text
DIRECTLY LEARN:
- offline vs online evaluation distinction
- real traces become regression/evaluation assets
- feedback may attach to specific child runs
- dataset/evaluator versioning

ADAPT:
- Catalyst maps production evidence to stable Capability identity / solution binding / known limits
- health status must not be reduced to a single generic score

DO NOT BUILD NOW:
- live monitoring/evaluator service
- generic dataset platform
- alerting backend
```

Implication: the requested future ability to discover degradation quickly has a mature external pattern; Catalyst should later integrate operational evidence rather than invent a monitoring stack.

---

## 4.4 OpenAI Agents SDK testing — test the owner at the correct boundary

OpenAI's testing guidance explicitly separates:

```text
SDK/application-owned orchestration
→ deterministic provider-neutral test doubles

provider/network/sandbox-owned behavior
→ real integration boundary tests

model decision quality
→ evaluation
```

### Classification for Catalyst

```text
DIRECTLY LEARN:
- test only the responsibility owned by the boundary under test
- deterministic tests should not overclaim provider behavior
- external integration behavior needs real integration evidence

ADAPT:
- use the same rule across Platform Contract / Binding / Runtime / Capability behavior
```

This strongly supports Catalyst's existing separation:

```text
Platform Contract Validation
!= Binding/Conformance
!= Runtime Execution Validation
!= Product/Capability Evaluation
```

---

# 5. Platform evolution / extension comparison

## 5.1 Kubernetes — extension-first and declarative desired/current separation

Kubernetes provides mature lessons on extending a stable core:

```text
built-in stable API
+ extension mechanisms
+ custom resources/controllers where justified
```

It explicitly advises choosing between extending the core API and using a standalone service, and warns against using extension resources as arbitrary application/monitoring data storage.

The controller pattern also separates:

```text
desired state
from
observed/current state
```

### Classification for Catalyst

```text
DIRECTLY LEARN:
- stable core + explicit extension points
- do not modify Core for every local concept
- new resource/schema has operational cost and should be justified
- desired/declared contract and observed status should be conceptually distinct

ADAPT:
- Catalyst Extension-first governance remains its own architecture, but can use these mature extension design heuristics
- future Capability status may separate declared promise from observed evidence status

DO NOT BUILD NOW:
- generic controller/reconciliation engine
- Kubernetes-style CRD framework
- desired-state control plane
```

This supports Catalyst's existing `Extension First. Core Promotion Later.` rule.

---

# 6. Audit of planned Integration phases

## Phase II — Minimal Capability Asset Index

### External precedent
Strong: Backstage catalog/source-controlled metadata; package/service catalogs generally.

### Decision
**ADAPT**, not greenfield invention.

Use:

```text
repository-native metadata/reference
stable identity
source ownership
relations/references
searchable/discoverable shape
```

Catalyst-specific adaptation:

```text
Capability is semantic value across multiple solution/asset forms
evidence + lineage + bindings + known limits matter
```

Do NOT build service/UI/database.

---

## Phase III — Shared Responsibility / Evidence Handoff

### External precedent
Partial, distributed across:

- API/contract descriptors;
- evaluation task metadata;
- trace context;
- workflow input/output contracts;
- declarative resource spec/status separation.

No reviewed external project exactly owns Catalyst's semantic combination of:

```text
need/responsibility
+ Capability claim/reuse
+ solution-form decision
+ runtime requirements
+ evaluation evidence requirements
+ lineage
```

### Decision
**CATALYST-SPECIFIC ADAPTATION / SMALL NEW CONTRACT CANDIDATE**.

But new construction is allowed only as a minimal method-level handoff, not Platform Core schema.

It should borrow:

```text
small versionable records
references over copies
explicit spec vs observed evidence distinction
trace/context correlation
```

---

## Phase IV — Harness Construction Method

### External precedent
Strong: Anthropic agent/workflow selection, Penguin asset-aware Harness patterns, Codex/DeepSeek operational behavior, Skill procedures.

### Decision
**ADAPT EXISTING METHOD**, not build a new engine.

The existing `agent-construction` Skill is the correct current carrier.

Catalyst-specific adaptation:

```text
Capability Search before solution-form selection
reuse organizational evidence/lineage
Stage authorization
Catalyst conformance/evidence handoff
```

---

## Phase V — Cross-component Integration Proof

### External precedent
Strong: integration/contract testing, trace correlation, evaluation experiments, catalog relations.

### Decision
**DIRECTLY LEARN testing method + Catalyst-specific scenario**.

Do not build integration infrastructure first. Use current code/test surfaces and prove one chain.

---

## Phase VI — Case01 real validation

### External precedent
Strong principle: test methods against real workloads, not toy examples.

### Decision
**CATALYST-SPECIFIC VALIDATION CASE**, no new platform abstraction by default.

The Harness must be free to choose Skill / Workflow / Agent / other implementation based on need rather than historical BREA shape.

---

# 7. What is genuinely Catalyst-specific today

After comparison, these remain legitimate Catalyst-owned differentiators rather than generic infrastructure reinvention:

```text
1. Capability as reusable semantic organizational value across solution forms.

2. Separation between Capability public semantic promise and replaceable implementation HOW.

3. Domain and Enterprise meaning remain outside Runtime and do not automatically enter Platform Core.

4. Stage-based evidence/authorization prevents architecture findings from silently becoming implementation changes.

5. Evaluation evidence is interpreted toward preserve / reuse / replace / do-not-harvest decisions, not only score/regression.

6. External Agent/Skill/Workflow implementations remain admissible; Catalyst Harness is optional.

7. Capability lineage, evidence, bindings and replacement knowledge should survive implementation/provider/runtime/tool churn.
```

These are the places where Catalyst may need thin original contracts/methods.

They do NOT justify rebuilding commodity catalog, telemetry, orchestration or evaluation systems.

---

# 8. Strict anti-duplication rules resulting from this audit

Before any Phase II+ implementation:

```text
CATALOG / DISCOVERY NEED
→ check Backstage-like source-controlled catalog pattern first

TRACE / METRIC / LOG NEED
→ check OpenTelemetry compatibility first

AGENT / WORKFLOW DECISION
→ use simple composable pattern guidance first

TOOL / CONTEXT INTEROP
→ check MCP/existing Adapter mechanism first

EVALUATION RUNNER / LOGGING
→ check Inspect / existing Case evaluator first

ONLINE QUALITY MONITORING
→ check LangSmith-style trace/feedback loop or standard observability integration first

TEST BOUNDARY
→ deterministic owner-level tests + real integration tests before inventing new conformance machinery

NEW PLATFORM RESOURCE / CONTROL LOOP
→ apply extension-vs-standalone discipline before creating Core semantics
```

If a proposal cannot explain why these mature patterns are insufficient, classify it:

# **DO NOT BUILD**

---

# 9. Current recommendation

Do not authorize implementation yet.

The next audit pass should go one level deeper and produce, for each planned Phase II–V artifact:

```text
RESPONSIBILITY
EXISTING CATALYST ASSET
EXTERNAL MATURE ANALOGUE
DIRECT REUSEABLE PART
CATALYST-SPECIFIC DELTA
MINIMUM CHANGE
FORBIDDEN DUPLICATION
PROOF
STOP CONDITION
```

Only after this matrix is reviewed should Phase II receive implementation authorization.

---

# 10. Sources reviewed in V0.1

Authoritative/primary documentation reviewed includes:

- Backstage Software Catalog: Overview, System Model, Entity lifecycle / model extension docs;
- OpenTelemetry: documentation and signal model;
- Anthropic: Building Effective Agents; Demystifying Evals for AI Agents;
- LangSmith: Evaluation Concepts / Evaluation workflow / Observability;
- OpenAI Agents SDK: Testing guidance;
- Inspect AI: evaluation log/task/scoring documentation;
- Model Context Protocol: server primitive model (Prompts / Resources / Tools);
- Kubernetes: Custom Resources / extension guidance.

External documentation is evidence/reference, not Catalyst architecture authority.
