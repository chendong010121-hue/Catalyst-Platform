"""The store is its own gate: a submission cannot decide what a reading may not decide.

An absence arrives with both halves or not at all, the places it names have to exist in
the source it is submitted against, and no submission - external or native - may carry the
fields this layer writes or a reviewer signs. An absence that is stored speaks for the
places it searched, and the reader of an accepted version is told so.
"""
from __future__ import annotations

import hashlib

import pytest

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki
from p0_test_authority import trusted_test_operation

SOURCE_LINES = [
    "# 合成质量制度",
    "质量评审负责人负责发布放行。",
    "供应商复核职责尚未确认。",
    "财务结账完成后生成月度分析。",
]


def _evidence(line: int) -> dict:
    quote = SOURCE_LINES[line - 1]
    return {"line_start": line, "line_end": line, "quote": quote,
            "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest()}


def _run(workspace, wiki, run_id, method, *args, **kwargs):
    """One closed run around one operation, the way the gateway performs it."""
    recorder = RunRecorder(
        JsonlTraceStore(workspace), run_id=run_id, request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        event_schema_version="1.5")
    recorder.start(request_kind="diagnostic_gate_test", actor="local_cli_user",
                   component="CatalystGateway")
    service = SemanticWiki(wiki, recorder=recorder)
    result = getattr(service, method)(*args, **kwargs)
    recorder.finish("success", model_calls=0)
    service.finalize_run(run_id, "success")
    return service, result


def _wiki(tmp_path, backend="json"):
    roots = tmp_path / "sources"
    roots.mkdir()
    path = roots / "quality_policy.md"
    path.write_text("\n".join(SOURCE_LINES) + "\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic",
                       project_id="diagnostic-gate", backend=backend)
    _service, staged = _run(workspace, wiki, "run_stage", "stage_source", path,
                            actor_origin="catalyst_deterministic")
    return workspace, roots, wiki, staged


def _submission(staged, items, *, version="catalyst.external_candidate.v2"):
    return {"schema_version": version, "producer_origin": "codex_external",
            "scope_id": staged["scope_id"], "source_id": staged["source_id"],
            "source_revision": staged["revision"],
            "origin_document_sha256": staged["revision"], "items": items}


def _absence_item(**overrides):
    item = {"kind": "unknown", "key": "supplier_review", "meaning": "供应商复核职责尚未确认",
            "evidence_class": "unresolved", "evidence": _evidence(3),
            "absence": "供应商复核职责", "searched": ["line:3"]}
    item.update(overrides)
    return item


def _rejection(workspace, wiki, submission, *, method="propose_external_submission_v2"):
    with pytest.raises(SemanticTransitionError) as raised:
        _run(workspace, wiki, "run_reject", method, submission)
    return raised.value.code


def test_a_submission_may_not_carry_the_layers_own_verdict(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [_absence_item(
        degradation={"class": "business_unknown", "code": "absence_scope_verified",
                     "at": "understand_semantic.row_classification"})])

    assert _rejection(workspace, wiki, submission) == "producer_may_not_author_governance_fields"


def test_a_submission_may_not_confirm_its_own_relation(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [{
        "kind": "relation", "subject": "@qa", "predicate": "approves", "object": "@gate",
        "evidence_class": "observed_from_source", "evidence": _evidence(2),
        "verification": "confirmed"}])

    assert _rejection(workspace, wiki, submission) == "producer_may_not_author_governance_fields"


def test_an_absence_without_the_places_it_searched_is_refused(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [
        {key: value for key, value in _absence_item().items() if key != "searched"}])

    assert _rejection(workspace, wiki, submission) == "unknown_without_scope"


def test_a_submission_may_not_carry_a_refusal_it_wrote_itself(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [_absence_item(
        uncertainty="degraded:scope_ref_not_supplied:kind=unknown")])

    assert _rejection(workspace, wiki, submission) == "producer_may_not_author_governance_fields"


def test_an_absence_naming_a_place_the_source_has_not_is_refused(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [_absence_item(searched=["line:99"])])

    assert _rejection(workspace, wiki, submission) == "unknown_scope_not_in_source"


def test_a_word_in_the_source_is_not_a_place_an_absence_searched(tmp_path):
    """A place is a locator the source can resolve, never a word that happens to occur in it."""
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [_absence_item(searched=["供应商"])])

    assert _rejection(workspace, wiki, submission) == "unknown_scope_not_a_locator"


def test_the_native_adapter_cannot_call_a_word_a_place_either(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    native = {**_submission(staged, [_absence_item(evidence_class="inferred",
                                                   searched=["供应商"])],
                            version="catalyst.native_projection.v1"),
              "producer_origin": "catalyst_model"}

    with pytest.raises(SemanticTransitionError) as raised:
        _run(workspace, wiki, "run_native_word", "_propose_native_projection", native)
    assert raised.value.code == "unknown_scope_not_a_locator"


def test_the_old_bridge_cannot_carry_an_absence_at_all(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [{
        "kind": "unknown", "key": "supplier_review", "meaning": "供应商复核职责尚未确认",
        "evidence_class": "unresolved", "evidence": _evidence(3)}],
        version="catalyst.external_candidate.v1")

    assert _rejection(workspace, wiki, submission,
                     method="propose_external_submission") == "unknown_without_scope"


def test_the_native_adapter_is_held_to_the_same_field_contract(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    native = {**_submission(staged, [_absence_item(
        evidence_class="inferred",
        degradation={"class": "run_diagnostic", "code": "absence_without_scope",
                     "at": "understand_semantic.row_classification"})],
        version="catalyst.native_projection.v1"),
        "producer_origin": "catalyst_model"}

    with pytest.raises(SemanticTransitionError) as raised:
        _run(workspace, wiki, "run_native", "_propose_native_projection", native)
    assert raised.value.code == "producer_may_not_author_governance_fields"


def test_the_native_adapter_keeps_the_verification_the_layer_computed(tmp_path):
    """`verification` is filled by the execution layer, so the native hand-over may carry it."""
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    native = {**_submission(staged, [{
        "kind": "relation", "subject": "@qa", "predicate": "approves", "object": "@gate",
        "evidence_class": "inferred", "evidence": _evidence(2),
        "verification": "confirmed"}], version="catalyst.native_projection.v1"),
        "producer_origin": "catalyst_model"}

    _service, proposed = _run(workspace, wiki, "run_native_ok",
                             "_propose_native_projection", native)

    assert proposed["status"] == "proposed"
    entry = wiki.semantic_state()["candidates"][proposed["candidate_id"]]["entries"][0]
    assert entry["verification"] == "confirmed"


# --- the limit a row was read under travels with the row ---------------------


def test_a_typed_entry_keeps_the_limit_the_absence_was_read_under():
    """A consumer of the typed row reads its limit there, not out of the raw quote."""
    from catalyst_platform.understand_wiki import UnderstandWikiAdapter

    item = {"item_id": "item_a", "kind": "unknown", "key": "supplier_review",
            "meaning": "供应商复核职责尚未确认", "evidence_class": "unresolved",
            "evidence_refs": ["ev_a"], "scope_refs": ["ev_a"],
            "observed_absence": "供应商复核职责", "unread_scopes": ["line:3"]}
    refs = {"ev_a": {"evidence_id": "ev_a", "locator": "line:3", "source_id": "source_a",
                     "quote": "供应商复核职责尚未确认。"}}

    entries, _report = UnderstandWikiAdapter.harvest_entries(
        None, {"item_a": item}, refs, ["item_a"], lines=[], strict=True)

    assert entries[0]["searched"] == ["line:3"]
    assert entries[0]["unread_scopes"] == ["line:3"]


def test_the_native_hand_over_may_carry_the_limit_the_layer_computed(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    native = {**_submission(staged, [_absence_item(evidence_class="inferred",
                                                   unread_scopes=["line:3"])],
                            version="catalyst.native_projection.v1"),
              "producer_origin": "catalyst_model"}

    _service, proposed = _run(workspace, wiki, "run_native_limit",
                              "_propose_native_projection", native)

    entry = wiki.semantic_state()["candidates"][proposed["candidate_id"]]["entries"][0]
    assert entry["unread_scopes"] == ["line:3"]


def test_an_external_submission_may_not_write_the_limit_itself(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [_absence_item(unread_scopes=["line:3"])])

    assert _rejection(workspace, wiki, submission) == "producer_may_not_author_governance_fields"


# --- what a reader of an accepted absence is told ----------------------------


def test_an_accepted_absence_is_read_for_the_places_it_searched(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _service, proposed = _run(workspace, wiki, "run_propose", "propose_external_submission_v2",
                              _submission(staged, [
                                  _absence_item(),
                                  {"kind": "claim", "key": "release_duty",
                                   "meaning": "质量评审负责人负责发布放行",
                                   "evidence_class": "observed_from_source",
                                   "evidence": _evidence(2)}]))
    _service, evaluation = _run(workspace, wiki, "run_evaluate", "evaluate",
                                proposed["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "pass", evaluation
    decision = trusted_test_operation(
        workspace, wiki, "run_decide", "decide", proposed["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance",
        reason_code="synthetic-manager-review")
    trusted_test_operation(
        workspace, wiki, "run_activate", "activate", decision["result"]["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=None)

    read = wiki.read_knowledge("供应商 质量评审", mode="accepted_enterprise_semantics",
                               include_all_active=True, limit=100)

    assert read["restricted_meaning_count"] == 1
    absence = next(row for row in read["meanings"] if row["kind"] == "unknown")
    assert absence["restriction"] == {"kind": "absence", "reads_as": "searched_scope_only",
                                     "absence": "供应商复核职责", "searched": ["line:3"]}
    claim = next(row for row in read["meanings"] if row["kind"] == "claim")
    assert "restriction" not in claim


def _native_proposal(workspace, wiki, staged, run_id):
    native = {**_submission(staged, [
        _absence_item(evidence_class="inferred", unread_scopes=["line:3"]),
        {"kind": "claim", "key": "release_duty", "meaning": "质量评审负责人负责发布放行",
         "evidence_class": "inferred", "evidence": _evidence(2)}],
        version="catalyst.native_projection.v1"),
        "producer_origin": "catalyst_model"}
    _service, proposed = _run(workspace, wiki, run_id, "_propose_native_projection", native)
    return proposed


def test_a_reader_of_an_accepted_absence_is_told_the_limit_it_was_read_under(tmp_path):
    """A row read over a part of its source says so on the row a consumer receives."""
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    proposed = _native_proposal(workspace, wiki, staged, "run_native_limit_read")
    _service, evaluation = _run(workspace, wiki, "run_native_evaluate", "evaluate",
                                proposed["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "pass", evaluation
    decision = trusted_test_operation(
        workspace, wiki, "run_native_decide", "decide", proposed["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance",
        reason_code="synthetic-manager-review")
    trusted_test_operation(
        workspace, wiki, "run_native_activate", "activate", decision["result"]["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=None)

    read = wiki.read_knowledge("供应商 质量评审", mode="accepted_enterprise_semantics",
                               include_all_active=True, limit=100)

    absence = next(row for row in read["meanings"] if row["kind"] == "unknown")
    assert absence["restriction"]["searched"] == ["line:3"]
    assert absence["restriction"]["unread_scopes"] == ["line:3"]
