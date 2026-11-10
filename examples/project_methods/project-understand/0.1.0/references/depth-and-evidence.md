# Depth and evidence completion

| Depth | Required result | Closure |
|---|---|---|
| D0 | Exact source/version, object type, entry, declarations, license location, read/not-read | Identify whether further analysis is justified; missing identity means identification incomplete |
| D1 | Target-related responsibility and input/output, necessary control/data/state chain, atomic claims and locators | Each key question SUPPORTED or EXPLICITLY_UNRESOLVED; decision-critical unknowns require NEEDS_EVIDENCE or BLOCKED |
| D2 | Reuse boundary, dependencies/environment/effects, conditions/exceptions, migration loss and existing assets | Explicit obligations or cannot-extract/pending-review; never equate by similar names |
| D3 | Actually observed inputs/outputs/environment/version/failure/effect receipts | Separate execution permission and records required; describe only what ran |

The model chooses subquestions, explains responsibility, requests evidence, revises
claims, and proposes stopping. The method guides those choices. Deterministic host
code owns identity, admitted paths, hashes, AST, resource limits, structural/reference
checks and lifecycle. Independent Evaluation checks source support and quality; it
does not rewrite the producer candidate to pass. Harvest may retain or return NO_OP
without re-reading the repository or granting execution permission.

Use exact evidence IDs and source locators. A valid reference proves location, not
semantic support. Structural ANSWERED coverage is a signal only. Keep unresolved
conditions and counterexamples visible. Distinguish analysis_finished from achieved
depth, readiness and evaluation_status. No paid calls or execution are authorized by
this reference.
