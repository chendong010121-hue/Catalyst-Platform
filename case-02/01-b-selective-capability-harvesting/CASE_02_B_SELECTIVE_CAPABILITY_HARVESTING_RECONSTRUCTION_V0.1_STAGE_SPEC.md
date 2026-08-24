# CASE 02-B — Selective Capability Harvesting & Catalyst-Native Reconstruction
## Stage Spec V0.1

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
later reconstruct an independent capability from the stored asset
```

The reason for decomposition is therefore NOT limited to repair.

Catalyst may decompose a healthy, mature, complete Agent for **selective capability harvesting** even when the source Agent itself does not need to be broken apart, rewritten, wrapped, or replaced.

This Stage tests whether the stored asset knowledge is sufficient to reconstruct one useful capability without returning to Waku source code.

## 2. Core Principle

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
RECONSTRUCTED CAPABILITY
!=
PLATFORM CORE
```

Waku remains a complete external Agent. Catalyst is testing whether one learned mechanism can become an independent Case-local capability.

## 3. Platform Capability Under Test

### PCAP-02-06 — Selective Capability Harvesting

Can Catalyst intentionally decompose a complete Agent for the purpose of extracting only selected high-value mechanisms while preserving the source Agent intact?

### PCAP-02-07 — Knowledge-Asset-to-Capability Reconstruction

Can Catalyst reconstruct a useful, independently runnable capability from a frozen governed asset record without rescanning or copying the original Agent implementation?

This Stage does not yet prove universal component composition or a generic asset runtime.

## 4. Frozen Knowledge Input

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

## 5. Reconstruction Target

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

The reconstructed capability must own only:

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
- Waku provider/message wire format.

## 6. Catalyst-Native Reconstruction Requirement

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

A deterministic scripted/fake decision provider is preferred for this Stage so the mechanism can be proven independently of provider availability.

The design must preserve the asset's meaningful contract:

```text
retrieve / skip
query
reason
bounded decision path
observable decision
fail-open retrieval fallback on decision-provider failure
```

## 7. Minimum Behavior Proof

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

Verify the reconstructed gate does not write durable memory and does not own ranking, prompt assembly, or Agent-loop behavior.

### R-05 Provenance / Lineage

Result evidence must identify:

```text
source_asset_id = WAKU-A01
source_catalog_id = CASE_02_WAKU_ASSET_CATALOG_V0.1
source_agent = waku-agent
source_commit = 8328f567ab52d07921445cb40feed23cbc5ea2ad
reconstruction_type = CATALYST_NATIVE_CASE_LOCAL
```

This is knowledge lineage, not code provenance.

## 8. What This Stage May Prove

If successful, CASE 02-B may claim:

```text
SELECTIVE CAPABILITY HARVESTING
CASE-EVIDENCED

FROZEN KNOWLEDGE ASSET
→ CATALYST-NATIVE RECONSTRUCTION
CASE-EVIDENCED
```

It may also support the stronger lifecycle:

```text
External Agent
→ analytical decomposition
→ valuable knowledge asset
→ later rediscovery
→ independent reconstruction
```

## 9. What This Stage MUST NOT Claim

Do not claim:

```text
all assets are reconstructable
all Waku capabilities are portable
Catalyst has a universal asset runtime
Catalyst can dynamically invoke arbitrary stored assets
WAKU-A01 belongs in Platform Core
Waku architecture should become Catalyst architecture
source code is unnecessary for all future maintenance
```

One asset proves one bounded reconstruction path.

## 10. Protected Boundaries

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

No Adapter and no Waku registration are authorized.

## 11. Minimal Persistent Outputs

Only persist:

```text
case-02/01-b-selective-capability-harvesting/
  reconstruction/
    retrieval_gate/**
  CASE_02_B_RESULTS.json
  CASE_02_B_REVIEW.md
```

Do not create a generic registry, framework, plugin system, asset service, or duplicate summaries.

## 12. Acceptance Criteria

PASS only if:

- reconstruction uses the frozen Catalog asset as its only Waku-derived knowledge input;
- Waku source is not reread;
- source Agent remains intact/unmodified;
- the implementation is Catalyst-native and Case-local;
- R-01 through R-05 pass;
- reconstructed behavior matches the asset responsibility boundary;
- Waku-specific personal-assistant assumptions are absent from the implementation;
- no Platform/Runtime/main/case-01 changes occur;
- no generic platform capability is promoted merely from this proof.

## 13. STOP Conditions

STOP if reconstruction requires:

- rereading Waku source;
- copying Waku implementation;
- modifying the frozen Catalog;
- adding a generic Catalyst Memory standard;
- changing Platform Core/Runtime;
- introducing a live LLM solely to make the proof pass;
- expanding into a second asset before external review.

## 14. Exit Boundary

```text
SELECT WAKU-A01
→ RECONSTRUCT FROM ASSET RECORD ONLY
→ RUN MINIMUM BEHAVIOR PROOF
→ RECORD LINEAGE
→ FREEZE RESULT
→ STOP
→ EXTERNAL REVIEW
```

A successful Case 02-B does not authorize whole-Waku integration or reconstruction of additional assets.
