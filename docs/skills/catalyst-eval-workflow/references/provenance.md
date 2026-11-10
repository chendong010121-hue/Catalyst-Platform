# Source and adaptation

Official reference: anthropics/skills @ dbd4588f9e1033efb41dad4bef2f7947c8993d44, files under
skills/claude-api/shared/evals/: build-eval.md, eval-audit.md, eval-hillclimb.md.
Frozen originals and SHA-256 manifest are at
E:/Catalyst_Research/eval-workflow-20261026/upstream/ and UPSTREAM_MANIFEST.json.
The supplied per-skill LICENSE.txt is Apache License 2.0; retained as LICENSE.txt.
This local workflow is modified provider-neutral guidance, not an official Anthropic
plugin, not a global replacement and not an import of their Runner/SDK.

## Adopted mechanisms
- build-eval: reuse existing entry/evaluator; explicit inputs and grading sign-off;
  outcome-first cases, full trajectories, cost and timing, no framework mandate.
- eval-audit: product parity, separate infrastructure/scaffold limits from model,
  oracle/null controls, independent truth, traceable metrics and noise checks.
- hillclimb: valid measurement first, one causal change, frozen Parent/allowed scope,
  train/held-out separation, guardrails, feedback, explicit stopping and provenance.

## Deliberate changes
- Keep Catalyst DeepSeek/Provider/P0; no Anthropic SDK or model substitution.
- Keep current durable dispatch ledger, Agent loop, Evaluator and R4; no copied runner.
- Original historical grades/transcripts never overwritten; rescore is new derivative.
- No implied replay after timeout or missing rows; reconcile dispatch and require scope.
- Approved financial ceiling is a hard send gate; no automatic budget extension.
- No automatic Judge, paid pilot, fan-out, maximal concurrency, model migration,
  extra full baseline or cross-model confirmation.
- Explicitly preserve task completion failures while separately qualifying the
  semantic denominator; no quiet removal of product/tool errors to improve a score.
- Catalyst-autonomous proposals cannot be replaced with Codex semantic edits.
- Current preparation grants no live execution or publication permission.

Upstream exact source:
https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/claude-api/shared/evals
