# CASE 02-A — Rediscovery Evidence Repair

## Result

**`REDISCOVERY_EVIDENCE_PASS`**

This document records an independent later rediscovery pass over the frozen asset catalog. It does not reopen Waku understanding, decomposition, implementation, execution, or integration.

## Frozen input evidence

- Catalog path: `case-02/01-a-waku-understanding/CASE_02_WAKU_ASSET_CATALOG_V0.1.json`
- Catalog status before discovery: `FROZEN_FOR_REDISCOVERY`
- Catalog commit: `d19c7b1cc03edb126a32ebde0b92b28aa9bd8976`
- Catalog bytes SHA-256 before discovery: `802E24EE44C185FB62C35B1947B03F515477E2F102B0EBBFDBF1B3CAA5D2849D`
- Catalog bytes SHA-256 after discovery: `802E24EE44C185FB62C35B1947B03F515477E2F102B0EBBFDBF1B3CAA5D2849D`
- `unchanged`: `true`

The catalog itself declares `source_commit = 8328f567ab52d07921445cb40feed23cbc5ea2ad` for its stored records. No source claim was refreshed from Waku during this pass.

## Need D

**Need:** I have multiple tasks that may run in parallel. I need to prevent parallel branches from writing the same state key, and the overall flow must have a clear maximum number of steps. Have we previously learned a mechanism relevant to this problem?

- `matched_asset_ids`: `["WAKU-A05"]`
- `why_relevant`: The catalog record describes a bounded wave graph whose parallel branches declare disjoint state outputs, whose same-wave key collision raises, whose routing is code-owned, and whose `max_visits` plus `max_steps` provide bounded execution. This directly matches both required properties.
- `reuse_preconditions`: ["The work shape is known and parallel branches can declare disjoint outputs", "routing is code-governed and testable", "global and per-node termination limits are explicit", "node side effects and failure recovery are authorized"]
- `why_not_directly_platform_core`: The catalog classifies `WAKU-A05` as `POTENTIAL_CASE_LOCAL_REUSE`, and its responsibility boundary is graph scheduling/state merge/bounds rather than model reasoning or tool semantics. The catalog reconstruction note explicitly says no graph adapter or Catalyst workflow change is authorized; promoting it directly would import a case-specific control mechanism into Platform Core.
- `next_action_if_reuse_is_authorized`: Run a later case-local proof only after deciding whether the need is predetermined structure or open-ended Agent work, then govern state ownership and side effects. Do not reconstruct or execute the stored asset in this stage.

## Need E

**Need:** I have many operational instructions, but I do not want to inject every full instruction into the Agent prompt on every turn. Have we previously learned a mechanism relevant to this problem?

- `matched_asset_ids`: `["WAKU-A06"]`
- `why_relevant`: The catalog record describes progressive procedural-memory loading: inexpensive metadata/description discovery, selective matching, and loading only matched instruction bodies into the prompt. This directly addresses avoiding full instruction injection on every turn.
- `reuse_preconditions`: ["Instructions have trusted metadata and an explicit body-loading boundary", "installed content is reviewed before being eligible", "matching misses and collisions are observable", "prompt budget and maximum inclusions are bounded"]
- `why_not_directly_platform_core`: The catalog bounds this mechanism to procedural instruction discovery and prompt inclusion, not semantic/episodic retrieval or tool execution. It classifies the mechanism as a high-value pattern but explicitly says it is not a generic Skill/Memory standard; trust, provenance, review, and injection resistance remain case-specific.
- `next_action_if_reuse_is_authorized`: Treat it as a knowledge candidate and define instruction trust, provenance, review, and injection-resistance policy before any later reuse. No instruction loader or reconstruction is created here.

## Need F

**Need:** I need an external Agent’s live runtime events to be observable by a UI while also preserving inspectable local execution evidence. Have we previously learned a mechanism relevant to this problem?

- `matched_asset_ids`: `["WAKU-A03"]`
- `why_relevant`: The catalog record describes observer fan-out that sends the same runtime events to live observers and an append-only UTF-8 JSONL trace, with optional telemetry spans and a separate usage ledger. Its problem statement directly covers UI observation plus inspectable local evidence.
- `reuse_preconditions`: ["A stable event vocabulary and run identity are defined", "append/write failure behavior is governed", "sensitive prompts/tool arguments are redacted or explicitly permitted", "downstream consumers can tolerate missing live text events"]
- `why_not_directly_platform_core`: The catalog defines the responsibility as event fan-out and operational evidence, not Agent behavior, business state, or external-platform provenance identity. It classifies the mechanism as a `POTENTIAL_INTEGRATION_SEAM` and explicitly rejects treating it as a drop-in Catalyst tracing standard; external-agent identity, source commit, run/correlation id, actor attribution, redaction, and retention must be bound first.
- `next_action_if_reuse_is_authorized`: Form a later evidence/provenance proof that binds external-agent identity, source commit, run/correlation id, actor attribution, redaction, and retention. Do not create a tracing adapter or execute the stored asset in this stage.

## Forbidden-read compliance

The only knowledge inputs used for the three probes were:

1. `CASE_02_A_REDISCOVERY_EVIDENCE_REPAIR_AUTHORIZATION_V0.1.yaml` for scope and probe text;
2. `CASE_02_WAKU_ASSET_CATALOG_V0.1.json` for all asset matching and reuse reasoning.

The following were not read during discovery: the Waku repository, `E:\试验场地\agent-lab\waku-agent`, Waku source/tests/README/docs, `.env`, `.waku`, `state.db`, trace files, `01_WAKU_UNDERSTANDING.md`, `02_WAKU_MECHANISM_DECONSTRUCTION.md`, and `03_CASE_02_A_REVIEW.md`.

No Waku source was rescanned. No source-derived answer was added after the catalog freeze. No new asset was inferred or created.

## Protected boundaries

- The frozen catalog was not modified; before/after bytes SHA-256 are identical.
- Existing asset records were not modified.
- No asset was reconstructed or executed.
- No adapter, Waku registration, Platform Core, Runtime, RuntimeAdapter, or main change was made.
- No case-01 file was read, modified, staged, or committed.
- Case 02-B was not entered.

## Stop

The independent catalog-only rediscovery evidence repair is complete. STOP.
