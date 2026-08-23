# CASE 01-D — D2 AUTHORIZATION MODEL V0.2

## Purpose

This document refines only the governance-recording mechanism for D2 authorization.
It does **not** replace the accepted D2 technical Stage Spec and does **not** itself authorize D2 execution.

The accepted technical contract remains:

`CASE_01_D_D2_LOCAL_ADMISSION_AND_BINDING_V0.1_STAGE_SPEC.md`

## Governance Separation

Catalyst treats four things as separate artifacts / responsibilities:

```text
1. User Decision
   = governance authority decision

2. Stage Spec
   = accepted technical / evidence contract

3. Authorization Record
   = declarative record that the decision occurred

4. Executor
   = implementation actor operating under the recorded scope
```

An Authorization Record is therefore evidence of a governance decision, not an executable prompt and not a second Stage Spec.

## Authorization Record Shape

After an explicit user decision, Catalyst may record the decision as a compact declarative YAML file.

Schema:

```yaml
record_type: case_stage_authorization
record_version: "0.1"
case_id: CASE-01
stage_id: D2
stage_name: Local Admission & Binding Proof
decision: <granted|denied>
decision_authority: user
decision_source: current_conversation
stage_contract_ref: CASE_01_D_D2_LOCAL_ADMISSION_AND_BINDING_V0.1_STAGE_SPEC.md
stage_contract_commit: 27b67cf9cad4a6f5036437aa63750cda8d9aaf1b
target_branch: case-01
scope:
  local_admission_proof: <true|false>
  local_execution_binding_proof: <true|false>
  attribution_and_provenance_evidence: <true|false>
publication_limit:
  implementation_evidence_commits: <integer>
  pushes: <integer>
protected_boundaries:
  catalyst_main_mutation: false
  platform_core_mutation: false
  runtime_mutation: false
  runtime_adapter_mutation: false
  enterprise_extension_mutation: false
  brea_candidate_mutation: false
  raw_corpus_upstream: false
next_stage:
  case_01_e_decision: not_granted
```

The record contains facts and limits only.

It does not contain executor-directed prose such as procedural commands, implementation steps, stop instructions, or architecture-review instructions.
Those remain defined by the Stage Spec and by the active conversation instruction that initiates execution.

## Admission Authority Semantics

For CASE 01 D2, a later `decision: granted` record means only:

- the User made the governance decision to allow the D2 proof to be attempted within the Stage contract;
- the scope and publication limit are recorded as facts;
- if the D2 mandatory gates pass, the Case-local Admission Record may cite this authorization record as the authority reference for the local admission decision;
- passing tests, Registry state, DeepSeek output, Runtime execution, or the authorization-record file itself do not independently create governance authority.

## Stage Contract Precedence

The D2 technical behavior, admission gates, identity separation, provenance requirements, fail-closed behavior, write boundaries and acceptance criteria remain governed by the accepted D2 Stage Spec.

This authorization model changes only how the User's decision is recorded.

## Canonical D2 Governance Chain

```text
User Decision
      ↓
Declarative Authorization Record
      ↓ reference
Accepted D2 Stage Contract
      ↓
Case-local D2 implementation / evidence
      ↓
Admission Record + Binding Record + Provenance
      ↓
External architecture / evidence review
```

## Current State

At the time this model is published:

```text
D2 technical Stage Spec: accepted
D2 authorization record: not yet created under this V0.2 model
D2 implementation publication: not yet started under this V0.2 model
CASE 01-E decision: not granted
```

A fresh explicit User authorization is required before the declarative D2 authorization record is created.
