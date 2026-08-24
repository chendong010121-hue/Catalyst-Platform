# F-EXP-03 — REPRESENTATION MINIMUM EXPERIMENT V0.1
## FORMAL EXPERIMENT CONTRACT
### A' RAW/LIGHT REPRESENTATION vs B-MIN TYPED REGULATION UNIT

> **Project:** Catalyst  
> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)  
> **Parent Stage:** CASE 01-E / E2  
> **Parent Review:** Scalable Retrieval & Reasoning Architecture Review  
> **Branch:** `case-01`  
> **Review baseline:** `3f7ffca687bb1ba4d1d83367ba027add0fdd03bb`  
> **Frozen product Candidate:** `case-01.brea @ 0.3-candidate` — READ-ONLY  
> **Catalyst main baseline:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **Experiment type:** Case-local architecture falsification experiment  
> **Experiment target:** determine the minimum professional knowledge representation required before the next BREA Candidate architecture is frozen  
> **Experiment Contract:** **ACCEPTED**  
> **Experiment execution:** **NOT AUTHORIZED**  
> **Authorization Record required before execution:** **YES**  
> **v0.4 / next BREA Candidate:** **NOT AUTHORIZED**  
> **E2-C Benchmark:** **NOT AUTHORIZED**  
> **Platform Core / Runtime / RuntimeAdapter / Enterprise mutation:** **FORBIDDEN**  
> **Raw regulation corpus upstream:** **FORBIDDEN**

---

# 0. Experiment Thesis

The current architecture review narrowed the unresolved question to:

```text
A' — refactored deterministic architecture
with raw / lightly annotated regulation units

vs

B-MIN — deterministic architecture
with a typed lightweight RegulationUnit
```

The experiment must NOT begin by assuming that a Regulation IR is necessary.

It must actively attempt to prove the opposite:

> **Can a raw/light representation satisfy the same professional contracts, with the same auditability and without hiding regulation-specific knowledge in code?**

Only if that falsification attempt fails may typed RegulationUnit structure gain architecture evidence.

The decision variable is:

# **HOW MUCH PROFESSIONAL STRUCTURE IS ACTUALLY REQUIRED?**

Not:

```text
Does one option have ingestion while the other does not?
Does one option use a newer technology?
Which option looks more future-proof?
```

---

# 1. Why F-EXP-03 Runs Before F-EXP-01

F-EXP-01 will later test:

```text
unseen supported source
→ source/corpus revision
→ normalization
→ index revision
→ NO Agent behavior-code change
→ NO Domain-schema change
```

But that test is meaningless until Catalyst knows what the selected representation is.

Therefore the sequence is fixed:

```text
F-EXP-03
Representation Minimum

↓ external review

F-EXP-01
Unseen Source / Zero-Agent-Code Growth

↓ external review

Next-Candidate Architecture Freeze
```

F-EXP-03 does NOT prove corpus scalability by itself.

---

# 2. Experiment Question

Primary question:

> **What is the minimum representation that can satisfy BREA's existing professional contracts across representative regulation forms without regulation-family-specific runtime knowledge being hidden in code?**

Secondary questions:

```text
Q-01 Can raw/light evidence units satisfy PC-01..PC-07?
Q-02 If not, exactly which professional semantic structures are missing?
Q-03 Does typed RegulationUnit solve those failures with less hidden knowledge ownership?
Q-04 Which proposed typed fields are actually necessary?
Q-05 Can both approaches add another same-structure rule instance through data only?
Q-06 Which approach gives clearer source → condition → conclusion → numeric derivation trace?
```

---

# 3. Hypotheses and Falsifiers

## H-A — A' IS SUFFICIENT

Working hypothesis:

```text
raw / lightly annotated evidence units
+
generic deterministic / declarative parsing and validators
```

are sufficient.

Evidence that falsifies H-A:

```text
A' cannot satisfy one or more mandatory PC-01..PC-07 contracts
without:
- regulation-family-specific Python branches,
- clause-specific answer mapping,
- hidden semantic values in generic metadata,
- unverifiable numeric derivation,
- or ambiguous applicability state.
```

## H-B — TYPED REGULATION UNIT IS NECESSARY

Working hypothesis:

```text
explicit professional semantic fields are necessary
for the failed contracts.
```

Evidence that falsifies H-B:

```text
A' passes all mandatory professional contracts
with equal or better auditability and no hidden knowledge-specific code.
```

H-B is also weakened if B-MIN contains fields that cannot be tied to an observed A' failure.

## H-MIN — THE PROPOSED B-MIN FIELD SET IS MINIMAL

Evidence that falsifies H-MIN:

```text
one or more typed field groups can be removed
without reducing professional correctness, auditability or data/code separation.
```

The experiment must therefore include field-group ablation for B-MIN.

---

# 4. Controlled Variables — MUST BE THE SAME

The two Tracks must share the same:

```text
source documents
source SHA / provenance
selected regulation examples
raw evidence excerpts
professional expected behavior
project fact inputs
PC-01..PC-07 contract definitions
evaluation harness
result schema
numeric comparison rules
fail-closed rules
```

The following are held OUT of the experiment:

```text
LLM
embeddings
dense retrieval
BM25 comparison
reranking
Vector DB
Web
user upload
multi-Agent behavior
Platform Core
Runtime changes
E2-C Benchmark
```

Retrieval quality is NOT the independent variable in F-EXP-03.

Use exact / controlled evidence loading so representation differences are not confounded by retrieval differences.

---

# 5. Source Boundary

Use only already admitted CASE 01 local professional sources.

Preferred source set:

```text
GB55037-2022
DBJ33T1021-2023
```

Use the existing admitted source references / SHAs.

Raw corpus remains:

```text
LOCAL
READ-ONLY
OUTSIDE GITHUB
```

The experiment may commit only:

```text
source identity
source SHA
locator
small evidence excerpts required for experiment evidence where permitted
normalized lab records
results
code
```

Do not commit full regulation documents.

If admitted local source files cannot be resolved:

```text
STOP — SOURCE EVIDENCE UNAVAILABLE
```

---

# 6. Representative Rule Forms

The experiment must cover at least five regulation forms.

The exact examples must be registered in:

```text
F_EXP_03_CASE_REGISTER_V0.1.md
```

before Track comparison results are generated.

Required forms:

```text
RF-01 DIRECT CLAUSE
single normative clause / direct evidence

RF-02 CONDITIONAL NUMBERED RULE
multiple conditions mapped to different normative outcomes

RF-03 TABLE RULE
row / column / condition-dependent evidence

RF-04 SCOPE + EXCEPTION / EXCLUSION
positive applicability scope plus one or more explicit exclusions

RF-05 DERIVED NUMERIC MODIFIER
source operand + source modifier → derived conclusion
```

The same regulation unit may contribute to more than one form only if the Case Register explains why the behavior remains independently testable.

The selected examples must be grounded in admitted local source evidence.

---

# 7. Professional Contract — PC-01..PC-07

Both Tracks must satisfy the same contracts.

## PC-01 — Positive applicability scope

A normative conclusion must not be produced merely because no exclusion matched.

Positive scope must be established where the source requires it.

## PC-02 — Condition / zone distinction

Materially different professional conditions must not collapse into one generic condition.

Known E2 example:

```text
underground equipment room
!=
other underground area
```

## PC-03 — Applicability responsibility is observable

Professional applicability remains owned / observable through the accepted SEAM-02 responsibility.

Experiment code does not redefine the production Seam; it must demonstrate how the proposed representation would feed an explicit applicability decision boundary.

## PC-04 — Derived numeric trace

A derived numeric conclusion must preserve:

```text
source operand
source modifier / operator
formula
result
source evidence for each normative input
```

Derived numeric must remain distinguishable from source-verbatim numeric.

## PC-05 — Retrieval != Applicability

Finding relevant evidence does not itself authorize a project-specific normative conclusion.

## PC-06 — Unsupported numeric fail closed

No numeric conclusion may appear unless it is source-supported or explicitly derived from source-supported operands / modifiers.

## PC-07 — No reliable evidence fail closed

If evidence or applicability cannot be established:

```text
NO normative conclusion
```

---

# 8. Track A' — Raw / Light Representation

Track A' represents the strongest fair version of the "less structure" alternative.

It MAY use a stable generic Evidence Unit such as:

```text
EvidenceUnit {
  source_id
  edition / effective status
  jurisdiction
  unit_type
  locator
  raw_evidence
  source_sha256
  generic non-semantic metadata
}
```

It may use generic deterministic parsing / declarative validator machinery.

It MAY NOT persist typed professional semantic fields equivalent to B-MIN under generic names.

Forbidden hidden equivalents include storing, inside arbitrary metadata:

```text
scope_conditions
exceptions
condition → value maps
numeric_operands
numeric_modifiers
derivation formulas
```

and then claiming the Track is "raw/light".

Track A' is allowed to derive semantics at evaluation / applicability time from raw evidence only if the mechanism is generic and not clause-family-specific.

Forbidden:

```text
if locator == "4.3.16": ...
if question contains "防火分区": fixed branch
hardcoded 1500/2500/1000/500 as family knowledge in code
family-specific extraction function per regulation example
```

---

# 9. Track B-MIN — Typed Lightweight RegulationUnit

Track B-MIN may use explicit professional semantic structure.

Initial candidate structure may include:

```text
RegulationUnit {
  source_id
  edition / effective_status
  jurisdiction
  unit_type
  locator
  subject
  scope_conditions
  exceptions
  conditions
  numeric_operands
  numeric_modifiers
  derivation_trace
  raw_evidence
  source_sha256
}
```

This is a starting hypothesis, not a frozen schema.

The experiment must prove why each semantic field group is needed.

---

# 10. B-MIN Field-Group Ablation

At minimum evaluate these groups independently:

```text
G-BASE
source identity / version / locator / raw evidence

G-SCOPE
subject / positive scope / exceptions

G-CONDITION
condition → outcome / value structure

G-NUMERIC
numeric operands / modifiers / derivation trace
```

For each group record:

```text
which PC contract requires it
what fails if the group is absent
whether the same behavior can be achieved generically in A'
```

A field group that has no observed contract consequence must be:

```text
REMOVE
or
DEFER
```

Do not keep fields because they may be useful someday.

---

# 11. Shared Experiment Harness

Implement one shared lab harness under the experiment directory.

Conceptual flow:

```text
REGISTERED SOURCE EVIDENCE
        ↓
TRACK REPRESENTATION ADAPTER
        ↓
SHARED PROFESSIONAL INPUT
        ↓
SHARED APPLICABILITY / VALIDATION INTERFACE
        ↓
SHARED RESULT CONTRACT
        ↓
PC-01..PC-07 ASSERTIONS
```

Track-specific code may only implement representation-specific adaptation.

The evaluation / assertions must be shared.

If Track A and Track B use different professional acceptance logic:

```text
EXPERIMENT INVALID
```

---

# 12. Result Contract

Each evaluated case must produce a comparable structured result containing at least:

```text
track
case_id
rule_form
source_id
source_revision
locator
applicability_status
missing_facts
scope_evidence
condition_evidence
raw_evidence
source_numeric
source_modifier
derived_numeric
derivation_trace
citation_status
fail_closed_status
pc_contract_results
knowledge_specific_code_refs
```

Not every field must be populated for every rule form.

Missing fields must be explicit, not silently omitted.

---

# 13. Anti-Cheating / Hidden Knowledge Review

Create:

```text
F_EXP_03_HIDDEN_KNOWLEDGE_REVIEW_V0.1.md
```

Inspect both Tracks for:

```text
clause-number-specific branches
source-specific value constants
question-string mappings
professional semantics hidden in generic metadata
professional semantics hidden in test fixtures but consumed as runtime truth
Track-specific Gold logic
```

Classify every knowledge-bearing artifact as:

```text
SOURCE EVIDENCE
NORMALIZED DATA
REPRESENTATION SCHEMA
GENERIC MECHANISM
PROFESSIONAL CONTRACT / GOLD
HIDDEN CODE KNOWLEDGE — FAIL
```

---

# 14. Same-Structure Data-Only Extension Probe

F-EXP-03 does not replace the later unseen-source experiment.

But it must include one smaller intra-corpus extension probe.

After each Track's generic mechanism is stable:

```text
add one additional SAME-STRUCTURE rule instance
from an already admitted source
```

Allowed changes:

```text
data / normalized record
case registration
```

Target:

```text
NO generic mechanism code change
NO schema change
```

This is not proof of unseen-source scalability.

It is only a check that the representation can absorb another instance of an already supported structure.

---

# 15. Mandatory Evaluation Dimensions

Do not decide based on pass/fail alone.

Evaluate both Tracks on:

```text
D-01 Professional correctness — PC-01..PC-07
D-02 Auditability — source → condition → conclusion trace
D-03 Numeric traceability
D-04 Fail-closed clarity
D-05 Hidden-knowledge risk
D-06 Knowledge-specific code surface
D-07 Representation complexity
D-08 Generic mechanism stability
D-09 Same-structure data-only extension
D-10 Replacement clarity / inspectability
```

---

# 16. Knowledge-Specific Code Surface Metric

For each Track record:

```text
number of generic mechanism files
number of professional-family-specific code files
number of clause/source-specific branches
number of regulation values embedded in code
number of schema / data artifacts
files changed for same-structure extension probe
```

The goal is not the fewest lines of code.

The goal is:

```text
professional knowledge
is data/evidence/contract
rather than hidden implementation behavior.
```

---

# 17. Representation Complexity Metric

For each Track record:

```text
number of required representation fields
number of typed professional semantic concepts
number of record types
number of mandatory transformations
number of contract-specific derived fields
```

Complexity is justified only when it produces an observable professional / auditability benefit.

---

# 18. Decision Rules

## VERDICT A — A_PRIME_SUFFICIENT

Use only if:

```text
A' passes ALL mandatory PC-01..PC-07 cases
AND
A' contains no hidden professional knowledge in code / generic metadata
AND
same-structure extension requires data only
AND
source / numeric / applicability audit trail is complete
AND
B-MIN adds no material contract or auditability benefit that A' cannot provide generically
```

Consequence:

```text
prefer the smaller A' representation
RegulationUnit necessity FALSIFIED / narrowed
```

## VERDICT B — B_MIN_EVIDENCED

Use only if:

```text
A' fails one or more mandatory professional contracts
for representation reasons
AND
B-MIN passes those same contracts
AND
failure cannot be repaired in A' without hiding family-specific semantics in code / metadata
AND
retained B-MIN field groups map to observed failures
AND
field-group ablation removes unnecessary structure
```

Consequence:

```text
lightweight typed RegulationUnit gains CASE evidence
```

## VERDICT C — BOTH_INSUFFICIENT

Use if:

```text
both Tracks fail mandatory contracts
or
both require family-specific knowledge in code
```

Consequence:

```text
no next-Candidate architecture freeze
return to architecture review
```

## VERDICT D — INCONCLUSIVE

Use if:

```text
both Tracks pass
but hidden complexity / auditability tradeoff cannot be distinguished fairly
```

Consequence:

```text
request one smaller follow-up experiment
```

## VERDICT E — EXPERIMENT_INVALID

Use if controlled variables diverge or the comparison is contaminated.

---

# 19. Mandatory Safety Rule

A representation may not win by weakening the professional contract.

If either Track passes only because it:

```text
drops positive applicability
ignores exclusion semantics
suppresses numeric derivation trace
collapses Retrieval into Applicability
allows unsupported numeric
returns uncertain normative conclusions
```

then that Track FAILS regardless of implementation simplicity.

---

# 20. Experiment-Local Code Boundary

All implementation must remain under:

```text
case-01/01-e-governed-agent-professional-completion/
e2-local-professional-coverage-expansion/
scalability-review/experiments/f-exp-03-representation-minimum/**
```

It is LAB CODE.

It is not:

```text
BREA v0.4
BREA Candidate source
Platform code
Domain package production code
Runtime code
Reusable Catalyst capability
```

No experiment artifact is promoted automatically.

---

# 21. Protected Repository Boundaries

The experiment may READ:

```text
v0.1 / v0.2 / frozen v0.3
E1 / E2 evidence
accepted BREA Governed Definition
existing local corpus reference metadata
accepted Method
scalability Review artifacts
```

The experiment may NOT WRITE:

```text
v0.1
v0.2
v0.3
01-B / 01-C / 01-D / E1 accepted evidence
Platform Standard / Core
Runtime / RuntimeAdapter
Enterprise extensions
main
raw local regulation corpus
E2-C evaluation / benchmark
```

---

# 22. No Retrieval / LLM Architecture Expansion

F-EXP-03 may not introduce:

```text
BM25 as a required replacement
Dense retrieval
Embeddings
Vector DB
Reranking
LLM
Agent loop changes
Web
Upload
```

If Track performance appears to require one of these:

```text
record the blocker
STOP
```

Do not turn F-EXP-03 into F-EXP-02 or F-EXP-04.

---

# 23. Required Experiment Artifacts

Expected package after authorized execution:

```text
experiments/f-exp-03-representation-minimum/

  F_EXP_03_REPRESENTATION_MINIMUM_V0.1_EXPERIMENT_CONTRACT.md
  F_EXP_03_AUTHORIZATION_RECORD_V0.1.yaml

  design/
    F_EXP_03_CASE_REGISTER_V0.1.md
    F_EXP_03_TRACK_A_PRIME_DESIGN_V0.1.md
    F_EXP_03_TRACK_B_MIN_DESIGN_V0.1.md
    F_EXP_03_SHARED_EVALUATION_CONTRACT_V0.1.md

  lab/
    shared/**
    track-a-prime/**
    track-b-min/**

  results/
    F_EXP_03_RESULTS_V0.1.json
    F_EXP_03_RESULTS_V0.1.md
    F_EXP_03_FIELD_ABLATION_RESULTS_V0.1.md
    F_EXP_03_SAME_STRUCTURE_EXTENSION_RESULTS_V0.1.md

  evidence/
    F_EXP_03_SOURCE_REFERENCE_V0.1.md
    F_EXP_03_HIDDEN_KNOWLEDGE_REVIEW_V0.1.md
    F_EXP_03_CODE_SURFACE_COMPARISON_V0.1.md
    F_EXP_03_REPRESENTATION_COMPLEXITY_V0.1.md
    F_EXP_03_REPOSITORY_INTEGRITY_V0.1.md
    F_EXP_03_EVIDENCE_INDEX_V0.1.md

  review/
    F_EXP_03_EXPERIMENT_REPORT_V0.1.md
    F_EXP_03_ARCHITECTURE_DECISION_CANDIDATE_V0.1.md
```

---

# 24. Authorization Gate — REQUIRED BEFORE ANY EXECUTION

No experiment execution may begin until a declarative authorization record exists at:

```text
F_EXP_03_AUTHORIZATION_RECORD_V0.1.yaml
```

The record must state at minimum:

```text
user decision = granted
experiment = F-EXP-03 only
lab code allowed = true
read-only admitted corpus use = true
raw corpus commit = false
Candidate mutation = false
v0.4 formation = false
E2-C benchmark = false
Platform / Runtime / main mutation = false
publication commit/push limit
```

The authorization record must be declarative facts, not an imperative second prompt.

---

# 25. Suggested Publication Boundary

Recommended execution authorization should allow:

```text
ONE experiment implementation+evidence commit
+
ONE push to case-01
```

After push:

```text
STOP
→ ChatGPT F-EXP-03 External Experiment Review
```

No architecture selection becomes final merely because DeepSeek reports a winner.

---

# 26. Stop Conditions

STOP if any occur:

```text
S-01 source evidence cannot be resolved
S-02 A' and B use different professional Gold / acceptance logic
S-03 one Track receives stronger source evidence than the other
S-04 Track A hides typed semantics in generic metadata
S-05 Track B retains unproven schema fields without ablation
S-06 family-specific / clause-specific runtime knowledge is required
S-07 raw corpus must be committed
S-08 Candidate source must be modified
S-09 Platform / Runtime change appears necessary
S-10 retrieval / LLM expansion becomes required to continue
S-11 E2-C benchmark is created
S-12 authorization record is missing
S-13 main changes
```

On STOP:

```text
preserve evidence
report the smallest blocker
no repair outside experiment scope
```

---

# 27. DeepSeek Final Report Shape

After authorized execution, report:

```text
F-EXP-03 STATUS
READY FOR EXTERNAL EXPERIMENT REVIEW / BLOCKED / INVALID

CASE-01 HEAD INPUT
<sha>

AUTHORIZATION REF
<file / commit>

SOURCE SET
<ids / SHAs>

RULE FORMS
RF-01..RF-05

TRACK A'
PC-01..07: <result>
HIDDEN KNOWLEDGE: PASS / FAIL
SAME-STRUCTURE EXTENSION: PASS / FAIL

TRACK B-MIN
PC-01..07: <result>
FIELD ABLATION: <summary>
HIDDEN KNOWLEDGE: PASS / FAIL
SAME-STRUCTURE EXTENSION: PASS / FAIL

KNOWLEDGE-SPECIFIC CODE SURFACE
A': <summary>
B:  <summary>

REPRESENTATION COMPLEXITY
A': <summary>
B:  <summary>

EXPERIMENT VERDICT CANDIDATE
A_PRIME_SUFFICIENT /
B_MIN_EVIDENCED /
BOTH_INSUFFICIENT /
INCONCLUSIVE /
EXPERIMENT_INVALID

RAW CORPUS COMMITTED
NO / YES

CANDIDATE MUTATION
NO / YES

PLATFORM / RUNTIME CHANGE
NO / YES

E2-C BENCHMARK
NOT CREATED / CREATED

EXPERIMENT COMMIT
<sha>

MAIN
UNCHANGED / CHANGED

FINAL
READY FOR F-EXP-03 EXTERNAL EXPERIMENT REVIEW
```

STOP.

---

# 28. What F-EXP-03 May Legitimately Decide

F-EXP-03 may provide evidence for:

```text
minimum representation depth
A' sufficiency
B-MIN necessity
field-group necessity
professional-contract expressiveness
knowledge/code separation
```

It may NOT decide:

```text
LLM architecture
Dense retrieval
Vector DB
Web architecture
full ingestion architecture
unseen-source scalability
v0.4 implementation
E2-C admission / benchmark
Platform promotion
```

---

# 29. Current State After This Contract

```text
SCALABILITY REVIEW
EVIDENCE-BACKED PARTIAL PASS

A' vs B-MIN
UNRESOLVED

F-EXP-03 CONTRACT
ACCEPTED

F-EXP-03 EXECUTION
NOT AUTHORIZED

F-EXP-01
WAITING FOR F-EXP-03 RESULT

v0.4
NOT AUTHORIZED

E2-C
NOT AUTHORIZED

Platform / Runtime / main
UNCHANGED
```

# **F-EXP-03 CONTRACT VERDICT — ACCEPTED / READY FOR EXPLICIT EXPERIMENT AUTHORIZATION**
