---
name: capability-evaluation
description: Execute one frozen user-capability benchmark case against a specified solution, preserve real execution evidence, score only observable behavior, and attribute failures to the owning layer.
short_description: Execute and score one capability case.
short_description_zh: 执行并评分一个真实能力案例。
version: 1
updated: 2026-08-26T17:20:00+08:00
---

# Capability Evaluation

This is a replaceable Harness-side evaluation method. It is not a Platform Evaluation Engine.

## Core rule

> A capability is proven by observable user-task evidence, not by the existence of architecture objects or passing internal contract tests.

## 1. Required inputs

Resolve exactly:

```text
target solution identity / revision
benchmark revision
case id
provider + model when a model is involved
source / knowledge revision when material
allowed external tools/APIs
```

If any identity required to interpret the result is unknown, mark the run invalid rather than silently substituting another target.

## 2. Isolation

The tested solution receives only the public case statement and public materials. It must not receive:

- private rubric / Gold;
- evaluator reasoning;
- unrelated prior case traces;
- hidden repair hints.

Preserve enough execution evidence to later reconstruct what happened.

## 3. Real vs deterministic execution

Label every run explicitly:

```text
DETERMINISTIC_REGRESSION
LIVE_MODEL_EXECUTION
LIVE_EXTERNAL_TOOL_EXECUTION
```

A scripted/fake provider may prove Harness/Runtime mechanics but MUST NOT be counted as live capability evidence.

If a live campaign requires a credential and the credential is absent, the live gate fails. Do not replace it with a fake response and report PASS.

## 4. Evidence to capture

When available, preserve:

```text
case id
target revision
provider/model
source/knowledge revision
final answer/artifacts
Runtime step history
Capability/tool calls and observations
provider finish reason/token usage
external API endpoint identity (never credentials)
duration
critical-gate results
score / verdict
failure attribution
```

Evidence artifacts may be case-local files or CI artifacts. No central Evidence Service is required.

## 5. Scoring

Score observable user behavior. Use deterministic gates for facts that can be checked exactly. A private model/human judge may score semantic quality only after deterministic critical gates are evaluated.

Wrong product output is a scored product/capability failure even when Runtime succeeded.

Infrastructure failure is not automatically score zero. Distinguish at least:

```text
resolution / capability not found
binding / conformance
model/provider transport
Runtime execution certainty
external tool/API
product/capability behavior
evaluation infrastructure
benchmark defect
```

## 6. Fail-closed tests

For high-risk or evidence-sensitive capabilities, include negative cases where the correct outcome is to refuse, ask for missing information, or state an evidence boundary.

A system that always answers is not automatically more capable.

## 7. Evaluation result

Return a case result with:

```text
status: valid | invalid | infrastructure_failed
case_id
observed_behavior
evidence_refs or artifact paths
critical_gates
score if valid
failure_owner if applicable
unproven_boundary
```

Do not decide Harvest/Admission merely because one case scored well.

## 8. STOP

Do not modify the tested solution during evaluation. Findings go to `capability-optimization` or the responsible implementation owner after the run is frozen.
