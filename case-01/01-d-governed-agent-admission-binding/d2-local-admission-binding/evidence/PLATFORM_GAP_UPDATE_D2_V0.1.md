# PLATFORM GAP UPDATE — D2 — V0.1

> Updates D1 Platform Gap Register (`d1-admission-architecture-compatibility/PLATFORM_GAP_REGISTER_D1_V0.1.md`)
> with D2 case evidence. Dispositions allowed by spec §14: `CASE-PROVEN`, `CASE-PROVEN / GENERALIZATION CANDIDATE`,
> `STILL OPEN`, `BLOCKED`. D2 may NOT declare `PLATFORM CORE ADOPTED` or `GENERIC CATALYST CAPABILITY`.

## Disposition summary

| Gap | Title | D1 disposition | D2 evidence | D2 disposition |
|---|---|---|---|---|
| G-D1-01 | Agent-level identity/version/admission representation | GENERALIZATION CANDIDATE | Case-local Admission Record (`admission/BREA_V0_1_ADMISSION_RECORD.json`) with frozen `agent_id=case-01.brea`, `agent_version=0.1-candidate`, `admission_ref`, evidence refs; Admission ≠ Registry.register (registry untouched) | **CASE-PROVEN / GENERALIZATION CANDIDATE** |
| G-D1-02 | Agent execution attribution across the Platform path | GENERALIZATION CANDIDATE | `governance.agent` Extension (canonical = `Invocation.extensions` ONLY; D2-T08); validated against Admission + Binding (D2-T05/T07); trace attribution on `TraceEvent.extensions`, conflict → fail closed (D2-T11); exact attribution proven on whole-Agent cases D2-T14/15/16 | **CASE-PROVEN / GENERALIZATION CANDIDATE** |
| G-D1-03 | Whole-Agent execution through capability-centric mechanics | GENERALIZATION CANDIDATE | BREA runner adapted via `describe()/invoke()`; RuntimeAdapter direct binding + version routing; Agent identity `case-01.brea` stays distinct from execution capability `case-01.brea.execute` (D2-T09); Platform-bound T-C01/02/03 execute whole Agent, professional behavior preserved | **CASE-PROVEN / GENERALIZATION CANDIDATE** |
| G-D1-04 | Deterministic implementation fingerprint (binding anti-swap) | CASE-LOCAL NEED | `candidate_tree_sha256=cbdd6b4d…` + `builder_output_manifest_sha256=394ef4da…` over the 19 files declared by the accepted 01-C manifest; fingerprint mismatch → binding rejected (D2-T04); recorded in Binding Record | **CASE-PROVEN** (no generalization evidence; remains case-local) |
| G-D1-05 | Admission status / decision record | CASE-LOCAL NEED | Case-local Admission Record `ADMITTED` with gate results, decision reason, decided_at, and explicit D2 authorization ref; successful Binding exists only for ADMITTED Agent (D2-T01..T04) | **CASE-PROVEN** (remains case-local; registry is not governance authority) |
| G-D1-06 | Generic Agent Manifest / object model | REJECTED PREMATURE CONCEPT | Not implemented in D2 (spec §16 forbids generic Agent Manifest SDK) | UNCHANGED — REJECTED |
| G-D1-07 | Network evidence / source trust / memory platform | DEFERRED FUTURE NEED | Not in D2 scope | UNCHANGED — DEFERRED (01-E/01-F) |

## What D2 does NOT claim

```text
PLATFORM CORE ADOPTED        — NO (no Core change; no new Core semantics)
GENERIC CATALYST CAPABILITY  — NO (only one Agent / one Case proven)
```

## New case evidence gained

- `governance.agent` attribution proven end-to-end (Invocation → Result → TraceEvent → ArtifactRef.producer) on three whole-Agent executions (D2-T14/15/16).
- Agent ≠ Capability proven operationally: execution routes via `case-01.brea.execute`, Agent identity rides `Invocation.extensions`, no Platform change required.
- fail-closed extension semantics proven in a real governed path (missing / version / required / payload / context duplication / trace conflict all reject).
