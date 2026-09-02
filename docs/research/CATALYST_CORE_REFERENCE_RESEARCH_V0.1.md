# Catalyst Core Reference Research V0.1

> **Status:** RESEARCH CANDIDATE / LONG-TERM REFERENCE  
> **Type:** Non-Governing Strategic & Architecture Research  
> **Date:** 2026-09-02  
> **Platform reference:** `Catalyst-Platform@65f634d57231e17015969f632f9639136dd5d537`  
> **Lab reference:** `Catalyst-Test-Lab@12bb9844ad1aea62a214d26e1b46db4e1abc4cf5` on `real-use/hru-01-native-understanding-complete-path-v0.1`  
> **Frozen Waku reference:** `ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad`  
> **Implementation Authorization:** NO  
> **Architecture Change Authorization:** NO  
> **Proof-03 status:** READY / PARKED — do not execute merely because this research exists.  
> **Authority:** research/reference only; subordinate to `ARCHITECTURE.md`, `CATALYST_OPERATIONAL_BASELINE_V1.md`, `PLATFORM_STANDARD_CORE_V0.1.md`, accepted governing baselines, current GitHub truth, and explicit bounded user authorization.

---

# 0. Why this document exists

Catalyst entered a strategic pause during the HRU-01 Waku learning experiment.

The pause was not triggered by rejection of the current Runtime, Harness, Waku-learning hypothesis, or prior engineering work. It was triggered by a higher-order question:

> **How can Catalyst ensure that all execution machinery — including Harnesses, Runtimes, Agents, Providers, models, tools, transports, and external systems — can be replaced, rebound, and put back into productive use quickly without forcing the organization to relearn and revalidate everything it already proved?**

This question is more important than whether one Harness can learn Waku efficiently.

Waku learning remains useful, but it is one instance of a broader design philosophy:

```text
External HOW
    ↓ understand / evaluate / harvest
Stable WHAT
    ↓ select / conform / bind
New HOW
    ↓ run / evidence / evaluate
Stable WHAT enriched by experience
```

The long-term Catalyst thesis is therefore not merely:

```text
learn another Agent quickly
```

or:

```text
build a better Harness
```

but rather:

> **Preserve organizational capability across rapid AI implementation change, and make rebinding to new execution HOW increasingly cheap.**

This document records the strategic reasoning, current module interpretation, external architectural precedents, research analogues, feasibility assessment, innovation hypothesis, risks, and future validation criteria that emerged from this pause.

It intentionally does **not** prescribe implementation work.

---

# 1. Strategic thesis

## 1.1 The central object is Capability / Responsibility, not software

Catalyst should treat the durable organizational object as the stable responsibility or Capability that must survive implementation change.

Potentially durable material includes:

```text
required outcome / goal
Capability / Responsibility identity
Domain meaning
Enterprise meaning
public or shared obligations
input / output semantics
material side-effect semantics
evidence obligations
Evaluation / benchmark knowledge
known limits
failure-attribution knowledge
compatibility / migration knowledge
Evolution Lineage
real-use history
reuse history
```

Potentially replaceable HOW includes:

```text
Agent
Skill
Workflow
prompt
Harness
Runtime
Provider
model
tool implementation
MCP server
A2A agent
API
SDK
framework
sandbox
storage implementation
retrieval implementation
repository-understanding mechanism
source code
UI
CI system
```

The distinction is not philosophical decoration. It is the economic mechanism Catalyst is trying to create.

If implementation changes repeatedly destroy or invalidate the organization’s accumulated Capability meaning, Evidence, Evaluation, known limits, or migration knowledge, Catalyst has failed even if each new implementation works technically.

---

## 1.2 Stable WHAT / Replaceable HOW is a bidirectional loop

The full Catalyst model is not a one-way adapter pattern.

It has two directions.

### Direction A — REBIND

```text
Stable WHAT
    ↓ execution requirements
candidate HOW
    ↓ binding / mapping
conformance
    ↓
RUN
    ↓
Evidence
    ↓
Evaluation
    ↓
accept / reject / repair / replace / recompose
```

### Direction B — LEARN / HARVEST

```text
External mature system / human practice / project experience
    ↓
UNDERSTAND
    ↓
DECOMPOSE responsibility from implementation
    ↓
EVIDENCE
    ↓
EVALUATE
    ↓
HARVEST only durable value
    ↓
Stable WHAT / organizational knowledge
```

These are not separate philosophies.

They are opposite directions across the same boundary:

```text
HOW ──Learn/Harvest──→ WHAT ──Rebind──→ HOW
```

This is the conceptual center of Catalyst.

---

# 2. Why the Waku / HRU pause became strategically important

## 2.1 Original HRU goal

The HRU-01 hypothesis was:

> Can Catalyst turn understanding of an existing external Agent into durable organizational capability knowledge that materially reduces the cost of designing and building a related Agent later?

The intended lifecycle was:

```text
Preparation
→ deep Waku learning
→ Harvest
→ source cutoff
→ isolated new-Agent design
→ bounded build
→ Evaluation
→ human use
→ closure / promotion decision
```

This remains conceptually valid.

However, implementation exposed a broader issue.

---

## 2.2 What actually happened

The attempt to make Catalyst — not Codex — perform native Waku understanding forced many assumptions in the current execution HOW to become observable.

Across repeated real runs, the work surfaced issues including:

```text
Codex understanding Waku != Catalyst understanding Waku
model-visible task contract completeness
frozen source identity binding
real C2 proof versus hard-coded evidence
Provider availability / credential binding
Provider attempt timeout
Provider retry ownership
logical model call versus physical Provider attempt
run wall-clock semantics
ContextProjection behavior
C1/A1 historical reduction
C2 model-assisted compaction
final-output capacity
finish_reason semantics
cumulative Tool-count semantics
failure attribution
semantic execution identity
proof execution identity
source-operation accounting
run evidence preservation
```

Several early “safety” numbers were later shown by real execution to be functioning as implicit expected task-length controls:

```text
short Provider timeout
finite total wall
8K final output
Tool64 cumulative limit
```

Each individual repair was evidence-driven and locally justified.

The strategic problem is that, taken together, the sequence revealed how much work was required to make one particular execution HOW satisfy one real task.

That raised the higher-order question:

> If the next Harness, Runtime, or Agent requires another long sequence of assumption discovery and local repair, is Catalyst truly delivering Replaceable HOW?

---

## 2.3 The key lesson from the first adoption cost

The Waku/HRU experience should not be interpreted as wasted work.

It is better understood as **first-adoption conformance discovery cost**.

The experiment made previously implicit responsibilities explicit:

```text
normal completion semantics
Provider attempt semantics
retry ownership
output truncation semantics
context ownership
Tool behavior
execution certainty
source containment
evidence availability
failure ownership
```

The value of this first cost depends on whether it makes future adoption cheaper.

If the same responsibilities must be rediscovered manually for every new HOW, Catalyst does not compound organizational learning.

If the first run creates reusable conformance knowledge, evaluation assets, migration knowledge, and clearer stable boundaries, the cost can become an investment.

---

# 3. Current Catalyst module interpretation

This section records the strategic classification developed during the pause.

The classification is responsibility-based, not filename-based.

## 3.1 Classification categories

```text
STABLE WHAT
    meaning or obligation expected to survive implementation change

STABLE COORDINATION BOUNDARY
    public / shared semantic objects through which independently evolving parts coordinate

BINDING / CONFORMANCE SEAM
    implementation-specific mapping between Stable WHAT and one candidate HOW

REPLACEABLE HOW
    current working mechanism that may be replaced wholesale

REUSABLE EVIDENCE / EVALUATION ASSET
    evidence or judging knowledge that should be usable across multiple HOWs

EXPERIMENT-ONLY / PROOF INSTRUMENTATION
    machinery created for one bounded experiment; no automatic promotion
```

---

## 3.2 `ARCHITECTURE.md`

Classification:

```text
STABLE WHAT / ARCHITECTURE RESPONSIBILITY AUTHORITY
```

It correctly defines:

```text
Capability = stable WHAT
Platform Standard = stable coordination boundary
Runtime = replaceable execution HOW
Domain = professional / industry meaning
Enterprise = organization-specific meaning
Evaluation = independent judgment of evidence
external systems = legitimate HOW candidates
```

The strongest current architectural commitment is not that Catalyst owns a specific Runtime, but that upper-layer durable meaning should not need to be rewritten merely because the Runtime changes.

Important caution:

```text
architecture commitment != cross-HOW empirical proof
```

The commitment is strong; the decisive second-HOW evidence is still missing.

---

## 3.3 `CATALYST_OPERATIONAL_BASELINE_V1.md`

Classification:

```text
CURRENT-STATE AUTHORITY
```

It is neither WHAT nor HOW. It answers what is currently accepted and active.

This separation is crucial because Catalyst now contains:

```text
current accepted Platform
historical branches
rejected candidates
HRU experiments
reference implementations
```

and branch existence must not imply current authority.

---

## 3.4 `platform_standard/**`

Classification:

```text
STABLE COORDINATION BOUNDARY
```

Current durable objects include:

```text
CapabilityDescriptor
Invocation
Result
ArtifactRef
TraceEvent
Extensions
```

This layer is strategically important because it does **not** require upper layers to know:

```text
Reasoner classes
Agent loop classes
Provider APIs
ContextProjection algorithms
C1/A1/C2
Tool-loop internals
Prompt implementation
```

Current Standard semantics such as:

```text
success
failure
unresolved
```

are good examples of stable semantics that can survive HOW change.

---

## 3.5 `platform_standard/extensions.py`

Classification:

```text
STABLE EVOLUTION SEAM
```

The extension-first rule is one of the strongest current protections against accidental HOW leakage into Core.

A Harness-specific feature should not automatically become a Platform field.

Future compatibility should allow:

```text
common stable obligations
+
HOW-specific optional richness
```

without reducing every HOW to a lowest common denominator.

---

## 3.6 `platform_standard/registry.py`

Classification:

```text
Capability identity/version resolution responsibility = potentially durable need
current InMemoryDescriptorRegistry = reference HOW
```

Catalyst should not confuse the need to resolve Capability identity with the current in-memory implementation.

Future resolution may use files, databases, catalogs, services, search, or other mechanisms without changing Capability meaning.

---

## 3.7 `platform_standard/runtime_adapter.py`

Classification:

```text
Binding / Conformance responsibility = stable responsibility
current RuntimeAdapter implementation = Catalyst-Runtime-specific HOW
```

This is the most important existing seam for future cross-HOW proof.

Current strengths:

```text
(capability_id, version) -> implementation binding remains adapter-local
maps semantics rather than Runtime exception class names
success / failure / unresolved are normalized
current direct-binding schema equivalence is explicitly non-universal
future mapping adapters may use different internal schemas with explicit mapping/conformance evidence
```

The strategic lesson is to generalize the **pattern**, not necessarily the current class.

A future Codex/DeepSeek/LangGraph binding should not be forced to implement the current Catalyst Runtime API.

---

## 3.8 `agent_runtime/contracts/**`

Classification:

```text
CURRENT RUNTIME INTERNAL CONTRACTS
REPLACEABLE HOW
NOT PLATFORM STABLE WHAT
```

Names such as:

```text
Reasoner
ModelProvider
CapabilityExecutor
Policy
StateStore
```

must not be mistaken for universal Catalyst requirements.

A replacement Runtime may have none of these types.

The stable requirement is the behavior needed by the Capability boundary, not the internal class topology.

---

## 3.9 `agent_runtime/runtime.py`

Classification:

```text
CURRENT EXECUTION HOW
```

The implementation has produced valuable architectural learning around:

```text
PendingExecution
execution identity
execution certainty
cancel
explicit reconcile
no unsafe automatic replay
exception != proof of non-execution
timeout != did-not-execute
```

The durable asset is the obligation/lesson, not the Python Runtime implementation.

A future Runtime may satisfy these responsibilities differently, or may not need all of them for a bounded Capability.

---

## 3.10 `agent_runtime/core.py`

Classification:

```text
CURRENT AGENT LOOP HOW
```

It is one implementation of reasoning/execution control.

It should not become Catalyst identity.

---

## 3.11 `agent_runtime/native_tools_v2.py`

Classification:

```text
CURRENT HARNESS / MODEL-TOOL INTERACTION HOW
```

Its current behavior around model turns, tool-call batches, protocol validation, and natural final response may be good and mature.

That does not make NativeToolsV2 a universal requirement for new HOWs.

---

## 3.12 `agent_runtime/context_projection.py`, C1/A1, C2

Classification:

```text
CURRENT CONTEXT-MANAGEMENT HOW
```

Durable lessons include:

```text
canonical execution evidence != active model context
historical content may be reduced/retired
critical evidence, uncertainty, and reread locators should remain recoverable
context management is a Harness responsibility when long-running model/tool loops are used
```

Non-durable implementation details include:

```text
specific C1/A1 revision
specific C2 seven-field checkpoint
specific compaction prompt
specific trigger constant
specific Provider/model used for compaction
```

C2 explicitly remains candidate-local model-assisted context-compaction HOW.

---

## 3.13 Provider adapters

Classification:

```text
PROVIDER-SPECIFIC HOW
```

`DeepSeekModelProvider` is valuable because it preserves visible physical-attempt semantics and isolates provider mapping.

The durable principle is:

```text
provider differences should remain outside Capability meaning
attempt / failure facts must be observable when Evaluation requires them
```

not:

```text
DeepSeek API shape is Catalyst contract
```

---

## 3.14 Enterprise / Domain

Classification:

```text
Enterprise responsibility = Stable WHAT category
Domain responsibility = Stable WHAT category
current implementations = deliberately partial
```

Current Enterprise support provides an architectural home and an identity extension example; it does not prove production enterprise semantics.

Current Domain meaning is architectural and demonstrated through bounded pilots, not through a universal Domain SDK.

This is healthy: architecturally recognized responsibility does not automatically authorize implementation.

---

## 3.15 `assets/**`

Classification:

```text
DURABLE ORGANIZATIONAL VALUE
```

This is potentially one of Catalyst’s most differentiated layers.

The asset rule is strong:

> Preserve the smallest durable value; preserve provenance; reference authority rather than copying historical containers.

Assets need not all become Platform Capabilities.

They may preserve bounded:

```text
mechanism knowledge
safety knowledge
Evaluation knowledge
migration knowledge
Domain knowledge
Enterprise mapping
workflow/method knowledge
```

---

## 3.16 `WAKU_RETRIEVAL_GATED_MEMORY_V0.1.json`

Classification:

```text
STRONG PRECEDENT FOR TRUE STABLE ORGANIZATIONAL WHAT
```

It preserves a responsibility and portable obligations while explicitly removing privilege from:

```text
original Waku gate
prompt
model
memory store
Agent Runtime
```

This is a concrete example of the desired outcome of Harvest.

---

## 3.17 Capability Visibility Index

Classification:

```text
Discoverability responsibility = durable need
current JSON Visibility Index = navigation HOW
```

The index correctly declares that it is not a Registry, health system, dependency graph, or source of truth.

Future discoverability may use other mechanisms.

---

## 3.18 `platform-harness/skills/**`

Classification:

```text
REUSABLE ORGANIZATIONAL METHODS
current Skill representation = replaceable method HOW
```

Important examples:

```text
agent-construction
capability-benchmark-design
capability-evaluation
capability-optimization
```

These methods embody valuable decision knowledge, but they must not become mandatory Platform objects.

The method may evolve or be replaced while the underlying responsibility remains.

---

## 3.19 `lab_ops/**`

Classification:

```text
LAB / OPERATIONAL HOW
```

Useful durable ideas exist inside it:

```text
execution provenance
run identity
Evidence recording
independent evaluation
provider/config ownership facts
```

but current file schemas, CLI shape, credential paths, and run packages are Lab implementation details.

External Harnesses should not be forced to reproduce Lab file structures.

---

## 3.20 `evidence/**`, tests, CI

Classification depends on what is being tested.

```text
Capability benchmark / contract / conformance knowledge
    → reusable Evidence/Evaluation asset

Runtime implementation regression
    → current HOW asset

GitHub Actions workflow
    → CI HOW

immutable accepted evidence
    → organizational lineage / proof
```

The purpose is to preserve what was proven, not to force all future HOWs to reproduce historical proof machinery.

---

## 3.21 `experiments/**`

Classification:

```text
EXPERIMENT-ONLY BY DEFAULT
```

A successful experiment may yield durable:

```text
responsibility knowledge
failure semantics
portable mechanism knowledge
Evaluation obligations
known limits
```

but the experiment folder, runner, prompt, budget, proof launcher, and file topology receive no automatic promotion.

---

# 4. The external architecture lineage behind Catalyst

Catalyst’s current thesis is not isolated. It sits at the intersection of several mature software and organizational traditions.

The novelty should therefore not be claimed at the level of individual techniques.

---

## 4.1 Hexagonal Architecture / Ports & Adapters

Alistair Cockburn’s Hexagonal Architecture (2005) formalized the idea that an application should be isolated from external devices and infrastructure through ports and adapters, so different drivers and driven systems can be replaced without rewriting the core application.

Reference:

- https://alistair.cockburn.us/hexagonal-architecture

Catalyst relationship:

```text
stable organizational / Capability obligation
            ≈ port

HOW-specific integration
            ≈ adapter
```

Difference:

Traditional Ports & Adapters primarily isolates application/business logic from technical infrastructure. Catalyst extends the question into probabilistic AI execution, Evidence, Evaluation, organizational learning, known limits, and implementation evolution.

Conclusion:

```text
Stable WHAT / Replaceable HOW has strong traditional architecture support.
Catalyst should not claim adapter separation itself as novel.
```

---

## 4.2 Consumer-Driven Contract Testing / Pact

Pact demonstrates a key principle for replaceability:

> The consumer should specify the interactions/behavior it actually depends on, while the provider may be implemented differently as long as it continues to satisfy the contract.

Reference:

- https://docs.pact.io/implementation_guides/pact_specification
- https://docs.pact.io/pact_nirvana

Catalyst relationship:

Future HOW conformance should resemble consumer-driven behavioral requirements more than a universal implementation API.

The upper Capability should declare only load-bearing obligations.

The replacement HOW should not have to reproduce internal implementation details that the Capability does not require.

Important lesson:

```text
Conformance should test necessary behavior.
Do not certify implementation resemblance.
```

---

## 4.3 Software Product Lines / variability management

CMU SEI product-line research defines product lines around a managed set of core assets with explicit variability used to produce multiple products efficiently.

References:

- https://www.sei.cmu.edu/library/software-product-lines-collection/
- https://insights.sei.cmu.edu/library/variability-in-software-product-lines/

The research emphasizes that unmanaged variability creates duplicated or incompatible variation mechanisms.

Catalyst mapping:

```text
managed core assets
    ↔ durable Capability / Evidence / Evaluation / organizational assets

variation points
    ↔ Harness / Runtime / Agent / Provider / implementation choices

product derivation
    ↔ Binding / Rebinding to a chosen HOW
```

Product-line economics also support Catalyst’s intended business metrics: lower development cost, shorter time-to-market, greater reuse, higher quality, and greater agility.

Catalyst’s additional challenge is that AI HOW changes much faster and often changes probabilistic behavior rather than only deterministic component behavior.

---

## 4.4 SEI MAP / OAR — mining existing systems

The SEI’s MAP and OAR methods address whether existing legacy assets should be mined into product-line core assets and whether to rehabilitate, reuse, or replace them.

Reference:

- https://www.sei.cmu.edu/library/map-and-oar-methods-techniques-for-developing-core-assets-for-software-product-lines-from-existing-assets/
- https://www.sei.cmu.edu/library/mining-existing-assets-for-software-product-lines/

This strongly resembles two Catalyst concerns:

```text
External mature system
→ understand whether useful assets exist
→ decide what is reusable
→ rehabilitate / adapt / replace / discard
```

and:

```text
REPAIR / LOCAL REPLACE / REBUILD / RECOMPOSE / EXTERNAL ADOPT / RETIRE
```

Implication:

Waku learning and Harvest can be understood as an AI-era form of architecture recovery and capability mining rather than a completely unprecedented activity.

---

## 4.5 Experience Factory / organizational learning

Victor Basili and collaborators developed the Experience Factory model to separate project delivery from organizational learning and experience packaging.

References:

- https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19950024815.pdf
- https://ntrs.nasa.gov/citations/19990021257
- https://ntrs.nasa.gov/citations/19900010450

The Experience Factory asks questions that are directly relevant to Catalyst:

```text
Which past experiences are relevant?
Can they be reused in the current context?
How does an organization reuse knowledge from other projects?
How can outside-world experience be adopted with confidence?
How should experience be analyzed, packaged, improved, and reused?
```

Catalyst mapping:

```text
real project / execution
        ↓
Evidence + Evaluation
        ↓
Harvest / package durable capability knowledge
        ↓
organizational asset base
        ↓
future project / HOW binding
```

The Experience Factory provides one of the strongest historical validations for Catalyst’s organizational-learning ambition.

Catalyst’s extension is to make the packaged organizational knowledge operational across AI execution machinery rather than preserving experience only as process/knowledge products.

---

## 4.6 Dynamic Capabilities

Teece, Pisano, and Shuen’s Dynamic Capabilities framework addresses enterprise advantage under rapid technological change. Teece later characterizes important enterprise capacities through sensing, seizing, and reconfiguring.

References:

- https://sms.onlinelibrary.wiley.com/doi/10.1002/(SICI)1097-0266(199708)18:7%3C509::AID-SMJ882%3E3.0.CO;2-Z
- https://sms.onlinelibrary.wiley.com/doi/10.1002/smj.640

Catalyst can be interpreted as a technical/organizational mechanism supporting a specific AI-era dynamic capability:

```text
SENSE
new models / Harnesses / Agents / tools / external capabilities

SEIZE
select useful Capability or implementation candidates

RECONFIGURE
replace / rebind execution HOW while preserving organizational WHAT
```

This gives the Catalyst thesis a stronger business interpretation:

> Competitive value may come less from owning one transient AI implementation and more from repeatedly absorbing, evaluating, and reconfiguring around better implementations without organizational forgetting.

---

## 4.7 Autonomic computing / MAPE-K

IBM autonomic-computing work introduced an architectural control-loop tradition around monitoring, analysis, planning, execution, and shared knowledge.

Reference:

- https://research.ibm.com/publications/an-architectural-approach-to-autonomic-computing

Catalyst relationship:

```text
RUN
→ Evidence / observe
→ Evaluate / analyze
→ evolution choice
→ repair / replace / recompose / rebind
→ RUN AGAIN
```

Difference:

Catalyst should not become a generic self-healing control plane by default.

The valuable analogy is the **goal-centered closed loop**, not an authorization to build an autonomous MAPE-K engine.

---

# 5. Modern Agent/Harness systems and what they already solve

The most important strategic finding is that the HOW layer is rapidly becoming more modular and standardized.

This reduces the need for Catalyst to own low-level machinery.

---

## 5.1 DeepSeek Harness / Cordis

DeepSeek Harness developer preview explicitly states:

> Everything is a plugin.

Its plugin system covers:

```text
models
tools
skills
sessions
sandboxes
storage
loops
scheduling
UI
```

Developers can swap or recombine capabilities through configuration without changing Harness source.

Reference:

- https://www.deepseek.com/harness/en/

Cordis provides the plugin kernel and dynamic composition model.

The associated 2026 paper “A Programming Paradigm for Spatiotemporal Composability” describes:

```text
temporal composability
    a component’s effects can be reversed when removed

spatial composability
    component dependencies can be declared and reactively managed
```

Reference:

- https://arxiv.org/abs/2608.25512

Catalyst implication:

```text
DeepSeek Harness / Cordis
    solves replaceability INSIDE one Harness family

Catalyst
    should focus on continuity when the entire Harness itself changes
```

Catalyst should not compete by rebuilding Cordis-like plugin infrastructure unless a bounded future need proves it necessary.

---

## 5.2 OpenAI Codex Harness / App Server

OpenAI’s Codex App Server exposes the same Codex Harness to CLI, IDE, desktop, web, and partner clients through a stable bidirectional JSON-RPC surface.

Reference:

- https://openai.com/index/unlocking-the-codex-harness/

Important lessons:

```text
complex evolving Harness can sit behind a stable boundary
clients do not need to reimplement the agent loop
server can evolve independently when protocol remains backward compatible
```

OpenAI also explicitly notes a tradeoff in cross-provider/harness protocols: portable abstractions often converge on the common subset of features and can make richer provider/session/tool semantics difficult to express.

Catalyst implication:

> Platform Standard must not become a universal Harness API that flattens every Harness into the same internal model.

Stable WHAT should contain only organizationally load-bearing semantics. HOW-specific richness may remain behind bindings/extensions.

---

## 5.3 AutoGen

AutoGen separates agents from runtimes and provides standalone/distributed runtime models. Its documentation states that agents can operate in different runtime forms without changing their implementation in the intended architecture.

References:

- https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/agent-and-agent-runtime.html
- https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/distributed-agent-runtime.html

Catalyst implication:

Runtime abstraction and runtime replacement are not unique Catalyst inventions.

Catalyst’s higher-order question is whether organizational Capability/Evaluation survives even when the AutoGen runtime itself is replaced by another system.

---

## 5.4 AIOS

AIOS proposes an Agent Operating System kernel that isolates resource management, scheduling, context, memory, storage, access control, LLM and tool resources from agent applications.

Reference:

- https://arxiv.org/abs/2403.16971

Catalyst implication:

If AIOS or a similar system satisfies a future execution responsibility, it can be a candidate HOW.

Catalyst does not need to recreate an Agent OS merely because such responsibilities exist.

---

## 5.5 OpenHands V1 / SDK

OpenHands’ recent architecture emphasizes:

```text
stateless components
one mutable conversation source of truth
clear boundary between agent SDK and applications
composable components
provider-agnostic LLM access
replaceable tools/workspaces
context condensation
security validation
```

References:

- https://docs.openhands.dev/sdk/arch/overview
- https://docs.openhands.dev/sdk/arch/design

OpenHands is especially relevant because its V1 architecture explicitly describes problems caused when application-specific logic and research/benchmark concerns polluted the old core.

Catalyst lesson:

> Research/proof machinery and application-specific semantics should not leak into the reusable execution core.

This strongly supports the current Catalyst decision to keep HRU experiment machinery experiment-local by default.

---

## 5.6 AOS — Agent Operating System reference architecture

The 2026 AOS paper argues that current frameworks/runtimes improve execution but do not provide an implementation-independent operating architecture for intent, authority, uncertainty, governance, auditability, observability, and heterogeneous component composition.

Reference:

- https://arxiv.org/abs/2608.03214

It separates:

```text
Control & Governance Plane
Runtime & Coordination Plane
```

Catalyst implication:

Catalyst cannot claim “governance is separate from Runtime” as unique innovation.

The remaining differentiator must be more specific:

```text
Capability identity + organizational meaning + Evidence + Evaluation + known limits + migration/evolution knowledge
surviving repeated HOW replacement and producing second-use compounding
```

---

# 6. Protocols and infrastructure that Catalyst should treat as external HOW

## 6.1 MCP

The Model Context Protocol standardizes a large part of Agent ↔ tool/data interaction and continues to evolve toward a stateless core, extensions, tasks, authorization, routing, and stronger interoperability.

References:

- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://modelcontextprotocol.io/

Catalyst implication:

Do not invent a Catalyst-native universal tool transport if MCP satisfies the bounded responsibility.

Catalyst should preserve what the tool means to a Capability and what Evidence/Evaluation requires, not own the transport merely for identity.

---

## 6.2 A2A

A2A v1.0 provides an open standard for communication between agents created with different frameworks, languages, or vendors, including capability discovery and task collaboration without exposing internal memory/tools.

References:

- https://a2a-protocol.org/dev/specification/
- https://a2a-protocol.org/v1.0.0/

Catalyst implication:

Agent-to-agent communication should be treated as an interoperability HOW when applicable.

Catalyst should not create a competing protocol simply to own the boundary.

---

## 6.3 LangGraph

LangGraph provides checkpointed graph state, thread identity, interrupts/resume, pending writes, time travel, and fault tolerance.

Reference:

- https://docs.langchain.com/oss/python/langgraph/persistence

Catalyst implication:

If a Capability requires durable long-running execution, LangGraph may satisfy that responsibility.

Catalyst should specify the obligation, not require its current Runtime to evolve into LangGraph.

---

## 6.4 Temporal

Temporal provides durable execution that can resume workflows after process/network/infrastructure failures, potentially over very long durations.

Reference:

- https://docs.temporal.io/

Catalyst implication:

Production durable execution is already a mature external infrastructure problem.

Catalyst should adopt it if future responsibilities justify the cost rather than building a durability platform by default.

---

## 6.5 OpenTelemetry GenAI semantic conventions

OpenTelemetry’s GenAI semantic-convention work defines shared operation names and spans for concepts such as:

```text
invoke_agent
invoke_workflow
execute_tool
retrieval
model/provider operations
```

References:

- https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
- https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md

Status remains developmental, so it should not be treated as final architecture authority.

Catalyst implication:

Low-level execution evidence may increasingly be normalized by industry conventions.

Catalyst’s unique responsibility should be to determine what those facts mean for Capability Evidence and Evaluation, not to invent a universal low-level telemetry format without need.

---

# 7. Research on repository understanding and why Waku learning was hard

A major strategic correction from HRU-01 is:

> `LEARN` should not be equated with “one generic Agent manually explores a repository through a tiny set of low-level source tools.”

Repository understanding is itself a technical problem with multiple viable HOWs.

---

## 7.1 SWE-agent / Agent-Computer Interface

SWE-agent demonstrates that interface design substantially changes an LM agent’s ability to navigate repositories, edit code, and execute development tasks.

Reference:

- https://arxiv.org/abs/2405.15793

Catalyst implication:

A generic Harness with inconvenient low-level source operations may perform poorly even if the model is capable.

The ACI/tooling is HOW and should be replaceable.

---

## 7.2 RepoCoder

RepoCoder uses iterative repository retrieval and generation to improve repository-level code completion by exploiting information distributed across multiple files.

Reference:

- https://arxiv.org/abs/2303.12570

Catalyst implication:

Repository retrieval can be a specialized Learn HOW rather than Platform Core.

---

## 7.3 RepoGraph

RepoGraph provides repository-level graph/navigation information as a plug-in and reports improvements when added to multiple software-agent approaches.

Reference:

- https://arxiv.org/abs/2410.14684

Catalyst implication:

A future Waku understanding attempt may legitimately use repository graph assistance without changing the Waku-understanding WHAT.

---

## 7.4 Agentless

Agentless challenges the assumption that complex autonomous agents are always the right execution form. It uses a simpler localization → repair → validation approach and achieved strong performance/cost results on its evaluated SWE-bench Lite setting.

Reference:

- https://arxiv.org/abs/2407.01489

Catalyst implication:

Catalyst should not default to Agent as the solution form.

For any responsibility, candidate HOWs may include:

```text
Agent
workflow
specialized analyzer
deterministic pipeline
human+AI
external service
```

This reinforces the existing Catalyst `agent-construction` philosophy.

---

# 8. “From Prompts to Contracts” and direct validation of the contract thesis

The 2026 paper “From Prompts to Contracts: Harness Engineering for Auditable Enterprise LLM Agents” is highly relevant.

Reference:

- https://arxiv.org/abs/2607.08028

The paper moves deterministic guarantees into code/manifests/schemas/validators around a replaceable composition boundary and reports preserved contract checks across model substitution.

Catalyst implication:

This is strong evidence for:

```text
stable deterministic contracts
+
replaceable probabilistic model HOW
```

However, its demonstrated replacement scope is narrower than Catalyst’s desired scope.

Catalyst seeks continuity across possible replacement of:

```text
model
provider
Agent implementation
Harness
Runtime
tool transport
external system
```

Therefore it is adjacent evidence, not a duplicate of the Catalyst thesis.

---

# 9. What appears genuinely distinctive about Catalyst

The research does **not** support claiming novelty for:

```text
Ports & Adapters
plugin systems
contract testing
Runtime abstraction
Agent interoperability
organizational learning
self-adaptation loops
software asset mining
benchmarking
Evidence collection
```

All have substantial precedents.

The potentially distinctive combination is:

> **Evidence-backed Organizational Capability Continuity across rapid AI HOW replacement.**

The center object is not a Harness or Runtime but one Capability/Responsibility identity that accumulates:

```text
Domain meaning
Enterprise meaning
public obligations
Evidence
independent Evaluation
known limits
failure attribution
migration / compatibility knowledge
Evolution Lineage
real-use history
reuse history
```

and supports both:

```text
HOW → Learn/Evaluate/Harvest → WHAT
```

and:

```text
WHAT → Conformance/Rebind → HOW
```

This is the strongest current innovation hypothesis.

It remains a hypothesis until cross-HOW and second-use economics are demonstrated.

---

# 10. Feasibility assessment

## 10.1 High-confidence feasible areas

### Stable coordination / adapter separation

Confidence: HIGH

Supported by decades of Ports & Adapters, contract testing, product-line architecture, and current Catalyst Platform Standard evidence.

### Replaceable internal Harness components

Confidence: HIGH

Supported by DeepSeek Harness/Cordis, OpenHands, AutoGen, and other composable architectures.

### Runtime interchange behind stable boundaries

Confidence: HIGH to MEDIUM-HIGH

Supported by AutoGen runtime models, Codex App Server boundary design, OpenHands local/remote execution patterns, AIOS, LangGraph/Temporal as alternate execution systems.

### Model/provider substitution under deterministic contracts

Confidence: HIGH to MEDIUM-HIGH

Supported by existing provider abstraction patterns and recent harness-contract research.

---

## 10.2 Medium-confidence areas requiring Catalyst evidence

### External Agent/System → durable organizational Capability Harvest

Confidence: MEDIUM

There are strong analogues in architecture recovery, product-line mining, Experience Factory, and repository-understanding research.

However, reliable semantic decomposition of an external AI system remains difficult and task-dependent.

### Same organizational WHAT surviving broad HOW replacement

Confidence: MEDIUM / UNPROVEN

This is Catalyst’s primary empirical gap.

### Meaningful reduction in organizational switching/revalidation cost

Confidence: MEDIUM / UNPROVEN

Architectural mechanisms make the hypothesis plausible, but economic value requires real measurement.

---

# 11. The key architectural danger: the lowest-common-denominator trap

A universal Harness abstraction is not necessarily desirable.

If Catalyst tries to normalize every Harness feature, it risks producing:

```text
Codex richness
DeepSeek richness
LangGraph richness
OpenHands richness
        ↓
common minimal subset
        ↓
loss of useful HOW-specific capabilities
```

Therefore:

> **Stable WHAT must be defined by organizational obligations, not by the intersection of all available HOW features.**

HOW-specific semantics may remain:

```text
binding-local
adapter-local
extension-local
implementation-local
```

unless repeated evidence proves a true cross-boundary semantic deserves Platform promotion.

This aligns with current Catalyst Extension-First architecture.

---

# 12. The hardest unsolved problems

## 12.1 Semantic portability

Matching JSON schema does not prove behavioral equivalence.

Material differences may include:

```text
execution certainty
side effects
approval semantics
retry safety
durability
context persistence
failure attribution
evidence availability
human control
```

Future cross-HOW conformance must remain responsibility-driven rather than schema-only.

---

## 12.2 Capability identity stability

If every implementation change creates a new Capability identity, Catalyst cannot accumulate organizational learning.

If materially different behavior is incorrectly called the same Capability, Catalyst creates false portability.

Maintaining the right identity boundary is therefore a central long-term governance problem.

---

## 12.3 Asset curation

Not every implementation detail, benchmark result, or experience deserves Harvest.

Experience Factory research already shows that selecting, packaging, and reusing the right experience is difficult.

Catalyst must remain selective.

The organization should preserve durable value, not accumulate indiscriminate artifacts.

---

## 12.4 Proof machinery becoming product machinery

HRU has generated extensive proof identity, evidence, transcript, and run-control instrumentation.

This is valuable for the first difficult validation.

It becomes harmful if future HOW adoption requires every external implementation to reproduce Catalyst-specific proof file structures.

The long-term objective is:

```text
HOW emits its own facts
        ↓
Catalyst Binding / Evidence translation
        ↓
minimum required Capability evidence
```

not:

```text
all HOWs must become Catalyst Lab implementations
```

---

# 13. What the first cross-HOW proof must eventually establish

This research does not authorize implementation, but it records the decisive future evidence requirement.

For one existing Capability X:

```text
Capability identity          unchanged
Capability version           unchanged unless semantics change
Domain meaning               unchanged
Enterprise meaning           unchanged
Invocation semantics         unchanged
Result semantics             unchanged
Evaluation / benchmark       unchanged
Evidence obligations         unchanged
```

Then:

```text
HOW A
→ accepted result

replace execution HOW

HOW B
→ new binding/conformance
→ same Evaluation
→ accepted result
```

The proof should measure:

```text
Core files modified
Platform Standard files modified
Capability definition changes
Domain changes
Enterprise changes
Evaluation changes
Benchmark changes
binding-only additions
HOW-specific config additions
engineering effort
calendar time
migration/revalidation effort
evidence reused from HOW A
```

The objective is not merely PASS.

It is to produce the first measured **Rebinding Cost**.

---

# 14. Strategic metrics

Three metrics currently appear more important than counting Agents or Platform modules.

## T1 — Time to First Validated Capability

How long does a real organizational need take to become a Capability with accepted real-use evidence?

## T2 — Rebinding Cost

How much work is required to replace one HOW with another and regain acceptance under the same Capability/Evaluation boundary?

This is the central metric for Stable WHAT / Replaceable HOW.

## T3 — Second-Use Cost

How much cheaper is the second use of existing organizational capability knowledge in:

```text
a new HOW
a new Agent
a second Enterprise
a second workflow
a related Decision Unit
```

The Catalyst thesis requires T2 and T3 to fall over time.

If each new adoption continues to resemble HRU-01’s first-adoption cost, organizational compounding has not been achieved.

---

# 15. Commercial value hypothesis

Catalyst’s commercial value should not be framed primarily as “less Agent code.”

The larger costs are:

```text
Vendor / Harness Switching Cost
Revalidation Cost
Organizational Forgetting Cost
Second-use / recomposition cost
legacy-understanding cost
migration risk
```

A successful Catalyst reduces the cost of replacing transient AI machinery while preserving already-proven organizational knowledge.

A useful long-term expression is:

```text
Catalyst Value
≈
(Durable Organizational WHAT
 × Evidence / Evaluation Quality
 × Reusability)
÷ Rebinding Cost
```

This is a conceptual expression, not a quantitative financial model.

---

# 16. Strategic interpretation: Catalyst as an AI-era dynamic capability mechanism

The strongest business interpretation is:

> Catalyst may function as an organizational mechanism for sensing, evaluating, adopting, replacing, and reconfiguring AI capabilities under rapid technological change.

Models, Harnesses, Agents, Providers, and frameworks are increasingly transient resources.

The durable enterprise asset is the organization’s ability to know:

```text
what capability is valuable
what evidence supports it
where it fails
what organization-specific meaning applies
how to evaluate it
which implementations have satisfied it
what must be revalidated when implementation changes
how prior migrations succeeded or failed
```

This is closer to an organizational dynamic capability than to a conventional Agent framework.

---

# 17. Strategic non-goals reinforced by this research

Without new real evidence, Catalyst should **not** become:

```text
another general-purpose Agent Harness
another Agent Operating System
another MCP/A2A protocol
a universal Workflow Engine
a universal distributed Runtime
a production durability platform
a universal telemetry format
a generic plugin kernel
a mandatory Capability Registry Service
a self-healing autonomous replacement engine
a universal Harness API
a repository-graph platform
```

Mature external systems should be adopted when they satisfy the responsibility at lower total cost.

The Catalyst platform should become thinner in transient execution machinery and thicker in durable organizational learning, Evidence, Evaluation, Capability identity, and migration knowledge.

---

# 18. Implications for Waku / HRU-01

## 18.1 Proof-03 remains READY / PARKED

The current frozen identity preparation is valid evidence, but this research does not authorize the next run.

Proof-03 should be understood as:

```text
one candidate HOW for Waku Learning
```

not:

```text
the architecture-defining next step of Catalyst
```

---

## 18.2 Waku learning is still valuable

Waku can continue to test:

```text
External HOW
→ UNDERSTAND
→ EVALUATE
→ HARVEST
→ durable organizational WHAT
```

The strategic correction is that the **method of understanding** is also Replaceable HOW.

A future Waku-learning execution may use:

```text
current NativeToolsV2 + LocalSourceAccess
Codex
DeepSeek Harness
repo-graph-assisted navigation
specialized static analysis
retrieval pipeline
human + AI review
agentless workflow
```

without changing the stable learning obligations.

---

# 19. Current evidence of readiness for a future cross-HOW proof

Catalyst already possesses many required pieces:

```text
Architecture Stable WHAT / Replaceable HOW principle
Platform Standard Capability / Invocation / Result boundary
Extension-first evolution seam
RuntimeAdapter binding precedent
Capability Contract conformance tests
versioned Capability identity
Evaluation / benchmark methods
execution provenance concepts
Evidence preservation practice
organizational asset precedent
capability-optimization evolution method
external HOW adoption policy
```

The primary missing facts are:

```text
no second real HOW binding yet
no measured Rebinding Cost yet
no proof that same Capability/Evaluation survives a truly different HOW
```

Therefore the next long-term value is likely to come from **evidence of portability**, not additional abstract architecture.

This is a research conclusion, not implementation authorization.

---

# 20. Research synthesis

## 20.1 What is strongly validated by external precedent

```text
separate stable purpose from technical adapters
explicitly manage variability
use contracts to verify replacement implementations
mine existing systems selectively rather than rewrite everything
package project experience into reusable organizational assets
operate goal-centered evaluate/reconfigure loops
use mature external execution infrastructure rather than own every mechanism
```

## 20.2 What remains Catalyst-specific and unproven

```text
one long-lived organizational Capability identity
accumulating Domain + Enterprise meaning + Evidence + Evaluation + limits + lineage
surviving broad AI HOW replacement
supporting both Learn/Harvest and Rebinding directions
producing measurable second-use compounding
```

## 20.3 Innovation hypothesis

Catalyst’s innovation is best described as **compositional / operating-model innovation**, not invention of a new adapter, Harness, or protocol.

Potential unique value:

> **Evidence-backed Organizational Capability Continuity across AI implementation change.**

This should remain a hypothesis until demonstrated by real cross-HOW and second-use evidence.

---

# 21. Reference map

## Traditional software architecture / reuse

- Alistair Cockburn — Hexagonal Architecture / Ports & Adapters  
  https://alistair.cockburn.us/hexagonal-architecture

- Pact — Consumer-driven contract testing  
  https://docs.pact.io/implementation_guides/pact_specification

- CMU SEI — Software Product Lines  
  https://www.sei.cmu.edu/library/software-product-lines-collection/

- CMU SEI — Variability in Software Product Lines  
  https://insights.sei.cmu.edu/library/variability-in-software-product-lines/

- CMU SEI — MAP and OAR Methods  
  https://www.sei.cmu.edu/library/map-and-oar-methods-techniques-for-developing-core-assets-for-software-product-lines-from-existing-assets/

- CMU SEI — Mining Existing Assets for Software Product Lines  
  https://www.sei.cmu.edu/library/mining-existing-assets-for-software-product-lines/

## Organizational learning / strategy

- Basili et al. — Domain analysis for reuse of software-development experiences / Experience Factory  
  https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19950024815.pdf

- Basili / Experience Factory strategy and practice  
  https://ntrs.nasa.gov/citations/19990021257

- Basili — Software development as an experimental / learning paradigm  
  https://ntrs.nasa.gov/citations/19900010450

- Teece, Pisano, Shuen — Dynamic Capabilities and Strategic Management  
  https://sms.onlinelibrary.wiley.com/doi/10.1002/(SICI)1097-0266(199708)18:7%3C509::AID-SMJ882%3E3.0.CO;2-Z

- Teece — Explicating Dynamic Capabilities  
  https://sms.onlinelibrary.wiley.com/doi/10.1002/smj.640

- IBM — An architectural approach to autonomic computing  
  https://research.ibm.com/publications/an-architectural-approach-to-autonomic-computing

## Modern Harness / Runtime / Agent architecture

- DeepSeek Harness developer preview  
  https://www.deepseek.com/harness/en/

- Cordis / A Programming Paradigm for Spatiotemporal Composability  
  https://arxiv.org/abs/2608.25512

- OpenAI — Unlocking the Codex Harness / App Server  
  https://openai.com/index/unlocking-the-codex-harness/

- AutoGen Agent Runtime  
  https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/agent-and-agent-runtime.html

- AIOS  
  https://arxiv.org/abs/2403.16971

- OpenHands SDK Architecture  
  https://docs.openhands.dev/sdk/arch/overview

- Agent Operating System (AOS) reference architecture  
  https://arxiv.org/abs/2608.03214

## Interoperability / durable execution / evidence

- Model Context Protocol  
  https://modelcontextprotocol.io/

- MCP 2026-07-28 specification update  
  https://blog.modelcontextprotocol.io/posts/2026-07-28/

- A2A Protocol  
  https://a2a-protocol.org/dev/specification/

- LangGraph Persistence  
  https://docs.langchain.com/oss/python/langgraph/persistence

- Temporal  
  https://docs.temporal.io/

- OpenTelemetry GenAI semantic conventions  
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md

## Agent / repository understanding

- SWE-agent  
  https://arxiv.org/abs/2405.15793

- RepoCoder  
  https://arxiv.org/abs/2303.12570

- RepoGraph  
  https://arxiv.org/abs/2410.14684

- Agentless  
  https://arxiv.org/abs/2407.01489

## Contract-centered AI Harness research

- From Prompts to Contracts: Harness Engineering for Auditable Enterprise LLM Agents  
  https://arxiv.org/abs/2607.08028

---

# 22. Final strategic statement

> **Catalyst should not win by owning the most AI machinery.**
>
> It should win by making AI machinery cheap to replace while preserving the organizational capability that has already been understood, evidenced, evaluated, and learned.

A strong Catalyst future looks like:

```text
HOW enters easily
HOW leaves safely
WHAT remains clear
Evidence accumulates
Evaluation remains reusable
Known limits become more truthful
Migration knowledge compounds
Second use becomes cheaper
```

The decisive future question is therefore not:

> “Can Catalyst build another Agent or Harness?”

It is:

> **“Can Catalyst preserve the same organizational Capability while repeatedly changing the execution machinery beneath it, and can each replacement become faster, safer, and cheaper because the organization learned from the previous one?”**

That question should remain one of the strongest long-term reference tests for Catalyst architecture and product value.
