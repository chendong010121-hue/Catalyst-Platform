# Catalyst Platform Harness Environment Infrastructure V0.1

## Execution result

Candidate `CATALYST_PLATFORM_HARNESS_0_2_CANDIDATE` was executed from the current `platform-harness` workspace at HEAD `7d801bb7d84b34fb52900f58b27e9a0d1cbb1c07`.

The deterministic suite passed 11 tests with zero failures and zero errors. E-01 through E-08 and E-10 are PASS. The fresh E-09 process resolved `deepseek.default` from `USER_LOCAL`, had no `DEEPSEEK_API_KEY` in its process environment, reached `preflight=READY`, invoked the existing `DeepSeekModelProvider` with model `deepseek-v4-flash`, received model responses, executed the fixed `verify` command through ApprovalPolicy and ExecutionPolicy, and completed deterministic verification with PASS. The tool subprocess environment did not contain the provider credential.

## I-04 root cause and repair

The live failure was a bounded candidate defect classified as F, with the concrete mechanism in B/C: ExecutionPolicy stored fixed command identities such as `verify`, while the model-visible `command` schema accepted an unconstrained string. The Session then compared the model's value as an identity, so a model proposal that did not use the fixed identity was correctly denied before approval and execution. The authorized operation was not represented unambiguously enough for the model.

The minimal repair binds the command tool schema for each HarnessSession to the task's `verification_command_id` through a single-value enum. The existing fixed argv remains owned by ExecutionPolicy and the existing ApprovalPolicy decision remains required. Unknown command identities continue to produce `EXECUTION_POLICY_DENIED`; no arbitrary shell, new tool, Runtime change, sandbox claim, or policy widening was introduced.

## Evidence matrix

| Proof | Status | Sanitized evidence |
|---|---|---|
| E-01 | PASS | READY preflight without a model call |
| E-02 | PASS | Distinguishable blocked preflight reasons |
| E-03 | PASS | Fresh USER_LOCAL credential resolution with process variable absent |
| E-04 | PASS | PROCESS_ENVIRONMENT source resolution |
| E-05 | PASS | Provider and synthetic secrets absent from tool subprocess environment |
| E-06 | PASS | `verify` is executable when declared; unknown command remains policy-denied |
| E-07 | PASS | Approval still governs an otherwise policy-permitted mutation |
| E-08 | PASS | Frozen V0.1 behavior preserved by candidate regression |
| E-09 | PASS | Fresh USER_LOCAL live DeepSeek proof and deterministic verification |
| E-10 | PASS | Required non-secret identity fields present; no environment dump |

## Boundary review

The frozen Minimum Harness V0.1 tree is unchanged. No protected tracked path is changed. The candidate remains under the authorized candidate root. No repository credential was created. Results, review, and traces contain only credential source/status booleans and never contain a credential value, credential-store content, or credential-store path. The implementation does not claim filesystem, OS, container, or network sandboxing. No Platform integration, Case 01 execution, merge, or PR was performed.

The candidate is frozen for a separately authorized low-risk Case 01 review; this result does not authorize Case 01 execution or further Harness feature work.

HARNESS_ENVIRONMENT_INFRASTRUCTURE_V0_1_PASS
