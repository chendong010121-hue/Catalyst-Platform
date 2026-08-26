# Catalyst Platform — History Map

Operational `main` is intentionally not an archive. Closed Stages, superseded candidates, old Handoffs, one-off audit reports, Case work, and pre-Operational proof fixtures remain recoverable through Git history, closed PRs, and frozen refs.

This page is navigation only. Historical material does not become current authority merely because it is linked here.

---

## Full pre-Operational V1 repository snapshot

```text
branch: archive/pre-operational-v1
commit: 3986236db1dc66ee0bc78ac2a4264792d4a8f5fb
```

This ref preserves the complete pre-consolidation tree: root Stage Specs, comparative audits, integration decision fixtures, Runtime implementation notes, V0.2 repair records, old Handoffs, the Capability-Preserving Evolution promotion review, and pre-Operational test campaigns.

Use it when reconstructing historical decisions. Do not copy those files back into the active root merely for convenience.

---

## Case01

```text
branch: case-01
head:   232d6837647c68670fba3f3b2faf7ec1fac73f0a
```

Role:

- historical Building Regulation / BREA product-development evidence;
- professional Capability Evaluation and failure-attribution lineage;
- source of bounded fail-closed numeric-safety learning.

Operational `main` does not execute Case01 and does not treat Case01 as Platform architecture authority.

Current durable value is navigated through:

```text
assets/knowledge/FAIL_CLOSED_NUMERIC_SAFETY_V0.1.json
docs/governance/CATALYST_PHASE_2_CLOSURE_REVIEW_V0.1.md
```

---

## Case02

```text
branch: case-02
head:   336f8e6f28c1569e5c53f245daaa3ee8a197f33d
external source: ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad
```

Role:

- historical external-Agent understanding / decomposition evidence;
- governed harvested mechanism catalog;
- proof that useful capability/mechanism knowledge may survive while the source Agent remains disposable.

Current durable value is navigated through:

```text
assets/knowledge/WAKU_RETRIEVAL_GATED_MEMORY_V0.1.json
```

---

## Capability-Preserving Evolution — PR #15

```text
PR:           #15 — docs: formalize capability-preserving evolution
status:       MERGED / CLOSED
merge commit: 3986236db1dc66ee0bc78ac2a4264792d4a8f5fb
```

PR #15 is not missing. Its stable result is now carried by current authority:

```text
ARCHITECTURE.md
→ stable capability-preserving evolution principle

platform-harness/skills/capability-optimization/SKILL.md
→ replaceable implementation-evolution method (v2)
```

The original Promotion Review remains historical evidence in the pre-Operational snapshot / PR lineage rather than a third active architecture layer.

---

## Phase 2

Current closure record is intentionally retained in active governance because it is the accepted real-Capability adoption evidence chain:

```text
docs/governance/CATALYST_PHASE_2_CLOSURE_REVIEW_V0.1.md
```

Status:

```text
PHASE 2 COMPLETE — PASS
```

---

## Superseded PR #1

Historical PR #1 (`RuntimeDomain identity closure`) is closed as **SUPERSEDED / NOT MERGED**.

Its head remains recoverable through Git history and the closed PR. Its RuntimeDomain approach is not current architecture or implementation authority.

This closure preserves the real historical failure/decision record instead of rewriting history to look uniformly successful.

---

## Historical branch policy

Historical development branches may remain as Git refs while they are useful for lineage, but they are not active work merely because they exist.

A branch name such as:

```text
docs/*
ds/*
stage/*
review/*
release/*
case-*
```

must not be interpreted as current authorization.

The repository should have no open historical PRs competing with current work. Current work requires an explicitly active branch / task / Stage.

Branch deletion is administrative hygiene only after the relevant commit/PR/evidence identity is safely preserved; deleting or retaining a historical ref must not change current Platform semantics.

---

## Historical evidence rule

When investigating why the current system looks the way it does:

```text
current authority / Operational Baseline
→ identify the responsibility or claim
→ follow explicit evidence / lineage ref
→ inspect exact historical commit / closed PR / frozen branch when needed
```

Do not use filename recency, numbering, branch existence, or an old `Status:` line to infer current authorization.
