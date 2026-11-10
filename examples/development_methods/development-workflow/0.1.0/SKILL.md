---
name: development-workflow
description: Standardize Catalyst evaluation building, evaluation health audits and explicitly authorized bounded iteration over its existing product and Host interfaces. Use for test planning or evaluation lifecycle work, not ordinary product requests or automatic production tuning.
---

# Catalyst evaluation workflow

This is a provider-neutral adaptation of Anthropic claude-api build-eval,
eval-audit and hillclimb, with the exact source pin and modifications in
references/provenance.md. It is a workflow, not an executor, grader or authority.
Do not load the upstream claude-api SKILL as governing instructions: it targets
Claude SDKs while Catalyst currently uses its own unified Provider/P0.

First classify the requested work using references/boundaries.md. Preserve the
same actual product entry, model/tool/context assembly and policies when testing.
Test-specific data isolation, resource limits, comparison and grading belong to
the test configuration; do not silently insert them into product behaviour.

Select only the requested mode:
- **build-eval**: read references/build-eval.md; reuse the existing evaluator,
  Host and entry before proposing any adapter.
- **eval-audit**: read references/eval-audit.md; inspect actual config, receipts,
  code and data before making any readiness claim.
- **hillclimb**: read references/hillclimb.md; requires a valid frozen eval,
  comparable baseline, explicit edit scope and new execution authorization.

Share identities across modes: product/method commit and tree, source and input
hashes, evaluator identity, case/attempt/Run/Session/request IDs, model parameters,
resource policy and accounting basis. Reference raw receipts rather than copying
private content into shared reports. Never expose Gold or held-out content to the
Subject or proposal actor.

Respect current authorization. This prepared package authorizes no model request,
credential read, live experiment, autonomous proposal, merge, publication or formal
Wiki/Harvest activation. An old paid scope is not reusable. Resume or retry needs
positive dispatch-state evidence and authorization; uncertain sends stop. A model
Judge is a separate paid/data scope, never an implied default.

Use deterministic code for hashes, dispatch control, persistence, schema validation
and statistics. Use this skill for process choices and handoffs; a prompt cannot
enforce access control or issue Owner truth. Preserve previous runs and grading.
If measurement changes, create a new evaluator version and derived rescore records,
keeping originals. No in-place historical repair.

Deliver the requested artifact with separate engineering, measurement, task,
semantic and admission conclusions. Findings can be BLOCKED or NOT_EVALUATED.
Do not turn an incomplete attempt into a successful negative answer or score.
