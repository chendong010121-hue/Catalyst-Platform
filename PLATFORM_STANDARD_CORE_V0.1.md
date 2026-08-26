# PLATFORM_STANDARD_CORE_V0.1.md
## FINAL · Minimal Executable Contract

**Status:** **IMPLEMENTED / VERIFIED / MERGED / ACCEPTED / CLOSED**  
**Current-state authority:** `CATALYST_OPERATIONAL_BASELINE_V1.md` + GitHub `main` + active tests / CI  
**Historical acceptance lineage:** PR #4 implementation candidate → PR #5 documentation closure  
**Principle:** **enterprise-extensible, not enterprise-complete**

---

# 1. Goal

Build only this path:

```text
Capability Descriptor
      ↓
InMemory Registry
      ↓
Standard Invocation
      ↓
Validator
      ↓
Runtime Adapter
      ↓
Existing Agent Runtime
      ↓
Standard Result
  + ArtifactRef(s)
  + Minimal Trace
```

Core v0.1 is complete only when a second, meaningfully different Capability can be added without modifying:

```text
Core schemas
Validator architecture
Runtime
AgentCore
```

---

# 2. Current scope

Implement:

```text
Common Object Envelope
Extension
Capability
Invocation
Result
ArtifactRef
Minimal Trace Event
Validator
InMemory Descriptor Registry
Runtime Adapter
one reference vertical slice
one second-capability portability test
```

Do not implement anything else unless required to make this path run.

---

# 3. Common Object Envelope

Every top-level Standard object:

```yaml
standard_version: "0.1"
kind: "<kind>"
id: "<non-empty stable string>"
extensions: {}
```

Rules:

- all payloads MUST be JSON-compatible;
- `kind` MUST match the object contract;
- `extensions` MUST be a map;
- v0.1 defines no tenant, user, role or domain fields in the envelope.

---

# 4. Extension Contract

Example:

```yaml
extensions:
  enterprise.identity:
    version: "1"
    required: false
    payload:
      user_ref: "user_123"
```

Each Extension MUST contain:

```text
version
required
payload
```

Rules:

```text
required=false
→ unsupported semantic meaning MAY be ignored
→ Extension MUST still be preserved unchanged

required=true
→ unsupported implementation MUST fail closed
```

Reserved namespaces:

```text
enterprise.*
domain.*
governance.*
interop.*
experimental.*
```

Enterprise/domain change should enter through Extensions first, not through new Core fields.

---

# 5. Capability Contract

```yaml
standard_version: "0.1"
kind: "capability"
id: "compose_report"
extensions: {}

name: "Compose Report"
description: "Create a report from structured input."
capability_version: "1.0.0"

input_schema:
  type: object

output_schema:
  type: object

execution:
  side_effect: "none"
```

Required:

```text
name
description
capability_version
input_schema
output_schema
execution.side_effect
```

Allowed `side_effect`:

```text
none
possible
```

Permissions, roles, approval, risk, budget, tenant and routing are NOT Core v0.1 fields.

---

# 6. Invocation Contract

```yaml
standard_version: "0.1"
kind: "invocation"
id: "inv_001"
extensions: {}

capability_id: "compose_report"
capability_version: "1.0.0"
input: {}

context:
  extensions: {}

trace_id: "trace_001"
```

Required:

```text
capability_id
capability_version
input
context
trace_id
```

v0.1 `context` contains only `extensions`.

Future identity, delegation, project, policy, risk and domain context enter here later only if justified by evidence and the applicable architecture decision.

---

# 7. Result Contract

```yaml
standard_version: "0.1"
kind: "result"
id: "result_001"
extensions: {}

invocation_id: "inv_001"
status: "success"
output: {}
artifacts: []
error: null
```

Allowed status:

```text
success
failure
unresolved
```

If `error` exists:

```yaml
error:
  code: "capability_failed"
  message: "Human-readable summary"
```

Semantics:

```text
success
→ known successful completion
→ error MUST be null

failure
→ known terminal failure
→ error MUST exist

unresolved
→ execution certainty is not closed
→ error MUST exist
→ MUST NOT imply did_not_execute
→ MUST NOT imply safe_to_retry
```

The Adapter MUST preserve:

```text
exception != proof of non-execution
timeout != failure
```

---

# 8. ArtifactRef Contract

```yaml
standard_version: "0.1"
kind: "artifact_ref"
id: "artifact_001"
extensions: {}

artifact_type: "report"
artifact_version: "1"
uri: "file:///outputs/report.md"

producer:
  capability_id: "compose_report"
  invocation_id: "inv_001"
```

Required:

```text
artifact_type
artifact_version
uri
producer.capability_id
producer.invocation_id
```

A Capability MAY return zero artifacts.

The reference vertical slice MUST return at least one so this contract is tested.

---

# 9. Minimal Trace Event

```yaml
standard_version: "0.1"
kind: "trace_event"
id: "event_001"
extensions: {}

trace_id: "trace_001"
event_type: "invocation.completed"
timestamp: "2026-08-17T10:00:00Z"
subject_id: "inv_001"
```

Supported event types:

```text
invocation.started
invocation.completed
invocation.failed
invocation.unresolved
artifact.created
```

Reference implementation may store events in memory.

No observability platform is required.

---

# 10. Validator

Validator checks only the Platform Standard contract:

```text
object envelope
required fields
JSON compatibility
Extension structure
Result status semantics
Capability descriptor minimum structure
```

It MUST fail closed and MUST NOT silently repair malformed payloads.

It MUST NOT duplicate Runtime business/execution validation.

> Existing Runtime / CapabilityExecutor remains responsible for actual capability input validation during execution.

---

# 11. InMemory Descriptor Registry

Required operations:

```text
register(descriptor)
get(capability_id, capability_version)
list()
reject duplicate id/version
```

It stores Standard descriptors only.

It is NOT a future production Registry Service and does not authorize one.

---

# 12. Runtime Adapter

Adapter flow:

```text
validate Invocation
→ resolve descriptor
→ resolve implementation binding
→ call existing Runtime
→ map Runtime outcome to Standard Result
→ attach ArtifactRef(s)
→ emit Trace Event(s)
```

The descriptor Registry does not store executable Runtime objects.

The Adapter MAY use a simple internal binding:

```text
(capability_id, capability_version)
→ existing Runtime Capability implementation / registration key
```

This binding is an implementation detail, not a Standard object.

The Adapter MUST NOT:

```text
modify AgentCore
reimplement Runtime lifecycle
invent retry
auto-replay unresolved execution
embed enterprise/domain logic
become a workflow engine
```

---

# 13. Runtime outcome mapping

Standardize semantics, not current exception class names:

```text
known successful completion
→ success

known terminal failure
→ failure

execution certainty not closed
→ unresolved
```

Timeout, cancellation, interruption or an exception after a possible side effect may therefore map to `unresolved`.

---

# 14. Reference vertical slice

Use:

```text
compose_report
```

Definition of Done:

```text
1. define descriptor
2. bind existing Runtime Capability implementation
3. register descriptor
4. create Invocation
5. validate Invocation
6. Adapter resolves descriptor + binding
7. existing Runtime executes
8. Adapter returns Result
9. at least one ArtifactRef is produced
10. minimal Trace events are emitted
11. all Standard objects validate
```

---

# 15. Portability gate

After the first slice passes, add one different Capability.

It MAY add:

```text
new descriptor
new Runtime implementation/binding
new example/test registration
```

It MUST NOT change:

```text
Core schemas
Validator architecture
Runtime
AgentCore
```

When this passes, stop adding Capability types.

---

# 16. Explicit non-goals

Core v0.1 MUST NOT become:

```text
IAM / RBAC / ABAC
tenant system
approval system
policy engine
audit platform
workflow engine
Enterprise Profile
Domain Package
Control Plane
MCP / A2A
OpenTelemetry implementation
multi-agent system
plugin framework / marketplace
new Runtime
new Agent Loop
production Registry Service
```

These remain absent unless future real use provides evidence and explicit bounded authorization.

---

# 17. Acceptance tests

Required:

```text
PS-1  valid Capability accepted
PS-2  malformed Capability rejected
PS-3  valid Invocation accepted
PS-4  unknown required Extension rejected
PS-5  unknown optional Extension preserved
PS-6  success Result validates
PS-7  failure Result validates
PS-8  unresolved Result implies no safe retry
PS-9  ArtifactRef validates
PS-10 Trace Event validates
PS-11 duplicate registry id/version rejected
PS-12 vertical slice passes
PS-13 second Capability requires no Core/Runtime/AgentCore change
PS-14 uncertain Runtime outcome maps to unresolved
```

Do not add more v0.1 tests unless a current contract requires them.

---

# 18. Accepted deliverables

```text
platform_standard/
  models.py
  extensions.py
  validation.py
  registry.py
  runtime_adapter.py

examples/
  run_platform_standard_vertical_slice.py
  platform_standard_reference.py

tests/
  test_platform_standard_core.py

PLATFORM_STANDARD_CORE_V0.1.md
```

Historical Stage/Handoff files are not required on the current Operational V1 surface.

---

# 19. Stop condition

v0.1 is done when:

```text
vertical slice PASS
second-capability portability PASS
required tests PASS
AgentCore unchanged
no future enterprise/domain subsystem implemented
```

This condition has been satisfied. Core v0.1 is closed.

> **The purpose of Core v0.1 is not to model the whole enterprise. It is to prove one stable, extensible contract above a replaceable Runtime implementation.**

---

# 20. Accepted v0.1 evidence status

```text
acceptance results
  PS-1..PS-14                                              PASS

audit-repair results
  AR-1..AR-7                                               PASS

reference execution
  vertical slice (compose_report)                          PASS
  second Capability (count_words)                          PASS
  same-ID multi-version routing                            PASS

runtime integrity at acceptance
  AgentCore / Runtime / CapabilityExecutor / contracts    UNCHANGED for the v0.1 slice

repository status
  PR #4 implementation candidate                          MERGED
  PR #5 documentation closure                             MERGED
  Platform Standard Core v0.1                             ACCEPTED / CLOSED
```

Current implementation truth is GitHub `main`; current operational state is summarized by `CATALYST_OPERATIONAL_BASELINE_V1.md`.
