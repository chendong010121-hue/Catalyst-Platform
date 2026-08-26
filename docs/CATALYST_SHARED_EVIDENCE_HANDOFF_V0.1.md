# Catalyst Shared Evidence Handoff V0.1

> **Status:** Minimum operational convention  
> **Authority:** Method-level coordination only; not Platform Standard  
> **Purpose:** Let Construction, Runtime, Evaluation, and Harvest refer to the same Capability responsibility and evidence state without centralizing evidence bytes or creating a Registry.

---

## 1. Core rule

> **Share references, identity, and attribution. Do not duplicate authority.**

The handoff exists so later work can answer:

```text
What responsibility is being served?
Which governed Capability / method value is relevant?
Where is the authority?
What evidence supports or limits it?
Which implementation / lineage is involved?
What changed after this run / evaluation / harvest?
```

The handoff is NOT a source of truth for the Capability, Evaluation, Runtime, Domain, Enterprise, or evidence payload.

---

## 2. Minimum reference shape

A handoff record may omit irrelevant fields. It SHOULD contain only what is needed to reconnect later work to authoritative assets.

```text
responsibility_summary
capability_ref?              # existing stable id/version only; do not mint one casually
method_ref?                  # repository + exact ref + path
asset_refs[]                 # implementation / knowledge / skill / workflow / other governed assets
evidence_refs[]              # repository refs, artifact refs, hashes, or local manifest identities
known_limits_refs[]
lineage_refs[]
implementation_refs[]
observed_failure_owner?      # when evidence supports attribution
stage_or_campaign_ref?
```

Rules:

- use exact Git SHA / immutable artifact identity where practical;
- local/private evidence may be represented by an immutable manifest hash rather than uploaded bytes;
- do not copy public schemas, professional evidence text, or Evaluation scores into the handoff unless the owning authority defines that as the portable artifact;
- absence of evidence is not PASS;
- the handoff does not infer current health.

---

## 3. Construction → Evaluation

Construction emits:

```text
responsibility_summary
reused_capability_or_method_refs[]
missing_or_unproven_needs[]
selected_solution_form / mechanism candidate
runtime_requirements_if_material[]
evidence_requirements[]
```

Evaluation receives references and required observable proof. It does not inherit Construction conclusions as truth.

---

## 4. Runtime → Evaluation / Harvest

Runtime emits execution facts through existing Result / Artifact / Trace surfaces where applicable.

The handoff may reference:

```text
execution / request identity
capability id/version attribution when available
result / artifact / trace references
failure / uncertainty facts
implementation identity when material
```

Runtime does not decide business/professional correctness and does not write Harvest conclusions.

---

## 5. Evaluation → Harvest

Evaluation emits:

```text
frozen target / candidate identity
benchmark / case identity
raw evidence references
accepted / failed obligations
failure attribution when supported
known limits / unproven boundaries
comparison result when a baseline exists
```

Harvest may then decide what organizational value should be preserved, replaced, promoted, or left local.

---

## 6. Harvest → Visibility

Harvest updates discoverability by adding or changing references in the repository-native Capability Visibility Index.

Visibility may expose:

```text
summary
responsibility
authority_ref
evidence_refs
known_limits_ref
lineage_refs
implementation refs
status / evidence level
```

Visibility MUST NOT become:

```text
Capability contract authority
Evaluation authority
Runtime authority
Domain / Enterprise authority
health monitor
production Registry
```

---

## 7. Failure handoff

When a failure is observed:

```text
failure evidence
↓
Capability / responsibility identified when possible
↓
owner classified only when supported
↓
evidence references attached
↓
known limitation becomes discoverable
```

Do not create a background monitoring system merely to satisfy this convention. Event-driven evidence from actual stages/runs is sufficient until real use proves otherwise.

---

## 8. Local / private evidence

Local evidence may remain outside the Catalyst repository.

Repository-safe linkage pattern:

```text
Catalyst authority / review SHA
+
local immutable manifest SHA256
+
optional individual artifact hashes
```

The manifest must be frozen at the relevant Stage Close or explicitly labeled as later recertification.

This convention does not authorize uploading professional, project, enterprise, credential, or private evidence bytes to GitHub.

---

## 9. Minimality guard

This document does not authorize:

```text
Evidence Service
Capability Registry service
central artifact database
graph DB
new universal asset schema
health daemon
workflow engine
new Platform Core object
```

If references become insufficient under real operational load, preserve the failure evidence and open a separate architecture decision.

---

## 10. Operational test

This convention is accepted only when a later real need can follow the handoff chain from a discoverable Capability/method entry to authority/evidence/known limits and reuse that value without reconstructing the original project history.
