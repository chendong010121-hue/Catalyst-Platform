# CASE 01-E / E1 — CHANGE IMPACT REVIEW — V0.1

> Governed Change Impact Review per Stage Spec §6, performed BEFORE v0.2 generation.
> Inputs: `E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md`, accepted 01-B definition (SHA
> `6c6e4707…`), admitted v0.1 Candidate (read-only), admitted corpus (read-only).

## 0. Change request (fixed, §1)

> 让 BREA 能够对已经接入的本地建筑规范进行一般化查询，而不是只能回答预设测试题；
> 回答必须继续提供原文证据、条款/表格定位和数值来源，找不到可靠证据时不能编造。

## 1. Professional purpose / OBL decision (E1-3)

| Item | Decision | Reason |
|---|---|---|
| Professional purpose | **UNCHANGED** | "use project context to provide reliable, applicable, traceable building-regulation evidence" — generalization is a capability completion, not a purpose change |
| OBL-01..OBL-06 | **UNCHANGED** | all six obligations remain satisfiable by the generalized path (see conformance evidence) |
| STOP condition S-E1-02 / S-E1-03 | not triggered | no material purpose change; no new obligations required |

## 2. Responsibility classification (spec §6)

Legend: **UNCHANGED** · **EXTENDED** · **IMPLEMENTATION-ONLY** · **REQUIRES DESIGN REVIEW**

| Responsibility | Classification | Rationale |
|---|---|---|
| FN-01 Question & Context Intake | **EXTENDED** | intake must also recognize evidence-query intent (standard reference, clause locator, table locator, topic) — same input contract, wider intent parsing |
| FN-02 Professional Fact Normalization | **UNCHANGED** | SEAM-01 fact vocabulary stays stable; no new professional facts proven necessary (change request §Governance interpretation) |
| FN-03 Regulation Applicability Resolution | **EXTENDED** | must now explicitly separate *evidence retrieval* from *applicability decision* (§13); existing professional rules (防火间距→GB、配建→DBJ) preserved unchanged |
| FN-04 Evidence Locating & Extraction | **EXTENDED (major implementation completion)** | generic clause lookup by any locator, generic table-caption/region resolution, topic-window extraction — reuse existing `locate_clause`/`table_region` primitives |
| FN-05 Evidence Binding & Numeric Safety | **EXTENDED (major implementation completion)** | verbatim assertion + numeric traceability extended to retrieval excerpts; normative numeric claims still require applicability binding |
| FN-06 Uncertainty & Fail-Closed Decision | **EXTENDED** | new statuses for retrieval outcomes (`evidence_retrieved`/`no_reliable_evidence`); fail-closed paths preserved |
| FN-07 Result Composition & Attribution | **IMPLEMENTATION-ONLY** | same 7-field contract; Case-local metadata gains `query_mode` (backward-compatible additive field) |
| FN-08 Artifact & Provenance Preservation | **UNCHANGED** | evidence bundles / ArtifactRefs unchanged; query results may reuse bundle writer |
| FN-09 Corpus Access & Parsing | **EXTENDED (major implementation completion)** | add clause index, table-caption index, normalized search units; manifest SHA fail-closed preserved |
| FN-10 Provider & Execution Plumbing | **UNCHANGED (PRIVATE/DEFERRED)** | no provider work in E1 |
| FN-11 Local Runner / Service Shell | **EXTENDED** | whole-Agent dispatch by query mode (QMODE-01..05); CLI preserved |
| SEAM-01 Professional Project Facts | **UNCHANGED** | default hypothesis confirmed — no new professional facts needed |
| SEAM-02 Regulation Applicability | **EXTENDED** | applicability chain stays Domain-owned; query mode detection distinguishes retrieval from applicability |
| SEAM-03 Regulation Evidence | **EXTENDED** | evidence locating/binding generalized to arbitrary locators/topics; numeric authority remains in admitted corpus text |
| OBL-01 | **UNCHANGED** | direct-clause and conditional-table professional answers still provided with verbatim evidence |
| OBL-02 | **UNCHANGED** | applicability chain remains observable |
| OBL-03 | **UNCHANGED** | numeric authority stays in corpus text; no implementation-generated numeric authority |
| OBL-04 | **UNCHANGED** | no fabricated certainty; no invented clauses/values |
| OBL-05 | **UNCHANGED** | source identity + locator + verbatim content on every accepted answer |
| OBL-06 | **UNCHANGED** | enterprise remains attribution metadata only; retrieval semantics never enter Platform/Runtime |

## 3. New/removed responsibilities

| Change | Detail |
|---|---|
| NEW private module `brea/query.py` | query-intent parsing + deterministic local retrieval (PRIVATE implementation freedom, §10) |
| NO new FN / SEAM / OBL | decomposition preserved (spec §8) |
| NO responsibility removed | all FN-01..11, SEAM-01..03, OBL-01..06 remain |

## 4. Hard anti-fixture commitment (spec §4)

v0.2 runtime code will contain:
- **NO** benchmark question literals
- **NO** per-benchmark clause-id branches (`if … in question: clause="x.x.x"`)
- **NO** per-benchmark table-id branches
- **NO** per-benchmark conclusion strings

Clause/table resolution is data-driven: standard aliases → corpus; clause locator regex
(`第?X.Y.Z条` / `X.Y.Z条`) → clause index lookup; table caption regex → caption index
resolution; topic → deterministic token search. Professional applicability rules
(T-C01/02/03: 防火间距→GB 3.1.3、配建→DBJ 表5.0.1+表5.0.4) are pre-existing
professional rules and are explicitly allowed (spec §15 "professional applicability rules").

## 5. Platform / Runtime / Enterprise impact

| Boundary | Impact |
|---|---|
| Platform Core (`platform_standard/**`) | **NONE** — no change, no new semantics |
| Runtime / RuntimeAdapter | **NONE** — no change |
| Enterprise extensions | **NONE** — `enterprise.identity` reuse only (attribution) |
| D2 binding mechanics | conceptually reusable for a future v0.2 admission (E1 is NOT an admission stage) |
| main | **UNCHANGED** |

## 6. Design-review triggers

None. Default hypothesis confirmed: purpose + obligations unchanged; SEAM-01 unchanged;
SEAM-02/03 extended; FN-04/05/09 major implementation completion. No STOP per
S-E1-01..S-E1-14.

## 7. Builder / Agent-development mechanism (spec §7)

The existing 01-C Builder (`01-c-governed-local-formation/builder/run_builder.py`) is an
initial-Candidate generator (templates → candidate, clean-target). It **cannot consume a
governed professional change** (no change-request / impact-review input, no
baseline-copy semantics) → **BUILDER GAP recorded**.

E1 therefore implements the smallest **Case-local Builder change mechanism** under
`e1-local-evidence-query-generalization/builder/`:

```text
read accepted baseline definition (SHA enforced)
read Professional Change Request
read this Change Impact Review
copy admitted v0.1 Candidate tree → candidate/brea-v0.2 (clean target)
overlay ONLY the authorized changed modules (change source)
verify UNCHANGED modules are byte-identical to v0.1
emit change provenance (manifest + run report + development trace)
```

This is a Case-local development mechanism, NOT a generic Builder Platform.
