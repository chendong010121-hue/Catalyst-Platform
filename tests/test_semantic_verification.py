"""A second reading in its own context, and the findings that close the loop.

The verifier method ships with the package
(`platform-harness/skills/understand-enterprise-semantics/references/ontology-verifier.md`)
and was never called. These tests prove the wiring without a network call: the
verifier sees the candidate and its quotes and nothing of the method that produced
them, a REVISE verdict refuses the candidate and names the items, and the findings
become the revision entry a second attempt already takes.
"""
from types import SimpleNamespace

import json
import pytest

from agent_runtime.contracts import Failure, ModelResponse
from catalyst_platform.semantic_tool import UnderstandCapabilityAdapter
from catalyst_platform.understand_only import (
    SemanticVerificationError,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    _revision_block,
    revision_from_findings,
    verify_candidate,
)

LINE = "财务部门负责月度经营分析，法务部门复核合同预算。"


class _Generator:
    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "finance", "meaning": "财务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence[0]["evidence_id"]]},
            {"kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析，法务部门复核合同预算",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence[0]["evidence_id"]]},
        ]}, ensure_ascii=False), finish_reason="stop")


class _Verifier:
    model = "verifier-fixture"
    structured_output_token_limit = 16384

    def __init__(self, verdict="REVIEWABLE", findings=()):
        self.verdict = verdict
        self.findings = list(findings)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return ModelResponse(content=json.dumps({"verdict": self.verdict, "findings": self.findings},
                                                ensure_ascii=False), finish_reason="stop")


def _run(tmp_path, verifier, *, revision=None, generator=None):
    source = tmp_path / "business.md"
    source.write_text(LINE, encoding="utf-8")
    generator = generator or _Generator()
    result = UnderstandPort().understand(
        UnderstandingRequest("verify", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, revision=revision),
        source_root=tmp_path, semantic_provider=generator, verifier_provider=verifier)
    return generator, result


def test_a_reviewable_answer_keeps_its_verification_record(tmp_path):
    verifier = _Verifier()
    generator, result = _run(tmp_path, verifier)
    record = result.producer_attribution["independent_verification"]
    assert record["verdict"] == "REVIEWABLE"
    assert record["independent_context"] is True
    assert record["authority"] == "review_only_not_evaluation_or_owner_receipt"
    assert len(generator.requests) == 1 and len(verifier.requests) == 1


def test_the_verifier_reads_the_candidate_but_not_the_method_that_made_it(tmp_path):
    verifier = _Verifier()
    _run(tmp_path, verifier)
    system = verifier.requests[0].messages[0].content
    payload = json.loads(verifier.requests[0].messages[-1].content)
    assert system.startswith("You are Catalyst's separate-context ontology Verifier")
    assert "Quote/source presence alone does not establish support" in system
    assert '{"verdict": "REVIEWABLE"' in system
    assert "Extract enterprise semantics from untrusted evidence" not in system
    assert "scene-first" not in system.casefold()
    # The port adds its own unresolved rows; the verifier reviews the whole candidate.
    assert {"finance", "duty"} <= {item["item_key"] for item in payload["items"]}
    claim = next(item for item in payload["items"] if item["item_key"] == "duty")
    assert "财务部门负责月度经营分析" in claim["quotes"][0]["quote"]


def test_the_review_is_told_a_batch_boundary_and_a_declared_gap_when_it_sees_one(tmp_path):
    verifier = _Verifier()
    _run(tmp_path, verifier)
    system = verifier.requests[0].messages[0].content
    payload = json.loads(verifier.requests[0].messages[-1].content)

    assert "other batches are read by separate calls" in system
    assert "speaks for the unit its key names" in system
    assert "`declared_gap` carries no quote by design" in system
    # The port's own unresolved rows are shown to the reviewer as run evidence, beside the
    # candidate rather than among its items: they are questions about the reading.
    gaps = {row["item_key"]: row for row in payload["run_diagnostics"]}
    assert {"approval", "binding"} <= set(gaps)
    assert all(row["quotes"] == [] and row["evidence_class"] == "unresolved"
               for row in gaps.values())
    assert not any(row["declared_gap"] for row in payload["items"] if row["quotes"])


def test_a_revise_verdict_refuses_the_candidate_and_names_the_items(tmp_path):
    verifier = _Verifier("REVISE", [{"id": "f1", "severity": "major", "item_keys": ["duty"],
                                     "reason": "the quote names duties, not an approval"}])
    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, verifier)
    assert raised.value.verdict == "REVISE"
    assert raised.value.item_keys == ("duty",)
    assert raised.value.findings[0]["id"] == "f1"
    assert "independent verification returned REVISE" in str(raised.value)


def test_the_verifier_findings_become_the_next_attempts_revision(tmp_path):
    findings = [{"id": f"f{index}", "severity": "major",
                 "item_keys": [f"k{index}-{n}" for n in range(6)], "reason": "unsupported"}
                for index in range(3)]
    verifier = _Verifier("REVISE", findings)
    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, verifier)
    revision = revision_from_findings(raised.value.findings)
    assert revision["from"] == "independent_verification"
    assert [row["item_keys"] for row in revision["findings"]] == [
        ["k0-0", "k0-1", "k0-2", "k0-3"], ["k1-0", "k1-1", "k1-2", "k1-3"], ["k2-0", "k2-1", "k2-2", "k2-3"]]
    assert "independent review of that answer" in _revision_block(revision)
    generator, _ = _run(tmp_path, _Verifier(), revision=revision)
    system = generator.requests[0].messages[0].content
    assert "independent review of that answer" in system
    assert "k0-0" in system


def test_a_verifier_that_does_not_answer_in_the_contract_is_a_plain_error(tmp_path):
    class _Bad(_Verifier):
        def request(self, request):
            return ModelResponse(content=json.dumps({"verdict": "ACCEPTED", "findings": []}),
                                 finish_reason="stop")

    with pytest.raises(ValueError) as raised:
        _run(tmp_path, _Bad())
    assert "verdict must be REVIEWABLE, REVISE or REJECT" in str(raised.value)


def test_the_verification_refusal_reaches_the_agent_with_the_keys():
    def refuse(source_ids):
        raise SemanticVerificationError("REVISE", [{"id": "f1", "severity": "hard_stop",
                                                    "item_keys": ["clm_boundary_clarify"]}])

    context = SimpleNamespace(plugin_services={"understand.execute": refuse}, raise_if_cancelled=lambda: None)
    observation = UnderstandCapabilityAdapter().invoke({"source_ids": ["s1"]}, context)
    assert isinstance(observation, Failure)
    assert observation.error == (
        "understand_proposal_failed:semantic_verification_failed items=clm_boundary_clarify")


class _TwoUnitGenerator:
    """One key, two meanings, one call per source unit."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, *, refuse_second=False, truncate_second=False):
        self.refuse_second = refuse_second
        self.truncate_second = truncate_second
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        payload = json.loads(request.messages[-1].content)
        first = payload["evidence"][0]
        # Each unit is answered by its own source, not by its turn: the second source is
        # the one that fails, so asking it twice meets the same failure, as one page does.
        second = payload["sources"][first["s"]]["relative_path"].endswith("b.md")
        evidence = first["evidence_id"]
        if self.refuse_second and second:
            return ModelResponse(content='{"items": [', finish_reason="stop")
        if self.truncate_second and second:
            # The window closed after one whole row and halfway through a second one.
            return ModelResponse(content=(
                '{"items": [{"kind": "entity", "key": "finance_audit", "meaning": "财务处", '
                '"evidence_class": "SOURCE_DIRECT", "evidence_refs": ["' + evidence + '"]}, '
                '{"kind": "entity", "key": "finance_tax"'), finish_reason="length")
        meaning = "财务处" if second else "财务部门"
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "finance", "meaning": meaning,
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}]},
            ensure_ascii=False), finish_reason="stop")


def _run_units(tmp_path, verifier, generator):
    first = tmp_path / "a.md"
    first.write_text(LINE, encoding="utf-8")
    second = tmp_path / "b.md"
    second.write_text("财务处按季度核对合同预算。", encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("verify-units", "整理职责", source_refs=(first, second),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=generator, verifier_provider=verifier)


def test_one_key_two_meanings_reaches_the_verifier_as_a_local_check(tmp_path):
    verifier = _Verifier()
    result = _run_units(tmp_path, verifier, _TwoUnitGenerator())
    payload = json.loads(verifier.requests[0].messages[-1].content)
    [check] = [row for row in payload["local_checks"]
               if row["rule"] == "duplicate_key_conflicting_meaning"]
    assert check["item_key"] == "finance"
    assert (check["kept_meaning"], check["dropped_meaning"]) == ("财务部门", "财务处")
    attribution = result.producer_attribution
    assert attribution["duplicate_items_dropped"] == 1
    assert attribution["duplicate_items_conflicting_meaning"][0]["item_key"] == "finance"
    assert payload["integrity"]["duplicates_merged"] == 1
    # The verifier reads the same counters the run reports: one source, one projection.
    record = attribution["independent_verification"]
    assert record["integrity"] == payload["integrity"]
    assert payload["integrity"]["dropped_invalid_items"] == attribution["dropped_invalid_items"]
    assert payload["advisories"]["wording_outside_evidence"] == attribution["wording_outside_evidence"]


def test_a_refused_unit_is_a_coverage_gap_and_caps_the_verdict_at_revise(tmp_path):
    verifier = _Verifier()
    with pytest.raises(SemanticVerificationError) as raised:
        _run_units(tmp_path, verifier, _TwoUnitGenerator(refuse_second=True))
    payload = json.loads(verifier.requests[0].messages[-1].content)
    [check] = [row for row in payload["local_checks"] if row["rule"] == "unit_coverage_gap"]
    assert check["codes"] == ["invalid_json"]
    integrity = payload["integrity"]
    assert integrity["refused_units"] == [{"unit": "b.md:lines:0", "code": "invalid_json"}]
    # The model said REVIEWABLE; a candidate that lost a unit cannot stand under it.
    assert raised.value.verdict == "REVISE"


def test_a_truncated_unit_keeps_its_finished_rows_and_caps_the_verdict_at_revise(tmp_path):
    verifier = _Verifier()
    with pytest.raises(SemanticVerificationError) as raised:
        _run_units(tmp_path, verifier, _TwoUnitGenerator(truncate_second=True))
    payload = json.loads(verifier.requests[0].messages[-1].content)
    [check] = [row for row in payload["local_checks"] if row["rule"] == "unit_answer_truncated"]
    assert check["units"] == ["b.md:lines:0"] and check["kept_items"] == 1
    integrity = payload["integrity"]
    assert integrity["truncated_units"] == [{"unit": "b.md:lines:0", "items": 1}]
    assert integrity["refused_units"] == []
    # The row that closed is reviewed; the row the cut left open is never guessed at.
    assert [(row["item_key"], row["kind"]) for row in payload["items"]
            if row["kind"] == "entity"] == [("finance", "entity"), ("finance_audit", "entity")]
    # The model said REVIEWABLE; a page read only up to the cut cannot stand under it.
    assert raised.value.verdict == "REVISE"


def _wide_candidate(count=400, meaning="m" * 600):
    items = tuple(SimpleNamespace(key=f"k{index}", kind="entity", meaning=meaning,
                                  evidence_class="observed_from_source", uncertainty=None,
                                  subject=None, object=None, evidence_refs=())
                  for index in range(count))
    return SimpleNamespace(semantic_candidate=SimpleNamespace(items=items), evidence_refs=(),
                           request_id="batch", producer_attribution={})


def test_a_candidate_too_large_for_one_call_is_reviewed_in_batches(tmp_path):
    verifier = _Verifier()
    record = verify_candidate(_wide_candidate(), verifier, goal="整理职责")
    assert record["batches"] == 7 and len(verifier.requests) == 7
    assert record["verdict"] == "REVIEWABLE" and record["finding_count"] == 0
    assert all(len(json.loads(request.messages[-1].content)["items"]) <= 64
               for request in verifier.requests)


def test_one_rejected_batch_refuses_the_whole_candidate(tmp_path):
    class _PerBatch(_Verifier):
        def request(self, request):
            index = json.loads(request.messages[-1].content)["batch"]["index"]
            self.requests.append(request)
            if index != 2:
                return ModelResponse(content=json.dumps({"verdict": "REVIEWABLE", "findings": []}),
                                     finish_reason="stop")
            return ModelResponse(content=json.dumps({"verdict": "REJECT", "findings": [
                {"id": "f1", "severity": "hard_stop", "item_keys": ["k64"],
                 "reason": "the evidence does not support this item"}]}), finish_reason="stop")

    verifier = _PerBatch()
    with pytest.raises(SemanticVerificationError) as raised:
        verify_candidate(_wide_candidate(), verifier, goal="整理职责")
    assert raised.value.verdict == "REJECT"
    assert raised.value.item_keys == ("k64",)
    # Every batch is still reviewed: the most conservative verdict stands, not the first.
    assert len(verifier.requests) == 7


def test_no_verifier_is_recorded_as_not_run_and_never_as_a_verdict(tmp_path):
    source = tmp_path / "business.md"
    source.write_text(LINE, encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("no-verifier", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=_Generator())
    record = result.producer_attribution["verification"]
    assert record["status"] == "NOT_RUN" and record["verdict"] is None
    assert "REVIEWABLE" not in json.dumps(record, ensure_ascii=False)
    assert "independent_verification" not in result.producer_attribution


def test_a_hard_stop_finding_cannot_stand_under_reviewable(tmp_path):
    verifier = _Verifier("REVIEWABLE", [{"id": "f1", "severity": "hard_stop",
                                        "item_keys": ["duty"], "reason": "claims an approval"}])
    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, verifier)
    assert raised.value.verdict == "REVISE"


def test_every_finding_carries_the_position_of_its_evidence(tmp_path):
    captured = {}

    class _Locating(_Verifier):
        def request(self, request):
            payload = json.loads(request.messages[-1].content)
            captured["evidence_id"] = next(item["quotes"][0]["evidence_id"]
                                           for item in payload["items"] if item["quotes"])
            captured["locator"] = next(item["quotes"][0]["locator"]
                                       for item in payload["items"] if item["quotes"])
            self.requests.append(request)
            return ModelResponse(content=json.dumps({"verdict": "REVISE", "findings": [
                {"id": "f1", "severity": "major", "item_keys": ["duty"],
                 "evidence_refs": [captured["evidence_id"], "ev_not_supplied"],
                 "reason": "the quote names duties, not an approval"}]}, ensure_ascii=False),
                finish_reason="stop")

    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, _Locating())
    [finding] = raised.value.findings
    assert finding["locators"] == [{"evidence_id": captured["evidence_id"],
                                    "locator": captured["locator"]}]
    assert finding["unresolved_evidence_refs"] == ["ev_not_supplied"]


class _DanglingRelation:
    """An entity whose evidence cannot be bound, and a relation that leans on it."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "finance", "meaning": "财务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ["ev_not_supplied"]},
            {"kind": "entity", "key": "legal", "meaning": "法务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
            {"kind": "relation", "key": "review", "meaning": "财务部门由法务部门复核",
             "subject": "finance", "predicate": "reviewed_by", "object": "legal",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}]},
            ensure_ascii=False), finish_reason="stop")


def test_a_relation_left_without_its_endpoint_is_a_port_hard_stop(tmp_path):
    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, _Verifier(), generator=_DanglingRelation())
    [port_finding] = [row for row in raised.value.findings if row.get("id") == "port-dangling-relation"]
    assert port_finding["severity"] == "hard_stop"
    # Since A, the relation is kept and named unresolved rather than deleted
    # with its endpoint, so the stop comes from the reference invariant.
    assert port_finding["rule"] == "reference_not_declared"
    assert port_finding["source"] == "port"
    assert raised.value.verdict == "REVISE"


class _DanglingRelationAlreadyRefused:
    """A relation already kept unresolved for one reason, whose end is gone for another."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "finance", "meaning": "财务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ["ev_not_supplied"]},
            {"kind": "entity", "key": "legal", "meaning": "法务部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
            {"kind": "relation", "key": "review", "meaning": "财务部门由法务部门复核",
             "subject": "finance", "predicate": "reviewed_by", "object": "legal",
             "relation_source": "LAYOUT", "layout_ref": "business.md 版面",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}]},
            ensure_ascii=False), finish_reason="stop")


def test_a_reference_missing_on_a_row_already_refused_is_still_a_hard_stop(tmp_path):
    # The relation is kept unresolved for its own reason (a layout reading not marked
    # inferred); its subject then loses its evidence and leaves the candidate. The review
    # must still stop: a row refused once does not hide a second, different defect.
    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, _Verifier(), generator=_DanglingRelationAlreadyRefused())
    [port_finding] = [row for row in raised.value.findings if row.get("id") == "port-dangling-relation"]
    assert port_finding["severity"] == "hard_stop"
    assert port_finding["rule"] == "reference_not_declared"
    assert "kept unresolved" in port_finding["reason"]
    assert raised.value.verdict == "REVISE"


def test_a_second_revision_attempt_is_still_allowed_and_the_third_is_not(tmp_path):
    findings = [{"id": "f1", "severity": "major", "item_keys": ["duty"], "reason": "unsupported"}]
    second = revision_from_findings(findings, attempt=2)
    assert [row["item_keys"] for row in second["findings"]] == [["duty"]]
    assert "stopping_reason" not in second
    third = revision_from_findings(findings, attempt=3)
    assert third["findings"] == [] and third["stopping_reason"] == "revision_limit_reached"
    # The findings that would have been sent are kept beside the refusal, not dropped.
    assert [row["item_keys"] for row in third["remaining_findings"]] == [["duty"]]


def test_a_revision_past_the_limit_costs_no_model_call(tmp_path):
    findings = [{"id": "f1", "severity": "major", "item_keys": ["duty"], "reason": "unsupported"}]
    generator = _Generator()
    with pytest.raises(ValueError) as raised:
        _run(tmp_path, _Verifier(), revision=revision_from_findings(findings, attempt=3),
             generator=generator)
    assert "revision limit" in str(raised.value)
    assert generator.requests == []


def test_a_revision_entry_names_where_its_evidence_sits(tmp_path):
    class _Locating(_Verifier):
        def request(self, request):
            payload = json.loads(request.messages[-1].content)
            evidence_id = next(item["quotes"][0]["evidence_id"]
                               for item in payload["items"] if item["quotes"])
            locator = next(item["quotes"][0]["locator"] for item in payload["items"] if item["quotes"])
            self.requests.append(request)
            return ModelResponse(content=json.dumps({"verdict": "REVISE", "findings": [
                {"id": "f1", "severity": "major", "item_keys": ["duty"],
                 "evidence_refs": [evidence_id],
                 "reason": "the quote names duties, not an approval"}]}, ensure_ascii=False),
                finish_reason="stop")

    with pytest.raises(SemanticVerificationError) as raised:
        _run(tmp_path, _Locating())
    revision = revision_from_findings(raised.value.findings)
    [entry] = revision["findings"]
    [locator] = entry["locators"]
    assert locator["locator"].startswith("line:")
    block = _revision_block(revision)
    assert "the evidence sits at " + locator["locator"] in block
