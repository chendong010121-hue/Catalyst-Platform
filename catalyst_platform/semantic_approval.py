"""The two signed receipts and the two transitions that turn a candidate into a live version.

A person runs this from the CLI: the reviewer's report is hashed into a reviewer receipt,
the owner's acceptance is a second receipt, and the store checks both before it records
anything. Nothing here fabricates a verdict — the report file is what was actually
reviewed, and a disposition other than ACCEPT stops the chain at the decision.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .semantic_keys import load_key, sign
from .semantic_wiki import SemanticTransitionError, _candidate_content_digest

RUBRIC = "name-in-evidence; meaning-restates-source; evidence-is-enough"


def _secret(workspace, role: str) -> bytes:
    secret = load_key(workspace, role)
    if secret is None:
        raise SemanticTransitionError(
            f"{role}_key_missing",
            f"no {role} key in {workspace}; run `catalyst ontology key init --workspace ...` first")
    return secret


def review_receipt(workspace, candidate, *, disposition: str, report_sha256: str,
                   finding_ids: tuple = (), evaluator_id: str = "local-reviewer",
                   ttl_seconds: int = 86400, package_sha256: str | None = None,
                   evaluator_context: str | None = None) -> dict:
    now = int(time.time())
    fields = {
        "receipt_type": "semantic_evaluation",
        "scope_id": candidate["scope_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "evaluator_id": evaluator_id,
        "disposition": disposition,
        "authority_class": "independent_evaluator",
        "rubric_sha256": hashlib.sha256(RUBRIC.encode("utf-8")).hexdigest(),
        "report_sha256": report_sha256,
        "finding_count": len(finding_ids),
        "finding_ids_sha256": hashlib.sha256(
            json.dumps(sorted(finding_ids), ensure_ascii=False).encode("utf-8")).hexdigest(),
        "issued_at": now,
        "expires_at": now + ttl_seconds,
    }
    # A review that came back from elsewhere binds the exact package it read.
    if package_sha256 is not None:
        fields["review_package_sha256"] = package_sha256
    if evaluator_context is not None:
        fields["evaluator_context"] = evaluator_context
    return sign(fields, role="reviewer", secret=_secret(workspace, "reviewer"))


def owner_receipt(workspace, candidate, *, action: str, decision: str,
                  ttl_seconds: int = 86400) -> dict:
    now = int(time.time())
    return sign({
        "receipt_type": "owner_authority",
        "scope_id": candidate["scope_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "action": action,
        "decision": decision,
        "authority_class": "organization_owner",
        "issued_at": now,
        "expires_at": now + ttl_seconds,
    }, role="owner", secret=_secret(workspace, "owner"))


def version_receipt(workspace, version_id: str, candidate, *, action: str,
                    expected_head, ttl_seconds: int = 86400) -> dict:
    now = int(time.time())
    return sign({
        "receipt_type": "version_authority",
        "scope_id": candidate["scope_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "version_id": version_id,
        "action": action,
        "expected_head_version_id": expected_head,
        "authority_class": "organization_owner",
        "issued_at": now,
        "expires_at": now + ttl_seconds,
    }, role="owner", secret=_secret(workspace, "owner"))


def approve(semantic, candidate_id: str, *, reviewer_report, disposition: str = "ACCEPT",
            reason_code: str = "independent_review_passed", finding_ids: tuple = (),
            evaluator_id: str = "local-reviewer") -> dict:
    """Record the review receipt the report stands for, then let the owner accept.

    The report file is hashed as it is: the receipt binds what was reviewed, not a claim
    about it. A disposition other than ACCEPT is recorded and the decision is refused,
    which is the chain saying no.
    """
    report = Path(reviewer_report)
    if not report.is_file():
        raise SemanticTransitionError("reviewer_report_missing",
                                      f"review report {str(report)!r} does not exist")
    workspace = semantic.wiki.workspace
    candidate = semantic.wiki.semantic_state()["candidates"][candidate_id]
    receipt = review_receipt(workspace, candidate, disposition=disposition,
                             report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                             finding_ids=tuple(finding_ids), evaluator_id=evaluator_id)
    recorded = semantic.record_external_evaluation_receipt(
        receipt=receipt, actor_origin="independent_evaluator")
    if disposition != "ACCEPT":
        return {"status": "refused", "disposition": disposition,
                "evaluation_id": recorded["evaluation_id"],
                "reason": "external_semantic_evaluation_not_accept"}
    return semantic.decide(
        candidate_id, decision="ACCEPTED", actor_origin="manager_acceptance",
        reason_code=reason_code, external_evaluation_id=recorded["evaluation_id"],
        authority_receipt=owner_receipt(workspace, candidate, action="ACCEPT", decision="ACCEPTED"))


def approve_external(semantic, candidate_id: str, *, package_dir, response_path,
                     evaluator_id: str = "external-reviewer",
                     evaluator_context: str = "external_model",
                     accept: bool = True) -> dict:
    """Record the answer an outside reviewer gave over a sealed package, then let the owner decide.

    The package is re-read and re-hashed, and the answer is hashed as it arrived: the receipt
    covers both, so a claim about a review can be checked against the bytes that were sent and
    the bytes that came back. The signature is local custody — a chat model cannot hold a key —
    so the receipt names the evaluator instead of proving who wrote the answer.
    """
    from . import external_review

    package = external_review.load_package(package_dir)
    response, response_sha256 = external_review.read_response(response_path)
    workspace = semantic.wiki.workspace
    candidate = semantic.wiki.semantic_state()["candidates"][candidate_id]
    if package.get("scope_id") != semantic.wiki.scope_id:
        raise SemanticTransitionError("review_package_scope_mismatch",
                                      "the review package belongs to another Wiki scope")
    if package.get("candidate_id") != candidate_id or package.get("candidate_sha256") != _candidate_content_digest(candidate):
        raise SemanticTransitionError("review_package_binding_mismatch",
                                      "the review package does not bind this candidate")
    if package.get("source_revision") != candidate["source_revision"]:
        raise SemanticTransitionError("source_revision_changed",
                                      "the package was written against another source revision")
    disposition = external_review.VERDICTS[response["verdict"]]
    finding_ids = tuple(str(row.get("id")) for row in response.get("findings", []))
    receipt = review_receipt(workspace, candidate, disposition=disposition,
                             report_sha256=response_sha256, finding_ids=finding_ids,
                             evaluator_id=evaluator_id,
                             package_sha256=package["package_sha256"],
                             evaluator_context=evaluator_context)
    recorded = semantic.record_external_evaluation_receipt(
        receipt=receipt, actor_origin="independent_evaluator")
    if disposition != "ACCEPT" or not accept:
        return {"status": "refused" if disposition != "ACCEPT" else "recorded",
                "disposition": disposition, "verdict": response["verdict"],
                "evaluation_id": recorded["evaluation_id"],
                "reason": "external_semantic_evaluation_not_accept"}
    return semantic.decide(
        candidate_id, decision="ACCEPTED", actor_origin="manager_acceptance",
        reason_code="external_review_passed", external_evaluation_id=recorded["evaluation_id"],
        authority_receipt=owner_receipt(workspace, candidate, action="ACCEPT", decision="ACCEPTED"))


def activate(semantic, version_id: str, *, expected_head) -> dict:
    workspace = semantic.wiki.workspace
    state = semantic.wiki.semantic_state()
    if version_id not in state["accepted_versions"]:
        raise SemanticTransitionError("accepted_version_not_found",
                                      "activation target is not an accepted semantic version")
    candidate = state["candidates"][state["accepted_versions"][version_id]["candidate_id"]]
    return semantic.activate(
        version_id, actor_origin="manager_acceptance",
        authority_receipt=version_receipt(workspace, version_id, candidate,
                                          action="ACTIVATE", expected_head=expected_head),
        expected_head_version_id=expected_head)


def rollback(semantic, version_id: str, *, expected_head) -> dict:
    workspace = semantic.wiki.workspace
    state = semantic.wiki.semantic_state()
    if version_id not in state["accepted_versions"]:
        raise SemanticTransitionError("accepted_version_not_found",
                                      "rollback target is not an accepted semantic version")
    candidate = state["candidates"][state["accepted_versions"][version_id]["candidate_id"]]
    return semantic.rollback(
        version_id, actor_origin="manager_acceptance",
        authority_receipt=version_receipt(workspace, version_id, candidate,
                                          action="ROLLBACK", expected_head=expected_head),
        expected_head_version_id=expected_head)
