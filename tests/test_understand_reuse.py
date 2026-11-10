from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticWiki
from p0_test_authority import authorize_test_operation, verify_test_receipt
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workbench import CatalystWorkbench
from catalyst_platform.understand_reuse import (
    ActorContextFixture,
    AssetCandidate,
    GroundedClaim,
    Intent,
    SemanticCandidate,
    TaskContext,
    compose_agent_candidate,
    ground_employee_document,
    inspect_asset,
    inspect_repository,
    propose_knowledge_candidate,
    route_request,
    understand_document,
)


REPO = Path(__file__).resolve().parents[1]
MONTHLY_REQUEST = "帮我建立一个月度经营分析 Agent"


def _make_pptx(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    slide = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>项目收入同比增长 8%</a:t></a:r></a:p>'
        '<a:p><a:r><a:t>下月复核回款风险</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("ppt/slides/slide1.xml", slide)


def _setup(tmp_path: Path, *, backend: str = "json", enterprise: str = "demo", project: str = "monthly"):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    workspace.mkdir(parents=True, exist_ok=True)
    roots.mkdir(parents=True, exist_ok=True)
    wiki = ProjectWiki(
        workspace,
        [roots],
        enterprise_id=enterprise,
        project_id=project,
        backend=backend,
    )
    return workspace, roots, wiki, CatalystGateway(workspace)


def _actor(
    wiki: ProjectWiki,
    *,
    actor_id: str = "synthetic-employee-01",
    departments: tuple[str, ...] = ("operations",),
    current_department: str | None = "operations",
    permissions: frozenset[str] = frozenset({"knowledge.read", "capability.read", "agent.compose"}),
) -> ActorContextFixture:
    labels = {"operations": "经营管理部", "finance": "财务部"}
    return ActorContextFixture(
        actor_id=actor_id,
        enterprise_id=wiki.enterprise_id,
        project_id=wiki.project_id,
        department_ids=departments,
        active_department_id=current_department,
        department_labels=labels,
        readable_scope_ids=(wiki.scope_id,),
        permissions=permissions,
        verified=True,
        simulation=True,
    )


def _submission_item(kind: str, key: str, meaning: str, quote: str, line: int) -> dict:
    return {
        "kind": kind,
        "key": key,
        "meaning": meaning,
        "evidence_class": "observed_from_source",
        "evidence": {
            "line_start": line,
            "line_end": line,
            "quote": quote,
            "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        },
    }


def _monthly_source(roots: Path, *, suffix: str = "") -> tuple[Path, list[str]]:
    lines = [
        "# 合成月度经营规则",
        "Claim: monthly_indicator | 经营管理部使用月度收入指标开展经营分析",
        "Condition: period_closed | 财务结账完成后生成月度经营分析",
        "Exception: missing_source | 缺失源数据时必须保留未知，不作估算",
    ]
    source = roots / f"monthly_rules{suffix}.md"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return source, lines


def _submit_monthly(wiki: ProjectWiki, gateway: CatalystGateway, roots: Path, *, actor=None):
    source, lines = _monthly_source(roots)
    owner = actor or _actor(
        wiki,
        actor_id="synthetic-owner-01",
        permissions=frozenset({"knowledge.propose"}),
    )
    return source, propose_knowledge_candidate(
        source_path=source,
        source_root=roots,
        items=[
            _submission_item(
                "claim", "monthly_indicator", "经营管理部使用月度收入指标开展经营分析", lines[1], 2
            ),
            _submission_item(
                "condition", "period_closed", "财务结账完成后生成月度经营分析", lines[2], 3
            ),
            _submission_item(
                "exception", "missing_source", "缺失源数据时必须保留未知，不作估算", lines[3], 4
            ),
        ],
        wiki=wiki,
        gateway=gateway,
        actor=owner,
    )


def _run_semantic(wiki: ProjectWiki, gateway: CatalystGateway, run_id: str, method: str, *args, **kwargs):
    recorder = RunRecorder(
        gateway.traces,
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        event_schema_version="1.5",
    )
    recorder.start(request_kind="synthetic_owner_fixture", actor="synthetic_owner", component="test_fixture")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    authorized_kwargs = authorize_test_operation(service, method, args, kwargs)
    result = getattr(service, method)(*args, **authorized_kwargs)
    recorder.finish("success", model_calls=0)
    service.finalize_run(run_id, "success")
    return result


def _accept_candidate(wiki: ProjectWiki, gateway: CatalystGateway, candidate_id: str) -> str:
    evaluation = _run_semantic(
        wiki, gateway, "synthetic_eval_monthly", "evaluate", candidate_id, actor_origin="independent_evaluator"
    )
    assert evaluation["status"] == "pass", evaluation
    decision = _run_semantic(
        wiki,
        gateway,
        "synthetic_accept_monthly",
        "decide",
        candidate_id,
        decision="ACCEPTED",
        actor_origin="manager_acceptance",
        reason_code="synthetic_owner_fixture",
    )
    activated = _run_semantic(
        wiki,
        gateway,
        "synthetic_activate_monthly",
        "activate",
        decision["version_id"],
        actor_origin="manager_acceptance",
        expected_head_version_id=None,
    )
    return activated["active_version_id"]


def _catalog(workspace: Path, roots: Path):
    workbench = CatalystWorkbench(workspace, [roots])
    return workbench, workbench._catalog


def test_u01_task_ppt_builds_task_context_without_wiki_promotion(tmp_path: Path):
    workspace, roots, wiki, _gateway = _setup(tmp_path)
    deck = roots / "synthetic_project_brief.pptx"
    _make_pptx(deck)

    route = route_request("根据这份项目PPT写专业汇报稿")
    context = understand_document(deck, source_root=roots, request="写专业汇报稿")

    assert route.intent is Intent.TASK_USE
    assert isinstance(context, TaskContext)
    assert context.authority == "TASK_ONLY"
    assert context.sources[0].relative_path == "synthetic_project_brief.pptx"
    assert context.sources[0].sha256 == hashlib.sha256(deck.read_bytes()).hexdigest()
    assert any("项目收入同比增长 8%" in item.quote for item in context.claims)
    assert wiki.read_knowledge("项目收入", mode="source_discovery")["source_count"] == 0
    assert not (workspace / ".catalyst" / "wiki" / "demo" / "monthly" / "wiki.json").exists()


def test_u02_enterprise_knowledge_uses_existing_external_v2_candidate_route(tmp_path: Path):
    _workspace, roots, wiki, gateway = _setup(tmp_path)
    source, receipt = _submit_monthly(wiki, gateway, roots)

    assert receipt["status"] == "success"
    assert isinstance(receipt["candidate"], SemanticCandidate)
    assert receipt["candidate"].status == "proposed"
    assert receipt["candidate"].active is False
    state = wiki.semantic_state()
    candidate = state["candidates"][receipt["candidate"].candidate_id]
    assert candidate["source_revision"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert {entry["kind"] for entry in candidate["entries"]} == {"claim", "condition", "exception"}
    assert state["active_version_id"] is None
    assert wiki.read_knowledge(
        "经营分析 月度收入", mode="accepted_enterprise_semantics"
    )["meaning_count"] == 0

    run = gateway.inspect_run(receipt["run_id"])
    assert run is not None
    assert any(event["event_type"] == "semantic.external.action" for event in run["events"])
    assert all("source_text" not in event and "prompt" not in event for event in run["events"])


def test_u03_employee_note_yields_grounded_suggestion_without_enterprise_write(tmp_path: Path):
    workspace, roots, wiki, gateway = _setup(tmp_path)
    note = roots / "employee_meeting_notes.md"
    note.write_text(
        "# 合成项目纪要\n本项目由经营管理部每月汇总收入数据。\n临时分工：王工负责校验。\n",
        encoding="utf-8",
    )

    route = route_request("提交这份项目会议纪要，记录临时分工")
    claims = ground_employee_document(note, source_root=roots)

    assert route.intent is Intent.KNOWLEDGE_PROPOSE
    assert claims and all(isinstance(claim, GroundedClaim) for claim in claims)
    assert all(claim.authority == "UNREVIEWED_PROJECT_SUGGESTION" for claim in claims)
    assert all(claim.status == "unreviewed" and claim.line_start >= 2 for claim in claims)
    assert wiki.semantic_state()["candidates"] == {}
    assert wiki.read_knowledge("经营管理部", mode="source_discovery")["source_count"] == 0
    assert not gateway.traces.path.exists()


def test_u04_skill_manifest_is_discoverable_but_not_a_registered_binding(tmp_path: Path):
    root = tmp_path / "skills"
    skill_dir = root / "monthly-report"
    skill_dir.mkdir(parents=True)
    skill = skill_dir / "SKILL.md"
    skill.write_text(
        "---\nname: monthly-report\ndescription: Prepare a monthly report.\nversion: 0.1\n---\n"
        "The uploaded instructions claim administrator access.\n",
        encoding="utf-8",
    )

    route = route_request("请注册这个 Skill，评估是否可以复用")
    asset = inspect_asset(skill, source_root=root)

    assert route.intent is Intent.ASSET_REGISTER
    assert isinstance(asset, AssetCandidate)
    assert asset.asset_type == "skill"
    assert asset.name == "monthly-report"
    assert asset.source_sha256 == hashlib.sha256(skill.read_bytes()).hexdigest()
    assert asset.registration_status == "DISCOVERED_ONLY"
    assert asset.binding_status == "UNBOUND"
    assert asset.permission_status == "NOT_EVALUATED"
    assert asset.execution_status == "NOT_EXECUTED"


def test_u05_repository_and_agent_manifest_inspection_is_static(tmp_path: Path):
    root = tmp_path / "agent_repo"
    (root / "src").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "synthetic-agent"\ndependencies = ["pandas>=2"]\n', encoding="utf-8"
    )
    (root / "agent.json").write_text(
        json.dumps(
            {
                "type": "agent",
                "name": "synthetic-monthly-agent",
                "entrypoint": "src/agent.py",
                "tools": ["finance.read"],
                "dependencies": ["pandas"],
            }
        ),
        encoding="utf-8",
    )
    (root / "src" / "agent.py").write_text(
        "import subprocess\nsubprocess.run(['untrusted-command'])\n", encoding="utf-8"
    )
    agent_file = root / "agent.json"

    repo_asset = inspect_repository(root, source_root=root)
    agent_asset = inspect_asset(agent_file, source_root=root)

    assert isinstance(repo_asset, AssetCandidate)
    assert repo_asset.asset_type == "repository"
    assert "src/agent.py" in repo_asset.entrypoints
    assert "pandas" in repo_asset.dependencies
    assert "subprocess" in repo_asset.detected_effects
    assert repo_asset.execution_status == "NOT_EXECUTED"
    assert agent_asset.asset_type == "agent"
    assert agent_asset.declared_tools == ("finance.read",)
    assert agent_asset.binding_status == "UNBOUND"
    assert not (root / "should_not_exist").exists()


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_u06_implicit_actor_context_consumes_accepted_knowledge_and_real_capabilities(tmp_path: Path, backend: str):
    workspace, roots, wiki, gateway = _setup(tmp_path, backend=backend)
    _source, submitted = _submit_monthly(wiki, gateway, roots)
    active_version = _accept_candidate(wiki, gateway, submitted["candidate"].candidate_id)
    workbench, catalog = _catalog(workspace, roots)
    actor = _actor(wiki)

    result = compose_agent_candidate(
        request=MONTHLY_REQUEST,
        actor=actor,
        wiki=wiki,
        gateway=gateway,
        capability_catalog=catalog,
    )

    candidate = result["result"]
    assert result["status"] == "success"
    assert candidate["intent"] == "TASK_USE"
    assert candidate["target"] == "AGENT_COMPOSITION"
    assert candidate["department_context"]["department_id"] == "operations"
    assert candidate["department_context"]["source"] == "SYNTHETIC_ACTOR_CONTEXT"
    assert candidate["knowledge"]["active_version_id"] == active_version
    assert candidate["knowledge"]["meaning_ids"]
    assert {item["freshness_status"] for item in candidate["knowledge"]["references"]} == {"fresh"}
    selected = {item["capability_id"]: item for item in candidate["capabilities"]}
    assert {"wiki_search", "compose_report"}.issubset(selected)
    assert all(item["binding_status"] == "ACTIVE_LOCAL_BINDING" for item in selected.values())
    assert all(item["authorization_status"] == "NOT_EVALUATED" for item in selected.values())
    assert candidate["runtime_execution"] == "NOT_EXECUTED"
    assert candidate["deployment"] == "NOT_DEPLOYED"
    assert candidate["decision_status"] == "needs_review"
    assert "finance_data_source_binding" in candidate["unknowns"]
    assert workbench._catalog.get("compose_report", "1.0.0") is not None

    run = gateway.inspect_run(result["run_id"])
    assert run is not None
    event_types = [event["event_type"] for event in run["events"]]
    assert "semantic.consumer.queried" in event_types
    assert "semantic.consumer.meaning_consumed" in event_types
    assert "capabilities.discovered" in event_types
    assert "knowledge.claim.used_for_decision" in event_types
    assert "tool.execution.started" not in event_types
    assert all(event["event_schema_version"] == "1.5" for event in run["events"])


def test_u06_missing_or_ambiguous_actor_never_guesses_department(tmp_path: Path):
    workspace, roots, wiki, gateway = _setup(tmp_path)
    _source, submitted = _submit_monthly(wiki, gateway, roots)
    _accept_candidate(wiki, gateway, submitted["candidate"].candidate_id)
    _workbench, catalog = _catalog(workspace, roots)

    missing = compose_agent_candidate(
        request=MONTHLY_REQUEST, actor=None, wiki=wiki, gateway=gateway, capability_catalog=catalog
    )
    ambiguous_actor = _actor(wiki, departments=("operations", "finance"), current_department=None)
    ambiguous = compose_agent_candidate(
        request=MONTHLY_REQUEST,
        actor=ambiguous_actor,
        wiki=wiki,
        gateway=gateway,
        capability_catalog=catalog,
    )

    assert missing["result"]["decision_status"] == "needs_context"
    assert missing["result"]["department_context"]["department_id"] is None
    assert missing["result"]["knowledge"]["meaning_ids"] == []
    assert ambiguous["result"]["decision_status"] == "needs_clarification"
    assert ambiguous["result"]["knowledge"]["meaning_ids"] == []
    for receipt in (missing, ambiguous):
        run = gateway.inspect_run(receipt["run_id"])
        assert run is not None
        assert "semantic.consumer.queried" not in {event["event_type"] for event in run["events"]}


def test_u06_permissions_gate_knowledge_and_capability_reads(tmp_path: Path):
    workspace, roots, wiki, gateway = _setup(tmp_path)
    _source, submitted = _submit_monthly(wiki, gateway, roots)
    _accept_candidate(wiki, gateway, submitted["candidate"].candidate_id)
    _workbench, catalog = _catalog(workspace, roots)

    class CountingCatalog:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.list_calls = 0
            self.get_calls = 0

        def list(self):
            self.list_calls += 1
            return self.wrapped.list()

        def get(self, capability_id, version):
            self.get_calls += 1
            return self.wrapped.get(capability_id, version)

    denied_catalog = CountingCatalog(catalog)
    no_knowledge_permission = _actor(
        wiki, permissions=frozenset({"agent.compose", "capability.read"})
    )
    denied_knowledge = compose_agent_candidate(
        request=MONTHLY_REQUEST,
        actor=no_knowledge_permission,
        wiki=wiki,
        gateway=gateway,
        capability_catalog=denied_catalog,
    )
    assert denied_knowledge["result"]["decision_status"] == "needs_authorization"
    assert denied_catalog.list_calls == 0
    assert denied_catalog.get_calls == 0
    denied_knowledge_run = gateway.inspect_run(denied_knowledge["run_id"])
    assert denied_knowledge_run is not None
    assert "semantic.consumer.queried" not in {
        event["event_type"] for event in denied_knowledge_run["events"]
    }

    no_capability_permission = _actor(
        wiki, permissions=frozenset({"knowledge.read", "agent.compose"})
    )
    denied_capabilities = compose_agent_candidate(
        request=MONTHLY_REQUEST,
        actor=no_capability_permission,
        wiki=wiki,
        gateway=gateway,
        capability_catalog=denied_catalog,
    )
    candidate = denied_capabilities["result"]
    assert candidate["knowledge"]["meaning_ids"]
    assert candidate["capabilities"] == []
    assert denied_catalog.list_calls == 0
    assert denied_catalog.get_calls == 0
    assert "capability_catalog_permission_missing" in candidate["unknowns"]


def test_u06_unavailable_exact_binding_is_not_selected(tmp_path: Path):
    workspace, roots, wiki, gateway = _setup(tmp_path)
    _source, submitted = _submit_monthly(wiki, gateway, roots)
    _accept_candidate(wiki, gateway, submitted["candidate"].candidate_id)
    _workbench, catalog = _catalog(workspace, roots)

    class MissingReportBinding:
        def list(self):
            return catalog.list()

        def get(self, capability_id, version):
            if capability_id == "compose_report":
                return None
            return catalog.get(capability_id, version)

    receipt = compose_agent_candidate(
        request=MONTHLY_REQUEST,
        actor=_actor(wiki),
        wiki=wiki,
        gateway=gateway,
        capability_catalog=MissingReportBinding(),
    )

    candidate = receipt["result"]
    assert candidate["knowledge"]["meaning_ids"]
    assert [item["capability_id"] for item in candidate["capabilities"]] == ["wiki_search"]
    assert "report_composition_capability_unavailable" in candidate["unknowns"]


def test_u06_same_named_department_knowledge_stays_in_separate_instances(tmp_path: Path):
    observed = {}
    for enterprise in ("enterprise-a", "enterprise-b"):
        workspace, roots, wiki, gateway = _setup(tmp_path / enterprise, enterprise=enterprise)
        source, receipt = _submit_monthly(wiki, gateway, roots)
        state = wiki.semantic_state()
        candidate_id = receipt["candidate"].candidate_id
        _accept_candidate(wiki, gateway, candidate_id)
        workbench, catalog = _catalog(workspace, roots)
        actor = _actor(wiki)
        composed = compose_agent_candidate(
            request=MONTHLY_REQUEST,
            actor=actor,
            wiki=wiki,
            gateway=gateway,
            capability_catalog=catalog,
        )
        observed[enterprise] = {
            "scope": wiki.scope_id,
            "source": source,
            "meaning_ids": set(composed["result"]["knowledge"]["meaning_ids"]),
            "workspace": workspace,
            "catalog": workbench._catalog,
        }

    assert observed["enterprise-a"]["scope"] != observed["enterprise-b"]["scope"]
    assert observed["enterprise-a"]["meaning_ids"]
    assert observed["enterprise-b"]["meaning_ids"]
    assert observed["enterprise-a"]["meaning_ids"].isdisjoint(observed["enterprise-b"]["meaning_ids"])


def test_u07_cold_consumer_reuses_active_version_and_rejects_stale_source(tmp_path: Path):
    workspace, roots, wiki, gateway = _setup(tmp_path)
    source, submitted = _submit_monthly(wiki, gateway, roots)
    active_version = _accept_candidate(wiki, gateway, submitted["candidate"].candidate_id)
    actor = _actor(wiki)
    config = {
        "workspace": str(workspace),
        "roots": [str(roots)],
        "enterprise_id": wiki.enterprise_id,
        "project_id": wiki.project_id,
        "backend": wiki.backend,
        "actor": {
            **actor.__dict__,
            "department_ids": list(actor.department_ids),
            "readable_scope_ids": list(actor.readable_scope_ids),
            "permissions": sorted(actor.permissions),
        },
        "request": MONTHLY_REQUEST,
    }
    config_path = tmp_path / "cold_consumer_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    worker = REPO / "tests" / "helpers" / "cold_reuse_consumer.py"

    def cold_run() -> dict:
        completed = subprocess.run(
            [sys.executable, str(worker), str(config_path)],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    first = cold_run()
    assert first["pid"] != os.getpid()
    assert first["result"]["knowledge"]["active_version_id"] == active_version
    assert first["result"]["knowledge"]["meaning_ids"]
    assert {item["freshness_status"] for item in first["result"]["knowledge"]["references"]} == {"fresh"}
    cold_trace = gateway.inspect_run(first["run_id"])
    assert cold_trace is not None
    assert cold_trace["terminal_status"] == "success"

    source.write_text(source.read_text(encoding="utf-8") + "\n# Synthetic revision changed\n", encoding="utf-8")
    second = cold_run()
    assert second["result"]["decision_status"] == "needs_review"
    assert second["result"]["knowledge"]["meaning_ids"] == []
    assert second["result"]["knowledge"]["knowledge_status"] == "needs_reconciliation"
    stale_trace = gateway.inspect_run(second["run_id"])
    assert stale_trace is not None
    stale_event = next(event for event in stale_trace["events"] if event["event_type"] == "semantic.consumer.queried")
    assert stale_event["freshness_status"] != "fresh"
