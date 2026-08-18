# PART A — Stable Governing Core

> 本部分定义当前阶段应长期保持稳定的治理原则。除非新的已接受 Evidence 改变项目目标、责任边界或核心演进方法，否则不应因单次 Gate、Stage 或状态变化而修改。

# 0. How this baseline must be used

从本文件生效开始，任何新的讨论、实现建议、Stage Spec、代码变更或架构扩展，都必须先回答：

```text
1. 是否符合本文件定义的当前项目目标？
2. 是否尊重 ARCHITECTURE v2.3 的层级责任？
3. 这是 Architecturally Exists、Evidence-backed Exists，还是 Production Exists？
4. 当前是否真的存在足够证据值得实现？
5. 这个问题属于哪一层？
6. 是否存在更小的验证方式？
7. 是否会把未来假想需求提前固化进 Core / Runtime？
8. 是否定义了明确 Stop Condition？
```

如果不能回答清楚：

> **默认不实施。**

---

# 1. Long-term North Star

项目长期方向仍然是：

> **Enterprise Agent Operating Model**

长期来看，系统可能包含：

```text
Platform Standard
Runtime ecosystem
Domain Packages
Enterprise Mapping / Enterprise Semantics
Workflow / Orchestration
Governance semantics
Evaluation / Feedback
Capability ecosystem
Control Plane
other future extensions
```

但是：

> **长期架构中“存在”某一层，不代表当前项目必须把这一层实现出来。**

Architecture 是长期责任地图，不是 Feature Backlog。

---

# 2. Current Project Goal

当前项目真正要完成的不是一个完整企业系统。

当前项目目标正式定义为：

# Minimum Architectural Framework
# 最小架构证明框架

定义：

> **用尽可能少、但真实可运行的实现，证明 Agent Runtime、Platform Standard、Capability、Adapter、Extension 以及未来上层语义之间最关键的架构边界确实成立。**

当前框架必须满足：

```text
- 能真实运行；
- 核心层真实存在；
- 每一层有明确责任；
- 已实现组件必须具有当前价值，而不是为未来假想需求提前建设；
- 关键架构主张能够被代码和测试证明；
- 能清楚说明未来如何生长；
- 不追求当前成为 Production Enterprise Agent System；
- 不以“实现功能数量”衡量架构成熟度。
```

核心判断：

> **用最少的代码，证明最重要的架构原则。**

---

# 3. Three Levels of “Exists”

以后讨论任何模块、语义、系统或能力，都必须先判断它属于哪一种存在状态。

## 3.1 Architecturally Exists
### 架构上存在

表示：

```text
我们已经确认：
- 这是一个真实且合法的架构责任 / 问题；
- 它当前有明确的默认责任层或合法架构位置；
- 已经知道它不应该污染哪些已稳定层；
- 未来真实需求出现时，应优先回到这个责任位置继续澄清或实现；
- 但它的内部模型、完整 Contract、最终边界和具体实现仍可以保持未定义。
```

做到这里，并不要求代码，也不代表最终设计已经完成。

当前可仅以 Architecturally Exists 存在的典型内容包括：

```text
Authority
Role
Enterprise Policy
Approval
Workflow / Orchestration
Domain Package
Enterprise Profile
Control Plane
Production Registry
```

原则：

> **Architecturally Exists ≠ fully specified ≠ implementation required.**

---

## 3.2 Evidence-backed Exists
### 有最小证据证明

仅对那些：

> **如果设计错误，会影响整体架构成立、可替换性、互操作性或长期资产沉淀的重要边界**

进行最小 vertical slice 验证。

Evidence-backed Exists 的目标不是提供完整功能，而是：

> **证明一个架构假设能够在真实代码里成立。**

当前已经属于这一层的内容包括：

```text
Runtime execution semantics
Platform Standard Core v0.1
second Capability portability
enterprise.identity Extension Pilot
```

---

## 3.3 Production Exists
### 生产级存在

表示完整、可部署、面向真实企业运行的生产能力。

例如：

```text
完整 IAM / Authentication
Role / Authority system
Policy Engine
Approval System
Workflow Engine
Control Plane
Enterprise Profile platform
tenant isolation
production registry
production-grade governance
```

当前项目：

> **不以 Production Exists 为目标。**

---

## 3.4 Closure Status ≠ Exists Level
### “关闭状态”与“存在层级”必须分开

`Architecturally Exists / Evidence-backed Exists / Production Exists` 描述的是一个能力或边界**以什么程度存在**。

`Conceptually Closed / Evidence-backed Closed` 描述的是一个当前问题或 Gate **是否已经足够关闭**。

二者不得混用。

### Conceptually Closed

表示：

```text
- 核心责任已经明确；
- 边界已经明确到足以指导后续行为；
- 不存在阻塞当前 v1 的结构性矛盾；
- 可以不依赖额外实现而在当前范围内关闭；
- 但不代表该主张已经获得新的 empirical evidence。
```

### Evidence-backed Closed

表示：

```text
- 该边界被明确选入当前 Evidence Scope；
- 仅靠概念澄清不足以关闭；
- 已完成所需的最小运行实验 / test / vertical slice；
- Evidence 足以支持当前 v1 的关闭判断。
```

因此允许出现：

```text
Platform Contract Authority
→ Conceptually Closed for v1

Binding Conformance
→ Evidence Gap / PARK

Minimum Architectural Framework v1
→ 仍然可以成立
```

前提是：

> **Binding Conformance 没有被 Architecture Review 明确选入 v1 Evidence Scope，且其未证明状态不与已有 evidence-backed 边界发生矛盾。**

原则：

> **Conceptual Closure ≠ Evidence-backed Closure.**

> **Normative architectural meaning ≠ automatic implementation requirement.**

---

# 4. Core Architecture Thesis

当前架构的最高原则：

> **Everything is replaceable. Nothing is casually replaceable.**

含义：

```text
- 没有任何实现拥有永久特权；
- Runtime 可以替换；
- Adapter 可以替换；
- Capability implementation 可以替换；
- Domain / Enterprise semantics 可以演进；
- Platform Standard 自身也可以版本化和演进；
- 但替换必须保持已有架构义务，或提供明确迁移路径；
- 越多长期资产依赖的边界，变化越需要谨慎。
```

稳定的目标不是：

```text
固定某一份代码
```

而是：

```text
稳定责任
稳定边界
稳定公共承诺
允许实现替换
```

---

# 5. Current Layer Model

当前架构关系：

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

重要：

```text
Domain
```

与：

```text
Enterprise
```

不是严格父子关系。

它们是不同维度：

```text
one Enterprise may use multiple Domains
one Domain may be used by multiple Enterprises
```

---

# 6. Layer Responsibility

所有问题优先按责任层判断，而不是按“哪个文件最方便改”判断。

| 问题 / 变化 | 默认责任层 |
|---|---|
| execution lifecycle / cancel / timeout / recovery / reconciliation / execution certainty | Runtime |
| vendor / API / external-system integration difference | Adapter |
| concrete Capability implementation | Capability implementation |
| shared cross-implementation contract / invocation / result semantics | Platform Standard |
| professional / industry meaning | Domain |
| enterprise-specific organization / policy / approval / vocabulary / risk preference | Enterprise |
| local new semantic affecting only limited contexts | Extension |
| repeated cross-boundary semantic gap affecting interoperability / replaceability / portability | Platform Standard review candidate |
| current Runtime cannot satisfy execution obligations | Runtime repair / upgrade / replacement candidate |
| Runtime must understand enterprise/domain meaning | architecture boundary failure candidate |
| cross-capability sequencing / parallel / branch / long-running process structure | Workflow / Orchestration |

原则：

> **Change where the responsibility lives.**

---

# 7. Runtime — Current Meaning

Runtime 回答：

> **How does execution run?**

Runtime 是：

> **可替换的执行实现，负责将已经被接受的执行意图可靠地变成真实运行状态和执行结果。**

Runtime 当前拥有：

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

已经接受的重要执行语义：

```text
exception != proof of non-execution
timeout != failure
unresolved execution never auto-replays
reconciliation is explicit
```

Runtime 负责：

```text
execution lifecycle
execution state
execution certainty
cancel / timeout
recovery
reconciliation
runtime-local control
capability execution mechanics
```

Runtime 不负责理解：

```text
company organization
role meaning
approval meaning
professional ontology
enterprise policy meaning
domain vocabulary
```

Runtime 必须继续保持：

```text
enterprise-free
domain-free
replaceable
```

---

# 8. Runtime Replaceability

Runtime 可替换是 Architecture Commitment。

替代 Runtime 不要求：

```text
same classes
same APIs
same Agent Loop
same framework
same source structure
```

它需要保持的是架构义务，例如：

```text
required execution semantics
standard invocation/result usability
execution certainty semantics
required lifecycle guarantees
necessary context preservation
no forced rewrite of upper-layer contracts
```

这被称为：

> **Runtime Conformance Boundary**

该边界在治理上长期成立：

```text
Runtime implementation
= replaceable

Runtime architectural obligations
= must be preserved or explicitly migrated
```

是否已经存在第二 Runtime、是否需要 empirical replacement proof、是否授权 Runtime replacement pilot，属于 **Current Decision Snapshot / Architecture Risk Queue**，不属于 Stable Governing Core。

任何 Runtime replacement pilot 都必须经过独立的 Stage authorization；不得因为“Runtime 可替换”是 Architecture Commitment，就自动要求实现第二 Runtime。

---

# 9. Platform Standard — Current Meaning

Platform Standard 不是：

```text
完整企业模型
抽象世界本体
所有未来概念的集合
Runtime 的替代品
```

Platform Standard 是：

> **独立演进的上层资产与可替换的下层执行实现之间，稳定而可演进的协调边界。**

它的三项核心价值：

## Coordination

通过公共 Contract 让独立实现可以协作。

## Isolation

保证变化尽量只发生在应该变化的位置。

例如：

```text
enterprise policy change
≠ Runtime rewrite

domain terminology change
≠ Platform Core rewrite

Runtime replacement
≠ rewriting all Domain / Enterprise assets
```

## Evolution

让系统通过：

```text
Extension
Versioning
Compatibility
Migration
Evidence-based promotion
```

持续生长，而不是每次新需求都重构整个系统。

价值判断：

> **Platform Standard is valuable when it removes unnecessary coupling while preserving necessary variation.**

---

# 10. Platform Standard Core v0.1 — Current Status

当前已经验证的最小执行路径：

```text
Capability Descriptor
      ↓
InMemory Descriptor Registry
      ↓
Standard Invocation
      ↓
Platform Validator
      ↓
Runtime Adapter
      ↓
Existing Runtime
      ↓
Standard Result
  + ArtifactRef(s)
  + Minimal Trace
```

当前已经证明：

```text
one complete Standard → Adapter → Runtime → Result path
second Capability portability
same-ID multi-version routing
no AgentCore change
no Runtime change
unresolved execution mapping
Extension support
```

重要解释：

> **Core v0.1 是第一组 evidence-backed stable contract slice。**

它不是：

> “未来 Platform Standard 的全部最终 Core 已经被确定。”

---

# 11. Capability — Stable Contract Meaning

Capability 表示：

> **系统能够做什么。**

当前架构希望 Capability 成为可沉淀、可替换实现、可被 Platform 稳定暴露的长期资产单位。

## 11.1 Capability is not only an implementation

一个 Capability 不等同于：

```text
Python class
tool function
provider SDK
specific model
specific Runtime object
```

更准确地说：

> **Capability 是一个版本化的能力身份：它具有稳定的 semantic intent，以及对 Platform caller 可合法依赖的公开、可移植 Contract；不同 implementation 可以通过 Binding / Adapter 去兑现它，并由不同 Runtime 可靠执行，而不要求上层资产随 implementation 一起变化。**

## 11.2 Minimum Sufficient Authority

Platform Capability Contract 的 authority 必须处于两个极端之间。

Too weak：

```text
Platform Capability Descriptor
= metadata only
```

会失去：

```text
interoperability
implementation replaceability
Runtime replaceability
asset portability
```

Too strong：

```text
Platform decides:
implementation algorithm
Runtime internals
provider/model choice
implementation-specific execution detail
```

会让 Platform 变成新的巨石。

因此当前稳定原则是：

> **Platform Capability Contract 对 Platform caller 可以合法依赖、且在替换 implementation 后仍应保持的 versioned observable promise 具有最小充分权威。**

也可以表达为：

> **Platform owns the public WHAT, not the internal HOW.**

## 11.3 Responsibility split

```text
Domain / Enterprise / Capability Definition
→ owns professional / organizational semantic meaning

Platform Capability Contract
→ stabilizes the public, portable, versioned promise

Binding / Adapter
→ owns compatibility / translation between the Platform promise and a concrete implementation

Capability Implementation
→ owns HOW the capability work is actually performed

Runtime
→ owns HOW the implementation is executed reliably
```

其中：

```text
Domain / Enterprise meaning
≠ Platform Core ontology

Platform public contract
≠ Runtime internal contract

Binding / Adapter compatibility
≠ Runtime execution lifecycle
```

## 11.4 Versioned Observable Promise

Platform Capability Contract 当前概念上至少保护：

```text
stable capability identity
capability version
public accepted input contract
public success output contract
portable observable execution semantics
semantic identity must not silently change
```

它不拥有：

```text
algorithm
prompt
model
provider
internal steps
reasoning method
retry strategy
Runtime internals
professional ontology
enterprise policy
domain evaluation methodology
```

`execution.side_effect` 属于 portable observable execution semantic 的当前最小例子，因为它描述 caller / governance 可以跨 implementation 依赖的外部效果边界，而不是 Runtime 内部执行方法。

## 11.5 Semantic Commitment

Schema compatibility alone does not define capability meaning.

例如：

```text
translate_text:
string → string
```

结构正确并不意味着 implementation 真正在“翻译”。

因此 Capability 同时具有：

```text
Portable Observable Contract
+
Stable Semantic Commitment
```

但是：

> **Semantic Commitment 是 normative in meaning，并不意味着当前 Platform Core 必须拥有 Universal Semantic Schema 或 Universal Semantic Validator。**

专业语义可继续由：

```text
Domain
Enterprise
generic Capability definition
Capability-specific specification / evidence
```

承担。

Platform 的责任是保护：

> **同一个 versioned Capability 不得被 implementation 静默改成另一件事。**

## 11.6 Validation separation

必须长期保持：

```text
Platform Contract Validation
≠
Binding / Conformance Validation
≠
Runtime Execution Validation
```

分别回答：

```text
Platform Contract Validation
→ 这个公共 Contract 本身是否合法？

Binding / Conformance
→ 这个 implementation 是否/如何有资格兑现这个公共 Contract？

Runtime Execution Validation
→ 这一次真实执行是否合法、是否完成、执行结果是否确定？
```

其中 Binding / Conformance 是一个**责任概念**，不等于当前必须建设通用 Conformance Framework。

其具体 Evidence 未来可以来自：

```text
schema checks
contract tests
reference examples
domain tests
evaluation
human review
```

具体选择必须服从 Minimum Stage / Evidence First 原则。

---

# 12. Adapter — Current Meaning

Adapter 是允许理解两边差异的翻译边界。

正确关系：

```text
Platform Standard
       │
       ▼
     Adapter
       │
       ▼
Current Runtime
```

Adapter 可以知道：

```text
Platform Capability id/version
Standard Invocation / Result
current Runtime-specific Action / Goal / Result
current Runtime execution API
```

这不违反 Runtime replaceability。

未来可能：

```text
Platform Standard
       │
       ├── Adapter A → Runtime A
       └── Adapter B → Runtime B
```

Architecture 要求：

> **Platform assets 不绑定 Runtime internals。**

Architecture 不要求：

> **Adapter 不知道 Runtime。**

---

# 13. Extension First

当前长期原则：

> **Extension First. Core Promotion Later.**

基本生命周期：

```text
Observed Need
    ↓
Local Solution
    ↓
Extension
    ↓
Real Usage
    ↓
Evidence
    ↓
RFC Candidate if justified
    ↓
Compatibility Review
    ↓
Promote / Reject / Remain Extension
    ↓
Migration if required
```

重要：

> **Repeated usage alone does NOT justify Platform Core promotion.**

Extension 可以长期甚至永久保持：

```text
Enterprise Extension
Domain Extension
Vendor / Adapter Extension
Experimental Extension
```

只有当一个语义在**多个彼此独立的真实上下文**中反复出现——这些上下文可以跨一个或多个 Domain、Enterprise、Runtime / Adapter implementation——并且开始损害：

```text
interoperability
replaceability
asset portability
```

时，才有资格进入 Platform Standard Review。

这不要求 Domain / Enterprise / Runtime / Adapter 四类环境必须全部各出现一次；判断依据是**跨边界重复性 + 系统性耦合成本**，不是类别凑齐。

---

# 14. Current Extension Evidence

当前 `enterprise.identity` 已经证明：

```text
enterprise semantics can enter via Extension
Platform Core schema unchanged
generic RuntimeAdapter remains enterprise-agnostic
agent_runtime/** unchanged
trace attribution can carry enterprise semantic evidence
```

它证明的是：

> **Stable Core + Adjustable Semantics**

它不是：

```text
完整 Identity system
Authentication
Authorization
Authority
Role
IAM
```

因此：

```text
enterprise.identity
= Evidence-backed Exists

Role / Authority / Policy
= Architecturally Exists
```

---

# 15. Architecture is NOT a Feature Roadmap

当前明确禁止以下错误理解：

```text
Architecture 里有 Identity
→ 下一步 Role

有 Role
→ 下一步 Authority

有 Authority
→ 下一步 Policy

有 Policy
→ 下一步 Approval

有 Approval
→ 下一步 Workflow
```

Architecture 的作用是：

> **当真实问题出现时，告诉系统这个问题属于哪一层。**

不是：

> **要求把图里的未来盒子全部实现出来。**

---

# 16. Architecture Risk Queue

Architecture Risk Queue 不是 roadmap。

它的定义：

> **当前尚未被证明、且一旦判断错误可能导致最大架构返工的风险集合。**

它不代表：

```text
P1 做完自动 P2
P2 做完自动 P3
```

正确机制：

```text
Hypothesis
    ↓
Minimum Stage / Discussion
    ↓
Evidence
    ↓
STOP
    ↓
Architecture Review
    ↓
Refresh Risk Queue
```

一个 WATCH / PARK 项目：

> 可以永远不进入实现。

---
