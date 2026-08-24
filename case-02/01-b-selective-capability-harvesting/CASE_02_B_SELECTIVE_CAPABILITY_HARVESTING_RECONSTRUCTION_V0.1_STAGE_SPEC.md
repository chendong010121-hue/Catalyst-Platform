# CASE 02-B — Selective Capability Harvesting & Catalyst-Native Reconstruction
## Stage Spec V0.2

> Status: STAGE SPEC — READY FOR AUTHORIZATION
> Implementation Authorization: NO
> Case Branch: `case-02`
> Required Base: Case 02-A CLOSED with independent catalog rediscovery evidence
> Primary Input Asset: `WAKU-A01` from `CASE_02_WAKU_ASSET_CATALOG_V0.1.json`

## 1. Purpose

CASE 02-B tests a distinct Catalyst platform capability:

```text
A complete external Agent may remain intact and fully usable
        ↓
Catalyst may still analytically decompose it
        ↓
select one valuable capability/mechanism
        ↓
preserve that mechanism as a governed knowledge asset
        ↓
later reconstruct an independent mechanism from the stored asset
```

The reason for decomposition is therefore NOT limited to repair.

Catalyst may decompose a healthy, mature, complete Agent for **selective capability harvesting** even when the source Agent itself does not need to be broken apart, rewritten, wrapped, or replaced.

This Stage tests whether the stored asset knowledge is sufficient to reconstruct one useful mechanism without returning to Waku source code.

The reconstructed result in this Stage is intentionally **UNBOUND**: it is not yet a Domain capability, Enterprise capability, BREA capability, Platform capability, or admitted Agent component.

## 2. Core Principles

```text
SOURCE AGENT INTEGRITY
!=
CATALYST ANALYTICAL DECOMPOSITION
```

```text
DECOMPOSE FOR LEARNING / HARVESTING
!=
MODIFY OR DISASSEMBLE THE SOURCE SYSTEM
```

```text
HARVEST A CAPABILITY
!=
COPY SOURCE IMPLEMENTATION
```

```text
RECONSTRUCTED MECHANISM
!=
PLATFORM CORE
```

```text
CROSS-CASE REUSE
!=
CROSS-LAYER SEMANTIC TRANSFER
```

Waku remains a complete external Agent. Catalyst is testing whether one learned mechanism can become an independent Case-local reconstruction while preserving layer boundaries.

## 3. Platform Capabilities Under Test

### PCAP-02-06 — Selective Capability Harvesting

Can Catalyst intentionally decompose a complete Agent for the purpose of extracting selected high-value mechanisms while preserving the source Agent intact?

### PCAP-02-07 — Knowledge-Asset-to-Mechanism Reconstruction

Can Catalyst reconstruct a useful, independently runnable mechanism from a frozen governed asset record without rescanning or copying the original Agent implementation?

### PCAP-02-08 — Cross-Layer Contamination Control

Can Catalyst preserve a harvested mechanism as unbound/reusable knowledge without silently importing the source Agent's Domain, Enterprise, Agent, Runtime, or product assumptions into another Case?

This Stage does not prove universal component composition, a generic asset runtime, or direct cross-Case adoption.

## 4. Layer / Semantic Boundary

Catalyst architecture treats Domain and Enterprise as different semantic dimensions that compose with Agent/Workflow behavior; they are not interchangeable with generic implementation mechanisms.

For this Stage:

```text
WAKU-A01
= source-derived mechanism knowledge
= no inherited Domain authority
= no inherited Enterprise authority
= no automatic Agent ownership
= no automatic Runtime ownership
= no automatic Platform Core ownership
```

The absence of Enterprise semantics in Case 02-B is acceptable ONLY because this is an **unbound mechanism reconstruction proof**, not a real organizational deployment or Agent admission.

Enterprise semantics become mandatory when a target Case asks questions such as:

```text
who may use the mechanism?
which organization policy changes its behavior?
which data/privacy/risk rule applies?
which approval or authority is required?
which enterprise vocabulary or ownership applies?
```

Domain semantics become mandatory when a target Case asks questions such as:

```text
what professional meaning is being retrieved?
what counts as relevant evidence?
what domain fact/query vocabulary applies?
what professional failure semantics are required?
```

Neither Waku nor Case 02-B may answer those questions for Case 01.

## 5. Frozen Knowledge Input

The only Waku-derived knowledge allowed for reconstruction is:

```text
case-02/01-a-waku-understanding/CASE_02_WAKU_ASSET_CATALOG_V0.1.json
```

Selected asset:

```text
WAKU-A01
Retrieval-gated memory query selection
```

The asset record is treated as the design/evidence input.

The following are forbidden reconstruction inputs:

```text
ShenSeanChen/waku-agent repository
E:\试验场地\agent-lab\waku-agent
Waku README / docs / tests / source code
01_WAKU_UNDERSTANDING.md
02_WAKU_MECHANISM_DECONSTRUCTION.md
03_CASE_02_A_REVIEW.md
04_CASE_02_A_REDISCOVERY_EVIDENCE_REPAIR.md
```

The executor may read the Stage Spec, Authorization, frozen Asset Catalog, and the new Case 02-B implementation/tests only.

## 6. Reconstruction Target

Reconstruct the minimum responsibility expressed by `WAKU-A01`:

```text
current turn
   ↓
retrieval decision
   ├── SKIP
   └── RETRIEVE + query
              ↓
        memory-store search
```

The reconstructed mechanism must own only:

- pre-retrieval decision;
- explicit query handoff;
- decision reason;
- observable decision trace;
- governed failure fallback.

It MUST NOT own:

- long-term memory semantics;
- memory ranking quality;
- durable memory writes;
- prompt assembly;
- Agent loop;
- Waku persona;
- Waku state schema;
- Waku provider/message wire format;
- Domain relevance policy;
- Enterprise privacy/risk/approval policy;
- target-Agent admission semantics.

## 7. Catalyst-Native Reconstruction Requirement

The implementation must be newly written for Case 02-B from the asset record.

It must not copy or translate Waku source line-by-line.

The proof should use the smallest independent collaborators necessary, for example:

```text
RetrievalDecisionGate
Fake/Scripted decision provider
Tiny memory-store seam
In-memory fake store
Decision trace record
```

A live LLM is NOT required.

A deterministic scripted/fake decision provider is preferred so the mechanism can be proven independently of provider availability.

The design must preserve the asset's meaningful contract:

```text
retrieve / skip
query
reason
bounded decision path
observable decision
fail-open retrieval fallback on decision-provider failure
```

The implementation must be labelled:

```text
UNBOUND_CASE_LOCAL_MECHANISM
```

It must not be labelled as BREA, Domain, Enterprise, Platform Core, or admitted Agent functionality.

## 8. Minimum Behavior Proof

Use the minimum cases necessary to falsify the reconstruction claim.

### R-01 Relevant Turn

Decision provider returns `RETRIEVE` with a query.

Expected:

```text
store searched exactly once
provided query propagated
retrieved result returned
trace records RETRIEVE + query + reason
```

### R-02 Irrelevant Turn

Decision provider returns `SKIP`.

Expected:

```text
store not searched
no retrieved material returned
trace records SKIP + reason
```

### R-03 Decision Failure

Decision provider raises/fails.

Expected:

```text
fail-open
store searched using original turn text as fallback query
trace explicitly records fallback/failure state
```

### R-04 Boundary Test

Verify the reconstructed gate does not write durable memory and does not own ranking, prompt assembly, Agent-loop behavior, Domain semantics, or Enterprise semantics.

### R-05 Provenance / Lineage

Result evidence must identify:

```text
source_asset_id = WAKU-A01
source_catalog_id = CASE_02_WAKU_ASSET_CATALOG_V0.1
source_agent = waku-agent
source_commit = 8328f567ab52d07921445cb40feed23cbc5ea2ad
reconstruction_type = CATALYST_NATIVE_CASE_LOCAL
semantic_binding = UNBOUND
```

This is knowledge lineage, not code provenance or cross-Case admission.

### R-06 Semantic Non-Inheritance

Verify the reconstruction contains no Waku personal-assistant semantics and no Case 01 / building-regulation semantics.

Expected:

```text
Domain binding = NONE
Enterprise binding = NONE
Target Agent binding = NONE
```

## 9. Target-Case Composition Gate

A reconstructed mechanism MUST NOT move directly from Case 02 into Case 01 or any future Case.

Cross-Case reuse requires a separate target-Case decision:

```text
Target Case observes a real need
        ↓
Asset rediscovery
        ↓
Layer-owner classification
        ↓
Is the mechanism relevant at:
  implementation / Agent / Workflow / Domain / Enterprise / Adapter / Runtime level?
        ↓
Target Domain mapping
        ↓
Target Enterprise mapping (when organization-specific meaning exists)
        ↓
Target Agent contract / seam fit
        ↓
case-specific safety + evaluation proof
        ↓
explicit target-Case adoption authorization
        ↓
reuse / adapt / reconstruct / wrap / reject
```

No step may be skipped merely because the source asset is already recorded or reconstructed.

For Case 01 specifically, a Waku-derived mechanism may be considered only after BREA has an observed product need. Case 01 must independently determine:

```text
what professional responsibility the mechanism would serve
what Domain semantics constrain it
what Enterprise semantics constrain it
which BREA seam owns it
whether existing BREA contracts can express it
whether using the mechanism improves the product
```

Case 02 has no authority to answer those questions on behalf of Case 01.

## 10. Cross-Case Transfer Modes

Any later reuse must explicitly classify the transfer as one of:

```text
KNOWLEDGE_REFERENCE
  use the stored mechanism record as design knowledge only

CATALYST_NATIVE_RECONSTRUCTION
  reconstruct for the target Case under target contracts

IMPLEMENTATION_REUSE
  reuse an existing implementation only after compatibility + semantic binding proof

EXTERNAL_AGENT_INTEGRATION
  invoke the whole external Agent through an Adapter / governed seam

REJECT
  mechanism does not fit the target Case
```

Default is `KNOWLEDGE_REFERENCE`, not implementation transfer.

## 11. What This Stage May Prove

If successful, CASE 02-B may claim:

```text
SELECTIVE CAPABILITY HARVESTING
CASE-EVIDENCED

FROZEN KNOWLEDGE ASSET
→ UNBOUND CATALYST-NATIVE RECONSTRUCTION
CASE-EVIDENCED

CROSS-LAYER CONTAMINATION CONTROL
CASE-EVIDENCED WITHIN THIS PROOF
```

It may support:

```text
External Agent
→ analytical decomposition
→ valuable knowledge asset
→ later rediscovery
→ independent unbound reconstruction
```

## 12. What This Stage MUST NOT Claim

Do not claim:

```text
all assets are reconstructable
all Waku capabilities are portable
Catalyst has a universal asset runtime
Catalyst can dynamically invoke arbitrary stored assets
WAKU-A01 belongs in Platform Core
WAKU-A01 is already suitable for BREA
WAKU-A01 is Domain-neutral in every future context
WAKU-A01 is Enterprise-neutral in every future context
Waku architecture should become Catalyst architecture
source code is unnecessary for all future maintenance
```

One asset proves one bounded unbound reconstruction path.

## 13. Protected Boundaries

MUST remain unchanged:

```text
Waku source
frozen Case 02-A Asset Catalog
Case 02-A evidence files
Catalyst Platform Core
Catalyst Runtime
RuntimeAdapter
main
case-01
```

No Adapter, Waku registration, Case 01 adoption, Domain binding, Enterprise binding, or Agent admission is authorized.

## 14. Minimal Persistent Outputs

Only persist:

```text
case-02/01-b-selective-capability-harvesting/
  reconstruction/
    retrieval_gate/**
  CASE_02_B_RESULTS.json
  CASE_02_B_REVIEW.md
```

Do not create a generic registry, framework, plugin system, asset service, shared cross-Case component store, or duplicate summaries.

## 15. Acceptance Criteria

PASS only if:

- reconstruction uses the frozen Catalog asset as its only Waku-derived knowledge input;
- Waku source is not reread;
- source Agent remains intact/unmodified;
- implementation is Catalyst-native, Case-local, and explicitly UNBOUND;
- R-01 through R-06 pass;
- reconstructed behavior matches the asset responsibility boundary;
- Waku personal-assistant assumptions are absent;
- Case 01 / building-regulation semantics are absent;
- no Domain/Enterprise binding is silently invented;
- no Platform/Runtime/main/case-01 changes occur;
- no cross-Case adoption occurs;
- no generic platform capability is promoted merely from this proof.

## 16. STOP Conditions

STOP if reconstruction requires:

- rereading Waku source;
- copying Waku implementation;
- modifying the frozen Catalog;
- importing Case 01 Domain/Enterprise semantics;
- creating a shared implementation for Case 01 without a target-Case gate;
- adding a generic Catalyst Memory standard;
- changing Platform Core/Runtime;
- introducing a live LLM solely to make the proof pass;
- expanding into a second asset before external review.

## 17. Exit Boundary

```text
SELECT WAKU-A01
→ RECONSTRUCT FROM ASSET RECORD ONLY
→ KEEP SEMANTIC BINDING = UNBOUND
→ RUN MINIMUM BEHAVIOR PROOF
→ RECORD LINEAGE
→ FREEZE RESULT
→ STOP
→ EXTERNAL REVIEW
```

A successful Case 02-B does not authorize whole-Waku integration, reconstruction of additional assets, or adoption by Case 01.
