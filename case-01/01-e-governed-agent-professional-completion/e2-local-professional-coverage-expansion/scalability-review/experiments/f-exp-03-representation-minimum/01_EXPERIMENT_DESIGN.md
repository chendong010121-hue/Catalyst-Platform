# F-EXP-03 — Experiment Design

Status: authorized execution design; no architecture decision is made here.

## 1. Fixed question and controls

This lab compares the minimum representation required by BREA:

- A': source identity, version/effective note, jurisdiction, unit type, locator,
  verbatim evidence, SHA-256, and non-semantic metadata, plus an ephemeral
  semantic view derived from raw evidence by a generic grammar. The derivation
  uses shared project-fact vocabulary and `unit_type`; it has no source,
  locator, family, clause, or hardcoded-value branches and does not read B-MIN.
- B-MIN: the same G-BASE fields plus only G-SCOPE, G-CONDITION, and G-NUMERIC
  typed groups where the professional contract needs them.

Both tracks receive the same project facts and fact descriptors, source
identifiers, locators, SHA-256 values, evidence excerpts, PC-01..PC-07
validator, independent Gold, fail-closed rules, and deterministic evaluation.
A' and B-MIN enter the same `semantic_view = {scope, conditions, numeric}`
interface before validation. Retrieval is controlled: the lab loads registered
records directly. No LLM, Web, retrieval technology, embedding, vector store,
platform, runtime, or candidate code is used.

The raw corpus is read-only and remains outside Git. The two admitted local
sources are recorded by the existing manifest:

| Source | Local SHA-256 | Use |
|---|---|---|
| GB55037-2022 | `2a217deac98636584dbd328d8449a21bfb4ab30d80483d5355915beaba0594f3` | RF-01, RF-02, RF-04 |
| DBJ33T1021-2023 | `1296922e3dd7ef209aa8c5cc447e4fdd9a64f37e4f4d403cb8533de8cb31d3f7` | RF-03, RF-05, extension |

## 2. Representative forms and professional Gold

The five forms are the smallest set used to expose the representation boundary.
The excerpts below are copied from the admitted local source records; they are
not a corpus submission.

| Case | Form | Source locator and evidence basis | Shared project facts | Expected professional behavior |
|---|---|---|---|---|
| RF-01 | direct clause | GB55037-2022 §4.3.1: `民用建筑内不应设置经营、存放或使用甲乙类火灾危险性物品的商店、作坊或储藏间等。` | `building_kind=民用建筑`; `has_class_ab_hazardous_goods=true` | applicability resolves positive; conclusion is `not_permitted`; preserve locator and verbatim evidence |
| RF-02 | conditional numbered rule | GB55037-2022 §3.4.3: `除受环境地理条件限制只能设置1条消防车道的公共建筑外，其他高层公共建筑和占地面积大于3000m²的其他单、多层公共建筑应至少沿建筑的两条长边设置消防车道。` | `building_kind=公共建筑`; `is_high_rise=true`; `environment_limited_one_lane=false` | applicability resolves positive; conclusion is the two-long-edges fire-lane requirement; exception remains visible |
| RF-03 | table rule | DBJ33T1021-2023 §5.0.4 / 表5.0.4: `商业场所停车位指标不应小于表5.0.4的规定。` and row `大型商业（建筑面积>10000m²）` with rates `机动车 0.8`, `非机动车 1.1` | `project_type=商业`; `building_area_m2=12000` | select the large-commercial row; return both table rates and table locator; do not infer from retrieval alone |
| RF-04 | positive scope + exception/exclusion | GB55037-2022 §2.2.3: `除有特殊要求的建筑和甲类厂房可不设置消防救援口外，在建筑的外墙上应设置便于消防救援人员出入的消防救援口。` | `building_kind=公共建筑`; `special_requirement=false`; `is_class_a_factory=false` | positive scope applies; conclusion is rescue openings required; exclusions are auditable |
| RF-05 | derived numeric modifier | DBJ33T1021-2023 §3.0.11: `住宅建筑应设置访客停车位，设置数量不计入应配建机动车停车位总数，访客停车位数量不应小于应配建机动车停车位总数的2%，且不宜超过20个。` | `project_type=住宅`; `visitor_parking=true`; `required_motor_spaces=600` | retain operand reference, multiply operator, modifier `0.02`, and advisory cap `20`; calculate `12` at runtime and compare it with independent Gold |

RF-05 has one negative control variant with `required_motor_spaces` absent.
It must fail closed as unsupported numeric rather than guess. RF-04 has one
negative control variant with `special_requirement` unresolved; it must fail
closed as unresolved applicability. These controls reuse existing forms and do
not introduce a sixth form.

## 3. Shared professional contract and result contract

The shared deterministic validator evaluates the same declarative predicate
operators for both tracks. It never contains source IDs, clause numbers,
regulation-family terms, or hardcoded regulation values.

PC-01 — a positive applicability scope is present and matches project facts.

PC-02 — material conditions/zone distinctions are explicit and evaluated.

PC-03 — the applicability decision remains observable through a SEAM-02
responsibility trace (`owner=applicability`).

PC-04 — every derived numeric retains source operand, modifier, runtime formula,
and result trace; stored B-MIN regulation data contains no project-derived
result; non-derived cases are explicitly `not_applicable`.

PC-05 — evidence presence is not treated as applicability; applicability must
be based on the representation and project facts.

PC-06 — unsupported numeric input returns `FAIL_CLOSED` with no guessed value.

PC-07 — missing evidence or unresolved applicability returns `FAIL_CLOSED`.

Each assertion produces the same machine result shape:

```text
{
  case_id, track, status, contract_ok, conclusion,
  evidence_trace: {source_id, source_sha256, locator, raw_evidence,
                   semantic_view, applicability_basis, numeric_trace,
                   table_values, table_values_gold_match},
  pc_results: [{id, status, reason}],
  diagnostics: {representation_groups, hidden_knowledge, data_only_extension}
}
```

`contract_ok=true` means either a reliable positive conclusion satisfied all
applicable PCs or the required fail-closed state was returned. `status` remains
the professional result (`PASS` or `FAIL_CLOSED`); a track can therefore fail
the experiment while correctly failing closed when it cannot represent a
required decision.

## 4. B-MIN groups and ablation

| Group | Fields | Required evidence |
|---|---|---|
| G-BASE | source/version/locator/raw evidence/SHA | source and evidence auditability; removal must break PC-07/audit trace |
| G-SCOPE | subject/positive scope/exceptions | RF-01, RF-02, RF-04 applicability and PC-01 |
| G-CONDITION | condition predicates/outcomes/SEAM-02 responsibility | RF-02..RF-05 distinctions and PC-02/03/05 |
| G-NUMERIC | operand reference/operator/modifier/advisory cap; no project-derived result | RF-05 PC-04 and unsupported numeric closure |

Each group is removed in isolation, affected cases are rerun, and a retained
group is justified only if its removal causes a material mandatory-contract or
auditability failure. The ablation does not change the validator or Gold.

## 5. Same-structure data-only extension

After base execution, `RF-EXT-01` adds one direct-clause record from
DBJ33T1021-2023 §4.5.1 (`非机动车停车场（库）应设在建筑工程用地红线内。`).
It uses the existing direct-clause shape, facts, and result contract. The
probe is valid only if the extension changes data records and neither track's
mechanism or schema code changes. It is not unseen-source testing and does not
replace F-EXP-01.

## 6. Decision evidence

The runner records raw per-case results, semantic-interface comparison, PC
summaries, B-MIN ablation, the extension probe, hidden-knowledge scan,
code-surface counts, repository boundary checks, and a verdict derived from
those observations in `02_RESULTS.json`. Interpretation, limitations, and the
observed decision candidate are integrated in `03_EXPERIMENT_REVIEW.md` only.
