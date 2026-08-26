# CATALYST — CAPABILITY-PRESERVING EVOLUTION PROMOTION REVIEW V0.1

> **Status:** ARCHITECTURE / GOVERNANCE HARVEST REVIEW — CANDIDATE
> **Type:** Evidence-backed promotion review; not a Platform object or implementation engine
> **Reviewed baseline:** `main @ 763a3777713fd38e6db3c4eeeddcf321506cc20f`
> **Implementation authorization:** Documentation / Harness-method clarification only
> **Functional Runtime/Core change:** NONE

## 1. Question under review

Catalyst already states that implementations are replaceable and that long-term assets should survive implementation churn. Real V0.2 and Case01 work exposed a more specific recurring engineering question:

> When a real implementation fails or becomes expensive to maintain, should Catalyst repair it, replace one component, rebuild it cleanly, recompose it, adopt a mature external mechanism, replace a larger subsystem, or retire it?

The review must decide whether this recurring pattern deserves formal sedimentation, and if so, **where it belongs without creating duplicate authority or a new Platform object**.

## 2. Existing authority / overlap audit

### 2.1 `ARCHITECTURE.md`

Already owns:

```text
responsibility boundaries
stable WHAT / replaceable implementation direction
Everything is replaceable. Nothing is casually replaceable.
Runtime conformance boundary
Extension First / evidence before Core promotion
asset preservation
architecture failure signals
```

Gap:

It does not yet explicitly state that **repair has no default priority**, nor does it define the stable architecture obligation for preserving capability/evidence/lineage while implementation-evolution alternatives are compared.

Decision:

**UPDATE MINIMALLY.** Add the stable principle only. Do not add a repair engine, candidate schema, decision service, or implementation algorithm.

### 2.2 Active Governing Baseline v1.1 Part A

Already owns:

```text
Everything is replaceable. Nothing is casually replaceable.
Change where responsibility lives.
evidence before implementation/Core promotion
minimum-stage / STOP discipline
stable responsibility / boundary / public promise
```

Gap:

None that requires mutating the already-activated v1.1 baseline in place. The new principle is consistent with, and more specific than, existing governance.

Decision:

**NO CHANGE.** Rewriting an activated historical governing baseline would create unnecessary duplicate authority. A future independently authorized governance version may absorb the architecture refinement if needed.

### 2.3 `docs/CATALYST_CAPABILITY_HARVEST_DESIGN_PHILOSOPHY_V0.1.md`

Already explains:

> **Preserve capability, not implementation.**

It also explains that evidence/evaluation knowledge, compatibility/migration knowledge, Domain/Enterprise meaning, and operational learning may survive temporary implementations.

Decision:

**NO CHANGE.** Do not duplicate that philosophy into a second design-philosophy document. Architecture may reference and elevate the principle at the responsibility level.

### 2.4 `platform-harness/skills/agent-construction/SKILL.md`

Already owns pre-construction decisions:

```text
UNDERSTAND
→ responsibility / capability need
→ capability search
→ REUSE / ADAPT / COMPOSE / RECONSTRUCT / BUILD GAP
→ simplest justified solution form
```

It already admits failed implementations and external complete solutions as inputs, and it already treats Harness/Runtime/mechanisms as replaceable.

Decision:

**NO CHANGE.** Construction decides how to satisfy a need. It should not also own the complete post-failure evolution/accept-rollback method.

### 2.5 `platform-harness/skills/capability-evaluation/SKILL.md`

Already owns observable execution evidence and failure attribution. It explicitly separates product/capability, provider, Runtime, external API, evaluator, and benchmark failures and forbids modifying the tested solution during evaluation.

Decision:

**NO CHANGE.** Components report facts; independent Evaluation attributes and judges them. Do not create a second self-monitoring or self-certification mechanism.

### 2.6 `platform-harness/skills/capability-optimization/SKILL.md`

Already owns:

```text
Reference
→ failure diagnosis by responsibility
→ bounded hypothesis/candidate
→ same benchmark
→ accept or rollback
→ reusable migration/replacement learning
```

Gap:

The current method implicitly assumes "choose a candidate change" but does not explicitly compare Repair / Local Replace / Rebuild / Recompose / Replace Subsystem / External Adopt / Retire, preserve organizational value before changing implementation, compare total evolution cost rather than diff size, or record an explicit Evolution Lineage.

Decision:

**UPDATE / VERSION METHOD.** This is the correct home for the detailed replaceable HOW.

### 2.7 Platform Asset Census / Integration Artifact Decision Matrix

The Asset Census already identifies fragmented evolution/replacement reasoning and recommends **one shared replacement decision model while preserving implementation-specific execution separately**. The Artifact Decision Matrix repeatedly rejects new Engines/Services/Registries when existing methods and references can carry the responsibility.

Decision:

**REFERENCE AS SUPPORTING EVIDENCE; DO NOT MODIFY.**

### 2.8 README / Capability Visibility Index / Development Workflow / historical Stage and Evidence files

- README already summarizes Capability-not-Implementation and replaceability; full method text there would duplicate authority.
- Capability Visibility Index navigates governed Capability value/evidence, not architecture methods; adding this principle as a Capability entry would be a category error.
- Development Workflow governs repository publication/audit authority, not implementation evolution choices.
- Historical Stage/Evidence files must remain immutable records of what was decided and observed at that time.

Decision:

**NO CHANGE.**

## 3. Evidence supporting promotion

### Evidence Case A — native-tools v1 → native-tools v2

Repository-authoritative evidence exists in:

```text
CATALYST_V0.2_MULTI_TOOL_REPAIR_REPLACE_DESIGN_REVIEW.md
CATALYST_V0.2_NATIVE_TOOLS_V2_STAGE_SPEC.md
evidence/v0.2/**
```

Observed pattern:

```text
real model emitted multiple tool calls
→ failure attributed to Harness native-tool interaction
→ stable per-execution Runtime certainty semantics identified as worth preserving
→ old assumption "one model turn == one tool call == one Act" identified as obsolete
→ candidates compared:
     PATCH v1                    REJECT
     REBUILD v2                  ACCEPT
     EXTERNAL TOOL LOOP ADOPT    WATCH / CONDITIONAL
     REPLACE WHOLE HARNESS       REJECT
→ v1 retained as reference/rollback
→ v2 built around the corrected primitive
→ same capability benchmark / real model+tool evidence
→ durability finding repaired in a bounded seam
→ Formal Baseline + Candidate re-evaluation
→ accepted without Platform Core expansion
```

This is direct evidence that a small patch can be worse than a clean rebuild, and that replacing the largest possible subsystem would discard more proven value than the failure justified.

### Evidence Case B — Building Regulation Evidence Capability Local Pilot

The Phase 2B Local Pilot was intentionally performed outside the Catalyst repository and ended with Catalyst `main` unchanged. The Stage Close report supplied to the Post-Pilot Architecture Review recorded:

```text
implementation selection: REBUILD
old Building Regulation Agent 2.0 retained only as reference
repair cost judged higher than a minimal clean implementation because of provider/network/OCR/SQLite/index/API/project-facts coupling
real Case A / B accepted with source-native regulation evidence
Case C insufficient-context fail closed
100% normative/quantitative claims bound to evidence
unsupported regulatory numbers = 0
Runtime change = NONE
Platform Core change = NONE
```

Because the Local Pilot was explicitly repository-external, this review does **not** pretend its local evidence bytes are GitHub code truth. It is supporting cross-context architecture evidence supplied through the completed Stage Close / Post-Pilot review, not a reason to copy Domain evidence into Platform Core.

Important architectural value:

The same evolution logic appeared in a professional Capability implementation, not only in Harness infrastructure. That supports treating the principle as cross-implementation architecture guidance while keeping the detailed decision method Harness-side and replaceable.

## 4. Two-layer necessity review

### Layer 1 — Stable Architecture Principle

Necessary because Catalyst needs a stable answer to:

```text
What must survive implementation churn?
Does Repair have automatic priority?
What obligations constrain replacement?
When should external replacement be admissible?
How is organizational learning preserved across implementation changes?
```

Accepted stable meaning:

> **Stable WHAT / replaceable HOW. Preserve capability and required obligations, not implementation privilege. Repair is not the default; implementation evolution is selected from evidence. Replacement is a first-class path, but never a casual one.**

Architecture should define only the obligation and decision discipline.

### Layer 2 — Replaceable Harness Method

Necessary because the stable principle alone does not tell an implementer how to compare concrete alternatives after evidence reveals a failure.

The existing `capability-optimization` method is the correct owner for:

```text
Attribute
Preserve
Diagnose
Search alternatives
Generate candidates
Compare total evolution cost
Freeze Reference
Bounded candidate
Same benchmark/evidence
Accept / Rollback
Record Evolution Lineage
```

This layer remains replaceable HOW. A better future method can replace it without changing the architecture principle.

## 5. Candidate action vocabulary

The method may consider:

```text
REPAIR / PATCH
LOCAL REPLACE / REPLACE COMPONENT
REBUILD COMPONENT
RECOMPOSE
REPLACE SUBSYSTEM
EXTERNAL ADOPT / ADAPT
RETIRE / REMOVE
```

These are not Platform ontology IDs, schema enums, or automatic state-machine transitions. They are decision vocabulary for comparing bounded alternatives.

No action has automatic priority.

## 6. Total Evolution Cost principle

Candidate comparison must not collapse to "smallest code diff". Material cost may include:

```text
immediate implementation effort
legacy-understanding cost
future maintenance burden
compatibility-patch debt
regression risk
migration risk
rollback difficulty
hidden coupling
pressure to pollute Runtime / Platform Core
future replaceability cost
loss of proven semantics/evidence
opportunity cost versus mature external alternatives
```

Therefore a larger clean rewrite can be the lower-cost decision when a small patch keeps an invalid assumption or long-term coupling alive.

## 7. Self-observability boundary

Replaceability requires enough evidence to locate the failure. The accepted direction is:

```text
components report bounded facts
→ Evaluation independently attributes/judges
→ Optimization compares evolution candidates
```

Not:

```text
component fails
→ component certifies its own diagnosis
→ automatic self-repair service mutates production
```

This review does not authorize a Monitoring Service, Health Platform, Self-Healing Engine, or autonomous architecture mutation.

## 8. Evolution Lineage

Implementation replacement should preserve enough organizational memory to later answer:

```text
what Reference existed?
what failure/limitation triggered review?
who owned the responsibility?
what obligations/value had to survive?
what candidates were considered?
why was one accepted/rejected?
what benchmark/evidence supported it?
what migration/rollback implications remain?
what limits remain unproven?
what implementation is current now?
```

This does not require a Lineage Service or universal schema. Git history, evidence artifacts, Stage reviews, and authoritative references may carry the lineage.

## 9. External mechanism boundary

External implementations are first-class HOW candidates when they can satisfy the required Catalyst responsibility/evidence boundary with lower total cost and acceptable coupling.

Catalyst need not own source code for every mechanism. It must preserve the obligations that make the mechanism admissible, for example where material:

```text
public/semantic responsibility
execution identity / certainty
policy boundary
tool/result correlation
recovery semantics
evidence availability
failure attribution
Domain / Enterprise separation
```

Do not clone mature machinery merely so Catalyst can claim authorship.

## 10. Non-duplication / non-expansion verdict

```text
NEW PLATFORM OBJECT                    NO
NEW PLATFORM STANDARD FIELD           NO
NEW REGISTRY / ENGINE / SERVICE        NO
NEW MONITORING / SELF-HEALING SYSTEM  NO
GOVERNING BASELINE v1.1 REWRITE       NO
README METHOD DUPLICATION              NO
CONSTRUCTION METHOD DUPLICATION        NO
EVALUATION METHOD DUPLICATION          NO
CAPABILITY INDEX ENTRY                 NO

ARCHITECTURE PRINCIPLE CLARIFICATION   YES
CAPABILITY-OPTIMIZATION METHOD v2      YES
```

## 11. Promotion verdict

```text
CAPABILITY-PRESERVING EVOLUTION PRINCIPLE
EVIDENCE-BACKED ENOUGH FOR ARCHITECTURE CLARIFICATION — PASS

DETAILED IMPLEMENTATION EVOLUTION DECISION METHOD
BELONGS TO REPLACEABLE HARNESS-SIDE OPTIMIZATION — PASS

REPAIR AS DEFAULT
REJECT

REPLACEMENT AS UNCONSTRAINED DEFAULT
REJECT

PLATFORM CORE EXPANSION
REJECT
```

The intended result is not more architecture. It is a cleaner evolution rule:

> **Preserve the organizational capability and proven obligations; let implementation compete for the right to remain.**

## 12. Stop condition

After the Architecture clarification and `capability-optimization` v2 method are reviewed and merged:

**STOP.**

Do not implement an Evolution Engine, automatic replacement controller, health service, new registry, migration service, or new Platform Standard object from this review alone.
