"""One command from admitted material to a cold read of the version it published.

The chain is the product path, not a test harness. It stages the material, proposes the
candidate the material supports, runs the structural checks, turns the independent review
into a signed receipt, has the owner accept and activate the result, and then reads the
version back through a fresh Wiki that never saw the writing side. Each step is its own
recorded Run, so the chain report can name the run behind every state change.

Nothing here mints a verdict: a review disposition other than ACCEPT stops at the
decision, and the chain says so instead of publishing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import semantic_approval
from .gateway import CatalystGateway
from .semantic_keys import ROLES, ensure_key, load_key, verifier
from .semantic_wiki import SemanticTransitionError, SemanticWiki
from .wiki import ProjectWiki, WikiScopeError, WikiUnavailable

SCHEMA = "catalyst.ontology_chain.v0.1"
STAGE_ACTOR = "catalyst_deterministic"
PROPOSE_ACTOR = "codex_fixture"
EVALUATE_ACTOR = "independent_evaluator"
READ_ACTOR = "catalyst_deterministic"
ACCEPT_ACTOR = "manager_acceptance"


def _step(gateway: CatalystGateway, wiki: ProjectWiki, operation: str, actor_origin: str,
          input_value: dict, action) -> tuple[dict, str]:
    holder: dict = {}

    def execute(recorder):
        service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verifier(wiki.workspace))
        holder["service"] = service
        return action(service)

    outcome = gateway.semantic_operation(
        operation=operation,
        scope_id=wiki.scope_id,
        actor_origin=actor_origin,
        input_value=input_value,
        action=execute,
        finalize=lambda run_id, terminal: holder["service"].finalize_run(run_id, terminal),
    )
    if outcome["status"] != "success":
        error = outcome.get("error") or {}
        code = error.get("code", "chain_step_failed")
        raise SemanticTransitionError(
            code, f"{operation} failed with {code}; its Run is {outcome.get('run_id')}")
    return outcome["result"], outcome["run_id"]


def _quote(wiki: ProjectWiki, snapshot_cache: dict, evidence: dict) -> dict:
    """The source span an accepted meaning points at, read back from the Wiki's own source."""
    source_id = str(evidence.get("source_id"))
    if source_id not in snapshot_cache:
        try:
            snapshot_cache[source_id] = wiki.source_snapshot(source_id)
        except (WikiScopeError, WikiUnavailable):
            snapshot_cache[source_id] = None
    snapshot = snapshot_cache[source_id]
    start, end = evidence.get("line_start"), evidence.get("line_end") or evidence.get("line_start")
    quote = None
    if snapshot is not None and snapshot.get("current_revision") == evidence.get("source_revision"):
        lines = str(snapshot.get("content") or "").splitlines()
        if type(start) is int and type(end) is int and 1 <= start <= end <= len(lines):
            quote = "\n".join(lines[start - 1:end])
    row = {**evidence, "quote": quote}
    if quote is not None:
        digest = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        row["quote_sha256"] = digest
        if evidence.get("span_sha256"):
            row["quote_matches_span"] = digest == evidence["span_sha256"]
    return row


def run_chain(*, workspace, source, review, query: str | None = None,
              enterprise_id: str = "synthetic", project_id: str = "ontology-chain",
              backend: str = "json", disposition: str = "ACCEPT",
              source_root=None, report_path=None, limit: int = 100) -> dict:
    """Run the whole chain and return the report a person can check."""
    workspace = Path(workspace).expanduser()
    source = Path(source).expanduser()
    review = Path(review).expanduser()
    if not source.is_file():
        raise SemanticTransitionError("chain_source_missing", f"material {str(source)!r} does not exist")
    if not review.is_file():
        raise SemanticTransitionError("reviewer_report_missing",
                                      f"independent review {str(review)!r} does not exist")
    roots = [Path(root).expanduser() for root in source_root] if source_root else [source.parent]
    wiki = ProjectWiki(workspace, roots, enterprise_id=enterprise_id, project_id=project_id,
                       backend=backend)
    keys = {role: "existing" if load_key(wiki.workspace, role) else "created" for role in ROLES}
    for role in ROLES:
        ensure_key(wiki.workspace, role)
    gateway = CatalystGateway(wiki.workspace)

    report: dict = {
        "schema": SCHEMA,
        "workspace": str(wiki.workspace),
        "scope_id": wiki.scope_id,
        "material": {
            "path": str(source.resolve()),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        "review": {
            "path": str(review.resolve()),
            "sha256": hashlib.sha256(review.read_bytes()).hexdigest(),
            "disposition": disposition,
        },
        "signing_keys": keys,
        "steps": [],
        "candidate_id": None,
        "version_id": None,
        "active_version_id": None,
        "status": None,
    }

    staged, run_id = _step(
        gateway, wiki, "source.stage", STAGE_ACTOR,
        {"file": str(source), "project_id": project_id},
        lambda service: service.stage_source(source, actor_origin=STAGE_ACTOR))
    report["steps"].append({"step": "source.stage", "run_id": run_id, "status": staged["status"],
                            "source_id": staged["source_id"], "source_revision": staged["revision"]})
    report["material"]["source_id"] = staged["source_id"]
    report["material"]["source_revision"] = staged["revision"]

    proposed, run_id = _step(
        gateway, wiki, "candidate.propose", PROPOSE_ACTOR,
        {"file": str(source), "project_id": project_id},
        lambda service: service.propose(source, actor_origin=PROPOSE_ACTOR))
    candidate_id = proposed["candidate_id"]
    report["candidate_id"] = candidate_id
    report["steps"].append({"step": "candidate.propose", "run_id": run_id, "status": proposed["status"],
                            "candidate_id": candidate_id, "meaning_count": len(proposed["meaning_ids"])})

    state = wiki.semantic_state()
    candidate = state["candidates"][candidate_id]
    decision = state["decisions"].get(candidate.get("latest_decision_id") or "", {})
    version_id = decision.get("version_id") if decision.get("decision") == "ACCEPTED" else None
    active = state.get("active_version_id")

    if version_id is not None and version_id == active:
        report["status"] = "no_op"
        report["version_id"] = version_id
        report["steps"].append({"step": "candidate.evaluate", "run_id": None, "status": "already_accepted"})
        report["steps"].append({"step": "candidate.approve", "run_id": None, "status": "already_accepted"})
        report["steps"].append({"step": "version.activate", "run_id": None, "status": "already_active"})
    else:
        if version_id is None:
            evaluation, run_id = _step(
                gateway, wiki, "candidate.evaluate", EVALUATE_ACTOR,
                {"candidate_id": candidate_id, "evaluator_id": "structural-evaluator-v1"},
                lambda service: service.evaluate(candidate_id, actor_origin=EVALUATE_ACTOR,
                                                 evaluator_id="structural-evaluator-v1"))
            report["steps"].append({"step": "candidate.evaluate", "run_id": run_id,
                                    "status": evaluation["status"],
                                    "evaluation_id": evaluation["evaluation_id"]})
            if evaluation["status"] != "pass":
                report["status"] = "blocked"
                report["blocked"] = {"reason": "structural_evaluation_not_pass",
                                     "findings": [finding.get("code")
                                                  for finding in evaluation.get("findings", [])]}
                return _finish(wiki, report, query, report_path, limit)

            accepted, run_id = _step(
                gateway, wiki, "candidate.decide", ACCEPT_ACTOR,
                {"candidate_id": candidate_id, "decision": "ACCEPTED", "reason_code": "chain_review"},
                lambda service: semantic_approval.approve(
                    service, candidate_id, reviewer_report=review, disposition=disposition,
                    reason_code="chain_review"))
            report["steps"].append({"step": "candidate.approve", "run_id": run_id,
                                    "status": accepted["status"],
                                    "version_id": accepted.get("version_id")})
            if accepted["status"] == "refused":
                report["status"] = "refused"
                report["blocked"] = {"reason": accepted.get("reason"),
                                     "disposition": accepted.get("disposition")}
                return _finish(wiki, report, query, report_path, limit)
            version_id = accepted["version_id"]

        head = wiki.semantic_state().get("active_version_id")
        activated, run_id = _step(
            gateway, wiki, "version.activate", ACCEPT_ACTOR,
            {"version_id": version_id, "expected_head_version_id": head},
            lambda service: semantic_approval.activate(service, version_id, expected_head=head))
        report["steps"].append({"step": "version.activate", "run_id": run_id, "status": "activated",
                                "active_version_id": activated["active_version_id"]})
        report["status"] = "success"
        report["version_id"] = version_id

    return _finish(wiki, report, query, report_path, limit)


def _finish(wiki: ProjectWiki, report: dict, query, report_path, limit: int) -> dict:
    """Read the active version back through a fresh Wiki and record what was read."""
    cold = ProjectWiki(wiki.workspace, wiki.roots, enterprise_id=wiki.enterprise_id,
                       project_id=wiki.project_id, backend=wiki.backend)
    query_text = query or Path(report["material"]["path"]).stem.replace("_", " ")
    gateway = CatalystGateway(cold.workspace)
    projection, run_id = _step(
        gateway, cold, "ontology.query", READ_ACTOR,
        {"query": query_text, "mode": "accepted_enterprise_semantics", "include_all_active": query is None},
        lambda service: service.read_knowledge(
            query_text, mode="accepted_enterprise_semantics", actor_origin=READ_ACTOR,
            include_all_active=query is None, limit=limit))
    snapshots: dict = {}
    meanings = [{**meaning, "evidence": [_quote(cold, snapshots, evidence)
                                        for evidence in meaning.get("evidence", [])]}
                for meaning in projection["meanings"]]
    report["active_version_id"] = wiki.semantic_state().get("active_version_id")
    report["read"] = {
        "run_id": run_id,
        "query": query_text,
        "version_id": projection.get("version_id"),
        "active_version_id": projection.get("active_version_id"),
        "knowledge_status": projection.get("knowledge_status"),
        "freshness_status": projection.get("freshness_status"),
        "meaning_count": len(meanings),
        "meanings": meanings,
        "matches_active_version": projection.get("version_id") == report["active_version_id"],
    }
    report["steps"].append({"step": "ontology.query", "run_id": run_id,
                            "status": projection.get("knowledge_status"),
                            "meaning_count": len(meanings)})
    if report_path is not None:
        target = Path(report_path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report_path"] = str(target)
    return report
