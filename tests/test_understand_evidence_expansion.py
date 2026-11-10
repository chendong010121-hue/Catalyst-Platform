from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.observability import RunRecorder
from catalyst_platform.__main__ import main
from catalyst_platform.understand_only import (
    EvidenceExpansionRequest,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    handoff_external_candidate,
)
from catalyst_platform.wiki import ProjectWiki


def _prepared(tmp_path: Path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "ledger.md"
    source.write_text(
        "Revenue: 10 units.\nCost: 7 units.\nUnrelated note.\n",
        encoding="utf-8",
    )
    base = UnderstandPort().understand(
        UnderstandingRequest(
            "req_expand_base",
            "Revenue",
            (source,),
            UnderstandIntent.TASK_USE,
            requested_depth="semantic",
        ),
        source_root=source_root,
    )
    return source_root, source, base


def _expand_request(base, **overrides):
    values = {
        "request_id": "req_expand_cost",
        "query": "Cost",
        "allowed_source_ids": (base.source_inventory[0].source_id,),
        "known_evidence_ids": tuple(item.evidence_id for item in base.evidence_refs),
        "max_steps": 1,
        "max_additional_refs": 8,
        "max_bytes": 1024,
    }
    values.update(overrides)
    return EvidenceExpansionRequest(**values)


def test_expansion_finds_unmapped_evidence_within_one_source_and_preserves_identity(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    result = UnderstandPort().expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        _expand_request(base),
        source_root=source_root,
    )

    assert result.status == "EXPANDED"
    assert result.map_status == "EXPANDED"
    assert [item.quote for item in result.evidence_refs] == ["Cost: 7 units."]
    assert result.evidence_refs[0].source_id == base.source_inventory[0].source_id
    assert result.evidence_refs[0].source_revision == base.source_inventory[0].source_revision
    assert result.evidence_refs[0].source_sha256 == base.source_inventory[0].source_sha256
    assert result.evidence_refs[0].evidence_id not in {item.evidence_id for item in base.evidence_refs}
    assert result.steps_used == 1
    assert result.bytes_read == base.source_inventory[0].byte_size


def test_no_match_is_evidence_not_mapped_not_semantic_unknown(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    result = UnderstandPort().expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        _expand_request(base, query="NEVER_PRESENT_SENTINEL"),
        source_root=source_root,
    )

    assert result.status == "NO_MATCH"
    assert result.map_status == "EVIDENCE_NOT_MAPPED"
    assert not result.evidence_refs
    assert "UNKNOWN" not in result.to_dict()


def test_expansion_rejects_unselected_source_ids_without_scanning(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    result = UnderstandPort().expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        _expand_request(base, allowed_source_ids=("src_not_in_the_prepared_inventory",)),
        source_root=source_root,
    )

    assert result.status == "DENIED"
    assert result.map_status == "DENIED"
    assert result.steps_used == 0
    assert result.bytes_read == 0
    assert not result.evidence_refs


def test_expansion_denies_path_escape_in_prepared_inventory(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    forged_record = replace(base.source_inventory[0], relative_path="../outside.md")
    request = _expand_request(base, allowed_source_ids=(forged_record.source_id,))
    result = UnderstandPort().expand_evidence(
        (forged_record,),
        base.evidence_refs,
        request,
        source_root=source_root,
    )

    assert result.status == "DENIED"
    assert result.map_status == "DENIED"
    assert not result.evidence_refs


def test_expansion_stops_when_source_revision_changed(tmp_path: Path):
    source_root, source, base = _prepared(tmp_path)
    source.write_text("Revenue: 10 units.\nCost: 99 units.\n", encoding="utf-8")
    result = UnderstandPort().expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        _expand_request(base),
        source_root=source_root,
    )

    assert result.status == "STALE_SOURCE"
    assert result.map_status == "STALE_SOURCE"
    assert not result.evidence_refs
    assert result.bytes_read == 0


def test_expansion_enforces_byte_and_reference_budgets(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    port = UnderstandPort()
    blocked = port.expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        _expand_request(base, max_bytes=1),
        source_root=source_root,
    )
    assert blocked.status == "BUDGET_EXHAUSTED"
    assert blocked.bytes_read == 0
    assert not blocked.evidence_refs

    many_source = source_root / "many.md"
    many_source.write_text("Cost: 1\nCost: 2\nCost: 3\n", encoding="utf-8")
    many_base = port.understand(
        UnderstandingRequest(
            "req_many_base", "Cost", (many_source,), UnderstandIntent.TASK_USE,
            requested_depth="targeted",
        ),
        source_root=source_root,
    )
    limited = port.expand_evidence(
        many_base.source_inventory,
        many_base.evidence_refs[:1],
        _expand_request(
            many_base,
            query="Cost",
            allowed_source_ids=(many_base.source_inventory[0].source_id,),
            known_evidence_ids=tuple(item.evidence_id for item in many_base.evidence_refs[:1]),
            max_additional_refs=1,
            max_bytes=1024,
        ),
        source_root=source_root,
    )
    assert len(limited.evidence_refs) == 1


def test_expansion_hard_caps_are_validated_before_source_reads(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    with pytest.raises(ValueError, match="max_steps"):
        UnderstandPort().expand_evidence(
            base.source_inventory,
            base.evidence_refs,
            _expand_request(base, max_steps=999),
            source_root=source_root,
        )


def test_expansion_records_r4_boundary_without_source_text(tmp_path: Path):
    source_root, _source, base = _prepared(tmp_path)
    workspace = tmp_path / "workspace"
    gateway = CatalystGateway(workspace)
    recorder = RunRecorder(
        gateway.traces,
        run_id="expansion_run_test",
        request_id="req_expansion_run_test",
        invocation_id="inv_expansion_run_test",
        event_schema_version="1.5",
    )
    recorder.start(request_kind="understand_expansion_test", actor="synthetic_test", component="test")
    result = UnderstandPort().expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        _expand_request(base),
        source_root=source_root,
        recorder=recorder,
    )
    recorder.finish("success", model_calls=0, error_owner=None)

    assert result.status == "EXPANDED"
    trace = gateway.inspect_run("expansion_run_test")
    assert trace is not None
    span_start = next(
        event for event in trace["events"]
        if event.get("span_name") == "understand.evidence_expansion"
    )
    span_end = next(
        event for event in trace["events"]
        if event.get("event_type") == "span.ended" and event.get("span_id") == span_start["span_id"]
    )
    span_summary = span_end["attributes"]["status"]
    assert "map_status=EXPANDED" in span_summary
    assert "steps=1" in span_summary
    assert "refs=1" in span_summary
    assert "query_sha256=" in span_summary
    serialized_trace = json.dumps(trace, ensure_ascii=False)
    assert "Cost: 7 units." not in serialized_trace
    assert "Revenue: 10 units." not in serialized_trace
    assert "model_calls" in serialized_trace


def test_expansion_cli_uses_shared_port_r4_and_correlates_prepare(tmp_path: Path, capsys):
    source_root, _source, base = _prepared(tmp_path)
    workspace = tmp_path / "workspace"
    prepared = tmp_path / "prepared-result.json"
    prepared.write_text(json.dumps(base.to_dict(), ensure_ascii=False), encoding="utf-8")
    expansion_request = tmp_path / "expansion-request.json"
    expansion_request.write_text(json.dumps({
        "request_id": "req_expand_cli",
        "query": "Cost",
        "allowed_source_ids": [base.source_inventory[0].source_id],
        "known_evidence_ids": [item.evidence_id for item in base.evidence_refs],
        "locator_hints": [],
        "max_steps": 1,
        "max_additional_refs": 8,
        "max_bytes": 1024,
    }), encoding="utf-8")

    assert main([
        "understand-expand",
        "--workspace", str(workspace),
        "--source-root", str(source_root),
        "--prepared-result", str(prepared),
        "--request", str(expansion_request),
        "--correlation-id", "prepare-run-01",
    ]) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["operation"] == "understand.evidence_expand"
    assert envelope["result"]["map_status"] == "EXPANDED"
    assert envelope["result"]["evidence_refs"][0]["quote"] == "Cost: 7 units."
    trace = CatalystGateway(workspace).inspect_run(envelope["run_id"])
    assert trace is not None
    assert all(event.get("correlation_id") == "prepare-run-01" for event in trace["events"])
    assert any(event.get("span_name") == "understand.evidence_expansion" for event in trace["events"])
    serialized_trace = json.dumps(trace, ensure_ascii=False)
    assert "Cost: 7 units." not in serialized_trace
    assert "Revenue: 10 units." not in serialized_trace


def test_expanded_evidence_projects_through_existing_v2_as_proposed_only(tmp_path: Path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "monthly.md"
    source.write_text("Revenue: 10 units.\nCost: 7 units.\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    wiki = ProjectWiki(workspace, [source_root], enterprise_id="synthetic", project_id="d2")
    base = UnderstandPort().understand(
        UnderstandingRequest(
            "req_v2_base", "Revenue", (source,), UnderstandIntent.KNOWLEDGE_PROPOSE,
            scope_id=wiki.scope_id, requested_depth="semantic",
        ),
        source_root=source_root,
    )
    expansion = UnderstandPort().expand_evidence(
        base.source_inventory,
        base.evidence_refs,
        EvidenceExpansionRequest(
            request_id="req_v2_expand", query="Cost",
            allowed_source_ids=(base.source_inventory[0].source_id,),
            known_evidence_ids=tuple(item.evidence_id for item in base.evidence_refs),
            max_steps=1, max_additional_refs=4, max_bytes=1024,
        ),
        source_root=source_root,
    )
    merged = replace(base, evidence_refs=(*base.evidence_refs, *expansion.evidence_refs))
    port = UnderstandPort()
    typed = port.attach_producer_items(
        merged,
        producer_kind="CODEX_EXTERNAL",
        producer_invocation_id="synthetic_codex_invocation",
        items=[{
            "kind": "claim", "key": "monthly_cost", "meaning": "Cost: 7 units.",
            "evidence_refs": [expansion.evidence_refs[0].evidence_id],
            "evidence_class": "SOURCE_DIRECT",
        }],
    )
    recorder = RunRecorder(
        CatalystGateway(workspace).traces,
        run_id="d2_v2_projection_run", request_id="d2_v2_projection_req",
        invocation_id="d2_v2_projection_inv", event_schema_version="1.5",
    )
    recorder.start(request_kind="d2_v2_projection", actor="synthetic_test", component="test")
    handoff = handoff_external_candidate(
        typed,
        source_root=source_root,
        wiki=wiki,
        recorder=recorder,
        producer_origin="codex_external",
        producer_items=[{
            "kind": "claim", "key": "monthly_cost", "meaning": "Cost: 7 units.",
            "evidence_class": "observed_from_source",
            "evidence": {
                "line_start": 2, "line_end": 2, "quote": "Cost: 7 units.",
                "span_sha256": expansion.evidence_refs[0].span_sha256,
            },
        }],
        actor_context={
            "simulation": True, "verified": True, "permissions": ("knowledge.propose",),
            "readable_scope_ids": (wiki.scope_id,),
        },
    )
    recorder.finish("success", model_calls=0, error_owner=None)

    assert handoff.wiki_handoff == "CANDIDATE_PROPOSED_ONLY"
    assert handoff.handoff_receipt["status"] == "proposed"
    assert handoff.handoff_receipt["active"] is False
    assert handoff.handoff_receipt["accepted"] is False
    candidate = wiki.semantic_state()["candidates"][handoff.handoff_receipt["candidate_id"]]
    assert candidate["status"] == "PROPOSED"
    assert wiki.semantic_state()["active_version_id"] is None
