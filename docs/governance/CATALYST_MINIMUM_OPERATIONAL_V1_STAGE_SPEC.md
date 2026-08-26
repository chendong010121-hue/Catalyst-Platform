# Catalyst Minimum Operational V1 — Stage Spec

> **Stage:** Post-Phase-2 minimum operationalization  
> **Base:** `main@1e9c4554747a4959f78fbde1399151554f088ec2`  
> **Status:** IMPLEMENTATION AUTHORIZED — STRICTLY BOUNDED  
> **Target:** `CATALYST MINIMUM OPERATIONAL V1`  
> **Primary principle:** **Build only until Catalyst can remember, rediscover, assimilate, and reuse capability value once. Then STOP and enter real use.**

---

## 1. Why this stage exists

Phase 1 proved the minimum architecture. Phase 2 proved that a real professional Capability can operate under Catalyst governance without contaminating Runtime/Core.

The remaining pre-use gap is not lack of more execution features. Existing Asset Census already identified the smallest integration gap as:

```text
Organizational Capability Visibility
+
Shared Evidence Handoff
```

Catalyst already has Runtime, Platform Standard, Harness evidence, Evaluation patterns, Capability identity, Domain/Enterprise boundaries, Harvest evidence, and replacement/evolution evidence. The problem is that capability value is still fragmented and difficult to rediscover from a later need.

This stage exists only to make that accumulated value operationally reusable.

---

## 2. Hard end boundary

This stage MUST END when Catalyst can demonstrate this one closed loop:

```text
REAL NEED
↓
CAPABILITY SEARCH
↓
EXISTING CAPABILITY / METHOD VALUE FOUND
↓
AUTHORITATIVE REFERENCES + EVIDENCE + KNOWN LIMITS RECOVERED
↓
REUSE / ADAPT / ASSIMILATE WITHOUT RE-DERIVING FROM SOURCE IMPLEMENTATION
↓
EXECUTE / EVALUATE
↓
HARVEST UPDATED EVIDENCE / LINEAGE
↓
THE SAME CAPABILITY VALUE IS REDISCOVERABLE AGAIN
```

Once this loop passes one real-use proof:

```text
CATALYST MINIMUM OPERATIONAL V1
= READY FOR CONTROLLED REAL USE
```

Then:

```text
STOP PLATFORM BUILDING
↓
START REAL OPERATIONAL USE
↓
ONLY REAL FAILURES / FRICTION MAY AUTHORIZE NEW WORK
```

There is no automatic next feature phase.

---

## 3. What “ready for use” means

`MINIMUM OPERATIONAL V1` means ready for **controlled real project/team use with human review**.

It does NOT mean:

```text
production enterprise platform
24/7 SLA
full organization control plane
universal workflow engine
enterprise authorization system
complete observability platform
complete memory platform
marketplace / plugin ecosystem
```

The operational baseline is sufficient when a real user can use Catalyst to avoid losing or unnecessarily rebuilding already-proven capability value.

---

## 4. Only four required primitives

The stage may establish only these four minimum responsibilities.

### P1 — Capability Visibility

Answer:

```text
What capability / method value already exists?
What responsibility does it serve?
Where is its authority?
What evidence supports it?
What are its known limits?
What lineage / implementations are known?
```

Preferred form: repository-native references / index entries.

NOT authorized: production Registry service, capability database, graph database, new source-of-truth store.

### P2 — Shared Evidence Handoff

Construction / Runtime / Evaluation / Harvest must be able to refer to the same capability identity and evidence references without centralizing evidence bytes.

Preferred form: thin reference records and stable IDs/SHAs.

NOT authorized: Evidence Service, artifact database, universal trace warehouse.

### P3 — Capability Assimilation

Catalyst may learn from an external system without making that system the owner of Catalyst identity.

Default flow:

```text
EXTERNAL SYSTEM
↓
OBSERVE
↓
DECOMPOSE
↓
REMOVE PRODUCT / API / CLASS-SPECIFIC DETAILS
↓
IDENTIFY STABLE RESPONSIBILITY
↓
EXTRACT OBLIGATIONS / METHOD
↓
RECORD EVIDENCE + LINEAGE
↓
CATALYST-OWNED CAPABILITY / METHOD CANDIDATE
```

Pi is the first approved research source.

Initial Pi harvest is limited to three research topics:

1. Comparative Evaluation / candidate comparison.
2. Durable external effect / recovery obligations.
3. Observation vs Intervention in extension seams.

Pi must remain a **knowledge/evidence source**, not a mandatory runtime dependency.

NOT authorized: Pi adapter, Pi migration, Pi-as-primary-Harness, copying Pi architecture wholesale.

### P4 — Real Rediscovery / Reuse Proof

At least one later real need must rediscover existing Catalyst capability/method value and reuse or adapt it without rereading/reconstructing the original source implementation from scratch.

This is the decisive acceptance proof.

---

## 5. Pi-inspired minimalism constraints

Pi is used here as engineering evidence for maintaining a small powerful surface, not as a product template.

Catalyst adopts these constraints for this stage:

### 5.1 Few strong primitives over many features

Do not add a new platform object when references and an existing responsibility can solve the problem.

### 5.2 Extension before Core promotion

A repeated real need must be observed before any new shared Core/Standard concept is promoted.

### 5.3 Observation is not control

If an integration only needs facts, use passive evidence/event references. Do not grant intervention authority merely for visibility.

### 5.4 Portable value over implementation state

Preserve capability responsibility, evidence, method, known limits, benchmark, and lineage in provider/framework-neutral forms when practical.

### 5.5 External systems contribute HOW / evidence, not Catalyst identity

No external Harness, model, Agent, or framework may become necessary for Catalyst to know what a capability is, why it is trusted, or how it evolved.

---

## 6. Required minimum deliverables

Only these deliverables are authorized:

### D1 — Capability Visibility Index V0.2

Extend the existing repository-native visibility index rather than creating a Registry.

Minimum fields are references, not duplicated authority:

```text
summary
capability / method reference where applicable
responsibility reference
authority reference
asset references
evidence references
known-limits reference
lineage references
current implementation references when useful
status / evidence level
```

Do not force all entries into one universal schema if the underlying asset types differ.

### D2 — Shared Evidence Handoff V0.1

A thin documented convention showing how Construction / Evaluation / Harvest refer to the same capability responsibility and evidence identity.

Prefer existing ArtifactRef / Trace / exact SHA / file-reference semantics.

### D3 — External Capability Assimilation Method V0.1

A replaceable Harness-side / research method, not Platform Core authority.

It must support Pi as the first evidence source while remaining source-neutral.

### D4 — One Real Rediscovery / Reuse Campaign

A real later need must:

```text
search existing Catalyst capability value
→ recover an existing capability / method
→ reuse or adapt it
→ evaluate against a bounded real requirement
→ preserve evidence / lineage
```

No synthetic “lookup succeeds” test alone can close the stage.

---

## 7. Acceptance gates

All must pass.

### G1 — Rediscoverability

A user/Harness can locate relevant existing capability/method value without knowing the original Case/branch history.

### G2 — Authority integrity

The visibility layer points to authoritative assets; it does not become a new source of truth.

### G3 — Evidence integrity

Evidence remains inspectable and attributable. No unsupported confidence/health claim is invented by the index.

### G4 — External assimilation independence

At least one Pi-derived method/obligation candidate is preserved in Catalyst-owned language and remains meaningful if Pi disappears.

### G5 — Reuse proof

A real task demonstrably reuses or adapts existing capability value and avoids unnecessary rebuild/research.

### G6 — Core integrity

No new Domain/Enterprise/external-product semantics enter Runtime/Core merely to support visibility or assimilation.

### G7 — Minimality

The accepted solution contains no production Registry, graph DB, background monitoring, universal Workflow, Authority/Policy system, Context/Memory platform, Pi dependency, or other unproven infrastructure.

---

## 8. Explicit non-goals / parked work

The following remain PARK / WATCH and are NOT required before controlled real use:

```text
second Runtime / Runtime replacement
Pi integration / Pi migration
Semantic Context platform
Compaction engine
Session tree / lanes
production Capability Registry
background health monitoring
Workflow / Orchestration platform
Domain SDK / Framework
Enterprise Framework
Role / Authority / Policy / Approval
Control Plane
full output enforcement framework
universal side-effect attestation
provider marketplace
UI / marketplace / package ecosystem
```

If one becomes a real blocker during operational use, it must return through evidence-driven Stage authorization.

---

## 9. Operational release boundary

The platform becomes formally eligible for controlled real use when:

```text
Phase 1 Architecture                         PASS
Phase 2 Governed Capability Adoption        PASS
Capability Visibility                       PASS
Shared Evidence Handoff                     PASS
External Capability Assimilation            PASS at one source / bounded scope
Real Capability Rediscovery + Reuse          PASS
Core / Runtime boundary integrity            PASS
Minimality audit                             PASS
```

Then record:

```text
CATALYST MINIMUM OPERATIONAL V1
READY FOR CONTROLLED REAL USE
```

After that declaration, planned platform expansion STOPS.

---

## 10. Post-release development rule

After Minimum Operational V1:

```text
REAL USE
↓
OBSERVED FRICTION / FAILURE / MISSED VALUE
↓
ATTRIBUTE RESPONSIBILITY
↓
SEARCH EXISTING CAPABILITY / EXTERNAL KNOWLEDGE
↓
GENERATE CANDIDATES
↓
COMPARE WITH FROZEN EVIDENCE / BENCHMARK
↓
ACCEPT / ROLLBACK
↓
HARVEST
```

No feature is added because another framework has it.

No roadmap item is implemented because it has been PARKED for a long time.

**Operational evidence becomes the roadmap.**

---

## 11. Final stage statement

> Catalyst will not attempt to become a feature-complete Harness before real use. This stage ends as soon as the platform can preserve, rediscover, assimilate, and reuse capability value through one real closed loop. At that point Catalyst enters controlled operational use, and further architecture work must be pulled by real evidence rather than pre-built speculation.
