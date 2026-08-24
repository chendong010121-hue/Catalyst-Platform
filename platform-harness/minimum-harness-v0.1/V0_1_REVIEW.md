# Catalyst Platform Minimum Harness V0.1 — Integrated Review

Final verdict: **MINIMUM_HARNESS_V0_1_TARGETED_REPAIR**

## Proof status

| Proof | Status | Evidence boundary |
|---|---|---|
| H-00 | PASS | Harness development responsibilities are explicitly separated from Runtime loop/session/capability semantics. |
| H-01 | PASS | Session/task/workspace/model identity and start/final status are bound in result and trace. |
| H-02 | PASS | Traversal, absolute outside paths, and symlink escape are rejected; symlink test is skipped only when the host cannot create symlinks. |
| H-03 | TARGETED_REPAIR | Scripted provider uses the same ModelProvider request path; live status is `UNAVAILABLE` with provider `DeepSeekModelProvider`. |
| H-04 | PASS | Only read, write, and command are model-visible; all are Workspace/task bounded. |
| H-05 | PASS | External approval allow/deny paths are tested; the model has no approval field or authority. |
| H-06 | PASS | The supplied unittest command actually runs; model text alone cannot complete a task. |
| H-07 | PASS | A failed initial verification receives actual evidence and permits at most one repair cycle. |
| H-08 | PASS | Representative JSON trace reconstructs task start, model turn, read, mutation proposal, approval, mutation result, verification, repair, and final result. |
| H-09 | PASS | No governance, Git, Platform, Case, admission, promotion, or replacement operation exists in the task/tool contract. |
| H-10 | PASS | Reuse/model/tool/private implementation classifications are recorded below and in results. |

## H-00 / H-10 classification

- `ModelProvider`: REUSED EXISTING NEUTRAL CONTRACT
- `HarnessSession`: HARNESS RESPONSIBILITY
- `DeepSeekModelProvider`: MODEL-SPECIFIC ADAPTER
- `WorkspaceBoundary`: PRIVATE IMPLEMENTATION HOW
- `read/write/command`: TOOL-SPECIFIC IMPLEMENTATION

The Harness does not wrap or alias the accepted Runtime loop, Runtime Session, Agent-facing Capability interface, or Runtime execution-certainty semantics. File/shell/test operations remain Harness Environment infrastructure. Trace is Stage-local evidence, not a Platform Trace standard.

## Verification and boundaries

- Deterministic test command: `python -m unittest discover -s tests -p 'test_*.py' -v`
- Deterministic result: 8 passed, 1 skipped, 0 failed, 0 errors.
- Live proof: `UNAVAILABLE`; provider identity: `DeepSeekModelProvider`.
- Credential source is `DEEPSEEK_API_KEY` only; the key is not stored, traced, or printed.
- Changed-path boundary: PASS; protected boundary: UNCHANGED.

## Failure semantics

The implementation keeps TASK_INVALID, WORKSPACE_VIOLATION, APPROVAL_DENIED, MODEL_FAILED, TOOL_FAILED, COMMAND_TIMEOUT, VERIFICATION_FAILED, REPAIR_EXHAUSTED, and TRACE_INCOMPLETE distinguishable. These are Harness-stage classes and do not redefine Runtime execution-certainty semantics.

**MINIMUM_HARNESS_V0_1_TARGETED_REPAIR**
