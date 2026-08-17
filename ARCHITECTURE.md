# Agent Runtime + Platform Standard — System Architecture
## v2.3 FINAL · Responsibility & Evolution Model

> **Accepted Runtime baseline:** `main @ 1eab80348af69389f21d33376a219051d5f339e4`（tree `55223bf3aeacc050bbef218095d65641233ec67b`）  
> **Current stage:** Architecture-only correction / clarification（v2.3）—— 不授权任何未来功能。  
> **Role of this file:** 系统 purpose + layer meaning + ownership + boundaries + replacement rules + evolution rules。  
> **Guiding thesis:** **Everything is replaceable. Nothing is casually replaceable.**

---

# 1. Current accepted reality

The repository has already validated three architectural facts:

## 1.1 Runtime（可替换的执行基础设施）

The existing Agent Runtime owns execution concerns:

```text
Agent Loop
Reasoner
ModelProvider seam
Capability execution
Session / state lifecycle
PendingExecution
execution certainty
reconciliation
cancellation / timeout
Runtime-local execution control
```

It remains **enterprise-free, domain-free, replaceable infrastructure**. Its fail-closed execution semantics remain valid:

```text
exception != proof of non-execution
timeout != failure
unresolved execution never auto-replays
reconciliation is explicit
```

## 1.2 Platform Standard Core v0.1（证据支撑的稳定契约切片）

The validated executable path:

```text
Capability Descriptor → InMemory Descriptor Registry → Standard Invocation
  → Validator → Runtime Adapter → Existing Runtime → Standard Result
    + ArtifactRef(s) + Minimal Trace
```

Core v0.1 demonstrated:

```text
one complete Standard → Adapter → Runtime → Result path
second Capability portability（count_words，零 Core/Runtime/AgentCore 改动）
same-ID multi-version routing
Extension support（required=false preserved；required=true fail closed）
unresolved execution mapping
```

Core v0.1 is the **first evidence-backed stable slice** of Platform Standard, not a claim that all future Platform semantics are already known.

## 1.3 Enterprise Extension Pilot v0.1（Extension First 的证据）

`enterprise.identity` demonstrated:

```text
enterprise semantics can enter through Extension
Core schema unchanged
generic RuntimeAdapter remains enterprise-agnostic
agent_runtime/** unchanged
identity visible in trace attribution（TraceEvent.extensions）
```

This supports the thesis:

> **Stable Core + Adjustable Semantics / Extension First.**

---

# 2. Long-term system purpose

The final product is an **Enterprise Agent Operating Model**, not merely an Agent ↔ Tool framework:

```text
Enterprise Agent Operating Model
  + Platform Standard
  + Domain Packages
  + Enterprise Mapping
  + Governed Runtime Ecosystem
```

Strategic assets are expected to accumulate mainly in:

```text
Platform Standard
Enterprise Mapping
Domain Packages
Workflow Patterns
Governance semantics
Evaluation / Feedback
Capability ecosystem
```

Runtime remains essential infrastructure but stays replaceable.

---

# 3. Core architecture principles

> **The project is not building a permanently fixed Runtime or a permanently complete Platform Standard. It is building an evolvable architecture in which implementations, semantics, and standards may be replaced or upgraded while accumulated assets remain as portable as possible.**

Design around:

```text
clear responsibility
stable boundaries
replaceable implementations
extension-first growth
evidence-based standard evolution
asset preservation
```

Guiding statement:

> **Everything is replaceable. Nothing is casually replaceable.**

Meaning:

- no implementation is permanently privileged;
- replacement is allowed only if required architectural obligations remain satisfied;
- the more downstream assets depend on a boundary, the more carefully that boundary must evolve.

---

# 4. Layer model

`Domain` and `Enterprise` are **different semantic dimensions that may be composed**, not a strict parent/child chain.

```text
                    Application Surfaces
                            │
                            ▼
                  Agent / Workflow Layer
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       Domain Packages            Enterprise Semantics
   professional meaning        organization-specific meaning
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
                   Platform Standard
             stable coordination boundary
                            │
                            ▼
                      Runtime Adapter
                            │
                            ▼
                         Runtime
                            │
                            ▼
                     Infrastructure
```

Semantic point:

```text
one Enterprise may use multiple Domains
one Domain may be used by multiple Enterprises
```

Do not over-model this; the architecture meaning is what matters.

---

# 5. Layer responsibilities and boundaries

The system asks first:

> **"Which layer owns this problem?"**

not:

> "Which file is easiest to edit?"

| Problem / change | Default owner |
|---|---|
| execution lifecycle, cancellation, timeout, recovery, reconciliation, execution certainty | Runtime |
| vendor/system/API-specific integration differences | Adapter |
| concrete implementation of a capability | Capability implementation |
| shared cross-implementation invocation/result semantics | Platform Standard |
| professional/domain meaning | Domain Package / Domain Layer |
| organization-specific structure, policy, approval, vocabulary, risk preference | Enterprise semantics / Enterprise Profile |
| new requirement local to a small number of contexts | Extension |
| repeated cross-domain / cross-enterprise / cross-runtime semantic gap | Platform Standard review candidate |
| current Runtime cannot satisfy required execution semantics | Runtime upgrade/replacement candidate |
| Runtime must learn enterprise/domain semantics to support a feature | architecture boundary failure candidate |

---

# 6. Platform Standard role and value

Platform Standard is the **stable, evolvable coordination boundary** between independently evolving upper-layer assets and replaceable lower-layer execution implementations.

Its three primary responsibilities:

## 6.1 Coordination

Allow independently implemented components to cooperate through shared contracts.

## 6.2 Isolation

Prevent changes in one layer from unnecessarily propagating into unrelated layers:

```text
enterprise policy change      ≠ Runtime rewrite
domain terminology change     ≠ Platform Core rewrite
Runtime implementation replacement ≠ rewriting all Domain / Enterprise assets
```

## 6.3 Evolution

Provide enough extension, compatibility, versioning and migration semantics so the system can grow without repeatedly collapsing into a new monolith.

Value test:

> **Platform Standard is valuable when it removes unnecessary coupling while preserving necessary variation.**

---

# 7. Runtime role and replacement boundary

Runtime answers: **How does execution run?**

> Runtime is a replaceable execution implementation responsible for reliably turning accepted execution intent into runtime state and execution outcomes.

Runtime owns:

```text
execution lifecycle
execution state
execution certainty
cancel / timeout
recovery
reconciliation
runtime-local execution control
capability execution mechanics
```

Runtime must NOT own semantic meaning:

```text
company organization
role meaning
professional ontology
approval meaning
company-specific policy meaning
domain vocabulary
```

## 7.1 Runtime Conformance Boundary（替换判据）

A replacement Runtime does **not** need:

```text
the same classes
the same internal APIs
the same Agent Loop
the same framework
the same source structure
```

It must preserve the architectural obligations required by the Standard / Adapter boundary, for example:

```text
required execution semantics
standard invocation/result usability
execution certainty semantics
required lifecycle guarantees
required context preservation
no forced rewrite of upper-layer contracts
```

This is an architectural criterion, not a conformance-test requirement.

---

# 8. Domain and Enterprise semantic dimensions

- **Domain Packages** carry professional/industry meaning.
- **Enterprise Semantics** carry organization-specific meaning.

They compose; neither is a strict parent of the other. Current stage defines no concrete Domain Package or Enterprise Profile; they remain future layers whose meaning is now architecturally explicit.

---

# 9. Extension-first evolution model

> **Extension First. Core Promotion Later.**

Conceptual lifecycle:

```text
Observed Need
    ↓
Local Solution
    ↓
Experimental Extension
    ↓
Repeated Real Usage
    ↓
Evidence
    ↓
RFC Candidate
    ↓
Compatibility Review
    ↓
Promote / Reject / Remain Extension
    ↓
Migration if required
    ↓
Deprecation of superseded form
```

> **The Standard grows from evidence, not from trying to predict every future requirement in advance.**

---

# 10. Change routing model

Conceptual decision model（不实现为引擎）:

```text
NEW REQUIREMENT
      │
      ▼
Can existing contracts express it?
      │
 ┌────┴────┐
 YES       NO
 │          │
 ▼          ▼
Implement   Is it implementation-specific?
at owner          │
             ┌────┴────┐
            YES        NO
             │          │
          Adapter      ▼
                Is it domain-specific?
                       │
                  ┌────┴────┐
                 YES        NO
                  │          │
               Domain       ▼
                     Is it enterprise-specific?
                            │
                       ┌────┴────┐
                      YES        NO
                       │          │
                  Enterprise     ▼
                           Experimental Extension
                                   │
                                   ▼
                            collect evidence
                                   │
                                   ▼
                         repeated cross-system need?
                              │             │
                             NO            YES
                              │             │
                      remain Extension   Platform RFC
                                         candidate
```

---

# 11. Platform Standard change criteria

## 11.1 Platform Core must NOT change merely because

```text
one enterprise has a unique rule
one domain introduces a new concept
one tool/vendor has a special API
the current Runtime has an implementation limitation
one project needs an exception
one experimental idea seems elegant
a new concept is theoretically "general"
```

## 11.2 Platform Standard should be reconsidered when evidence shows

A review is justified when several of the following are true:

```text
1. existing contracts cannot express a recurring requirement;
2. the same semantic gap appears across independent domains / enterprises / implementations;
3. multiple Extensions duplicate the same meaning or workaround;
4. interoperability or replaceability is being damaged;
5. Runtime / Adapter implementations repeatedly require special coupling;
6. upper-layer assets cannot remain portable because a common semantic is missing;
7. promoting a shared contract would reduce total system coupling more than it increases Core complexity.
```

> **A concept does not enter Core because it is elegant. It enters Core because real system evidence reveals a stable shared boundary.**

---

# 12. Replacement and asset-preservation principles

## 12.1 Stable boundary ≠ permanently fixed implementation

```text
ModelProvider can be replaced
Capability implementation can be replaced
Adapter can be replaced
Runtime can be replaced
Domain packages can evolve
Enterprise semantics can evolve
Platform Standard can version and evolve
```

Replacement must preserve or explicitly migrate the assets that depend on the replaced boundary.

## 12.2 Change-rate expectation（stability expectation, not an immutable law）

```text
fast-changing
  Model / vendor / tool / adapter
  Runtime implementation
  Capability implementation
  workflow / domain packages
  enterprise configuration
  Platform modules
  Platform Core contracts
slow-changing
```

## 12.3 Asset preservation

> **Long-term assets should not be unnecessarily destroyed by short-lived implementation changes.**

Likely long-term assets:

```text
Domain knowledge
Enterprise mappings
Capability descriptors
Workflow patterns
Governance semantics
Evaluation data
Compatibility knowledge
Migration rules
operational evidence
```

> **Platform Standard protects accumulated upper-layer assets from lower-layer technology churn.**

---

# 13. Architecture failure signals

Diagnostic signals（不是自动授权修改 Core）:

## Boundary smell A

```text
Runtime must be modified because one enterprise changed a business rule
```

→ possible enterprise/runtime boundary violation

## Boundary smell B

```text
a Domain Package must be rewritten for each Runtime implementation
```

→ possible Platform boundary insufficiency

## Boundary smell C

```text
many Extensions independently encode the same cross-system semantic
```

→ possible Platform promotion candidate

## Boundary smell D

```text
one vendor-specific limitation forces a new Platform Core concept
```

→ possible Adapter/implementation problem incorrectly promoted upward

---

# 14. Source of truth

```text
ARCHITECTURE.md
= system purpose + layer meaning + ownership + boundaries + replacement rules + evolution rules

PLATFORM_STANDARD_CORE_V0.1.md
= normative engineering contract for that Standard version

Stage Spec
= implementation authorization for one stage

GitHub main
= accepted implementation reality

HANDOFF
= current delivery / review state

Tests / verification evidence
= evidence that an implementation satisfies the relevant contract

Research documents
= evidence / ideas / architectural candidates only
```

> A stale status in another document does **not** authorize changing that file in this stage. Inconsistencies are reported as follow-up findings only.

---

# 15. Current validated evidence

```text
Platform Standard Core v0.1          IMPLEMENTED / VERIFIED / MERGED / ACCEPTED / CLOSED
  PS-1..PS-14 + AR-1..AR-7 PASS；vertical slice（compose_report）PASS；second capability（count_words）PASS
Enterprise Extension Pilot v0.1     IMPLEMENTED / VERIFIED / MERGED / ACCEPTED / CLOSED
  EE-1..EE-12 + ER-1..ER-5 PASS；Org A/Org B portability PASS；trace attribution PASS
Runtime                             accepted execution infrastructure（agent_runtime/** ZERO DIFF across both stages）
Governance                          CI（agent-runtime-ci）+ exact-ref（agent-runtime-audit-ref）+ PR template + dev workflow
Accepted baseline                   main @ 1eab80348af69389f21d33376a219051d5f339e4
```

Current stage meaning after this architecture update:

```text
Platform Standard Core v0.1 remains valid
Enterprise Identity Extension Pilot remains valid evidence
Runtime remains accepted execution infrastructure
no next feature is automatically authorized
```

The roadmap `Identity → Role / Authority → Policy → Approval` is **not** automatic next-implementation authorization. The next stage must be selected by applying this responsibility and evolution model to actual evidence.

---

# 16. Current non-goals / unauthorized work

```text
Role / Authority / Delegation / Policy Engine / Approval
Enterprise Profile implementation / Domain Package implementation
Workflow Engine / Control Plane / MCP / A2A / OpenTelemetry integration
Conformance framework / new Extension / new Runtime / new Agent Loop
new Platform Core fields / new tests
Runtime replacement / Platform Standard v0.2
```

These are future architecture, not current work.

---

# 17. Architecture acceptance / stop condition

This `ARCHITECTURE.md` is acceptable when a future developer can answer YES to:

```text
1. Can the default owner of a new problem be identified?
2. Can Runtime problems be distinguished from Platform Standard problems?
3. Can Domain semantics be distinguished from Enterprise semantics?
4. Is it clear that implementations are replaceable?
5. Is replaceability defined by preserved obligations, not arbitrary replacement?
6. Is it clear when Platform Standard should NOT change?
7. Is it clear when Platform Standard deserves review?
8. Is Extension First a first-class principle?
9. Is evidence required before Core promotion?
10. Is asset preservation part of architecture value?
11. Is Runtime replacement defined by obligations rather than internal shape?
12. Can boundary-failure signals be identified?
13. Is the Source-of-Truth hierarchy clear?
14. Are all validated Runtime / Platform / Extension facts preserved?
15. Was only ARCHITECTURE.md modified?
```

After this update: **STOP.** Do not implement Role / Authority / Policy / Approval / Domain Package / Enterprise Profile / Control Plane / Conformance tooling / new Runtime / new Platform Standard contracts.

---

# 18. Final statement

> **Runtime is the execution heart — replaceable infrastructure.**
>
> **Platform Standard is the stable shared language — a coordination, isolation and evolution boundary.**
>
> **Extensions preserve adjustability — Extension First, Core Promotion Later, evidence before promotion.**
>
> **Domain Layer carries industry meaning; Enterprise Mapping carries organization-specific meaning; they compose.**
>
> **The long-term product is an Organization-AI Operating Model, not a larger Runtime.**
>
> **Everything is replaceable. Nothing is casually replaceable.**
