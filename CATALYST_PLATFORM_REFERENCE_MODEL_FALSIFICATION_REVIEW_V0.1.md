# CATALYST PLATFORM — REFERENCE MODEL FALSIFICATION REVIEW V0.1

> **Status:** RESEARCH / FALSIFICATION REVIEW
> **Implementation Authorization:** NO
> **Phase II Authorization:** NO
> **Stage:** Catalyst Platform Integration V0.1
> **Base integration branch before this review:** `301547b65138c3433ff6dfbe3c7a27dab766330f`
> **Purpose:** test the minimized reference model against real existing Catalyst assets before authorizing any integration implementation.

---

# 0. Falsification rule

The model is accepted only if real existing assets can be connected without:

```text
- duplicating Platform Capability contracts;
- promoting Case-local harvested assets into Platform Capability identities;
- copying mutable Evaluation status into an Index;
- minting Capability IDs for unmet needs;
- creating a new shared Platform schema merely so Construction and Evaluation can communicate.
```

Required tests:

```text
F-01 Platform-admitted Capability discovery
F-02 Case-local harvested asset discovery
F-03 Evaluation/Harvest evidence discovery
F-04 Existing Capability + missing Capability need in one Construction Decision
F-05 Construction responsibility → Evaluation evidence formation without implementation reverse-engineering
```

---

# 1. F-01 — Platform-admitted Capability discovery

## Real sample

`main @ 19f0d7701ff849bd837bd5c2c4aba16ad5914968`

Existing Capability:

```text
compose_report@1.0.0
```

Existing authority/evidence surfaces:

```text
examples/platform_standard_reference.py
  → compose_report_descriptor()
  → ComposeReportCapability
  → make_stack() registers compose_report@1.0.0

tests/test_capability_contract_conformance_pilot.py
  → CC-1 conforming binding accepted
  → CC-4/CC-5 incompatible bindings rejected before execution
  → CC-9 protects the existing Platform CapabilityDescriptor field set
```

## Minimal hypothetical Index entry

```text
capability_ref: compose_report@1.0.0
summary: Create a report from structured input.
authority_ref: main@19f0d770...:examples/platform_standard_reference.py#compose_report_descriptor
asset_refs:
  - main@19f0d770...:examples/platform_standard_reference.py#ComposeReportCapability
  - main@19f0d770...:examples/platform_standard_reference.py#make_stack
evidence_refs:
  - main@19f0d770...:tests/test_capability_contract_conformance_pilot.py
```

No input/output/execution schema is copied into the Index.

## Result

# **PASS**

The Index can discover and navigate to a real Platform Capability without becoming a second Capability contract or Registry.

No new Platform object is required.

---

# 2. F-02 — Case-local harvested asset discovery

## Real sample

`case-02 @ 336f8e6f28c1569e5c53f245daaa3ee8a197f33d`

Existing harvested asset:

```text
WAKU-A01
Retrieval-gated memory query selection
```

The frozen Case02 catalog explicitly says:

```text
catalog_scope
= Case-local governed knowledge assets
= not a Platform Core registry
= not callable implementations
```

`WAKU-A01` already owns:

```text
asset_id
problem_solved
responsibility_boundary
replaceability
reuse_preconditions
known_limits
source_evidence
source_commit
classification
confidence
```

It is useful organizational value, but it is NOT a Platform Capability identity.

## Initial field-model test

The prior Field Minimization Audit required:

```text
capability_ref
```

for every Index entry.

Applying that requirement to `WAKU-A01` creates a semantic problem:

```text
Case-local harvested/provisional asset
→ forced into a field named capability_ref
→ appears more admitted/stable than current evidence authorizes
```

## Initial result

# **FAIL**

The mandatory `capability_ref` rule is too strong.

## Minimum repair

Do NOT add a new field or a new identity system.

Repair only the cardinality/meaning:

```text
authority_ref
= REQUIRED for every Index entry

capability_ref
= OPTIONAL
= present only when a stable Capability identity actually exists
```

A provisional/harvested entry may therefore be:

```text
summary: Retrieval-gated memory query selection
authority_ref: case-02@336f8e6...:case-02/01-a-waku-understanding/CASE_02_WAKU_ASSET_CATALOG_V0.1.json#WAKU-A01
asset_refs:
  - same governed Case asset record
evidence_refs:
  - source evidence reachable through the authority record
lineage_refs:
  - ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad
capability_ref: OMITTED
```

## Post-repair result

# **PASS**

This preserves the distinction:

```text
valuable governed asset
!= admitted Platform Capability
```

and avoids creating a generic provisional-Capability ID scheme.

---

# 3. F-03 — Case01 Evaluation / Harvest evidence discovery

## Real sample

`case-01 @ 232d6837647c68670fba3f3b2faf7ec1fac73f0a`

Existing product/evaluation authority:

```text
CASE_01_E2_BREA_PRODUCT_CAPABILITY_EVALUATION_V0.1.md
```

It defines BREA's accepted product purpose, OBL-01..OBL-06, product responsibilities PR-01..PR-18, target identity requirements, capability-state vocabulary, benchmark case contract and grader separation.

Existing execution evidence:

```text
evaluation-v0.1/PRODUCT_CAPABILITY_EVALUATION_REPORT.md
```

The report records:

```text
frozen Candidate identity
benchmark results
failure attribution
PR evidence states
explicit unproven boundaries
Harvest interpretations
```

Most importantly:

```text
OBL-03/OBL-04 fail-closed numeric safety
→ HARVEST_CANDIDATE

FN-04/FN-05/SEAM-03 source-evidence binding
→ DO_NOT_HARVEST_YET

Case01 evaluation runner
→ KEEP_CASE_LOCAL
```

## Minimal navigation model

No `health=green/yellow/red` is required.
No Harvest verdict needs to be copied into the Index.
No Platform Capability ID needs to be minted for `OBL-03/OBL-04` yet.

A discovery entry can point to:

```text
summary: Bounded fail-closed / no-unsupported-numeric safety candidate
authority_ref:
  case-01@232d683...:.../CASE_01_E2_BREA_PRODUCT_CAPABILITY_EVALUATION_V0.1.md

evidence_refs:
  case-01@232d683...:.../evaluation-v0.1/PRODUCT_CAPABILITY_EVALUATION_REPORT.md

known_limits_ref:
  same accepted evaluation report

capability_ref: OMITTED until a stable reusable Capability identity is separately accepted
```

## Result

# **PASS**

The mutable evidence state remains owned by Evaluation.
The Index only provides a path to it.

This proves a separate Capability Health object is not required for the current integration.

---

# 4. F-04 — Existing Capability + missing Capability need in one Construction Decision

## Test need

Use a deliberately mixed requirement:

```text
Create a structured professional-regulation report from validated evidence,
while preserving source-native citation binding and preventing unsupported normative numeric claims.
```

## Existing value available

A real admitted generic Capability already exists:

```text
compose_report@1.0.0
```

Case01 also contains governed safety evidence for:

```text
OBL-03/OBL-04 fail-closed numeric safety
```

but complete source-native professional evidence binding remains unproven / DO_NOT_HARVEST_YET.

## Minimized Construction Decision sketch

```text
NEED
  purpose_or_required_outcome:
    Produce a structured professional-regulation report from validated evidence.

RESPONSIBILITY
  responsibilities:
    - produce the report artifact from structured validated content
    - preserve source/citation traceability
    - do not emit unsupported normative numeric conclusions
  material_uncertainties:
    - whether current source-native evidence binding is sufficient for the target source set

CAPABILITY SEARCH
  reused_capability_refs:
    - compose_report@1.0.0
  reused_asset_refs:
    - Case01 OBL-03/OBL-04 Evaluation/Harvest evidence
  missing_capability_needs:
    - complete source-native citation/evidence binding for the target professional corpus

SOLUTION
  selected_solution_form:
    undecided until the missing capability need is characterized
  mechanism_or_implementation_candidate:
    reuse compose_report for formatting; do not decide the professional binding mechanism yet

PROOF
  evidence_requirements:
    - source/citation fidelity
    - no unsupported normative numeric claims
    - positive evidence-binding case
    - fail-closed negative case

GOVERNANCE
  not_required_now:
    - generic Agent loop unless adaptive execution is proven necessary
    - vector database unless retrieval evidence requires it
  stop_condition:
    stop once the smallest binding mechanism satisfies the target evidence requirements
```

## Result

# **PASS**

The Decision can express:

```text
known admitted Capability
+
reusable Case-local evidence asset
+
genuinely missing capability need
```

without creating a premature Platform Capability ID for the missing need.

No new Capability identity system is required.

---

# 5. F-05 — Construction responsibility → Evaluation evidence without implementation reverse-engineering

## Existing Construction-side mechanism

The current `agent-construction` Skill already maps task characteristics to evidence needs, for example:

```text
BOUNDED_CORPUS + evidence sensitivity
→ retrieval/citation evidence

EXTERNAL_SIDE_EFFECT
→ world-state verification

CROSS_SESSION_STATE
→ restart/persistence evidence

DYNAMIC_AGENT_LOOP
→ trajectory/tool-boundary evidence

HIGH_RISK_PROFESSIONAL_JUDGMENT
→ fail-closed + professional review evidence
```

Its current weakness is not absence of this relationship. It is that the Construction Decision does not yet explicitly persist `RESPONSIBILITIES`, capability search results, selected solution form, material uncertainty and Runtime requirements.

## Existing Evaluation-side mechanism

The Case01 Evaluation Contract explicitly separates:

```text
Product responsibility
Agent implementation
Knowledge/source state
Execution infrastructure
Evaluation infrastructure
```

and requires each benchmark Case to declare fields such as:

```text
product_responsibilities_tested
public_task_statement
provided context
expected observable outcome
hidden rubric
critical gate conditions
required evidence properties
failure attribution hints
```

The Evaluation Contract also explicitly says the responsibility map is by user responsibility, not repository files.

## Test

Given a repaired Construction Decision containing:

```text
responsibilities:
  - select applicable regulation evidence
  - avoid unsupported normative numbers
  - preserve citation/provenance

evidence_requirements:
  - applicability evidence
  - deterministic numeric trace
  - source/locator fidelity
  - fail-closed negative case
```

Evaluation can form the Case Contract and its private rubric/grader implementation without first reading the implementation to discover what the product was supposed to do.

Implementation inspection remains valid later for:

```text
failure attribution
trajectory diagnosis
Harvest/reconstruction understanding
```

but it is not required to define product responsibility.

## Result

# **PASS**

The existing Construction Decision can be minimally adapted into the handoff.

A new `ResponsibilityEvidenceBrief` Platform object, Handoff Service or universal shared schema is not justified.

---

# 6. Consolidated falsification result

```text
F-01 Platform-admitted Capability discovery
PASS

F-02 Case-local harvested asset discovery
INITIAL FAIL → MINIMUM FIELD RULE REPAIR → PASS

F-03 Evaluation/Harvest evidence discovery
PASS

F-04 Existing Capability + missing Capability need
PASS

F-05 Construction → Evaluation responsibility/evidence handoff
PASS
```

Overall:

# **PASS WITH ONE TARGETED RESEARCH-LEVEL REPAIR**

The model survived real existing assets after making `capability_ref` optional for provisional/non-admitted entries.

---

# 7. Targeted correction authority

This review supersedes ONLY the following statements in:

```text
CATALYST_PLATFORM_FIELD_MINIMIZATION_AUDIT_V0.1.md
```

### Superseded

```text
capability_ref
= REQUIRED for every Index entry
```

and the minimum-entry example that treated it as universally required.

### Corrected rule

```text
authority_ref
= REQUIRED

summary
= REQUIRED discovery hint

capability_ref
= OPTIONAL
= required only when the indexed value already has a stable governed Capability identity

asset_refs[]
= sparse references when asset forms exist

evidence_refs[]
= references when evidence exists
```

No new field is introduced by this correction.

All other Field Minimization Audit decisions remain unchanged unless separately superseded later.

---

# 8. Reference syntax decision

Do NOT create a Catalyst URI protocol in V0.1.

A reference only needs to be resolvable and sufficiently revision-stable for its authority/evidence role.

Current repository-native practice is sufficient:

```text
branch-or-exact-commit
+ repository path
+ optional local anchor/asset id
```

Use exact commit SHA for frozen evidence/provenance when material.
Use a branch/current authority reference only when following the current accepted authority is the intended behavior.

A custom URI/ref schema is NOT justified.

---

# 9. What this falsification removes from scope

The review provides direct evidence against building:

```text
mandatory provisional Capability IDs
Capability Health object
Capability Status state machine
shared ResponsibilityEvidenceBrief Platform object
Handoff Service
Capability Registry service
Evidence Ledger
reference URI protocol
```

---

# 10. Remaining minimum candidate surface

After real-asset falsification, the persistent integration candidate remains only:

```text
1. one tiny repository-native visibility index
   - authority_ref required
   - capability_ref optional when real identity exists
   - references, not copies

2. targeted repair of existing agent-construction Skill
   - no new Construction Engine

3. expanded existing Construction Decision
   - Construction → Evaluation handoff
   - no standalone shared Platform object

4. one minimum cross-component proof
   - current Platform/Runtime/Harness/Evaluation surfaces only
```

---

# 11. Authorization status after falsification

This review does NOT itself authorize Phase II implementation.

However, the pre-implementation research gate is now substantially closed:

```text
Asset Census
PASS

External Comparative Audit
PASS FOR CURRENT SCOPE

Artifact Decision Matrix
PASS FOR CURRENT SCOPE

Field Minimization Audit
PASS WITH TARGETED CORRECTION

Real-Asset Reference Model Falsification
PASS
```

Recommended next governance action:

> review this falsification result and, only if accepted, issue a **minimum Phase II implementation authorization** limited to one repository-native visibility index and its deterministic rediscovery proof.

Do not combine Phase II implementation with Harness Skill repair, Runtime changes, Evaluation changes, Case01 work or Platform Core changes in the same authorization.
