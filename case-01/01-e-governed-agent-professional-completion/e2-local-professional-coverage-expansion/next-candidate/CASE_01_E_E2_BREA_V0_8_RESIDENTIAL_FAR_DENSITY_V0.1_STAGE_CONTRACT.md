# CASE 01-E / E2 — BREA v0.8 Residential FAR & Building Density Professional Slice
## STAGE CONTRACT V0.1

> Baseline branch HEAD: `915ad9057780e2b446c92c63d8afc798096f97e8`  
> Frozen predecessor: `case-01.brea @ 0.7-candidate`  
> Target Candidate: `case-01.brea @ 0.8-candidate`  
> Baseline Knowledge: `KR-002`  
> Target Knowledge: `KR-003`  
> Trigger: KR-002 Growth Gate `G-03 = STRUCTURAL_GROWTH_REQUIRED`  
> Professional slice: 《杭州市城市规划管理技术规定》表（2-3）  
> Table（3-2） road setback / Q semantics: OUT OF SCOPE  
> E2-C: NOT AUTHORIZED  
> Admission / Binding: NOT AUTHORIZED

## 1. Single Stage thesis

Add exactly one new useful planning-professional capability:

```text
single-nature urban residential land (0701)
+
residential average storeys
→
select the applicable row of 表（2-3）
→
return source-backed maximum FAR
+
source-backed maximum building density
```

Do not expand to the whole Hangzhou regulation.

The new professional meaning is legitimate Domain growth proven necessary by G-03. Keep the implementation minimal, declarative where possible, and evidence-bound.

---

## 2. Capability Contract

### Observable supported behavior

For a project-specific question asking the residential FAR / building-density control under 表（2-3）, v0.8 must:

```text
1. resolve the Hangzhou source through KR-003;
2. require the minimum professional project facts;
3. establish positive applicability instead of treating retrieval as applicability;
4. retrieve 表（2-3） and preserve native locator / verbatim evidence;
5. select the row using residential average storeys;
6. return BOTH maximum FAR and maximum building density from the selected source row;
7. preserve the table note that residential building height shall not exceed 80m;
8. explicitly state that this Stage does not by itself decide full-project compliance with the 80m note;
9. fail closed when applicability, row selection, or source-backed numeric binding is unresolved.
```

### Weaker behavior that must NOT pass

```text
retrieval-only answer presented as project applicability;
choosing a row from words in the user question instead of governed project facts;
hardcoding 1.2 / 43% / 2.0 / 35% / 3.0 / 30% in Python as normative authority;
assuming every residential project in Hangzhou is governed by 表（2-3）;
ignoring the “single-nature 0701” scope;
ignoring special-area / separately-determined planning indicators;
returning a value when average storeys do not map to a supported source row;
answer-specific / benchmark-specific branches.
```

---

## 3. Source-backed professional boundary

The source establishes:

```text
single-nature urban residential land (0701)
→ capacity-control indicators follow 表（2-3）

1–3 storeys
→ FAR max 1.2
→ building density max 43%

4–9 storeys
→ FAR max 2.0
→ building density max 35%

10–26 storeys
→ FAR max 3.0
→ building density max 30%

Table note:
residential building height shall not exceed 80m
```

The source also states that the regulation directly applies to Hangzhou urban-area urban construction land, while designated special/heritage/urban-renewal and similar areas may lawfully determine FAR / building density and related indicators separately.

Therefore project-specific positive applicability must not be inferred from “Hangzhou + residential” alone.

---

## 4. Minimum new Domain facts

Reuse existing:

```text
jurisdiction
```

Authorize only these new SEAM-01 professional facts:

```text
land_use_nature
residential_average_storeys
planning_special_area_status
```

Minimum intended meaning:

```text
land_use_nature
  whether the project land is the source-defined single-nature urban residential land (0701)

residential_average_storeys
  numeric project fact used to select the source table band

planning_special_area_status
  whether a source-recognized special-area / separately-determined planning-indicator condition applies or remains unresolved
```

Do not add `road_width_m`, Q, road-setback facts, orientation, or other future planning facts.

`residential_average_storeys` must be normalized as numeric. Invalid numeric input fails closed.

---

## 5. KR-003 boundary

Create `knowledge/KR-003.json` from KR-002.

KR-003 may add only what this professional slice requires:

```text
knowledge_revision_id = KR-003
KR-002 sources / standards preserved
one declarative Hangzhou 表（2-3） professional route
fact descriptors for the three authorized new facts
minimum declarative selector / table semantics needed by the route
```

Do not mutate KR-002.

Do not add a 表（3-2） professional route.

The normative table values may not become unverified configuration authority. They must be derived from source evidence at execution time OR, if a minimal normalized representation is used, be deterministically verified against the bound source evidence before a professional conclusion is emitted.

KR-003 must preserve source locator `表（2-3）` and CORPUS-03 provenance.

---

## 6. Minimum new professional reasoning primitive

A single reusable PRIVATE-HOW extension is authorized for this source-proven need:

```text
numeric-banded table selection
```

Conceptually:

```text
selector fact
→ source-backed numeric range/band
→ matching source table row
→ multiple source-backed outputs
```

For this slice:

```text
selector fact = residential_average_storeys
outputs = FAR maximum + building-density maximum
```

The implementation must be generic by route/unit semantics, not by source name or route name.

Forbidden:

```text
if route == residential_far_density
if source == CORPUS-03
if question contains 容积率 then return known row
if average_storeys <= 3 then hardcoded 1.2,43
```

The selected result must remain traceable to the actual source row.

---

## 7. Applicability / fail-closed requirements

The professional path must establish all required conditions before returning project-specific values.

At minimum:

```text
jurisdiction is within the directly supported Hangzhou urban-area applicability used by this Stage;
land_use_nature resolves to single-nature urban residential land (0701);
planning_special_area_status establishes that no separately-determined special-area override is active;
residential_average_storeys resolves to one source-supported row.
```

If a county/city merely falls under the source language “may refer to”, do not silently treat that as the same direct authority without an explicit accepted policy.

If `planning_special_area_status` is unknown or indicates a separately-determined indicator regime, fail closed for the general 表（2-3） project-specific conclusion.

If average storeys fall outside source-supported bands, return no reliable professional value rather than extrapolating.

---

## 8. Height-note boundary

The 表（2-3） note `住宅建筑高度不大于80米` must be preserved in source evidence / answer qualification.

This Stage does NOT add a governed `residential_building_height_m` fact and does NOT claim full compliance with that note.

A successful answer may state, in substance:

```text
根据当前已建立的 表（2-3）适用条件，所选行的 FAR / 建筑密度最大值为 X / Y；
同时表注另要求住宅建筑高度不大于80m，本次未据此判定完整项目合规性。
```

If the user explicitly asks for full compliance including the 80m condition, fail closed / state the missing unsupported fact rather than claiming complete compliance.

---

## 9. Preserve existing architecture boundaries

Keep:

```text
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
```

The three new facts extend SEAM-01; the new table-row applicability remains inside existing SEAM-02; source/numeric binding remains SEAM-03.

No new Governed Seam or Obligation is authorized.

The professional Semantic View remains ephemeral PRIVATE HOW.

No Platform / Runtime / RuntimeAdapter / Enterprise responsibility change is authorized.

---

## 10. Required construction proof

Use a small fixed construction self-check set. At minimum:

```text
P-01 low-rise band
  ordinary supported scope + average storeys 2
  → FAR 1.2 + density 43%

P-02 multi-storey band
  ordinary supported scope + average storeys 6
  → FAR 2.0 + density 35%

P-03 high-rise band
  ordinary supported scope + average storeys 12
  → FAR 3.0 + density 30%

P-04 missing selector fact
  missing residential_average_storeys
  → fail closed

P-05 wrong land-use scope
  non-single-nature / non-0701
  → no project-specific 表（2-3） conclusion

P-06 special-area unresolved / override
  → fail closed for general 表（2-3） project-specific conclusion

P-07 unsupported band
  average storeys outside source-supported rows
  → no extrapolation / fail closed

P-08 evidence fidelity
  native 表（2-3） locator + selected row values + 80m note are source-backed

P-09 natural-language paraphrase
  wording differs from construction examples but resolves the same route without a dedicated branch
```

Do not multiply near-duplicate cases.

---

## 11. Regression / anti-hardcode proof

Must preserve:

```text
v0.7 S-01..S-05 source-structure behavior
legacy X.Y.Z + 表5.0.4
E1 generalized local query
existing PC-01..PC-07 professional contract
existing five professional forms
T-C01 / T-C02 / T-C03
KR-001 / KR-002 binding
Knowledge Revision traceability
FN / SEAM / OBL
Platform-bound compatibility
```

Anti-hardcode check must verify that Python professional behavior does not contain the authoritative 表（2-3） output tuple as family-specific answer logic and does not branch on `CORPUS-03`, `HZ-PLANNING-TECH-2026`, or the new route name.

---

## 12. Explicitly deferred

Do NOT implement in v0.8:

```text
表（3-2） building setback from road red line
road_width_m
Q coefficient
building-height-based Q selection
orientation / wall-type planning semantics
mixed-use planning control
all Hangzhou planning rules
80m full compliance evaluation
Web fallback
LLM / Dense retrieval / embeddings / Vector DB
Platform knowledge service
E2-C benchmark
Admission / Binding
```

Discovery of a need for one of these is evidence, not authorization.

---

## 13. Knowledge hash hardening boundary

The previously observed cross-environment Knowledge Revision byte-SHA instability is NOT part of this professional slice.

Do not redesign Knowledge identity in v0.8 merely to clean it up.

Record the current binding SHA consistently and keep the hardening item open for closure before final E2 admission/close decision.

---

## 14. Minimal artifact surface

After explicit authorization, long-lived output only:

```text
knowledge/KR-003.json
candidate/brea-v0.8/**
V0_8_RESULTS.json
V0_8_CANDIDATE_REVIEW.md
V0_8_FREEZE_RECORD.json
```

No extra Evidence Index / design-summary / conformance package by default.

Raw PDF / local derivative remain uncommitted.

---

## 15. Freeze / evaluation chronology

Construction self-checks may use the known source rows above.

Specific independent E2-C Benchmark cases / private Golds must NOT be created before v0.8 Freeze.

After successful implementation:

```text
record KR-003 binding identity
record v0.8 candidate tree SHA
record implementation fingerprint
freeze v0.8
status = FROZEN / NOT ADMITTED / NOT BOUND
ONE implementation + evidence + freeze commit
ONE push to case-01
STOP
```

Then ChatGPT performs External v0.8 Candidate Freeze Review.

Only after external PASS may the next E2 evaluation decision be considered.

---

## 16. Success boundary

A successful v0.8 may claim only:

```text
HANGZHOU TABLE（2-3）
RESIDENTIAL FAR / BUILDING-DENSITY
BOUNDED PROFESSIONAL COVERAGE — CASE PROVEN

NEW PLANNING FACTS
INTEGRATED THROUGH EXISTING SEAM RESPONSIBILITIES

NUMERIC-BANDED TABLE SELECTION
PROVEN AS PRIVATE PROFESSIONAL MECHANISM
```

It may not claim:

```text
full Hangzhou planning compliance
road-setback capability
all planning regulations supported
production readiness
Platform-general professional planning capability
E2 complete
```

# VERDICT — READY FOR EXPLICIT v0.8 + KR-003 IMPLEMENTATION AUTHORIZATION
