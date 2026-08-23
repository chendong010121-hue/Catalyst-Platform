# CASE 01-E / E1 — PROFESSIONAL CHANGE REQUEST V0.1

> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)  
> **Change class:** Professional product capability completion  
> **Decision source:** User-approved CASE 01-E product-mainline direction  
> **Current admitted version:** `case-01.brea @ 0.1-candidate`  
> **Current admitted version mutation:** not part of this change request  
> **Execution authorization:** not represented by this document

## Natural-language product change request

> **让 BREA 能够对已经接入的本地建筑规范进行一般化查询，而不是只能回答预设测试题；回答必须继续提供原文证据、条款/表格定位和数值来源，找不到可靠证据时不能编造。**

## Product intent

The requested change advances BREA from a narrow formation-proof implementation toward a genuinely usable local Building Regulation evidence-query Agent.

The change is intended to make the already admitted local corpus behave as a reusable evidence source rather than as a set of hardcoded fixtures.

## Current observed limitation

BREA v0.1 currently proves professional behavior for a narrow deterministic slice:

```text
fire-distance question
→ GB 55037-2022
→ fixed Clause 3.1.3 path

parking / allocation question
→ DBJ33/T1021-2023
→ fixed Table 5.0.1 + Table 5.0.4 path

missing required facts
→ fail closed
```

The underlying corpus and evidence modules already contain reusable parsing / evidence-binding primitives, but the whole-Agent routing remains strongly tied to the initial formation cases.

## Desired E1 outcome

A later E1 implementation should be able to demonstrate, using only the currently admitted two local regulations, that BREA can:

```text
identify / resolve local regulation sources
look up evidence by explicit clause locator
look up evidence by explicit table locator where reliably parseable
perform deterministic local topic/evidence retrieval beyond the original fixtures
return verbatim evidence + locator + source identity
preserve numeric safety
preserve professional applicability boundaries
preserve insufficient-context / no-reliable-evidence behavior
```

The change should not depend on adding more regulations merely to increase apparent coverage.

## Scope intentionally excluded from this request

This product change does not itself request:

```text
Web fallback
official-site Web verification
URL supplementation
RAG
LLM inference
Agent loop
Memory
multi-turn UX
frontend
backend product shell
new Platform Core semantics
Runtime redesign
Enterprise IAM / RBAC / policy engine
```

Those remain later evidence-driven product / architecture decisions.

## Versioning intent

The currently admitted / bound BREA v0.1 is an immutable evidence baseline.

The professional change is expected to produce a new Candidate version rather than mutate the admitted implementation in place.

Candidate version naming is to be frozen by the E1 Stage Spec.

## Governance interpretation

The change is expected to primarily affect the existing responsibilities:

```text
FN-01 Question & Context Intake
FN-03 Regulation Applicability Resolution
FN-04 Evidence Locating & Extraction
FN-05 Evidence Binding & Numeric Safety
FN-06 Uncertainty & Fail-Closed Decision
FN-07 Result Composition & Attribution
FN-08 Artifact & Provenance Preservation
FN-09 Corpus Access & Parsing

SEAM-02 Regulation Applicability
SEAM-03 Regulation Evidence
```

`SEAM-01 Professional Project Facts` may remain semantically stable unless real E1 evidence proves that additional professional facts are necessary.

The accepted professional purpose and OBL-01..OBL-06 are expected to remain sufficient unless an explicit Change Impact Review proves otherwise.

## Product success signal

The essential anti-fixture criterion is:

> **The new Candidate must answer / retrieve evidence for local regulation queries that were not individually encoded as dedicated runtime branches or original T-C01/T-C02/T-C03 fixtures.**

A larger collection of hardcoded question-specific branches is not considered completion of this request.
