# F-EXP-03R — Integrated Targeted Repair Review

Status: READY FOR EXTERNAL REVIEW. This is an observed decision candidate,
not an accepted BREA architecture decision.

Baseline input: F-EXP-03 implementation/evidence commit
`00ae01df7cdc8909d0289fa7a63e65b551ef9802`.

## Fairness repair checks

| Repair | Observed result |
|---|---|
| A' generic semantic derivation | PASS: A' derives a temporary semantic view from raw evidence, unit type, shared project-fact descriptors, and generic grammar; no source/locator/family branch is used |
| Shared semantic interface | PASS: both tracks expose `semantic_view = {scope, conditions, numeric}` and use the same validator and PC-01..PC-07 |
| B-MIN project-derived Gold removal | PASS: RF-05 stores operand reference, operator, modifier, and advisory cap only; `12` is calculated at runtime and compared with independent Gold |
| RF-03 table validation | PASS: both tracks expose and validate source-backed `机动车=0.8` and `非机动车=1.1` |
| Test oracle | PASS: tests derive the verdict from observations and do not assert an A'/B-MIN winner |

## Observed comparison

| Track | PC-01 | PC-02 | PC-03 | PC-04 | PC-05 | PC-06 | PC-07 | Core contract |
|---|---|---|---|---|---|---|---|---|
| A' | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| B-MIN | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

Both tracks used the same seven core records: five representative forms and
two negative controls. They used the same source evidence, SHA-256 values,
locators, project facts, independent Gold, result contract, validator, and
fail-closed rules. The same-structure extension also passed the shared
contract for both tracks; its mechanism hash was unchanged before/after the
probe and its schema shape was unchanged.

## A' result

A' no longer loses by construction. Its adapter keeps only light evidence and
creates an ephemeral semantic view through a generic derivation mechanism:
generic scope/value alignment, exception-segment detection, normative modal
extraction, percentage/modifier extraction, and generic table label/value
pairing. The mechanism contains no source ID, locator, regulation-family term,
tested conclusion, or hardcoded tested numeric value.

A' passed RF-01..RF-05, the unsupported-numeric control, the unresolved-scope
control, all PC-01..PC-07, and RF-EXT-01. RF-05 produced runtime result `12`
from project operand `600 * 0.02`; it did not receive B-MIN's typed record.

## B-MIN result

B-MIN passed the same seven core records and extension with the same validator.
Its RF-05 regulation representation contains no `result` or project-specific
formula. The validator generated the runtime formula and result trace from the
stored operand reference, multiply operator, modifier `0.02`, and advisory cap
`20`. The independent Gold expected `12`, and the observed result matched it.

RF-03 independently matched both source-backed table values `0.8` and `1.1`,
not merely the `commercial_large_rates` label.

## B-MIN field-group ablation

All four original groups still caused material failures when removed:

| Group | Observed failed PC surface |
|---|---|
| G-BASE | PC-05, PC-07 |
| G-SCOPE | PC-01, PC-02, PC-03, PC-05, PC-06 |
| G-CONDITION | PC-01, PC-02, PC-03, PC-05, PC-06 |
| G-NUMERIC | PC-04, PC-06 |

No tested B-MIN group is removed or deferred. This remains evidence limited to
the fixed experiment surface, not a permanent field decision.

## Hidden-knowledge and protected-boundary checks

Hidden-knowledge scan: A' PASS, B-MIN PASS, shared validator PASS, shared
semantic derivation PASS. No source-specific, locator-specific, or regulation-
family-specific runtime knowledge was found in the mechanism code.

PASS: only the existing F-EXP-03 artifact surface was changed. No new case
family, BREA Candidate, raw corpus, F-EXP-01 execution, E2-C Benchmark,
Platform Core, Runtime, RuntimeAdapter, Enterprise extension, or `main` change
was made.

## Verdict candidate

`INCONCLUSIVE`

This verdict is computed from the observed results: A' and B-MIN both satisfy
the professional contract and both pass the data-only extension, while every
tested B-MIN field-group ablation still produces a material failure. The
repaired experiment therefore does not fairly establish that A' is sufficient
or that B-MIN is evidenced as necessary. External Experiment Review remains
required; no final architecture is declared here.
