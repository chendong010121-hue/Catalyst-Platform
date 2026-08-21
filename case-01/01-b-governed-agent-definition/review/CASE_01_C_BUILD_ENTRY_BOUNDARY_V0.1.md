# CASE 01-C — BUILD ENTRY BOUNDARY V0.1

> This is the accepted successor build boundary from CASE 01-B. It contains no implementation authorization by itself.

## Build target

```text
Building Regulation Evidence Agent (BREA)
project professional facts
→ applicability
→ verbatim regulation evidence
→ evidence-backed conclusion
→ explicit uncertainty / fail closed
```

## Accepted professional purpose

Use project context to provide reliable, applicable, traceable building-regulation evidence for architectural / preliminary design work, and explicitly return uncertainty or fail closed when reliable evidence is unavailable.

## Initial build obligations

```text
OBL-01 Verbatim evidence traceability
OBL-02 Applicability determination
OBL-03 Numeric safety — zero unsupported numeric claims
OBL-04 Fail-closed uncertainty
OBL-05 Source fidelity / provenance
OBL-06 Minimum attribution
```

## Required functional decomposition

CASE 01-C must implement FN-01..FN-11 as explicit function/responsibility boundaries. It must not collapse the whole Agent into one Prompt, one RAG pipeline, one class, or one module.

Governed seams:

```text
SEAM-01 Professional Project Facts
SEAM-02 Regulation Applicability
SEAM-03 Regulation Evidence
```

Private implementation remains free for retrieval, chunking, ranking, provider, prompt wording, internal data structures, cache, database, module layout, internal orchestration, service shape, and corpus parser, unless later evidence promotes a boundary.

## Selected legacy adaptation inputs

```text
A-02
A-04
A-11
A-12
A-13a
```

No direct Legacy Agent architecture inheritance.

## Corpus

Read `../evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md`. Raw corpus remains local, READ ONLY, organizational asset=NO, upstream=FORBIDDEN.

## CASE 01-C co-evolution intent

```text
TRACK A — CASE
Build the first BREA Candidate.

TRACK B — CATALYST
Build only the minimum local Builder / formation capability needed by Track A.
```

Immediate formation gaps:

```text
GAP-01 Builder-consumable definition
GAP-05 minimum local Builder capability
```

Penguin Harness may be used as a reference for Builder engineering patterns; it does not define Catalyst governance semantics.

## Formation evidence required

```text
identity/version evidence
obligation conformance evidence
legacy adaptation trace
Domain / Enterprise separation evidence
functional-boundary evidence
no Platform / Runtime contamination evidence
source/evidence traceability
fail-closed evidence
numeric-safety evidence
local Builder input→generated-output trace
```

A source-code literal scan may be used as local numeric-safety build verification, but it is not part of OBL-03 public semantics.

## Explicitly not part of CASE 01-C unless separately authorized

```text
Platform admission / binding
Capability assetization
N+1 evolution
Platform Core change
Runtime change
generic Builder Platform
full benchmark/evaluation platform
```

## STOP conditions

STOP if implementation requires changing accepted professional purpose, responsibility ownership, governed seams, corpus admission, selected legacy adaptation, Platform/Runtime boundary, or if it creates unsupported normative numeric authority.
