# Catalyst Platform History Map

Operational `main` is intentionally not an archive. Closed stages, old Handoffs, one-off audit reports, Case work, and pre-Operational proof fixtures remain recoverable through immutable Git history and frozen refs.

This page is a navigation map only. Historical material does not become current authority merely because it is linked here.

## Full pre-Operational V1 repository snapshot

```text
branch: archive/pre-operational-v1
commit: 3986236db1dc66ee0bc78ac2a4264792d4a8f5fb
```

This ref preserves the complete root-level Stage Specs, comparative audits, integration decision fixtures, Runtime implementation notes, V0.2 repair records, old Handoff, and pre-Operational test campaign exactly as they existed before consolidation.

Use it when reconstructing historical decisions. Do not copy those files back into the active root merely for convenience.

## Case01

```text
branch: case-01
head:   232d6837647c68670fba3f3b2faf7ec1fac73f0a
```

Role:

- historical Building Regulation / BREA product-development evidence;
- product capability evaluation and failure-attribution lineage;
- earlier source for bounded fail-closed numeric-safety learning.

Operational `main` does not execute Case01 and does not treat Case01 as Platform architecture authority.

Current durable value that survived Case01/Phase2 is navigated through:

```text
assets/knowledge/FAIL_CLOSED_NUMERIC_SAFETY_V0.1.json
docs/governance/CATALYST_PHASE_2_CLOSURE_REVIEW_V0.1.md
```

## Case02

```text
branch: case-02
head:   336f8e6f28c1569e5c53f245daaa3ee8a197f33d
external source: ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad
```

Role:

- historical external-Agent understanding/decomposition evidence;
- governed harvested mechanism catalog;
- proof that useful Capability/mechanism knowledge may survive while the source Agent remains disposable.

Current durable Waku-derived value is navigated through:

```text
assets/knowledge/WAKU_RETRIEVAL_GATED_MEMORY_V0.1.json
```

## Closed Phase 2

Current closure record is intentionally retained in active governance because it is the accepted real-Capability adoption evidence chain:

```text
docs/governance/CATALYST_PHASE_2_CLOSURE_REVIEW_V0.1.md
```

Phase 2 status:

```text
COMPLETE — PASS
```

## Historical root material preserved by the archive ref

The frozen pre-Operational ref includes, among others:

- Platform Integration V0.1 Stage / research / falsification / pre-merge / final-delivery records;
- V0.2 Stage and native-tools evolution records;
- Capability-Preserving Evolution promotion review;
- Enterprise Extension Pilot Stage record;
- old `HANDOFF.md`;
- Runtime `IMPLEMENTATION_NOTES.md`, `INTERNAL_AUDIT_REPORT.md`, `TEST_MANIFEST.md`;
- Case01/Waku construction-decision fixtures;
- comparative-test fixtures.

Their accepted lessons may still be referenced by current Architecture, methods, tests, evidence, or assets. Their old current-state/status lines are historical.

## Historical evidence rule

When investigating why the current system looks the way it does:

```text
current authority / Operational Baseline
→ identify the responsibility or claim
→ follow explicit evidence/lineage ref
→ inspect the exact historical commit/branch when needed
```

Do not use filename recency, numbering, or an old `Status:` line to infer current authorization.
