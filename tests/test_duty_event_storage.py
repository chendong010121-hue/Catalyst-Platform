"""A duty keeps its holder, an event keeps both sides, and both say how far they were read.

D of the C/D/E contract. Two qualifications are kept apart: a complete duty or event may
be saved and reviewed even while it is pending, and only a row whose content the cited
passage carries, and which was confirmed and qualified, may be returned as a fact. A
pending row comes back with the limit it was read under, never dressed as confirmed.
"""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from catalyst_platform.harness_plugins import EvoWikiSearchCapability
from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.understand_wiki import UnderstandWikiAdapter
from catalyst_platform.wiki import ProjectWiki, WikiScopeError
from p0_test_authority import trusted_test_operation

SOURCE_LINES = [
    "# 合成组织与变化",
    "后台职能部门负责服务：专业能力建设，服务一线，风险管控。",
    "中台职能部门负责管理+赋能：体系建设、风险管控+能力建设、资源池。",
    "四分公司合并到天水智静；保留四分法人主体。",
    "一分公司合并到天水智信；不再保留一分法人主体。",
    "整合投资管理中心、市场营销中心，设置为市场营销中心。",
]

ENTITIES = [
    ("houtai_zhineng", "后台职能部门", 2),
    ("zhongtai_zhineng", "中台职能部门", 3),
    ("si_fengongsi", "四分公司", 4),
    ("tianshui_zhijing", "天水智静", 4),
    ("yi_fengongsi", "一分公司", 5),
    ("tianshui_zhixin", "天水智信", 5),
    ("touzi_guanli", "投资管理中心", 6),
    ("shichang_yingxiao", "市场营销中心", 6),
]


def _evidence(line: int) -> dict:
    quote = SOURCE_LINES[line - 1]
    return {"line_start": line, "line_end": line, "quote": quote,
            "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest()}


def _entity(key: str, name: str, line: int) -> dict:
    return {"kind": "entity", "canonical_key": key, "display_name": name,
            "evidence_class": "inferred", "evidence": _evidence(line)}


def _duty(**overrides) -> dict:
    item = {"kind": "duty", "key": "houtai_fuwu", "meaning": SOURCE_LINES[1],
            "evidence_class": "observed_from_source", "evidence": _evidence(2),
            "holder": "@houtai_zhineng", "predicate": "负责"}
    item.update(overrides)
    return item


def _event(**overrides) -> dict:
    item = {"kind": "event", "key": "si_fengongsi_hebing_zhijing", "meaning": SOURCE_LINES[3],
            "evidence_class": "observed_from_source", "evidence": _evidence(4),
            "from": ["@si_fengongsi"], "to": ["@tianshui_zhijing"], "predicate": "合并",
            "keeps_legal_entity": True}
    item.update(overrides)
    return item


def _run(workspace, wiki, run_id, method, *args, **kwargs):
    recorder = RunRecorder(
        JsonlTraceStore(workspace), run_id=run_id, request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        event_schema_version="1.5")
    recorder.start(request_kind="duty_event_test", actor="local_cli_user",
                   component="CatalystGateway")
    service = SemanticWiki(wiki, recorder=recorder)
    result = getattr(service, method)(*args, **kwargs)
    recorder.finish("success", model_calls=0)
    service.finalize_run(run_id, "success")
    return service, result


def _wiki(tmp_path):
    roots = tmp_path / "sources"
    roots.mkdir()
    path = roots / "org_change.md"
    path.write_text("\n".join(SOURCE_LINES) + "\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic",
                       project_id="duty-event", backend="json")
    _service, staged = _run(workspace, wiki, "run_stage", "stage_source", path,
                            actor_origin="catalyst_deterministic")
    return workspace, roots, wiki, staged


def _submission(staged, items, *, version="catalyst.external_candidate.v2"):
    return {"schema_version": version, "producer_origin": "codex_external",
            "scope_id": staged["scope_id"], "source_id": staged["source_id"],
            "source_revision": staged["revision"],
            "origin_document_sha256": staged["revision"], "items": items}


def _entities():
    return [_entity(*row) for row in ENTITIES]


def _rejection(workspace, wiki, submission, *, method="propose_external_submission_v2"):
    with pytest.raises(SemanticTransitionError) as raised:
        _run(workspace, wiki, "run_reject", method, submission)
    return raised.value.code


def _accepted(workspace, wiki, staged, items, run_id):
    """Propose, evaluate, decide and activate one candidate, the way the gateway does."""
    _service, proposed = _run(workspace, wiki, run_id, "propose_external_submission_v2",
                              _submission(staged, items))
    _service, evaluation = _run(workspace, wiki, f"{run_id}_evaluate", "evaluate",
                                proposed["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "pass", evaluation
    decision = trusted_test_operation(
        workspace, wiki, f"{run_id}_decide", "decide", proposed["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance",
        reason_code="synthetic-manager-review")
    trusted_test_operation(
        workspace, wiki, f"{run_id}_activate", "activate", decision["result"]["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=None)
    return proposed


def _read(wiki, query="组织 职责 合并 整合"):
    return wiki.read_knowledge(query, mode="accepted_enterprise_semantics",
                               include_all_active=True, limit=100)


# --- what is stored -----------------------------------------------------------


def test_a_duty_is_stored_with_its_holder_as_a_field(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [*_entities(), _duty()], "run_duty")

    row = next(item for item in _read(wiki)["meanings"] if item["kind"] == "duty")

    # The holder is a field that addresses an entity, not a sentence about one.
    assert row["holder"] == "houtai_zhineng"
    assert row["holder_name"] == "后台职能部门"
    assert row["predicate"] == "负责"
    assert row["meaning"] == SOURCE_LINES[1]
    assert row["qualification"] == "stated"
    assert row["verification"] == "confirmed"
    # The passage travels with the row by the line it occupies and the digest of its text.
    anchor = row["evidence"][0]
    assert (anchor["line_start"], anchor["line_end"]) == (2, 2)
    assert anchor["span_sha256"] == _evidence(2)["span_sha256"]


def test_a_duty_can_be_read_by_the_object_that_holds_it(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    # Neither duty's own sentence names the unit that holds it, and the two holders share no
    # character, so the only way either row is found by a holder's name is the holder field.
    held = _duty(meaning="服务一线", evidence=_evidence(2))
    neighbour = _duty(key="bingfang_guanli", meaning="体系建设", evidence=_evidence(3),
                      holder="@bingfang", predicate="负责")
    _accepted(workspace, wiki, staged,
              [*_entities(), _entity("bingfang", "丙方", 3), held, neighbour],
              "run_duty_by_object")

    def held_by(name):
        read = wiki.read_knowledge(name, mode="accepted_enterprise_semantics", limit=100)
        return [row["key"] for row in read["meanings"] if row["kind"] == "duty"]

    assert held_by("后台职能部门") == ["houtai_fuwu"]
    assert held_by("丙方") == ["bingfang_guanli"]


def test_a_duty_is_read_by_the_object_that_holds_it_and_not_by_a_shared_name(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    # 后台职能部门 and 中台职能部门 share every character but one, so a text query for
    # either finds both: asking by the object is what tells them apart.
    mirror = _duty(key="zhongtai_guanli", meaning="管理+赋能", evidence=_evidence(3),
                   holder="@zhongtai_zhineng", predicate="负责")
    _accepted(workspace, wiki, staged, [*_entities(), _duty(), mirror], "run_duty_by_index")

    both = wiki.read_knowledge("后台职能部门", mode="accepted_enterprise_semantics", limit=100)
    assert {row["key"] for row in both["meanings"] if row["kind"] == "duty"} == {
        "houtai_fuwu", "zhongtai_guanli"}

    read = wiki.read_knowledge("职责", mode="accepted_enterprise_semantics", limit=100,
                               about="后台职能部门")

    assert [row["key"] for row in read["meanings"] if row["kind"] == "duty"] == ["houtai_fuwu"]
    # The entity itself comes along, so the answer says who the holder is.
    assert "houtai_zhineng" in {row["key"] for row in read["meanings"] if row["kind"] == "entity"}


def test_an_event_is_read_by_the_unit_on_either_side(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    other = _event(key="yi_fengongsi_hebing_zhixin", meaning=SOURCE_LINES[4],
                   evidence=_evidence(5), **{"from": ["@yi_fengongsi"]},
                   to=["@tianshui_zhixin"], keeps_legal_entity=False)
    _accepted(workspace, wiki, staged, [*_entities(), _event(), other], "run_event_by_index")

    # A text query for one unit finds both changes, because both names share 分公司.
    both = wiki.read_knowledge("四分公司", mode="accepted_enterprise_semantics", limit=100)
    assert len([row for row in both["meanings"] if row["kind"] == "event"]) == 2

    went_in = wiki.read_knowledge("变化", mode="accepted_enterprise_semantics", limit=100,
                                  about="四分公司")
    came_out = wiki.read_knowledge("变化", mode="accepted_enterprise_semantics", limit=100,
                                   about="天水智静")

    for read in (went_in, came_out):
        assert [row["key"] for row in read["meanings"] if row["kind"] == "event"] == [
            "si_fengongsi_hebing_zhijing"]


def test_a_read_by_object_is_only_for_accepted_semantics(tmp_path):
    _workspace, _roots, wiki, _staged = _wiki(tmp_path)

    with pytest.raises(WikiScopeError):
        wiki.read_knowledge("职责", mode="grounded_claims", about="后台职能部门")
    with pytest.raises(WikiScopeError):
        wiki.read_knowledge("职责", mode="accepted_enterprise_semantics", about="  ")


def test_an_event_can_be_read_by_either_of_its_sides(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [*_entities(), _event()], "run_event_by_side")

    def changed(name):
        read = wiki.read_knowledge(name, mode="accepted_enterprise_semantics", limit=100)
        return [row["key"] for row in read["meanings"] if row["kind"] == "event"]

    # What went in and what came out are both ways to the same change.
    assert changed("四分公司") == ["si_fengongsi_hebing_zhijing"]
    assert changed("天水智静") == ["si_fengongsi_hebing_zhijing"]


def test_a_duty_whose_holder_is_not_a_selected_entity_is_refused(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [*_entities(), _duty(holder="@nobody_here")])

    assert _rejection(workspace, wiki, submission) == "duty_holder_not_selected"


def test_an_event_keeps_both_sides_and_the_legal_person_it_names(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [*_entities(), _event()], "run_event")

    row = next(item for item in _read(wiki)["meanings"] if item["kind"] == "event")

    # A change is one action with two sides, and the sides are what is stored.
    assert row["from"] == ["si_fengongsi"]
    assert row["to"] == ["tianshui_zhijing"]
    assert row["from_names"] == ["四分公司"]
    assert row["to_names"] == ["天水智静"]
    assert row["ends_source"] == "lists"
    assert row["predicate"] == "合并"
    # Which legal person came out of it: the absorbed party's, said in the sentence.
    assert row["keeps_legal_entity"] is True
    assert row["qualification"] == "stated"
    assert row["verification"] == "confirmed"


def test_an_event_that_does_not_keep_the_legal_person_says_so(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [
        *_entities(),
        _event(key="yi_fengongsi_hebing_zhixin", meaning=SOURCE_LINES[4],
               evidence=_evidence(5), **{"from": ["@yi_fengongsi"]},
               to=["@tianshui_zhixin"], keeps_legal_entity=False),
    ], "run_event_false")

    row = next(item for item in _read(wiki)["meanings"] if item["kind"] == "event")

    assert row["keeps_legal_entity"] is False
    assert row["from"] == ["yi_fengongsi"] and row["to"] == ["tianshui_zhixin"]


# --- what stays pending --------------------------------------------------------


def _same_unit_both_sides():
    """246: the change names one unit on both sides, so it does not say which is which."""
    return _event(
        key="touzi_shichang_zhenghe", meaning=SOURCE_LINES[5], evidence=_evidence(6),
        **{"from": ["@touzi_guanli", "@shichang_yingxiao"]}, to=["@shichang_yingxiao"],
        predicate="整合", keeps_legal_entity=None)


def test_an_event_whose_two_sides_share_a_unit_is_saved_but_pending(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [*_entities(), _same_unit_both_sides()], "run_pending")

    read = _read(wiki)
    row = next(item for item in read["meanings"] if item["kind"] == "event")

    # Saved whole, with both sides and the limit it was read under.
    assert row["from"] == ["touzi_guanli", "shichang_yingxiao"]
    assert row["to"] == ["shichang_yingxiao"]
    assert row["verification"] == "unconfirmed"
    assert row["qualification"] == "pending"
    assert row["restriction"]["reads_as"] == "candidate_only"
    assert row["restriction"]["kind"] == "pending"
    assert read["restricted_meaning_count"] >= 1


def test_a_duty_whose_own_evidence_does_not_name_its_holder_is_pending(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [
        *_entities(),
        _duty(holder="@zhongtai_zhineng", meaning=SOURCE_LINES[1], evidence=_evidence(2),
              key="houtai_fuwu_read_from_elsewhere"),
    ], "run_holder_pending")

    row = next(item for item in _read(wiki)["meanings"]
               if item["key"] == "houtai_fuwu_read_from_elsewhere")

    assert row["holder"] == "zhongtai_zhineng"
    assert row["verification"] == "unconfirmed"
    assert row["qualification"] == "pending"
    assert row["restriction"]["missing"] == ["holder_not_in_evidence"]


# --- what is refused ----------------------------------------------------------


def test_an_event_with_no_side_at_all_is_refused(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [*_entities(),
                                      _event(**{"from": [], "to": []})])

    assert _rejection(workspace, wiki, submission) == "event_endpoints_missing"


def test_an_event_naming_a_unit_outside_the_candidate_is_refused(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [*_entities(),
                                      _event(to=["@nobody_here"])])

    assert _rejection(workspace, wiki, submission) == "event_participant_not_selected"


def test_a_submission_may_not_decide_how_far_it_was_read(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [*_entities(),
                                      _duty(qualification="stated", verification="confirmed")])

    assert _rejection(workspace, wiki, submission) == "producer_may_not_author_governance_fields"


def test_an_external_submission_may_not_say_where_its_ends_came_from(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [*_entities(), _event(ends_source="lists")])

    assert _rejection(workspace, wiki, submission) == "producer_may_not_author_governance_fields"


# --- a limit that travels with the row ----------------------------------------


def test_a_condition_says_which_duty_it_limits(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [
        *_entities(),
        _duty(),
        {"kind": "condition", "key": "peak_only", "meaning": "风险管控",
         "evidence_class": "observed_from_source", "evidence": _evidence(2),
         "applies_to": ["@houtai_fuwu"]},
    ], "run_condition")

    row = next(item for item in _read(wiki)["meanings"] if item["kind"] == "condition")
    assert row["applies_to"] == ["houtai_fuwu"]


def test_a_condition_that_names_no_duty_is_marked_unattached(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _accepted(workspace, wiki, staged, [
        *_entities(),
        _duty(),
        {"kind": "condition", "key": "peak_only", "meaning": "风险管控",
         "evidence_class": "observed_from_source", "evidence": _evidence(2),
         "applies_to": []},
    ], "run_condition_unattached")

    row = next(item for item in _read(wiki)["meanings"] if item["kind"] == "condition")
    assert row["applies_to"] == []
    assert row["unattached"] is True


def test_a_condition_that_limits_nothing_in_the_candidate_is_refused(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    submission = _submission(staged, [
        *_entities(),
        {"kind": "condition", "key": "peak_only", "meaning": "风险管控",
         "evidence_class": "observed_from_source", "evidence": _evidence(2),
         "applies_to": ["@not_in_this_candidate"]},
    ])

    assert _rejection(workspace, wiki, submission) == "condition_applies_to_unknown"


# --- what the native harvest assembles, row by row ------------------------------


def _harvest_items():
    """The rows the way `propose_native` hands them over: the producer's own shape.

    A native row comes to the harvest as a dict with `from` / `to` / `subject`, not as a
    `GroundedItem`: reading it with attribute access finds nothing and the event arrives at
    the store with no sides at all. These rows are the guard on that.
    """
    return {row["item_id"]: row for row in [
        {"item_id": "i_houtai", "kind": "entity", "key": "houtai_zhineng",
         "meaning": "后台职能部门", "evidence_class": "inferred", "evidence_refs": ["ev_entity"]},
        {"item_id": "i_si", "kind": "entity", "key": "si_fengongsi",
         "meaning": "四分公司", "evidence_class": "inferred", "evidence_refs": ["ev_entity"]},
        {"item_id": "i_zhijing", "kind": "entity", "key": "tianshui_zhijing",
         "meaning": "天水智静", "evidence_class": "inferred", "evidence_refs": ["ev_entity"]},
        {"item_id": "i_duty", "kind": "duty", "key": "houtai_fuwu",
         "meaning": SOURCE_LINES[1], "evidence_class": "observed_from_source",
         "evidence_refs": ["ev_duty"], "subject": "houtai_zhineng", "predicate": "负责",
         "scope_state": "current"},
        {"item_id": "i_event", "kind": "event", "key": "si_fengongsi_hebing_zhijing",
         "meaning": SOURCE_LINES[3], "evidence_class": "observed_from_source",
         "evidence_refs": ["ev_event"], "from": ["si_fengongsi"],
         "to": ["tianshui_zhijing"], "predicate": "合并", "ends_source": "lists",
         "keeps_legal_entity": True, "keeps_legal_entity_scope": "unclear"},
        {"item_id": "i_condition", "kind": "condition", "key": "peak_only",
         "meaning": "风险管控", "evidence_class": "inferred", "evidence_refs": ["ev_duty"],
         "applies_to": ["houtai_fuwu"]},
    ]}


def _harvest(selected, *, items=None):
    refs = {"ev_entity": {"evidence_id": "ev_entity", "locator": "line:1",
                          "quote": SOURCE_LINES[0], "source_id": "src"},
            "ev_duty": {"evidence_id": "ev_duty", "locator": "line:2",
                        "quote": SOURCE_LINES[1], "source_id": "src"},
            "ev_event": {"evidence_id": "ev_event", "locator": "line:4",
                         "quote": SOURCE_LINES[3], "source_id": "src"}}
    adapter = UnderstandWikiAdapter(wiki=None, semantic=None, source_root="/")
    return adapter.harvest_entries(items or _harvest_items(), refs, selected,
                                   lines=[], strict=False)


def test_the_native_harvest_keeps_a_duty_holder_and_an_event_two_sides():
    entries, report = _harvest(["i_houtai", "i_si", "i_zhijing", "i_duty", "i_event",
                                "i_condition"])
    by_key = {entry.get("key"): entry for entry in entries}

    duty = by_key["houtai_fuwu"]
    assert duty["kind"] == "duty"
    assert duty["holder"] == "@houtai_zhineng"
    assert duty["predicate"] == "负责"
    assert duty["scope_state"] == "current"
    # A native meaning is stored as `inferred` whatever the producer called it.
    assert duty["evidence_class"] == "inferred"

    event = by_key["si_fengongsi_hebing_zhijing"]
    assert event["from"] == ["@si_fengongsi"]
    assert event["to"] == ["@tianshui_zhijing"]
    assert event["ends_source"] == "lists"
    # The legal-person answer travels with the row, and says whom it is about.
    assert event["keeps_legal_entity"] is True
    assert event["keeps_legal_entity_scope"] == "unclear"

    # A restriction names the duty it limits instead of sitting beside it.
    assert by_key["peak_only"]["applies_to"] == ["@houtai_fuwu"]
    assert report["dropped"] == []


def test_the_native_harvest_names_a_duty_whose_holder_is_not_selected():
    # The duty is selected; the entity that holds it is not.
    entries, report = _harvest(["i_si", "i_zhijing", "i_duty", "i_event", "i_condition"])

    assert "houtai_fuwu" not in {entry.get("key") for entry in entries}
    assert {row["rule"] for row in report["dropped"]} == {"duty_holder_not_selected"}


def test_the_native_harvest_names_an_event_whose_side_is_not_selected():
    # The event is selected; one of the two units it joins is not.
    entries, report = _harvest(["i_houtai", "i_zhijing", "i_duty", "i_event", "i_condition"])

    assert "si_fengongsi_hebing_zhijing" not in {entry.get("key") for entry in entries}
    assert {row["rule"] for row in report["dropped"]} == {"event_participant_not_selected"}


# --- what a consumer is handed ------------------------------------------------


def _semantic(wiki, workspace, run_id="run_consumer"):
    recorder = RunRecorder(
        JsonlTraceStore(workspace), run_id=run_id, request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        event_schema_version="1.5")
    recorder.start(request_kind="consumer_restriction_test", actor="local_cli_user",
                   component="CatalystGateway")
    return SemanticWiki(wiki, recorder=recorder), recorder


def _one_pending_and_one_confirmed(workspace, wiki, staged):
    # The same sentence read twice: once with the holder its own words name, once with a
    # holder the passage does not name - so exactly one of the two is saved for review.
    _accepted(workspace, wiki, staged, [
        *_entities(),
        _duty(),
        _duty(key="houtai_fuwu_read_from_elsewhere", holder="@zhongtai_zhineng",
              meaning=SOURCE_LINES[1], evidence=_evidence(2)),
    ], "run_consumer_rows")


def test_a_consumer_is_handed_a_pending_duty_to_review_and_not_among_the_facts(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _one_pending_and_one_confirmed(workspace, wiki, staged)
    semantic, recorder = _semantic(wiki, workspace)

    result = {}
    EvoWikiSearchCapability._attach_scoped_project_knowledge(
        result, "负责",
        SimpleNamespace(plugin_services={"semantic_wiki": semantic, "project_wiki": wiki}),
        "synthetic")
    knowledge = result["project_knowledge"]
    facts = knowledge["accepted_semantics"]["meanings"]
    review = knowledge["pending_review"]

    # The confirmed duty is a fact; the row saved for review is handed over as review.
    assert [row["key"] for row in facts if row["kind"] == "duty"] == ["houtai_fuwu"]
    assert [row["key"] for row in review] == ["houtai_fuwu_read_from_elsewhere"]
    # Its holder and its wording come along only under the limit the read gave them.
    assert review[0]["holder_name"] == "中台职能部门"
    assert review[0]["restriction"]["reads_as"] == "candidate_only"
    assert review[0]["restriction"]["missing"] == ["holder_not_in_evidence"]
    # Nothing in the fact list is there under that limit, and the counts agree with it.
    assert not [row for row in facts
                if (row.get("restriction") or {}).get("reads_as") == "candidate_only"]
    assert knowledge["accepted_semantics"]["meaning_count"] == len(facts)
    assert knowledge["accepted_semantics"]["meaning_ids"] == [row["meaning_id"] for row in facts]
    recorder.finish("success", model_calls=0)


def test_a_reader_is_told_which_saved_row_is_still_pending(tmp_path):
    workspace, _roots, wiki, staged = _wiki(tmp_path)
    _one_pending_and_one_confirmed(workspace, wiki, staged)
    view = wiki.read_knowledge("负责", mode="accepted_enterprise_semantics", limit=100)

    rendered = ProjectWiki.format_context({
        "scope_id": view["scope_id"],
        "read_mode": "grounded_claims",
        "accepted_semantics": [row for row in view["meanings"]
                               if row.get("freshness_status") == "fresh"],
        "accepted_semantic_view": view,
    })

    lines = rendered.splitlines()
    facts = [line for line in lines if line.startswith("Meaning ")]
    review = [line for line in lines if line.startswith("Candidate ")]

    # One duty is stated and one is only saved: each is said in its own place, and the
    # pending one carries the fragment that is missing instead of reading as a fact.
    assert len(facts) == 1 and len(review) == 1
    assert "pending (pending/unconfirmed; missing holder_not_in_evidence)" in review[0]
    assert "pending" not in facts[0]
