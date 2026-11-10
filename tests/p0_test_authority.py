from __future__ import annotations

import hashlib
import hmac
import json

from catalyst_platform.semantic_wiki import _candidate_content_digest


_KEYS = {
    "test-evaluator": b"p0-test-evaluator-key-do-not-use-in-products",
    "test-owner": b"p0-test-owner-key-do-not-use-in-products",
}
_ISSUED_AT = 1_760_000_000
_EXPIRES_AT = 1_900_000_000


def verify_test_receipt(receipt):
    key = _KEYS.get(receipt.get("issuer_id"))
    if key is None:
        return False
    unsigned = {name: value for name, value in receipt.items() if name != "signature"}
    expected = hmac.new(key, _canonical(unsigned), hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(receipt.get("signature", "")), expected)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _signed(fields, issuer):
    value = {**fields, "issuer_id": issuer}
    value["signature"] = hmac.new(_KEYS[issuer], _canonical(value), hashlib.sha256).hexdigest()
    return value


def semantic_receipt(wiki, candidate):
    return _signed({
        "receipt_type": "semantic_evaluation",
        "scope_id": wiki.scope_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "evaluator_id": "fixture_evaluator_v1",
        "disposition": "ACCEPT",
        "authority_class": "test_evaluator",
        "rubric_sha256": hashlib.sha256(b"fixture-rubric").hexdigest(),
        "report_sha256": hashlib.sha256(b"fixture-report").hexdigest(),
        "finding_count": 0,
        "finding_ids_sha256": hashlib.sha256(b"[]").hexdigest(),
        "issued_at": _ISSUED_AT,
        "expires_at": _EXPIRES_AT,
    }, "test-evaluator")


def owner_receipt(wiki, candidate):
    return _signed({
        "receipt_type": "owner_authority",
        "scope_id": wiki.scope_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "action": "ACCEPT",
        "decision": "ACCEPTED",
        "authority_class": "test_only",
        "issued_at": _ISSUED_AT,
        "expires_at": _EXPIRES_AT,
    }, "test-owner")


def version_receipt(wiki, version_id, candidate, *, action, expected_head):
    return _signed({
        "receipt_type": "version_authority",
        "scope_id": wiki.scope_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "version_id": version_id,
        "action": action,
        "expected_head_version_id": expected_head,
        "authority_class": "test_only",
        "issued_at": _ISSUED_AT,
        "expires_at": _EXPIRES_AT,
    }, "test-owner")


def authorize_test_operation(service, method, args, kwargs):
    values = dict(kwargs)
    state = service.wiki.semantic_state()
    if method == "decide" and values.get("decision") == "ACCEPTED":
        candidate_id = args[0] if args else values["candidate_id"]
        candidate = state["candidates"][candidate_id]
        external_id = values.get("external_evaluation_id") or candidate.get("latest_external_evaluation_id")
        if not external_id:
            receipt = semantic_receipt(service.wiki, candidate)
            recorded = service.record_external_evaluation_receipt(
                receipt=receipt, actor_origin="independent_evaluator",
            )
            external_id = recorded["evaluation_id"]
        values["external_evaluation_id"] = external_id
        values["authority_receipt"] = values.get("authority_receipt") or owner_receipt(service.wiki, candidate)
    elif method in {"activate", "rollback"}:
        version_id = args[0] if args else values["version_id"]
        version = state["accepted_versions"][version_id]
        candidate = state["candidates"][version["candidate_id"]]
        values["authority_receipt"] = values.get("authority_receipt") or version_receipt(
            service.wiki,
            version_id,
            candidate,
            action="ROLLBACK" if method == "rollback" else "ACTIVATE",
            expected_head=state.get("active_version_id"),
        )
    return values


def trusted_test_operation(workspace, wiki, run_id, method, *args, correlation_id=None, **kwargs):
    from catalyst_platform.observability import RunRecorder
    from catalyst_platform.semantic_wiki import SemanticWiki
    from catalyst_platform.trace_log import JsonlTraceStore
    import hashlib

    recorder = RunRecorder(
        JsonlTraceStore(workspace),
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        correlation_id=correlation_id,
        event_schema_version="1.5",
    )
    recorder.start(request_kind="p0_test_lifecycle", actor="test_client", component="CatalystGateway")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    authorized_kwargs = authorize_test_operation(service, method, args, kwargs)
    result = getattr(service, method)(*args, **authorized_kwargs)
    recorder.finish("success", model_calls=0)
    service.finalize_run(run_id, "success")
    return {"run_id": run_id, "result": result}
