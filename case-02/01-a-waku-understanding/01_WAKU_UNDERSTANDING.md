# CASE 02-A — Waku Understanding

## Understanding verdict

**UNDERSTANDING_SUFFICIENT_FOR_STAGE**

The pinned source was understood from implementation, tests, configuration, HTTP/CLI surfaces, state schema, trace/eval code, and declared documentation. The result is sufficient for functional decomposition, mechanism classification, governed asset preservation, and catalog-only rediscovery.

This is a structural verdict, not a claim that Waku was live-exercised end to end. The local `.env` exposed only the provider selector; no DeepSeek credential was available. Any model-dependent behavior is therefore **NOT LIVE-VERIFIED**. Offline deterministic tests did verify many contracts, but the full suite on this Windows host reported 609 passed, 62 skipped, and 4 environment-specific failures in coding/delegate helpers (`python3`/shebang process launch). Those failures do not block source understanding and are not treated as Waku architecture evidence.

Source identity used for all source claims:

- Source Agent: `ShenSeanChen/waku-agent`
- Canonical repository: `https://github.com/ShenSeanChen/waku-agent.git`
- Pinned source commit: `8328f567ab52d07921445cb40feed23cbc5ea2ad`
- Local source root: `E:\试验场地\agent-lab\waku-agent`
- Case authorization HEAD: `abe14e56867b37f8d6fde45982572cf79f8388e1`

## Actual user-facing promise

Waku is a local-first personal assistant and readable Agent harness: a user can talk through a terminal, browser dashboard, or optional channels; the assistant can use tools, retain personal information, expose what happened, and evaluate whether a change is safe to release. Its promise is not merely “chat with a model”. The implementation promise is:

1. assemble a bounded prompt from persona, relevant memory, procedural instructions, and recent conversation;
2. run a plain reason → tool → observe loop with an explicit hard limit;
3. persist personal state in an inspectable local SQLite file, with human-readable memory export;
4. expose live events and append-only local traces;
5. keep deterministic completion checks separate from model-based response-quality evaluation.

The repository README declares “Harness · Loop · Memory · Eval/LLM-Ops”. Source inspection confirms these are responsibilities, but not four interchangeable Platform components. `waku/app.py` is the assembly owner; the lower-level modules remain replaceable seams.

## Declared intent versus implemented behavior

| Declared intent | Implemented behavior recovered from source | Status |
|---|---|---|
| Local-first personal assistant | `Waku` creates/uses a configured home, SQLite connection, memory facade, tool registry, session, and tracer; CLI/dashboard call the same `respond()` path | STRUCTURALLY VERIFIED |
| Memory is selective | `Session.build_system()` calls `Memory.gated_retrieve()`; the gate can skip stores or fail open; matching procedural skills are appended separately | STRUCTURALLY VERIFIED; model decision NOT LIVE-VERIFIED |
| Loop is readable and bounded | `run_loop()` repeats model/tool turns until no tool call or `max_iterations`; hard-stop reply is explicit | STRUCTURALLY VERIFIED; live model NOT LIVE-VERIFIED |
| Dashboard shows the harness | stdlib HTTP server exposes JSON/SSE routes and forwards observer events; route contracts are pinned by deterministic tests | STRUCTURALLY VERIFIED; live server turn NOT LIVE-VERIFIED |
| Memory is one inspectable local source | `state.db` schema contains calendar, semantic facts, episodic events, and chat log; `.waku/MEMORY.md` is a generated mirror when a turn runs | STRUCTURALLY VERIFIED; current read-only state had zero business rows |
| Eval is built in | deterministic scoring, separate judge scoring, and a release gate are implemented; missing active provider key causes judge status `skipped` | STRUCTURALLY VERIFIED; live judge NOT LIVE-VERIFIED |

## Recovered lifecycle

```text
gateway input
  → Waku.respond()
  → tracer turn_start
  → optional graph front door (flagged; failure falls open)
  → Session.build_system()
       → SOUL.md + current local time/model identity
       → retrieval gate → semantic/episodic search only if retrieve
       → procedural skill matching
       → bounded recent session history
  → run_loop()
       → model reason
       → zero or more tool executions
       → tool results appended as working context
       → natural reply OR hard iteration-stop reply
  → Session.add_exchange()
       → ephemeral history updated
       → chat_log rows persisted with source and per-turn metadata
  → consolidation when enough unconsolidated exchanges exist
       → durable facts + one episode; source rows marked consolidated only after parse
  → generated MEMORY.md mirror
  → tracer turn_end and usage ledger
  → gateway result / SSE done event
```

The graph path is not the normal loop replacement. When enabled, triage can classify and read today’s calendar in parallel, route a quick reply, or invoke the same full loop as one graph node. Any graph failure falls open to the plain loop.

## Entry and gateway surfaces

- `waku/__main__.py` dispatches the CLI surface: chat, dashboard, connections, voice, Telegram, Discord, WhatsApp, brief, gather, and skill install.
- `waku/gateway/cli.py` is a text-in/text-out gateway with `/memory` and `/quit`; it calls `Waku.respond(source="cli")`.
- `waku/ops/dashboard.py` provides the local browser gateway. `POST /api/chat` returns one structured final result; `POST /api/chat/stream` emits SSE events and ends with a structured `done` event. Both share `chat_stream()`.
- The dashboard is bound to loopback by the implementation. It exposes additional read/query/settings/session/graph/trace views, but those are operational surfaces around the same Waku state.
- Optional channel gateways use the same application responsibility but add channel-specific delivery and identity assumptions. They are not part of the loop itself.

## State model

### Ephemeral state

- `Session.history`: current conversation working memory, bounded again before the model call by `history_turns`.
- `run_loop()` messages: one-turn assistant/tool/tool-result transcript.
- Graph state: one in-memory dict with node outputs and errors; graph plumbing keys are excluded from persisted public state.
- Gate decision, triage route, and model response are per-turn decisions, later copied into turn metadata/trace but not owned as memory policy.

### Durable state

- `.waku/state.db`: SQLite schema for `calendar_events`, semantic `facts`, episodic `episodes`, FTS tables, and raw `chat_log`.
- `chat_log`: user/assistant pairs, session id, source, consolidation marker, and assistant-row metadata.
- `.waku/MEMORY.md`: generated human-readable mirror; the database remains the queryable source of truth.
- `.waku/traces/<date>.jsonl`: ordered turn/event evidence; `.waku/usage.jsonl`: append-only token ledger.
- `.waku/eval_report.json` and `.waku/eval_runs.jsonl`: release-gate result and history when the gate runs.
- `.waku/skills/`: local procedural instructions discovered by the loader.

The current read-only state check used the new source root and opened `state.db` read-only. The tables were present, and `calendar_events`, `facts`, `episodes`, and `chat_log` each had zero rows. No trace file was used as evidence for a live turn.

## Memory responsibilities

Waku separates three memory responsibilities, plus two managers:

- Semantic memory: durable facts, keyword-searchable with SQLite FTS5 or a configured backend seam.
- Episodic memory: dated summaries of what happened, with relevance plus recency behavior.
- Procedural memory: `SKILL.md` instructions; metadata is scanned cheaply and bodies are loaded only for matching skills.
- Retrieval gate: decides whether semantic/episodic retrieval is needed and provides the query; failures fail open.
- Consolidation: after a configured number of exchange rows, a small model extracts durable facts and one episode; failed/unparseable extraction leaves the log unconsolidated.

This is not one generic Memory object. The `Memory` facade coordinates distinct responsibilities and backend choices, while `Session` consumes the resulting prompt material.

## Dependencies and replaceability

The central dependency direction is:

```text
gateway → Waku assembly → Session / Memory / ToolRegistry / Loop / Tracer
                                      ↘ provider client
                                      ↘ SQLite or optional stores
```

Provider conversion is isolated behind an Anthropic-shaped client contract. Tools are described by name, description, JSON schema, and callable, and execution errors become model-visible text. Optional integrations (calendar targets, external memory stores, MCP, channels, OpenTelemetry) are opt-in or replaceable seams rather than requirements for the basic loop.

The most replaceable responsibilities are gateway transport, model wire adapter, memory store implementations, trace sink, and graph workflow definitions. The least replaceable Waku-specific assumptions are personal-assistant persona, local home layout, calendar/message/note tools, and the meaning of facts/episodes/skills.

## Structural evidence and confidence

Primary evidence is the pinned source itself: `waku/app.py`, `waku/runtime/session.py`, `waku/loop/agent.py`, `waku/loop/models.py`, `waku/memory/`, `waku/tools/`, `waku/graph/`, `waku/ops/`, `waku/gateway/`, `waku/db.py`, and their deterministic tests under `evals/deterministic/`. Documentation under `README.md` and `docs/` was treated as declared intent and checked against implementation.

Confidence is high for structural behavior, boundaries, and offline-tested contracts. Confidence is not live verification of model routing, DeepSeek behavior, external provider availability, real channel delivery, or OpenTelemetry export.
