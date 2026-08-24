# BREA SCALABLE RETRIEVAL & REASONING ARCHITECTURE REVIEW V0.1
## FORMAL REVIEW CONTRACT / STAGE DESIGN
### FALSIFICATION-FIRST · PRODUCT ENVELOPE · SCALE INVARIANT · KNOWLEDGE / REASONING / VERIFICATION SEPARATION

> **Project:** Catalyst  
> **Case:** CASE 01 — Building Regulation Evidence Agent (BREA)  
> **Parent Stage:** CASE 01-E / E2 — Local Professional Coverage Expansion  
> **Branch:** `case-01`  
> **Current case-01 baseline:** `57a1b30c46ac917f2937abe824b55a8782ee7b85`  
> **Frozen Candidate under review context:** `case-01.brea @ 0.3-candidate`  
> **v0.3 Candidate tree SHA256:** `37bb4864a9dd39812d9d77c24bb48d9b7abe2403c2ed6f4df31d2e7db847fa7b`  
> **Accepted Development Method:** `CATALYST_GOVERNED_AGENT_CONSTRUCTION_METHOD_V0.1_ACCEPTED`  
> **Catalyst main baseline:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **Input diagnosis:** `CASE 01 / BREA 可扩展规范查询架构问题诊断与外部机制调研报告 V0.2` — REVIEW CANDIDATE  
> **Review authority / external reviewer:** ChatGPT  
> **Research / evidence executor:** DeepSeek  
> **Product / Stage authority:** User  
> **Document type:** Architecture / Mechanism Review Contract inside E2  
> **Implementation authorization:** **NO**  
> **v0.4 Candidate authorization:** **NO**  
> **E2-C Benchmark authorization:** **NO**  
> **Platform Core / Runtime change:** **FORBIDDEN**  
> **Goal:** determine whether the current scalability diagnosis is actually true by actively trying to disprove it before selecting the next BREA architecture.

---

# 0. Review Thesis

This Review must not begin from:

```text
RAG is modern
→ therefore BREA should use RAG

LLM understands language
→ therefore BREA should use LLM reasoning

v0.3 has rule defects
→ therefore deterministic architecture is wrong
```

The Review begins from the opposite question:

# **What evidence would prove that our current conclusion is wrong?**

Current working diagnosis:

```text
BREA is an OPEN KNOWLEDGE / OPEN QUERY product.

Normal corpus growth should not require proportional Agent code growth.

The current family-specific professional-rule expansion pattern may not scale.

Ingestion / indexing / scalable retrieval are likely required.

LLM + RAG are mechanism candidates, not predetermined architecture.
```

This Review accepts the diagnosis only if serious falsification attempts fail.

---

# 1. Why This Review Exists

E1 proved:

```text
Evidence Retrieval
must not remain fixture-specific.
```

E2 v0.3 then exposed a deeper possibility:

```text
Professional Reasoning
may still remain family-specific.
```

The v0.3 Freeze Review also found concrete professional defects:

```text
public-building positive applicability incomplete
underground equipment-room vs other-area distinction incomplete
SEAM-02 implementation ownership mismatch
derived-numeric contract mismatch
```

Those findings remain valid.

But they do not by themselves prove that:

```text
LLM is required
RAG is required
vector retrieval is required
Regulation IR is required
current deterministic reasoning must be abandoned
```

Therefore the next legitimate activity is an architecture/mechanism Review, not an immediate v0.4 implementation.

---

# 2. Stage Placement

This is **not E3** and not a new top-level product stage.

It is an architecture/mechanism interruption inside:

```text
CASE 01-E / E2
```

because E2 Candidate Freeze exposed evidence that the chosen implementation-expansion model itself may be structurally wrong.

Current state:

```text
BREA v0.3
FROZEN
NOT ADMITTED
NOT BOUND

E2-C
PAUSED / NOT AUTHORIZED

v0.4
NOT AUTHORIZED

CURRENT ACTIVITY
SCALABLE RETRIEVAL & REASONING ARCHITECTURE REVIEW
```

The Review may change the design of the next Candidate.
It may not mutate historical Candidates.

---

# 3. Falsification Rule

Every major proposed conclusion must be written as:

```text
HYPOTHESIS

WHY WE CURRENTLY SUSPECT IT

WHAT EVIDENCE WOULD DISPROVE IT

TEST / ANALYSIS

RESULT

STATUS:
FALSIFIED
NOT FALSIFIED
PARTIALLY FALSIFIED
INSUFFICIENT EVIDENCE
```

Forbidden review behavior:

```text
collecting only evidence that supports RAG
collecting only examples where LLM performs well
using popularity as architecture proof
calling a technology necessary because external frameworks use it
using benchmark success on known cases as scalability proof
```

A hypothesis that cannot state a plausible falsifier is not yet suitable for architecture decision.

---

# 4. Primary Hypotheses Under Review

## H-01 — OPEN PRODUCT CLASSIFICATION

Working hypothesis:

```text
BREA is naturally an OPEN KNOWLEDGE / OPEN QUERY product.
```

Evidence that would falsify H-01:

```text
credible product boundary showing:
- finite / closed document set,
- finite / controlled question families,
- no meaningful user-upload requirement,
- no meaningful future local-standard growth,
- no meaningful controlled-Web requirement,
- no requirement for open natural-language paraphrase.
```

If such a boundary is real and accepted by Product Authority:

```text
OPEN-product architecture may be unnecessary.
```

---

## H-02 — CORPUS GROWTH SHOULD NOT REQUIRE PROPORTIONAL CODE GROWTH

Working hypothesis:

```text
ordinary new regulations should enter through data ingestion / index revision,
not per-document Agent code changes.
```

Evidence that would falsify H-02:

```text
representative ordinary regulations repeatedly introduce genuinely new professional primitives
such that per-source code is unavoidable even after reasonable schema / data abstraction.
```

Important qualifier:

```text
new document structure
new reasoning primitive
new source-authority semantic
new high-risk validation requirement

may legitimately require Candidate / schema change.
```

The target invariant is not "zero code forever".

---

## H-03 — CURRENT FAMILY-SPECIFIC DETERMINISTIC REASONING DOES NOT SCALE

Working hypothesis:

```text
question family
→ new facts
→ new parser
→ new applicability branch
→ new runner dispatch
```

is not a sufficient long-term architecture.

Evidence that would falsify H-03:

```text
current or minimally refactored deterministic architecture can represent
multiple materially different regulation families primarily as declarative data/config,
while reusable generic code remains stable.
```

A successful falsifier may prove:

```text
DETERMINISTIC IS FINE
but
KNOWLEDGE MUST MOVE OUT OF CODE.
```

This is an acceptable Review outcome.

---

## H-04 — SCALABLE INGESTION / INDEXING IS REQUIRED

Working hypothesis:

```text
BREA needs a stable path:
Document
→ Parse/OCR
→ Normalize
→ Structured Units / Metadata
→ Index
→ Queryable
```

Evidence that would falsify H-04:

```text
credible product scope remains so small / static that direct corpus parsing
provides the same maintainability and user-upload / update cost with lower complexity.
```

Do not call an ingestion subsystem necessary merely because RAG frameworks contain one.

---

## H-05 — HYBRID RETRIEVAL IS A STRONGER LONG-TERM FIT THAN SINGLE-MODE RETRIEVAL

Working hypothesis:

```text
exact locator + lexical/BM25 + metadata + optional dense semantic retrieval
```

is likely a better fit than a single retrieval mode.

Evidence that would falsify or narrow H-05:

```text
exact + lexical/BM25 + metadata retrieval reaches the required recall/precision
for representative paraphrase and locator workloads,
with dense retrieval adding no material benefit or unacceptable risk/cost.
```

Possible valid outcome:

```text
NO DENSE RETRIEVAL YET.
```

---

## H-06 — LLM IS NEEDED FOR SOME OPEN-LANGUAGE / REASONING RESPONSIBILITIES

Working hypothesis:

```text
LLM may be useful for:
question understanding
fact extraction
query rewriting/decomposition
candidate applicability reasoning
cross-clause synthesis
answer composition
```

Evidence that would falsify H-06 for a responsibility:

```text
a deterministic / schema-driven method achieves the required coverage,
accuracy, maintainability and paraphrase robustness at materially lower risk/cost.
```

LLM necessity must be decided **per responsibility**, not globally.

Allowed outcome:

```text
LLM for query understanding only
NO LLM for normative applicability conclusion
```

or any other evidence-backed partition.

---

## H-07 — REGULATION INTERMEDIATE REPRESENTATION / DATA MODEL IS REQUIRED

Working hypothesis:

```text
raw text chunks alone may be insufficient for robust professional applicability,
numeric derivation, exclusions, versioning and provenance.
```

Potential Regulation IR concepts:

```text
source identity
edition / effective status
jurisdiction
unit type
locator
subject / control item
conditions
exceptions
normative operator
numeric operands
units
modifiers
table coordinates
cross references
raw evidence
source SHA
```

Evidence that would falsify H-07:

```text
raw chunks + metadata + reasoning/verification can robustly satisfy
professional applicability / numeric / provenance contracts across representative rule forms
without introducing hidden unstructured knowledge ownership.
```

Do not create a large ontology merely because structured data is attractive.

---

## H-08 — DETERMINISTIC LOGIC SHOULD MOVE TOWARD CONTRACT / VALIDATOR ROLE

Working hypothesis:

```text
knowledge-specific Python branches should decrease,
while deterministic invariant enforcement remains strong.
```

Candidate deterministic responsibilities:

```text
source identity
version / effective status
mandatory-fact completeness
evidence existence
unsupported numeric prevention
derived numeric trace
known high-risk exclusions
citation binding
provenance
fail-closed
```

Evidence that would falsify H-08:

```text
a more declarative or generative verification approach provides equivalent or stronger
safety, auditability and replacement semantics without hidden normative inference.
```

Safety-critical invariants must not be removed merely for architectural elegance.

---

# 5. Required Product Capability Envelope Review

Create:

```text
review/PCE_BREA_PRODUCT_CAPABILITY_ENVELOPE_V0.1.md
```

It must explicitly classify BREA along:

```text
Knowledge Space        CLOSED / OPEN
Query Space            FIXED / OPEN NATURAL LANGUAGE
Source Space           FIXED LOCAL / LOCAL + USER / CONTROLLED WEB
Corpus Growth          LOW / MEDIUM / HIGH
Document Formats       stable / heterogeneous
User Upload            natural / exceptional / not required
Web Supplement         product requirement / optional / rejected
Cross-document Need    low / medium / high
Professional Risk      low / medium / high
Numeric Risk           low / medium / high
Version / authority    simple / complex
```

For every `OPEN / HIGH / COMPLEX` classification:

```text
evidence source required.
```

The review must actively look for evidence that the product envelope is smaller than currently assumed.

---

# 6. Required Scale Invariant Contract

Create:

```text
review/BREA_SCALE_INVARIANT_V0.1.md
```

Define two classes.

## NORMAL KNOWLEDGE GROWTH

Examples:

```text
ordinary new regulation
new local edition of a known source class
new version of an already supported regulation form
new clauses / tables in supported structures
user upload of supported document type
new natural-language paraphrase
```

Desired default cost:

```text
data/source admission
→ ingest
→ normalize
→ index update
→ evaluation
```

Normally:

```text
NO Agent code change
NO model retraining
```

## STRUCTURAL CAPABILITY GROWTH

Examples:

```text
new document structure
new semantic primitive
new professional reasoning primitive
new authority/conflict semantics
new verification obligation
new high-risk safety contract
```

Allowed cost:

```text
Domain Schema change
Capability change
Candidate N+1
Governance review
```

The Review must determine whether this distinction is actually achievable for BREA.

---

# 7. Change-Cost Classification

Create:

```text
review/BREA_CHANGE_COST_CLASSIFICATION_V0.1.md
```

For each future change type classify expected owner:

```text
DATA / CORPUS REVISION
INDEX REVISION
DOMAIN SCHEMA REVISION
CONFIG REVISION
PRIVATE HOW CHANGE
GOVERNED SEAM CHANGE
AGENT CANDIDATE CHANGE
PLATFORM CONTRACT REVIEW
```

Required cases:

```text
add ordinary regulation
replace regulation with new edition
add local standard
upload temporary PDF
new table shape
new appendix structure
new applicability reasoning type
new numeric modifier type
new source-authority conflict
controlled Web supplement
new natural-language paraphrase
```

A strong architecture minimizes unnecessary movement to the right side of this list.

---

# 8. Knowledge / Reasoning / Verification Analysis Planes

For Review purposes only, analyze the product in three responsibility planes.

These are **not new Catalyst Platform layers**.

## KNOWLEDGE PLANE

```text
Source Acquisition
→ Admission
→ Ingestion
→ Parse/OCR
→ Normalize
→ Regulation Unit / Chunk / Metadata
→ Index
→ Retrieval / Rerank
```

Question:

> Can knowledge grow without proportional Agent code growth?

## REASONING PLANE

```text
Question Understanding
→ Project Fact Extraction
→ Professional Issue Classification
→ Retrieval Constraints
→ Applicability Reasoning
→ Cross-clause / Cross-source Composition
→ Candidate Conclusion
```

Question:

> Can reasoning generalize beyond pre-coded question families without surrendering professional contracts?

## VERIFICATION PLANE

```text
Source Authority
Version / Effective Status
Evidence Existence
Applicability Preconditions
Numeric Support
Derived Numeric Trace
Exclusions / Conflicts
Citation / Provenance
Fail Closed
```

Question:

> Can open retrieval/reasoning be safely bounded by deterministic or otherwise auditable verification?

---

# 9. Architecture Alternatives — All Must Be Seriously Considered

The Review must compare at least these four alternatives.

## A — CURRENT / REFACTORED DETERMINISTIC

```text
generic parser
+ declarative rules/config
+ lexical retrieval
+ deterministic applicability / verification
```

Architecture thesis:

> Current direction was not wrong; knowledge was simply placed in Python instead of data/schema.

## B — STRUCTURED KNOWLEDGE + DETERMINISTIC REASONING

```text
ingestion
+ Regulation IR / structured data
+ exact/BM25/metadata retrieval
+ generic deterministic rule engine
+ deterministic verification
```

No LLM required for normative reasoning.

## C — HYBRID RETRIEVAL + BOUNDED LLM UNDERSTANDING

```text
ingestion
+ exact/BM25/metadata/dense as justified
+ LLM for language/fact/query understanding
+ structured applicability engine / validators
+ deterministic professional verification
```

## D — HYBRID RETRIEVAL + LLM-ASSISTED PROFESSIONAL REASONING

```text
ingestion
+ hybrid retrieval
+ structured professional facts / Regulation data
+ LLM-assisted applicability / synthesis
+ strong evidence / numeric / authority verification
+ fail-closed gates
```

The Review must not presume D is more mature than A/B/C.

---

# 10. Architecture Option Evaluation Criteria

Create:

```text
review/BREA_ARCHITECTURE_OPTION_COMPARISON_V0.1.md
```

Evaluate A/B/C/D on:

```text
ordinary corpus growth cost
new regulation code-change frequency
open natural-language robustness
exact-locator precision
semantic paraphrase recall
professional applicability accuracy
numeric safety
source/version authority
cross-clause reasoning
explainability
citation/provenance
fail-closed quality
user-upload compatibility
controlled-Web compatibility
offline operation
operational complexity
provider dependency
replaceability
benchmarkability
Case-local implementation cost
```

Score alone is insufficient.
Each major score requires evidence / reasoning.

---

# 11. Falsification Experiments / Spikes

If execution is later authorized, research spikes may be created only under this Review directory.

They are **not BREA Candidates** and must not mutate v0.3.

Recommended experiments:

## F-EXP-01 — UNSEEN DOCUMENT INGESTION

Question:

> Can a regulation not represented by Agent-specific Python become queryable through only source/ingestion/index work?

Use one or more non-production / lab sources with recorded provenance.

Measure:

```text
Agent source files changed?
Domain schema changed?
index only?
exact citation possible?
```

This experiment attempts to falsify:

```text
Corpus Growth = Code Growth risk.
```

## F-EXP-02 — LEXICAL vs SEMANTIC RETRIEVAL

Compare:

```text
exact locator
BM25 / lexical
metadata filtering
optional dense semantic retrieval
```

Use paraphrases not hand-authored into Candidate runtime logic.

If lexical + metadata is sufficient:

```text
dense retrieval is NOT justified yet.
```

## F-EXP-03 — RAW CHUNK vs REGULATION IR

Take representative:

```text
direct clause
conditional numbered rule
table rule
exception / exclusion
derived numeric modifier
```

Test whether raw chunks + metadata can support the required contracts.

If yes:

```text
large IR may be unnecessary.
```

If no:

identify the **minimum** structured representation required.

## F-EXP-04 — DETERMINISTIC vs LLM RESPONSIBILITY

For responsibilities such as:

```text
question intent
fact extraction
query decomposition
applicability candidate reasoning
```

compare deterministic/schema-based and LLM-assisted approaches.

The goal is not overall winner.
The goal is per-responsibility placement.

---

# 12. Professional Contract Preservation

The v0.3 Freeze findings become mandatory architecture-test contracts.

Regardless of A/B/C/D, the future architecture must prove it can prevent:

```text
PC-01
non-public building
→ public-building §4.3.16 conclusion forbidden

PC-02
underground equipment room
!= underground other area

PC-03
Applicability
→ must remain owned / observable through SEAM-02 responsibility

PC-04
Derived numeric
→ source operands + source modifier + explicit derivation trace

PC-05
Evidence Retrieval
!= Applicability

PC-06
unsupported numeric
→ fail closed

PC-07
no reliable evidence
→ fail closed
```

These findings should become:

```text
Professional Contract
+ Gold / Regression Cases
+ Validator requirements
```

They must not automatically become more special-purpose runtime branches.

---

# 13. Regulation Data Model / IR Decision

Create:

```text
review/BREA_REGULATION_DATA_MODEL_DECISION_V0.1.md
```

The Review must answer:

```text
Do we need only chunks + metadata?
Do we need a lightweight RegulationUnit?
Do we need structured Condition / Exception / Numeric fields?
Which structures are universal enough to justify schema?
Which structures should remain extracted on demand?
```

Default principle:

```text
MINIMUM STRUCTURE THAT SUPPORTS THE CONTRACT.
```

Forbidden:

```text
building a universal regulation ontology before Case evidence.
```

---

# 14. Retrieval Architecture Decision

Create:

```text
review/BREA_RETRIEVAL_ARCHITECTURE_DECISION_V0.1.md
```

Decide separately:

```text
Exact locator retrieval
Lexical / BM25 retrieval
Metadata filter
Dense semantic retrieval
Reranking
Cross-document retrieval
```

For each:

```text
REQUIRED NOW
OPTIONAL UPGRADE
DEFER
REJECT
```

No Vector DB product/provider decision is allowed in this Review.

---

# 15. Reasoning Architecture Decision

Create:

```text
review/BREA_REASONING_ARCHITECTURE_DECISION_V0.1.md
```

For each responsibility classify preferred mechanism:

```text
DETERMINISTIC
DECLARATIVE / SCHEMA
LLM-ASSISTED
HUMAN REVIEW
COMPOSED
```

Required responsibilities:

```text
question understanding
professional fact extraction
missing-fact detection
query rewriting
source selection
applicability candidate generation
applicability final decision
cross-clause synthesis
numeric derivation
answer composition
```

LLM must not silently become authority for:

```text
source existence
source version
unsupported numeric
final authority classification
citation binding
```

unless an equally auditable control is demonstrated.

---

# 16. Verification Architecture Decision

Create:

```text
review/BREA_VERIFICATION_ARCHITECTURE_DECISION_V0.1.md
```

Required invariants:

```text
source identity
source version / effective status
evidence existence
verbatim / bounded citation relationship
required project facts
professional applicability preconditions
numeric source support
derived numeric trace
explicit exclusions
source conflict / authority uncertainty
local vs web evidence distinction
provenance
fail closed
```

For each invariant determine:

```text
where it is enforced
what evidence proves enforcement
what happens on uncertainty
how it is tested
```

---

# 17. Agent Evolution vs Knowledge Evolution

Create:

```text
review/BREA_VERSION_AND_REVISION_MODEL_V0.1.md
```

At minimum distinguish conceptually:

```text
AGENT VERSION
behavior / code / reasoning capability

CORPUS REVISION
which source documents / editions are admitted

INDEX REVISION
retrieval representation of a corpus revision

DOMAIN SCHEMA VERSION
Regulation data / professional fact / contract structure

EVALUATION VERSION
benchmark / gold / evaluation contract revision
```

The Review must define examples where:

```text
Corpus revision changes
without Agent version change
```

and examples where:

```text
Candidate N+1 is legitimately required.
```

Key principle under review:

# **Agent Evolution != Knowledge Evolution**

---

# 18. User Upload and Controlled Web — Design Boundary Only

The Review must preserve these as long-term product change axes if supported by Product evidence.

## USER UPLOAD

Potential future path:

```text
Upload
→ Ephemeral User Corpus
→ Parse/OCR
→ Index Namespace
→ Query
→ Citation to uploaded source
```

Default:

```text
NOT authoritative organizational corpus
NOT permanent asset
```

## CONTROLLED WEB

Potential future path:

```text
LOCAL FIRST
→ insufficient local evidence
→ Web discovery
→ source trust / authority review
→ scrape / normalize
→ temporary supplementary evidence
→ reasoning / verification
→ LOCAL vs WEB SUPPLEMENT label + URL
```

This Review may define contracts.
It may not implement Web or Upload.

---

# 19. External Mechanism Research Discipline

The Review may use external systems as evidence sources.

At minimum preserve the already surfaced families:

```text
Penguin Harness
RAGFlow
LlamaIndex
Haystack
```

For every materially used mechanism record:

```text
repository / official source
version / commit / date where available
source file / documentation
mechanism learned
assumptions
what is deliberately NOT inherited
```

External framework popularity is not architecture evidence.

External README / Skill / code remains:

```text
research evidence
!= Catalyst authority
!= implementation authorization
```

---

# 20. Method Amendment Candidate — P-00 Scale Judgment

The Review may propose, but may not permanently modify the accepted Method, a lightweight conditional gate:

```text
P-00 PRODUCT CAPABILITY ENVELOPE / SCALE JUDGMENT
```

Possible trigger questions:

```text
open knowledge?
open natural-language query?
dynamic source growth?
user-upload natural?
controlled Web natural?
semantic paraphrase heavy?
high corpus growth?
```

If all materially NO:

```text
normal P-01
```

If one or more materially YES:

```text
Scale Invariant
+ Change-Cost Classification
+ Mechanism Pattern Selection
→ then P-01
```

The Review must actively test whether P-00 adds enough decision quality to justify Method amendment.

Method amendment is not automatic.

---

# 21. Required Review Deliverables

Expected review package:

```text
scalability-review/
  BREA_SCALABLE_RETRIEVAL_AND_REASONING_ARCHITECTURE_REVIEW_V0.1_REVIEW_CONTRACT.md

  review/
    FALSIFICATION_LEDGER_V0.1.md
    PCE_BREA_PRODUCT_CAPABILITY_ENVELOPE_V0.1.md
    BREA_SCALE_INVARIANT_V0.1.md
    BREA_CHANGE_COST_CLASSIFICATION_V0.1.md
    BREA_ARCHITECTURE_OPTION_COMPARISON_V0.1.md
    BREA_REGULATION_DATA_MODEL_DECISION_V0.1.md
    BREA_RETRIEVAL_ARCHITECTURE_DECISION_V0.1.md
    BREA_REASONING_ARCHITECTURE_DECISION_V0.1.md
    BREA_VERIFICATION_ARCHITECTURE_DECISION_V0.1.md
    BREA_VERSION_AND_REVISION_MODEL_V0.1.md
    BREA_USER_UPLOAD_WEB_BOUNDARY_V0.1.md
    P00_METHOD_AMENDMENT_CANDIDATE_V0.1.md
    BREA_SCALABLE_RETRIEVAL_AND_REASONING_ARCHITECTURE_REVIEW_V0.1.md

  external-research/
    EXTERNAL_MECHANISM_SOURCE_REGISTER_V0.1.md
    <bounded mechanism notes if needed>

  experiments/                     # only if separately authorized
    <isolated research spikes>

  evidence/
    REVIEW_EVIDENCE_INDEX_V0.1.md
    REVIEW_LIMITATIONS_V0.1.md

  handoff/
    NEXT_CANDIDATE_ARCHITECTURE_DECISION_V0.1.md
```

No BREA Candidate source belongs in this Review package.

---

# 22. Required Falsification Ledger

The central artifact is:

```text
review/FALSIFICATION_LEDGER_V0.1.md
```

Required rows:

```text
H-01 Open product classification
H-02 Corpus growth != proportional code growth
H-03 Family-specific deterministic reasoning does not scale
H-04 Ingestion/indexing required
H-05 Hybrid retrieval is stronger fit
H-06 LLM needed for selected responsibilities
H-07 Regulation IR needed
H-08 Deterministic moves toward invariant validator role
```

Each row must include:

```text
working hypothesis
strongest supporting evidence
strongest disconfirming evidence
falsifier attempted
result
confidence
unresolved uncertainty
architecture consequence
```

The final Review may not omit disconfirming evidence merely because it weakens the preferred architecture.

---

# 23. Valid Final Architecture Outcomes

The Review must allow all of the following outcomes.

## OUTCOME A — CURRENT DIRECTION WAS MOSTLY RIGHT

```text
Deterministic architecture remains primary.
Main correction = move knowledge from Python into declarative data/config.
RAG / LLM not justified now.
```

## OUTCOME B — INGESTION + STRUCTURED DATA, NO LLM REASONING

```text
Scalable ingestion/indexing required.
Regulation structure externalized.
Exact/BM25/metadata sufficient.
Professional reasoning remains deterministic/declarative.
```

## OUTCOME C — HYBRID RETRIEVAL + BOUNDED LLM

```text
Scalable ingestion/indexing required.
Hybrid retrieval justified.
LLM justified for language/fact/query tasks.
Professional final applicability remains strongly structured/validated.
```

## OUTCOME D — HYBRID RETRIEVAL + LLM-ASSISTED REASONING

```text
Open-language / cross-clause reasoning requires LLM assistance.
Strong verification / evidence / numeric / fail-closed contracts remain mandatory.
```

## OUTCOME E — INSUFFICIENT EVIDENCE

```text
Do not select next Candidate architecture yet.
Request a bounded research experiment.
```

A Review that can only conclude C/D is invalid.

---

# 24. Decision Threshold

The final architecture recommendation must show:

```text
1. which hypotheses survived falsification,
2. which were falsified,
3. what evidence changed the initial diagnosis,
4. why the selected architecture is the minimum sufficient architecture,
5. which technologies remain optional / deferred,
6. what next Candidate must prove that v0.3 did not prove.
```

The Review must prefer:

```text
minimum sufficient mechanism
```

over:

```text
maximum future-proof technology stack.
```

---

# 25. Next-Candidate Proof Requirement

The Review must design, but not execute, a proof stronger than:

```text
"one more known regulation question works."
```

Preferred proof target:

```text
freeze next Candidate implementation
↓
introduce an unseen but supported regulation / source revision
↓
source admission + ingestion + index only
↓
NO Agent source change
↓
ask previously unseen natural-language questions
↓
retrieve correct evidence
↓
apply professional contracts
↓
bind citations / numeric derivation
↓
fail closed when applicability cannot be established
```

This proof directly tests:

# **Corpus Growth != Code Growth**

If the selected architecture cannot state how this proof could pass, its scalability claim is weak.

---

# 26. Protected Boundaries

During this Review:

```text
BREA v0.1
READ-ONLY

BREA v0.2
READ-ONLY

BREA v0.3
FROZEN / READ-ONLY

E2-C Benchmark
MUST NOT BE CREATED

BREA v0.4+
MUST NOT BE FORMED

raw regulation corpus
MUST NOT BE UPSTREAMED

Platform Core
NO CHANGE

Runtime / RuntimeAdapter
NO CHANGE

Enterprise extensions
NO CHANGE

main
NO CHANGE
```

No admission / binding action is authorized.

---

# 27. Review Stop Conditions

STOP and return for architecture authority review if:

```text
S-01 selected architecture requires Platform Core semantics change
S-02 selected architecture requires Runtime responsibility change
S-03 accepted Domain / Enterprise responsibility model must be redefined
S-04 a new Governed Seam is claimed structurally necessary
S-05 Review cannot distinguish evidence from implementation preference
S-06 external framework becomes an undeclared runtime dependency
S-07 Review requires mutating v0.3 to continue
S-08 specific E2-C Benchmark is created early
S-09 raw corpus must be committed to produce evidence
S-10 no credible falsification attempt can be designed
```

A new Governed Seam may be recommended as an architecture question, but not created by this Review.

---

# 28. Final Review Verdict Model

DeepSeek may report only:

```text
READY FOR EXTERNAL ARCHITECTURE REVIEW

CURRENT SCALABILITY DIAGNOSIS FALSIFIED

PARTIALLY FALSIFIED — NARROWER ARCHITECTURE RECOMMENDED

SCALABILITY DIAGNOSIS SURVIVED FALSIFICATION

INSUFFICIENT EVIDENCE — BOUNDED EXPERIMENT REQUIRED

ARCHITECTURE REVIEW REQUIRED
```

DeepSeek may not self-authorize:

```text
v0.4 Candidate
E2-C
Method permanent amendment
Platform change
```

ChatGPT external review decides whether the Review is accepted and what next Stage action is legitimate.

---

# 29. Expected Final Review Statement

The final Review must be able to answer, without ambiguity:

```text
Was our diagnosis that BREA's current implementation model does not scale actually correct?

Which part was correct?
Which part was wrong?

What should normally change when new knowledge arrives?

What should require a new Agent Candidate?

What retrieval mechanism is minimally sufficient?

Where, if anywhere, is LLM justified?

What must remain deterministic / strongly verified?

Does BREA need a Regulation IR, and how much?

How do Agent Version, Corpus Revision, Index Revision and Domain Schema Version differ?

What exact next Candidate architecture should be tested?

What evidence would still prove that recommendation wrong?
```

If those questions are not answered, the Review is incomplete.

---

# 30. Current State After This Contract

```text
BREA v0.3
FROZEN

v0.3 FREEZE DEFECTS
VALID / PRESERVED AS PROFESSIONAL CONTRACT INPUT

SCALABILITY DIAGNOSIS
REVIEW CANDIDATE — NOT YET ARCHITECTURE FACT

SCALABLE RETRIEVAL & REASONING REVIEW CONTRACT
ACCEPTED

REVIEW EXECUTION
NOT AUTHORIZED YET

v0.4
NOT AUTHORIZED

E2-C
NOT AUTHORIZED

METHOD P-00 AMENDMENT
CANDIDATE ONLY

PLATFORM / RUNTIME
UNCHANGED
```

# **REVIEW CONTRACT VERDICT — ACCEPTED / READY FOR EXPLICIT REVIEW-EXECUTION AUTHORIZATION**
