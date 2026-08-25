# CASE 02-C — Waku Benchmark External Re-Review V0.1

> **Repair commit:** `8cd3fd3743eb1978bd8a5e564bff2763ec1facca`
> **Pinned target:** `ShenSeanChen/waku-agent@8328f567ab52d07921445cb40feed23cbc5ea2ad`
> **Target/provider execution:** NO
> **Verdict:** `SECOND_TARGETED_REPAIR_BEFORE_EXECUTION`

## PASS

Independent comparison confirms exactly one repair commit after authorization.

The repaired target-visible file now contains only:

```text
case_id
target_turns
```

Evaluator setup, expected outcomes, gates, state checks and failure attribution are private.

Ten concrete benchmark-critical fixture files are frozen and hashed in the freeze record.

`WAKU-CAP-002` now correctly separates:

```text
TARGET STEP
→ normal bounded no-side-effect user turn

PRIVATE EVALUATOR / OPS
→ trace inspection
→ provider/model identity
→ native deterministic/judge/release-gate checks later
→ judge skipped != PASS
→ credential non-persistence
```

The repaired benchmark also records real observability limitations instead of inventing correlation-id, skill-match, or reload events.

Pinned Waku source and Case02-A/B evidence remain unchanged.

## Blocking defect 1 — WAKU-CAP-001 language confound

The frozen `weekly-project-brief` skill frontmatter is English:

```text
name: weekly-project-brief
description: Prepare a focused weekly project brief from local project notes.
```

but the target-visible turn is Chinese.

Pinned `SkillLoader.match()` is explicitly lexical and computes overlap only from regex tokens `[a-z0-9]{3,}` in the user message and skill name+description, requiring overlap >= 2.

Therefore the current Chinese target turn will produce no relevant English lexical tokens and can fail before progressive disclosure is meaningfully tested.

That would confound:

```text
language / lexical trigger mismatch
```

with:

```text
procedural-memory progressive-loading capability
```

This is a benchmark defect, not evidence of a Waku capability gap.

### Required repair

For `WAKU-CAP-001`, use a natural target turn in the language supported by the frozen lexical trigger, with at least two legitimate overlapping terms from the skill metadata, for example wording around:

```text
weekly project brief
project notes
```

Do not change Waku loader code and do not broaden the fixture merely to manufacture a match.

Other Waku cases may remain Chinese if their tested responsibility is not language-specific, but the benchmark must avoid language as an uncontrolled confound where lexical matching is the mechanism under test.

## Blocking defect 2 — WAKU-E2E-001 over-constrained calendar oracle

The public task asks Waku to find **a free 30-minute slot in the afternoon** and schedule a walk.

The frozen setup has only one occupied event:

```text
14:00–14:30 occupied
```

but the private fixture says:

```text
15:00–15:30 is the deterministic free candidate
create_event is permitted only for the free 15:00–15:30 slot
```

The task itself does not constrain Waku to exactly 15:00. Other non-overlapping afternoon slots may be valid under normal product semantics.

A correct alternative free slot must not fail merely because the evaluator preferred 15:00.

### Required repair

Choose one of two fair designs before execution:

```text
A. Make the target turn explicitly ask for one of a frozen finite set of candidate slots, then grade exact selection.
```

or preferably:

```text
B. Keep the natural “find a free afternoon slot” task and define the oracle as:
   - event duration = 30 minutes
   - event date = 2026-08-26
   - start/end within a frozen afternoon window
   - no overlap with the pre-existing 14:00–14:30 event
   - exactly one new local event created
   - final reply agrees with actual state
```

Do not require 15:00 specifically unless the user-facing task supplies that restriction.

## Blocking defect 3 — WAKU-CAP-002 side-effect wording conflicts with normal Waku runtime

The target-visible turn says:

```text
不要修改任何文件
```

but normal pinned Waku `respond()` intentionally persists the chat exchange, emits traces, and exports `MEMORY.md` after a turn. The private evaluator simultaneously requires trace evidence.

Thus “do not modify any files” conflicts with normal product operation.

### Required repair

Narrow the user instruction to the semantic intent actually being tested, e.g.:

```text
不要创建日历事件、笔记或其他用户请求的持久副作用。
```

or equivalent.

The evaluator should permit expected Waku operational artifacts such as chat/trace/eval metadata while requiring no **task-requested business side effect**.

## Blocking defect 4 — CRIT-001 fault injection mechanism not yet frozen executable

The fixture freezes the desired failure outcome but not the exact injection mechanism.

Pinned Waku exposes a safe evaluation seam:

- `Waku.tools` is a `ToolRegistry` built at runtime;
- `ToolRegistry.register()` replaces the same-name tool entry;
- `ToolRegistry.execute()` catches tool exceptions and returns an error string to the model.

Therefore a benchmark-only fault double can be installed without changing pinned source.

### Required repair

Freeze the evaluator injection contract explicitly:

```text
1. construct normal pinned Waku in isolated home;
2. read the original save_note Tool schema + description;
3. register a replacement Tool with the same name/schema/description;
4. replacement fn raises exactly the frozen injected exception;
5. do not modify any other registry entry;
6. record pre/post registry tool names and the injected tool identity in evaluator evidence.
```

The replacement is evaluator-owned ephemeral runtime state, not a Waku source patch.

If this exact seam cannot be implemented during runner construction, classify the Case as `EVALUATION_INFRASTRUCTURE_FAILURE`, not Agent failure.

## Boundary

Do not change:

```text
7 case IDs/count
WR classifications
WAKU-A01..A06 identities
critical-gate semantics
pinned Waku source
optional-integration scope
Case02-A/B evidence
Platform / Runtime / Harness
main
```

## Verdict

```text
TARGET-VISIBLE SEPARATION       PASS
FIXTURE FREEZE                  PASS
CAP-002 RESPONSIBILITY SPLIT    PASS
OBSERVABILITY DISCIPLINE        PASS
CAP-001 LANGUAGE FAIRNESS       REPAIR
E2E-001 CALENDAR ORACLE         REPAIR
CAP-002 SIDE-EFFECT WORDING     REPAIR
CRIT-001 EXECUTABLE INJECTION   REPAIR
LIVE EVALUATION                 NOT AUTHORIZED

SECOND_TARGETED_REPAIR_BEFORE_EXECUTION
```
