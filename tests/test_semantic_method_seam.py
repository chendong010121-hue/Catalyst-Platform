"""One registered semantic method, one lease, one entry point, one record.

The product could admit a data-only method and freeze it for a run, and it could read a
Skill directory into a candidate. These cases cover the step between them: what the lease
holds is what the run reads, a repair is off unless it is named and scoped, a repaired
answer still goes through the typed validator, and a failed run leaves no method pinned.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from types import SimpleNamespace
from pathlib import Path

import pytest

from agent_runtime.contracts import Message, ModelRequest, ModelResponse

from catalyst_platform.components import ComponentError
from catalyst_platform.semantic_method import (
    SEMANTIC_COMPONENT,
    SEMANTIC_INTERFACE,
    SEMANTIC_SERVICES,
    SEMANTIC_SKILL,
    RecordedResponseProvider,
    SemanticMethodError,
    dispositions,
    producer_items,
    repair_spec,
    run_semantic_method,
)
from catalyst_platform.understand_only import UnderstandIntent, UnderstandingRequest
from catalyst_platform.understand_wiki import admission_plan
from catalyst_platform.workbench import CatalystWorkbench

MARKER = "SEAM-MARKER-4f1a"


def package(root, version="0.1.0", *, body=None, component_id=SEMANTIC_COMPONENT,
            skill=SEMANTIC_SKILL, provides=None, license_name="Catalyst"):
    """One method package: a Skill file, and the manifest that pins it."""
    root.mkdir(parents=True)
    text = body if body is not None else (
        f"---\nname: {skill}\nversion: {version}\ndescription: seam fixture\n---\n\n{MARKER}\n")
    (root / "SKILL.md").write_text(text, encoding="utf-8")
    manifest = {
        "manifest_version": 1, "component_id": component_id, "resource_type": "method_data",
        "version": version, "skill_name": skill,
        "required_product_interface": SEMANTIC_INTERFACE,
        "provides": list(provides or ["enterprise-ontology"]),
        "requires": sorted(SEMANTIC_SERVICES),
        "files": {"SKILL.md": hashlib.sha256((root / "SKILL.md").read_bytes()).hexdigest()},
        "license_sources": [{"name": license_name, "revision": "seam-fixture",
                             "license": "original", "adaptation": "seam fixture"}],
        "evaluation_refs": ["seam-fixture"], "llm_visibility": "explicit",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def admit(methods, source, *, version="0.1.0", activate=True):
    receipt = methods.discover(source)
    methods.admit(source, receipt["package_sha256"])
    if activate:
        methods.activate(SEMANTIC_COMPONENT, version)
    return receipt


def request_for(root, text="复核负责人负责单据复核。"):
    source = root / "org.md"
    source.write_text(text, encoding="utf-8")
    return UnderstandingRequest("seam-run", "整理组织", source_refs=(source,),
                                intent=UnderstandIntent.KNOWLEDGE_PROPOSE)


class _OneEntity:
    """One source, one entity, and an evidence id taken from the request it was given."""

    model = "seam-fixture"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "review_lead", "meaning": "复核负责人",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}]},
            ensure_ascii=False), finish_reason="stop")


class _Explodes:
    model = "seam-fixture"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        raise RuntimeError("the model call did not answer")


class _NoLease:
    """A store that fails the moment a lease is asked for."""

    def acquire_method(self, component_id):
        raise AssertionError(f"a refused run must not hold {component_id}")


def items_of(result):
    return [dict(row) for row in ((result.to_dict().get("semantic_candidate") or {}).get("items") or [])]


def _type_as_position(result):
    """The repair these cases name: one field stated, nothing added to or taken from the card."""
    rows = producer_items(result)
    for row in rows:
        if row.get("kind") == "entity":
            row["business_type"] = "Position"
    return rows


def _unstated_row(result):
    """A repaired row with a key and no statement: the typed validator refuses it."""
    rows = producer_items(result)
    rows[0].pop("meaning", None)
    return rows


def _unreadable_class(result):
    """A repaired row whose evidence class the contract never defined."""
    rows = producer_items(result)
    rows[0]["evidence_class"] = "MODEL_GUESS"
    return rows


def test_the_semantic_contract_is_admitted_and_another_contract_is_not(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    with methods.acquire_method(SEMANTIC_COMPONENT) as frozen:
        assert frozen["manifest"]["required_product_interface"] == "semantic-proposal.v1"
        assert frozen["manifest"]["requires"] == ("semantic_submit_candidate",)
    with pytest.raises(ComponentError, match="unknown Skill contract"):
        methods.discover(package(tmp_path / "elsewhere", provides=["other"]))
    assert [row["component_id"] for row in methods.list_components()] == [SEMANTIC_COMPONENT]


def test_a_run_reads_the_method_the_lease_holds(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    provider = _OneEntity()
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=provider, extraction_mode="single_stage", label="card-a")
    # The marker exists only in the frozen package, so its presence in the system prompt
    # is the run reading the lease rather than the product's own copy of this Skill.
    assert MARKER in provider.requests[0].messages[0].content
    assert run.identity["method"]["component_id"] == SEMANTIC_COMPONENT
    assert run.identity["method"]["version"] == "0.1.0"
    assert run.identity["method"]["skill_name"] == SEMANTIC_SKILL
    assert run.identity["extraction_mode"] == "single_stage"
    assert run.identity["label"] == "card-a"
    # The three built-in mechanical Skills the Port loads beside the method are product
    # text, so the record names them by digest instead of pretending the lease pinned them.
    builtin = run.identity["builtin_skills"]["files"]
    assert "_methods/understand-source-inventory.md" in builtin
    # The package's own Skill folder is the package's, whole: nothing of the product copy
    # of the same Skill survives beside it.
    assert not any(name.startswith(f"{SEMANTIC_SKILL}/") for name in builtin)
    assert run.lease["released"] is True


def test_a_run_without_a_named_repair_keeps_the_model_answer(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneEntity(), extraction_mode="single_stage", label="card-a")
    assert run.result is run.original
    assert run.diff == ()
    assert run.validation["ran"] is False
    assert run.identity["repairs"] == {"enabled": False, "reason": "no repair was named for this run"}
    assert items_of(run.result)


def test_a_named_repair_is_scoped_recorded_and_revalidated(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="type-as-position", version="1.0.0",
                       implementation=f"{__name__}:_type_as_position", scope={"labels": ["card-a"]})
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneEntity(), extraction_mode="single_stage",
                              label="card-a", repairs=spec)
    repairs = run.identity["repairs"]
    assert repairs["enabled"] is True
    assert (repairs["name"], repairs["version"]) == ("type-as-position", "1.0.0")
    assert repairs["implementation"] == f"{__name__}:_type_as_position"
    assert repairs["sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert repairs["scope"] == {"labels": ["card-a"]}
    # The repaired rows went back through the typed validator, not around it.
    assert run.validation["ran"] is True
    assert run.validation["validator"] == "UnderstandPort.attach_producer_items"
    assert run.validation["items_submitted"] == run.validation["items_accepted"]
    assert [change["change"] for change in run.diff] == ["changed"]
    assert run.diff[0]["fields"]["business_type"] == {"before": None, "after": "Position"}
    # The original is kept as it was: a repair is a second form, not a rewrite in place.
    assert run.original.to_dict() != run.result.to_dict()
    assert all(row.get("business_type") is None for row in items_of(run.original)
               if row.get("kind") == "entity")
    # The three forms and the verdict travel together in one record.
    record = run.record()
    assert set(record) == {"identity", "original", "result", "diff", "validation",
                           "disposition", "record_files", "lease"}
    assert record["original"]["digest"] != record["result"]["digest"]
    assert record["validation"]["ran"] is True
    assert record["lease"]["released"] is True
    assert record["diff"][0]["fields"]["business_type"]["after"] == "Position"
    # The card holds the statement. The port's standing absences about approval and
    # binding are run evidence: they are questions about the reading, not about the
    # organisation, so they are counted beside the card and never inside it.
    assert set(record["result"]["kinds"]) == {"entity"}
    assert [row["key"] for row in run.result.run_diagnostics] == ["approval", "binding"]


def test_a_run_must_name_the_extraction_mode_it_used(tmp_path):
    """The mode is chosen by the caller and recorded, never inherited from a recording."""
    with pytest.raises(SemanticMethodError, match="extraction_mode_unsupported"):
        run_semantic_method(_NoLease(), request_for(tmp_path), source_root=tmp_path,
                            provider=_OneEntity(), extraction_mode="as recorded", label="card-a")


def test_a_repair_outside_its_scope_is_refused_before_the_lease(tmp_path):
    spec = repair_spec(name="type-as-position", version="1.0.0",
                       implementation=f"{__name__}:_type_as_position", scope={"labels": ["card-a"]})
    with pytest.raises(SemanticMethodError, match="repair_out_of_scope"):
        run_semantic_method(_NoLease(), request_for(tmp_path), source_root=tmp_path,
                            provider=_OneEntity(), extraction_mode="single_stage",
                            label="card-b", repairs=spec)


def test_a_repair_that_names_no_implementation_is_refused(tmp_path):
    with pytest.raises(SemanticMethodError, match="repair_implementation_missing"):
        repair_spec(name="absent", version="1.0.0",
                    implementation=f"{__name__}:_nothing_here", scope={"labels": ["card-a"]})
    with pytest.raises(SemanticMethodError, match="repair_without_scope"):
        repair_spec(name="unscoped", version="1.0.0",
                    implementation=f"{__name__}:_type_as_position", scope={})


def test_a_repaired_row_the_validator_cannot_read_is_refused(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="unstated", version="1.0.0",
                       implementation=f"{__name__}:_unstated_row", scope={"labels": ["card-a"]})
    with pytest.raises(ValueError, match="kind, key, and meaning are required"):
        run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                            provider=_OneEntity(), extraction_mode="single_stage",
                            label="card-a", repairs=spec)
    # Refused inside the validator, so the method must be free again.
    assert methods.activate(SEMANTIC_COMPONENT, "0.1.0")["transition"] == "no-op"


def test_a_repaired_row_the_validator_reclassifies_is_recorded(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="unreadable-class", version="1.0.0",
                       implementation=f"{__name__}:_unreadable_class", scope={"labels": ["card-a"]})
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneEntity(), extraction_mode="single_stage",
                              label="card-a", repairs=spec)
    # The validator, not the repair, decided what the row is: a class it cannot read is a
    # row the run could not establish, so it leaves the candidate and is kept as evidence.
    assert producer_items(run.result) == []
    diagnostic = {row["key"]: row for row in run.result.run_diagnostics}["review_lead"]
    assert diagnostic["reason"] == "evidence_class_unsupported"
    assert diagnostic["destination"] == "run_evidence"
    changed = {(change["change"], change["kind"]) for change in run.diff if change["key"] == "review_lead"}
    assert changed == {("removed", "entity")}
    assert run.identity["repairs"]["enabled"] is True


def test_a_failed_run_releases_the_method(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    admit(methods, package(tmp_path / "next", "0.1.1"), activate=False)
    with pytest.raises(RuntimeError, match="did not answer"):
        run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                            provider=_Explodes(), extraction_mode="single_stage", label="card-a")
    # An unreleased lease would answer `method_update_busy` here.
    assert methods.activate(SEMANTIC_COMPONENT, "0.1.1")["transition"] == "replaced"
    with methods.acquire_method(SEMANTIC_COMPONENT) as frozen:
        assert frozen["version"] == "0.1.1"


def test_a_recorded_answer_is_replayed_and_anything_else_is_refused(tmp_path):
    capture = tmp_path / "capture"
    (capture / "calls").mkdir(parents=True)
    asked = ModelRequest(messages=(Message(role="system", content="method"),
                                   Message(role="user", content="evidence")),
                         parameters={"max_tokens": 8192, "response_format": {"type": "json_object"}})
    (capture / "calls" / "001_request.json").write_text(
        json.dumps(asdict(asked), ensure_ascii=False), encoding="utf-8")
    (capture / "calls" / "001_response.json").write_text(json.dumps(
        {"content": '{"items":[]}', "tool_calls": [], "finish_reason": "stop"}), encoding="utf-8")
    provider = RecordedResponseProvider(capture)
    assert provider.mode == "recorded"
    assert provider.request(asked).content == '{"items":[]}'
    assert provider.answered == [1]
    with pytest.raises(SemanticMethodError, match="replay_request_not_recorded"):
        provider.request(replace(asked, parameters={"max_tokens": 4096}))
    assert provider.missed and provider.request_count == 2


class _Stored:
    """A result as the ledger reads it: its rows, the evidence they may cite, and the rules."""

    def __init__(self, rows, evidence=(), attribution=None):
        self._rows = [dict(row) for row in rows]
        self.evidence_refs = tuple(evidence)
        self.producer_attribution = dict(attribution or {})

    def to_dict(self):
        return {"semantic_candidate": {"items": list(self._rows)}}


def _ref(evidence_id):
    return SimpleNamespace(evidence_id=evidence_id)


def _mixed_ledger(result):
    """Five rows over the one-source fixture: one kept, one field refused, one degraded,
    one folded into its twin, one kept. Between them they are the four outcomes."""
    rows = producer_items(result)
    entity = dict(rows[0])
    cited = list(entity["evidence_refs"])
    claim = {"kind": "claim", "key": "review_scope", "meaning": "复核范围限于单据",
             "evidence_class": "observed_from_source", "evidence_refs": cited,
             "scope_state": "current"}
    nowhere = {"kind": "claim", "key": "approval_authority", "meaning": "审批权限在财务部",
               "evidence_class": "observed_from_source", "evidence_refs": ["ev_never_issued"]}
    merged = {"kind": "entity", "key": "dan_ju", "meaning": "单据",
              "evidence_class": "observed_from_source", "evidence_refs": cited}
    survivor = {"kind": "entity", "key": "danju", "meaning": "单据",
                "evidence_class": "observed_from_source", "evidence_refs": cited}
    return [entity, claim, nowhere, merged, survivor]


def _ledger_run(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="mixed-ledger", version="1.0.0",
                       implementation=f"{__name__}:_mixed_ledger", scope={"labels": ["card-a"]})
    target = tmp_path / "disposition.json"
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneEntity(), extraction_mode="single_stage",
                              label="card-a", repairs=spec, disposition_path=target)
    ledger = json.loads(Path(run.disposition["path"]).read_text(encoding="utf-8"))
    return run, ledger, target


def test_a_run_writes_what_became_of_every_row_it_submitted(tmp_path):
    run, ledger, target = _ledger_run(tmp_path)
    counts = ledger["counts"]
    assert run.disposition["written"] is True
    assert Path(run.disposition["path"]) == target
    assert run.disposition["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert run.record()["disposition"]["sha256"] == run.disposition["sha256"]
    assert counts == run.disposition["counts"]
    assert counts["submitted"] == 5
    # The header names what the ledger's verdicts are about, or a `kept` row reads as
    # "nothing changed anywhere" rather than "this submitted row survived unchanged".
    baseline = ledger["header"]["compared_with"]["baseline"]
    assert "submitted row" in baseline and "unchanged" in baseline
    # Every submitted row is in exactly one bucket: the ledger is complete or it is wrong.
    # A row the run could not establish is its own bucket, not a drop.
    assert sum(counts[name] for name in ("kept", "changed", "degraded", "dropped",
                                         "run_diagnostic")) == 5
    assert (counts["kept"], counts["changed"], counts["degraded"], counts["dropped"],
            counts["run_diagnostic"]) == (2, 1, 0, 1, 1)
    assert counts["moved_to_run_evidence"] == 1
    assert counts["unrecorded"] == 0
    by_key = {row["key"]: row for row in ledger["rows"]}
    assert {key: row["outcome"] for key, row in by_key.items()} == {
        "review_lead": "kept", "review_scope": "changed", "approval_authority": "run_diagnostic",
        "dan_ju": "dropped", "danju": "kept"}
    # A field the contract would not carry says which rule took it, and what it looked like.
    changed = by_key["review_scope"]
    assert changed["reason"] == "scope_state_not_applicable"
    assert changed["fields"]["scope_state"] == {"before": "current", "after": None}
    # A row folded into its twin names the row that kept the name.
    dropped = by_key["dan_ju"]
    assert dropped["reason"] == "merged_duplicate_entity"
    assert dropped["source"] == "producer_attribution.merged_duplicate_entities"
    assert dropped["reasons"][0]["merged_into"] == "danju"
    assert dropped["item_id"] is None
    # The ledger is the run's own: what it says the repair submitted is what the run holds.
    assert ledger["header"]["request_id"] == "seam-run"
    assert ledger["header"]["validator"] == "UnderstandPort.attach_producer_items"
    assert ledger["header"]["method"]["component_id"] == SEMANTIC_COMPONENT
    assert ledger["header"]["repairs"]["name"] == "mixed-ledger"


def test_a_row_nothing_accounted_for_is_recorded_as_unnamed():
    stored = [{"item_id": "item_other", "kind": "unknown", "key": "other", "meaning": "别的",
               "evidence_refs": [], "evidence_class": "unresolved", "uncertainty": "x"}]
    rows, counts = dispositions(
        [{"kind": "claim", "key": "gone", "meaning": "消失的行",
          "evidence_class": "observed_from_source", "evidence_refs": ["ev_1", "ev_2"]}],
        _Stored(stored, evidence=[_ref("ev_1")]))
    assert rows[0]["outcome"] == "dropped"
    assert rows[0]["reason"] == "not recorded by the validator"
    assert rows[0]["source"] == "unrecorded"
    # The citation the row brought and the evidence never held is named, not hidden.
    assert rows[0]["evidence"]["not_in_evidence"] == ["ev_2"]
    assert rows[0]["evidence"]["submitted"] == ["ev_1", "ev_2"]
    assert counts["dropped"] == 1 and counts["unrecorded"] == 1


def test_a_row_degraded_for_a_citation_it_never_received_keeps_no_citation_it_cannot_show(tmp_path):
    run, ledger, _ = _ledger_run(tmp_path)
    row = {item["key"]: item for item in ledger["rows"]}["approval_authority"]
    # The row is not a drop and not a kept statement: it went to run evidence, and the
    # ledger says so with the rule that sent it there.
    assert row["outcome"] == "run_diagnostic"
    assert row["reason"] == "evidence_ref_not_supplied"
    assert row["diagnostic_class"] == "run_diagnostic"
    assert row["destination"] == "run_evidence"
    assert row["evidence"]["not_in_evidence"] == ["ev_never_issued"]
    # The run still holds the row whole, and it claims no citation it cannot show.
    stored = {item["key"]: item for item in run.result.run_diagnostics}["approval_authority"]
    assert (stored["kind"], stored["evidence_class"]) == ("unknown", "unresolved")
    assert stored["uncertainty"] == "degraded:evidence_ref_not_supplied:kind=claim"
    known = {ref["evidence_id"] for ref in run.result.to_dict()["evidence_refs"]}
    assert set(stored["evidence_refs"]) <= known
    assert not stored["evidence_refs"]
    # What the plan does with it now: nothing. The row is not a candidate, so no admission
    # path can adopt it and no handoff script has to filter it out afterwards.
    plan = admission_plan(run.result)
    assert stored["item_id"] not in {item["item_id"] for item in plan["default_adopt"]}
    assert [row for row in plan["default_adopt"]
            if str(row.get("uncertainty") or "").startswith("degraded:")] == []


def test_a_run_without_a_repair_writes_no_ledger(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    target = tmp_path / "disposition.json"
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneEntity(), extraction_mode="single_stage",
                              label="card-a", disposition_path=target)
    # Nothing submitted these rows separately, so there is nothing to compare them against.
    assert run.disposition["written"] is False
    assert "not retained" in run.disposition["reason"]
    assert not target.exists()


# ---------------------------------------------------------------- the whole record, kept whole


class _RowsPerUnit:
    """A reading of a long source: one answer per unit, many rows each.

    Two units make the model's own answer a merged candidate, which the product accepts at its
    merged ceilings. That is the shape a repair has to survive: the rows it hands back are rows
    the reading already carried, and the per-answer ceiling is narrower than that.
    """

    model = "seam-fixture"
    structured_output_token_limit = 65536
    model_output_token_limit = 65536

    def __init__(self, per_unit: int = 70):
        self.per_unit = per_unit
        self.requests = 0

    def request(self, request):
        self.requests += 1
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        unit = self.requests
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "claim", "key": f"claim_{unit}_{index}", "meaning": f"第 {unit} 段的第 {index} 条",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}
            for index in range(self.per_unit)]}, ensure_ascii=False), finish_reason="stop")


def _long_source(root):
    """Enough paragraphs that the Port splits the source into more than one unit."""
    lines = [f"第 {index} 段：这一段说明一件事，并给出它的依据。" for index in range(0, 40)]
    source = root / "long.md"
    source.write_text("\n\n".join(lines), encoding="utf-8")
    return source


def _hand_back(result):
    """A repair that changes nothing: it returns the reading's rows, whole."""
    return producer_items(result)


def test_a_repair_is_re_read_in_the_room_the_answer_used(tmp_path):
    """The per-answer ceiling refuses a repaired card the reading itself carried.

    Measured, not assumed: the run hands its whole row list back through the same entry point
    twice, with the answer's own room and with the default one, and keeps both verdicts.
    """
    from catalyst_platform.understand_semantic import (
        _MAX_MERGED_ENTITIES, _MAX_MERGED_OTHER_ITEMS,
        _MAX_SEMANTIC_ENTITIES, _MAX_SEMANTIC_OTHER_ITEMS,
    )

    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    request = UnderstandingRequest("seam-run", "整理组织", source_refs=(_long_source(tmp_path),),
                                   intent=UnderstandIntent.KNOWLEDGE_PROPOSE)
    spec = repair_spec(name="hand-back", version="1.0.0",
                       implementation=f"{__name__}:_hand_back", scope={"labels": ["card-a"]})
    run = run_semantic_method(methods, request, source_root=tmp_path, provider=_RowsPerUnit(),
                              extraction_mode="single_stage", label="card-a", repairs=spec,
                              record_dir=tmp_path / "record", probe_whole_answer=True,
                              # A unit-split reading is accepted at the merged tier; the run
                              # says so instead of letting the row count say it.
                              authorised_budget=(_MAX_MERGED_ENTITIES, _MAX_MERGED_OTHER_ITEMS))
    rows = producer_items(run.original)
    assert len(rows) > _MAX_SEMANTIC_OTHER_ITEMS,         f"the fixture has to exceed the per-answer ceiling, got {len(rows)}"
    # Every row came back: nothing was trimmed to fit a ceiling.
    assert run.validation["items_accepted"] == len(rows)
    budget = run.validation["segment_budget"]
    assert budget["answer_segments"]["other_items"] == len(rows)
    assert budget["default_segments"] == {"entities": _MAX_SEMANTIC_ENTITIES,
                                          "other_items": _MAX_SEMANTIC_OTHER_ITEMS}
    assert budget["authorised_segments"] == {"entities": _MAX_MERGED_ENTITIES,
                                             "other_items": _MAX_MERGED_OTHER_ITEMS}
    assert budget["clamped_by_authorisation"] is False
    assert budget["wider_than_default"] is True
    # The same rows under the default room are refused, and the refusal names the ceiling.
    record = json.loads((tmp_path / "record" / "run-record.json").read_text(encoding="utf-8"))
    probe = record["capacity_probe"]
    assert probe["rows"] == len(rows)
    assert probe["with_the_answers_room"] == {"accepted": len(rows), "refused": None}
    assert probe["with_the_default_room"]["accepted"] is None
    assert "SemanticCapacityError" in probe["with_the_default_room"]["refused"]
    # The verdict is about re-validation, and it says so: passing the validator is not a handoff.
    assert probe["whole_answer_passes_revalidation"] is True
    assert "whole_answer_can_be_handed_on" not in probe
    assert probe["handoff_authorised"] is False


def test_a_run_does_not_widen_its_own_room(tmp_path):
    """No declared ceiling, no wider room: the row count may not authorise itself.

    The same answer that is accepted whole at the merged tier is refused when the run declares
    nothing, because the default is the per-answer room and nothing in the seam can promote it.
    """
    from catalyst_platform.understand_models import SemanticCapacityError

    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    request = UnderstandingRequest("seam-run", "整理组织", source_refs=(_long_source(tmp_path),),
                                   intent=UnderstandIntent.KNOWLEDGE_PROPOSE)
    spec = repair_spec(name="hand-back", version="1.0.0",
                       implementation=f"{__name__}:_hand_back", scope={"labels": ["card-a"]})
    with pytest.raises(SemanticCapacityError, match="envelope accepts at most"):
        run_semantic_method(methods, request, source_root=tmp_path, provider=_RowsPerUnit(),
                            extraction_mode="single_stage", label="card-a", repairs=spec,
                            record_dir=tmp_path / "record")
    # And nothing was written: a refused run leaves no half-kept record behind.
    assert not (tmp_path / "record" / "run-record.json").exists()


def test_the_room_is_clamped_by_what_the_run_was_authorised_for():
    """The answer's own count is a wish; the run's ceiling is the bound."""
    from catalyst_platform.semantic_method import segment_budget_for

    rows = [{"item_id": f"i{index}", "kind": "claim", "key": f"k{index}", "meaning": "一句话"}
            for index in range(140)]
    result = _Stored(rows, attribution={})
    # An answer of 140 rows, in a run authorised to hold 130 of them: the room is the ceiling,
    # and the record says the ceiling decided it -- not the answer, and not a constant.
    budget = segment_budget_for(result, authorised=(64, 130))
    assert (budget["entities"], budget["other_items"]) == (64, 130)
    assert budget["clamped_by_authorisation"] is True
    assert budget["authorised_segments"] == {"entities": 64, "other_items": 130}
    # No declaration at all: the per-answer default, whatever the answer holds.
    undeclared = segment_budget_for(result)
    assert (undeclared["entities"], undeclared["other_items"]) == (64, 128)
    assert undeclared["authorised_segments"] is None
    assert undeclared["wider_than_default"] is False
    # A ceiling under the per-answer default is a mistake, not a narrow run.
    with pytest.raises(SemanticMethodError, match="segment_budget_below_default"):
        segment_budget_for(result, authorised=(32, 128))


def test_a_frozen_record_is_not_written_twice(tmp_path):
    """Two runs, one folder, is how a frozen run loses the artifact that says what it saw."""
    from catalyst_platform.semantic_method import write_record

    rows = [{"item_id": "i1", "kind": "entity", "key": "a", "meaning": "甲",
             "evidence_class": "observed_from_source", "evidence_refs": ["ev_1"]}]
    result = _Stored(rows, evidence=(_ref("ev_1"),))
    folder = tmp_path / "record"
    write_record(folder, original=result, repaired=rows, submitted=rows, stored=result,
                 identity={}, validation={}, segment_budget={})
    with pytest.raises(SemanticMethodError, match="record_directory_in_use"):
        write_record(folder, original=result, repaired=rows, submitted=rows, stored=result,
                     identity={}, validation={}, segment_budget={})
    # A rehearsal may still overwrite, but it has to say so.
    write_record(folder, original=result, repaired=rows, submitted=rows, stored=result,
                 identity={}, validation={}, segment_budget={}, overwrite=True)


def test_the_diff_names_both_rows_when_two_share_a_kind_and_a_key():
    from catalyst_platform.semantic_method import diff_items

    before = [{"kind": "entity", "key": "same", "meaning": "甲"},
              {"kind": "claim", "key": "other", "meaning": "乙"},
              {"kind": "entity", "key": "same", "meaning": "甲的分身"}]
    after = [{"kind": "entity", "key": "same", "meaning": "甲"}]
    changes = diff_items(before, after)
    # Three rows in, one row out: two rows left, and the second one is not folded away.
    assert [change["change"] for change in changes] == ["removed", "removed"]
    assert {change["key"] for change in changes} == {"same", "other"}
    # The identity that held two rows names the second one; the single-row identity needs no word.
    # Folded onto one identity, `same` would have compared row 0 with the survivor, found them
    # equal, and reported nothing -- the row that says 甲的分身 would leave without a line.
    by_key: dict[str, list] = {}
    for change in changes:
        by_key.setdefault(change["key"], []).append(change.get("occurrence"))
    assert by_key == {"same": [1], "other": [None]}
    assert {change["key"]: change.get("meaning") for change in changes} == {
        "same": "甲的分身", "other": "乙"}


def _keep_the_lead(result):
    """A repair that submits one row: what was left out has to survive the run somewhere."""
    return [row for row in producer_items(result) if row.get("key") == "review_lead"]


def test_a_run_keeps_every_row_set_whole_and_pinned(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="keep-the-lead", version="1.0.0",
                       implementation=f"{__name__}:_keep_the_lead", scope={"labels": ["card-a"]})
    folder = tmp_path / "record"
    run = run_semantic_method(methods, request_for(tmp_path, "复核负责人负责单据复核。单据由复核组保管。"),
                              source_root=tmp_path, provider=_OneEntity(),
                              extraction_mode="single_stage", label="card-a", repairs=spec,
                              record_dir=folder)
    record = json.loads((folder / "run-record.json").read_text(encoding="utf-8"))
    # Five complete row sets, each with the digest of exactly the bytes written.
    for name in ("original", "repaired", "submitted", "stored", "unsubmitted"):
        path = Path(record["files"][name]["path"])
        assert path.parent == folder and path.is_file()
        assert record["files"][name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert record["files"][name]["baseline"] == record["baseline"][name]
    original = json.loads((folder / "original-items.json").read_text(encoding="utf-8"))
    submitted = json.loads((folder / "submitted-items.json").read_text(encoding="utf-8"))
    unsubmitted = json.loads((folder / "unsubmitted-items.json").read_text(encoding="utf-8"))
    # The rows the repair did not submit are kept whole: the same rows the reading wrote,
    # field for field, not a list of names that would have to be looked up somewhere else.
    assert len(unsubmitted) == len(original) - len(submitted)
    kept = {(row.get("kind"), row.get("key")): row for row in submitted}
    for row in unsubmitted:
        assert (row.get("kind"), row.get("key")) not in kept
        assert row in original
    # And the sums are the run's own, stated rather than implied.
    conservation = record["conservation"]
    assert conservation["holds"] is True
    assert conservation["original"] == conservation["paired"] + conservation["unsubmitted"]
    assert conservation["stored"] == conservation["paired"] + conservation["added"]
    assert conservation["submitted_equals_repaired"] is True
    assert conservation["citations_invented_by_repair"] == []
    assert run.record_files["path"] == str(folder / "run-record.json")


def test_the_run_identity_travels_inside_the_result(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="type-as-position", version="1.0.0",
                       implementation=f"{__name__}:_type_as_position", scope={"labels": ["card-a"]})
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneEntity(), extraction_mode="single_stage",
                              label="card-a", repairs=spec, record_dir=tmp_path / "record")
    attribution = run.result.producer_attribution
    # What a derived package carries from here on: the method, the repair, the built-in Skills.
    assert attribution["method"]["component_id"] == SEMANTIC_COMPONENT
    assert attribution["method"]["package_sha256"] == run.identity["method"]["package_sha256"]
    assert attribution["repairs"]["sha256"] == run.identity["repairs"]["sha256"]
    assert attribution["builtin_skills"]["files"] == run.identity["builtin_skills"]["files"]
    # Every digest this record carries says what bytes it covers.
    units = attribution["digest_units"]
    assert set(units) >= {"producer_output_sha256", "repairs.sha256", "builtin_skills.files",
                          "skills_provided[].instruction_sha256", "method.package_sha256"}
    record = json.loads((tmp_path / "record" / "run-record.json").read_text(encoding="utf-8"))
    assert record["attribution"]["method"] == attribution["method"]
    assert record["attribution"]["digest_units"] == units


def test_the_record_refuses_a_stored_row_nothing_pair_with_or_submitted(tmp_path):
    from catalyst_platform.semantic_method import write_record

    original = _Stored([{"item_id": "i1", "kind": "entity", "key": "a", "meaning": "甲",
                         "evidence_class": "observed_from_source", "evidence_refs": ["ev_1"]}])
    stored = _Stored([{"item_id": "i1", "kind": "entity", "key": "a", "meaning": "甲",
                       "evidence_class": "observed_from_source", "evidence_refs": ["ev_1"]},
                      {"item_id": "i2", "kind": "entity", "key": "ghost", "meaning": "没提交过的行",
                       "evidence_class": "observed_from_source", "evidence_refs": ["ev_1"]}])
    with pytest.raises(SemanticMethodError, match="record_row_not_accounted"):
        write_record(tmp_path / "record", original=original, repaired=[], submitted=[],
                     stored=stored, identity={}, validation={}, segment_budget={})


class _OneRowWithACitationNothingIssued:
    """One claim citing an evidence id the reading never received: the validator degrades it."""

    model = "seam-fixture"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "claim", "key": "approval_authority", "meaning": "审批权限在财务部",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ["ev_never_issued"]}]},
            ensure_ascii=False), finish_reason="stop")


def _as_given(result):
    """A repair that changes nothing: it hands the rows back, degradation and all."""
    return producer_items(result)


def test_a_row_the_reading_refused_never_reaches_the_ledger(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "ontology"))
    spec = repair_spec(name="as-given", version="1.0.0",
                       implementation=f"{__name__}:_as_given", scope={"labels": ["card-a"]})
    run = run_semantic_method(methods, request_for(tmp_path), source_root=tmp_path,
                              provider=_OneRowWithACitationNothingIssued(),
                              extraction_mode="single_stage", label="card-a", repairs=spec,
                              disposition_path=tmp_path / "disposition.json")
    ledger = json.loads(Path(run.disposition["path"]).read_text(encoding="utf-8"))
    # The reading refused this row before any repair saw it, so the repair had nothing to
    # hand back. An empty ledger is the result, not a loss: nothing was dropped from it.
    assert ledger["rows"] == []
    assert run.disposition["counts"]["submitted"] == 0
    assert run.validation["items_submitted"] == run.validation["items_accepted"] == 0
    # The row itself is not gone: it is in the run's evidence, with the rule the reading
    # wrote on it, and the record can still say what the answer offered and why it stayed.
    diagnostics = {row["key"]: row for row in run.result.run_diagnostics}
    # The answer's own refused row is here beside the port's two standing absences about
    # approval and binding: all three are questions about the reading, none is a candidate.
    assert {"approval_authority", "approval", "binding"} <= set(diagnostics)
    refused = diagnostics["approval_authority"]
    assert refused["reason"] == "evidence_ref_not_supplied"
    assert refused["degradation"]["class"] == "run_diagnostic"
    assert refused["destination"] == "run_evidence"


def test_a_kept_row_still_names_the_step_and_the_call_that_wrote_it(tmp_path):
    _run, ledger, _target = _ledger_run(tmp_path)
    by_key = {row["key"]: row for row in ledger["rows"]}

    # `kept` is a verdict about the words: the tag is left out of the comparison and
    # still travels on the line, so a kept row can be traced to where it was written.
    kept = by_key["review_lead"]
    assert kept["outcome"] == "kept"
    assert "source_origin" not in kept["fields"]
    tag = kept["source_origin"]["after"]
    assert tag["category"] == "source_claim"
    assert tag["step"] == "answer:model"
    assert tag["call"] == "seam-run:repair:mixed-ledger:1.0.0"
    assert tag["item_id"] == kept["item_id"]
    # The submitted row carried no tag - a producer does not write this field - so the
    # ledger says what wrote the stored row without inventing a `before`.
    assert "before" not in kept["source_origin"]
    # A row that never reached the store says so, rather than naming a source it lacks.
    assert by_key["dan_ju"]["source_origin"]["after"] is None
    # And a reader who holds only this ledger is told what `kept` does not say.
    assert "not that its source did" in ledger["header"]["compared_with"]["source_origin"]
