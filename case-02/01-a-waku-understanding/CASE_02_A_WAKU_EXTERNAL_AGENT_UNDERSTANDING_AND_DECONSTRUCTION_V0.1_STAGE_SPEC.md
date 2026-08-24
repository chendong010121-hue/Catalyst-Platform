# CASE 02-A — Waku External Agent Understanding, Functional Decomposition & Asset Discovery
## Stage Spec V0.2

> Status: STAGE SPEC — READY FOR AUTHORIZATION
> Implementation Authorization: NO
> Case Branch: `case-02`
> Source Agent: `ShenSeanChen/waku-agent`
> Source Commit: `8328f567ab52d07921445cb40feed23cbc5ea2ad`
> Source Treatment: MATURE EXTERNAL REFERENCE SYSTEM + MECHANISM DONOR + POTENTIAL INTEGRATION TARGET

## 1. Stage Purpose

CASE 02-A is primarily a **Catalyst platform-capability test**.

Waku is the test subject, not the target architecture.

This Stage tests whether Catalyst can:

```text
UNDERSTAND a foreign mature Agent
→ DECOMPOSE it by function / responsibility rather than file tree
→ DISTINGUISH valuable mechanism from product-specific implementation
→ PRESERVE evidence and reuse conditions
→ ASSETIZE only the valuable knowledge
→ REDISCOVER those assets later from a new capability need
```

The Stage MUST NOT attempt to turn Catalyst into Waku.

The Stage MUST NOT conclude that because Waku has a good Memory, Loop, Tool, Graph, Eval or Dashboard design, Catalyst Core must own the same component.

## 2. Platform Capabilities Under Test

### PCAP-02-01 — External Agent Understanding

Can Catalyst recover the real product promise, executable behavior and lifecycle of a mature Agent from source evidence without seeding the expected answer?

### PCAP-02-02 — Functional Decomposition

Can Catalyst decompose a whole Agent into meaningful functional / responsibility units such as:

```text
Gateway
Working-memory assembly
Agent loop
Model-provider seam
Tool execution
Retrieval gating
Semantic memory
Episodic memory
Procedural memory
Memory consolidation
Graph/workflow control
Trace / observability
Evaluation
Release gating
State persistence
```

without treating Waku's directory tree as the architecture?

The decomposition MAY find a different set of functional units. The list above is not a required answer key.

### PCAP-02-03 — Valuable-Asset Identification

Can Catalyst distinguish:

```text
valuable reusable mechanism
vs
Waku-specific implementation
vs
integration seam
vs
reference-only evidence
vs
unknown
```

with explicit responsibility reasoning and source evidence?

### PCAP-02-04 — Governed Asset Preservation

Can Catalyst preserve high-value findings as small, discoverable, evidence-backed asset records without copying Waku code or promoting the mechanism into Platform Core?

### PCAP-02-05 — Asset Rediscovery

After the asset catalog is frozen, can a later capability need discover relevant stored assets **without rescanning the Waku source repository**?

This Stage tests discovery and selection only.

Actual Catalyst-native reconstruction / invocation of a selected asset belongs to a later explicitly authorized Stage.

## 3. Core Principles

```text
LEARN THE MECHANISM
!=
INHERIT THE ARCHITECTURE
```

```text
FUNCTIONALLY DECOMPOSABLE
!=
MAXIMALLY FRAGMENTED
```

```text
STORED ASSET KNOWLEDGE
!=
PLATFORM CORE CAPABILITY
```

```text
DISCOVERABLE FOR FUTURE REUSE
!=
ALREADY IMPLEMENTED / CALLABLE
```

Waku is a mature external system and may demonstrate strong engineering patterns. It has no automatic architecture authority inside Catalyst.

## 4. Canonical Source Baseline

```text
repository: https://github.com/ShenSeanChen/waku-agent.git
branch: main
commit: 8328f567ab52d07921445cb40feed23cbc5ea2ad
```

Known local deployment baseline may be used as operational evidence, but source and implementation claims must be checked against the pinned commit.

Source repository is READ-ONLY.

Missing `DEEPSEEK_API_KEY` is not a blocker for structural understanding. Live model-dependent claims must be marked `NOT LIVE-VERIFIED` unless actually exercised.

## 5. Scope

CASE 02-A may inspect and perform read-only/local verification of:

- README / architecture docs;
- CLI / Dashboard / HTTP surfaces;
- Agent loop and termination semantics;
- model/provider abstraction;
- state and working-memory assembly;
- semantic / episodic / procedural memory;
- retrieval gate / consolidation;
- tools and optional MCP boundary;
- graph/workflow layer;
- persistence;
- traces / usage / observability;
- deterministic eval / judge eval / release gate;
- gateway/channel handling;
- source tests / package config;
- declared extension/configuration surfaces.

## 6. Non-goals / Forbidden Actions

CASE 02-A MUST NOT:

```text
modify Waku source
fork Waku
copy Waku source into Catalyst
create a Catalyst adapter
register Waku in Catalyst
modify Platform Core
modify Catalyst Runtime / RuntimeAdapter
create a generic Memory / Tool / Workflow standard
promote a Waku pattern merely because it works in Waku
redesign CASE 01
create callable reconstructed mechanisms
start CASE 02-B
```

Do not optimize or repair Waku.

Do not require a live API credential to claim structural understanding.

## 7. Allowed Actions

```text
inspect
read source/tests/docs
run local read-only smoke tests
trace responsibility flow
compare declared vs implemented behavior
functionally decompose
classify mechanism value
record evidence
create small governed asset records
run post-freeze asset rediscovery checks
assess integration seams
```

## 8. Required Understanding Questions

At minimum answer:

1. What is Waku's actual user-facing promise?
2. What are its real entry/gateway surfaces?
3. What owns the loop and termination semantics?
4. How are model providers abstracted?
5. What state is ephemeral vs durable?
6. How are semantic, episodic and procedural memory separated?
7. What decides whether memory is retrieved?
8. How/when is memory consolidated or updated?
9. How are tools registered, invoked and traced?
10. What role do graphs/workflows play relative to the normal loop?
11. What evidence/trace is produced per turn?
12. How do deterministic eval, LLM-as-judge and release gating differ?
13. Which functions are essential vs optional?
14. Which boundaries are public vs private implementation seams?
15. Which mechanisms appear reusable beyond Waku?
16. Which are coupled to personal-assistant assumptions?
17. What is the smallest plausible Catalyst invocation seam?
18. What state/provenance/identity information would Catalyst need to govern Waku without owning its internals?
19. What would be lost by wrapping Waku unchanged?
20. What accidental architecture would be inherited by copying Waku wholesale?

## 9. Functional Decomposition Rules

Decomposition MUST be responsibility-first, not file-first.

Each material functional unit should record:

```text
functional_unit_id
name
problem_solved
observable_behavior
responsibility_owner
inputs
outputs
state_read
state_written
external_dependencies
implementation_locations
public_or_private_boundary
evidence_refs
replaceability
coupling
confidence
```

A functional unit should exist only when it has independent explanatory or reuse value.

Do not split one coherent responsibility into many pseudo-assets merely because it spans several files.

Do not merge clearly replaceable responsibilities merely because Waku implements them in one file.

## 10. Mechanism Classification

Each material mechanism must be classified as one of:

```text
LEARN_HIGH_VALUE_PATTERN
POTENTIAL_CASE_LOCAL_REUSE
POTENTIAL_INTEGRATION_SEAM
WAKU_SPECIFIC_IMPLEMENTATION
REFERENCE_ONLY
UNKNOWN_NEEDS_EVIDENCE
```

Classification must include evidence and responsibility reasoning.

## 11. Governed Asset Candidate Record

Only mechanisms with independent future value may become asset candidates.

Each stored asset candidate must minimally contain:

```text
asset_id
asset_name
asset_type
problem_solved
mechanism_summary
responsibility_boundary
source_system = waku-agent
source_commit = 8328f567ab52d07921445cb40feed23cbc5ea2ad
source_evidence
inputs
outputs
state_semantics
dependencies
replaceability
reuse_preconditions
known_limits
Waku_specific_assumptions
Catalyst_reconstruction_notes
classification
confidence
```

The record MUST NOT contain copied Waku implementation code except tiny evidence excerpts where legally and technically appropriate.

Asset candidates are **knowledge assets**, not Platform components.

## 12. Asset Catalog & Discovery Test

CASE 02-A must create one minimal machine-readable catalog:

```text
CASE_02_WAKU_ASSET_CATALOG_V0.1.json
```

The catalog is Case-local and has no Platform-Core authority.

After the catalog is frozen, perform a separate discovery pass that is not allowed to reread the Waku source repository.

The discovery pass receives new need statements such as:

```text
"I need a way to avoid retrieving memory on every Agent turn."
"I need a minimal reason → tool → observe → reason loop with hard termination."
"I need release decisions to combine deterministic checks with model-based quality evaluation."
```

These are discovery probes, not expected decomposition answers.

For each probe, return:

```text
matched_asset_ids
why_relevant
reuse_preconditions
why_not_directly_platform_core
next_action_if_reuse_is_authorized
```

PASS requires that relevant stored assets can be rediscovered from their records without rescanning Waku source.

No reconstructed capability is executed in CASE 02-A.

## 13. Responsibility Decomposition

At minimum distinguish:

```text
Waku product behavior
Waku private HOW
Agent-level responsibility
Domain-independent mechanism
state/memory responsibility
evaluation/ops responsibility
gateway/interface responsibility
execution/runtime-like responsibility
potential Catalyst-governed seam
potential Catalyst concern that should remain external
```

Do not force Waku's directory structure into Catalyst's responsibility model.

## 14. Integration Surface Assessment

Assess but do not implement:

```text
POST /api/chat
POST /api/chat/stream
CLI invocation
trace/event output
state/provenance observation
```

For each, assess:

- request/result stability;
- identity/attribution;
- failure semantics;
- state side effects;
- observability;
- authentication/security assumptions;
- replaceability;
- minimum future adapter responsibility.

## 15. CASE 01 Method-Portability Check

CASE 02-A is the second independent Agent test of the Catalyst Understanding / Deconstruction method.

Classify:

```text
METHOD_PORTABLE
METHOD_PORTABLE_WITH_REPAIR
INSUFFICIENT_EVIDENCE
METHOD_NOT_PORTABLE
```

This result does not create a generic Understanding service/API.

## 16. Minimal Long-lived Outputs

Keep artifact count small.

Required outputs only:

```text
01_WAKU_UNDERSTANDING.md
02_WAKU_MECHANISM_DECONSTRUCTION.md
CASE_02_WAKU_ASSET_CATALOG_V0.1.json
03_CASE_02_A_REVIEW.md
```

`01` = product / lifecycle / functional responsibility recovery.

`02` = functional decomposition, mechanism value classification, what to learn, what not to inherit, candidate integration seams.

`ASSET_CATALOG` = only high-value, independently reusable mechanism records.

`03` = external-review candidate verdict, method portability, asset-discovery results, unresolved questions, Case 02-B boundary.

Do not create duplicate evidence index / summary / conformance / architecture-map documents.

## 17. Acceptance Criteria

CASE 02-A passes only if:

- pinned Waku source identity is verified;
- declared intent is separated from implementation;
- major responsibilities are recovered;
- decomposition is functional/responsibility-based rather than file-tree based;
- Waku-specific HOW is separated from reusable mechanism knowledge;
- only justified high-value mechanisms become asset candidates;
- each asset has evidence, boundaries, dependencies and reuse preconditions;
- asset rediscovery succeeds without rereading Waku source;
- no stored asset is incorrectly promoted to Platform Core;
- at least one integration seam is assessed or evidence rejects all;
- Waku remains unmodified;
- Catalyst Platform / Runtime / main remain unchanged;
- unknown / NOT LIVE-VERIFIED behavior remains explicit;
- method-portability status is evidence-backed;
- no Case 02-B implementation begins.

## 18. STOP Conditions

STOP if the Stage requires:

- Waku mutation;
- Catalyst Core/Runtime change;
- copied Waku implementation as the only way to preserve value;
- expected decomposition seeding;
- turning the asset catalog into a universal Platform registry;
- implementing reconstructed assets during this Stage.

## 19. Exit / Next-stage Boundary

CASE 02-A ends:

```text
UNDERSTAND
→ FUNCTIONALLY DECOMPOSE
→ CLASSIFY
→ ASSETIZE HIGH-VALUE KNOWLEDGE
→ FREEZE CATALOG
→ REDISCOVER FROM NEW NEED
→ ASSESS INTEGRATION SURFACE
→ METHOD-PORTABILITY VERDICT
→ STOP
→ EXTERNAL REVIEW
```

Successful CASE 02-A does NOT authorize integration or reconstruction.

Only after external review may CASE 02-B choose exactly one next proof, for example:

```text
A. bounded unchanged-Waku wrapper/integration proof
B. select one catalog asset → Catalyst-native reconstruction → callable proof
C. state/provenance governance proof
D. no further adoption if evidence does not justify it
```

The preferred Case 02-B should be selected from evidence, not pre-decided here.
