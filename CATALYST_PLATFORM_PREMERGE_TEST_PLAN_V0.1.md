# CATALYST PLATFORM V0.1 — PRE-MERGE TEST PLAN

> **Status:** EXECUTION PLAN
> **Target candidate:** `b06dea42365ab3caaf7a10d528f7209958be6d19`
> **Merge gate:** ALL CRITICAL TESTS PASS
> **Method:** falsification first; same responsibility, not same implementation.
> **Scope:** self-audit + internal controlled tests + external heterogeneous comparison/tests + replacement/failure tests.
> **No architecture expansion is authorized by this plan.**

## 1. Testing principle

Catalyst is not being tested to prove that "the platform is good." It is being tested to discover:

```text
which responsibility is actually proven;
which component is replaceable;
which failure belongs to which layer;
which capability survives implementation replacement;
which claims remain unproven;
whether external project patterns expose a gap in Catalyst.
```

A failure must be attributed before repair. A test finding does not automatically authorize a new Platform object/service.

## 2. External comparison baseline

The same responsibility classes are compared against mature external approaches:

- Anthropic: simplest sufficient solution; workflows have predefined paths, agents dynamically direct process/tool use.
- LangGraph/LangChain: workflow vs agent separation; unit tests with in-memory state/checkpointers; integration tests for real components; trajectory evals for agentic behavior; multi-agent only when justified.
- OpenAI Agents SDK: deterministic provider-neutral doubles for SDK-owned orchestration; real providers/integration environments for provider-owned behavior; model quality belongs in evals.
- Inspect AI: Task = dataset + solver + scorer; scorer/eval machinery separated from the agent; logs preserve run evidence; solvers/tasks are replaceable.
- Backstage: discoverability through source-controlled metadata close to authoritative source; catalog helps discovery rather than replacing source truth.
- MCP: prompts/resources/tools have different control semantics; tool protocol identity is not the same as an organizational Capability identity.
- Case02 Waku: external complete Agent can be understood/harvested while preserving provenance and without making the original Agent form permanent.

These are comparison mechanisms, not Catalyst architecture authority.

## 3. Test waves

### WAVE A — SELF AUDIT

| ID | Test | Critical | Proof |
|---|---|---:|---|
| SA-01 | Architecture boundary audit | YES | static boundary assertions + existing regression |
| SA-02 | Duplicate-responsibility audit | YES | no duplicate Core/Registry/Eval/Harness service surface |
| SA-03 | Replaceability audit | YES | implementation/provider/harness-facing replacement proof |
| SA-04 | False-claim audit | YES | explicit non-claims + no status/health overclaim |

### WAVE B — INTERNAL CONTROLLED TESTS

| ID | Test | Critical | Expected |
|---|---|---:|---|
| IT-01 | Simple Capability reuse | YES | reuse `compose_report@1.0.0`, deterministic implementation |
| IT-02 | Fixed workflow | YES | Workflow / ordinary orchestration, not Agent |
| IT-03 | True adaptive Agent | YES | Agent selected only because next action depends on observations |
| IT-04 | Case01 professional need | YES | reuse evidence; solution form stays undecided while professional binding remains unproven |
| IT-05 | Case02/WAKU-A01 harvest reuse | YES | reusable asset found without requiring original Waku Agent code |
| IT-06 | Failure attribution matrix | YES | resolution / conformance / runtime-certainty / product-quality failures remain distinct |

### WAVE C — EXTERNAL HETEROGENEOUS TESTS

| ID | External analogue | Critical | Catalyst expectation |
|---|---|---:|---|
| ET-01 | Waku Agent | YES | Agent form disposable; harvested capability/knowledge remains discoverable |
| ET-02 | LangGraph fixed workflow | YES | predetermined graph classified as Workflow, not Agent ontology |
| ET-03 | MCP server/tool surface | YES | MCP = interoperability mechanism; tool != automatic Catalyst Capability |
| ET-04 | Simple external procedure/Skill | YES | keep as Skill when procedure is sufficient |
| ET-05 | Multi-agent pattern | YES | do not inherit multi-agent shape unless distinct dynamic responsibilities require it |

### WAVE D — REPLACEMENT / FAILURE TESTS

| ID | Test | Critical | Expected |
|---|---|---:|---|
| RT-01 | Harness-facing decision replacement | YES | downstream can consume equivalent decision semantics without depending on current Skill implementation |
| RT-02 | ModelProvider replacement | YES | same Runtime/Reasoner contract survives provider implementation swap |
| RT-03 | Capability implementation replacement | YES | stable Platform WHAT survives replaceable Runtime HOW |
| RT-04 | Original Agent absence | YES | harvested Waku value remains discoverable without local Waku implementation |

## 4. Merge gate

Merge is permitted only if:

```text
- all critical test IDs are PASS;
- existing Runtime regression remains PASS;
- Platform Standard Core remains PASS;
- Capability Contract Conformance remains PASS;
- Enterprise Extension regression remains PASS;
- new tests do not require Platform Core expansion;
- no finding is classified FIX NOW;
- any remaining limitation is explicit and does not contradict the V0.1 delivery claim.
```

If a test fails:

```text
OBSERVED FAILURE
→ identify owning responsibility
→ repair/replace only that component
→ rerun smallest affected proof
→ rerun full regression before merge
```

## 5. Result format

Every executed test is reported as:

```text
TEST ID
TARGET
EXPECTED
OBSERVED
EVIDENCE TYPE
EXTERNAL COMPARISON
FAILURE OWNER (if any)
UNPROVEN BOUNDARY
VERDICT: PASS / PARTIAL / FAIL / UNPROVEN
```

The final report must distinguish deterministic CI proof from architecture/comparative review evidence.
