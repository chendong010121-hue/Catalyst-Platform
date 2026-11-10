"""Every question asked of the active version is on the record, hit or miss."""

from __future__ import annotations

import hashlib
from pathlib import Path

from catalyst_platform.consumption import ledger_path, rows, summarize
from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_chain import run_chain
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki

MATERIAL = (
    "# Quality review\n"
    "Rule: Reviewer checks the package before release\n"
    "relation: reviewer | performs | quality_review\n"
)


def _published(tmp_path) -> Path:
    sources = tmp_path / "sources"
    sources.mkdir()
    material = sources / "responsibility.md"
    material.write_text(MATERIAL, encoding="utf-8")
    review = tmp_path / "review.md"
    review.write_text("# review\nACCEPT\n", encoding="utf-8")
    run_chain(workspace=tmp_path / "workspace", source=material, review=review)
    return material


def _reader(tmp_path, run_id: str):
    workspace = (tmp_path / "workspace").resolve()
    wiki = ProjectWiki(workspace, [tmp_path / "sources"], enterprise_id="synthetic",
                       project_id="ontology-chain")
    recorder = RunRecorder(
        JsonlTraceStore(workspace), run_id=run_id, request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest())
    recorder.start(request_kind="consumption_test", actor="local_cli_user", component="CatalystGateway")
    return wiki, SemanticWiki(wiki, recorder=recorder), recorder


def test_the_chain_read_is_already_on_the_ledger(tmp_path):
    _published(tmp_path)
    entries = rows((tmp_path / "workspace").resolve())

    assert len(entries) == 1
    assert entries[0]["read_mode"] == "accepted_enterprise_semantics"
    assert entries[0]["hit"] is True
    assert entries[0]["meaning_ids"]
    assert entries[0]["version_id"] == entries[0]["active_version_id"]
    assert entries[0]["freshness_status"] == "fresh"


def test_a_hit_and_a_miss_are_both_recorded(tmp_path):
    _published(tmp_path)
    wiki, service, recorder = _reader(tmp_path, "run_consumer")
    active = wiki.semantic_state()["active_version_id"]

    hit = service.read_knowledge("quality review", mode="accepted_enterprise_semantics",
                                 actor_origin="catalyst_deterministic", include_all_active=True)
    miss = service.read_knowledge("payroll approval", mode="accepted_enterprise_semantics",
                                  actor_origin="catalyst_deterministic")
    recorder.finish("success", model_calls=0)
    service.finalize_run("run_consumer", "success")

    entries = rows(wiki.workspace)
    assert [row["query"] for row in entries][-2:] == ["quality review", "payroll approval"]
    hit_row, miss_row = entries[-2:]
    assert hit_row["hit"] is True and sorted(hit_row["meaning_ids"]) == sorted(hit["meaning_ids"])
    assert hit_row["version_id"] == active
    assert miss_row["hit"] is False and miss_row["meaning_ids"] == []
    assert miss_row["version_id"] == active


def test_the_question_is_kept_out_of_the_run_trace(tmp_path):
    _published(tmp_path)
    wiki, service, recorder = _reader(tmp_path, "run_private_query")
    service.read_knowledge("who approves payroll overruns", mode="accepted_enterprise_semantics",
                           actor_origin="catalyst_deterministic")
    recorder.finish("success", model_calls=0)
    service.finalize_run("run_private_query", "success")

    trace_text = JsonlTraceStore(wiki.workspace).path.read_text(encoding="utf-8")
    assert "who approves payroll overruns" not in trace_text
    assert "who approves payroll overruns" in ledger_path(wiki.workspace).read_text(encoding="utf-8")


def test_the_summary_groups_each_question_with_what_answered_it(tmp_path):
    _published(tmp_path)
    wiki, service, recorder = _reader(tmp_path, "run_summary")
    service.read_knowledge("quality review", mode="accepted_enterprise_semantics",
                           actor_origin="catalyst_deterministic", include_all_active=True)
    service.read_knowledge("payroll approval", mode="accepted_enterprise_semantics",
                           actor_origin="catalyst_deterministic")
    recorder.finish("success", model_calls=0)
    service.finalize_run("run_summary", "success")

    summary = summarize(wiki.workspace)
    by_question = {row["query"]: row for row in summary["questions"]}
    assert set(by_question) == {"responsibility", "quality review", "payroll approval"}
    assert by_question["payroll approval"]["misses"] == 1
    assert by_question["payroll approval"]["hits"] == 0
    assert by_question["quality review"]["hits"] == 1
    assert by_question["responsibility"]["hits"] == 1
    assert summary["reads"] == 3
    assert summary["miss_reads"] == 1
    assert by_question["quality review"]["version_ids"] == [wiki.semantic_state()["active_version_id"]]
