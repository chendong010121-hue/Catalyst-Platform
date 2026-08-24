# CASE 02-A — External Review Candidate

## Stage verdict

| Required result | Verdict |
|---|---|
| Understanding | `UNDERSTANDING_SUFFICIENT_FOR_STAGE` |
| Functional decomposition | `PASS — responsibility-first, independently explained units` |
| Valuable asset count | `6` |
| Asset catalog status | `FROZEN_FOR_REDISCOVERY` |
| Asset rediscovery | `PASS — all three probes resolved from catalog records only` |
| Method portability | `METHOD_PORTABLE_WITH_REPAIR` |
| Integration | `ASSESSED_ONLY — no adapter created` |
| Waku mutation | `NONE` |
| Catalyst Platform/Core/Runtime/main change | `NONE` |
| Case 02-B | `NOT AUTHORIZED / NOT STARTED` |

## Evidence boundary

The source baseline was `ShenSeanChen/waku-agent @ 8328f567ab52d07921445cb40feed23cbc5ea2ad`, inspected from `E:\试验场地\agent-lab\waku-agent`. The Case branch was `case-02 @ abe14e56867b37f8d6fde45982572cf79f8388e1`.

The source inspection recovered declared intent against implementation and deterministic tests. The local state DB was opened read-only and showed the expected Waku schema with zero current business rows. The active local `.env` did not provide a DeepSeek key. Model-dependent claims therefore remain `NOT LIVE-VERIFIED`, not structural blockers.

The catalog was frozen before this review’s rediscovery section. The rediscovery statements below were matched against `CASE_02_WAKU_ASSET_CATALOG_V0.1.json` only. No Waku source, source test, `.env`, `.waku`, or trace was read for rediscovery, and no asset was rebuilt, copied, or executed.

## Functional decomposition quality

The decomposition is responsibility-first rather than file-first. It distinguishes:

- application orchestration from gateway transport;
- ephemeral session/working memory from durable facts, episodes, chats, traces, and reports;
- retrieval policy from concrete memory stores;
- loop control from provider wire normalization and tool side effects;
- graph structure from the normal open-ended loop;
- operational evidence from business state and from release authorization;
- Waku product-specific assumptions from mechanisms with independent future value.

The quality threshold is met because each material unit in `02_WAKU_MECHANISM_DECONSTRUCTION.md` has the required fields, an owner, state behavior, external dependencies, boundary, evidence anchors, replacement rationale, coupling, and confidence. Pseudo-units were not created for every folder, and clearly replaceable responsibilities were not merged merely because Waku wires them together.

## Valuable asset decision

Six mechanisms entered the catalog:

1. `WAKU-A01` — retrieval-gated memory query selection;
2. `WAKU-A02` — bounded reason-tool-observe loop;
3. `WAKU-A03` — observer fan-out with append-only turn trace;
4. `WAKU-A04` — separated deterministic completion, model quality judge, and release gate;
5. `WAKU-A05` — bounded wave graph with code-owned routing and disjoint state writes;
6. `WAKU-A06` — progressive procedural-memory loading.

The catalog intentionally excludes Waku’s personal calendar/message/note tools, provider IDs and wire details, SQLite/FTS and hosted-memory implementations, dashboard presentation code, local persona/configuration, and channel-specific delivery code. Those are either Waku-specific implementations, reference-only evidence, or integration context without independent case-local reuse value yet.

## Rediscovery pass — catalog only

### Need A — avoid retrieving long-term memory on every Agent turn

- `matched_asset_ids`: `["WAKU-A01"]`
- `why_relevant`: `WAKU-A01` directly addresses the stated problem. It separates a cheap pre-retrieval decision from the semantic/episodic stores, carries a query only when retrieval is selected, and records a reason. The catalog explicitly says the decision is per-turn and does not own the stores.
- `reuse_preconditions`: Define the target case’s memory scope, retrieval policy, store/query contract, cheap decision path, fail-open behavior, false-positive cost, and decision audit fields. Treat the Waku personal-assistant assumptions as non-portable until replaced.
- `why_not_directly_platform_core`: Retrieval policy depends on the target product’s memory meaning, privacy, cost, false-positive/false-negative tradeoff, and store interface. Promoting it to core would turn one external Agent’s policy into an unauthorized universal Memory standard.
- `next_action_if_reuse_is_authorized`: Create a separately authorized case-local proof that uses a fake/deterministic gate and a declared store seam; measure skip/retrieve behavior, verify provenance of the decision, and test gate failure without executing Waku or changing Platform Core in this stage.

### Need B — minimal reason → tool → observe → reason loop with hard termination

- `matched_asset_ids`: `["WAKU-A02"]`
- `why_relevant`: `WAKU-A02` describes exactly the minimal loop: model reason, tool execution, result observation through working context, repeat, natural stop when no tool call, and explicit hard stop at a configured iteration bound. `WAKU-A05` is not a primary match because a graph is for known structure around a loop, not the open-ended loop itself.
- `reuse_preconditions`: Define the model/tool message contract, tool-call identity/correlation, side-effect bounds, iteration/token limits, timeout/cancellation policy, and distinction between a natural answer and a hard-stop outcome.
- `why_not_directly_platform_core`: A loop with tool side effects is an execution/runtime responsibility. Making Waku’s implementation the Platform Core loop would silently import its message shape, error text, tool semantics, and lack of broader cancellation/identity governance.
- `next_action_if_reuse_is_authorized`: Write a case-local contract and offline scripted proof for one bounded loop, including no-tool completion, tool-result feedback, repeated-call handling, hard termination, and event/provenance output. Do not invoke or reconstruct `WAKU-A02` during Case 02-A.

### Need C — deterministic checks plus model-based quality evaluation before release

- `matched_asset_ids`: `["WAKU-A04", "WAKU-A03"]`
- `why_relevant`: `WAKU-A04` directly separates deterministic completion, model-based quality judging, and release-gate composition. `WAKU-A03` is a complementary match because a release decision needs inspectable run/evaluation evidence and the catalog describes its event/usage trace boundary.
- `reuse_preconditions`: Define deterministic observable checks, quality rubric/threshold, evaluator identity and independence, missing-key status, report retention, trace redaction, and the authorization owner for the release decision.
- `why_not_directly_platform_core`: The pass criteria, rubric, judge model, release threshold, and evidence retention are product- and case-specific. The mechanism is a governed evaluation pattern, not a universal platform release authority; the trace asset is local evidence, not tamper-proof provenance.
- `next_action_if_reuse_is_authorized`: Form a case-local evaluation contract with one deterministic fixture and one separately governed model-judge fixture; run them independently, preserve `pass/fail/skipped/not-live-verified` states, and only then decide whether a future release proof is warranted.

## Method portability

**`METHOD_PORTABLE_WITH_REPAIR`**

The core method transferred: source identity was pinned; declared intent was checked against implementation; responsibilities were decomposed without using the seeded example list as an answer key; mechanisms were separated from Waku-specific HOW; only six independent assets were preserved; and all three needs were rediscovered from the frozen catalog without source rescanning.

The repair is governance hardening, not a failure of the understanding method:

1. Every future run should require a machine-checkable evidence tier on each claim (`STRUCTURAL`, `OFFLINE_TESTED`, `LOCAL_OPERATIONAL`, `LIVE_VERIFIED`, `NOT_LIVE-VERIFIED`).
2. The source-read cutover must be recorded as a hard phase transition and enforced by the work protocol; the catalog needs a frozen hash/status before discovery begins.
3. Integration seams must require identity, source commit, actor, state side effects, and failure semantics before a future adapter proof.
4. The local smoke harness needs a platform-neutral subprocess fixture; this run’s four `python3`/shebang failures are environment-specific and must not be conflated with agent understanding.

These repairs preserve portability while preventing the method from silently promoting source knowledge into platform authority.

## Integration seam assessment

The five required surfaces were assessed in `02_WAKU_MECHANISM_DECONSTRUCTION.md`:

- `POST /api/chat`: useful local final-result seam, but it executes a full Waku turn and has no external identity/provenance contract.
- `POST /api/chat/stream`: useful event-rich SSE seam, but event names/payloads, disconnect behavior, and security assumptions are Waku-local.
- CLI: the smallest transport seam, with simple text I/O and `source="cli"`; local process identity and exit/cancellation policy remain implicit.
- trace/event: valuable evidence seam; current JSONL is inspectable local evidence, not a governed external provenance ledger.
- state/provenance: Waku’s SQLite/session/meta model is suitable for local observation, not an external canonical state or identity authority.

Minimum future adapter responsibility, if ever authorized, is to observe and translate identity, correlation, source commit, state side effects, failure/timeout semantics, security, and evidence status. No adapter was created.

## Protected boundaries and unresolved questions

Protected boundaries:

- Waku source is read-only and remains external.
- No Waku code was copied or forked.
- No Catalyst adapter, registry entry, Platform Core change, Runtime change, RuntimeAdapter change, or main change was made.
- No generic Memory/Tool/Workflow standard was created.
- No reconstructed asset was implemented or executed.
- Case 02-B was not entered.

Unresolved questions intentionally deferred:

- Which Catalyst-governed identity and provenance fields should surround an unchanged external Waku invocation?
- Which Waku side effects, if any, could be authorized in a bounded integration proof?
- Should a future proof use an unchanged wrapper, a Catalyst-native reconstruction, a state/provenance observation proof, or no adoption?
- Can the local operational contracts be made platform-neutral without importing Waku’s personal-assistant assumptions?

Those are Case 02-B choices and require a new authorization. They are not answered by this stage.

## Stop statement

CASE 02-A is complete at the boundary:

```text
understand → decompose → classify → assetize → freeze → rediscover → assess seams → review → stop
```

No further implementation is authorized by this review.
