# CATALYST PLATFORM — INTEGRATION ARTIFACT DECISION MATRIX V0.1

> **Status:** RESEARCH / DESIGN REVIEW
> **Implementation Authorization:** NO
> **Phase II Authorization:** NO
> **Stage:** Catalyst Platform Integration V0.1
> **Purpose:** decide, artifact by artifact, what Catalyst should reuse, adapt, build minimally, or explicitly not build before any integration implementation begins.

---

# 0. Decision rule

Every proposed artifact or mechanism is classified as exactly one of:

```text
DIRECTLY REUSE / LEARN
ADAPT EXISTING
CATALYST-SPECIFIC MINIMUM ADDITION
DO NOT BUILD
```

`CATALYST-SPECIFIC MINIMUM ADDITION` is allowed only if all are true:

```text
- no existing Catalyst artifact already owns the responsibility;
- no mature external mechanism can satisfy it directly;
- the responsibility is required by the current integration proof;
- the addition remains thinner than introducing a new service/engine/registry;
- replacement and migration are explicit;
- proof and STOP condition are defined.
```

---

# 1. Internal assets that already exist and must be reused

## 1.1 Platform CapabilityDescriptor

Current Platform Standard already owns the public Capability promise:

```text
stable capability id
capability version
name / description
public input schema
public output schema
portable execution declaration
```

Decision:

**DIRECTLY REUSE.**

Do not add organizational evidence, mutable health, Harvest state, implementation history, or Case-specific reasoning into `CapabilityDescriptor` merely to make the integration index self-contained.

Reason:

The public WHAT and observed evidence/status have different change rates and authorities.

---

## 1.2 Case02 Waku Asset Catalog

Case02 already demonstrates a rich Case-local asset record with fields such as:

```text
asset_id
asset_name
asset_type
problem_solved
mechanism_summary
responsibility_boundary
inputs / outputs
state_semantics
dependencies
replaceability
reuse_preconditions
known_limits
source_evidence
source_commit
reconstruction_notes
classification
confidence
```

Decision:

**DIRECTLY LEARN / REUSE AS EVIDENCE DONOR.**

Do not promote this full Case-local shape into a universal Platform schema.

What it proves:

- small structured records can support rediscovery;
- source provenance can stay explicit;
- responsibility / limits / replacement knowledge are useful;
- a harvested asset can outlive the source Agent implementation.

What it does NOT prove:

- every Capability needs every field;
- this JSON shape is a Platform contract;
- a generic Capability Registry is required.

---

## 1.3 Case01 Evaluation output

Case01 already records:

```text
target identity
frozen evidence identity
per-case result
critical gates
failure attribution
responsibility evidence state
Harvest findings
explicit unproven boundaries
next material gap
```

Decision:

**DIRECTLY REUSE AS EVIDENCE MODEL DONOR.**

Do not duplicate this information into Capability metadata. The integration layer should reference the authoritative evaluation artifact.

---

## 1.4 Harness Construction Decision output

Current `agent-construction` Skill already defines a compact pre-implementation record:

```text
INPUT_KIND
REQUIRED_OUTCOME
TASK_CHARACTERIZATION
SELECTED_PATTERN
WHY_THIS_PATTERN
CURRENT_MECHANISM_CANDIDATE
REUSED_ASSETS
EXTERNAL_REFERENCES_IF_USED
ASSUMPTIONS
MATERIAL_RISKS
EVIDENCE_NEEDED_TO_PROVE_SUCCESS
EXPLICITLY_NOT_NEEDED_NOW
STOP_CONDITION
```

Decision:

**ADAPT EXISTING.**

This should become the first shared Construction → Evaluation handoff surface rather than creating a new Handoff Engine or a second universal manifest.

---

# 2. External mechanisms that constrain our design

## 2.1 Backstage-style catalog pattern

Directly learn:

```text
metadata/reference close to source
source control remains authoritative
catalog/index exists for discovery, not ownership
directional relations only when useful
GitOps-style change history
```

Catalyst adaptation:

```text
catalog subject = semantic Capability and its asset/evidence references
not only deployable software component/API/resource
```

Do not copy:

```text
catalog backend
DB
REST API
portal UI
plugin ecosystem
generic graph
```

---

## 2.2 Kubernetes spec/status separation

Directly learn:

```text
declared/desired contract
!=
observed/current status
```

Catalyst implication:

```text
Capability public semantic promise
!=
latest evaluation / operational health evidence
```

Therefore:

- do not add mutable `health`, `score`, or current evaluation status to the stable Platform CapabilityDescriptor;
- evidence status should be separate and reference the Capability identity/version;
- no controller/reconciliation engine is justified now.

---

## 2.3 OpenTelemetry identity/context and semantic-convention discipline

Directly learn:

```text
signals correlate through stable resource/context identity
semantic attributes are reused before new ones are invented
new conventions should be prototyped before standardization
telemetry transport is separate from analysis/alerting
```

Catalyst implication:

- future runtime/production evidence should carry Capability + solution/binding identity as contextual attributes when justified;
- do not invent a Catalyst trace/metric/log transport;
- do not standardize new telemetry attributes during this integration Stage.

---

## 2.4 SLSA / in-toto provenance

Directly learn:

```text
subject identity
builder/producer identity
source / resolved dependencies
run/build definition
byproducts/evidence references
verifiable provenance is separate from the artifact itself
```

Catalyst implication:

- lineage/provenance should prefer resolvable source refs, exact commits and digests where useful;
- construction evidence should identify which Harness/builder and source inputs produced a Candidate when the risk justifies it;
- do not invent a custom cryptographic attestation framework;
- do not require SLSA/in-toto for ordinary V0.1 records.

---

## 2.5 Inspect AI evaluation machinery

Directly learn:

```text
Task = dataset + solver/agent + scorer + optional sandbox/setup
frozen/identified task configuration
structured eval log
external Agent bridge
scorer separation
sandbox/approval as execution concerns
```

Catalyst implication:

- Evaluation execution machinery remains replaceable;
- an external Agent does not need to be rebuilt in Catalyst to be evaluated;
- do not create a second generic evaluation runner/service.

---

## 2.6 LangSmith offline/online evaluation lifecycle

Directly learn:

```text
offline curated evaluation
online production trace evaluation
real failures become regression examples
fixes validated offline before redeployment
```

Catalyst implication:

- future Capability health can consume online evidence without creating a Catalyst monitoring stack;
- current integration only needs identity/evidence correlation, not continuous online evaluation.

---

## 2.7 OpenAI Agents SDK boundary testing

Directly learn:

```text
test orchestration with deterministic test doubles
real provider/network/sandbox behavior requires real integration evidence
model decision quality belongs to evaluation
```

Catalyst implication:

Keep separate:

```text
Platform Contract Validation
Binding / Conformance
Runtime Execution Validation
Capability / Product Evaluation
```

Do not invent one all-purpose conformance framework.

---

## 2.8 MCP primitive/control separation

Directly learn:

```text
Prompt / instruction
Resource / context
Tool / action
```

with different control semantics.

Catalyst implication:

- future tool/context interoperability may use MCP through an Adapter;
- do not treat MCP Tool identity as Catalyst Capability identity;
- do not build a Catalyst-native tool protocol.

---

## 2.9 Anthropic simplest-sufficient solution selection

Directly learn:

```text
workflow for predefined paths
agent for dynamic model-directed paths
increase complexity only when justified
patterns are composable techniques, not ontology
```

Catalyst adaptation:

```text
Need
→ Responsibility / Capability need
→ search existing organizational assets
→ choose simplest valid solution form
```

Do not privilege Agent / Workflow / Skill as the default form.

---

# 3. Phase II artifact decisions — Capability visibility

## II-A. Persistent Capability Asset Index

### Responsibility

Let humans/Harness discover what organizational Capability value already exists and where its authoritative artifacts/evidence live.

### Existing Catalyst assets

- Platform `CapabilityDescriptor` for admitted public contracts;
- Case02 Asset Catalog for Case-local harvested knowledge;
- Case01 Evaluation artifacts;
- repository / branch / exact SHA governance.

### External analogue

Backstage source-controlled metadata/catalog pattern.

### Decision

# **ADAPT EXISTING — ONE THIN REPOSITORY-NATIVE INDEX CANDIDATE**

The first implementation, if later authorized, should be no more than one small human-readable/machine-readable repository-native index that references authoritative artifacts.

It must NOT duplicate full Descriptor / Evaluation / Skill / source evidence content.

Minimum conceptual entries should be closer to:

```text
capability_ref / stable label
authority_ref
semantic/problem summary
asset_refs[]
evidence_refs[]
lineage/source refs[]
known-limits ref when available
current realization/binding refs when available
```

The exact file format is NOT authorized yet.

### Forbidden duplication

```text
new Capability public contract schema
new evidence database
new asset graph
copying Case artifacts into the index
mutable health embedded in CapabilityDescriptor
```

### Proof

A future Harness task can find at least one `main` Capability, one Case01 evidence asset and one Case02 harvested asset without prior knowledge of their branch/path.

### STOP

Once rediscovery works from one thin index, stop. Do not add service/UI/database/search engine.

---

## II-B. Capability Health / Current Status object

### Responsibility

Know whether current evidence suggests a Capability/binding is healthy, limited, unproven or failing.

### External analogue

Kubernetes spec/status; LangSmith online/offline evaluation; OpenTelemetry correlation.

### Decision

# **DO NOT BUILD NOW**

Reason:

Current Cases have evaluation and failure attribution, but Catalyst has no repeated production health-monitoring requirement yet.

V0.1 should only expose `evidence_refs` / `known_limits` references. Do not invent a mutable health state machine.

Future trigger:

Repeated real-use evidence shows humans/Harness cannot safely decide reuse/replacement without a current status summary.

---

## II-C. Dependency / Impact Graph

### Decision

# **DO NOT BUILD**

Start with explicit references only. A graph is justified only if real dependency-impact questions become difficult to answer from the thin index.

Backstage demonstrates relations are valuable, but that does not mean Catalyst needs a generalized graph at current scale.

---

## II-D. Ownership / Team metadata

### Decision

# **PARK / DO NOT ADD TO V0.1 INDEX BY DEFAULT**

Backstage ownership is useful organizationally, but Catalyst currently has no accepted Enterprise ownership/profile model. Do not smuggle future Enterprise semantics into a generic Capability index.

Add later only from a real Enterprise need through the proper Enterprise/Extension path.

---

# 4. Phase III artifact decisions — Shared Responsibility / Evidence Handoff

## III-A. New standalone `ResponsibilityEvidenceBrief` Platform object

### Decision

# **DO NOT BUILD**

Current evidence does not justify a second universal object.

The responsibility can first be satisfied by adapting the existing Harness Construction Decision output.

---

## III-B. Adapted Construction Decision / Evaluation Handoff

### Responsibility

Construction and Evaluation should agree on what problem/responsibility is being solved without independently reverse-engineering the implementation.

### Existing Catalyst asset

`agent-construction` Skill Construction Decision output.

### External analogues

- small versioned metadata records;
- Inspect Task metadata;
- OpenTelemetry contextual identity;
- Kubernetes declared vs observed separation.

### Decision

# **ADAPT EXISTING**

Candidate additions to the current Construction Decision:

```text
PURPOSE / DELIVERY CONTEXT
RESPONSIBILITIES
CAPABILITY_NEEDED / REUSED_CAPABILITY_REFS
SELECTED_SOLUTION_FORM
DOMAIN / ENTERPRISE CONTEXT WHEN MATERIAL
KNOWLEDGE_BOUNDARY
ACTION_BOUNDARY
STATE_HORIZON
RUNTIME_EXECUTION_REQUIREMENTS
LINEAGE / SOURCE REFS
EVIDENCE_REQUIREMENTS
MATERIAL_UNCERTAINTIES
NOT_REQUIRED_NOW
```

Evaluation consumes this record plus its own private benchmark/rubric/evidence setup.

The record is method-level and replaceable. It is not Platform Core.

### Proof

One Evaluation can derive its responsibility/evidence targets from the Construction Decision without re-reading implementation internals to discover the intended product responsibility.

### STOP

If this works, do not create a new shared-contract service/schema.

---

## III-C. Evidence Event / Evidence Ledger service

### Decision

# **DO NOT BUILD**

Use Git artifacts, exact refs, evaluation reports/results and existing trace/evidence surfaces for the integration proof.

Future runtime evidence may integrate OpenTelemetry; provenance may use SLSA/in-toto concepts when risk warrants.

---

# 5. Phase IV artifact decisions — Harness Construction Method

## IV-A. New Construction Engine

### Decision

# **DO NOT BUILD**

The current Harness execution substrate already exists. The missing value is procedural method, not another engine.

---

## IV-B. Update existing `agent-construction` Skill

### Decision

# **ADAPT EXISTING — REQUIRED CANDIDATE AFTER AUTHORIZATION**

Minimum repair only:

```text
UNDERSTAND before characterize/build
material uncertainty → targeted clarification
Capability Search > asset-form search
solution-form neutrality
reuse/adapt/compose/reconstruct/build ordering
reference patterns are non-exhaustive
Harness != Runtime
Runtime requirements are output, not Harness-owned semantics
Evaluation evidence requirements are output
remove Case01-specific generic procedure
```

### External learning

- Anthropic simplest-sufficient pattern choice;
- Penguin/Codex/DeepSeek Harness execution experience;
- MCP control-boundary discipline for actions/context;
- existing Catalyst governance/authorization.

### Proof

Three falsification inputs:

```text
1. raw user need
2. existing Skill/Workflow
3. complete external Agent
```

The method should be able to conclude different solution forms and should reuse existing assets when available.

### STOP

After the method makes stable bounded decisions for all three classes, stop. Do not expand Harness Core.

---

## IV-C. Pattern Registry / Mechanism Registry

### Decision

# **DO NOT BUILD**

Patterns remain replaceable reference knowledge inside procedural guidance.

---

## IV-D. Capability Search Engine

### Decision

# **DO NOT BUILD**

For V0.1, Capability Search means searching the thin repository-native index + authoritative refs + explicitly permitted external sources.

Only repeated scale/performance evidence can justify a search service later.

---

# 6. Phase V artifact decisions — Cross-component proof

## V-A. New Integration Test Framework

### Decision

# **DO NOT BUILD**

Use current tests, Harness trace/evidence and Case evaluation patterns.

---

## V-B. One minimum end-to-end identity/evidence proof

### Responsibility

Prove that independent parts form one system without sharing implementation internals.

### Decision

# **CATALYST-SPECIFIC MINIMUM PROOF SCENARIO**

No new general infrastructure is justified.

Preferred scenario characteristics:

```text
reuse an already-known simple Capability / solution
Harness first discovers it rather than rebuilding it
Construction Decision records Capability/ref + solution form + evidence need
current Platform/Adapter/Runtime executes when applicable
trace/result evidence retains identity
Evaluation/verification attaches result back to the same Capability/ref
one deliberately injected boundary failure is attributed to the correct owner
```

A pre-existing simple Platform capability such as the existing second-capability portability example is preferable to inventing a new business feature solely for this proof.

### Direct external learning

- OpenAI boundary-specific testing;
- Inspect structured evaluation/logging;
- OpenTelemetry correlation principle;
- SLSA/in-toto provenance references where exact build/source identity is relevant.

### STOP

Pass one valid chain and one correctly attributed failure, then stop. Do not create orchestration/control-plane infrastructure.

---

# 7. Phase VI decision — Case01

Phase VI remains a real-use validation Case, not a platform artifact.

Decision:

# **NO NEW PLATFORM ABSTRACTION BY DEFAULT**

After integration proof, give the real product requirement to the repaired Harness method.

It must:

```text
understand need
search existing Capability/evidence assets
choose the simplest valid solution form
reuse Case01 knowledge/evaluation evidence where valid
construct only what remains missing
execute/evaluate/harvest
```

Historical BREA shape does not force the new solution to be an Agent.

---

# 8. Net-new surface after this audit

If all recommendations hold, the entire integration may require only these persistent changes:

```text
1. ONE thin repository-native Capability visibility index
   (new, but only as references/discovery; format still undecided)

2. ONE repaired existing `agent-construction` Skill
   (adapt existing, not new engine)

3. Existing Construction Decision output extended with shared responsibility/evidence fields
   (adapt existing; no standalone handoff object)

4. ONE minimum cross-component proof/test artifact
   (no new framework)

5. Documentation/Stage updates required to record accepted boundaries
```

Everything else remains existing infrastructure or external/reusable machinery.

No new:

```text
Registry service
DB
Graph
Control Plane
Monitoring system
Telemetry protocol
Evaluation service
Harvest service
Understanding engine
Construction engine
Pattern registry
Mechanism registry
Capability search service
Workflow engine
Runtime rewrite
```

---

# 9. Anti-duplication gate before implementation authorization

For every future diff, reviewer must be able to answer:

```text
A. Which existing Catalyst artifact was checked first?
B. Which external mature analogue was checked?
C. Why is direct reuse insufficient?
D. What exact Catalyst-specific delta remains?
E. Why is this the smallest persistent surface?
F. What existing object/service is explicitly NOT being duplicated?
G. How is the new piece replaceable?
H. What proves it?
I. What causes us to STOP?
```

If any answer is missing:

# **DO NOT IMPLEMENT**

---

# 10. Comparative references used

Primary reference families reviewed:

```text
Backstage Software Catalog
Kubernetes Custom Resources / spec-status separation
OpenTelemetry Resources / Semantic Conventions
SLSA Provenance / in-toto Attestation
Inspect AI Tasks / Agent Bridge / Eval Logs
LangSmith offline/online Evaluation
OpenAI Agents SDK Testing
Model Context Protocol server primitives
Anthropic agent/workflow construction guidance
```

External systems are mechanism references. Catalyst governance and accepted repository evidence remain architecture authority.
