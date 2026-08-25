# CATALYST PLATFORM — HARNESS INFRASTRUCTURE GAP REVIEW V0.1

> **Status:** ARCHITECTURE / INFRASTRUCTURE GAP REVIEW
> **Implementation Authorization:** **NO**
> **Platform Integration Authorization:** **NO**
> **Branch:** `platform-harness`
> **Base:** `3ec8cfe2c1d2ebba60aaf1ef5331ae025f347be6`
> **Trigger:** Minimum Harness V0.1 passed, but the H-03 live proof exposed avoidable process-local credential/environment friction before the first real Case 01 trial.

---

# 0. Review Question

Before using the frozen Minimum Harness V0.1 on a real Case 01 development task, which foundational infrastructure responsibilities are repeatedly present in mature Harnesses and are actually missing from Catalyst's current proof?

The objective is **not feature parity**.

The objective is:

```text
close only the infrastructure gaps that would make the next real governed task
fragile, unsafe, process-dependent, or difficult to reproduce.
```

---

# 1. External Reference Set

External systems are mechanism evidence, never Catalyst architecture authority.

## DeepSeek Harness

Pinned research source:

```text
deepseek-ai/deepseek-harness
master @ b150a551b8d465e31e418e1b2eaf5e79bbb7d28e
```

Relevant evidence:

```text
docs/user/guide/providers.md
packages/credentials/credentials-local/README.md
docs/subsystems/shell.md
docs/subsystems/session.md
docs/subsystems/permission-presets.md
docs/capability-seams.md
packages/bundle/base/cordis.patch.yml
.github/workflows/e2e.yml
```

Observed infrastructure responsibilities:

- provider settings are separate from credential values;
- configuration stores credential references rather than secret values;
- credentials can resolve from launch environment and a Harness-home credential document;
- credential values are write-only / redacted at UI boundaries;
- credential resolution can occur without restarting the whole Harness;
- model routes are independently configurable;
- shell environment is a managed per-execution namespace rather than an uncontrolled copy of Harness-owned environment facts;
- sandbox policy and approval policy are independent controls;
- sessions are append-only event histories with separate persistence / recovery seams;
- CI performs explicit credential preflight so missing live credentials cannot become false-green skipped tests.

## OpenAI Codex

Pinned public source snapshot used for this review:

```text
openai/codex
main @ cbfd999db78cb088d2bd89b52051efe6f44555a4
```

Relevant evidence:

```text
codex-rs/core/config.schema.json
codex-rs/app-server/README.md
sdk/python/src/openai_codex/api.py
```

Observed infrastructure responsibilities:

- authentication storage mode is independently configurable (`file`, `keyring`, `auto`, `ephemeral`);
- model/provider selection is configuration, not embedded task logic;
- sandbox mode and approval policy are distinct;
- file/network permission escalation is explicit and scoped;
- threads can be resumed / forked / archived;
- effective execution configuration is a first-class session concern.

## Claude Code

Reference: public Anthropic documentation.

Observed infrastructure responsibilities:

- persistent authentication rather than requiring every shell session to restate credentials;
- API-key helper / external credential retrieval is supported for rotating or enterprise credentials;
- working-directory access and allowed / disallowed tools are explicit;
- permission modes are explicit;
- sessions can continue / resume by id;
- provider/gateway configuration is separate from coding task semantics.

## OpenHands

Pinned public repository identity for reference:

```text
OpenHands/OpenHands
main @ 150e76046db026dd944df0506642dc9b7b99391e
```

Reference also includes current OpenHands SDK documentation.

Observed infrastructure responsibilities:

- secrets have a dedicated manager and are not ordinary settings;
- confirmation policy and security analysis are explicit execution controls;
- sandbox/workspace is its own infrastructure concern;
- conversation state can be persisted and restored;
- provider/configuration/environment are explicit deployment concerns.

## PenguinHarness

Pinned research source:

```text
Prism-Shadow/penguin-harness
main @ 46a26dda0b53ce98806d3de6b825020281b80597
```

Observed infrastructure responsibilities:

- Agent creates a Session bound to `workspaceDir`;
- every tool call can pass through an approval callback;
- credentials are configured outside the model conversation;
- CLI / SDK / Server share one engine;
- build/runtime identity is exposed for reproducibility;
- sessions / traces survive beyond one model response;
- API-key failures are treated as environment/configuration issues rather than prompts to expose the secret in chat.

---

# 2. Current Catalyst Minimum Harness V0.1

Already proven:

```text
HarnessSession
WorkspaceBoundary
provider-neutral ModelProvider reuse
real DeepSeek live invocation
read / write / command tool surface
external approval
bounded repair
real deterministic verification
Stage-local execution trace
explicit failure classes
governance non-inheritance
```

This is sufficient to prove a minimum governed execution mechanism.

It is **not yet sufficient as a stable real-task execution environment**.

---

# 3. Material Gaps Found

## GAP-01 — Process-local credential coupling

Observed directly during H-03 repair:

```text
PowerShell child process: DEEPSEEK_API_KEY available
already-running Codex process: DEEPSEEK_API_KEY unavailable
```

The Harness currently relies on ambient process environment for the live provider credential.

Consequences:

- a correctly configured credential can still be invisible to another already-running executor process;
- users must understand parent/child process inheritance;
- repeated local sessions can require manual reconfiguration;
- credential readiness is not a stable Harness fact.

Verdict:

```text
MUST REPAIR BEFORE REAL CASE TRIAL
```

Required direction:

```text
CredentialRef
        ↓
CredentialResolver
        ↓
replaceable credential sources
```

Minimum source classes should support:

```text
PROCESS_ENV
USER_LOCAL_CREDENTIAL_STORE
```

The Harness task receives a credential reference / provider binding, never the literal key.

Do not establish an enterprise vault or universal secret manager in this stage.

---

## GAP-02 — Provider credential may leak into tool subprocess environment

Current V0.1 command verification uses Python `subprocess.run(...)` without an explicit `env`, so child processes inherit the parent environment by default.

When the parent carries `DEEPSEEK_API_KEY`, a tool subprocess can in principle inherit the same secret.

This is a stronger issue than convenience.

Provider credential access and model-generated tool execution are different trust boundaries.

Verdict:

```text
MUST REPAIR BEFORE REAL CASE TRIAL
```

Required direction:

```text
Provider Credential Environment
!=
Tool Execution Environment
```

Commands must receive an explicit sanitized environment.

Default rule:

```text
provider API keys / tokens / secrets are NOT inherited by tool subprocesses
```

A future task may explicitly bind a task-owned secret to a tool, but this must be separate authority.

---

## GAP-03 — No execution-environment preflight

Current Harness discovers some missing requirements only when execution begins.

A mature Harness repeatedly validates environment/configuration facts before expensive execution.

Minimum preflight should answer:

```text
workspace valid?
model provider constructible?
required credential resolvable?
required executable available?
verification command resolvable?
platform/runtime identity known?
required permission/sandbox posture available?
```

Verdict:

```text
MUST REPAIR BEFORE REAL CASE TRIAL
```

Required external result:

```text
READY
or
BLOCKED + explicit missing requirements
```

No secret value may appear in the report.

---

## GAP-04 — Task permissions and approval are not yet sufficiently separated

V0.1 has path allowlists in `HarnessTask` plus an approval callback.

This works for the tiny fixture but conflates:

```text
what the task is allowed to do
with
whether a particular proposed action is approved now
```

DeepSeek, Codex, Claude Code and OpenHands all independently separate capability confinement / sandbox policy from user approval.

Verdict:

```text
REPAIR NOW, MINIMALLY
```

Required direction:

```text
ExecutionPolicy
  - allowed reads
  - allowed writes
  - allowed commands
  - network posture
  - command timeout / execution budget

ApprovalPolicy
  - approve / deny a proposal permitted by ExecutionPolicy
```

Approval must never widen ExecutionPolicy by itself.

For the next stage:

```text
arbitrary shell = NOT REQUIRED
OS/container sandbox = NOT REQUIRED
```

A strict Stage-authorized argv allowlist is sufficient for the next proof.

---

## GAP-05 — Environment / build identity is under-recorded

A real Case execution should be reviewable across machines and processes.

Minimum identity should include non-secret facts such as:

```text
Harness revision / implementation identity
Python version
OS / architecture
workspace root
provider id / model id
credential source TYPE only
permission profile / execution policy identity
```

Penguin explicitly exposes build/runtime identity; mature Harnesses also bind model, cwd and permission configuration to sessions.

Verdict:

```text
REPAIR NOW, MINIMALLY
```

This should be part of preflight / result evidence, not a new telemetry platform.

---

## GAP-06 — No durable Harness-session resume

DeepSeek Harness, Codex, Claude Code and OpenHands all support durable or resumable sessions.

Current Catalyst HarnessSession is process-local.

A crash can lose live development-loop state even though final evidence is persisted after a completed run.

Verdict:

```text
VALID GAP
DEFER BEFORE FIRST REAL CASE TRIAL
```

Reason:

The next Case 01 proof should remain intentionally bounded and short. Implementing durable resume now risks recreating Runtime session semantics before evidence proves the necessary Harness-specific recovery contract.

Record the gap; do not solve it yet.

---

## GAP-07 — No general shell / OS sandbox

Current command tool is deliberately not an arbitrary shell: it runs a Stage-supplied deterministic command.

Mature Harnesses commonly add OS/container sandboxing plus controlled network/file escalation.

Verdict:

```text
VALID GAP
DEFER WHILE COMMAND SURFACE REMAINS ALLOWLISTED
```

Before Catalyst exposes arbitrary model-authored shell commands, this becomes mandatory.

---

## GAP-08 — No cancellation / job control / background process management

Mature Harnesses support interrupt, cancellation, managed processes or jobs.

Current V0.1 has command timeout and model-attempt bounds but no user interruption contract.

Verdict:

```text
VALID GAP
DEFER FOR SHORT SINGLE-TASK PROOF
```

Promote only when a real task requires long-running or background processes.

---

## GAP-09 — No context compaction / token budget infrastructure

DeepSeek, Codex and Penguin include compaction/token-budget mechanisms; long-lived coding Harnesses need them.

Verdict:

```text
VALID GAP
DEFER
```

A short Case 01 task does not justify this yet.

---

## GAP-10 — No generic tool / plugin ecosystem

DeepSeek uses `everything is a plugin`; Claude Code supports MCP; Codex has apps/plugins/MCP; Penguin has Skills/tools.

Catalyst ultimately needs replaceable tool implementations, but V0.1 already proves a minimal tool boundary.

Verdict:

```text
DO NOT BUILD NOW
```

The Catalyst objective is not tool-ecosystem parity.

---

# 4. Cross-Harness Comparison

| Infrastructure responsibility | DeepSeek Harness | Codex | Claude Code | OpenHands | Penguin | Catalyst V0.1 | Decision |
|---|---|---|---|---|---|---|---|
| Workspace boundary | Yes | Yes | Yes | Yes | Yes | Yes | KEEP |
| Approval | Yes | Yes | Yes | Yes | Yes | Yes | KEEP |
| Sandbox/confinement distinct from approval | Yes | Yes | Yes | Yes | Planned/partial shell governance | Partial | MINIMAL REPAIR |
| Credential seam / stable credential source | Yes | Yes | Yes | Yes | Yes | Ambient env only | REPAIR NOW |
| Secret redaction / value-free config | Yes | Yes | Yes | Yes | Yes | No persistent config | REPAIR NOW |
| Provider/model configuration | Yes | Yes | Yes | Yes | Yes | Adapter supplied directly | MINIMAL BINDING ONLY |
| Tool subprocess environment control | Yes | Yes/ sandbox env | Yes / controlled tool env | Sandbox runtime | Harness-owned runtime | Inherits parent env | REPAIR NOW |
| Preflight/readiness | Yes in E2E/config UX | Config/auth validation | `doctor` + setup validation | runtime/sandbox checks | config/runtime guards | No | REPAIR NOW |
| Durable sessions / resume | Yes | Yes | Yes | Yes | Yes | No | DEFER |
| Build/runtime identity | Explicit facts | session/config/build facts | session/tool environment | runtime/config | explicit version/build report | Limited | REPAIR NOW |
| General shell sandbox | Yes | Yes | permission/sandbox modes | Docker/remote sandbox | roadmap / execution guardrails | No general shell | DEFER |
| Cancellation/jobs | Yes | Yes | Ctrl-C/session controls | execution state | Ctrl-C / sessions | timeout only | DEFER |
| Compaction/token budget | Yes | Yes | context management | condenser | Yes | No | DEFER |
| Plugin/MCP ecosystem | Plugin-native | Yes | MCP | MCP/tools | skills/tools | No | DO NOT BUILD NOW |

---

# 5. Minimal Infrastructure Completion Set

Before the first real Case 01 trial, authorize only these five additions:

```text
I-01 ExecutionEnvironmentPreflight
I-02 CredentialResolver + one user-local credential source
I-03 SanitizedToolEnvironment
I-04 ExecutionPolicy separated from ApprovalPolicy
I-05 Environment / Harness Identity Snapshot
```

These solve the material gaps without turning Catalyst into a general coding Harness.

---

# 6. Credential Storage Direction

This Review supports a **replaceable credential source chain**, not one permanent storage mechanism.

Conceptually:

```text
CredentialRef
    ↓
CredentialResolver
    ├── ProcessEnvironmentSource
    └── UserLocalCredentialSource   # initial durable local fallback
```

Future sources may include:

```text
OS keyring
enterprise vault
cloud secret manager
external helper
```

but they are not justified now.

The initial user-local store must be:

```text
outside the repository
excluded from model context
excluded from tool subprocess environment by default
redacted in describe/preflight surfaces
never committed
best-effort owner-only permissions
```

The exact home path / file format should be chosen in the Stage Spec and remain replaceable implementation HOW.

Do not promote a credential file format into Platform Core.

---

# 7. Environment Boundary Invariant

The following three environments must no longer be treated as the same thing:

```text
1. Harness Host Environment
2. Model Provider Credential Context
3. Model-authored Tool Execution Environment
```

Required direction:

```text
HOST
  ↓ resolves credential
MODEL PROVIDER

HOST
  ↓ builds sanitized env
TOOL PROCESS
```

No automatic reverse or cross-flow.

In particular:

```text
DEEPSEEK_API_KEY visible to provider
DOES NOT imply
DEEPSEEK_API_KEY visible to pytest / PowerShell / arbitrary tool command
```

---

# 8. What Must Remain Deferred

Do not use this infrastructure pass to add:

```text
durable session resume
multi-agent
subagents
background jobs
arbitrary shell
OS/container sandbox
network escalation
MCP
plugin marketplace
Skill Builder
Agent Builder
Capability Registry
context compaction
automatic capability replacement
Git commit/push authority
Web UI
```

Each is valid future work but unnecessary for the immediate real Case trial.

---

# 9. Review Verdict

```text
MINIMUM HARNESS V0.1
PASS / CLOSED

CREDENTIAL PROCESS COUPLING
REAL GAP
REPAIR REQUIRED

PROVIDER SECRET -> TOOL ENV INHERITANCE
REAL SECURITY BOUNDARY GAP
REPAIR REQUIRED

EXECUTION ENVIRONMENT PREFLIGHT
REQUIRED

EXECUTION POLICY VS APPROVAL SEPARATION
MINIMAL REPAIR REQUIRED

ENVIRONMENT / BUILD IDENTITY
MINIMAL REPAIR REQUIRED

DURABLE SESSION RESUME
DEFER

GENERAL OS SANDBOX
DEFER UNTIL GENERAL SHELL

CANCELLATION / JOB CONTROL
DEFER

CONTEXT COMPACTION
DEFER

GENERIC PLUGIN ECOSYSTEM
NOT REQUIRED

PLATFORM INTEGRATION
NO

CASE 01 REAL TRIAL
WAIT UNTIL INFRASTRUCTURE COMPLETION PASS

IMPLEMENTATION AUTHORIZATION
NO
```

---

# 10. Next Deliverable

Create exactly one Stage Spec:

```text
CATALYST_PLATFORM_HARNESS_ENVIRONMENT_INFRASTRUCTURE_V0.1_STAGE_SPEC
```

It should implement and prove only I-01..I-05.

After that Stage passes and freezes, use the resulting Harness on one separately authorized low-risk Case 01 task.
