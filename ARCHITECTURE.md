# Agent Runtime + Platform Standard — System Architecture
## v2.4 FINAL · Responsibility & Capability-Preserving Evolution Model

> **Accepted implementation/evidence baseline:** `main @ 763a3777713fd38e6db3c4eeeddcf321506cc20f`  
> **Current stage:** Architecture / Governance Harvest clarification（v2.4）—— 不授权新的功能实现。  
> **Role of this file:** 系统 purpose + layer meaning + ownership + boundaries + replacement rules + capability-preserving evolution rules。  
> **Guiding thesis:** **Everything is replaceable. Nothing is casually replaceable.**

---

# 1. Current accepted reality

The repository has already validated several architectural facts:

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

## 1.4 Catalyst Minimum Usable V0.2（真实 Harness / Evidence / Evolution 证据）

V0.2 added a real operational proof without redefining Capability or expanding Platform Core merely for Harness convenience:

```text
real model API
real external tool/API
multi-case benchmark
raw execution evidence / failure attribution
Formal Baseline Reference
bounded Candidate
same-benchmark re-evaluation
accept / rollback decision
```

A real native-tool incompatibility also demonstrated an implementation-evolution boundary:

```text
native-tools v1 assumption failed under real multi-tool model behavior
→ failure owner localized to Harness native-tool interaction
→ existing per-execution Runtime certainty semantics preserved
→ PATCH v1 rejected
→ clean v2 rebuild accepted
→ whole-Harness replacement rejected for insufficient evidence
→ external mature tool-loop adoption retained as a conditional candidate
```

This is evidence for a stronger interpretation of replaceability:

> **Preserve proven responsibility and organizational value; do not grant permanent privilege to the current implementation.**

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
capability-preserving implementation evolution
```

Guiding statements:

> **Everything is replaceable. Nothing is casually replaceable.**
>
> **Stable WHAT / replaceable HOW.**
>
> **Preserve capability, not implementation privilege.**

Meaning:

- no implementation is permanently privileged;
- replacement is allowed only if required architectural obligations remain satisfied or are explicitly migrated;
- repair of the current implementation has no automatic priority over other justified evolution paths;
- implementation evolution is evidence-governed rather than driven by code ownership or sunk cost;
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
| current Runtime cannot satisfy required execution semantics | Runtime repair / upgrade / replacement candidate |
| an implementation fails while its responsibility remains valid | implementation-evolution decision at the owning layer; repair is one candidate, not the default |
| Runtime must learn enterprise/domain semantics to support a feature | architecture boundary failure candidate |
| cross-capability sequencing / parallel execution structure / conditional routing / long-running process structure | Workflow / Orchestration Layer |

Workflow / Orchestration relationship:

```text
Domain
→ may provide domain workflow patterns（行业流程模式）

Enterprise
→ may configure organization-specific process semantics（组织流程语义）

Workflow / Orchestration
→ expresses / runs cross-capability process structure（跨能力流程结构）
```

Workflow / Orchestration is a future layer responsibility; no Workflow Engine is implemented in the current stage.

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

Extension maturation clarification:

```text
Repeated usage alone DOES NOT justify Platform Core promotion.

An Extension may remain long-term — even permanently — as:
  Domain Extension
  Enterprise Extension
  Adapter / Vendor Extension
  Experimental Extension
and may mature and version independently.

Only a repeated cross-boundary common semantic gap — appearing across
multiple Domains, Enterprises and/or Runtime/Adapter implementations,
and beginning to affect interoperability / replaceability / asset
portability — enters the Platform Standard RFC Candidate path.

Core Promotion is optional, not inevitable.
```

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

This requirement-routing model and the implementation-evolution rule in Section 12 solve different questions:

```text
new or newly expressed need
→ which responsibility layer should own it?

observed failure / obsolete implementation
→ how should the implementation at that responsibility evolve?
```

Do not collapse them into one universal decision engine.

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
a current implementation is difficult to repair
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
Harness mechanisms can be replaced
Domain packages can evolve
Enterprise semantics can evolve
Platform Standard can version and evolve
```

Replacement must preserve or explicitly migrate the assets and obligations that depend on the replaced boundary.

## 12.2 Change-rate expectation（stability expectation, not an immutable law）

```text
fast-changing
  Model / vendor / tool / adapter
  Harness / Runtime implementation
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
Capability responsibility / semantic WHAT
public/shared Contract obligations
Domain knowledge
Enterprise mappings
Capability descriptors / identity
Workflow patterns
Governance semantics
Evaluation / benchmark knowledge
Compatibility knowledge
Migration rules
operational evidence
known limits
Evolution Lineage / decision rationale
```

> **Platform Standard protects accumulated upper-layer assets from lower-layer technology churn.**

For the broader explanatory interpretation of capability preservation and Harvest, see `docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md`. This Architecture file does not create a Harvest object or duplicate that philosophy.

## 12.4 Capability-preserving implementation evolution

> **Repair is not the default. Evolution decision comes first.**

When an observed failure or maintenance problem occurs, first identify the owning responsibility and the Capability, Contract, evidence, semantic meaning, and other obligations that must survive. Only then select an implementation path.

The stable architectural rule is:

> **Preserve the required organizational capability and proven obligations; let implementation compete for the right to remain.**

Architecture does not prescribe one preferred repair/rebuild/replace procedure or define implementation-evolution actions as Platform ontology. The detailed candidate vocabulary and decision procedure belong to a replaceable method such as `platform-harness/skills/capability-optimization/SKILL.md`.

## 12.5 Evidence-governed selection

Implementation evolution must be justified by evidence and by **total evolution cost**, not merely current diff size or sunk investment in the existing code.

A replacement or rebuild is legitimate only when the required obligations remain satisfied or have an explicit migration path. The detailed comparison dimensions belong to the replaceable Optimization method, not to Architecture or Platform Core.

## 12.6 Self-observability, independent evaluation, and Evolution Lineage

Replaceability requires enough evidence to localize a failure. Components may report bounded facts about their own behavior; independent Evaluation attributes and judges those facts; the responsible implementation owner may then compare bounded evolution candidates.

A component does not gain authority to certify itself merely because it reports its own facts.

Implementation evolution should preserve enough lineage to recover the Reference, triggering evidence, owning responsibility, preserved obligations, decision rationale, evidence identity, migration/rollback implications, remaining limits, and resulting implementation when those facts are material.

This does **not** create a Monitoring Service, Self-Healing Engine, Evolution Engine, Lineage Service, or universal schema. Git history, evidence artifacts, Stage reviews, and other authoritative references may carry the lineage.

## 12.7 External mechanisms are first-class HOW candidates

Catalyst does not need to own source code for every mechanism. A mature external Harness, Runtime, provider, retrieval mechanism, orchestration tool, or other implementation may be adopted when it satisfies the applicable Catalyst responsibility, evidence, and replacement obligations through an acceptable seam.

Do not clone mature machinery merely so Catalyst can claim authorship.

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

## Boundary smell E

```text
an obsolete implementation assumption is repeatedly preserved through compatibility patches because repair is treated as mandatory
```

→ possible implementation-evolution failure; compare alternatives before adding more debt

## Boundary smell F

```text
replacement requires discarding Capability evidence, Domain/Enterprise meaning, benchmark knowledge, or public obligations that should have been portable
```

→ possible missing stable boundary / migration responsibility

---

# 14. Source authority by question

There is **no single globally highest Source of Truth**. Authority depends on the question:

```text
current accepted implementation reality      -> GitHub main
system purpose / layer meaning / boundaries  -> ARCHITECTURE.md
Platform Standard v0.1 normative contract    -> PLATFORM_STANDARD_CORE_V0.1.md
current implementation authorization         -> Stage Spec
current delivery / review state              -> HANDOFF / current review record
verification result                          -> Tests / CI / frozen evidence
replaceable Harness evolution method         -> platform-harness/skills/capability-optimization/SKILL.md
research / ideas / candidates                -> research / review documents
```

Conflict semantics:

```text
Architecture / spec 与 implementation 冲突
≠ implementation 自动重新定义 Architecture

冲突按问题类别产生并处理：
  Architecture Conformance Finding   （架构与实现不符）
  Contract Conformance Finding       （实现不满足契约）
  Stage Authorization Violation      （超出当前授权）
```

冲突处理责任按 Section 5 responsibility model 路由；不自动修改任何文件。

> A stale status in another document does **not** authorize changing that file in this stage. Inconsistencies are reported as follow-up findings only.

---

# 15. Current validated evidence

```text
Platform Standard Core v0.1          IMPLEMENTED / VERIFIED / MERGED / ACCEPTED / CLOSED
  PS-1..PS-14 + AR-1..AR-7 PASS；vertical slice（compose_report）PASS；second capability（count_words）PASS
Enterprise Extension Pilot v0.1     IMPLEMENTED / VERIFIED / MERGED / ACCEPTED / CLOSED
  EE-1..EE-12 + ER-1..ER-5 PASS；Org A/Org B portability PASS；trace attribution PASS
Minimum Architectural Framework v1  PROVEN / ACCEPTED for declared evidence scope
Catalyst Minimum Usable V0.2        IMPLEMENTED / VERIFIED / MERGED / ACCEPTED
  real model + real external tool/API + frozen benchmark + Formal Baseline + bounded Candidate + re-evaluation / accept
Native-tools evolution evidence      v1 multi-tool assumption failure → rebuild v2; Platform Core unchanged
Runtime                              accepted replaceable execution infrastructure
Governance                           CI + exact-ref + PR workflow + frozen evidence / review records
Accepted code baseline               main @ 763a3777713fd38e6db3c4eeeddcf321506cc20f
```

Current architecture meaning after this update:

```text
Platform Standard Core v0.1 remains valid
Minimum Architectural Framework v1 remains valid
Catalyst Minimum Usable V0.2 evidence remains valid
Runtime remains replaceable execution infrastructure
implementation evolution is now explicitly capability-preserving and evidence-governed
no next feature is automatically authorized
```

The roadmap `Identity → Role / Authority → Policy → Approval` is **not** automatic next-implementation authorization. The next Stage must still be selected by applying the responsibility/evidence model to actual need.

---

# 16. Current non-goals / unauthorized work

```text
Role / Authority / Delegation / Policy Engine / Approval
Enterprise Profile implementation / Domain Package platform implementation
Workflow Engine / Control Plane / MCP / A2A / OpenTelemetry integration
new Registry / new Platform Core fields / new Platform Standard contracts
second Runtime merely to prove replaceability
Evolution Engine / Repair Engine / Replacement Service
Self-Healing / automatic self-modification / Monitoring Platform
Lineage Service / universal evolution schema
```

These are future possibilities or explicitly rejected expansions, not work authorized by this architecture clarification.

---

# 17. Architecture acceptance / stop condition

This `ARCHITECTURE.md` is acceptable when a future developer can answer YES to:

```text
1. Can the default owner of a new problem be identified?
2. Can Runtime problems be distinguished from Platform Standard problems?
3. Can Domain semantics be distinguished from Enterprise semantics?
4. Is it clear that implementations are replaceable?
5. Is replaceability defined by preserved obligations, not arbitrary replacement?
6. Is Repair clearly not an automatic default after failure?
7. Is it clear what organizational Capability value should survive implementation churn?
8. Is implementation evolution evidence-governed rather than implementation-privileged?
9. Is total evolution cost distinguished from current diff size without duplicating the detailed method here?
10. Is independent Evaluation separated from component self-observation/self-certification?
11. Is Evolution Lineage preserved without requiring a new service/schema?
12. Are mature external mechanisms admissible HOW when obligations are preserved?
13. Is it clear when Platform Standard should NOT change?
14. Is it clear when Platform Standard deserves review?
15. Is Extension First a first-class principle?
16. Is evidence required before Core promotion?
17. Is asset preservation part of architecture value?
18. Is Runtime replacement defined by obligations rather than internal shape?
19. Can boundary-failure signals be identified?
20. Is the Source-of-Truth hierarchy clear?
21. Are validated Runtime / Platform / Extension / V0.2 facts preserved without inventing new authority?
22. Is the detailed evolution procedure kept in a replaceable Harness-side method rather than Platform Core?
```

After this update: **STOP.** Do not implement Role / Authority / Policy / Approval / Domain Package platform / Enterprise Profile / Control Plane / Evolution Engine / new Registry / new Runtime / new Platform Standard contracts from this architecture clarification alone.

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
> **Capability and proven organizational value should survive implementation churn; implementation has no permanent privilege.**
>
> **Repair is not the default; implementation evolution must be evidence-governed and obligation-preserving.**
>
> **The long-term product is an Organization-AI Operating Model, not a larger Runtime.**
>
> **Everything is replaceable. Nothing is casually replaceable.**