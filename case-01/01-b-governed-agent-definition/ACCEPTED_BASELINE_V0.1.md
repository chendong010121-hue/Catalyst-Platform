# CASE 01-B — ACCEPTED GOVERNED AGENT BASELINE V0.1

## Agent

```text
ID      BREA — Building Regulation Evidence Agent
STATE   DESIGN
OWNER   USER / CASE 01 PRODUCT-RELEASE AUTHORITY
DOMAIN  Building Regulation / Engineering Construction Standards — architecture_pre_design
```

## Professional purpose

Use project context to provide reliable, applicable, traceable building-regulation evidence for architectural / preliminary design work, and explicitly return uncertainty or fail closed when reliable evidence is unavailable.

The Agent purpose is independent of the Catalyst experiment objective.

## Initial obligations accepted for CASE 01-C build

```text
OBL-01  Verbatim evidence traceability
OBL-02  Applicability determination
OBL-03  Numeric safety — zero unsupported normative numeric claims
OBL-04  Fail-closed uncertainty
OBL-05  Source fidelity / provenance
OBL-06  Minimum enterprise attribution
```

OBL-03 is a professional obligation. Source-code literal scanning is only CASE 01-C formation/build verification, not public Agent semantics.

## Functional decomposition

```text
FN-01 Question & Context Intake                 DECLARED FUNCTION BOUNDARY
FN-02 Professional Fact Normalization           GOVERNED SEAM — SEAM-01
FN-03 Regulation Applicability Resolution       GOVERNED SEAM — SEAM-02
FN-04 Evidence Locating & Extraction            GOVERNED SEAM — SEAM-03
FN-05 Evidence Binding & Numeric Safety         GOVERNED SEAM — SEAM-03
FN-06 Uncertainty & Fail-Closed Decision        DECLARED FUNCTION BOUNDARY
FN-07 Result Composition & Attribution          DECLARED FUNCTION BOUNDARY
FN-08 Artifact & Provenance Preservation        GOVERNED SEAM — SEAM-03
FN-09 Corpus Access & Parsing                   PRIVATE IMPLEMENTATION
FN-10 Provider & Execution Plumbing             PRIVATE / DEFERRED
FN-11 Local Runner / Service Shell              PRIVATE / DEFERRED
```

Required invariant:

> Every meaningful Agent function has an explicit responsibility boundary that can be understood, composed, tested, and where justified replaced independently.

But:

```text
decomposable != Platformized
modular != separately governed
Skill != governed seam
governed seam != Platform Core
```

## Governance depth

```text
LEVEL 0 — Whole-Agent Governance
+
LEVEL 1 — Declared Governed Seams
```

Governed seams:

```text
SEAM-01 Professional Project Facts
SEAM-02 Regulation Applicability
SEAM-03 Regulation Evidence
```

## Responsibility ownership

```text
DOMAIN      professional fact vocabulary; applicability; evidence and numeric authority
ENTERPRISE  minimum organization/user/project attribution only
AGENT       task coordination; input/output behavior; fail-closed behavior; claim/evidence binding behavior
PRIVATE     retrieval; parsing; storage; provider; internal module layout; service shell
RUNTIME     execution lifecycle semantics
PLATFORM    only already accepted Platform Standard responsibilities
```

Prompt / AGENTS.md is a projection of governed definition, not the source of Domain / Enterprise / public-obligation meaning.

## Legacy adaptation boundary

Selected for CASE 01-C adaptation:

```text
A-02 domain model concepts
A-04 facts lifecycle semantics
A-11 migration-governance manifest pattern
A-12 test patterns
A-13a environment/dependency descriptors
```

Deferred:

```text
A-01 documents/**
A-03 storage schema patterns
A-05 provider boundary pattern
```

A-15 corpus is `LOCAL PILOT ADMITTED INPUT`, not an organizational asset. A-16 and A-19 remain unavailable by default.

## Builder direction

```text
ONE SENTENCE USER NEED
→ CATALYST GOVERNED INTERPRETATION
→ GOVERNED AGENT DEFINITION
→ BUILDER-CONSUMABLE DEFINITION
→ BUILDER AGENT
→ DECOMPOSABLE AGENT CANDIDATE
→ EVIDENCE
→ ACCEPT / REJECT
```

Penguin Harness is a reference pattern source for Builder/Target, agent creation, evaluation, Trace, Snapshot, Candidate N+1 and rollback. Its ontology, Runtime, folder layout, Skill semantics, and score-based acceptance do not become Catalyst authority.
