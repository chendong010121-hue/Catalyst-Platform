# CASE 02-A — Waku External Agent Understanding & Deconstruction
## Stage Spec V0.1

> Status: STAGE SPEC — READY FOR EXTERNAL REVIEW / AUTHORIZATION
> Implementation Authorization: NO
> Case Branch: `case-02`
> Source Agent: `ShenSeanChen/waku-agent`
> Source Commit: `8328f567ab52d07921445cb40feed23cbc5ea2ad`
> Source Treatment: MATURE EXTERNAL REFERENCE SYSTEM + MECHANISM DONOR + POTENTIAL INTEGRATION TARGET

## 1. Purpose

CASE 02-A tests whether Catalyst can understand and deconstruct a mature, substantially complete external Agent without importing that Agent's architecture as Catalyst authority.

The goal is not to repair Waku and not to clone Waku into Catalyst.

The goal is to recover, from source evidence:

- Waku's real product purpose and user promise;
- its actual executable architecture and lifecycle;
- its major capability/mechanism boundaries;
- its state, memory, trace, tool, gateway, model/provider and evaluation responsibilities;
- the mechanisms that are valuable to learn;
- the implementation choices that are Waku-specific rather than generally required;
- the smallest plausible Catalyst integration seam, if one exists;
- the evidence still missing before any integration or adoption may be authorized.

This Stage also acts as a second-Agent portability test for the Agent Understanding / Deconstruction method previously exercised in CASE 01.

## 2. Core Principle

```text
LEARN THE MECHANISM
!=
INHERIT THE ARCHITECTURE
```

Waku may demonstrate strong engineering patterns.
It does not automatically define Catalyst Platform, Runtime, Agent, Memory, Tool, Evaluation or Domain architecture.

## 3. Source Baseline

Canonical source under review:

```text
repository: https://github.com/ShenSeanChen/waku-agent.git
branch: main
commit: 8328f567ab52d07921445cb40feed23cbc5ea2ad
```

Known local deployment baseline may be used as operational evidence, but source claims and implementation claims must be independently checked against the pinned repository commit.

The source repository is READ-ONLY for this Stage.

## 4. Scope

CASE 02-A may inspect and execute read-only/local verification of:

- README / architecture documentation;
- CLI / Dashboard / local HTTP surfaces;
- Agent loop;
- model/provider abstraction;
- memory system;
- retrieval gate / consolidation;
- tools and optional MCP boundary;
- graph/workflow layer;
- local persistence/state;
- traces / usage / observability;
- deterministic eval / judge eval / release gate;
- gateway/channel handling;
- source tests and package configuration;
- declared extension/configuration surfaces.

## 5. Non-goals

CASE 02-A MUST NOT:

- modify Waku source;
- fork Waku;
- create a Catalyst adapter;
- register Waku in Catalyst;
- modify Platform Core;
- modify Catalyst Runtime or RuntimeAdapter;
- create a new generic Memory/Tool/Workflow/Agent standard;
- copy Waku modules into Catalyst;
- claim a Waku pattern is reusable merely because Waku implements it;
- require a live DeepSeek credential merely to complete structural understanding;
- optimize or repair Waku;
- redesign CASE 01;
- generalize from two Cases into Platform Core without later evidence.

## 6. Allowed Actions

```text
inspect
run local read-only smoke tests
read source/tests/docs
trace responsibility flow
compare declared vs implemented behavior
classify mechanisms
identify integration surfaces
record evidence
```

If a live LLM key is unavailable, mark live model-dependent behavior as `NOT LIVE-VERIFIED`; do not fabricate execution evidence.

## 7. Required Understanding Questions

CASE 02-A must answer at minimum:

1. What is Waku's actual user-facing product promise?
2. What are its real entry/gateway surfaces?
3. What owns the Agent loop and termination semantics?
4. How are model providers abstracted and selected?
5. What state is ephemeral vs durable?
6. How are semantic, episodic and procedural memory separated?
7. What decides whether memory is retrieved?
8. How and when is memory consolidated or updated?
9. How are tools registered, invoked and traced?
10. What role do graph workflows play relative to the normal loop?
11. What evidence/trace is produced per turn?
12. How do deterministic evaluation, LLM-as-judge and release gating differ?
13. Which capabilities are essential to Waku's product and which are optional?
14. Which boundaries are explicit/public and which are private implementation seams?
15. Which mechanisms appear reusable beyond Waku?
16. Which mechanisms are tightly coupled to Waku's personal-assistant assumptions?
17. What is the smallest plausible invocation/integration seam with Catalyst?
18. What state/provenance/identity information would Catalyst need to govern Waku without owning Waku internals?
19. What would be lost if Waku were wrapped unchanged?
20. What would be accidentally inherited if Catalyst copied Waku architecture wholesale?

## 8. Mechanism Classification

Each material Waku mechanism should be classified as one of:

```text
LEARN / HIGH-VALUE PATTERN
POTENTIAL CASE-LOCAL REUSE
POTENTIAL INTEGRATION SEAM
WAKU-SPECIFIC IMPLEMENTATION
REFERENCE ONLY
UNKNOWN / NEEDS EVIDENCE
```

Classification MUST include evidence and responsibility reasoning.

## 9. Responsibility Decomposition

At minimum distinguish:

```text
Waku product behavior
Waku private implementation HOW
Agent-level responsibility
Domain-independent reusable mechanism
Execution/runtime-like responsibility
State/memory responsibility
Evaluation/ops responsibility
Gateway/interface responsibility
Potential Catalyst-governed seam
Potential Catalyst concern that should remain external
```

Do not force Waku's directory structure to become Catalyst's responsibility model.

## 10. Integration Surface Assessment

Assess, but do not implement, at least these candidate seams:

```text
POST /api/chat
POST /api/chat/stream
CLI invocation
trace/event output
state/provenance observation
```

For each, determine:

- request/result stability;
- identity/attribution availability;
- failure semantics;
- state side effects;
- observability;
- authentication/security assumptions;
- replaceability;
- minimum adapter responsibility if later authorized.

The output may conclude that no integration seam is yet acceptable.

## 11. CASE 01 Method-Portability Check

CASE 02-A is also a second-Agent method test.

It must record whether the existing Catalyst understanding/deconstruction method can recover a materially correct Waku model without seeding an expected decomposition.

At minimum classify:

```text
METHOD PORTABLE
METHOD PORTABLE WITH REPAIR
INSUFFICIENT EVIDENCE
METHOD NOT PORTABLE
```

Do not promote a generic Catalyst Understanding service/API merely from this result.

## 12. Minimum Outputs

Keep the artifact surface minimal.

Required long-lived outputs only:

```text
01_WAKU_UNDERSTANDING.md
02_WAKU_MECHANISM_DECONSTRUCTION.md
03_CASE_02_A_REVIEW.md
```

`01` should contain product/architecture/responsibility recovery.

`02` should contain mechanism classification, what Catalyst can learn, what must not be inherited, and candidate integration seams.

`03` should contain evidence-backed verdict, method portability result, unresolved questions and Case 02-B entry boundary.

Do not create separate evidence-index, conformance, summary, architecture-map, trace-report or duplicate review documents unless a distinct decision cannot be supported otherwise.

## 13. Acceptance Criteria

CASE 02-A passes only if:

- source commit identity is verified;
- declared intent is separated from implemented behavior;
- major loop/memory/tool/state/eval/gateway responsibilities are recovered;
- Waku-specific implementation is separated from potentially reusable mechanism;
- no external architecture is silently adopted as Catalyst authority;
- at least one plausible integration seam is assessed, or evidence supports rejecting all current seams;
- source remains unmodified;
- Catalyst Platform/Runtime/main remain unchanged;
- unknowns and non-live-verified behavior are explicit;
- method-portability status is evidence-backed;
- no Case 02-B implementation is started.

## 14. STOP Conditions

STOP immediately if understanding requires:

- modifying Waku;
- changing Catalyst Core/Runtime;
- assuming missing credentials imply functionality;
- seeding the expected architecture decomposition;
- importing Waku code as the only way to understand its behavior.

## 15. Exit / Next-stage Boundary

Successful CASE 02-A does NOT authorize integration.

CASE 02-A ends with:

```text
UNDERSTAND
→ DECONSTRUCT
→ CLASSIFY
→ ASSESS INTEGRATION SURFACE
→ METHOD-PORTABILITY VERDICT
→ STOP
→ EXTERNAL REVIEW
```

Only after external review may CASE 02-B be defined.

Possible CASE 02-B directions include, but are not pre-authorized here:

```text
bounded unchanged-Waku integration proof
specific mechanism reconstruction under Catalyst contracts
state/provenance governance proof
or no integration if the evidence does not justify one
```
