# CATALYST PLATFORM — HARNESS CAPABILITY ARCHITECTURE REVIEW V0.1

> **Status:** ARCHITECTURE REVIEW
> **Branch:** `platform-harness`
> **Implementation Authorization:** **NO**
> **Platform Integration Authorization:** **NO**
> **Base:** `main @ 5874be1130e8867082880fcd63f659fc909d9efd`
> **Purpose:** determine the minimum Harness capability Catalyst Platform should own as a platform responsibility while keeping every concrete Harness implementation replaceable.

---

# 0. Executive Decision

Catalyst remains **Catalyst Platform**.

Harness is a Platform capability, not the identity of the Platform.

```text
CATALYST PLATFORM
    ├── governance / contracts / assets / lineage / evaluation / admission
    ├── Runtime for already-built Agents
    └── Harness capability for governed construction / inspection / evolution
```

The strategic goal is **not**:

```text
build a better Codex
build a better PenguinHarness
build a general desktop Agent
make one-sentence Agent generation the product
```

The goal is:

```text
Catalyst should be able to perform its own governed construction loop
without permanently depending on one external Harness implementation.
```

The current Harness implementation is replaceable.
The future Harness implementation is replaceable.
Model providers are replaceable.
Tool implementations are replaceable.

Catalyst owns the **Harness responsibility contract**, not one permanent Harness implementation.

---

# 1. Why Harness Capability Is Now Justified

This capability is no longer speculative platform-first work.

It is derived from repeated Case evidence.

## CASE 01 evidence donor

Current Case 01 development has repeatedly required an external coding Harness to perform:

```text
read current Candidate / Stage context
understand current implementation
modify bounded code
run tests
inspect failures
repair
record evidence
form / freeze Candidate
inspect repository diff
preserve protected boundaries
```

Case 01 has also established that governed construction is not merely code generation. A Candidate must preserve professional purpose, functions, obligations, evidence, version identity, decomposability and replaceability.

Current Case 01 evidence branch referenced for this review:

```text
case-01 @ 30e85a917535773844df8f8af20f579ee2538f50
BREA v0.8 residential slice frozen
```

## CASE 02 evidence donor

Case 02 proved a second class of Harness work:

```text
inspect an unfamiliar complete Agent
understand observable behavior
responsibility-first decomposition
identify valuable mechanisms
preserve governed knowledge assets
rediscover an asset from a later need
reconstruct one mechanism without rereading source
```

Current Case 02 evidence branch referenced for this review:

```text
case-02 @ ba169805ec074e80cd53e5b6b2b998ba595baaa2
WAKU-A01 unbound Catalyst-native reconstruction
```

Therefore the need is no longer:

```text
"maybe Catalyst should have a Harness"
```

It is:

```text
"which repeatedly observed external-Harness responsibilities
must Catalyst be able to invoke through its own replaceable Harness boundary?"
```

---

# 2. Evidence Sources and Authority

This review uses three evidence classes.

## 2.1 Catalyst Case evidence

- Case 01: governed professional Agent construction and iterative Candidate formation.
- Case 02: external Agent understanding, decomposition, assetization, rediscovery and unbound reconstruction.

Case evidence defines Catalyst needs.

## 2.2 PenguinHarness mechanism evidence

Pinned research source for this review:

```text
Prism-Shadow/penguin-harness
commit: 11d6d16efccd889557236b0f951683d8b350cd91
```

Relevant source surfaces include:

```text
packages/docs/content/architecture.en.md
packages/docs/content/tools.en.md
packages/docs/content/quickstart-sdk.en.md
packages/core/src/state/agent-state.ts
packages/cli/src/task-loop.ts
packages/skills/skills/agent-initialization/SKILL.md
packages/skills/skills/agent-evaluation/SKILL.md
packages/skills/skills/agent-optimization/SKILL.md
```

Penguin is a mechanism reference, not Catalyst architecture authority.

## 2.3 Codex / DeepSeek Harness operational evidence

Current Catalyst development has practically used external coding Harnesses as executors. Their observed ability to read repos, write files, run commands/tests and work with Git is relevant operational evidence.

Their internal architecture is **not source-audited in this review** and must not be treated as an architecture authority.

---

# 3. Important Penguin Findings

## 3.1 A Harness is more than a model call

Penguin's center is one execution engine shared by SDK / CLI / Server. Its architecture separates:

```text
Human boundary
LLM interface
Environment / tool interface
```

The engine maintains the message loop while concrete provider, environment and UI implementations remain outside the kernel.

Catalyst should learn the separation principle, not copy Penguin's package layout or message protocol.

## 3.2 Workspace + Session is a real execution boundary

Penguin creates an Agent, creates a Session bound to a `workspaceDir`, then executes `session.run(...)` with an approval callback.

This demonstrates a useful Harness responsibility split:

```text
Agent / instruction state
Session
Workspace
Model
Tools
Approval
Trace
```

Catalyst needs equivalent responsibilities, but not necessarily Penguin's APIs or state layout.

## 3.3 Tool surface should remain small

Penguin intentionally keeps dedicated file tools plus a general shell fallback. Tool execution has centralized timeout, output handling, terminal state and approval semantics.

Catalyst should learn:

```text
small tool vocabulary
explicit permission semantics
centralized execution result semantics
observable tool calls
bounded output / timeout behavior
```

Catalyst should NOT copy all Penguin tools into Platform V0.1.

## 3.4 Approval is part of execution, not only UI

Penguin routes every tool call through an approval callback. CLI / Server choose concrete approval modes while core owns the approval seam.

Catalyst requires the same architectural idea:

```text
execution permission
!=
LLM preference
```

The current Catalyst Stage / Authorization model must remain higher authority than any Harness model decision.

## 3.5 Penguin Agent creation is already asset-aware

Penguin does not only generate brand-new instructions. Current `main` allows a newly created Agent to be seeded from:

```text
built-in Skill library
project directory Skills
```

It resolves Skill sources before writing the Agent and carries Skill source identity.

Therefore Catalyst must NOT claim its differentiation is simply:

```text
"Penguin creates new things; Catalyst reuses old things"
```

The deeper differentiation must be:

```text
Catalyst treats reusable organizational capability as a governed asset
with problem identity, lineage, bindings, evidence and replacement path,
not only as an installable Skill.
```

## 3.6 Penguin's one-sentence creation behavior is NOT Catalyst's target UX

Penguin's `agent-initialization` Skill explicitly says that when a requirement is concrete, even one sentence can be expanded without follow-up questions and assumptions are reported afterwards.

Catalyst should intentionally differ.

Catalyst principle:

```text
ONE SENTENCE MAY START CONSTRUCTION
BUT MUST NOT BYPASS UNDERSTANDING
```

The Platform should first infer as much as possible, then ask only questions whose answers materially change:

```text
purpose
responsibility
Domain meaning
Enterprise meaning
risk / authority
required evidence
implementation choice
```

It should not ask implementation trivia the Platform can decide later.

## 3.7 Evaluation / optimization mechanisms are valuable but not V0.1 Harness scope

Penguin has mature separation of isolated evaluation and versioned Candidate optimization, including frozen benchmark conditions, snapshots, rollback and score-linked traces.

These are high-value future references.

However Catalyst already has its own governance / evaluation / authorization semantics. Penguin's optimization workflow must not become Catalyst authority or V0.1 scope by default.

---

# 4. The Core Catalyst Distinction

Catalyst is not primarily an Agent generator.

Catalyst's long-term value is cumulative organizational capability.

```text
BUILD
→ EVALUATE
→ PRESERVE
→ DISCOVER
→ REUSE / ADAPT / RECONSTRUCT
→ BUILD NEXT
```

A new Agent should increasingly be composed from previously proven organizational capability instead of being regenerated from zero.

Therefore the Harness should optimize for:

```text
UNDERSTAND
→ SEARCH
→ COMPOSE
→ BUILD WHAT IS MISSING
→ EVALUATE
→ HARVEST NEW VALUE
```

not:

```text
PROMPT
→ GENERATE
→ DONE
```

---

# 5. Capability Is Not the Same as Skill

A **Skill** is a strong reusable form for procedural knowledge:

```text
how to build
how to configure
how to operate
how to evaluate
how to perform a repeatable workflow
```

But an organizational Capability may exist in several useful forms.

Conceptual minimum:

```text
CAPABILITY
    ├── Capability Record     "what is this / what problem does it solve?"
    ├── Skill / Recipe        "how can a Harness build or use it?"
    ├── Implementation        "is there already runnable code / service?"
    ├── Evaluation            "what evidence supports it?"
    └── Lineage / Bindings    "where did it come from and where may it apply?"
```

Not every Capability needs every form.

Examples:

```text
Benchmark Design
→ may mainly be a Skill + evidence

RAG engine
→ may have Record + Skill + Implementation + Evaluation

Domain applicability knowledge
→ may have Record + Domain Knowledge + Evaluation with little/no reusable code

WAKU-A01 in Case 02-A
→ initially Record only

Case 02-B reconstruction
→ Record lineage + Case-local Implementation + tests
```

Therefore:

```text
CAPABILITY != SKILL
SKILL may be one asset form of a Capability
```

---

# 6. Capability Asset Bundle — Minimal Concept Only

This review introduces **Capability Asset Bundle** only as a conceptual retrieval / composition model.

It is NOT yet:

```text
Platform Core resource
new database
universal registry
new service
runtime-callable component system
mandatory folder structure
```

Conceptual fields:

```text
capability_id
name
problem_solved
responsibility_boundary
status

asset_forms:
  knowledge_record
  skill_or_recipe
  implementation
  evaluation

lineage:
  learned_from
  reconstructed_from
  adapted_from
  created_by_case

bindings:
  domain
  enterprise
  target_agent

known_limits
reuse_preconditions
```

The exact persistent representation remains intentionally undecided.

The current Case 02 Asset Catalog already proves that a small structured record can support rediscovery. Do not create a generic Registry before more Cases justify it.

---

# 7. Search Capability First

Future Catalyst Agent construction should not default to searching only Skills.

The desired logical flow is:

```text
NEW NEED
    ↓
CAPABILITY SEARCH
    ↓
What already exists?
    ↓
knowledge only?
skill / recipe?
runnable implementation?
evaluation evidence?
compatible bindings?
    ↓
choose the cheapest valid reuse path
```

## Reuse path order

```text
1. REUSE EXISTING IMPLEMENTATION
   when compatibility + binding + evidence are sufficient

2. ADAPT EXISTING IMPLEMENTATION
   when bounded changes are required

3. RECONSTRUCT FROM SKILL / RECIPE
   when procedure exists but implementation is unsuitable / absent

4. RECONSTRUCT FROM KNOWLEDGE RECORD
   when mechanism knowledge exists but no executable recipe exists

5. BUILD NEW
   only when the required capability is genuinely missing
```

This is a target construction principle, not yet an automated resolver.

---

# 8. Harness Responsibility Classification

Every candidate Harness feature must be classified into one of three groups.

## A — CATALYST MUST OWN

Catalyst must own the semantics / authority even if execution is delegated.

```text
construction intent
user-need interpretation boundary
responsibility decomposition
Domain / Enterprise semantic binding
Capability identity and lineage
asset discovery semantics
Stage / task authorization
protected-boundary definition
evaluation contract
acceptance / admission authority
promotion / replacement authority
```

The Harness must never silently invent these authorities.

## B — REPLACEABLE HARNESS RESPONSIBILITY

Catalyst needs these execution responsibilities but should not privilege one implementation.

```text
Harness Session
Workspace binding / isolation
Model Provider invocation
context assembly for the authorized task
file read
file write / edit
command execution
test execution
Git / diff inspection
approval callback enforcement
execution trace
bounded retry / failure semantics
result handoff
```

A future Penguin-derived, Codex-like, DeepSeek-like or new implementation may satisfy this contract.

## C — REFERENCE ONLY / PREMATURE

Do not build by default in the first Harness capability.

```text
one-shot production Agent generation
multi-agent orchestration
subagent hierarchy
generic self-optimization engine
automatic benchmark generation
automatic capability replacement
generic plugin marketplace
universal MCP/tool ecosystem
browser / desktop automation
vector capability registry
Graph DB for assets
full Web UI
```

A later Case may justify any of them.

---

# 9. Harness Modes

Harness code-writing authority must not be permanently active.

Logical modes:

## INSPECT

```text
read / search / bounded command / test inspection
WRITE = OFF by default
```

Useful for external Agent understanding and decomposition.

## BUILD

Triggered by an explicit construction / repair authorization.

```text
authorized Workspace
file write / edit
command / test
candidate evidence
```

## EVOLVE

Future mode for bounded N+1 improvement.

Not part of V0.1 unless later evidence requires it.

## RUN

Normal use of an already-built Agent belongs to Catalyst Runtime / Agent execution path.

Harness should not be required for normal Agent operation.

---

# 10. Build for Decomposability

A Catalyst-built Agent must remain understandable and decomposable by responsibility.

This does NOT mean maximally fragmenting code.

```text
DECOMPOSABLE BY RESPONSIBILITY
!=
MAXIMALLY SPLIT IMPLEMENTATION
```

The construction result must preserve enough machine-readable or inspectable structure to recover:

```text
Agent identity
purpose
responsibilities / functions
Domain binding
Enterprise binding
important seams / obligations
implementation blocks
asset lineage
replaceability assumptions
evaluation identity
version / change identity
```

V0.1 should first reuse existing Catalyst Agent / Candidate records where possible.

Do not create a second universal Agent Manifest merely because this review can name one.

---

# 11. Harness Must Preserve External Construction Freedom

Catalyst's built-in Harness is optional infrastructure.

The Platform must continue allowing Agents / Skills / Capabilities to be created through:

```text
Catalyst built-in Harness
Codex-like external Harness
DeepSeek-like external Harness
Penguin or another external system
human development
future tools
```

The admission question is not:

```text
"Was this made by Catalyst Harness?"
```

It is:

```text
Can Catalyst understand it?
Can responsibilities be identified?
Can lineage be recorded?
Can Domain / Enterprise meaning be bound correctly?
Can it be evaluated?
Can it be admitted / rejected under Catalyst authority?
Can it later be replaced / upgraded without losing organizational meaning?
```

This is essential to Platform neutrality.

---

# 12. Minimum Harness V0.1 Target

Do NOT begin V0.1 by building an Agent Builder.

First prove a smaller claim:

> Catalyst Platform can invoke a replaceable LLM through a controlled Harness Session to complete one already-authorized, bounded software-development task inside an isolated Workspace and return auditable evidence.

Minimum responsibilities likely required:

```text
HarnessSession
WorkspaceBoundary
ModelGateway
ReadFile
Write/EditFile
CommandExecution
TestExecution
ApprovalBoundary
ExecutionTrace
Result / Failure
```

Git mutation is not required for the first proof if diff / workspace evidence is sufficient.
Commit / push may remain outside the first Harness proof until justified.

A live production Agent does not need to be built in the first proof.

---

# 13. First V0.1 Proof Should Use a Real Catalyst Task

Do not validate only with Hello World.

Preferred proof pattern:

```text
accepted small Stage / task
        +
authorized Case-local Workspace
        ↓
Harness reads only permitted context
        ↓
LLM makes a bounded code change
        ↓
Harness runs deterministic test
        ↓
if test fails, bounded repair may occur
        ↓
Harness records tool / model / file / test trace
        ↓
result + diff returned
        ↓
STOP BEFORE PLATFORM INTEGRATION
```

Case 01 should eventually provide the first real low-risk task because it represents actual governed Agent product development.

Do not manufacture a fake Case merely to make Harness V0.1 look successful.

---

# 14. Safety / Authority Invariant

The Harness may execute.

The Harness may reason.

The Harness may propose.

The Harness does **not** gain governance authority from its intelligence.

```text
LLM decision
!= authorization

tool success
!= acceptance

tests pass
!= admission

better score
!= automatic replacement
```

A model cannot authorize itself to:

```text
expand Stage scope
modify protected Platform Core
change Domain / Enterprise meaning
promote Case-local mechanism
replace an admitted Capability
merge to main
```

unless a higher Catalyst authority explicitly grants that action.

---

# 15. Replacement Principle

Harness itself follows the same Catalyst replacement philosophy as every other implementation.

```text
CURRENT HARNESS V0.1
    ↓ evidence + compatibility
FUTURE HARNESS V0.2
    ↓
EXTERNAL / THIRD-PARTY HARNESS
```

Replacement should preserve the required Harness contract and evidence semantics.

Therefore model-specific, shell-specific, vendor-specific and framework-specific details should remain behind replaceable implementation seams wherever practical.

---

# 16. Explicit Non-Goals for the Next Stage

The next Stage must NOT attempt to solve:

```text
full Agent construction UX
Capability automatic comparison
Capability replacement
Skill marketplace
universal asset database
semantic/vector asset search
multi-user Web UI
multi-agent planning
self-improving Harness
Harness self-modification
whole Penguin port
whole Codex replacement
whole DeepSeek Harness replacement
```

These are future possibilities, not current requirements.

---

# 17. Architecture Review Verdict

```text
CATALYST REMAINS A PLATFORM
PASS

HARNESS AS PLATFORM CAPABILITY
REQUIRED

HARNESS AS PLATFORM IDENTITY
REJECT

HARNESS IMPLEMENTATION REPLACEABILITY
REQUIRED

MODEL PROVIDER REPLACEABILITY
REQUIRED

ONE-SENTENCE AGENT COMPLETION
REJECT

ONE-SENTENCE CONSTRUCTION ENTRY
SUPPORTED WITH TARGETED CLARIFICATION

UNDERSTAND BEFORE BUILD
REQUIRED

SEARCH CAPABILITY BEFORE BUILD
REQUIRED DIRECTION

CAPABILITY == SKILL
REJECT

SKILL AS CAPABILITY ASSET FORM
SUPPORTED

CAPABILITY ASSET BUNDLE
SUPPORTED AS MINIMAL CONCEPT ONLY
NO REGISTRY IMPLEMENTATION AUTHORIZED

AGENT DECOMPOSABILITY AFTER BUILD
REQUIRED

BUILT-IN HARNESS EXCLUSIVITY
REJECT

EXTERNAL HARNESS COMPATIBILITY
REQUIRED DIRECTION

MINIMUM HARNESS V0.1 PROOF
JUSTIFIED

PLATFORM INTEGRATION NOW
NO

IMPLEMENTATION AUTHORIZATION
NO
```

---

# 18. Next Deliverable

The next legitimate artifact is **one minimum Stage Spec**, not another general architecture document:

```text
CATALYST_PLATFORM_MINIMUM_HARNESS_V0.1_STAGE_SPEC
```

It should authorize only the smallest proof needed to answer:

> Can a Catalyst-controlled, replaceable Harness Session perform one bounded, already-authorized development task with Workspace isolation, model/tool boundaries, approval and trace evidence?

Before that Stage Spec is authorized, no Harness implementation should be written.

---

# 19. STOP Boundary

This Review ends at architecture definition.

```text
RESEARCH
→ CASE-DERIVED REQUIREMENTS
→ PENGUIN MECHANISM REVIEW
→ RESPONSIBILITY CLASSIFICATION
→ CAPABILITY ASSET MODEL
→ MINIMUM V0.1 TARGET
→ STOP
```

No merge to `main`.
No Case 01 mutation.
No Case 02 mutation.
No Harness implementation.
No Platform integration.
