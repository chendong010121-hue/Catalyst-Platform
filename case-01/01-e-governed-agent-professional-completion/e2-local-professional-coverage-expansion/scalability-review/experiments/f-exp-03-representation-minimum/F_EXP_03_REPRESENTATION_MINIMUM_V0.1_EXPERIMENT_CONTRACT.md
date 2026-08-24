# F-EXP-03 — REPRESENTATION MINIMUM EXPERIMENT V0.1
## MINIMUM FORMAL EXPERIMENT CONTRACT

> **Case:** CASE 01 / BREA  
> **Parent:** CASE 01-E / E2 Scalability Review  
> **Baseline:** `3f7ffca687bb1ba4d1d83367ba027add0fdd03bb`  
> **Frozen Candidate:** `case-01.brea @ 0.3-candidate` — READ-ONLY  
> **Catalyst main:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **Question:** What is the minimum professional knowledge representation BREA actually needs?  
> **Execution:** NOT AUTHORIZED  
> **Authorization Record:** REQUIRED BEFORE EXECUTION  
> **v0.4 / E2-C / Platform / Runtime changes:** NOT AUTHORIZED

---

# 1. Single Experiment Question

Compare only:

```text
A' — RAW / LIGHT
source identity + locator + raw evidence + generic metadata
+ generic deterministic/declarative mechanism

vs

B-MIN — LIGHTWEIGHT TYPED STRUCTURE
same source/evidence basis
+ only the professional semantic fields proven necessary
+ same generic deterministic/declarative mechanism
```

The experiment must try to prove **A' is sufficient**.

B-MIN gains evidence only if A' fails a mandatory professional contract for a representation reason and B-MIN resolves that failure without hiding regulation-family knowledge in code.

The independent variable is only:

# **representation depth**

Not retrieval technology, LLM, RAG, Web, Platform or Runtime.

---

# 2. Fixed Professional Contracts

Both tracks use the same acceptance logic.

```text
PC-01 Positive applicability scope
PC-02 Material condition / zone distinction
PC-03 Applicability remains explicit through SEAM-02 responsibility
PC-04 Derived numeric keeps source operand + modifier + formula + result trace
PC-05 Retrieval != Applicability
PC-06 Unsupported numeric -> fail closed
PC-07 No reliable evidence / unresolved applicability -> fail closed
```

A track cannot win by weakening these contracts.

---

# 3. Minimum Representative Forms

Use the minimum five forms needed to distinguish the representations:

```text
RF-01 direct clause
RF-02 conditional numbered rule
RF-03 table rule
RF-04 positive scope + exception/exclusion
RF-05 derived numeric modifier
```

Use only already admitted CASE 01 local sources.

Preferred sources:

```text
GB55037-2022
DBJ33T1021-2023
```

Raw corpus remains local, read-only and outside GitHub.

The exact source examples and expected professional behavior are recorded once inside `01_EXPERIMENT_DESIGN.md` before results are produced.

Do not add more forms unless a sixth form represents a genuinely different decision boundary that the first five cannot test.

---

# 4. Fair Comparison Rules

A' and B-MIN must share:

```text
same source evidence / SHA / locator
same project facts
same five rule forms
same PC-01..07
same evaluation assertions
same result contract
same numeric rules
same fail-closed rules
```

Use controlled evidence loading. Retrieval quality is outside this experiment.

Held out:

```text
LLM
embeddings
dense retrieval
BM25 comparison
reranking
Vector DB
Web
user upload
E2-C Benchmark
Platform / Runtime changes
```

If either track requires one of these to continue, STOP and report the blocker.

---

# 5. Track A' — Strongest Fair Light Representation

A' may contain a generic evidence record such as:

```text
EvidenceUnit
- source_id
- edition / effective status
- jurisdiction
- unit_type
- locator
- raw_evidence
- source_sha256
- generic non-semantic metadata
```

A' may use generic parser / declarative validator machinery.

A' may NOT hide B-MIN semantics under generic metadata names.

Examples of forbidden hidden structure:

```text
scope_conditions
exceptions
condition -> value map
numeric modifier / derivation formula
```

A' also may not use clause-specific or family-specific runtime code such as:

```text
if locator == "4.3.16"
if question contains "防火分区"
hardcoded regulation values in generic mechanism code
one extraction function per tested regulation family
```

---

# 6. Track B-MIN — Typed Structure Candidate

B-MIN starts with only four possible field groups:

```text
G-BASE
source / version / locator / raw evidence

G-SCOPE
subject / positive scope / exceptions

G-CONDITION
condition -> outcome/value

G-NUMERIC
numeric operand / modifier / derivation trace
```

Every group beyond G-BASE must be justified by an observed A' failure or a mandatory professional/auditability requirement.

Run field-group ablation:

```text
remove group
-> rerun affected contracts
-> if nothing meaningful breaks: REMOVE or DEFER the group
```

Do not keep fields because they may be useful later.

---

# 7. Shared Lab Rule

Implement one small shared lab harness:

```text
registered source evidence
-> track representation adapter
-> shared professional input
-> shared applicability/validation interface
-> shared structured result
-> PC-01..07 assertions
```

Track-specific code may implement only representation-specific adaptation.

If A' and B-MIN use different Gold / acceptance logic, the experiment is INVALID.

---

# 8. One Small Extension Probe

After each track is stable, add **one** additional same-structure regulation instance from an already admitted source.

Allowed change:

```text
data / normalized record only
```

Target:

```text
NO generic mechanism code change
NO schema change
```

This is only a local same-structure probe.

It does not replace F-EXP-01 unseen-source testing.

---

# 9. Minimal Decision Evidence

Compare only these dimensions:

```text
1. PC-01..07 correctness
2. source -> condition -> conclusion auditability
3. numeric derivation traceability
4. fail-closed clarity
5. hidden-knowledge risk
6. knowledge-specific code surface
7. representation complexity
8. same-structure data-only extension result
```

Do not create standalone reports for each dimension.

All interpretation belongs in one integrated experiment review.

---

# 10. Decision Rules

## A_PRIME_SUFFICIENT

Choose A' only if:

```text
all PC-01..07 pass
no hidden professional semantics in code / generic metadata
same-structure extension is data-only
source/numeric/applicability trace is complete
B-MIN adds no material contract or auditability benefit
```

## B_MIN_EVIDENCED

Choose B-MIN only if:

```text
A' fails a mandatory contract for a representation reason
B-MIN passes the same contract
A' cannot be repaired without hiding family-specific semantics
retained B-MIN field groups map to observed failures
ablation removes unnecessary structure
```

## BOTH_INSUFFICIENT

Use if both tracks fail mandatory contracts or both require hidden family-specific code.

## INCONCLUSIVE

Use if both pass but the representation tradeoff still cannot be fairly distinguished.

## EXPERIMENT_INVALID

Use if source, Gold, acceptance logic or controlled variables diverge.

DeepSeek reports a **decision candidate** only. External review decides the accepted architecture consequence.

---

# 11. Minimal Artifact Surface

After authorization, F-EXP-03 may create only:

```text
F_EXP_03_REPRESENTATION_MINIMUM_V0.1_EXPERIMENT_CONTRACT.md
F_EXP_03_AUTHORIZATION_RECORD_V0.1.yaml

01_EXPERIMENT_DESIGN.md
  - source refs / SHAs
  - five cases
  - A' design
  - B-MIN design
  - shared PC-01..07 / result contract

lab/
  shared/**
  a-prime/**
  b-min/**

02_RESULTS.json
  - raw machine-readable per-case results
  - ablation results
  - same-structure probe result

03_EXPERIMENT_REVIEW.md
  - PC results
  - hidden-knowledge review
  - code-surface comparison
  - representation complexity
  - ablation interpretation
  - limitations
  - decision candidate
  - repository / protected-boundary integrity
```

No additional Markdown report, evidence index, conformance report, repository-integrity report, summary report or duplicate human-readable result is created unless execution reveals an independent governance decision that cannot live in these artifacts.

Supporting consistency checks belong in test output / execution Trace and are summarized only where they affect the final decision.

---

# 12. Authorization / Publication Boundary

Before any lab execution, create the declarative:

```text
F_EXP_03_AUTHORIZATION_RECORD_V0.1.yaml
```

It must record:

```text
user decision = granted
F-EXP-03 lab code = allowed
read-only admitted corpus use = allowed
raw corpus commit = false
Candidate mutation = false
v0.4 formation = false
E2-C benchmark = false
Platform / Runtime / main mutation = false
publication limit = one experiment commit + one push
```

Authorization Record is evidence of the decision, not a second imperative prompt.

After the authorized experiment commit/push:

```text
STOP
-> ChatGPT External Experiment Review
```

---

# 13. Protected Boundaries / Stop Conditions

All experiment writes remain under this F-EXP-03 directory.

Do not modify:

```text
BREA v0.1 / v0.2 / frozen v0.3
accepted historical evidence
Platform Standard / Core
Runtime / RuntimeAdapter
Enterprise extensions
main
raw corpus
E2-C evaluation/benchmark
```

STOP if:

```text
source evidence cannot be resolved
A' / B-MIN use different professional acceptance logic
one track receives stronger source evidence
A' hides typed semantics in generic metadata
B-MIN cannot justify retained field groups
family/clause-specific runtime knowledge becomes necessary
raw corpus must be committed
Candidate / Platform / Runtime mutation appears necessary
LLM/retrieval expansion becomes necessary
E2-C benchmark is created
authorization record is missing
main changes
```

Preserve the smallest blocker evidence and return for review.

---

# 14. Final Report Shape

DeepSeek's final message only needs:

```text
STATUS
READY FOR EXTERNAL REVIEW / BLOCKED / INVALID

SOURCE SET
<ids + SHAs>

A'
PC-01..07 result
hidden knowledge PASS/FAIL
same-structure probe PASS/FAIL

B-MIN
PC-01..07 result
retained field groups
ablation summary
hidden knowledge PASS/FAIL
same-structure probe PASS/FAIL

CODE SURFACE
A' / B summary

REPRESENTATION COMPLEXITY
A' / B summary

DECISION CANDIDATE
A_PRIME_SUFFICIENT / B_MIN_EVIDENCED /
BOTH_INSUFFICIENT / INCONCLUSIVE / EXPERIMENT_INVALID

PROTECTED BOUNDARIES
PASS/FAIL

EXPERIMENT COMMIT
<sha>

MAIN
UNCHANGED / CHANGED
```

STOP.

---

# 15. Current State

```text
A' vs B-MIN
UNRESOLVED

F-EXP-03 CONTRACT
ACCEPTED — MINIMUM ARTIFACT SURFACE

F-EXP-03 EXECUTION
NOT AUTHORIZED

F-EXP-01
WAITING FOR F-EXP-03

v0.4
NOT AUTHORIZED

E2-C
NOT AUTHORIZED
```

# **VERDICT — READY FOR EXPLICIT F-EXP-03 AUTHORIZATION**
