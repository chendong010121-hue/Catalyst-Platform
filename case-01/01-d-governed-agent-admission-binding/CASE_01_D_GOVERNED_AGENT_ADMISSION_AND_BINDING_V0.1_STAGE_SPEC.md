# CASE 01-D — GOVERNED AGENT ADMISSION & BINDING V0.1
## STAGE SPEC — D0 AUTHORIZED / D1-D2 CONDITIONAL
### AGENT UNDERSTANDING GATE · ADMISSION · EXECUTION BINDING · CASE ↔ PLATFORM CO-EVOLUTION

> **Project:** Catalyst  
> **Case:** CASE 01 — Building Regulation Evidence Agent  
> **Branch:** `case-01`  
> **Parent Stage:** CASE 01-C — `EVIDENCE-BACKED PASS / CLOSED`  
> **CASE 01-C final closure commit:** `dd491a73a5dc59227a7c93c7962e9ba23ea04efa`  
> **Catalyst accepted `main`:** `5874be1130e8867082880fcd63f659fc909d9efd`  
> **Architecture / Stage authority + external auditor:** ChatGPT  
> **Implementation author:** DeepSeek  
> **Product / Release authority:** User  
> **D0 Agent Understanding Proof:** **AUTHORIZED**  
> **D1 Admission Architecture Compatibility:** **NOT YET AUTHORIZED**  
> **D2 Local Admission / Binding Proof:** **NOT YET AUTHORIZED**  
> **CASE 01-E:** **NOT AUTHORIZED**  
> **Catalyst `main` mutation:** **FORBIDDEN**

---

# 0. Stage Thesis

CASE 01-D keeps the accepted Case 01 mainline unchanged:

```text
01-A  UNDERSTAND LEGACY                 CLOSED
01-B  DEFINE GOVERNED AGENT             CLOSED
01-C  GOVERNED LOCAL FORMATION          CLOSED
01-D  ADMISSION / BINDING               NOW
01-E  PROFESSIONAL AGENT COMPLETION     LATER
01-F  PROFESSIONAL VALIDATION / EVOLVE  LATER
```

CASE 01-D adds one explicit entry proof before Admission:

# **D0 — Governed Agent Understanding Proof**

The purpose is not to redo CASE 01-A.

The purpose is to test whether Catalyst can take an existing / legacy / externally-built Agent workspace and recover, from its own evidence, a useful governed understanding of:

```text
what the Agent was intended to become
what it actually implements
what remains incomplete
what functions exist
who owns which meaning
what belongs to Domain
what belongs to Enterprise
what is only implementation HOW
what assets and evidence exist
what is uncertain
```

Only after this capability is independently reviewed may CASE 01-D proceed to:

```text
D1 — Admission Architecture Compatibility
D2 — Local Admission / Binding Proof
```

---

# 1. Why D0 Exists

CASE 01-C proved the forward formation path:

```text
Governed Definition
→ Case-scoped Governed Builder
→ Decomposable Agent Candidate
```

D0 tests the reverse intake path:

```text
Existing Agent Workspace
→ Agent Understanding
→ Evidence-backed Governed Understanding
```

Long-term Catalyst should support both:

```text
EXISTING AGENT
→ UNDERSTAND
→ GOVERN / REPAIR / ADMIT

and

REQUIREMENT / GOVERNED DEFINITION
→ BUILD
→ NEW AGENT
```

This matters because organizations will contain Agents that were:

```text
legacy-built
team-built
third-party-built
framework-built
Penguin-Harness-built
externally acquired
```

Catalyst must not assume every Agent entering governance was originally built by Catalyst.

---

# 2. Critical Blind-Test Rule

D0 must be a genuine understanding test.

Therefore the initial Agent Understanding pass must **NOT** read any source that contains the already-known answer.

## D0-A — BLIND INTAKE SOURCES — ALLOWED

Read-only Legacy Agent 2.0 workspace evidence may include:

```text
README / README variants
AGENTS.md
system / developer / charter / prompt files
historical requirement / migration / design docs stored in the workspace
code
config
schemas
Tests / fixtures
scripts
package / dependency manifests
local Git history if present
known issue notes / TODOs
runtime logs already present
existing local file history that belongs to the Legacy workspace
```

Historical conversation exports may be used only if they already exist as files within the authorized Legacy workspace or a user-designated read-only history location.

## D0-A — FORBIDDEN ANSWER SOURCES

Before `UNDERSTANDING_SNAPSHOT_V0.1` is frozen, do **not** read:

```text
CASE 01-A assessment outputs
CASE 01-A responsibility decomposition
CASE 01-A asset classification
CASE 01-B Governed Agent Definition
CASE 01-B Builder-consumable Definition
CASE 01-C Candidate definition / evidence as an answer source
this conversation's newly-restated product requirements
any manually prepared Product Requirement Recovery document
```

The Stage Spec itself may define the output schema and governance method, but must not seed the expected legacy product requirements.

If forbidden answer sources are read before the blind snapshot is frozen:

```text
D0 INVALID
→ STOP
→ do not claim Agent Understanding proof
```

---

# 3. Authorized Legacy Input

Primary known Legacy workspace from CASE 01-A:

```text
E:\试验场地\规范查询agent2.0
```

Treat it as:

```text
READ ONLY
LEGACY DEVELOPMENT INPUT
ASSET DONOR
PRE-CATALYST BASELINE
```

No source repair is authorized.

Do not:

```text
fix RAG
fix Prompt
rewrite README
add Memory
add Web Search
repair tests
refactor modules
change dependency files
change databases
change corpus
```

If a file cannot be read without repair, record an observability blocker.

---

# 4. D0 Is a Catalyst Capability Proof, Not a Product-Recovery Stage

Do not create a separate manually-authored Product Requirement Recovery Stage.

Instead, D0 must prove a reusable architectural pattern:

# **Governed Agent Intake & Understanding**

For CASE 01 this remains:

```text
CASE-SCOPED CAPABILITY PROOF
LOCAL ONLY
NOT PLATFORM CORE
NOT GENERALIZED
```

The product-intent baseline may emerge as an output of Understanding, but it must be evidence-derived rather than manually seeded.

---

# 5. D0 Required Understanding Model

Create a structured output capable of separating at least five different questions.

## U-1 — Intended Product Purpose

What product / professional outcome does the workspace evidence indicate the Agent was intended to deliver?

This must be separated from current implementation reality.

## U-2 — Intended Capabilities / Requirements

What behaviors or capabilities appear to have been intended?

Every requirement must include:

```text
requirement_id
statement
evidence_refs[]
confidence
source_type
implementation_status
```

## U-3 — Observed Implemented Capabilities

What is actually implemented or directly executable?

Do not infer implementation merely because a README / Prompt describes it.

## U-4 — Missing / Partial / Contradicted Capabilities

For each intended capability classify:

```text
IMPLEMENTED
PARTIAL
INTENDED_NOT_IMPLEMENTED
CONTRADICTED
UNKNOWN
```

## U-5 — Responsibility Model

Classify meaningful recovered semantics as:

```text
DOMAIN INTENT / RESPONSIBILITY
ENTERPRISE INTENT / RESPONSIBILITY
AGENT BEHAVIOR
PRIVATE IMPLEMENTATION HOW
RUNTIME RESPONSIBILITY
PLATFORM / INTEROP CANDIDATE
UNRESOLVED
```

Do not use file location as responsibility proof.

---

# 6. Evidence Classes

Every non-trivial recovered claim must use exactly one confidence class:

```text
PROVEN
STRONGLY SUPPORTED
WEAKLY SUPPORTED
UNKNOWN
```

Meaning:

```text
PROVEN
multiple direct evidence items or executable implementation/tests clearly establish the claim

STRONGLY SUPPORTED
clear intent evidence exists, but implementation or cross-source confirmation is incomplete

WEAKLY SUPPORTED
single ambiguous or indirect signal; cannot enter accepted product baseline without review

UNKNOWN
insufficient or conflicting evidence
```

Do not use confidence as probability math.

---

# 7. Evidence Hierarchy — No Single Global Source of Truth

D0 must distinguish source roles.

Examples:

```text
README / requirement docs
→ product intent evidence

Prompt / AGENTS / charter
→ intended behavior / instruction evidence
→ NOT proof that the behavior works

Tests
→ expected behavior evidence
→ executable tests may strengthen implementation proof

Code
→ implementation evidence

Config
→ implementation capability / intended option evidence

Git history
→ change-history / removed-intent / chronology evidence

Logs
→ observed-run evidence
```

Conflicts must be preserved, not silently reconciled.

Example:

```text
README says capability exists
code absent

→ intended requirement may be PROVEN/STRONG
→ implementation status = INTENDED_NOT_IMPLEMENTED
```

---

# 8. D0 Required Functional Decomposition

Recover a Legacy functional decomposition without forcing the current BREA FN-01..FN-11 model onto the source.

For each recovered function record:

```text
legacy_function_id
name
professional purpose
input/output
evidence refs
semantic owner
implementation location(s)
implementation status
coupling / mixed-responsibility finding
possible replaceability boundary
confidence
```

After blind freeze, comparison may map recovered legacy functions to current BREA functions.

Before freeze, current BREA FN IDs must not be used as extraction targets.

---

# 9. D0 Must Recover Enterprise Intent Explicitly

Enterprise does not disappear merely because CASE 01 currently uses Minimum Enterprise Context.

D0 must actively separate organization-specific intent from professional Domain intent.

Possible Enterprise-type findings may include, when supported by evidence:

```text
organization / owner / user / project attribution
data admission constraints
network access constraints
source trust rules
human review expectations
project persistence
memory / retention expectations
approved Agent/version expectations
organization-specific policy / risk / workflow meaning
```

Do not invent any of these if the Legacy evidence does not support them.

Output:

```text
ENTERPRISE_INTENT_RECOVERY_V0.1.md
```

This is evidence recovery only; no Enterprise subsystem implementation is authorized.

---

# 10. D0 Must Recover Domain Intent Explicitly

Recover professional meaning that appears intended to survive implementation replacement.

Examples of categories — not expected answers:

```text
professional project facts
source authority
applicability meaning
clause/table/numeric evidence meaning
professional uncertainty
professional result expectations
```

Do not seed specific values or requirements.

Output:

```text
DOMAIN_INTENT_RECOVERY_V0.1.md
```

---

# 11. D0 Initial Output Package — Blind Snapshot

Write outside the Legacy workspace, under:

```text
case-01/01-d-governed-agent-admission-binding/d0-agent-understanding/
```

Required blind outputs:

```text
blind/
├── UNDERSTANDING_SNAPSHOT_V0.1.md
├── INTENDED_PRODUCT_PURPOSE_V0.1.md
├── PRODUCT_INTENT_REQUIREMENT_MATRIX_V0.1.md
├── OBSERVED_CAPABILITY_MATRIX_V0.1.md
├── LEGACY_FUNCTIONAL_DECOMPOSITION_V0.1.md
├── RESPONSIBILITY_RECOVERY_V0.1.md
├── DOMAIN_INTENT_RECOVERY_V0.1.md
├── ENTERPRISE_INTENT_RECOVERY_V0.1.md
├── ASSET_AND_IMPLEMENTATION_INVENTORY_V0.1.md
├── UNDERSTANDING_EVIDENCE_INDEX_V0.1.md
└── UNDERSTANDING_UNCERTAINTIES_V0.1.md
```

Also record:

```text
Legacy root path
file inventory used
Git HEAD/history reference if available
hash or fingerprint for material input files where practical
scan start/end time
forbidden-answer-source declaration
```

---

# 12. Blind Snapshot Freeze

After D0-A completes:

```text
freeze all blind outputs
compute SHA256 for each blind output
create BLIND_SNAPSHOT_MANIFEST_V0.1.json
```

After freeze:

```text
DO NOT edit blind outputs
```

Any comparison / reconciliation must go into separate `comparison/` files.

This prevents post-hoc answer fitting.

---

# 13. D0-B — Known-Answer Comparison — Only After Freeze

Only after the blind snapshot is frozen may DeepSeek read:

```text
accepted CASE 01-A evidence / assessment outputs
accepted CASE 01-B Governed Agent Definition
current CASE 01-C formation outputs
```

Purpose:

```text
compare, not rewrite
```

Create:

```text
comparison/
├── BLIND_VS_CASE_01_A_COMPARISON_V0.1.md
├── BLIND_VS_CURRENT_BREA_COMPARISON_V0.1.md
├── RECOVERED_PRODUCT_INTENT_BASELINE_V0.1.md
└── UNDERSTANDING_CAPABILITY_SCORECARD_V0.1.md
```

`RECOVERED_PRODUCT_INTENT_BASELINE_V0.1.md` must preserve:

```text
recovered intent
confidence
evidence source
current BREA status
future completion relevance
```

It is an output of Catalyst Understanding, not a manually seeded requirement document.

---

# 14. D0 Capability Scorecard

Do not reduce Understanding quality to one scalar score.

Score at least these dimensions:

```text
UC-01 Product-purpose recovery
UC-02 Intended-capability coverage
UC-03 Intent vs implementation separation
UC-04 False implemented-claim control
UC-05 Functional decomposition quality
UC-06 Domain / Enterprise separation
UC-07 Evidence traceability
UC-08 Confidence calibration
UC-09 Missing/partial capability detection
UC-10 No architecture-answer leakage before freeze
```

Each dimension:

```text
PASS
PARTIAL
FAIL
```

A D0 overall PASS requires:

```text
no FAIL in UC-01 / 02 / 03 / 04 / 06 / 07 / 10
and
no material unsupported requirement promoted as PROVEN
and
no material implemented capability claimed solely from Prompt/README intent
```

---

# 15. Research Trigger

If D0 demonstrates that Catalyst / the current extraction method cannot reliably understand the Legacy Agent, do **not** patch the result by repeatedly adding known answers to the prompt.

Trigger:

```text
UNDERSTANDING RESEARCH REQUIRED
```

Research is required if one or more occur:

```text
R-U1 core product purpose materially missed
R-U2 major intended capabilities systematically missed
R-U3 intent repeatedly confused with implementation
R-U4 Enterprise intent cannot be separated from Domain / Agent behavior
R-U5 evidence grounding is weak or hallucinated
R-U6 functional decomposition is dominated by file/module structure rather than responsibility
R-U7 confidence labels are unreliable
R-U8 successful output requires manually seeding expected answers
```

On trigger:

```text
STOP CASE 01-D
DO NOT START D1
DO NOT START D2
```

Then perform a focused research stage before retrying D0.

Potential research subjects may include:

```text
Penguin Harness Agent creation / Agent state / skill context patterns
Pi extension / skill / context patterns
software-agent repository understanding / architecture recovery patterns
codebase intent mining
spec/test/prompt evidence fusion
agent manifest / introspection patterns
```

The exact research scope must be determined from the observed D0 failure, not predicted in advance.

---

# 16. D0 Implementation Freedom

DeepSeek may choose the minimum local mechanism needed to perform the understanding proof:

```text
LLM reasoning
file inventory scripts
static code inspection
grep/search
Git history inspection
structured extraction scripts
small local index
report generation
```

However:

```text
NO legacy source mutation
NO Catalyst Platform Core change
NO Runtime change
NO generic repository-understanding Platform
NO embedding/vector DB requirement unless evidence proves necessary
NO Internet research during blind extraction
```

D0 may use an LLM because semantic intent recovery is inherently language-heavy.

The implementation mechanism remains CASE-scoped until evidence supports generalization.

---

# 17. D0 Publication Boundary

D0 is the only currently authorized execution portion of CASE 01-D.

DeepSeek may create D0 files and local helper scripts under:

```text
case-01/01-d-governed-agent-admission-binding/d0-agent-understanding/**
```

Do not modify:

```text
Legacy Agent 2.0 workspace
CASE 01-A/B/C accepted artifacts
Catalyst root
Platform Core
Runtime
main
```

Raw private Legacy files do not need to be copied into GitHub.

GitHub should receive:

```text
structured understanding outputs
evidence locators/hashes
CASE-scoped helper code if required
comparison outputs
logs needed for reproducibility
```

Do not publish sensitive/raw data merely for convenience.

---

# 18. D0 Execution Sequence

```text
D0-0  verify branch == case-01
D0-1  verify CASE 01-C closure exists
D0-2  inventory authorized Legacy workspace
D0-3  declare forbidden answer sources NOT read
D0-4  inspect Legacy README / prompts / AGENTS / docs / tests / config / code / history
D0-5  build evidence index
D0-6  recover intended product purpose
D0-7  recover intended requirements/capabilities
D0-8  recover observed implementation status
D0-9  recover functional decomposition
D0-10 recover Domain / Enterprise / Agent / HOW responsibility
D0-11 record unknowns/conflicts/confidence
D0-12 produce blind output package
D0-13 freeze + hash blind snapshot
D0-14 only now read CASE 01-A / B / C accepted outputs
D0-15 compare blind understanding to known evidence
D0-16 create product-intent baseline derived from understanding
D0-17 create Understanding Capability Scorecard
D0-18 classify PASS / RESEARCH REQUIRED / FAIL
D0-19 final repo contamination check
D0-20 one D0 commit + one push to case-01
D0-21 STOP
→ EXTERNAL REVIEW BY CHATGPT
```

Do not continue to D1 even if DeepSeek self-rates PASS.

---

# 19. D0 Required Final Report

```text
D0 STATUS
PASS / RESEARCH REQUIRED / FAIL

LEGACY WORKSPACE
...

BLIND ANSWER SOURCES READ BEFORE FREEZE
NONE / list

FILES / HISTORY ITEMS INSPECTED
N / summary

RECOVERED PRODUCT PURPOSE
summary

INTENDED REQUIREMENTS RECOVERED
N

IMPLEMENTED
N

PARTIAL
N

INTENDED_NOT_IMPLEMENTED
N

CONTRADICTED
N

UNKNOWN
N

DOMAIN INTENT ITEMS
N

ENTERPRISE INTENT ITEMS
N

LEGACY FUNCTIONS RECOVERED
N

PROVEN CLAIMS
N

STRONGLY SUPPORTED CLAIMS
N

WEAK CLAIMS
N

UNKNOWN CLAIMS
N

UC-01..UC-10
PASS / PARTIAL / FAIL

RESEARCH TRIGGER
NO / YES + IDs

CASE 01 PRODUCT INTENT BASELINE
GENERATED / NOT GENERATED

LEGACY SOURCE CHANGED
NO

CATALYST MAIN
UNCHANGED

D1
NOT AUTHORIZED

D2
NOT AUTHORIZED

FINAL
READY FOR D0 EXTERNAL REVIEW
or
UNDERSTANDING RESEARCH REQUIRED
```

---

# 20. D0 STOP Conditions

STOP if:

```text
S-U1 forbidden answer source is read before blind freeze
S-U2 Legacy source must be repaired to understand it
S-U3 recovered claims cannot be evidence-linked
S-U4 output begins copying entire Legacy source into GitHub
S-U5 current BREA definition is used as the extraction template before freeze
S-U6 user/current-conversation expected requirements are seeded into the blind prompt
S-U7 Platform Core or Runtime change appears necessary
S-U8 repeated prompt patching is required to recover known intent
S-U9 research is required
S-U10 unauthorized workspace change occurs
```

---

# 21. Planned D1 — Admission Architecture Compatibility — NOT YET AUTHORIZED

If and only if D0 passes external review, D1 will answer:

```text
What is the minimum Agent Admission Record?
What exact Agent Version is the governed subject?
What Formation Evidence is required for admission?
What is an Execution Binding?
How is implementation fingerprinted?
Can existing Platform Standard express execution without Agent=Capability?
Can governance.agent semantics travel through Extension?
Does Adapter need a Case-local binding mechanism?
Does Runtime remain unchanged?
```

Hard rules:

```text
Agent != Capability
Admission != Registry.register()
Admission != runnable
Binding != Agent identity
Extension First
Platform Core Review Last
```

If D1 concludes Platform Core or Runtime must change:

```text
STOP → ARCHITECTURE REVIEW
```

No automatic change.

---

# 22. Planned D2 — Local Admission / Binding Proof — NOT YET AUTHORIZED

If D1 passes and receives explicit authorization, D2 will attempt:

```text
BREA v0.1-candidate
→ verify Governed Definition SHA
→ verify implementation fingerprint
→ verify required Formation Evidence
→ create Agent Admission Record
→ ADMITTED
→ create Execution Binding
→ invoke through existing Platform-compatible boundary
→ execute
→ Standard Result / Trace
→ prove exact admitted Agent version attribution
```

Expected fail-closed classes include:

```text
wrong definition SHA
wrong implementation fingerprint
missing Formation Evidence
unknown Agent version
wrong binding
Agent attribution mismatch
untraceable execution result
```

D2 is not authorized by this Stage Spec yet.

---

# 23. Enterprise Layer in 01-D

Enterprise remains a first-class semantic dimension.

D0 recovers Enterprise intent from Legacy evidence.

D1/D2 will use only the minimum Enterprise Context needed for current admission proof, likely including:

```text
organization / owner / project attribution
evaluation / acceptance authority
Agent ownership
```

Future Case needs may later grow Enterprise assets such as:

```text
source trust policy
network permission
data admission
human review policy
memory / retention
approved Agent versions
```

Do not implement these merely because they are foreseeable.

They grow from real Case evidence.

---

# 24. Product Mainline Preservation

D0-derived `RECOVERED_PRODUCT_INTENT_BASELINE_V0.1.md` becomes the explicit product-intent reference for future CASE 01-E professional completion.

It must not redefine current accepted BREA formation contracts retroactively.

Instead it answers:

```text
what the original product wanted
what BREA currently covers
what remains partial / unimplemented
what later completion work should reconsider
```

This keeps two success lines explicit:

```text
PLATFORM SUCCESS
Catalyst can understand, build, govern, admit, run and evolve Agents.

CASE SUCCESS
BREA eventually becomes a genuinely useful professional building-regulation Agent.
```

Case 01 is not complete until both lines are satisfied.

---

# 25. Current Authorization Summary

```text
CASE 01-D STAGE SPEC
ACCEPTED FOR D0 EXECUTION

D0 BLIND AGENT UNDERSTANDING PROOF
AUTHORIZED

LEGACY READ-ONLY SCAN
AUTHORIZED

CASE-SCOPED UNDERSTANDING HELPER IMPLEMENTATION
AUTHORIZED

BLIND SNAPSHOT + COMPARISON OUTPUT
AUTHORIZED

ONE D0 COMMIT + ONE PUSH TO case-01
AUTHORIZED

LEGACY SOURCE MUTATION
FORBIDDEN

CATALYST MAIN CHANGE
FORBIDDEN

PLATFORM CORE CHANGE
FORBIDDEN

RUNTIME CHANGE
FORBIDDEN

D1 ADMISSION ARCHITECTURE
NOT AUTHORIZED

D2 ADMISSION / BINDING IMPLEMENTATION
NOT AUTHORIZED

CASE 01-E
NOT AUTHORIZED
```

---

# 26. Stage Exit

D0 exits only as:

```text
D0 EVIDENCE PACKAGE
→ STOP
→ CHATGPT EXTERNAL REVIEW
```

External review then chooses exactly one:

```text
A. D0 PASS
   → authorize D1 planning/execution

B. TARGETED NON-SEMANTIC REPAIR
   → bounded repair only

C. UNDERSTANDING RESEARCH REQUIRED
   → focused research before retrying D0

D. FAIL / ARCHITECTURE RECONSIDERATION
```

DeepSeek must not self-authorize the next branch.
