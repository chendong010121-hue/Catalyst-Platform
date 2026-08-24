# F-EXP-03 — Integrated Experiment Review

Status: READY FOR EXTERNAL REVIEW. This is a decision candidate, not an
accepted BREA architecture decision.

## Result at a glance

| Track | PC-01 | PC-02 | PC-03 | PC-04 | PC-05 | PC-06 | PC-07 | Core contract |
|---|---|---|---|---|---|---|---|---|
| A' | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| B-MIN | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

The comparison was controlled: both tracks used the same seven core input
records (five representative forms plus two negative controls), the same two
admitted source SHAs, the same locators and verbatim excerpts, the same project
facts, the same PC validator, and the same result shape. The machine-readable
details are in `02_RESULTS.json`.

## A' result

A' preserved source identity, version/jurisdiction metadata, locator, raw
evidence, SHA-256, and generic metadata. It correctly failed closed when it
could not resolve applicability, but it could not produce the required
positive professional conclusions for RF-01..RF-05 or the extension.

The failures are representation failures, not retrieval failures:

- PC-01: no explicit positive scope.
- PC-02: no explicit material condition / exception distinction.
- PC-03: no observable SEAM-02 applicability responsibility.
- PC-04: no operand/modifier/formula/result trace for RF-05.
- PC-05: evidence exists, but applicability cannot be separated from evidence
  without semantic structure.
- PC-06: the missing-operand control cannot be identified as an unsupported
  numeric rule from A' alone; it fails closed for the wrong unresolved reason.
- PC-07: unresolved applicability is fail-closed.

Adding these meanings as generic metadata would hide typed semantics under A'
and would no longer be A'. Adding family- or clause-specific runtime branches
would violate the experiment contract.

## B-MIN result

B-MIN passed all five representative forms and both negative controls using
the same generic predicate evaluator and the same result contract. RF-05
returned a numeric trace with operand `600`, modifier `0.02`, formula
`required_motor_spaces * visitor_min_ratio`, result `12`, and the advisory cap
`20`. The missing-operand control returned `FAIL_CLOSED` with no conclusion
and `unsupported_numeric`. The unresolved-scope control returned
`FAIL_CLOSED` with `unresolved_applicability`.

The observed B-MIN groups are:

| Group | Observed role | Ablation result |
|---|---|---|
| G-BASE | source/version/locator/raw evidence/SHA audit chain | removing it fails PC-05 and PC-07 |
| G-SCOPE | positive scope and exceptions | removing it fails applicability, condition, and evidence/applicability separation |
| G-CONDITION | condition predicates, outcomes, and SEAM-02 ownership | removing it fails condition, responsibility, and applicability separation |
| G-NUMERIC | numeric operands, modifiers, formula, result | removing it fails RF-05 PC-04 and numeric fail-closed handling |

All four groups caused a material mandatory-contract failure when removed;
therefore no tested group is removed or deferred by this experiment. This is
only evidence for these groups and these controls, not a claim that any future
field is permanently required.

## Same-structure data-only extension

RF-EXT-01 added one DBJ33T1021-2023 direct-clause record at §4.5.1. No
mechanism code or schema change occurred: the implementation hash was equal
before and after (`3279d566d65958e61a220bf076c02eb45cfc606af5bc5e07968d3abe8e815206`),
and the existing group shape was reused.

A' remained unable to produce a positive professional result. B-MIN produced
the expected conclusion and passed the shared contract. This is a local
same-structure probe only; it is not F-EXP-01 unseen-source testing.

## Hidden-knowledge check

The scan found no source ID, tested locator, regulation-family term, or
clause-specific branch in A' adapter code, B-MIN adapter code, or the shared
validator. Result: A' PASS, B-MIN PASS, shared validator PASS. Regulation
semantics reside in the lab data records for B-MIN; the validator remains
generic and declarative.

## Code surface and representation complexity

Track-specific adapter surface was 21 lines for A' and 28 lines for B-MIN.
The shared lab mechanism was 406 lines across model, runner, and validator;
this is experiment harness code, not BREA or Platform code.

A' has one represented group (G-BASE) and lower representation complexity, but
cannot satisfy the mandatory professional contract. B-MIN has four explicit
field groups and slightly more adapter surface, while preserving the same
generic mechanism and making source → scope/condition → conclusion and
source → numeric trace auditable. The ablation result is the evidence that the
extra groups were not retained merely for possible future usefulness.

## Decision candidate

`B_MIN_EVIDENCED`

Basis: A' fails mandatory PC-01..PC-06 for a representation reason; B-MIN
passes the same contracts; repairing A' would require introducing the very
typed semantics it excludes or hiding them in generic metadata; all retained
B-MIN groups map to observed failures; and the same-structure extension is
data-only. External Experiment Review must decide whether this candidate is
accepted, rejected, or limited. No final architecture is declared here.

## Limitations

This experiment uses five representative forms from two already admitted local
sources and one same-structure extension. It does not test unseen sources,
source admission, retrieval recall, OCR quality, conflicting editions,
cross-source composition, user uploads, Web, LLM behavior, or long-term
product readiness. It also does not form BREA v0.4 or any new Candidate.

## Protected boundaries and execution evidence

PASS: only this F-EXP-03 directory was written. BREA v0.1, BREA v0.2, frozen
BREA v0.3, Platform Core, Runtime, RuntimeAdapter, Enterprise extensions, and
`main` were not modified. No raw corpus was committed. F-EXP-01 and E2-C were
not executed or created. No LLM, Dense Retrieval, Vector DB, Web, or runtime
change was used. The five experiment tests passed; detailed consistency,
hidden-knowledge, extension-hash, and repository checks remain in test output,
`02_RESULTS.json`, and the execution trace rather than separate reports.
