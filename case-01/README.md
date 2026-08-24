# CASE 01 — BREA Governed Product Development

This directory is the Case-local workspace for the real **Building Regulation Evidence Agent (BREA)** product and the Catalyst evidence generated while building it.

This README is a **navigation / current-state surface**, not Architecture authority and not Stage authorization.

---

## Current authoritative state

```text
CASE 01-A
CLOSED

CASE 01-B — Governed Agent Definition
EVIDENCE-BACKED PASS / CLOSED

CASE 01-C — Governed Local Formation
EVIDENCE-BACKED PASS / CLOSED

CASE 01-D — Understanding / Admission / Binding
EVIDENCE-BACKED PASS / CLOSED

CASE 01-E / E1 — Local Evidence Query Generalization
EVIDENCE-BACKED PASS / CLOSED

CASE 01-E / E2
ACTIVE
```

Current product states:

```text
BREA v0.1-candidate
ADMITTED / BOUND / READ-ONLY

BREA v0.2-candidate
GENERALIZED LOCAL EVIDENCE QUERY PROVEN
REFERENCE / READ-ONLY

BREA v0.3-candidate
FROZEN
NOT ADMITTED / NOT BOUND
FREEZE REVIEW FOUND PROFESSIONAL CONTRACT DEFECTS
PRESERVED AS EVIDENCE
```

Current architecture investigation:

```text
Scalable Retrieval & Reasoning Review
EVIDENCE-BACKED PARTIAL PASS

A' vs B-MIN representation depth
UNRESOLVED

F-EXP-03 Representation Minimum Contract
ACCEPTED
EXECUTION NOT AUTHORIZED

F-EXP-01 Unseen Source Experiment
WAITING FOR F-EXP-03

v0.4+
NOT AUTHORIZED

E2-C independent benchmark
NOT AUTHORIZED
```

Catalyst `main` remains protected from Case-local work unless separately authorized.

---

## Active canonical inputs

For current work, start from these files instead of reading every historical artifact:

```text
methods/
  CATALYST_GOVERNED_AGENT_CONSTRUCTION_METHOD_V0.1_ACCEPTED.md

01-e-governed-agent-professional-completion/
  e2-local-professional-coverage-expansion/
    CASE_01_E_E2_LOCAL_PROFESSIONAL_COVERAGE_EXPANSION_V0.1_STAGE_SPEC.md

    scalability-review/
      BREA_SCALABLE_RETRIEVAL_AND_REASONING_ARCHITECTURE_REVIEW_V0.1_REVIEW_CONTRACT.md

      experiments/
        f-exp-03-representation-minimum/
          F_EXP_03_REPRESENTATION_MINIMUM_V0.1_EXPERIMENT_CONTRACT.md
```

Earlier Stage Plans, execution reports, Evidence indexes, test logs, Freeze records and rejected Candidates remain valid historical evidence, but they are **not automatically active requirements** for the next action unless one of the canonical inputs references them.

---

## Historical evidence rule

Closed Stage directories are preserved because they establish:

```text
what was attempted
what exact Candidate existed
what evidence was observed
what was accepted / rejected
why later decisions changed
```

Do not rewrite or delete historical evidence merely to make the tree look clean.

Repository cleanliness is achieved by keeping the **active surface small**, not by erasing history.

---

## Artifact-minimum working rule

From the current E2 work onward, use the smallest artifact set that can support the decision.

Before creating a new document, test, schema field, module or governed object, ask:

```text
1. Which current decision cannot be made without it?
2. What independent evidence would disappear if it were removed?
3. Can the same responsibility live inside an existing artifact?
```

Default result when the answers are weak:

```text
DO NOT CREATE IT.
```

### Prefer

```text
one Contract
one declarative Authorization Record
minimum implementation / lab code
machine-readable result when useful
one integrated Review / Decision artifact
Git / Trace / test output for supporting checks
```

### Avoid by default

```text
separate Markdown for every check
Evidence Index that only repeats the directory tree
standalone repository-integrity report when Git compare already proves it
standalone conformance report when the final Review can contain the same decision evidence
summary-of-summary documents
multiple human-readable copies of the same machine result
persisting duplicate source trees only to prove a change that a manifest / diff can prove
```

A check belongs in a separate artifact only when it has independent governance or decision value.

---

## Agent-minimum rule

A Governed Agent must remain decomposable, testable and replaceable, but it must not be split merely because Catalyst can name more layers.

```text
FUNCTIONALLY DECOMPOSABLE
!=
MAXIMALLY DECOMPOSED
```

Default:

```text
no new Governed Seam
no new Platform capability
no new Enterprise object
no new RAG / LLM / Memory / sub-agent
```

until real Case evidence requires it.

Implementation should remain the smallest mechanism that satisfies the accepted professional contract.

---

## Test-minimum rule

Testing exists to eliminate wrong architectures and unsafe professional behavior, not to maximize case count.

```text
one important hypothesis
→ minimum cases capable of falsifying it
```

Add more cases only when they cover a distinct failure mode or decision boundary.

Do not add near-duplicate cases merely to make a benchmark look comprehensive.

---

## Evidence-minimum rule

Evidence exists to support a decision, not to maximize documentation.

Prefer:

```text
machine result
+ exact source / version / hash
+ concise integrated interpretation
```

Keep analysis, consistency checks and leak checks in execution Trace / test output when they do not need independent long-lived authority.

---

## Corpus rule

Raw regulation corpus files marked `upstream=FORBIDDEN` remain local and read-only.

GitHub may contain only the minimum traceable metadata / SHA / bounded excerpts / derived non-corpus material required by an accepted Stage or experiment.

---

## Branch / promotion rule

Case-local success does not promote a mechanism into Catalyst Platform Core.

```text
CASE NEED
→ MINIMUM LOCAL SOLUTION
→ EVIDENCE
→ REVIEW
→ only then possible generalization
```

No merge to `main`, Platform promotion, Runtime change, Candidate admission or next Stage is implied by presence in this directory.

---

## Current immediate boundary

Do not form a new BREA Candidate yet.

The next legitimate decision is still:

```text
F-EXP-03
What is the minimum professional knowledge representation?

A' raw/light representation
vs
B-MIN typed lightweight RegulationUnit
```

Only after that experiment and external review should CASE 01 decide whether F-EXP-01 and the next Candidate architecture are justified.
