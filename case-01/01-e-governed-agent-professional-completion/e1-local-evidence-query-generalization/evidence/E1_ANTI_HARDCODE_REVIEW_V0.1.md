# E1 — ANTI-HARDCODE REVIEW — V0.1

> Stage Spec §15 / AC-E1-17/18. Inspects the v0.2 Candidate source for
> benchmark-specific implementation. Automated checks run in
> `tests/run_e1_tests.py` (E1-A-01..03); this document records the manual
> source-level inspection.

## 1. Questions asked (spec §15)

```text
Are benchmark questions copied into runtime code?          → NO
Are benchmark-specific clause ids in dedicated branches?   → NO
Are benchmark-specific conclusions hardcoded?              → NO
Does a reusable locator / retrieval path exist?            → YES (brea/query.py)
Can at least 3 previously unencoded local queries succeed? → YES (7, see §4)
```

## 2. Automated inspection (E1-A-01..03)

| Check | Result |
|---|---|
| E1-A-01 no benchmark question literals in runtime code | PASS |
| E1-A-02 no per-benchmark clause-id branches | PASS |
| E1-A-03 reusable locator/retrieval path exists | PASS |

Forbidden literals scanned across all `candidate/brea-v0.2/brea/*.py`:
`人员密集场所？` · `怎么规定？` · `2.1.1` · `4.1.2` · `99.9.9` · `表5.0.2` ·
`机动车出入口的规定` · `防雷` · `商业（建筑面积` · `配建指标应为多少`
→ **0 hits** (allowed professional-rule literals `3.1.3` / `表5.0.1` / `表5.0.4` / `配建指标` exempt).

## 3. Manual source inspection (brea/query.py — the generalization locus)

- `STANDARD_ALIASES` — data table of standard names/aliases; no per-benchmark entries.
- `extract_clause_locator` — generic regex `第?X.Y.Z条`; NO clause ids in code.
- `extract_table_locator` — generic regex `表X.Y.Z`; NO table ids in code.
- `classify_query` — data-driven mode rules (standard+clause / standard+table /
  standard+retrieval-intent / else applicability); no question literals.
- `topic_search` — n-gram token scoring over the corpus clause index; bounded
  top-3 ranking; no topic literals.

`runner.py` QMODE dispatch contains **no** `if <benchmark question fragment> in question`
branches. The only question-triggered logic is the pre-existing professional
applicability rules (防火间距 / 停车位 / 配建), which the spec explicitly allows
(§15 "professional applicability rules") and which are required by T-C01/02/03.

## 4. Generalization proof — previously unencoded queries that succeed

| Benchmark | Query (not encoded in runtime) | Mechanism |
|---|---|---|
| B-E1-01 | `GB55037-2022 第2.1.1条怎么规定？` | generic clause lookup |
| B-E1-02 | `查一下 GB 55037 的 2.1.1 条原文。` | generic clause lookup (alt wording) |
| B-E1-03 | `DBJ33/T1021-2023 第4.1.2条怎么规定？` | generic clause lookup (different clause) |
| B-E1-05 | `GB55037 里哪里提到人员密集场所？` | topic n-gram search |
| B-E1-06 | `DBJ33/T1021-2023 里关于机动车出入口的规定有哪些？` | topic n-gram search |
| B-E1-07 | `DBJ33/T1021-2023 表5.0.2 的内容？` | generic table-caption resolution |
| B-E1-09 | `GB55037-2022 里关于防雷设计的规定？` | topic search → 0 hits → fail closed |

**7 successful queries** involve locators/topics never individually encoded in the
Candidate runtime — exceeds the required minimum of 3 (AC-E1-17).

## 5. Allowed knowledge used (spec §15)

```text
standard metadata            (STANDARD_ALIASES)
known parser patterns        (clause/table locator regexes, caption filter)
table structure knowledge    (general OCR caption pattern for this source format)
professional applicability rules (pre-existing 防火间距/配建 rules — T-C01/02/03)
```

## 6. What is NOT claimed

```text
NOT one branch per benchmark
NOT one conclusion string per benchmark
NOT one dedicated handler per test question
```

## Verdict

**E1 ANTI-HARDCODE REVIEW: PASS**
