# E1 — AGENT DEVELOPMENT TRACE — V0.1

> Governed Agent-development trace (Stage Spec §7 / §20). Shows the full chain from
> Professional Change Request → Change Impact → Builder change mechanism → Candidate
> N+1 → tests/benchmark → output. No v0.2 code was changed outside this trace.

## 1. Chain

```text
E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md
        ↓
E1_CHANGE_IMPACT_REVIEW_V0.1.md (change/)
        ↓
builder/run_e1_builder.py  (Case-local Builder change mechanism)
        ↓
candidate/brea-v0.2/**  (Candidate N+1 workspace)
        ↓
tests/run_e1_tests.py + tests/benchmark/E1_BENCHMARK_V0.1.json
        ↓
evidence/E1_TEST_RESULTS.log.txt + E1_BENCHMARK_RESULTS_V0.1.json
```

## 2. Professional Change Request (fixed)

> 让 BREA 能够对已经接入的本地建筑规范进行一般化查询，而不是只能回答预设测试题；
> 回答必须继续提供原文证据、条款/表格定位和数值来源，找不到可靠证据时不能编造。

## 3. Impacted vs unchanged responsibilities (from E1_CHANGE_IMPACT_REVIEW_V0.1.md)

```text
EXTENDED              : FN-01 Intake · FN-03 Applicability · FN-04/05 Evidence ·
                        FN-06 Uncertainty · FN-09 Corpus · FN-11 Runner ·
                        SEAM-02 · SEAM-03
IMPLEMENTATION-ONLY   : FN-07 Result (metadata extension) · FN-08 none ·
                        identity/contracts/result modules
UNCHANGED             : FN-02 Facts · FN-08 Artifact · FN-10 Provider ·
                        SEAM-01 · OBL-01..06 · professional purpose
```

## 4. Builder / change mechanism input

`builder/run_e1_builder.py` consumed:

| Input | Path |
|---|---|
| accepted baseline definition (SHA enforced) | `01-b-governed-agent-definition/builder/BUILDER_CONSUMABLE_DEFINITION_V0.1.md` |
| Professional Change Request | `E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md` |
| Change Impact Review | `change/E1_CHANGE_IMPACT_REVIEW_V0.1.md` |
| admitted v0.1 baseline tree | `01-c-governed-local-formation/candidate/brea-v0.1/**` |
| authorized change source | `builder/change_source/**` |

**BUILDER GAP recorded (Change Impact Review §7):** the 01-C Builder is an
initial-Candidate generator (templates → clean target) and cannot consume a governed
professional change. E1 implemented the smallest Case-local change mechanism
(baseline copy + authorized overlay), NOT a generic Builder Platform.

## 5. Files created / changed in v0.2 Candidate

| File | Change | Reason |
|---|---|---|
| `brea/corpus.py` | EXTENDED | clause index + table caption index + search units for generic retrieval (FN-09 completion) |
| `brea/evidence.py` | EXTENDED | generic clause/table/topic evidence building + line-verbatim assertion (FN-04/05) |
| `brea/query.py` | NEW | generalized local evidence-query mechanism: standard/clause/table resolution + topic n-gram retrieval (QMODE-01..04) |
| `brea/runner.py` | EXTENDED | whole-Agent QMODE dispatch; T-C01/02/03 professional paths preserved |
| `brea/identity.py` | IMPL-ONLY | version → `v0.2-candidate`; module refs updated (FN-01/04/09) |
| `brea/contracts.py` | IMPL-ONLY | `ImplementationMetadata` + `query_mode`/`standard_id` (backward-compatible) |
| `brea/result.py` | IMPL-ONLY | pass-through of query metadata |
| `README.md` | IMPL-ONLY | v0.2 candidate description |
| `brea/{applicability,facts,uncertainty,__init__}.py` | UNCHANGED | byte-identical to v0.1 (verified by builder) |
| `tests/**` (candidate) | UNCHANGED | byte-identical v0.1 tests + fixtures (regression surface) |

## 6. Reason per changed module

- **corpus.py**: the v0.1 corpus layer had extraction primitives but no generic
  index (clause id → text/locator, table caption index) and no search units.
- **evidence.py**: v0.1 `locate_clause` was hardwired to a single clause via
  `extract_clauses`; generalized to clause-index lookup; added table-caption
  resolution and topic-excerpt evidence; verbatim check moved to line-level to
  handle multi-page clauses/tables without weakening fidelity.
- **query.py (new)**: implements the reusable query mechanism — standard alias
  resolution, clause/table locator extraction, deterministic n-gram topic
  retrieval with bounded ranking. This is where generalization lives; no
  benchmark-specific branch exists (see anti-hardcode review).
- **runner.py**: v0.1 `answer()` hardcoded 防火间距→3.1.3 and 配建→表5.0.1+表5.0.4
  routing. The E1 dispatch classifies query intent first (QMODE-01..05); the
  professional applicability paths are preserved verbatim as QMODE-05.
- **identity/contracts/result**: version bump + backward-compatible metadata.

## 7. Tests / benchmark

- Candidate self-check (copied v0.1 tests): **15/15 PASS** on v0.2.
- E1 tests (structural + anti-hardcode + benchmark + regression): **23/23 PASS**.
- Benchmark B-E1-01..13: all PASS (data in `tests/benchmark/E1_BENCHMARK_V0.1.json`).

## 8. Candidate output

```text
candidate/brea-v0.2/**  (separate workspace; v0.1 untouched)
status: evidence_retrieved for generalized queries
      : accepted_with_evidence / insufficient_context for professional cases
query_mode + standard_id in metadata (retrieval vs applicability observable)
```

## 9. Platform / Runtime impact

NONE (see `evidence/E1_PLATFORM_COMPATIBILITY_CHECK_V0.1.md`).
