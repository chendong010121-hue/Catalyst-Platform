# CATALYST MINIMUM USABLE V0.2 — STAGE SPEC

> Status: IMPLEMENTATION / LIVE-USE CANDIDATE
> Base: `main@bdbb7c202b0bf2c1fd58e7e20f296530ded74c38`
> Goal: reach the minimum practical Harness capability range demonstrated by Penguin Harness without copying its Agent-centric ontology or product UI.

## 1. User-level outcome

V0.2 is accepted only when Catalyst can perform this loop on real user-like tasks:

```text
real need
→ construct/select a solution
→ design a multi-case capability benchmark
→ execute the solution with a REAL model API
→ use a REAL external API/tool when the task requires it
→ preserve answer/tool/usage/step evidence
→ score against hidden evaluation requirements
→ diagnose the capability gap
→ define a bounded improvement candidate
→ re-evaluate / accept or rollback
```

Fake/scripted providers remain valid for deterministic regression but cannot satisfy the live-use gate.

## 2. Penguin capability-range mapping

Catalyst V0.2 must cover the responsibility range of Penguin's current:

```text
agent-initialization
benchmark-design
agent-evaluation
agent-optimization
Trace/evidence feedback
```

Catalyst translation is deliberately solution-form neutral:

```text
agent-initialization
→ existing capability-first construction method

benchmark-design
→ capability-benchmark-design Skill

agent-evaluation
→ capability-evaluation Skill + case-local live runner

agent-optimization
→ capability-optimization Skill

Trace
→ existing Runtime step/model/tool evidence + evaluation artifact
```

This does NOT authorize a Benchmark Service, Evaluation Service, Optimizer Service, Registry, UI, database, or new Platform Core object.

## 3. Live API gate

At least one accepted live campaign must use:

1. a real OpenAI-compatible model endpoint through `ModelProvider → LLMReasoner → Runtime`;
2. a real external read-only API invoked by the running solution when local evidence is insufficient;
3. real provider/model identity and token usage when the provider returns usage;
4. persisted per-case outputs and step/tool evidence;
5. an explicitly selected and frozen provider/model configuration for the campaign;
6. no automatic substitution of a different model when the selected provider credential is unavailable.

Default supported live configuration:

```text
CATALYST_LIVE_API_KEY
CATALYST_LIVE_BASE_URL
CATALYST_LIVE_MODEL
```

A repository may map these to DeepSeek or another OpenAI-compatible provider. Credentials are never committed.

Missing credentials mean the formal live gate is **BLOCKED**, not silently replaced by a fake provider, a local model, or another provider/model. A local Ollama endpoint may be used as a separately identified plumbing/diagnostic run when deliberately selected, but an automatically provisioned local fallback cannot establish the Formal Baseline for a different intended provider/model.

The live workflow is opt-in. Normal deterministic CI must remain runnable without model credentials. A PR may not be accepted as V0.2 complete until at least one explicit live campaign has been separately verified.

## 4. First real-user capability probe

The first V0.2 live benchmark is deliberately generic but structurally equivalent to the Case01 concerns:

```text
natural-language user question
local evidence when available
source authority / conflict handling
local-first behavior
real remote authoritative fallback when local evidence is absent
bounded natural-language answer
fail closed when the authoritative evidence does not establish the claim
```

The remote authority in the first probe is the repository's own current README reached through the real GitHub REST API. This proves the machinery before applying it to professional-regulation web sources.

## 5. Acceptance boundary

V0.2 may claim MINIMUM USABLE only if:

- deterministic regression stays green;
- an explicitly identified live provider/model campaign actually executes;
- at least one case actually invokes the real external API;
- outputs are saved as evidence artifacts;
- critical gates distinguish execution success from answer quality;
- infrastructure failure is distinguishable from capability/product failure;
- a Formal Baseline is established from a valid frozen campaign;
- at least one bounded evidence-driven Candidate is re-evaluated against the frozen benchmark and accepted or rolled back;
- no architecture expansion is required to make the proof pass.

It may NOT claim:

- production enterprise readiness;
- production monitoring;
- automatic universal capability discovery;
- complete Case01 professional capability;
- full Penguin desktop/web UX parity;
- arbitrary provider parity;
- autonomous self-improvement without bounded review/evidence.
