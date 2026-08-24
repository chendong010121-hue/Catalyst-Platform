# CASE 01-E / E2 — BREA v0.5 Targeted Product Repair
## STAGE CONTRACT V0.1

> Baseline: `d2d2c4d7578c7e717cef500ae9951c087c91582c`  
> Frozen predecessor: `case-01.brea @ 0.4-candidate`  
> Target: `case-01.brea @ 0.5-candidate`  
> Purpose: repair only the v0.4 External Freeze Review findings  
> Architecture review: NO  
> New experiment: NO  
> E2-C: NOT AUTHORIZED  
> Admission / Binding: NOT AUTHORIZED

## 1. Stage thesis

Do not reopen architecture research.

Preserve v0.4 as frozen evidence and form Candidate N+1 with the smallest product repair needed to make the accepted A' direction actually generic.

## 2. Required repairs

### R-01 — Generic modifier semantics

Remove professional-family-specific modifier behavior from generic semantic code.

Forbidden example:

```text
if auto_extinguishing_system == specific value
and raw contains "增加1.0倍"
→ multiply 2.0
```

Generic semantic derivation must extract normative modifier semantics from evidence in a reusable form, such as:

```text
"增加 X 倍" → factor = 1 + X
"提高 X%" / "按 X%" → explicit percentage/operator form when supported
```

Applicability conditions determine whether a modifier applies; the generic modifier parser must not know a specific regulation family.

### R-02 — Declarative route resolution

`professional_data` already owns route declarations.

Replace family-specific Python dispatch such as:

```text
if fire_compartment ...
if 防火间距 ...
if 停车位 / 配建 ...
```

with generic route selection over declarative route data.

Allowed route data may contain:

```text
intent terms
source/standard id
kind/unit type
locator
required facts
scope/condition descriptors
```

Generic code may dispatch by generic `kind`, but not by named regulation family.

### R-03 — Real anti-hardcode evidence

Replace the narrow literal blacklist with a stronger check that can detect family-specific behavior in implementation code.

At minimum check that:

```text
route/family names and professional trigger phrases live in Domain data, not generic code;
normative values/modifiers are not embedded as family behavior in generic code;
locators/source-specific routing are not hardcoded in generic execution code.
```

The check may use allowlisted Domain data files rather than attempting an impossible universal static proof.

### R-04 — Align C-03 claim and proof

Explicitly prove all five supported professional forms on the coherent path:

```text
direct clause
conditional rule
table rule
scope + exception/exclusion
derived numeric modifier
```

Do not claim more than the test actually executes.

## 3. Preserve

Must preserve without regression:

```text
PC-01..PC-07
v0.3 defect repairs
E1 generalized local query
T-C01 / T-C02 / T-C03
source fidelity / provenance
derived numeric trace
table numeric fidelity
SEAM-02 applicability ownership
Platform-bound compatibility
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
```

No new Seam / Obligation is authorized.

## 4. Growth Gate

Growth Gate remains `PENDING` unless a real provenance-backed additional supported source/revision is available.

Do not fabricate a source.
Do not create a separate F-EXP-01 in this repair.

v0.5 may freeze with Growth Gate still PENDING.

## 5. Technology boundary

Do not introduce:

```text
LLM
Dense retrieval
Embeddings
Vector DB
Web
Memory
Multi-Agent
Platform Core change
Runtime / RuntimeAdapter change
Enterprise extension change
```

If any becomes truly necessary, STOP and report the smallest blocker.

## 6. Candidate / repository boundary

Do not mutate:

```text
v0.1
v0.2
v0.3
v0.4
main
raw corpus
closed historical evidence
```

Form a new `candidate/brea-v0.5/**` tree.

## 7. Minimum checks

Use only the checks needed to prove:

```text
T-01 R-01 generic modifier extraction
T-02 R-02 declarative route resolution
T-03 R-03 anti-hardcode boundary
T-04 five-form coherent path
T-05 PC-01..PC-07 regression
T-06 E1 + T-C01/T-C02/T-C03 regression
T-07 identity / lineage / fingerprint
T-08 Platform-bound compatibility
T-09 protected boundaries
```

Do not add near-duplicate tests for count.

## 8. Minimal artifacts

After explicit authorization, long-lived output only:

```text
candidate/brea-v0.5/**
V0_5_RESULTS.json
V0_5_CANDIDATE_REVIEW.md
V0_5_FREEZE_RECORD.json
```

Reuse Git/test output for supporting checks. No duplicate Evidence Index / conformance package.

## 9. Freeze / publication

After implementation:

```text
record candidate tree SHA
freeze v0.5
status = FROZEN / NOT ADMITTED / NOT BOUND
ONE implementation+evidence+freeze commit
ONE push to case-01
STOP
```

After push, ChatGPT performs v0.5 Candidate Freeze External Review.

## 10. Success boundary

A successful v0.5 may claim:

```text
A' MINIMUM PROFESSIONAL PATH
GENERICITY REPAIRED
PROFESSIONAL CONTRACT PRESERVED
FROZEN NEXT CANDIDATE
```

It may not claim E2 complete, Growth Gate proven, production ready, admission, binding, or Platform generalization.

# VERDICT — READY FOR EXPLICIT v0.5 IMPLEMENTATION AUTHORIZATION
