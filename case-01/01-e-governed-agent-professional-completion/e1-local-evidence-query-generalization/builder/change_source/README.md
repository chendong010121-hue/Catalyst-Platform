# BREA — Building Regulation Evidence Agent · v0.2-candidate

CASE 01-E / E1 governed candidate — **Local Evidence Query Generalization** (product-completion slice).

Same governed Agent lineage: `case-01.brea`. New professional implementation Candidate:
**`v0.2-candidate`** (not admitted, not bound — E1 is not an admission stage).

## What is new in v0.2 (vs admitted v0.1 baseline)

```text
generalized local evidence query over the two admitted regulations:
  QMODE-01 explicit standard + clause locator   -> verbatim clause evidence
  QMODE-02 explicit standard + missing clause   -> no_reliable_evidence (no invention)
  QMODE-03 local topic evidence search          -> bounded source-backed candidates
  QMODE-04 explicit table / table-region query  -> verbatim table region
  QMODE-05 existing professional applicability  -> T-C01 / T-C02 / T-C03 preserved

anti-fixture rule:
  NO benchmark question literals / per-benchmark clause ids / table ids / conclusions
  all clause/table resolution is data-driven from the admitted corpus
```

The mechanism is deterministic, stdlib-only (no LLM / RAG / Web / vector DB), and the
evidence contract (request_id/status/conclusion/evidence_items/artifacts/uncertainty/
implementation_metadata) is preserved; `implementation_metadata` gains
`query_mode`/`standard_id` (backward-compatible).

## Source layout

```text
brea/query.py        NEW      — generalized local evidence-query mechanism
brea/corpus.py       EXTENDED — clause index, table caption index, search units
brea/evidence.py     EXTENDED — generic clause/table/topic evidence building
brea/runner.py       EXTENDED — whole-Agent QMODE dispatch (T-C01/02/03 preserved)
brea/identity.py     IMPL-ONLY — version v0.2-candidate
brea/contracts.py    IMPL-ONLY — metadata extension (query_mode/standard_id)
brea/result.py       IMPL-ONLY — pass-through of query metadata
(applicability.py / facts.py / uncertainty.py / __init__.py: byte-identical to v0.1)
```

## Professional boundaries (unchanged)

- Numeric authority stays in the admitted corpus text (OBL-03); no invented values.
- Evidence retrieval is explicitly distinguished from professional applicability (spec §13).
- Enterprise context remains attribution only (OBL-06).
- Corpus: exactly the two admitted local regulations; raw corpus never committed.

See `change/E1_CHANGE_IMPACT_REVIEW_V0.1.md` and `change/E1_AGENT_DEVELOPMENT_TRACE_V0.1.md`
for the governed change trace.
