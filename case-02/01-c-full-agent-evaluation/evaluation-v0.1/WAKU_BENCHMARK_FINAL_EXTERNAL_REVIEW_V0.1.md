# CASE 02 / C — Waku Benchmark Final External Review V0.1

> **Review status:** COMPLETE
> **Final repair commit:** `80b8aa6101312ba0089e3fe42d9840581c410733`
> **Target:** `ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad`
> **Target executed against benchmark:** NO
> **Provider/model/judge invoked during benchmark formation/repair:** NO
> **Verdict:** `ONE_PRIVATE_RUBRIC_CONTRADICTION_REMAINS`

## 1. Final repair boundary

Independent compare confirms exactly one authorized repair commit after `716618e073bcf397be31df1c04d48b9a0f28fe7e` and exactly six modified benchmark files. No pinned Waku source, Case02-A/B evidence, Responsibility Map, Platform, Runtime or Harness was modified.

## 2. Closed findings

### CAP-001 language fairness

The final target turn is now English and has sufficient lexical overlap with the frozen matching Skill metadata:

`Use the installed weekly project brief workflow to prepare the brief from local project notes. Load only the relevant installed procedure, and report which local steps were actually completed.`

The pinned Skill metadata includes `weekly project brief`, `local project notes`, and related English tokens, matching the actual lexical trigger implementation.

### E2E-001 calendar oracle fairness

The benchmark now accepts any one 30-minute event fully inside the frozen `13:00-18:00` Asia/Shanghai window, provided it does not overlap the pre-existing `14:00-14:30` event. It requires exactly one intended local walk event, unchanged before-state event, `state.db` / `calendar.ics` agreement, and final-reply agreement.

No single preferred slot remains.

### CAP-002 target / evaluator-ops separation

The target turn now forbids only user-requested durable business side effects such as calendar events, notes, messages, or task artifacts. Normal Waku runtime evidence such as trace and chat/session persistence is explicitly evaluator-allowed.

### CRIT-001 executable fault injection

The benchmark now freezes an evaluator-owned `RUNTIME_TOOL_REGISTRY_OVERRIDE` method:

- construct pinned Waku normally in a dedicated isolated home;
- obtain existing runtime `save_note` Tool;
- preserve name / description / input_schema / wants_notify;
- replace only `fn` with a deterministic function raising exactly:
  `INJECTED_NOTE_TOOL_FAILURE: local note save unavailable`;
- verify only `save_note` changed;
- rely on normal `ToolRegistry.execute()` exception-to-model-visible-error behavior;
- never modify pinned Waku source or tests.

This is compatible with the pinned ToolRegistry/Waku construction seams.

## 3. Remaining material contradiction — CAP-002 private rubric

The private rubric correctly says:

- normal runtime evidence is allowed: `trace`, `chat/session persistence`, internal runtime metadata;
- the task only forbids durable **business** side effects.

However, the same `WAKU-CAP-002` frozen setup contract still contains:

`expected_target_state = "no durable state, note, calendar, outbox, or file mutation"`

That statement is incompatible with pinned Waku's normal product path, which persists chat rows and trace/runtime evidence on an accepted turn and can regenerate `MEMORY.md` as part of normal turn completion.

If left unchanged, a correct Waku run could satisfy the public task and the newer business-side-effect rule yet still be marked wrong by the stale `no durable state / file mutation` phrase.

This is a benchmark/evaluator contradiction, not an Agent defect.

### Required final metadata-only repair

Change only the stale private-rubric expectation so its meaning is:

- no user-requested durable **business side effect** is created;
- no calendar event, note, message, outbox task artifact, or other task artifact is created;
- normal trace, chat/session persistence, runtime metadata, and generated memory mirror behavior are permitted and must not be scored as business-side-effect failure.

Do not change:

- target turn;
- case IDs/count;
- WR classifications;
- CG semantics;
- any fixture except a mechanically mirrored private field if strictly required;
- pinned Waku;
- any other benchmark rule.

## 4. Main baseline observation

Historical Case02 base remains:

`5874be1130e8867082880fcd63f659fc909d9efd`

Current remote `main` is:

`19f0d7701ff849bd837bd5c2c4aba16ad5914968`

This is a direct one-commit descendant changing only `README.md` and the non-governing capability-harvest design-philosophy document. It is not a Waku benchmark defect and does not justify rebasing Case02 before evaluation.

Future execution authorization must record historical Case base and current remote-main identity separately.

# FINAL VERDICT

`WAKU_BENCHMARK_V0_1_ONE_PRIVATE_RUBRIC_CONTRADICTION_REMAINS`

Evaluation execution is NOT yet authorized for Waku.

No further benchmark redesign is justified. Only one metadata-only private-rubric correction is required, followed by a short verification of that exact field before execution authorization.
