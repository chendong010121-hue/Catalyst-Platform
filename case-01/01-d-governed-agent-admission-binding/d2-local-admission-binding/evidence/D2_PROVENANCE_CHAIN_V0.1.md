# D2 PROVENANCE CHAIN — V0.1

**Verification:** `PASS`

## Chain (spec §11)

```text
Admission Record  ->  admission/BREA_V0_1_ADMISSION_RECORD.json (admission_ref=admission-case-01-brea-v0.1-001)
Binding Record    ->  binding/BREA_V0_1_EXECUTION_BINDING.json (binding_id=binding-case-01-brea-v0.1-001)
Invocation.extensions['governance.agent'] (canonical source)
Platform Invocation (id/trace_id)
execution routing identity = case-01.brea.execute @ 0.1
RuntimeAdapter / Runtime (unchanged)
Result.invocation_id
TraceEvent.trace_id + subject_id
TraceEvent.extensions['governance.agent']
ArtifactRef.producer.invocation_id
```

## Resolved identifiers

- agent_id = `case-01.brea`
- agent_version = `0.1-candidate`
- admission_ref = `admission-case-01-brea-v0.1-001`
- binding_ref = `binding-case-01-brea-v0.1-001`
- candidate_tree_sha256 = `cbdd6b4d13df0f2b4408ab6a50a9b882fd4aa35cb2ddeeb668e98d6634599193`
- builder_output_manifest_sha256 = `394ef4da3658776b34a4ad2c2d3fbd803b3ff332f7b7f6669c82a5917f00e3de`

## Executions

### T-C01
- invocation_id: `inv_d2_T-C01`  trace_id: `trace_d2_T-C01`
- resolved_to: `{"agent_id": "case-01.brea", "agent_version": "0.1-candidate", "admission_ref": "admission-case-01-brea-v0.1-001", "binding_ref": "binding-case-01-brea-v0.1-001"}`
- trace events: 3 (all carry exact governance.agent)
- artifacts: 1 (producer capability_id = case-01.brea.execute)

### T-C02
- invocation_id: `inv_d2_T-C02`  trace_id: `trace_d2_T-C02`
- resolved_to: `{"agent_id": "case-01.brea", "agent_version": "0.1-candidate", "admission_ref": "admission-case-01-brea-v0.1-001", "binding_ref": "binding-case-01-brea-v0.1-001"}`
- trace events: 4 (all carry exact governance.agent)
- artifacts: 2 (producer capability_id = case-01.brea.execute)

### T-C03
- invocation_id: `inv_d2_T-C03`  trace_id: `trace_d2_T-C03`
- resolved_to: `{"agent_id": "case-01.brea", "agent_version": "0.1-candidate", "admission_ref": "admission-case-01-brea-v0.1-001", "binding_ref": "binding-case-01-brea-v0.1-001"}`
- trace events: 2 (all carry exact governance.agent)
- artifacts: 0 (producer capability_id = case-01.brea.execute)

## Verification checks

- admission_resolves_agent: `PASS`
- binding_resolves_admission: `PASS`
- governance_payload_resolves: `PASS`
- fingerprint_matches_binding: `PASS`
- all_cases_linked: `PASS`
- artifacts_producer_linked: `PASS`