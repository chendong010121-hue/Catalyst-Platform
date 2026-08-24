# CASE 02-A — Waku Mechanism Deconstruction

## Decomposition rule

The units below are responsibility units, not a directory inventory. A unit exists because it owns an independently explainable behavior, state transition, boundary, or replacement decision. Files are evidence locations, not the unit definition.

## Functional responsibility units

### FU-01 — Application assembly and turn orchestration

- `functional_unit_id`: `FU-01`
- `name`: Application assembly and turn orchestration
- `problem_solved`: Build one coherent Waku from configuration, persistence, model client, memory, tools, session, and observability, then run the complete turn lifecycle.
- `observable_behavior`: `Waku.respond()` creates the composed observer, opens a trace turn, optionally tries graph triage, falls back to the full path, persists the exchange, triggers consolidation/export, and closes the turn trace.
- `responsibility_owner`: `waku/app.py::Waku`
- `inputs`: settings, optional client/connection injection, user message, gateway source, observer, stream flag
- `outputs`: `LoopResult`, persisted turn, turn metadata, trace events
- `state_read`: settings, configured home, session/memory state
- `state_written`: session history, chat log, consolidation/export side effects, trace/usage through observers
- `external_dependencies`: SQLite connection, provider client, configured stores, optional graph and integrations
- `implementation_locations`: `waku/app.py::Waku.__init__`, `respond`, `_run_full_turn`, `_respond_via_graph`
- `public_or_private_boundary`: public application boundary for gateways; internal assembly details are private
- `evidence_refs`: `waku/app.py::Waku.respond`; `waku/app.py::Waku._run_full_turn`; `evals/helpers.py::make_waku`
- `replaceability`: medium; the responsibility is portable, but the Waku-specific lifecycle and injected collaborators must be preserved
- `coupling`: high inward orchestration coupling; low gateway coupling because the gateway sees `respond()`
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-02 — Gateway and channel delivery

- `functional_unit_id`: `FU-02`
- `name`: Gateway and channel delivery
- `problem_solved`: Move user input and Agent output across CLI, browser, and optional channel transports without reimplementing the Agent turn.
- `observable_behavior`: CLI loops over text input; dashboard exposes JSON/SSE HTTP routes; optional channels deliver through gateway runners and tag source/identity. Dashboard `/api/chat` and `/api/chat/stream` share `chat_stream()`.
- `responsibility_owner`: `waku/gateway/*`, `waku/ops/dashboard.py::chat`, `chat_stream`, `Handler`, `waku/__main__.py`
- `inputs`: text/audio/HTTP JSON/channel events, session/source identity, optional credentials
- `outputs`: console reply, JSON result, SSE event sequence, channel delivery
- `state_read`: settings, current agent/session, read-only dashboard data
- `state_written`: indirectly through `Waku.respond()`; channel delivery/outbox/integration side effects are gateway-specific
- `external_dependencies`: stdlib HTTP server, terminal, optional channel SDKs/tokens, browser client
- `implementation_locations`: `waku/gateway/cli.py`, `waku/gateway/runner.py`, `waku/ops/dashboard.py`, `waku/__main__.py`
- `public_or_private_boundary`: public transport boundary; channel-specific polling/auth/delivery are private implementations
- `evidence_refs`: `waku/gateway/cli.py::main`; `waku/ops/dashboard.py::chat`, `chat_stream`, `Handler.do_POST`; `evals/deterministic/test_dashboard_routes.py`
- `replaceability`: high for transport; low for any adapter that assumes Waku’s exact event/result payload without translation
- `coupling`: medium to `Waku.respond()` and event vocabulary; optional channels have external identity/security coupling
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-03 — Working-memory assembly and session lifecycle

- `functional_unit_id`: `FU-03`
- `name`: Working-memory assembly and session lifecycle
- `problem_solved`: Construct a bounded model context from persona, current time/model identity, relevant memory, relevant procedures, and recent conversation; support new/switchable chat sessions.
- `observable_behavior`: `Session.build_system()` loads/creates `SOUL.md`, adds current local time and model identity, invokes gated retrieval and skill matching, then `respond()` adds a bounded history window and current message. `start_new()` clears history; `switch()` reloads a recent persisted tail.
- `responsibility_owner`: `waku/runtime/session.py::Session`
- `inputs`: settings, memory facade, user message, session id, persisted session history
- `outputs`: system prompt, bounded message list, session history records
- `state_read`: `SOUL.md`, facts/episodes/skills through memory, chat log through session history
- `state_written`: in-memory history; later `Memory.log_chat()` receives the turn
- `external_dependencies`: local filesystem, memory facade, datetime
- `implementation_locations`: `waku/runtime/session.py::load_soul`, `Session.build_system`, `add_exchange`, `start_new`, `switch`; `waku/app.py::_run_full_turn`
- `public_or_private_boundary`: internal runtime boundary exposed to application, not to the model as a callable service
- `evidence_refs`: `waku/runtime/session.py::Session`; `waku/config.py::history_turns`; `evals/deterministic/test_working_memory.py`
- `replaceability`: medium-high if the context contract and boundedness are preserved
- `coupling`: high to Waku persona and memory shapes; intentionally low to provider wire format
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-04 — Bounded Agent loop

- `functional_unit_id`: `FU-04`
- `name`: Reason → tool → observe loop
- `problem_solved`: Execute an open-ended model-led turn with tools while guaranteeing a natural or hard termination.
- `observable_behavior`: For each iteration the model receives messages/tool schemas; assistant content is appended; each tool call is executed and observed; tool results are appended; no-tool response returns a reply; reaching `max_iterations` returns a hard-stop message.
- `responsibility_owner`: `waku/loop/agent.py::run_loop`
- `inputs`: Anthropic-shaped client, model, system, messages, ToolRegistry, bounds, observer, stream flag
- `outputs`: `LoopResult(reply, tool_calls, iterations)`, event stream, mutated in-memory messages
- `state_read`: current working messages and tool schemas
- `state_written`: working messages only; durable persistence is outside the loop
- `external_dependencies`: model client, tool registry, observer
- `implementation_locations`: `waku/loop/agent.py::run_loop`, `LoopResult`
- `public_or_private_boundary`: public responsibility seam used by app and graph nodes; iteration internals are private
- `evidence_refs`: `waku/loop/agent.py::run_loop`; `evals/deterministic/test_tool_trigger.py::test_no_tool_turn_ends_loop_in_one_iteration`; `test_iteration_guardrail_stops_runaway_loop`
- `replaceability`: high as a bounded control responsibility; its message/tool contract is the critical interface
- `coupling`: medium to provider-shaped messages and tool registry; low to persistence
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-05 — Model-provider wire normalization

- `functional_unit_id`: `FU-05`
- `name`: Provider selection and wire-format normalization
- `problem_solved`: Let one loop dialect use multiple provider families and provider-specific endpoints/models.
- `observable_behavior`: Settings select a provider/key/model; `get_client()` validates provider/key/model family and returns a native Anthropic client or an OpenAI-compatible client that converts messages, tool calls, tool results, streaming, and usage into the loop’s expected shape.
- `responsibility_owner`: `waku/loop/models.py::get_client`, `OpenAICompatClient`
- `inputs`: Settings, env key/base URL/model values, provider catalog
- `outputs`: client with `.messages.create()` and optionally `.messages.stream()` in Anthropic-shaped form
- `state_read`: environment/configuration
- `state_written`: none in the provider seam; provider/network calls are external effects
- `external_dependencies`: Anthropic SDK, OpenAI SDK, remote model endpoints
- `implementation_locations`: `waku/loop/models.py::PROVIDERS`, `get_client`, `OpenAICompatClient`
- `public_or_private_boundary`: provider abstraction is a public internal seam; endpoint/model catalog details are private Waku configuration
- `evidence_refs`: `waku/loop/models.py::Provider`, `PROVIDERS`, `get_client`; `evals/deterministic/test_models.py`, `test_provider_base_urls.py`, `test_provider_disabled.py`
- `replaceability`: high if the loop-facing message contract is preserved
- `coupling`: high to provider SDKs and model IDs; low to memory/tool business semantics
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-06 — Tool description and safe execution

- `functional_unit_id`: `FU-06`
- `name`: Tool registry and execution boundary
- `problem_solved`: Expose callable capabilities to the model with schemas and turn tool failures into observable model input instead of crashing the loop.
- `observable_behavior`: A registered tool has name, description, JSON input schema, callable, and optional progress notification. `schemas()` supplies model-facing definitions; `execute()` looks up, invokes, catches exceptions, and returns text.
- `responsibility_owner`: `waku/tools/registry.py::ToolRegistry`; registration composition in `waku/tools/__init__.py::build_registry`
- `inputs`: Tool definitions, model tool-call name/arguments, observer
- `outputs`: tool schemas, string result, tool/progress events
- `state_read`: tool-specific state and optional integration credentials
- `state_written`: tool-specific effects such as SQLite rows, calendar files, outbox, external systems
- `external_dependencies`: tool callables, filesystem/SQLite, optional integrations/MCP
- `implementation_locations`: `waku/tools/registry.py`, `waku/tools/__init__.py`, `waku/tools/*`
- `public_or_private_boundary`: model-facing schema is public within a turn; callable implementation and side effects are private/tool-specific
- `evidence_refs`: `waku/tools/registry.py::Tool`, `ToolRegistry.execute`; `waku/tools/__init__.py::build_registry`; `evals/deterministic/test_tool_trigger.py`
- `replaceability`: high for the registry responsibility; each side-effecting tool requires independent governance
- `coupling`: medium to loop event contract; high to Waku-specific personal-assistant tools and integration credentials
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-07 — Retrieval decision gate

- `functional_unit_id`: `FU-07`
- `name`: Pre-retrieval decision and query selection
- `problem_solved`: Avoid querying long-term memory on turns where it is irrelevant, while retaining a fail-open path.
- `observable_behavior`: One small-model decision produces retrieve/skip, query, and reason. Skip returns no memory. Retrieve searches semantic plus episodic stores. Missing JSON or exceptions fail open to retrieval using the message.
- `responsibility_owner`: `waku/memory/retrieval_gate.py::should_retrieve`; facade integration in `waku/memory/__init__.py::Memory.gated_retrieve`
- `inputs`: message, small model client/id, observer
- `outputs`: decision/query/reason; retrieved prompt material when selected; gate event
- `state_read`: no durable state in the gate; stores are read downstream only
- `state_written`: none in gate; event capture is downstream
- `external_dependencies`: small model, fact store, episode store
- `implementation_locations`: `waku/memory/retrieval_gate.py`, `waku/memory/__init__.py`, `waku/runtime/session.py`
- `public_or_private_boundary`: private policy seam surfaced through a memory facade
- `evidence_refs`: catalog `WAKU-A01` source evidence; pre-freeze source anchors were recorded in that asset
- `replaceability`: high with explicit decision/query/reason and fail-open contract
- `coupling`: medium to personal-assistant memory prompt; low to concrete store implementations
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-08 — Semantic memory store

- `functional_unit_id`: `FU-08`
- `name`: Durable semantic fact storage and search
- `problem_solved`: Store durable facts and retrieve relevant facts for a personal assistant.
- `observable_behavior`: SQLite implementation inserts normalized facts, maintains FTS5 triggers, performs tokenized keyword search, and supports list/update/delete. A facade can select hosted implementations such as Supabase, Mem0, Zep, or LangMem.
- `responsibility_owner`: `waku/memory/semantic/store.py::SqliteFactStore`; backend selection in `waku/memory/__init__.py::Memory._make_fact_store`
- `inputs`: fact subject/content/source; search query/top-k; CRUD ids
- `outputs`: fact rows or formatted search results
- `state_read`: facts/FTS tables and configured backend
- `state_written`: facts and FTS index for SQLite; remote store for optional backends
- `external_dependencies`: SQLite FTS5 or optional hosted memory service/SDK
- `implementation_locations`: `waku/db.py::SCHEMA`, `waku/memory/semantic/store.py`, optional semantic backends
- `public_or_private_boundary`: store interface is a private Waku memory seam; content semantics are product-specific
- `evidence_refs`: `waku/db.py::SCHEMA`; `waku/memory/semantic/store.py::SqliteFactStore`; `evals/deterministic/test_memory_search.py`, `test_fact_store_conformance.py`
- `replaceability`: high at the backend seam, not a reason to standardize one memory model in Catalyst
- `coupling`: medium to FTS/query shape; high to personal facts and memory facade contract
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-09 — Episodic memory store

- `functional_unit_id`: `FU-09`
- `name`: Dated episode storage and relevance/recency search
- `problem_solved`: Preserve what happened and when separately from durable factual truth.
- `observable_behavior`: SQLite episodes store `happened_at` plus summary, search combines FTS relevance with date order, and recent episodes can be listed. Notion is an optional alternate store.
- `responsibility_owner`: `waku/memory/episodic/store.py::SqliteEpisodeStore`; backend selection in `Memory._make_episode_store`
- `inputs`: episode summary/date; query/top-k; episode id for deletion
- `outputs`: dated episode results
- `state_read`: episodes/FTS tables or Notion database
- `state_written`: local SQLite or optional Notion store
- `external_dependencies`: SQLite FTS5 or Notion API/SDK
- `implementation_locations`: `waku/db.py::SCHEMA`, `waku/memory/episodic/store.py`, `notion_store.py`
- `public_or_private_boundary`: private memory backend seam
- `evidence_refs`: `waku/db.py::SCHEMA`; `waku/memory/episodic/store.py::search`; `evals/deterministic/test_episodic_store_switch.py`
- `replaceability`: high at store interface; the semantic distinction between “fact” and “episode” is case-specific
- `coupling`: medium to query helper; high to Waku consolidation and personal-history assumptions
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-10 — Procedural instruction discovery

- `functional_unit_id`: `FU-10`
- `name`: Progressive procedural-memory loading
- `problem_solved`: Make repeatable instructions available without including every instruction body in every prompt.
- `observable_behavior`: Scan frontmatter/description for all eligible `SKILL.md` files, match by keyword overlap, return at most two matching skills, and load their bodies into the system prompt; changed files trigger refresh.
- `responsibility_owner`: `waku/memory/procedural/loader.py::SkillLoader`; facade integration in `Memory.matching_skills`
- `inputs`: skill directories/files, current message, maximum matches
- `outputs`: matched skill bodies and names
- `state_read`: skill file metadata and content
- `state_written`: in-memory parsed skill list/signature; installer separately writes local skill files
- `external_dependencies`: filesystem and SKILL.md format
- `implementation_locations`: `waku/memory/procedural/loader.py`, `installer.py`, repository/home `skills/`
- `public_or_private_boundary`: procedure-discovery seam; loaded text becomes model-visible prompt content
- `evidence_refs`: catalog `WAKU-A06` source evidence; pre-freeze anchors were recorded in that asset
- `replaceability`: high as a context-budget responsibility; matching and trust policy must be replaceable
- `coupling`: medium to prompt assembly; high to Waku’s SKILL.md convention
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-11 — Memory consolidation

- `functional_unit_id`: `FU-11`
- `name`: Thresholded chat-to-memory consolidation
- `problem_solved`: Batch recent chats into durable facts and one episode without running a summarizer on every exchange or losing the raw log on failure.
- `observable_behavior`: Count unconsolidated user/assistant rows; below threshold do nothing; at threshold call a small model, parse facts/episode, write valid outputs, and mark only the rows read as consolidated. Errors or unparseable output leave rows pending.
- `responsibility_owner`: `waku/memory/consolidation.py::consolidate_if_due`; invocation in `Memory.maybe_consolidate`
- `inputs`: chat log, threshold, small model, semantic/episodic stores
- `outputs`: new facts/episode count, consolidation event, row markers
- `state_read`: unconsolidated `chat_log` rows
- `state_written`: facts, episodes, consolidated markers
- `external_dependencies`: small model, memory store contracts, SQLite transaction
- `implementation_locations`: `waku/memory/consolidation.py`, `waku/memory/__init__.py`, `waku/app.py`
- `public_or_private_boundary`: private memory-maintenance boundary
- `evidence_refs`: `waku/memory/consolidation.py::consolidate_if_due`; `evals/deterministic/test_consolidation.py`
- `replaceability`: medium-high if threshold, extraction schema, atomicity, and failure preservation remain explicit
- `coupling`: high to Waku chat schema and personal-memory extraction prompt
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-12 — Durable state and provenance-lite metadata

- `functional_unit_id`: `FU-12`
- `name`: Local persistence, session labels, and per-turn metadata
- `problem_solved`: Keep Waku’s business artifacts, memory, chat history, and reopenable turn metadata in an inspectable local state store.
- `observable_behavior`: `db.connect()` creates/migrates SQLite schema and enables busy timeout; `Memory.log_chat()` writes user and assistant rows with session/source/meta; dashboard/session code can list and reload sessions.
- `responsibility_owner`: `waku/db.py::connect`, `SCHEMA`, migration; `waku/memory/__init__.py::Memory.log_chat/session_history/list_sessions`
- `inputs`: home path, messages, session id, source, gate/graph/iteration/tool metadata
- `outputs`: SQLite rows, queryable state, session reload data
- `state_read`: local DB schema, chat rows, session rows
- `state_written`: calendar/facts/episodes/chat tables and migrations
- `external_dependencies`: SQLite filesystem, dashboard lock/threading assumptions
- `implementation_locations`: `waku/db.py`, `waku/memory/__init__.py`, `waku/runtime/session.py`
- `public_or_private_boundary`: local operational persistence boundary; not a Catalyst identity/provenance authority
- `evidence_refs`: `waku/db.py::SCHEMA`, `connect`, `_migrate`; `Memory.log_chat`; `evals/deterministic/test_session_resume.py`, `test_turn_meta.py`
- `replaceability`: medium; schema and migration semantics need a deliberate case-local contract
- `coupling`: high to Waku home layout and SQLite schema; medium to gateway source tagging
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-13 — Structured graph execution

- `functional_unit_id`: `FU-13`
- `name`: Bounded wave graph and workflow definitions
- `problem_solved`: Express known parallel/conditional work around the loop with barriers, code-owned routes, disjoint writes, and explicit bounds.
- `observable_behavior`: `run_graph()` fires ready nodes in waves, runs parallel nodes concurrently, merges outputs deterministically, raises on same-wave key collision, routes via Python functions, records errors, and ends on max steps or graph completion. Triage can embed the full loop; gather is proposal-only.
- `responsibility_owner`: `waku/graph/engine.py::Graph/run_graph`; workflow-specific builders under `waku/graph/workflows/`
- `inputs`: graph nodes/edges/routers, initial state, observer, max bounds
- `outputs`: final in-memory graph state, path, errors, graph/node/route events, topology description
- `state_read`: graph blackboard and node snapshots
- `state_written`: in-memory state/errors only; node side effects are external to engine ownership
- `external_dependencies`: Python functions, thread pool, workflow-specific services
- `implementation_locations`: `waku/graph/engine.py`, `nodes.py`, `workflows/triage.py`, `workflows/gather.py`
- `public_or_private_boundary`: internal structured-control seam; workflow definitions are case/product-specific
- `evidence_refs`: catalog `WAKU-A05` source evidence; pre-freeze anchors were recorded in that asset
- `replaceability`: high only for known-shape work; not a replacement for open-ended loop control
- `coupling`: medium to observer/state conventions; high to workflow-specific nodes
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-14 — Trace and operational observability

- `functional_unit_id`: `FU-14`
- `name`: Event observation, trace persistence, usage ledger, and optional OTel export
- `problem_solved`: Make each turn inspectable in order, displayable live, and optionally exportable to span tooling.
- `observable_behavior`: `Tracer` writes `turn_start`, model/tool/gate/graph events, `turn_end`, and usage records; `compose()` fans events to gateway/tracer/capture observers; UTF-8 legacy files are refused without rewrite.
- `responsibility_owner`: `waku/ops/tracing.py::Tracer`, `compose`, dashboard event readers
- `inputs`: observer events, turn/reply metadata, home path, optional endpoint
- `outputs`: JSONL trace, usage JSONL, optional OTel spans, live events
- `state_read`: current daily trace for encoding validation; settings
- `state_written`: trace and usage files
- `external_dependencies`: filesystem, optional OpenTelemetry SDK/exporter
- `implementation_locations`: `waku/ops/tracing.py`, `waku/ops/show_trace.py`, dashboard event readers
- `public_or_private_boundary`: operational evidence boundary; durable file format is local Waku contract
- `evidence_refs`: catalog `WAKU-A03` source evidence; pre-freeze anchors were recorded in that asset
- `replaceability`: high as an event-sink responsibility; low if consumers rely on undocumented payloads
- `coupling`: medium to all event producers; medium to dashboard and trace readers
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

### FU-15 — Evaluation and release decision

- `functional_unit_id`: `FU-15`
- `name`: Deterministic completion, model quality judge, and release gate
- `problem_solved`: Separate “did the expected action happen?” from “was the answer good?” and combine them into an explicit release verdict.
- `observable_behavior`: `check_case()` is binary and tool/argument based; `judge_reply()` returns bounded score/reason or no score; `release_gate.main()` requires deterministic pass, runs judge only when a key is available, persists report/history, and marks missing-key judge status skipped.
- `responsibility_owner`: `waku/ops/scoring.py`, `waku/ops/judge.py`, `waku/ops/release_gate.py`; test suites under `evals/`
- `inputs`: dataset cases, transcripts/tool calls, judge config/key, suite results
- `outputs`: completion result, quality result, gate verdict, JSON report/history
- `state_read`: dataset, environment/provider state, prior operational data as used by dashboard
- `state_written`: eval report/history under Waku home
- `external_dependencies`: pytest, optional DeepEval/judge model, filesystem
- `implementation_locations`: `waku/ops/scoring.py`, `judge.py`, `release_gate.py`, `evals/deterministic/`, `evals/judge/`
- `public_or_private_boundary`: operational/release boundary, not Platform Core authorization
- `evidence_refs`: catalog `WAKU-A04` source evidence; pre-freeze anchors were recorded in that asset
- `replaceability`: high as a case-local evaluation policy; exact rubric/threshold is not portable by default
- `coupling`: medium to tool-call result shape; high to release policy and judge credentials
- `confidence`: HIGH_STRUCTURAL_NOT_LIVE_VERIFIED

## Mechanism value classification

### Stored as independent high-value knowledge assets

The frozen catalog contains exactly six mechanisms: retrieval gating (`WAKU-A01`), bounded loop control (`WAKU-A02`), observer/trace evidence (`WAKU-A03`), separated eval/release logic (`WAKU-A04`), bounded known-shape graph execution (`WAKU-A05`), and progressive procedural loading (`WAKU-A06`). Each has an independent problem, boundary, precondition, limitation, and replacement rationale.

### Deliberately not assetized

- Personal calendar, note, message, browser, GitHub, Apple, Telegram, WhatsApp, and MCP tools: `WAKU_SPECIFIC_IMPLEMENTATION` or optional integration implementation; their mechanism value is not independent enough for this catalog.
- Provider IDs, endpoint catalogs, OpenAI/Anthropic conversion details: `WAKU_SPECIFIC_IMPLEMENTATION`; the provider seam is explained in FU-05, but no provider implementation is preserved as a Catalyst asset.
- SQLite schema, FTS tokenization, Notion/Supabase/Mem0/Zep/LangMem adapters: `REFERENCE_ONLY` for understanding store substitution, with no generic Memory standard created.
- Dashboard HTML/JS views and port selection: `REFERENCE_ONLY` gateway evidence; the stable seam is assessed below, not copied.
- `SOUL.md`, local `.env`, `.waku` layout, and Waku persona: product-specific state/configuration, not reusable governed assets.

## Integration seam assessment — no adapter created

| Seam | Request/result stability | Identity/attribution | Failure semantics | State side effects | Observability | Auth/security assumptions | Replaceability | Minimum future adapter responsibility |
|---|---|---|---|---|---|---|---|---|
| `POST /api/chat` | Stable JSON final-result convenience door; delegates to shared `chat_stream()` and keeps `done` payload | Payload carries result/source indirectly; external caller must supply correlation/actor identity | Empty message returns JSON error; turn exceptions are represented by the shared stream-to-final path; HTTP implementation is local | Runs a full Waku turn: memory reads, tool effects, chat persistence, consolidation, trace | Final result includes gate/graph/tools/iterations/latency/model; raw event stream is not returned | Loopback binding is a deployment assumption; no Catalyst auth contract is established | High as a local script seam, but payload is Waku-specific | Validate caller identity, bind source commit/agent id, correlate request/run, normalize errors, and preserve side-effect policy |
| `POST /api/chat/stream` | SSE event order is more informative but event vocabulary is Waku-specific; ends with `done` | No independent external run identity; event source/node fields are local Waku attribution | Empty message emits `done.error`; exceptions emit terminal `done.error`; broken pipe is ignored | Same full turn side effects as `/api/chat` | Gate/tool/text/graph events stream live; tracer records non-text events | Local browser/loopback and optional gateway credentials; no external authorization model | High transport replaceability, low payload portability without mapping | Validate SSE framing, backpressure/disconnect policy, actor/request correlation, redaction, and terminal-state rules |
| CLI | Text contract is simple and directly calls `Waku.respond(source="cli")`; commands `/memory` and `/quit` are Waku-specific | Source tag is `cli`; user identity is implicit local process identity | EOF/interrupt exits; tool errors become model-visible text; loop hard stop becomes reply | Full turn persistence and tool side effects | Console displays gate/tool/consolidation; tracer also records events | Local process trust; provider key in `.env`; no multi-tenant auth | Very high as a transport, low as a complete external-agent contract | Wrap input/output, identity, cancellation, exit status, and provenance while keeping Waku untouched |
| trace/event | Event types are structurally useful (`turn_start`, `gate`, `llm`, `tool`, `turn_end`, graph events); exact payload is Waku-local | Provider/model and source are present in parts of event/meta, but no canonical external agent/run identity | Trace encoding failure is explicit and refuses mixed encoding; observer failures are not a general transaction protocol | Appends local trace/usage and dashboard event reads; trace is not the business state source | Strong local inspectability and optional OTel | Filesystem access and optional exporter endpoint are trusted; sensitive content may be present | Event sink replaceable after a contract is defined | Bind source repository/commit, run/correlation id, actor, redaction, retention, and tamper/evidence status |
| state/provenance | SQLite schema and JSON metadata are stable enough for Waku-local reopen/read views, not an external canonical API | Session id/source/meta provide provenance-lite attribution; no immutable identity/commit binding | SQLite migration is additive/idempotent; business operation errors belong to tools; no cross-system transaction | Facts, episodes, chats, calendar rows, reports, traces write to separate local artifacts | Dashboard can inspect DB, sessions, trace and eval views | Local filesystem/DB access is assumed; integration security is per optional backend | Store/backend is replaceable inside Waku; external governance requires a new contract | Observe rather than own state initially; bind read/write scope, identity, source commit, side-effect ledger, and consistency/failure semantics |

## Protected boundaries

The following boundaries are preserved by this stage:

1. Waku remains an external source system. Its source root, `.env`, `.waku`, state, and trace remain outside the Case 02-A output tree.
2. The six catalog records are knowledge assets, not implementations, adapters, registered tools, or Platform Core capabilities.
3. `Waku.respond()`/gateway behavior is not reimplemented in Catalyst.
4. Memory store semantics remain Waku-specific; no generic Memory/Tool/Workflow standard is created.
5. Model-dependent claims are explicitly marked `NOT LIVE-VERIFIED`; missing DeepSeek key is not a structure blocker.
6. Graph execution remains a candidate case-local mechanism; no Catalyst Runtime, RuntimeAdapter, or main change is made.
7. The frozen catalog is the only input permitted to the rediscovery pass.

## Asset-to-boundary conclusion

The strongest reusable knowledge is about bounded decisions, bounded control, progressive context loading, evidence fan-out, and evaluation-axis separation. Waku’s personal-assistant product choices are not inherited. Any future integration must be a separately authorized proof that establishes identity, state/provenance, side effects, failure handling, and security before callable behavior is admitted.
