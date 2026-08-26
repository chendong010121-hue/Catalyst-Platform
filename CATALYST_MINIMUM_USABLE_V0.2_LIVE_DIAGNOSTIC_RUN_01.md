# CATALYST MINIMUM USABLE V0.2 — LIVE DIAGNOSTIC RUN 01

> Status: DIAGNOSTIC EVIDENCE — NOT FORMAL BASELINE
> Branch: `stage/catalyst-minimum-usable-v0.2`
> Tested branch SHA: `ddcb2d8e5b1aaba896d6945f67b65364b4e16784`
> Workflow run: `32963012218`
> Provider mode: automatically provisioned local Ollama HTTP API
> Model: `qwen3:1.7b`
> External tool: real read-only GitHub REST API

## 1. Why this run matters

This was the first V0.2 campaign to get past repository checkout, real-model API startup, import/path integration, and into actual multi-case Runtime execution.

It therefore provides useful engineering and capability evidence, but it is **not** a valid Formal Baseline because the selected external provider credential was absent and the workflow automatically substituted a different local model. That substitution changes a material campaign variable.

The Stage Spec and live workflow have subsequently been corrected so that a formal live campaign requires an explicitly selected and frozen provider/model. Missing credentials now mean **LIVE_GATE_BLOCKED**, not automatic provider/model substitution.

## 2. Deterministic track

The deterministic regression campaign for the same candidate passed.

Observed state:

```text
compile                    PASS
minimal loop               PASS
V0.1 regression surfaces   PASS
V0.2 deterministic surface PASS
full regression workflow   PASS
```

This supports the conclusion that the V0.2 live failure was not caused by a general regression of the accepted V0.1 Runtime/Platform skeleton.

## 3. Live plumbing proof

The workflow successfully provisioned a real local Ollama API and a real model responded to a direct probe with:

```text
LIVE_API_OK
```

The V0.2 benchmark runner then executed through the repository import path and produced persistent evidence artifacts.

This proves that the live execution seam can reach a real model HTTP API. It does **not** prove that `qwen3:1.7b` is an accepted provider/model for the V0.2 Formal Baseline.

## 4. Case results

### UC-001 — local grounded

```text
PASS
score: 100
external API calls: 0
```

Observed behavior:

- correctly used sufficient local evidence;
- correctly stated `Rich ecosystem, small constitutional core`;
- did not call the remote API unnecessarily.

This is valid positive capability evidence for local-first behavior under this diagnostic model.

### UC-002 — remote fallback

```text
INFRASTRUCTURE_FAILED
```

Top-level recorded error:

```text
RuntimeExecutionError
```

The current runner preserved only the wrapper error, not the chained underlying exception. Therefore the evidence does **not** support claiming whether the owner is provider timeout, native tool-call protocol compatibility, Runtime, or external API.

No architecture change is authorized from this result.

### UC-003 — fail closed

```text
FAIL
score: 0
```

The answer correctly refused to invent a customer count and explicitly said the evidence was insufficient.

However, the case required the current repository authority to be checked and the solution made no `github_repo_read` call.

Therefore the FAIL is correct. The benchmark gate must **not** be relaxed merely because the final wording happened to be cautious.

Observed capability gap:

```text
The solution can produce cautious language without actually performing the required evidence acquisition.
```

This is exactly the shortcut behavior the benchmark is intended to distinguish.

### UC-004 — authority conflict

```text
INFRASTRUCTURE_FAILED
```

The underlying cause was not preserved. No architecture conclusion is authorized yet.

### UC-005 — current-state multi-tool

```text
INFRASTRUCTURE_FAILED
```

The underlying cause was not preserved. One plausible hypothesis is native multi-tool protocol incompatibility because the current `LLMReasoner` native-tools protocol accepts at most one tool call per model turn, but this hypothesis is **not proven by Run 01 evidence** and must not be treated as the diagnosis until the chained error is captured.

## 5. Run summary

```text
passed:                  1 / 5
product/capability fail: 1
infrastructure failed:   3
```

The run duration and per-case durations also suggest that the CPU-local diagnostic model is not an appropriate default PR acceptance provider, but performance alone is not the reason this run is excluded from the Formal Baseline. The decisive reason is automatic provider/model substitution.

## 6. Architectural verdict

```text
V0.1 architecture regression        NO EVIDENCE OF REGRESSION
real model seam                     PROVEN AT DIAGNOSTIC LEVEL
real external-tool capability       NOT YET PROVEN END-TO-END
benchmark discrimination            PROVEN BY UC-003
Formal Baseline                     NOT ESTABLISHED
Optimization authorization          NOT YET
Platform Core expansion             NOT AUTHORIZED
Runtime redesign                    NOT AUTHORIZED
```

## 7. Required next actions

1. Keep deterministic regression green.
2. Preserve the corrected explicit-provider live gate.
3. Improve live failure evidence so chained infrastructure causes are visible without changing Runtime semantics.
4. Run one frozen campaign using an explicitly selected capable provider/model and the real GitHub REST tool.
5. Establish the first Formal Baseline only from that valid campaign.
6. Only after the Formal Baseline exists, form a bounded Candidate from observed capability evidence and re-evaluate against the same frozen benchmark.
7. Accept or rollback the Candidate based on evidence.

## 8. Subsequent hardening

After Run 01, the live evaluator was changed to use explicit `Runtime.create → Runtime.run` rather than the convenience `Runtime.start` wrapper. This preserves Runtime semantics while allowing the evaluator to record the underlying exception type and a bounded failure snapshot (session id, history length, pending state, last decision/observation, model finish reason and tool-call names/count) on a future valid campaign.

The deterministic V0.2 regression now also protects the explicit-provider / opt-in live gate and forbids reintroducing an automatic Ollama fallback.

## 9. Mainline interpretation

Run 01 is a successful **diagnostic milestone**, not a failed V0.2 conclusion.

It moved Catalyst from “can the live machinery even execute?” to the more useful question:

> Given a frozen real provider/model and real external tool, what user capability is actually observed, where does it fail, and can a bounded evidence-driven change improve it?
