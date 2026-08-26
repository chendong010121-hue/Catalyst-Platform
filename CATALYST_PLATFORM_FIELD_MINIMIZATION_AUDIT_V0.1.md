# CATALYST PLATFORM — FIELD MINIMIZATION AUDIT V0.1

> **Status:** RESEARCH / FIELD-LEVEL DESIGN REVIEW
> **Implementation Authorization:** NO
> **Phase II Authorization:** NO
> **Stage:** Catalyst Platform Integration V0.1
> **Purpose:** minimize the persistent field surface before any Capability visibility or Harness-method integration is implemented.

---

# 0. Governing rule

Each persistent surface must answer one distinct question:

```text
CapabilityDescriptor
→ WHAT may callers rely on?

Capability Visibility Index
→ WHERE can existing organizational value/evidence be found?

Construction Decision
→ WHY is this need being solved this way now?

Evaluation / Evidence Artifact
→ WHAT has actually been proven / failed / limited?
```

Therefore:

> **Reference across surfaces. Do not copy authority across surfaces.**

A field is admitted only if it cannot be more correctly owned by an existing authoritative artifact.

Allowed field dispositions:

```text
KEEP      — persist here
REF       — persist only a resolvable reference
DERIVE    — compute/read from referenced authority; do not persist twice
OPTIONAL  — include only when materially present
DROP      — do not include
```

---

# 1. Existing authority map

## 1.1 Platform CapabilityDescriptor authority

Already authoritative for:

```text
capability id
capability version
name
description
public input contract
public output contract
portable execution declaration
```

Do not duplicate those contracts into the visibility index or Construction Decision.

---

## 1.2 Case / harvested asset authority

Case02 demonstrates that harvested knowledge may legitimately own rich mechanism-specific facts such as:

```text
problem solved
responsibility boundary
mechanism summary
state semantics
dependencies
replaceability
reuse preconditions
known limits
source evidence
source commit
reconstruction notes
```

The Visibility Index should point to such a record rather than becoming a second copy of it.

---

## 1.3 Evaluation authority

Evaluation artifacts own observed evidence such as:

```text
run identity
benchmark identity
case outcomes
critical gates
failure attribution
responsibility evidence state
Harvest interpretation
explicit unproven boundaries
next material gap
```

The Visibility Index should reference evaluation evidence, not summarize mutable health as a second source of truth.

---

## 1.4 Construction Decision authority

Construction Decision owns the current choice context:

```text
need / outcome
material uncertainty
responsibility
reused assets
selected solution form / pattern / mechanism
why this choice
runtime requirements
evidence requirements
risks
not-required-now
stop condition
```

It is not a durable Capability definition.

---

# 2. Capability Visibility Index — field-by-field decision

The Index has one job:

> **allow a human or Harness to discover existing Capability value and reach the authoritative artifacts without prior knowledge of branch/path.**

It is NOT:

```text
Capability contract
asset catalog replacement
evaluation report
health database
dependency graph
Enterprise directory
implementation manifest
```

## 2.1 `capability_ref`

Disposition: **KEEP — REQUIRED**

Meaning:

A stable reference/label that allows multiple assets to be recognized as belonging to the same Capability identity where such identity already exists.

Rules:

- use Platform `id@version` when a Platform Capability exists;
- for pre-admission harvested/provisional capability, use the existing governed Case asset identity rather than inventing a fake Platform id;
- do not force every knowledge asset to become a Platform Capability.

Reason:

Without this field, cross-surface evidence cannot converge on the same organizational value.

---

## 2.2 `summary`

Disposition: **KEEP — REQUIRED, ONE SHORT LINE**

Meaning:

Human/Harness discovery hint: what problem/value this Capability represents.

Rules:

- not normative contract text;
- no detailed mechanism explanation;
- preferably derived from authoritative description/problem statement, but one small cached discovery summary is acceptable to avoid opening every artifact during search.

Reason:

A pure list of opaque refs is not discoverable enough.

---

## 2.3 `authority_ref`

Disposition: **KEEP — REQUIRED**

Meaning:

Reference to the current authoritative definition/record for the Capability identity or provisional asset.

Examples:

```text
Platform CapabilityDescriptor source
Case02 harvested asset record
other accepted Capability-specific governing record
```

Reason:

The index must never become authority merely because it is convenient.

---

## 2.4 `asset_refs[]`

Disposition: **KEEP — REQUIRED, SPARSE**

Meaning:

References to useful realizations/forms of the Capability.

Possible typed refs:

```text
knowledge
skill / recipe
workflow / composition
implementation / service
evaluation pattern
```

Rules:

- only list forms that actually exist;
- reference source location + exact revision where practical;
- do not copy full asset metadata;
- no requirement that every Capability have every asset form.

Reason:

Capability != Skill/Agent/Workflow; discovery must expose available forms without privileging one.

---

## 2.5 `evidence_refs[]`

Disposition: **KEEP — REQUIRED WHEN EVIDENCE EXISTS; EMPTY ALLOWED**

Meaning:

References to authoritative evaluation, reconstruction, regression, live-use or other governed evidence.

Rules:

- reference, do not summarize mutable score/status;
- exact commit/digest where useful;
- absence of evidence is not automatically failure; it means unproven or not yet evaluated depending on the authority.

Reason:

Reuse/replacement decisions must be able to reach evidence quickly.

---

## 2.6 `lineage_refs[]`

Disposition: **OPTIONAL**

Meaning:

References that explain provenance when provenance materially affects trust/reconstruction/replacement.

Examples:

```text
learned_from
reconstructed_from
adapted_from
source repository + pinned commit
builder/construction decision
```

Rules:

- do not create a full provenance graph;
- exact source refs are enough for V0.1;
- omit when there is no meaningful lineage beyond the authority ref.

Reason:

Useful for harvested/external/reconstructed capabilities, unnecessary for every trivial local capability.

---

## 2.7 `realization_refs[]` / `binding_refs[]`

Disposition: **OPTIONAL**

Meaning:

Where the currently known implementation/binding that realizes the Capability can be found.

Rules:

- reference Adapter/Binding/implementation artifact;
- do not duplicate schemas or execution details;
- may be multiple;
- omit for knowledge-only/provisional harvested capability.

Reason:

Needed for replacement and execution discovery, but not universal.

---

## 2.8 `known_limits_ref`

Disposition: **OPTIONAL REF ONLY**

Meaning:

Reference to authoritative current limits/unproven boundary evidence.

Rules:

- never copy a list of mutable limits into the index when an evaluation/asset record already owns it;
- if several evidence artifacts exist, point to the current accepted synthesis/review artifact rather than every raw result.

Reason:

Known limits change faster than semantic identity.

---

## 2.9 `status` / `health` / `score`

Disposition: **DROP**

Reason:

Would create a second mutable truth competing with Evaluation / runtime evidence.

No V0.1 health state machine is justified.

If humans later need a quick status summary, first prove that following `evidence_refs` is materially insufficient.

---

## 2.10 `responsibility_boundary`

Disposition: **DERIVE / REF, NOT COPY BY DEFAULT**

Reason:

For Platform-admitted Capability, semantic responsibility belongs to the authoritative Capability definition/specification.
For harvested assets, it belongs to the asset record.

The index only needs enough summary for discovery; full responsibility text should remain at authority.

---

## 2.11 `input_schema` / `output_schema` / `execution`

Disposition: **DROP FROM INDEX**

Authority already exists in `CapabilityDescriptor` or the relevant implementation/asset contract.

---

## 2.12 `dependencies[]`

Disposition: **DROP FROM V0.1 INDEX**

Reason:

A dependency graph is not currently required for rediscovery.
Implementation dependencies belong with implementation/asset records.

Future trigger:

Repeated replacement/impact analysis cannot be performed from referenced implementation/binding artifacts.

---

## 2.13 `owner` / `team` / `department`

Disposition: **DROP / PARK**

Reason:

This is Enterprise semantics and no accepted generic ownership model currently exists.
Do not import Backstage organizational metadata into Platform-neutral Capability identity.

---

## 2.14 `domain` / `enterprise`

Disposition: **OPTIONAL BINDING REF ONLY**

Rules:

- include only when an accepted Domain/Enterprise binding artifact exists and materially scopes reuse;
- do not embed professional ontology or organization policy into the generic index.

---

## 2.15 `created_at` / `updated_at`

Disposition: **DROP BY DEFAULT**

Reason:

Git already provides change history. Do not duplicate repository metadata unless a later non-Git storage mechanism requires it.

---

## 2.16 `confidence`

Disposition: **DROP FROM GENERIC INDEX**

Reason:

Confidence is evidence-type specific and can be misleading when compressed into one number/label.
Case-local asset records may keep their own confidence semantics.

---

# 3. Resulting minimum Index entry

After minimization, a V0.1 conceptual entry needs only:

```text
capability_ref
summary
authority_ref
asset_refs[]
evidence_refs[]

optional:
  lineage_refs[]
  realization_or_binding_refs[]
  known_limits_ref
  domain_or_enterprise_binding_refs[]
```

Nothing else is currently justified.

Important:

> The index entry is intentionally incomplete. Its value is navigability, not self-containment.

---

# 4. Construction Decision — field-by-field decision

The current Skill already has:

```text
INPUT_KIND
REQUIRED_OUTCOME
TASK_CHARACTERIZATION
SELECTED_PATTERN
WHY_THIS_PATTERN
CURRENT_MECHANISM_CANDIDATE
REUSED_ASSETS
EXTERNAL_REFERENCES_IF_USED
ASSUMPTIONS
MATERIAL_RISKS
EVIDENCE_NEEDED_TO_PROVE_SUCCESS
EXPLICITLY_NOT_NEEDED_NOW
STOP_CONDITION
```

Do not replace this object. Repair it minimally.

---

## 4.1 `INPUT_KIND`

Disposition: **KEEP**

Useful procedural context; not architectural identity.

---

## 4.2 `REQUIRED_OUTCOME`

Disposition: **KEEP, RENAME/CLARIFY TO `PURPOSE_OR_REQUIRED_OUTCOME` IF NEEDED**

Must capture user/business outcome rather than implementation request alone.

Example:

```text
"answer professional regulation questions with traceable evidence"
```

not merely:

```text
"build an Agent"
```

---

## 4.3 `RESPONSIBILITIES`

Disposition: **ADD — REQUIRED**

Reason:

This is the central missing shared meaning between Construction and Evaluation.

Rules:

- describe observable responsibilities, not code modules;
- bounded enough to derive evidence needs;
- do not create separate Responsibility IDs unless an existing accepted identity already exists or repeated evidence later requires one.

---

## 4.4 `CAPABILITY_REFS` / `CAPABILITY_NEEDS`

Disposition: **ADD — REQUIRED**

Use two notions in one compact section:

```text
reused_capability_refs[]
missing_or_required_capability_needs[]
```

Rules:

- use references for existing capabilities;
- use plain provisional need labels/descriptions for genuinely missing capability;
- do not mint Platform Capability IDs before admission/definition authority exists.

Reason:

This is what makes Capability Search operational rather than rhetorical.

---

## 4.5 `TASK_CHARACTERIZATION`

Disposition: **KEEP, BUT DO NOT DUPLICATE RAW QUESTIONNAIRE**

Only persist dimensions that materially affected the decision:

```text
path predictability
knowledge boundary
action boundary
state horizon
decomposition/evidence/risk where material
```

Do not require every dimension to be populated for every task.

---

## 4.6 `MATERIAL_UNCERTAINTIES`

Disposition: **ADD — REQUIRED WHEN PRESENT; EMPTY ALLOWED**

Reason:

Supports targeted clarification and makes assumptions auditable.

If an uncertainty would materially change responsibility/risk/evidence/solution form, it must be explicit before construction.

---

## 4.7 `ASSUMPTIONS`

Disposition: **KEEP, BUT ONLY RESIDUAL NON-MATERIAL ASSUMPTIONS**

Material uncertainty must not be hidden in assumptions.

---

## 4.8 `SELECTED_SOLUTION_FORM`

Disposition: **ADD — REQUIRED**

Allowed vocabulary remains descriptive, not ontology:

```text
Skill
Workflow
Agent
Service
Deterministic implementation
Composition
Other
```

Reason:

Prevents the selected pattern/mechanism from silently assuming Agent-first construction.

---

## 4.9 `SELECTED_PATTERN`

Disposition: **KEEP — OPTIONAL IF NO PATTERN NEEDED**

Pattern is procedural reference, not governed identity.

For trivial deterministic reuse, it may be `NONE / NOT_NEEDED`.

---

## 4.10 `WHY_THIS_PATTERN`

Disposition: **KEEP, MERGE LOGICALLY WITH `WHY_THIS_SOLUTION`**

Preferred output should explain the choice of solution form + pattern + mechanism together, not generate three repetitive essays.

A compact rationale is enough.

---

## 4.11 `CURRENT_MECHANISM_CANDIDATE`

Disposition: **KEEP, RENAME TO `MECHANISM_OR_IMPLEMENTATION_CANDIDATE`**

Must remain replaceable and non-authoritative.

---

## 4.12 `REUSED_ASSETS`

Disposition: **KEEP, TIGHTEN TO RESOLVABLE REFS**

Prefer:

```text
Capability index ref
Skill path/ref
implementation/binding ref
knowledge/evidence ref
```

Do not paste copied content.

---

## 4.13 `EXTERNAL_REFERENCES_IF_USED`

Disposition: **KEEP — OPTIONAL**

Must preserve provenance/source revision where practical.

Do not turn external reference into Catalyst authority.

---

## 4.14 `DOMAIN / ENTERPRISE CONTEXT`

Disposition: **ADD — OPTIONAL, ONLY WHEN MATERIAL**

Reason:

Professional/organizational meaning may change responsibility or acceptance.

Rules:

- use binding/reference when accepted artifacts exist;
- plain scoped context is acceptable for a Case decision;
- do not make these mandatory generic fields.

---

## 4.15 `RUNTIME_EXECUTION_REQUIREMENTS`

Disposition: **ADD — OPTIONAL BUT REQUIRED WHEN EXECUTION NEEDS ARE MATERIAL**

Examples:

```text
durable session
external side effects
cancel/timeout
reconciliation
resumability
provider/tool requirements
```

Rules:

- requirement only; Harness does not own Runtime implementation;
- if no special Runtime obligation exists, say `CURRENT_RUNTIME_BASELINE_SUFFICIENT` or omit according to final format.

---

## 4.16 `EVIDENCE_NEEDED_TO_PROVE_SUCCESS`

Disposition: **KEEP, RENAME/CLARIFY TO `EVIDENCE_REQUIREMENTS`**

This is the main Construction → Evaluation handoff.

Must describe what observable evidence is required, not how the evaluator must implement its benchmark.

Examples:

```text
source/citation fidelity
world-state verification
restart persistence
fail-closed behavior
trajectory/tool-boundary evidence
human professional acceptance
```

Private rubric/oracle remains Evaluation-owned.

---

## 4.17 `MATERIAL_RISKS`

Disposition: **KEEP**

Only risks that change approval/evidence/solution design.

---

## 4.18 `EXPLICITLY_NOT_NEEDED_NOW`

Disposition: **KEEP / RENAME `NOT_REQUIRED_NOW`**

Important anti-expansion field.

---

## 4.19 `LINEAGE / SOURCE REFS`

Disposition: **ADD — OPTIONAL**

Useful when adapting/reconstructing from external or prior Catalyst assets.

Do not duplicate provenance already captured by `REUSED_ASSETS` / `EXTERNAL_REFERENCES`; the final shape may merge all source/provenance refs into one compact section.

---

## 4.20 `STOP_CONDITION`

Disposition: **KEEP — REQUIRED**

Essential Catalyst governance behavior.

---

# 5. Resulting minimum Construction Decision

The target is NOT a huge manifest.

A minimized decision can be grouped into seven sections:

```text
1. NEED
   input_kind
   purpose_or_required_outcome

2. RESPONSIBILITY
   responsibilities[]
   material_uncertainties[]
   material task characteristics only

3. CAPABILITY SEARCH
   reused_capability_refs[]
   missing_capability_needs[]
   reused_asset/source refs[]

4. SOLUTION
   selected_solution_form
   selected_pattern if useful
   mechanism_or_implementation_candidate
   short rationale

5. BOUNDARIES
   domain/enterprise context if material
   runtime_execution_requirements if material
   material_risks

6. PROOF
   evidence_requirements[]
   not_required_now[]

7. GOVERNANCE
   stop_condition
```

This remains procedural output of a replaceable Harness method.
It is NOT Platform Standard.

---

# 6. Fields explicitly rejected from Construction Decision

Do NOT add:

```text
Capability public input/output schemas
full implementation dependency graph
runtime trace/event schema
evaluation scores/results
Harvest verdict
mutable health
admission decision
Enterprise ownership model
universal responsibility IDs
pattern IDs as ontology
mechanism registry IDs
```

Those belong elsewhere or are not justified.

---

# 7. Minimal cross-surface linkage

The complete V0.1 linkage can remain reference-based:

```text
Capability Visibility Index
  capability_ref
      │
      ├── authority_ref ──→ CapabilityDescriptor / harvested asset record
      ├── asset_refs ─────→ Skill / Workflow / Implementation / Knowledge
      └── evidence_refs ──→ Evaluation / reconstruction / regression evidence

Construction Decision
  reused_capability_refs ───────────────┘
  evidence_requirements ──→ Evaluation formation

Runtime / Evaluation evidence
  capability identity / binding identity where applicable
      ↓
authoritative evidence artifact
      ↓
Index only needs evidence_ref updated
```

No service-to-service protocol is required for the first proof.

---

# 8. Expected persistent net-new data after minimization

If implementation is later authorized, the likely persistent net-new surface is now only:

```text
A. one thin Capability Visibility Index file
   containing reference-oriented entries

B. a repaired existing agent-construction Skill
   with a minimized Construction Decision template

C. one proof artifact/test demonstrating reference/evidence continuity
```

No new universal Handoff object is required.
No CapabilityDescriptor expansion is required.
No Runtime schema expansion is currently required.
No Evaluation schema/platform service is currently required.

---

# 9. Falsification checks before Phase II authorization

Before implementation, verify these claims against at least three existing assets:

```text
1. A Platform-admitted Capability can be discovered without duplicating its Descriptor.

2. A Case02 harvested Capability/asset can be discovered without promoting it into Platform Core.

3. A Case01 evaluation/Harvest artifact can be reached through evidence refs without copying its mutable status into the Index.

4. The repaired Construction Decision can reference existing capabilities and state missing capability needs without minting premature Capability IDs.

5. Evaluation can derive evidence targets from the Decision without requiring a new shared Platform schema.
```

If any claim fails, repair the minimum reference model first.
Do not respond by adding a service/DB/graph/engine.

---

# 10. Current verdict

```text
Capability Visibility Index
→ JUSTIFIED AS A TINY REFERENCE INDEX CANDIDATE
→ FIELD SURFACE MINIMIZED
→ IMPLEMENTATION STILL NOT AUTHORIZED

Construction Decision repair
→ JUSTIFIED AS ADAPTATION OF EXISTING SKILL
→ FIELD SURFACE MINIMIZED
→ IMPLEMENTATION STILL NOT AUTHORIZED

Standalone Responsibility/Evidence object
→ REJECTED

CapabilityDescriptor expansion
→ REJECTED

Capability health/status object
→ REJECTED FOR V0.1

Dependency graph / ownership model
→ REJECTED/PARKED
```

The next review should not invent more fields. It should run the falsification checks above against real existing assets, and only then decide whether Phase II receives a minimum implementation authorization.
