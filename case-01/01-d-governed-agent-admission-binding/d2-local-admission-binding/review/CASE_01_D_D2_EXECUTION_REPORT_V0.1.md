# CASE 01-D / D2 — EXECUTION REPORT — V0.1

> Final D2 execution report per Stage Spec §25. DeepSeek does not close D2;
> external review (ChatGPT) decides A/B/C/D.

```text
D2 STATUS
READY FOR EXTERNAL REVIEW

CASE-01 HEAD INPUT
285cfe58f82bf20a5b82a28930c9350730471153

CATALYST MAIN
5874be1130e8867082880fcd63f659fc909d9efd

D2 AUTHORIZATION REF
D2_AUTHORIZATION_RECORD_V0.1.yaml (granted; commit 285cfe5)

GOVERNED AGENT
case-01.brea @ 0.1-candidate

EXECUTION CAPABILITY
case-01.brea.execute @ 0.1

AGENT == CAPABILITY
NO

DEFINITION SHA
PASS
6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4

FORMATION EVIDENCE
PASS
01-C closure present: FORMATION_EVIDENCE_INDEX / FUNCTION_CONFORMANCE /
GOVERNED_SEAM_CONFORMANCE / OBLIGATION_CONFORMANCE / BUILDER_FORMATION_TRACE /
LEGACY_ADAPTATION_TRACE / 15/15 selfcheck / T-C01/02/03 result JSON

IMPLEMENTATION FINGERPRINT
candidate_tree_sha256         = cbdd6b4d13df0f2b4408ab6a50a9b882fd4aa35cb2ddeeb668e98d6634599193
builder_output_manifest_sha256 = 394ef4da3658776b34a4ad2c2d3fbd803b3ff332f7b7f6669c82a5917f00e3de
(19 files declared by accepted 01-C BUILDER_OUTPUT_MANIFEST_V0.1.json, all unchanged)

CANDIDATE REGRESSION
15/15 PASS

T-C01 BASELINE
PASS (accepted_with_evidence, 50m clause 3.1.3)

T-C02 BASELINE
PASS (accepted_with_evidence, 1.1 车位/100m², 表5.0.1→表5.0.4)

T-C03 BASELINE
PASS (insufficient_context, no digits)

ADMISSION STATUS
ADMITTED (admission_ref=admission-case-01-brea-v0.1-001)

ADMISSION AUTHORITY
User explicit D2 authorization ref (D2_AUTHORIZATION_RECORD_V0.1.yaml, granted)

BINDING STATUS
BOUND (binding_id=binding-case-01-brea-v0.1-001)

governance.agent CANONICAL LOCATION
Invocation.extensions (context.extensions presence → fail closed, D2-T08)

D2 TESTS
16/16 PASS (D2-T01..D2-T16)

PLATFORM-BOUND T-C01
PASS (whole Agent via D2 binding path; professional behavior preserved; exact Agent attribution)

PLATFORM-BOUND T-C02
PASS (whole Agent via D2 binding path; professional behavior preserved; exact Agent attribution)

PLATFORM-BOUND T-C03
PASS (professional fail-closed preserved; exact Agent attribution)

PROVENANCE CHAIN
PASS (evidence/D2_PROVENANCE_CHAIN_V0.1.json — all checks true)

RAW CORPUS COMMITTED
NO

UNAUTHORIZED PATH CHANGES
0

PLATFORM CORE CHANGE
NO

RUNTIME / ADAPTER CHANGE
NO

MAIN
UNCHANGED

PLATFORM GAP UPDATE
G-D1-01/02/03 → CASE-PROVEN / GENERALIZATION CANDIDATE
G-D1-04/05 → CASE-PROVEN (case-local)
G-D1-06 → unchanged REJECTED; G-D1-07 → unchanged DEFERRED
(evidence/PLATFORM_GAP_UPDATE_D2_V0.1.md)

CASE 01-E ENTRY BOUNDARY
GENERATED (review/CASE_01_E_ENTRY_BOUNDARY_V0.1.md)

D2 COMMIT
<filled at publication>

CASE 01-E
NOT AUTHORIZED

FINAL
READY FOR D2 EXTERNAL REVIEW
```

---

## What D2 proved (evidence summary)

1. **Local admission without Platform change** — all seven mandatory gates
   (G-A01..G-A07) pass; Admission Record is a Case-local record, not a Registry
   entry; `InMemoryDescriptorRegistry` and `PlatformValidator` are untouched.
2. **Execution binding without Agent == Capability** — `case-01.brea @ 0.1-candidate`
   stays the Agent identity; execution routes through `case-01.brea.execute @ 0.1`;
   the read-only BREA Candidate runner is adapted via `describe()/invoke()` with no
   FN/SEAM/OBL change (D2-T09).
3. **Exact attribution through the whole path** — `governance.agent` rides
   `Invocation.extensions` (canonical, D2-T08), is validated against Admission +
   Binding (D2-T05/T07), and is written to `TraceEvent.extensions` for every event
   (D2-T11 conflict → fail closed); the provenance chain resolves to exact
   agent_id / agent_version / admission_ref / binding_ref / fingerprint.
4. **Professional behavior preserved on Platform** — whole-Agent T-C01/02/03 via the
   D2 binding path return the same professional outcomes (including the
   `insufficient_context` fail-closed case) with exact Agent attribution
   (D2-T14/15/16; Platform `Result.status="success"` = execution succeeded, the
   professional outcome lives in `output.status`).
5. **Enterprise remains attribution, not Runtime meaning** — `enterprise.identity`
   conflict with the admitted enterprise context fails closed (D2-T13); BREA
   professional semantics unchanged (OBL-06).

## Non-blocking findings

- `python -m brea.runner` emits a benign `RuntimeWarning` ('brea.runner' found in
  sys.modules after import of package 'brea'); recorded, NON-BLOCKING (01-C known).
- Root `.gitignore` excludes `*.log`; D2 commits `.log.txt` twins of the evidence
  logs while keeping real `.log` locally (01-C precedent) — noted in
  `D2_EVIDENCE_INDEX_V0.1.md`.
- The Runtime `CapabilityDescriptor.id` requires a portable tool-name regex, so the
  Runtime-facing id is `case_01_brea_execute` while the Platform routing identity
  stays `case-01.brea.execute` (the RuntimeAdapter rewrites ids to internal keys
  anyway). Documented in the adapter source; no Platform change.

## STOP

DeepSeek stops after one D2 implementation + evidence commit and one push to
`case-01`. CASE 01-E is NOT authorized and has NOT started.
