from __future__ import annotations

import json
from pathlib import Path

from catalyst_platform.__main__ import main
from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.understand_only import (
    GroundedItem,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    _SkillResolver,
    _coverage,
    format_understanding_context,
)


def _request(source: Path, *, depth: str = "targeted", budget: int = 4) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_code_first",
        message="请理解这些资料中的经营职责、规则和未知项",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_test",
        requested_depth=depth,
        budget_steps=budget,
    )


def test_selected_skill_instructions_are_available_to_the_consumer(tmp_path: Path):
    source = tmp_path / "business.md"
    source.write_text("经营分析应关注收入与成本。", encoding="utf-8")

    result = UnderstandPort().understand(_request(source), source_root=tmp_path)

    assert all(skill.instructions.strip() for skill in result.selected_skills)
    assert "Separate explicit entities" in format_understanding_context(result)
    assert "understand-enterprise-semantics" in format_understanding_context(result)


def test_inventory_depth_and_one_step_budget_stop_before_semantic_skills(tmp_path: Path):
    source = tmp_path / "business.md"
    source.write_text("组织职责和经营分析方法。", encoding="utf-8")

    result = UnderstandPort().understand(_request(source, depth="inventory", budget=1), source_root=tmp_path)

    assert result.route.requested_depth == "inventory"
    assert result.result_type == "SourceInventory"
    assert [skill.skill_id for skill in result.selected_skills] == ["understand-source-inventory"]
    assert len(result.strategy_run_receipt) == 1
    assert result.status == "COMPLETE"


def test_insufficient_budget_is_visible_and_coverage_is_not_claimed(tmp_path: Path):
    source = tmp_path / "business.md"
    source.write_text("组织职责和经营分析方法。", encoding="utf-8")

    result = UnderstandPort().understand(_request(source, depth="semantic", budget=1), source_root=tmp_path)

    assert result.status == "PARTIAL"
    assert result.stopping_reason == "strategy_budget_exhausted"
    assert all(row.status == "NOT_TESTED" for row in result.coverage_receipt)
    assert all(receipt.status in {"COMPLETED", "SKIPPED_BUDGET"} for receipt in result.strategy_run_receipt)


def test_depth_changes_document_selection_and_keeps_source_inventory(tmp_path: Path):
    source = tmp_path / "business.md"
    source.write_text("收入应按月统计。\n成本应按月核对。\n人力考勤由部门管理。", encoding="utf-8")
    port = UnderstandPort()
    targeted = port.understand(
        UnderstandingRequest("req_targeted", "经营资料摘要", (source,), UnderstandIntent.TASK_USE, requested_depth="targeted"),
        source_root=tmp_path,
    )
    deep = port.understand(
        UnderstandingRequest("req_deep", "成本", (source,), UnderstandIntent.TASK_USE, requested_depth="semantic"),
        source_root=tmp_path,
    )

    assert len(targeted.source_inventory) == len(deep.source_inventory) == 1
    assert len(targeted.evidence_refs) == 3
    assert [item.quote for item in deep.evidence_refs] == ["成本应按月核对。"]
    assert any(item.strategy_id == "document_grounding" for item in deep.strategy_run_receipt)


def test_coverage_requires_source_evidence_and_relation_shape_not_kind_alone():
    item = GroundedItem(
        item_id="item_call",
        kind="call",
        key="tool_call",
        meaning="A function calls a tool.",
        evidence_refs=(),
        evidence_class="inferred",
        confidence="not_calibrated",
    )

    rows = _coverage(UnderstandIntent.ASSET_INSPECT, [item], [], [], known_evidence_ids=set())

    by_id = {row.question_id: row for row in rows}
    assert by_id["tools_and_workers"].status != "ANSWERED"
    assert by_id["effects"].status != "ANSWERED"


def test_codex_producer_row_with_unbound_evidence_is_kept_unresolved_and_named(tmp_path: Path):
    source = tmp_path / "business.md"
    source.write_text("财务部门负责月度经营分析。", encoding="utf-8")
    port = UnderstandPort()
    base = port.understand(_request(source), source_root=tmp_path)

    result = port.attach_producer_items(
        base,
        producer_kind="CODEX_EXTERNAL",
        producer_invocation_id="codex-call-test",
        items=[{
            "kind": "claim",
            "key": "responsibility",
            "meaning": "财务部门承担月度经营分析。",
            "evidence_refs": ["ev_missing"],
            "evidence_class": "SOURCE_DIRECT",
        }],
    )
    # A row that names evidence the port never supplied cannot stand on what it claims;
    # it is kept unresolved and counted, and does not take the rest of the answer down
    # with it.
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "responsibility", "rule": "evidence_ref_not_supplied"}]
    # A row that cannot stand on evidence this run never issued is run evidence, not a
    # candidate: it is kept whole with its reason, and no Wiki is ever handed it as a claim.
    assert list(result.semantic_candidate.items) == []
    diagnostic = {row["key"]: row for row in result.run_diagnostics}["responsibility"]
    assert diagnostic["kind"] == "unknown"
    assert diagnostic["uncertainty"].startswith("degraded:evidence_ref_not_supplied")
    assert diagnostic["destination"] == "run_evidence"
    assert diagnostic["degradation"]["class"] == "run_diagnostic"


def test_codex_producer_result_records_attribution_without_claiming_hidden_trace(tmp_path: Path):
    source = tmp_path / "business.md"
    source.write_text("财务部门负责月度经营分析。", encoding="utf-8")
    port = UnderstandPort()
    base = port.understand(_request(source), source_root=tmp_path)
    evidence_id = base.evidence_refs[0].evidence_id

    result = port.attach_producer_items(
        base,
        producer_kind="CODEX_EXTERNAL",
        producer_invocation_id="codex-call-test",
        items=[{
            "kind": "claim",
            "key": "responsibility",
            "meaning": "财务部门负责月度经营分析。",
            "subject": "财务部门",
            "predicate": "负责",
            "object": "月度经营分析",
            "evidence_refs": [evidence_id],
            "evidence_class": "SOURCE_DIRECT",
        }],
    )

    assert result.semantic_candidate is not None
    assert result.semantic_candidate.producer_origin == "codex_external"
    assert result.producer_attribution["producer_kind"] == "CODEX_EXTERNAL"
    assert result.producer_attribution["r4_visibility"] == "PORT_BOUNDARY_ONLY"
    assert result.semantic_candidate.items[0].evidence_refs == (evidence_id,)


def test_codex_understand_cli_uses_gateway_r4_and_same_port(tmp_path: Path, capsys):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "business.md"
    source.write_text("部门负责分析并按月提交报告。", encoding="utf-8")
    workspace = tmp_path / "workspace"

    exit_code = main([
        "understand",
        "--workspace", str(workspace),
        "--source-root", str(source_root),
        "--source", "business.md",
        "--message", "理解经营职责和月度报告要求",
        "--intent", "KNOWLEDGE_PROPOSE",
        "--scope-id", "scope_test",
        "--depth", "semantic",
        "--budget-steps", "4",
    ])

    assert exit_code == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["operation"] == "understand.inspect"
    assert envelope["result"]["request_id"]
    assert envelope["result"]["selected_skills"]
    assert envelope["trace_path"]
    trace = CatalystGateway(workspace).inspect_run(envelope["run_id"])
    assert trace is not None
    assert any(event.get("span_name", "").startswith("understand.strategy.") for event in trace["events"])
    assert all(event.get("run_id") == envelope["run_id"] for event in trace["events"])
    assert "部门负责分析并按月提交报告" not in json.dumps(trace, ensure_ascii=False)


def test_codex_cli_attaches_external_items_to_the_same_port_and_correlates_r4(tmp_path: Path, capsys):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "business.md"
    source.write_text("财务部门负责月度经营分析。", encoding="utf-8")
    workspace = tmp_path / "workspace"
    request_args = [
        "--workspace", str(workspace),
        "--source-root", str(source_root),
        "--source", "business.md",
        "--message", "整理经营职责语义候选",
        "--intent", "KNOWLEDGE_PROPOSE",
        "--scope-id", "scope_test",
        "--depth", "targeted",
        "--budget-steps", "4",
    ]
    assert main(["understand", *request_args]) == 0
    prepared = json.loads(capsys.readouterr().out)
    evidence_id = prepared["result"]["evidence_refs"][0]["evidence_id"]
    producer_items = tmp_path / "private-producer-items.json"
    producer_items.write_text(json.dumps([{
        "kind": "claim",
        "key": "monthly_analysis_responsibility",
        "meaning": "财务部门负责月度经营分析。",
        "subject": "财务部门",
        "predicate": "负责",
        "object": "月度经营分析",
        "evidence_refs": [evidence_id],
        "evidence_class": "SOURCE_DIRECT",
    }], ensure_ascii=False), encoding="utf-8")

    assert main([
        "understand", *request_args,
        "--producer-items", str(producer_items),
        "--producer-invocation-id", "codex-invocation-01",
        "--correlation-id", prepared["run_id"],
    ]) == 0
    attached = json.loads(capsys.readouterr().out)
    result = attached["result"]
    assert result["producer_attribution"]["producer_kind"] == "CODEX_EXTERNAL"
    assert result["producer_attribution"]["hidden_reasoning"] == "NOT_OBSERVED"
    assert result["wiki_handoff"] == "CANDIDATE_READY_PROPOSAL_ONLY"
    trace = CatalystGateway(workspace).inspect_run(attached["run_id"])
    assert trace is not None
    assert all(event.get("correlation_id") == prepared["run_id"] for event in trace["events"])
    assert any(
        event.get("span_name") == "understand.producer.output_attached"
        and event.get("execution_id") == "codex-invocation-01"
        for event in trace["events"]
    )
    assert "财务部门负责月度经营分析" not in json.dumps(trace, ensure_ascii=False)


def test_progressive_skill_load_reads_markdown_references_but_never_scripts(tmp_path: Path):
    skill_root = tmp_path / "skills"
    skill_dir = skill_root / "understand-asset-inspector"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: understand-asset-inspector\nversion: 0.1.0\ndescription: inspect\n---\nRead asset declarations.\n",
        encoding="utf-8",
    )
    (skill_dir / "references" / "guide.md").write_text("WHAT, HOW, and unresolved boundaries.", encoding="utf-8")
    (skill_dir / "scripts" / "do_not_run.py").write_text("raise RuntimeError('must not run')", encoding="utf-8")

    skill = _SkillResolver(skill_root).load(["understand-asset-inspector"], progressive=True)[0]

    assert skill.instructions == "Read asset declarations."
    assert skill.loaded_reference_paths == ("understand-asset-inspector/references/guide.md",)
    assert skill.reference_texts == (("understand-asset-inspector/references/guide.md", "WHAT, HOW, and unresolved boundaries."),)

