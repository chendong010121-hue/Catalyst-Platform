# CATALYST PLATFORM — HARNESS ENVIRONMENT INFRASTRUCTURE V0.1 STAGE SPEC

> **Stage Spec Version:** **V0.2**
> **Status:** STAGE SPEC — TARGETED SAFETY / PROOF REPAIR COMPLETE
> **Supersedes:** Stage Spec V0.1 at commit `24a4d32458f47382319e260f0e5b17b236172251`
> **Implementation Authorization:** **NO**
> **Platform Integration Authorization:** **NO**
> **Branch:** `platform-harness`
> **Source Review:** `platform-harness/HARNESS_INFRASTRUCTURE_GAP_REVIEW_V0.1.md`
> **Frozen Source Harness:** `platform-harness/minimum-harness-v0.1/** @ 3ec8cfe2c1d2ebba60aaf1ef5331ae025f347be6`
> **Implementation Base:** must be the exact Stage-Spec commit named by a later Authorization Record
> **Purpose:** complete the minimum execution-environment infrastructure required before the first real Case 01 Harness trial, without expanding Catalyst into a general coding Harness or claiming security properties not actually enforced.

---

# 0. Stage Question

This Stage answers one question:

> Can Catalyst form a new Harness Candidate that preserves the proven Minimum Harness V0.1 behavior while adding stable credential resolution, environment preflight, provider-secret-sanitized tool subprocess environments, explicit execution policy and reproducible non-secret environment identity?

The Stage exists because Minimum Harness V0.1 proved the execution loop, but the live proof exposed real infrastructure gaps around process-local credentials and execution environment boundaries.

This Stage does **not** reopen Minimum Harness V0.1.

```text
minimum-harness-v0.1
= FROZEN EVIDENCE BASELINE

new environment-complete Harness
= NEW CANDIDATE
```

---

# 1. Candidate Identity

If authorized, this Stage forms:

```text
Catalyst Platform Harness implementation
version: 0.2-candidate
scope: ENVIRONMENT_INFRASTRUCTURE_ONLY
status: NOT PLATFORM-INTEGRATED
```

Preferred implementation root:

```text
platform-harness/harness-v0.2-candidate/**
```

The version increase reflects an implementation revision after a frozen V0.1 proof. It does **not** mean Catalyst has started a general Harness V0.2 feature program.

---

# 2. Required Infrastructure Additions

Only these five additions are in scope:

```text
I-01 ExecutionEnvironmentPreflight
I-02 CredentialResolver + user-local credential source
I-03 SanitizedToolEnvironment
I-04 ExecutionPolicy separated from ApprovalPolicy
I-05 Environment / Harness Identity Snapshot
```

Everything else remains out of scope unless a blocker proves it is strictly necessary for I-01..I-05.

---

# 3. I-01 — ExecutionEnvironmentPreflight

Before any live model call or mutating tool action, the Harness must be able to produce a machine-readable readiness result.

Minimum checks:

```text
workspace root exists and is valid
execution policy is valid
required read/write paths remain inside Workspace
verification executable is resolvable
verification command is allowed by policy
model provider binding is valid
required credential reference is resolvable
Harness / environment identity can be formed
```

External readiness state:

```text
READY
BLOCKED
```

A BLOCKED result must include explicit non-secret reasons, for example:

```text
CREDENTIAL_UNAVAILABLE
WORKSPACE_INVALID
EXECUTABLE_UNAVAILABLE
POLICY_INVALID
PROVIDER_BINDING_INVALID
```

Rules:

```text
preflight MUST NOT print secret values
preflight MUST NOT make a model request merely to prove configuration exists
preflight MUST complete before model-driven mutation begins
```

---

# 4. I-02 — CredentialResolver

## 4.1 Responsibility

Harness task/configuration must bind to a credential reference, not a literal secret.

Conceptually:

```text
ProviderBinding
  provider_id: deepseek
  credential_ref: deepseek.default

            ↓

CredentialResolver
            ↓
CredentialSource(s)
```

## 4.2 Minimum source chain

This Candidate must support exactly these source classes:

```text
1. ProcessEnvironmentCredentialSource
2. UserLocalCredentialSource
```

These are V0.2-candidate implementation options, not permanent Platform credential-source standards.

Resolution priority may be explicit configuration or a small deterministic order, but it must be observable by source **type**, never by secret value.

## 4.3 User-local credential store

The first durable local source is intentionally **local-development convenience infrastructure**, not an enterprise secret manager and not a strong sandbox boundary.

Recommended default location:

```text
Windows: %USERPROFILE%\.catalyst\credentials.json
POSIX:   ~/.catalyst/credentials.json
```

The location must be overridable for deterministic tests.

Minimum conceptual content may be equivalent to:

```json
{
  "deepseek.default": "<secret>"
}
```

The exact path, file name and representation are private implementation HOW and are **not** Platform standards.

Requirements:

```text
outside repository by default
never copied into Workspace
never included in model context
never included in trace/results/review
never printed by describe/preflight
best-effort owner-only file permissions
invalid / missing store fails explicitly
```

### Security limitation — must remain explicit

Without an OS/container sandbox, a local credential file owned by the same OS user is **not proven inaccessible to arbitrary same-user code**.

Therefore this Stage proves:

```text
credential values are not intentionally passed into model context
credential values are not intentionally passed into tool subprocess ENVIRONMENT
```

It does NOT prove:

```text
a malicious same-user process cannot discover/read the local credential store
filesystem-level secret isolation
enterprise-grade secret protection
```

This limitation is acceptable only while the next proof keeps command execution Stage-declared, bounded and non-general-shell. Before arbitrary model-authored shell or broader untrusted code execution is introduced, an actual sandbox / stronger secret boundary must be separately justified.

## 4.4 One-time interactive setup

The Candidate should provide one tiny **human-boundary** local setup entry point using hidden input (for example Python `getpass`) so the user can configure a credential once without pasting it into chat or command arguments.

Required UX behavior:

```text
human runs credential setup
→ secret entered with echo disabled
→ store written outside repo
→ confirmation prints credential ref + source type only
→ later Harness process resolves it without depending on the PowerShell that originally entered it
```

The credential-setup entry point must NOT be exposed as a model-callable Harness tool in this Stage.

Do not build a general settings UI.

## 4.5 Secret authority

Credential resolution grants only model-provider use.

It does not grant:

```text
tool subprocess environment access
model-visible secret text
task-visible secret text
Git access
Platform authority
```

---

# 5. I-03 — SanitizedToolEnvironment

Model-provider credentials and model-authored tool subprocess environments are separate trust boundaries.

Required invariant:

```text
PROVIDER CREDENTIAL CONTEXT
!=
TOOL PROCESS ENVIRONMENT
```

Every command/test subprocess must receive an explicit environment via `env=...` or equivalent.

The implementation must not rely on implicit full parent-environment inheritance.

## 5.1 Minimal safe environment construction

The Stage may preserve a small OS/runtime allowlist required for deterministic command execution, for example:

```text
PATH
PATHEXT
SystemRoot / WINDIR / COMSPEC where required on Windows
TEMP / TMP
HOME / USERPROFILE where required
LANG / locale runtime fields where required
explicit task-owned non-secret environment values
```

Exact allowlist is implementation HOW and must be justified by tests.

Default rule:

```text
provider API keys / tokens / credential values are absent from subprocess environment
```

At minimum the proof must show that when the Harness host process can resolve a DeepSeek credential:

```text
DEEPSEEK_API_KEY
```

is not present in the verification subprocess environment.

The same test must also cover a representative synthetic secret variable.

## 5.2 No overclaim

The Stage does not need a universal secret detector.

Security comes from constructing a small positive environment allowlist, not from claiming every possible secret name can be recognized.

This Stage proves **environment sanitization only**. It does not claim filesystem sandboxing of same-user processes.

---

# 6. I-04 — ExecutionPolicy vs ApprovalPolicy

V0.1 used task path allowlists plus an approval callback. The new Candidate must make the responsibility split explicit.

## ExecutionPolicy owns

```text
allowed read paths
allowed write paths
allowed Stage-declared command identities / argv
command timeout
model-attempt budget
repair-cycle budget
explicit task-owned non-secret environment values
```

For this Stage:

```text
arbitrary model-authored shell = FORBIDDEN
network-specific Harness tool = NOT EXPOSED
```

Only Stage-declared command specifications may execute.

### Network boundary precision

This Stage does NOT claim OS-level network denial for an otherwise executable process.

```text
NO NETWORK TOOL EXPOSED
!=
OS NETWORK SANDBOX
```

Actual filesystem/network sandboxing remains deferred until a broader shell/tool surface is justified.

## ApprovalPolicy owns

```text
ALLOW / DENY for a proposed action that is already permitted by ExecutionPolicy
```

Required invariant:

```text
ApprovalPolicy may narrow permission.
ApprovalPolicy may NOT widen ExecutionPolicy.
```

Negative proof:

```text
ExecutionPolicy forbids path/command
ApprovalPolicy returns ALLOW
→ action still rejected
```

---

# 7. I-05 — Environment / Harness Identity Snapshot

Each preflight/run must record enough non-secret execution identity to make evidence interpretable across processes and machines.

Minimum fields:

```text
harness_implementation_version
harness_source_revision or source identity when available
python_version
os_name
os_release or platform family
architecture
workspace_root
provider_id
model_id where configured / observable
credential_source_type
execution_policy_id or stable digest/identity
preflight_status
```

Rules:

```text
credential value = NEVER
full environment dump = FORBIDDEN
user secret file path/content = FORBIDDEN
```

Git/source revision lookup may degrade to `UNKNOWN` when unavailable. Do not make Git presence a runtime requirement merely for identity reporting.

This is Stage evidence, not a telemetry platform.

---

# 8. Provider Binding — Minimum Only

The Stage may introduce one small Harness-local provider binding structure so Harness configuration can say:

```text
provider_id
model_id
credential_ref
```

It must not create:

```text
universal provider registry
provider marketplace
automatic model routing
cost optimizer
fallback fleet
```

The existing Catalyst `ModelProvider` contract remains the first neutral model seam.

DeepSeek remains only the live proof adapter for this Stage, not permanent Harness identity.

---

# 9. Required Proofs

## E-01 — Preflight READY

With valid Workspace, policy, executable, provider binding and resolvable local credential:

```text
preflight = READY
```

No model call is required for the readiness check.

## E-02 — Preflight BLOCKED

At least these failures must be independently distinguishable:

```text
credential unavailable
workspace invalid
verification executable unavailable or policy-disallowed
```

No mutation or model call may begin after BLOCKED.

## E-03 — Durable Local Credential Resolution Across Fresh Process

A credential configured in the user-local credential store must be resolvable by a **fresh separately launched Harness proof process** when the corresponding provider environment variable is explicitly absent from that process.

This is the proof that closes the process-inheritance problem observed during H-03.

Required evidence:

```text
fresh_process = true
DEEPSEEK_API_KEY_in_process_env = false
credential_ref = deepseek.default
credential_source_type = USER_LOCAL
credential_resolved = true
```

Never record the credential value.

The proof must not simulate freshness merely by mutating `os.environ` and continuing inside the same long-lived HarnessSession process.

## E-04 — Process Environment Source Still Works

The ProcessEnvironment source remains a valid replaceable source.

A deterministic test may use a synthetic credential value.

This proves local persistent storage is not hard-coded as the only possible future source.

## E-05 — Provider Secret Absent From Tool Process Environment

With a model credential resolvable by the Harness, a verification subprocess must prove:

```text
DEEPSEEK_API_KEY absent from subprocess environment
synthetic secret absent from subprocess environment
required safe runtime variables sufficient for command execution
```

This proof is strictly about the subprocess **environment**. It does not claim the same-user process cannot access the filesystem credential store through other OS mechanisms.

## E-06 — ExecutionPolicy Cannot Be Widened by Approval

Required negative checks:

```text
forbidden write + approval ALLOW → DENIED
forbidden command + approval ALLOW → DENIED
```

## E-07 — Approval Still Governs Allowed Mutation

For an action permitted by ExecutionPolicy:

```text
approval DENY → no mutation
approval ALLOW → mutation may execute
```

## E-08 — Existing Minimum Harness Behavior Preserved

The new Candidate must still prove the V0.1 core behavior:

```text
Workspace isolation
provider-neutral model path
bounded tool surface
external approval
real deterministic verification
at most one repair cycle
trace
explicit result/failure
governance non-inheritance
```

Do not rewrite the old V0.1 evidence. Run equivalent regression proofs against the new Candidate.

## E-09 — Live DeepSeek Through User-Local Credential From Fresh Process

Final Stage PASS requires one real live DeepSeek-driven bounded fixture task executed from a **fresh separate proof process** where:

```text
DEEPSEEK_API_KEY is explicitly absent from the fresh process environment
credential is resolved from UserLocalCredentialSource
preflight = READY
provider invocation succeeds
tool subprocess environment does not contain the credential
verification passes
```

The external launcher may inherit ordinary non-secret runtime variables, but it must construct the fresh proof process environment with `DEEPSEEK_API_KEY` removed.

If the user-local credential is unavailable, deterministic proofs may complete but final verdict remains TARGETED_REPAIR / BLOCKED, not PASS.

## E-10 — Identity Snapshot

Results must contain the required non-secret identity fields and no environment dump, secret value, or credential-store content/path.

---

# 10. Credential Setup Proof Boundary

The executor must never ask the user to paste a secret into chat, a Stage file, Git, or a command-line argument.

If the live E-09 proof requires user setup, the only acceptable setup path is the Candidate's hidden-input local credential setup entry point.

Expected flow:

```text
executor says credential ref is missing
→ human runs local setup entry point
→ terminal requests hidden secret input
→ setup confirms ref configured without showing value
→ fresh proof process runs
```

The Harness should not require the executor itself to restart solely because the credential was added to the user-local store.

---

# 11. Candidate Artifact Set

Preferred minimum:

```text
platform-harness/harness-v0.2-candidate/
  harness/**
  fixture/**
  tests/**
  V0_2_RESULTS.json
  V0_2_REVIEW.md
```

A tiny credential setup executable/module may live inside `harness/**` or a small sibling entry point under this candidate root.

Do not create separate reports for E-01..E-10.

Do not create a credential file inside the repository.

---

# 12. Allowed Source Reuse

The implementation may read and reconstruct from frozen Minimum Harness V0.1:

```text
platform-harness/minimum-harness-v0.1/harness/**
platform-harness/minimum-harness-v0.1/fixture/**
platform-harness/minimum-harness-v0.1/tests/**
```

The frozen V0.1 files must remain unchanged.

Existing neutral Runtime model contracts/providers may again be read/reused where compatible, without modification.

No Case 01 / Case 02 implementation is needed for this Stage.

---

# 13. Explicit Non-Scope

Do NOT add:

```text
durable Harness session resume
conversation persistence
multi-agent
subagents
background job manager
arbitrary model-authored shell
OS/container sandbox
filesystem secret sandbox
network sandbox / escalation
MCP
plugin ecosystem
Skill Builder
Agent Builder
Capability Registry
Capability search/replacement
context compaction
automatic model routing
Git commit/push authority inside Harness
Web UI
Platform integration
Case 01 execution
Case 02 work
```

---

# 14. Protected Boundaries

Must remain unchanged:

```text
platform-harness/minimum-harness-v0.1/**
agent_runtime/**
platform_standard/**
runtime_adapter/**
case-01/**
case-02/**
ARCHITECTURE.md
README.md
pyproject.toml
main
```

All new implementation/evidence stays under:

```text
platform-harness/harness-v0.2-candidate/**
```

until a later explicit decision.

---

# 15. Dependencies

Use:

```text
Python stdlib
existing repository dependencies only
```

No new dependency is authorized by this Stage Spec.

This intentionally means:

```text
OS keyring integration = deferred
enterprise vault integration = deferred
```

The user-local credential file is a temporary replaceable local-development implementation, not the long-term enterprise answer.

---

# 16. Acceptance Criteria

Final PASS requires:

```text
E-01 PASS
E-02 PASS
E-03 PASS
E-04 PASS
E-05 PASS
E-06 PASS
E-07 PASS
E-08 PASS
E-09 PASS
E-10 PASS
```

and:

```text
frozen Minimum Harness V0.1 unchanged
no protected-boundary mutation
no repository-stored credential
no credential value in trace/results/review
no provider credential in tool subprocess environment
no false claim of filesystem/network sandboxing
no general-shell expansion
no Platform integration
```

Passing proves only:

> Catalyst has an environment-complete Harness Candidate suitable for the first separately-authorized low-risk Case 01 trial under the bounded execution assumptions of this Stage.

It does not prove:

```text
enterprise-grade secret storage
filesystem-level secret isolation
OS-level sandbox security
network isolation
durable long-running development sessions
multi-provider portability
full Agent construction
production Platform integration
```

---

# 17. Verdict Vocabulary

Final integrated review must end with exactly one of:

```text
HARNESS_ENVIRONMENT_INFRASTRUCTURE_V0_1_PASS
HARNESS_ENVIRONMENT_INFRASTRUCTURE_V0_1_TARGETED_REPAIR
HARNESS_ENVIRONMENT_INFRASTRUCTURE_V0_1_FAIL
```

A PASS does not authorize Case 01 execution or Platform integration.

---

# 18. Next Decision After PASS

Preferred next step:

```text
freeze environment-complete Harness Candidate
        ↓
separate Case 01 low-risk task authorization
        ↓
use the frozen Candidate on one real BREA development task
```

Do not automatically expand Harness features after this Stage.

---

# 19. STOP / Authorization Boundary

This file defines the Stage only.

Until a separate Authorization Record exists:

```text
NO harness-v0.2-candidate code
NO credential store creation
NO credential setup tool
NO tests
NO live proof
NO Case mutation
NO Platform integration
```
