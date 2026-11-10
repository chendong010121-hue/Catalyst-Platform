"""S2 bounded control: one repair, and measurements of what is still open.

Owner's round-08 review named one defect that can be accepted without settling any
business question - `_degrade` rebuilds a refused row out of the fields its caller
passes, and `scope_state` is never one of them, so a page that draws a proposal
degrades into a page that dates nothing. That repair, and the boundary of what it
carries, is measured in G1.

The rest are measurements. None of them is marked `xfail` any more. The two that were -
the reading layer's own guard rail read as source knowledge once a scope is attached, and
a key that differs from its one declaration only in case - now pass as behaviour, each by
a contract the Owner pinned: the source contract (a guard sentence is run evidence however
it is armed) and the reference-binding rule of 2026-11-02 (a reference binds by ASCII
letter case alone, and only when exactly one declaration can own it). A marker is only
removed by making the behaviour true; deleting the test would have left pytest quiet and
the gap exactly where it was.

Four more were strict xfails until the duty repair landed: two units named above one work
item, a passage that denies the duty, a passage that makes it conditional, and a paraphrase
standing for an original condition. Each now passes as a *refusal* - the row stays
`unconfirmed` with the fragment that is missing named - and the paraphrase case passing says
only that the system keeps the uncertainty; whether '调整后…' may stand for '若通过调整…' is
still nobody's decision here.

A second bounded round followed the d5cbcd6 review, which found the reader still confirming
two simple sentences it should not have: a claim stitched out of two units' clauses, and a
claim whose sentence holds wording - before or after it - that the claim does not say. Both
are refused now, clause by clause and side by side. The disclosed cost is the last test in
G2: an opening fragment this reader cannot read is not assumed to be adverbial, so a claim
that keeps such a fragment word for word still stays unconfirmed. Telling an adverbial from a
headless predicate is not a text rule, and that test is there so nobody "fixes" it by adding
one more condition word.

The duty contract these tests are written against: `confirmed` says a stored claim - its
subject, its work item, its polarity, its condition and its exception - is carried by the
passage it cites. It does **not** say a proposal has taken effect or that anything may be
executed. So a clear responsibility sentence may pass even when it names a second unit; a
name and a duty that are only adjacent in two cells may not pass on co-occurrence alone; a
negation or a condition may pass when the claim keeps it whole, and must fail when it is
dropped, flipped or replaced. Where support cannot be judged, the row stays `unconfirmed`
with the reason named - no judge model, no general reasoning engine, no new schema.

What is deliberately *not* measured or built here: no key or identifier is changed, no
query is re-scoped, no global case folding is introduced, and `approval` / `binding` are
not turned into source knowledge - nor is the key `approval` blocked, because material
may really discuss an approval.
"""
from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_models import GroundedItem, source_origin_tag
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.semantic_wiki import _reading_qualification

# No heading word from `_SCOPE_CURRENT_WORDS` / `_SCOPE_PROPOSED_WORDS`: the page says
# nothing about which arrangement it draws, so every state a row carries is the row's own
# word and never one inherited from its page.
TEXT = ("投资管理中心与市场营销中心整合为一个中心，设置为市场营销中心。\n"
        "后台职能部门负责专业能力建设，服务一线。\n")
LINE = "投资管理中心与市场营销中心整合为一个中心，设置为市场营销中心。"
NAMES = {"touzi_guanli_zhongxin": "投资管理中心",
         "shichang_yingxiao_zhongxin": "市场营销中心",
         "houtai_zhineng_bumen": "后台职能部门",
         "zhongtai_zhineng_bumen": "中台职能部门"}


class _Answer:
    model = "stub-s2-bounded-control"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _evidence(evidence, name):
    return next(item["evidence_id"] for item in evidence if name in item["quote"])


def _entity(key, name, evidence):
    return {"kind": "entity", "key": key, "meaning": name, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, name)]}


def _run(tmp_path, build):
    source = tmp_path / "deck.md"
    source.write_text(TEXT, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("s2-bounded-control", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_s2",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def _declared(evidence):
    return [_entity("touzi_guanli_zhongxin", "投资管理中心", evidence),
            _entity("shichang_yingxiao_zhongxin", "市场营销中心", evidence)]


def _drop_rules(result, key):
    return [row["rule"] for row in result.producer_attribution["item_contract_drops"]
            if row["item_key"] == key]


# --- G1: a refused row keeps what it said, and only what it said -------------------


def _refused_event(evidence, **overrides):
    """One change the contract refuses for one end, written the way 246 was."""
    row = {"kind": "event", "key": "zhenghe_shichang_zhongxin", "predicate": "整合",
           "meaning": "「投资管理中心」与「市场营销中心」整合为一个中心",
           "subject": "touzi_guanli_zhongxin", "object": "shichang_yingxiao_zhongxin",
           "evidence_class": "SOURCE_DIRECT",
           "evidence_refs": [_evidence(evidence, "投资管理中心")],
           "from": ["touzi_guanli_zhongxin"],
           # 新设部门 is a unit this answer never declared: the row is kept, refused.
           "to": ["shichang_yingxiao_zhongxin", "xinzeng_bumen"]}
    row.update(overrides)
    return row


def test_a_change_refused_for_one_end_still_says_it_was_proposed(tmp_path):
    def build(evidence):
        return [*_declared(evidence), _refused_event(evidence, scope_state="proposed")]

    item = _by_key(_run(tmp_path, build))["zhenghe_shichang_zhongxin"]

    # Still the row it was: an event, kept, refused - and now still dated as a proposal.
    assert (item.kind, item.evidence_class) == ("event", "unresolved")
    assert item.uncertainty == "degraded:event_endpoint_not_declared:xinzeng_bumen"
    assert item.scope_state == "proposed"


def test_a_change_refused_for_one_end_keeps_the_current_state_too(tmp_path):
    """The repair carries the label, not the word `proposed`: a current page is dated too."""
    def build(evidence):
        return [*_declared(evidence), _refused_event(evidence, scope_state="current")]

    item = _by_key(_run(tmp_path, build))["zhenghe_shichang_zhongxin"]

    assert item.evidence_class == "unresolved"
    assert item.scope_state == "current"


def test_a_refused_row_whose_page_said_nothing_gets_no_state_invented(tmp_path):
    def build(evidence):
        return [*_declared(evidence), _refused_event(evidence)]

    item = _by_key(_run(tmp_path, build))["zhenghe_shichang_zhongxin"]

    assert item.evidence_class == "unresolved"
    assert item.scope_state is None


@pytest.mark.parametrize("state", ["invalid-state", "CURRENT", " current", ""],
                         ids=["not-a-state", "wrong-case", "untrimmed", "empty"])
def test_a_state_the_contract_does_not_name_is_dropped_and_named(tmp_path, state):
    """A value nobody defined is a dropped field with its rule, not a silent `None`."""
    def build(evidence):
        return [*_declared(evidence), _refused_event(evidence, scope_state=state)]

    result = _run(tmp_path, build)
    item = _by_key(result)["zhenghe_shichang_zhongxin"]

    assert item.scope_state is None
    assert _drop_rules(result, "zhenghe_shichang_zhongxin") == [
        "event_endpoint_not_declared", "scope_state_unsupported"]


@pytest.mark.parametrize("state", [{"state": "current"}, ["current"], 1, True],
                         ids=["object", "array", "number", "boolean"])
def test_a_state_written_in_another_type_costs_the_field_and_not_the_run(tmp_path, state):
    """A type nobody checked used to raise; the row now loses the field and says which rule."""
    def build(evidence):
        return [*_declared(evidence), _refused_event(evidence, scope_state=state)]

    result = _run(tmp_path, build)
    item = _by_key(result)["zhenghe_shichang_zhongxin"]

    assert item.scope_state is None
    assert _drop_rules(result, "zhenghe_shichang_zhongxin") == [
        "event_endpoint_not_declared", "scope_state_unsupported"]


@pytest.mark.parametrize("state", [{"state": "current"}, ["current"]], ids=["object", "array"])
def test_a_state_written_in_another_type_never_reaches_the_row(tmp_path, state):
    """The ordinary path asks the same question first: a row that is not refused still
    loses a label nobody could read, and the run keeps going."""
    def build(evidence):
        return [*_declared(evidence),
                {**_entity("houtai_zhineng_bumen", "后台职能部门", evidence),
                 "scope_state": state}]

    result = _run(tmp_path, build)
    item = _by_key(result)["houtai_zhineng_bumen"]

    assert item.kind == "entity"
    assert item.scope_state is None
    assert _drop_rules(result, "houtai_zhineng_bumen") == ["scope_state_unsupported"]


def test_a_state_on_a_kind_that_cannot_carry_it_is_dropped_and_named(tmp_path):
    """A claim has no arrangement of its own: the field goes, the statement stays.

    Asked through the ordinary path, not the refusal path: this is the same rule the
    degraded rows go through, so it is answered in one place (`_scope_state_of`).
    """
    def build(evidence):
        return [*_declared(evidence),
                {"kind": "claim", "key": "fuwu_yixian", "meaning": "后台职能部门服务一线",
                 "evidence_class": "SOURCE_DIRECT",
                 "evidence_refs": [_evidence(evidence, "后台职能部门")],
                 "scope_state": "current"}]

    result = _run(tmp_path, build)
    item = _by_key(result)["fuwu_yixian"]

    assert item.kind == "claim"
    assert item.meaning == "后台职能部门服务一线"
    assert item.scope_state is None
    assert _drop_rules(result, "fuwu_yixian") == ["scope_state_not_applicable"]


def test_a_state_on_a_row_that_degrades_to_unknown_is_dropped_and_named(tmp_path):
    def build(evidence):
        return [*_declared(evidence),
                {"kind": "claim", "key": "fuwu_yixian", "meaning": "后台职能部门服务一线",
                 # An evidence id this answer never received: the claim degrades to an
                 # unknown, and an unknown is not a kind that carries an arrangement label.
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": ["ev_nie_ma"],
                 "scope_state": "current", "uncertainty": "自述"}]

    result = _run(tmp_path, build)
    row = next(row for row in result.run_diagnostics if row.get("key") == "fuwu_yixian")

    # The row is kept whole and named where it went; the label its new kind cannot hold is
    # dropped and named too, in the same pass.
    assert (row["kind"], row["evidence_class"]) == ("unknown", "unresolved")
    assert row["scope_state"] is None
    assert row["reason"] == "evidence_ref_not_supplied"
    assert _drop_rules(result, "fuwu_yixian") == [
        "evidence_ref_not_supplied", "scope_state_not_applicable"]


def test_a_refused_row_still_loses_the_fields_it_may_not_write(tmp_path):
    def build(evidence):
        return [*_declared(evidence), _refused_event(
            evidence, scope_state="proposed",
            # A verdict and its standing are the layer's or a reviewer's, on a refused row too.
            verification="confirmed", qualification="stated",
            # The answer's own note is replaced by the refusal that is actually true.
            uncertainty="这一行是我推断的")]

    result = _run(tmp_path, build)
    item = _by_key(result)["zhenghe_shichang_zhongxin"]

    assert result.producer_attribution["governance_fields_refused"] == [{
        "item_key": "zhenghe_shichang_zhongxin", "kind": "event",
        "fields": ["qualification", "verification"]}]
    assert (item.verification, item.qualification) == (None, None)
    # The answer's own note is replaced by the refusal that is actually true - the row keeps
    # the reason it was refused, not the reason it gave for itself.
    assert item.uncertainty == "degraded:event_endpoint_not_declared:xinzeng_bumen"
    # The state is the page's word, not a verdict: it travels, and only it travels.
    assert item.scope_state == "proposed"


# --- G2: a holder named in the passage is not yet a binding ------------------------


def test_a_duty_whose_passage_names_two_units_is_not_confirmed(tmp_path):
    """Owner, round-08: 名字格与职责格分别有据 ≠ 二者绑定正确.

    Both units stand in cells above the work, so neither of them is the subject of the
    sentence that states it. The row is kept and stays unconfirmed, and the fragment that
    is missing is named instead of a verdict being guessed.
    """
    quote = "后台职能部门\n中台职能部门\n服务：专业能力建设，服务一线，风险管控"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source",
        meaning="服务：专业能力建设，服务一线，风险管控")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "holder_and_duty_not_in_one_sentence"


def test_a_clear_responsibility_sentence_that_also_names_another_unit_is_confirmed(tmp_path):
    """The guard against the lazy repair: two names in one passage is not itself the fault.

    Here the passage says who is responsible ("后台职能部门负责…") and merely mentions the
    other unit afterwards, so the binding is read off the sentence, not counted. Only the
    standing is asserted: a repair may rename the basis, and must not start refusing this.
    """
    quote = "后台职能部门负责专业能力建设，服务一线；中台职能部门负责资源统筹。"

    qualification, verification, _basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="负责专业能力建设，服务一线")

    assert verification == "confirmed"
    assert qualification in {"stated", "inferred"}


def test_a_duty_the_passage_denies_is_not_confirmed(tmp_path):
    """「不负责…」 and 「负责…」 are two claims; the passage makes one of them."""
    quote = "后台职能部门不负责专业能力建设。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="负责专业能力建设")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "polarity_not_carried"


def test_a_duty_the_passage_makes_conditional_is_not_confirmed(tmp_path):
    """A work item that waits for a condition is not the work item stated outright."""
    quote = "若通过调整，后台职能部门负责专业能力建设。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="负责专业能力建设")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "condition_not_carried"


def test_a_duty_whose_statement_is_the_denial_is_confirmed(tmp_path):
    """The other guard: a passage that says 「不负责」 and a row that says the same is carried.

    Refusing every passage with a negation in it would lose exactly these rows.
    """
    quote = "后台职能部门不负责专业能力建设。"

    qualification, verification, _basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="不负责专业能力建设")

    assert verification == "confirmed"
    assert qualification in {"stated", "inferred"}


def test_a_duty_whose_statement_is_the_condition_is_confirmed(tmp_path):
    """The condition has to survive whole: the same clause, in the same words.

    A shorthand ("调整后…") is a different claim, and whether it may stand for
    「若通过调整…」 is a question of its own - kept as the pending case below, not
    answered by this one passing.
    """
    quote = "若通过调整，后台职能部门负责专业能力建设。"

    qualification, verification, _basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="若通过调整，负责专业能力建设")

    assert verification == "confirmed"
    assert qualification in {"stated", "inferred"}


def test_a_paraphrased_condition_is_not_confirmed_until_equivalence_is_decided(tmp_path):
    """Still a pending decision, and what this now asserts is only that nothing decided it.

    Whether '调整后…' may stand for '若通过调整…' is not ours to settle. Until it is, the
    passage does not carry the claim in the row's own words, so the row stays unconfirmed -
    the system keeping the uncertainty, never a verdict that the two wordings differ.
    """
    quote = "若通过调整，后台职能部门负责专业能力建设。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="调整后负责专业能力建设")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "duty_text_not_in_evidence"


def test_a_duty_stitched_out_of_two_units_clauses_is_not_confirmed(tmp_path):
    """Owner, d5cbcd6 review, counterexample one: one sentence, two subjects.

    「后台职能部门负责专业能力建设，中台职能部门负责资源统筹」 states two duties. Reading
    the nearest name before the *last* fragment and confirming the whole claim joins a half
    of 后台's sentence to 中台's: the first clause is 后台's, so the joined claim is nobody's.
    """
    quote = "后台职能部门负责专业能力建设，中台职能部门负责资源统筹。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="zhongtai_zhineng_bumen",
        evidence_class="observed_from_source",
        meaning="负责专业能力建设，负责资源统筹")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "duty_attached_to_another_unit"


def test_a_duty_whose_lead_in_the_claim_drops_is_not_confirmed(tmp_path):
    """Owner, d5cbcd6 review, counterexample two: a word list is not a reading.

    「仅在审批通过后…」 is not in any condition vocabulary this reader carries, and that is
    exactly why it may not be taken to mean the passage is unconditional. The one thing that
    can be shown is that the passage has words before the work which the claim does not say.
    """
    quote = "仅在审批通过后，后台职能部门负责专业能力建设。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="负责专业能力建设")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "restriction_not_carried"


def test_a_duty_whose_sentence_holds_more_after_it_is_not_confirmed(tmp_path):
    """The same rule on the other side of the work, so neither side is a special case."""
    quote = "后台职能部门负责专业能力建设，自 2026 年起每年复核。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="负责专业能力建设")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "restriction_not_carried"


def test_a_duty_that_skips_the_words_between_its_clauses_is_not_confirmed(tmp_path):
    """Owner, 3c68eeb review: the gap between two matched fragments is not a safe omission.

    「后台职能部门负责专业能力建设，仅在审批通过后负责资源统筹」 puts the second duty under a
    condition. A claim that matches the two clauses and says nothing about what stands
    between them has made that duty unconditional, and the intervals a claim leaves out are
    read on every side of it - before, between and after.
    """
    quote = "后台职能部门负责专业能力建设，仅在审批通过后负责资源统筹。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="负责专业能力建设，负责资源统筹")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "restriction_not_carried"


def test_a_lead_in_this_reader_cannot_read_stays_unconfirmed_even_when_kept(tmp_path):
    """The disclosed cost of that rule, pinned so nobody "fixes" it with a longer word list.

    The claim keeps every word of the sentence, so nothing was dropped; what cannot be shown
    is that 「仅在审批通过后」 modifies the work that follows rather than being a predicate
    whose subject stands elsewhere. Telling an adverbial from a headless predicate is not a
    text rule, so the row stays unconfirmed and the reason says the fragment has no holder.
    """
    quote = "仅在审批通过后，后台职能部门负责专业能力建设。"

    qualification, verification, basis = _reading_qualification(
        "duty", quote=quote, names=NAMES, holder="houtai_zhineng_bumen",
        evidence_class="observed_from_source", meaning="仅在审批通过后，负责专业能力建设")

    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "duty_not_attached_to_holder"


# --- G3: one casing question, three answers ---------------------------------------


def test_a_key_differing_only_in_case_resolves_to_the_one_declaration(tmp_path):
    """Owner, 2026-11-02: a reference may bind by case when one declaration can own it.

    This was the round-08 gap: the answer wrote one unit with a capital I, seven times,
    against a declaration spelled correctly, and the two spellings were read as
    different names. Binding is by ASCII letter case alone, against the
    declarations this run allowed - and it says nothing about whether the row is true.
    """
    def build(evidence):
        return [*_declared(evidence), _refused_event(
            evidence,
            # 246 as the model wrote it: the same unit spelled with a capital I, seven times
            # in one answer, against four declarations that spell it correctly.
            **{"from": ["touzi_guanli_zhongxin", "shichang_yIngxiao_zhongxin"],
               "to": ["shichang_yIngxiao_zhongxin"]})]

    item = _by_key(_run(tmp_path, build))["zhenghe_shichang_zhongxin"]

    assert item.uncertainty is None
    assert item.event_from == ("touzi_guanli_zhongxin", "shichang_yingxiao_zhongxin")
    assert item.event_to == ("shichang_yingxiao_zhongxin",)


def test_a_key_two_declarations_could_own_keeps_its_ambiguity(tmp_path):
    """The conflict case cannot reach the resolver: intake refuses it first.

    Every key a card submits is casefolded into the store's own spelling, so two
    declarations that differ only in case arrive as one key and the submission is
    refused. That is a refusal, not a choice between the two - which is the answer to
    "两个声明时必须保留歧义": nothing here may silently pick one, and today nothing does,
    because nothing gets that far.
    """
    from catalyst_platform.understand_models import SemanticContractError

    def build(evidence):
        return [
            {"kind": "entity", "key": "zhongxin", "meaning": "甲中心",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [_evidence(evidence, "投资管理中心")]},
            {"kind": "entity", "key": "Zhongxin", "meaning": "乙中心",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [_evidence(evidence, "后台职能部门")]},
            _entity("touzi_guanli_zhongxin", "投资管理中心", evidence),
            _refused_event(evidence, **{"from": ["ZHONGXIN"], "to": ["touzi_guanli_zhongxin"]})]

    with pytest.raises(SemanticContractError) as refused:
        _run(tmp_path, build)

    assert "duplicate_key" in str(refused.value)
    assert "zhongxin" in str(refused.value)


def test_a_key_no_declaration_carries_is_refused_by_name(tmp_path):
    def build(evidence):
        return [*_declared(evidence), _refused_event(
            evidence, **{"from": ["weixuan_danwei"], "to": ["touzi_guanli_zhongxin"]})]

    item = _by_key(_run(tmp_path, build))["zhenghe_shichang_zhongxin"]

    assert item.uncertainty == "degraded:event_endpoint_not_declared:weixuan_danwei"
    assert item.event_from == () and item.event_to == ()


# --- G4: which arrangement, and how well it is carried, are two axes ---------------


def test_the_state_and_the_standing_are_read_on_two_axes(tmp_path):
    def build(evidence):
        ends = {"from": ["touzi_guanli_zhongxin", "shichang_yingxiao_zhongxin"],
                "to": ["shichang_yingxiao_zhongxin"]}
        return [*_declared(evidence),
                _refused_event(evidence, key="proposed_change",
                               scope_state="proposed", **ends),
                _refused_event(evidence, key="undated_change", **ends)]

    items = _by_key(_run(tmp_path, build))

    def qualification(item):
        return _reading_qualification(
            "event", quote=LINE, names=NAMES, predicate=item.predicate,
            ends={"from": item.event_from, "to": item.event_to},
            evidence_class=item.evidence_class)

    # What the page drew, and what its passage carries, side by side and unmixed.
    assert items["proposed_change"].scope_state == "proposed"
    assert items["undated_change"].scope_state is None
    assert qualification(items["proposed_change"]) == (
        "pending", "unconfirmed", "roles_or_endpoints_unsettled")
    # Same passage, same standing: the state is not an input to the qualification.
    assert qualification(items["proposed_change"]) == qualification(items["undated_change"])


# --- G5: the reading's own guard rail, and an absence the material really carries --


def _base(tmp_path):
    source = tmp_path / "business.md"
    source.write_text("财务部门负责月度经营分析，法务部门复核合同预算。", encoding="utf-8")
    port = UnderstandPort()
    result = port.understand(
        UnderstandingRequest("s2-diagnostic-boundary", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path)
    return port, result, result.evidence_refs[0].evidence_id


def _attach(port, base, items):
    return port.attach_producer_items(base, producer_kind="CODEX_EXTERNAL",
                                      producer_invocation_id="s2-bounded-control", items=items)


def _absence(evidence_id, **overrides):
    row = {"kind": "unknown", "key": "approval", "meaning": "材料是否已获批准，文本未说明。",
           "evidence_class": "UNKNOWN", "evidence_refs": [evidence_id],
           "scope_refs": [evidence_id], "observed_absence": "审批",
           "uncertainty": "材料只写职责分工"}
    row.update(overrides)
    return [row]


def _item(**overrides):
    """A row the reading wrote in this call, with the tag its step wrote."""
    row = dict(item_id="item_a", kind="unknown", key="approval", meaning="未说明审批。",
               evidence_refs=(), evidence_class="unresolved", confidence="not_calibrated")
    row.update(overrides)
    return GroundedItem(
        source_origin=source_origin_tag("reading:passage", row["item_id"],
                                        call="s2-diagnostic-boundary"), **row)


def _classify(items, *, refs=(), inventory=(), origin="submitted",
              call="s2-diagnostic-boundary"):
    from catalyst_platform.understand_semantic import _split_run_diagnostics

    return _split_run_diagnostics(items, warnings=[], inventory=list(inventory),
                                  evidence_refs=list(refs), origin=origin,
                                  recorded_calls={call})


def _guard_rows(result):
    """The two sentences the reading layer writes itself, taken from the layer itself."""
    return [row for row in result.unknowns if row.key in {"approval", "binding"}]


def test_the_reading_layers_own_guard_rails_stay_run_evidence(tmp_path):
    """The original wording, through the pass that actually writes it (`origin: answer`)."""
    _port, result, _evidence_id = _base(tmp_path)
    guards = _guard_rows(result)

    # Taken from the layer, not retyped: these are the sentences 342-row card carried.
    assert {row.key for row in guards} == {"approval", "binding"}
    assert {row.meaning for row in guards} == {
        "正式审批授权不由本次文本理解授予或证明。",
        "真实工具绑定不由本次文本理解授予或证明。"}

    kept, diagnostics, _summary = _classify(
        guards, refs=result.evidence_refs, inventory=result.source_inventory, origin="answer")

    assert kept == []
    assert {row["reason"] for row in diagnostics} == {"absence_without_scope"}
    assert {row["destination"] for row in diagnostics} == {"run_evidence"}
    # Which pass refused them: the reading's own, not a producer's submission.
    assert {row["degradation"]["at"] for row in diagnostics} == {
        "understand_semantic.answer:absence:scope"}


def test_an_absence_the_material_really_carries_keeps_the_key_approval(tmp_path):
    """The gate reads the statement, not the word: real material may be about approval."""
    port, base, evidence_id = _base(tmp_path)
    result = _attach(port, base, _absence(evidence_id))

    item = next(row for row in result.unknowns if row.key == "approval")
    assert item.meaning == "材料是否已获批准，文本未说明。"
    assert item.degradation["class"] == "business_unknown"
    assert result.run_diagnostics == ()


def test_a_guard_sentence_given_a_scope_is_not_read_as_source_knowledge(tmp_path):
    _port, result, evidence_id = _base(tmp_path)
    armed = [replace(row, scope_refs=(evidence_id,), observed_absence="审批")
             for row in _guard_rows(result)]

    kept, diagnostics, _summary = _classify(
        armed, refs=result.evidence_refs, inventory=result.source_inventory, origin="answer")

    # Not a source statement, however complete it looks: the row says what this run cannot
    # grant, so no scope or gap attached to it makes it something the material said. The
    # reason is now pinned, because the contract it had to come from exists: the step that
    # wrote the row is not one that writes claims about the material.
    assert kept == []
    assert {row["reason"] for row in diagnostics} == {"source_origin_run_diagnostic"}
    assert {row["destination"] for row in diagnostics} == {"run_evidence"}
    assert {row["degradation"]["at"] for row in diagnostics} == {
        "understand_semantic.answer:source_origin:run_diagnostic"}


def test_a_guard_row_that_says_what_it_looked_for_still_lacks_its_scope():
    kept, diagnostics, _summary = _classify([_item(observed_absence="审批")])

    assert kept == []
    assert diagnostics[0]["reason"] == "absence_without_scope"
    # The gap is there; the range it was looked for in is not, and only that is named.
    assert diagnostics[0]["missing"] == ["scope"]


def test_a_row_with_a_scope_but_no_gap_basis_is_a_question_about_the_reading():
    kept, diagnostics, _summary = _classify(
        [_item(scope_refs=("ev_a",), observed_absence=None)],
        # A range this run did read: the scope holds, and only the gap is missing.
        refs=[SimpleNamespace(evidence_id="ev_a", locator="line:1",
                              relative_path="business.md", source_id="source_a")],
        inventory=[SimpleNamespace(source_id="source_a", relative_path="business.md",
                                   extraction_status="COMPLETE")])

    assert kept == []
    assert diagnostics[0]["reason"] == "gap_basis_missing"
    assert diagnostics[0]["missing"] == ["gap_basis"]
