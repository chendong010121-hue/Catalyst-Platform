# CASE 01-E / E2 — KR-002 Hangzhou Growth Gate
## GROWTH GATE CONTRACT V0.1

> Frozen Agent: `case-01.brea @ 0.6-candidate`  
> Agent freeze commit: `807c9aede8fd0646da07c79c457286f221ce61ae`  
> Candidate tree SHA256: `0f92a171a7a3e204d650ac7b456e04bd224c13b6b3ed7cd2630f8d9589a13319`  
> Implementation fingerprint: `70cdf812addfbdf5c86dd990cd28a8880f73a84fcb66fcfe9c8194a20c63f6a2`  
> Baseline Knowledge Revision: `KR-001`  
> Target Knowledge Revision: `KR-002`  
> New source: 《杭州市城市规划管理技术规定》  
> Authority: 杭州市规划和自然资源局  
> Document: `杭规划资源发〔2026〕4号`  
> Issued: `2026-02-05`  
> Effective: `2026-04-01`  
> Source PDF SHA256: `3b72f0b0cff971ac56b1fdabf1f9d4a6af5c4e53a9e12bb0b4c3d6f5084afee8`  
> New Candidate: **NO**  
> Agent mutation: **FORBIDDEN**  
> E2-C: **NOT AUTHORIZED**

## 1. Purpose

Run the first real post-freeze Knowledge Revision growth test against the frozen v0.6 Agent.

The Gate must distinguish three different growth classes rather than flattening them into one PASS/FAIL:

```text
G-01 Knowledge Lifecycle Growth
G-02 Source-Structure Compatibility
G-03 Professional Semantic Growth
```

Do not repair a discovered gap during this Gate.

---

## 2. Frozen Agent invariant

Throughout the Gate the following must remain byte-identical to the v0.6 Freeze:

```text
candidate/brea-v0.6/**
Candidate tree SHA256
Implementation fingerprint
Semantic View interface
Fact schema / FACT_VOCABULARY
FN-01..FN-11
SEAM-01..SEAM-03
OBL-01..OBL-06
```

Expected frozen values:

```text
candidate_tree_sha256 = 0f92a171a7a3e204d650ac7b456e04bd224c13b6b3ed7cd2630f8d9589a13319
implementation_fingerprint = 70cdf812addfbdf5c86dd990cd28a8880f73a84fcb66fcfe9c8194a20c63f6a2
```

Any Agent-code or Candidate-tree mutation invalidates the Gate.

---

## 3. KR-002 construction boundary

Create `knowledge/KR-002.json` as a new Knowledge Revision.

Start from KR-001 and add only what is necessary to identify and bind the Hangzhou source for generalized evidence use:

```text
knowledge_revision_id = KR-002
schema_version unchanged unless the current schema itself cannot represent the source
existing KR-001 sources/standards/routes/fact_descriptors preserved
+
CORPUS-03 source identity / provenance / local reference / SHA
+
Hangzhou standard metadata / aliases
```

Recommended Case-local standard key:

```text
HZ-PLANNING-TECH-2026
```

This is an internal knowledge key, not an assertion that the document has that official standard number.

Do NOT add new Hangzhou professional routes, new planning fact descriptors, new reasoning primitives, or test-specific conclusions to KR-002.

---

## 4. Local source preparation

The supplied PDF is the authoritative source input for this Gate.

First verify its SHA256 exactly:

```text
3b72f0b0cff971ac56b1fdabf1f9d4a6af5c4e53a9e12bb0b4c3d6f5084afee8
```

Because frozen v0.6 currently consumes UTF-8 text source records, the executor MAY create one local normalized text derivative solely for this Gate.

Requirements:

```text
local only
read-only after preparation
not committed to GitHub
record derived-file SHA256
record extraction / normalization method
preserve source wording and structural numbering
```

Forbidden normalization:

```text
表（2-3） → 表2.3
表（3-2） → 表3.2
一、 / （一） / 1. / （1） → invented X.Y.Z clause numbers
manual rewriting of rules into parser-friendly syntax
hand-curated test snippets used as the corpus
semantic paraphrase presented as source text
```

This Gate tests the actual source structure after ordinary text extraction, not a source rewritten to fit v0.6.

Passing this Gate does NOT prove generic PDF ingestion; it proves only the behavior actually observed with the recorded local source preparation.

---

## 5. G-01 — Knowledge Lifecycle Growth

Question:

> Can `KR-001 → KR-002` occur while the frozen v0.6 Agent remains byte-identical?

Minimum checks:

```text
KR-002 can be created outside Candidate tree
v0.6 explicit Knowledge Binding accepts KR-002 identity + SHA
CORPUS-03 is loaded through KR-002 source records
no historical manifest edit
no Candidate-local professional data edit
Candidate tree SHA unchanged
implementation fingerprint unchanged
```

Verdict:

```text
PASS
or
KNOWLEDGE_LIFECYCLE_GROWTH_FAILED
```

If G-01 fails, STOP. Do not repair.

---

## 6. G-02 — Source-Structure Compatibility

Only if G-01 PASS, test the frozen generalized evidence-query path against the Hangzhou source.

Use a minimal set of real, previously unsupported source questions. At least:

```text
S-01 implementation/effective-date evidence
S-02 wall-height evidence (2.2m rule)
S-03 underground pedestrian connection evidence (4m width / 2.5m clear height)
S-04 residential FAR / building-density evidence around 表（2-3）
S-05 explicit table-locator or table-structure probe for 表（2-3）
```

The goal is not project-specific applicability. The goal is:

```text
source resolution
→ evidence retrieval
→ verbatim/source fidelity
→ usable locator
→ no unsupported numeric fabrication
```

Use the existing v0.6 generalized retrieval behavior exactly as frozen.

Do not add parser/query code, aliases in Python, special query branches, or transformed fake locators.

Verdict:

```text
GENERAL_EVIDENCE_GROWTH_PASS
or
SOURCE_STRUCTURE_GROWTH_DETECTED
```

If some probes pass and others fail, report the exact boundary rather than flattening the result.

---

## 7. G-03 — Professional Semantic Growth Classification

G-03 is classification only. It does not authorize new professional coverage.

Classify at minimum these two real planning rule families:

```text
P-01 表（2-3）住宅用地容积率 / 建筑密度
P-02 表（3-2）建筑后退道路红线
```

Compare each against the frozen v0.6:

```text
current Fact Vocabulary
current Semantic View
current route kinds
current deterministic applicability / verification primitives
```

For each return:

```text
CURRENTLY_EXPRESSIBLE
or
STRUCTURAL_GROWTH_REQUIRED
```

If structural growth is required, list only the smallest missing professional primitives evidenced by the source and current implementation, for example facts/relations/operators that are actually necessary.

Do NOT add those primitives in this Gate.

G-03 may still be completed as analysis-only when G-02 exposes a source-structure gap, so Source Format Growth and Professional Semantic Growth remain distinguishable.

---

## 8. Layered verdicts

The final Gate report must preserve independent outcomes:

```text
G-01 Knowledge Lifecycle:
PASS / FAILED

G-02 General Evidence / Source Structure:
PASS / PARTIAL / SOURCE_STRUCTURE_GROWTH_DETECTED / NOT_REACHED

G-03 Professional Semantic Classification:
NORMAL_WITHIN_CURRENT_CONTRACT / STRUCTURAL_GROWTH_REQUIRED / NOT_REACHED
```

Do not force one simplistic overall PASS when the layers differ.

A strong positive claim is permitted only when supported:

```text
NORMAL KNOWLEDGE CONTENT GROWTH WITHOUT AGENT MUTATION — CASE PROVEN
```

This claim requires at minimum G-01 PASS plus useful new-source generalized evidence retrieval under G-02 while the frozen Agent fingerprint remains unchanged.

It does NOT imply that all Hangzhou planning professional rules are already supported.

---

## 9. Protected boundaries

Forbidden writes/mutations:

```text
candidate/brea-v0.6/**
v0.1..v0.5
Platform Core
Runtime
RuntimeAdapter
Enterprise extensions
main
FN / SEAM / OBL
Fact Vocabulary / Semantic View
parser / query / runner repair
v0.7 formation
Admission / Binding
E2-C Benchmark
raw PDF upstream
normalized full source text upstream
```

Discovery of a need for any of these is evidence, not authorization.

---

## 10. Minimal artifact surface

Long-lived GitHub output for an authorized execution is limited to:

```text
knowledge/KR-002.json
KR_002_GROWTH_RESULTS.json
KR_002_GROWTH_REVIEW.md
```

Use test output / execution trace for supporting detail. Do not create an Evidence Index, separate conformance package, or duplicate summaries.

The raw PDF and normalized full-text derivative remain local and uncommitted.

---

## 11. Publication boundary

Execution requires a separate declarative Authorization Record.

Recommended publication:

```text
ONE KR-002 + growth-evidence commit
ONE push to case-01
STOP
```

If G-01 fails before KR-002 can be validly formed, do not fabricate a successful KR-002; commit only the minimum authorized blocker evidence if the authorization permits it.

After execution:

```text
STOP
→ ChatGPT External KR-002 Growth Review
```

No discovered repair is authorized automatically.

---

## 12. Current state

```text
BREA v0.6
FROZEN / EXTERNAL PASS

KR-001
BASELINE

KR-002 GROWTH GATE CONTRACT
ACCEPTED

KR-002 EXECUTION
NOT AUTHORIZED BY THIS CONTRACT ALONE

v0.7
NOT AUTHORIZED

E2-C
NOT AUTHORIZED
```

# VERDICT — READY FOR EXPLICIT KR-002 GROWTH GATE AUTHORIZATION
