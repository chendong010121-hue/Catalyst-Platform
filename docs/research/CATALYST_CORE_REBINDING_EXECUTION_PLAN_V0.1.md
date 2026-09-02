# Catalyst Core Rebinding Execution Plan V0.1

> **Status:** EXECUTION-READY STRATEGIC PLAN / NOT YET STARTED  
> **Type:** Engineering validation plan derived from Catalyst Core Reference Research  
> **Date:** 2026-09-02  
> **Platform base:** `Catalyst-Platform@65f634d57231e17015969f632f9639136dd5d537`  
> **Research reference:** `docs/research/CATALYST_CORE_REFERENCE_RESEARCH_V0.1.md`  
> **Lab reference:** `Catalyst-Test-Lab@12bb9844ad1aea62a214d26e1b46db4e1abc4cf5` on `real-use/hru-01-native-understanding-complete-path-v0.1`  
> **Proof-03:** READY / PARKED  
> **Current Harness mutation:** NOT AUTHORIZED BY THIS DOCUMENT  
> **Current Proof-03 execution:** NOT AUTHORIZED BY THIS DOCUMENT  
> **Platform pre-development:** remains STOP unless a bounded real finding justifies work  
> **Primary purpose:** prove that Stable WHAT can survive real HOW replacement at decreasing rebinding cost, then resume the Waku Learn → Harvest → Recompose line with a deliberately selected HOW.

---

# 0. Why this plan exists

Catalyst has reached a point where further local optimization of the current Harness would risk obscuring the product's higher-order objective.

The next engineering work should therefore no longer be organized around:

```text
make current Harness better
```

or:

```text
finish Waku by any means necessary
```

The next engineering work should be organized around the central Catalyst property:

> **A stable organizational Capability should remain usable when its execution HOW changes, without forcing the organization to redefine, relearn, or completely re-evaluate what it already proved.**

The engineering program therefore has two independent but eventually converging validation lines:

```text
LINE A — REBIND
Stable WHAT → different HOW → same Evaluation → measured rebinding cost

LINE B — LEARN / HARVEST
External HOW → understand → evaluate → harvest → Stable WHAT → enter LINE A
```

The immediate priority is LINE A.

Reason:

- Catalyst already has an accepted Platform Standard and a working Runtime HOW.
- Catalyst already has Capability identity, Invocation, Result, Artifact, Evaluation, evidence and evolution methods.
- Catalyst does not yet have a real second-HOW proof.
- Without second-HOW evidence, `Replaceable HOW` remains an architectural commitment rather than a verified platform property.
- Waku/HRU has already demonstrated that blindly improving one HOW can become expensive.

The plan therefore validates the highest-value missing property first.

---

# 1. Governing engineering thesis

The implementation program must preserve this rule:

```text
WHAT owns the target.
HOW is a candidate implementation.
Evaluation judges whether HOW satisfies WHAT.
Evidence records the result.
Evolution chooses repair / adapt / compose / rebuild / replace / external adopt.
```

The system must not invert into:

```text
current HOW exists
→ redefine WHAT around current HOW
```

or:

```text
new HOW differs
→ expand Platform Core until new HOW looks like old HOW
```

The central test is not interface similarity.

It is preservation of meaning and obligations across implementation change.

---

# 2. What must remain frozen across HOW replacement

A cross-HOW proof is only meaningful if the durable target is frozen before implementation work begins.

For each selected Capability, freeze at minimum:

```text
Capability identity
Capability version
required user outcome
public/shared input semantics
public/shared output semantics
material status semantics
material side-effect semantics, when present
Artifact semantics, when present
Domain meaning, when present
Enterprise meaning, when present
Evidence obligations
Evaluation criteria / benchmark
known limits already accepted
failure semantics that belong to the Capability boundary
```

These are the comparison baseline.

If a new HOW requires these to change materially, the default interpretation is NOT automatically:

```text
update the Capability so the HOW can fit
```

Instead ask:

```text
Is the HOW incompatible?
Is the existing WHAT over-specified?
Was an implementation assumption mistakenly promoted into WHAT?
Is this actually a new Capability version?
```

Only after attribution may a WHAT change be considered.

---

# 3. What is explicitly allowed to vary

A candidate HOW may differ completely in:

```text
Agent architecture
Harness architecture
Runtime architecture
reasoning loop
workflow/graph structure
Provider/model
prompting strategy
Tool implementation
tool transport
MCP/A2A use
context management
checkpointing
retry mechanism
sandbox
storage
session model
internal schema
internal error classes
source structure
language/framework
process topology
local/remote deployment
```

The new HOW does not need to implement current Catalyst internal types such as:

```text
Reasoner
StateStore
CapabilityExecutor
NativeToolsV2
C1/A1
C2
```

unless the selected binding deliberately chooses to reuse them.

The stable requirement is externally observable conformance to the frozen WHAT.

---

# 4. Current strategic state before execution

## 4.1 Platform

Current Platform is treated as:

```text
Catalyst Minimum Operational V1
Platform pre-development = STOP
```

No new Platform layer is authorized merely to support this experiment.

Current relevant assets already exist:

```text
platform_standard/**
CapabilityDescriptor / Invocation / Result / Artifact / Trace semantics
RuntimeAdapter precedent
Capability Contract conformance precedent
Capability Evaluation method
Capability Benchmark Design method
Capability Optimization method
execution provenance ideas
organizational assets / lineage
```

## 4.2 Lab

Current Waku HRU line is frozen at:

```text
Proof-03 execution identity:
12bb9844ad1aea62a214d26e1b46db4e1abc4cf5

semantic execution identity:
a8858a17d6dca948b7291fbf10f17f398cf15beb

frozen Waku:
8328f567ab52d07921445cb40feed23cbc5ea2ad
```

Status:

```text
READY / PARKED
```

No Proof-03 execution occurs before the strategic rebinding line is deliberately revisited.

## 4.3 Local DeepSeek Harness readiness

User-reported current condition:

```text
DeepSeek Harness is already deployed locally and can be used when Cross-HOW Proof-01 begins.
```

This is an operational readiness input, not yet independently verified evidence.

At Proof-01 start, perform only the minimum needed identity/environment confirmation necessary to execute the selected bounded experiment.

Do not turn local environment inspection into a new platform project.

---

# 5. Program overview

The complete execution sequence is:

```text
R0  Core Reference Research                         DONE
R1  Freeze first Stable WHAT                       NEXT
R2  Cross-HOW Rebinding Proof-01                   DeepSeek Harness
R3  Measure Rebinding Cost #1
R4  Harvest only demonstrated conformance knowledge
R5  Cross-HOW Rebinding Proof-02                   second genuinely different HOW
R6  Measure Rebinding Cost #2
R7  Compare Cost #1 vs Cost #2 and reassess Waku Learn HOW
R8  Execute selected Waku native-understanding HOW
R9  Independent semantic review → Harvest → Source Cut
R10 Recompose / build related new Agent or other solution form
R11 Measure Second-use Cost and move toward a real Enterprise Decision Unit
```

Each stage has an explicit STOP condition.

No stage automatically authorizes the next mutation.

---

# 6. R0 — Catalyst Core Reference Research

Status:

```text
DONE
```

Artifact:

```text
docs/research/CATALYST_CORE_REFERENCE_RESEARCH_V0.1.md
```

Purpose:

- establish external architectural precedents;
- distinguish innovation from established software-engineering practice;
- classify current Catalyst modules;
- identify WHAT/HOW leakage risks;
- define the bidirectional Learn/Harvest and Rebind model;
- identify Rebinding Cost and Second-use Cost as critical validation metrics.

R0 does not authorize code changes.

---

# 7. R1 — Freeze the first Stable WHAT

## 7.1 Selected initial Capability

Recommended first target:

```text
compose_report@1.0.0
```

Reason:

- simple enough that Harness complexity does not dominate;
- already represented by Platform Standard objects;
- already has current Runtime reference implementation;
- already has Standard Invocation / Result behavior;
- already has conformance tests;
- can expose whether HOW replacement works without mixing in Waku reverse engineering.

The point is NOT to prove that report generation is commercially important.

The point is to prove the portability mechanism on a controlled but real Platform Capability.

## 7.2 R1 deliverable

Create a bounded freeze record containing only existing authority/reference material:

```text
Capability ID/version
frozen descriptor
input semantics
output semantics
Artifact semantics
status semantics
current known limits
existing Evaluation / conformance checks
current accepted HOW A identity
```

Prefer references to current authority over copying or inventing a second Capability schema.

## 7.3 R1 forbidden work

Do not:

```text
create HOW Registry
create Rebinding Engine
create Universal Harness interface
create new Platform ontology
expand Platform Standard fields for hypothetical future systems
rewrite compose_report merely to make DeepSeek Harness easier
```

## 7.4 R1 PASS

PASS when the experiment has a stable target that can be compared before and after HOW replacement without ambiguity.

STOP if freezing the target reveals that the existing Capability boundary is itself materially unclear.

If that occurs, return for architecture review before any second HOW work.

---

# 8. R2 — Cross-HOW Rebinding Proof-01

## 8.1 Purpose

Prove the minimum claim:

> The same frozen Catalyst Capability can be executed through a genuinely different external HOW while preserving its WHAT and Evaluation boundary.

## 8.2 HOW A

```text
Current Catalyst Runtime / current accepted Platform binding
```

This is the baseline.

Do not modify HOW A during Proof-01 unless a new material bug in the baseline itself is independently demonstrated.

## 8.3 HOW B

Recommended:

```text
DeepSeek Harness
```

Reasons:

- already available locally;
- architecturally distinct from current Catalyst Runtime;
- designed around replaceable plugins/components;
- therefore a meaningful cross-HOW test rather than a shallow Provider swap.

## 8.4 The binding rule

New work should live at the narrowest implementation boundary possible.

Conceptually:

```text
compose_report@1.0.0
        ↓
Platform Standard semantics
        ↓
DeepSeek-Harness-specific binding/mapping
        ↓
DeepSeek Harness execution
        ↓
normalize result/evidence
        ↓
existing Evaluation
```

Do not force DeepSeek Harness to emulate current `agent_runtime` internals.

## 8.5 Questions the binding must answer

Only what the frozen WHAT actually needs, for example:

```text
How does a Standard Invocation enter this HOW?
How is the target responsibility presented?
How is success represented?
How is known terminal failure represented?
How is unresolved/uncertain execution represented if materially relevant?
How is output mapped back to Standard Result?
How are Artifacts mapped if produced?
What evidence is available to support Evaluation?
What HOW identity/provenance facts must be recorded?
```

Do not answer unrelated questions merely because DeepSeek Harness supports them.

## 8.6 Proof-01 success conditions

Target conditions:

```text
Capability identity materially changed      = NO
Capability version changed                  = NO
Platform Standard contract changed          = NO
Domain meaning changed                      = NO
Enterprise meaning changed                  = NO
Evaluation rewritten                        = NO
Benchmark rewritten                         = NO
Current Catalyst Runtime modified            = NO
DeepSeek Harness source modified             = ideally NO
New HOW-specific Binding                     = YES
Same frozen user outcome                     = PASS
Same Evaluation boundary                     = PASS
Execution HOW provenance                     = explicit
```

## 8.7 Proof-01 acceptable failure

A failed Proof-01 is valuable when it produces bounded evidence showing one of:

```text
WHAT is not actually portable
current Platform Standard leaks Runtime assumptions
DeepSeek Harness cannot satisfy required obligation
binding seam is insufficient
Evaluation is accidentally HOW-specific
Artifact/evidence semantics are too coupled to current HOW
```

Failure must be attributed before modification.

Do not automatically expand Platform Core.

---

# 9. R3 — Measure Rebinding Cost #1

Proof-01 is incomplete without measuring cost.

Record at minimum:

```text
calendar elapsed time
active engineering time, when reasonably measurable
files added
files modified
lines added/modified
Platform Standard files touched
Capability files touched
Domain files touched
Enterprise files touched
Evaluation files changed
benchmark files changed
current Runtime files changed
external HOW source files changed
binding-specific files added
configuration files added
new assumptions discovered
new conformance obligations discovered
existing obligations reused
existing evidence reused
new evidence required
manual reasoning / review steps required
```

Derive:

```text
REBINDING_COST_01
```

No single numeric score is required initially.

A structured factual record is sufficient.

The important question is whether later proofs become cheaper on the same dimensions.

---

# 10. R4 — Harvest only demonstrated conformance knowledge

After Proof-01, examine what had to be learned for HOW B to satisfy the frozen WHAT.

Potential reusable material may include:

```text
mapping obligations
status semantics
minimum provenance facts
Artifact mapping obligations
execution certainty rules, where relevant
evidence normalization rules
forbidden coupling patterns
```

Do NOT immediately create a new Platform subsystem.

First classify each finding:

```text
CAPABILITY-SPECIFIC
HOW-SPECIFIC
PLATFORM-STABLE
EVALUATION-SPECIFIC
EXPERIMENT-ONLY
```

Only knowledge demonstrated by the real proof may be considered for future reuse.

The preferred first output is a small reference/checklist/test pattern, not a new Engine/Registry/Service.

---

# 11. R5 — Cross-HOW Rebinding Proof-02

## 11.1 Purpose

Prove that Proof-01 did not merely create a DeepSeek-specific adaptation pattern.

Choose a second HOW that is architecturally different from both:

```text
current Catalyst Runtime
DeepSeek Harness
```

Recommended candidate when access/integration is practical:

```text
Codex App Server / Codex Harness boundary
```

The important property is architectural difference, not vendor brand.

## 11.2 Frozen WHAT

Reuse the same frozen Capability target from R1 unless there is a documented reason to use a second equally simple Capability.

Do not weaken the target to make Proof-02 easier.

## 11.3 Reuse requirement

Attempt to reuse the conformance knowledge discovered in R4.

Record which obligations transfer directly and which do not.

## 11.4 R5 PASS

PASS requires another genuinely different HOW to satisfy the same frozen WHAT / Evaluation boundary with bounded new binding work.

The experiment should actively detect whether R4 accidentally encoded DeepSeek-Harness assumptions.

---

# 12. R6 — Measure Rebinding Cost #2

Record the same dimensions as R3.

Produce:

```text
REBINDING_COST_02
```

The central strategic test is:

```text
Cost #2 < Cost #1
```

not necessarily on every dimension, but materially in total discovery / mapping / revalidation effort.

If Cost #2 is not lower, determine why.

Possible interpretations:

```text
conformance knowledge was not reusable
Stable WHAT is too implementation-coupled
binding pattern is too framework-specific
Evaluation contains hidden HOW assumptions
second HOW has legitimately different capability/risk semantics
organization did not preserve enough migration knowledge from Proof-01
```

Do not fabricate improvement merely to satisfy the thesis.

A failure to reduce cost is a direct challenge to the Catalyst value proposition and should be preserved as such.

---

# 13. R7 — Strategic comparison and Waku HOW selection

Only after at least one real cross-HOW proof should the project return to the Waku native-learning path.

At this point, compare candidate Waku Learn HOWs.

Potential candidates include:

```text
current parked Proof-03 HOW
DeepSeek Harness
Codex Harness / App Server path
specialized repository-understanding pipeline
repo-graph/retrieval-assisted method
human + AI hybrid
other external mature system
```

Selection criteria should include:

```text
ability to satisfy the exact Waku understanding obligations
source/evidence traceability
uncertainty preservation
cost
latency
model/context efficiency
implementation complexity
reusability
replacement cost
new Platform coupling required
```

Sunk cost is not a selection criterion.

Current Proof-03 gets no permanent privilege simply because significant engineering effort has already been invested.

Likewise, DeepSeek Harness or Codex gets no privilege merely because they are external mature products.

Choose the simplest valid HOW that best satisfies the frozen learning responsibility.

---

# 14. R8 — Execute selected Waku native-understanding HOW

## 14.1 Stable Waku WHAT

Preserve the currently established HRU understanding target unless strategic review explicitly changes it:

```text
frozen Waku source identity
20 investigation obligations
source-relative evidence
SOURCE_PROVEN / DOC_STATED / INFERRED / UNPROVEN classification
explicit uncertainty
independent native understanding
no reference answer available to executing model
no premature Harvest/new-Agent design in the understanding result
```

This is the target.

HOW is replaceable.

## 14.2 Existing Proof-03

Current prepared execution identity remains parked until selected.

If current HOW wins the selection:

```text
unpark Proof-03
perform normal bounded execution
```

If another HOW wins:

```text
preserve Proof-03 as a prepared but superseded candidate
bind the same Waku WHAT to the selected HOW
```

Do not erase historical engineering investment.

Its lineage remains useful evidence of first-adoption cost and architectural learning.

---

# 15. R9 — Independent semantic review → Harvest → Source Cut

If native Waku understanding passes:

```text
independent semantic review
→ compare understanding quality against accepted obligations/reference evidence
→ accept/reject understanding
```

Only after acceptance:

```text
HARVEST
```

Harvest should extract durable responsibilities/knowledge, not source implementation privilege.

Then enforce:

```text
SOURCE CUT
```

The next design activity must not depend on reopening Waku source merely for convenience unless a new explicit evidence question requires it.

This proves that organizational value survived source-container removal.

---

# 16. R10 — Recompose a new related solution

The original HRU objective resumes here.

Start from:

```text
new real need
→ responsibility definition
→ search harvested Catalyst value
→ REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD ONLY GAP
```

Do not pre-decide that the output must be an Agent.

Valid solution forms may include:

```text
Skill
deterministic implementation
Workflow
Agent
Service
hybrid composition
external system adoption
```

The purpose is to prove that harvested WHAT materially reduces creation cost for a new related capability.

---

# 17. R11 — Measure Second-use Cost

Record the second-use cost of consuming harvested organizational value.

Suggested dimensions:

```text
time to identify reusable value
amount of Waku/source rereading required
amount of new architecture reasoning required
amount of new code required
evaluation reuse
known-limit reuse
migration/evolution knowledge reuse
number of decisions avoided because organizational knowledge already existed
```

Produce:

```text
SECOND_USE_COST_01
```

Compare against first-adoption cost.

The target is not a predetermined percentage.

The target is credible evidence that organizational learning reduced future work.

---

# 18. Only after R11 — move toward a real Enterprise Decision Unit

The long-term product proof is not report composition or Waku reverse engineering.

The product proof is a real Decision Unit in which:

```text
Domain meaning
Enterprise meaning
Business Action semantics
Evidence requirements
risk / authority constraints
Capability Evaluation
```

remain durable while execution HOW evolves.

This is where vendor-switching cost, organizational forgetting cost and revalidation cost become business metrics rather than architecture metrics.

Do not prematurely build universal Enterprise infrastructure before this bounded real-use need appears.

---

# 19. Program metrics

Three strategic metrics govern the overall program.

## T1 — Time to First Validated Capability

```text
real need
→ validated usable Capability
```

Measures how quickly Catalyst turns a need into proven organizational value.

## T2 — Rebinding Cost

```text
same WHAT
HOW A → HOW B
→ same Evaluation PASS
```

This is the primary metric of the immediate program.

## T3 — Second-use Cost

```text
existing harvested value
→ second Agent / workflow / Enterprise / HOW use
```

Measures whether organizational learning compounds.

Long-term Catalyst value requires T2 and T3 to decline as reusable knowledge accumulates.

---

# 20. Decision framework for every future failure

When a proof fails, classify before mutation.

```text
1. WHAT defect?
2. Binding defect?
3. HOW implementation defect?
4. HOW incompatible with required obligation?
5. Evaluation defect?
6. Evidence/provenance defect?
7. environment/deployment defect?
8. experiment-only instrumentation defect?
```

Then apply:

```text
REUSE
→ ADAPT
→ COMPOSE
→ LOCAL REPLACE
→ REBUILD COMPONENT
→ RECOMPOSE
→ REPLACE SUBSYSTEM
→ EXTERNAL ADOPT / ADAPT
→ RETIRE
```

Choose based on total evolution and future rebinding cost, not code-change size alone.

---

# 21. Global anti-overengineering rules

The following are explicitly NOT authorized by this plan unless a real proof demonstrates a material missing responsibility:

```text
HOW Registry
HOW Manager
Universal Harness API
Universal Runtime API
Rebinding Engine
Conformance Engine
Capability dependency graph
new Control Plane
new Workflow Engine
new generic Evidence Service
new universal telemetry format
new generic Enterprise SDK
new generic Domain SDK
new replacement C2 system
new Harness solely because current Harness is imperfect
```

Prefer external mature HOW when it already solves the execution responsibility well.

Catalyst should become thinner in replaceable machinery and richer in durable organizational knowledge.

---

# 22. External-system reuse policy

Prefer mature existing infrastructure for lower-level HOW responsibilities.

Examples of legitimate external candidates include:

```text
DeepSeek Harness / Cordis       — Harness internal composition
Codex App Server                — rich Harness protocol boundary
MCP                             — tool/data interoperability
A2A                             — agent interoperability
LangGraph / Temporal            — durable execution when required
OpenTelemetry GenAI             — low-level execution observability where useful
specialized repo-understanding  — repository learning HOW
```

External systems are:

```text
implementation candidates
knowledge sources
mechanism references
```

They are not automatically Catalyst architecture authority.

---

# 23. What success would mean after R6

If two distinct external HOWs can execute the same frozen Capability while:

```text
Platform Standard remains unchanged
Capability identity remains unchanged
Evaluation remains reusable
Core Runtime remains untouched
new work stays mostly binding/configuration-specific
Rebinding Cost declines
```

then Catalyst may claim initial empirical support for:

```text
REPLACEABLE HOW
```

This would still NOT prove full organizational continuity.

It would prove the lower half of the thesis.

R8–R11 then test the upper learning/harvest/reuse half.

---

# 24. What success would mean after R11

If Catalyst can:

```text
learn from Waku or another external system
→ harvest stable responsibility knowledge
→ remove dependence on source container
→ reuse that knowledge in a related new solution
→ bind the resulting capability to replaceable HOW
→ demonstrate lower second-use cost
```

then the full bidirectional thesis has meaningful empirical support:

```text
HOW → LEARN/HARVEST → WHAT → REBIND → HOW
```

That is the intended Catalyst core loop.

---

# 25. Failure interpretation

The program is useful even if the thesis fails.

Examples:

### If cross-HOW binding requires repeated Platform changes

Interpretation:

```text
Stable coordination boundary is not actually stable enough
or WHAT currently leaks implementation assumptions
```

### If Evaluation must be rewritten for each HOW

Interpretation:

```text
Evaluation is implementation-specific rather than capability-specific
```

### If HOW #2 costs as much as HOW #1

Interpretation:

```text
organization has not yet captured reusable conformance/migration knowledge
```

### If Waku Harvest does not reduce second-use cost

Interpretation:

```text
Harvested asset is not operationally reusable
or learning cost exceeds downstream value
```

These are core product findings, not embarrassing test failures.

Preserve them.

---

# 26. Relationship to Proof-03

Proof-03 remains intentionally preserved.

```text
Execution identity:
12bb9844ad1aea62a214d26e1b46db4e1abc4cf5

Status:
READY / PARKED
```

This plan does not invalidate it.

It changes its role from:

```text
default next step of Catalyst
```

to:

```text
one prepared candidate HOW for the Waku Learn responsibility
```

After R7 it may be:

```text
SELECTED
SUPERSEDED
KEPT AS REFERENCE
```

according to evidence.

---

# 27. Initial operational starting point

When the user explicitly starts execution, begin at:

```text
R1 — Freeze compose_report@1.0.0 WHAT
```

Do not begin by modifying DeepSeek Harness.

Do not begin by running Waku.

Do not begin by changing Platform Standard.

After R1 acceptance, proceed to:

```text
R2 — DeepSeek Harness Cross-HOW Rebinding Proof-01
```

At R2 start:

1. verify the local DeepSeek Harness identity/version/environment only as needed;
2. inspect its supported execution/binding surfaces;
3. choose the thinnest binding path;
4. freeze expected file/change boundaries before mutation;
5. implement one bounded candidate;
6. execute the same Capability Evaluation;
7. collect cost/evidence;
8. STOP for independent review.

---

# 28. Required evidence discipline

Every cross-HOW proof should preserve enough evidence to answer:

```text
What WHAT was frozen?
What HOW A was used?
What HOW B was used?
What changed?
What did not change?
What Evaluation was reused?
Did the user outcome remain satisfied?
What assumptions were newly discovered?
What did rebinding cost?
```

Do not require every HOW to emit the same internal trace shape.

Normalize only the evidence facts needed by the frozen Evaluation/Capability boundary.

---

# 29. Architecture checkpoint after each proof

After R2 and R5, perform a short read-only architecture review before any promotion.

Questions:

```text
Did HOW assumptions leak upward?
Did Platform Standard grow unnecessarily?
Did Evaluation remain independent?
Did the binding stay HOW-local?
Did evidence remain sufficient?
Did we create a new generic abstraction without second-system proof?
Did rebinding cost move in the right direction?
```

If no material blocker exists:

```text
STOP architecture work
continue next real proof
```

---

# 30. Promotion rules

No experiment-local binding automatically becomes Platform Core.

A mechanism may be promoted only after evidence shows a durable responsibility that:

```text
is shared across multiple real HOWs or Capabilities
cannot remain safely local
has a clear owner
has evidence that duplication/fragmentation is now materially harmful
```

Promotion should preserve:

```text
minimum complete responsibility
not maximum generality
```

---

# 31. Long-term desired operating state

The desired mature Catalyst operating loop is:

```text
REAL NEED
    ↓
identify Stable WHAT
    ↓
search organizational assets + external HOW candidates
    ↓
select simplest candidate
    ↓
conform / bind
    ↓
RUN
    ↓
Evidence
    ↓
Evaluation
    ↓
PASS -------------------------------┐
 │                                  │
 │ preserve lineage / known limits  │
 │                                  │
 └──────────────────────────────────┘

FAIL
 ↓
attribute owner
 ↓
repair / adapt / compose / replace / adopt
 ↓
rebind
 ↓
RUN AGAIN

External mature system
 ↓
learn / decompose / evaluate
 ↓
harvest durable value
 ↓
organizational assets
 ↓
future Capability construction / rebinding
```

The loop should gradually reduce dependence on any specific AI execution machinery.

---

# 32. Economic interpretation

The long-term value proposition is:

```text
Catalyst Value
≈
Durable Organizational WHAT
× Evaluation/Evidence Quality
× Reusability
÷ Rebinding Cost
```

The engineering program should therefore not optimize mainly for:

```text
number of built-in Agents
number of built-in Harness features
number of Runtime abstractions
number of supported Providers
```

It should optimize for:

```text
how much proven organizational meaning survives change
how quickly a new HOW can be validated
how much prior Evaluation can be reused
how much known-limit/migration knowledge can be reused
how much cheaper the second use becomes
```

---

# 33. Program stop / rethink conditions

Pause and reconsider the thesis if repeated evidence shows one or more of:

```text
Stable WHAT must be materially rewritten for each real HOW
Evaluation portability is consistently impossible
new HOW adoption repeatedly requires deep Core rewrites
Rebinding Cost does not decline after multiple attempts
Harvested knowledge does not reduce second-use cost
organizational semantics cannot be separated from implementation semantics at useful granularity
```

Do not continue adding layers merely to protect the theory.

A strategic hypothesis must remain falsifiable.

---

# 34. Current final status

```text
CATALYST CORE REFERENCE RESEARCH
= RECORDED

CROSS-HOW REBINDING PROGRAM
= EXECUTION-READY

R0
= DONE

R1
= READY TO START ON EXPLICIT USER COMMAND

DEEPSEEK HARNESS
= USER-REPORTED LOCAL DEPLOYMENT AVAILABLE
= verify minimally at R2 start

PROOF-03
= READY / PARKED

CURRENT HARNESS MODIFICATION
= NO

CURRENT PLATFORM EXPANSION
= NO
```

The immediate next executable task, when explicitly started, is:

> **R1 — freeze `compose_report@1.0.0` as the first cross-HOW Stable WHAT baseline.**

After R1 review:

> **R2 — bind that unchanged WHAT to the locally available DeepSeek Harness and perform Cross-HOW Rebinding Proof-01.**

Then STOP for evidence review and Rebinding Cost measurement before generalizing anything.
