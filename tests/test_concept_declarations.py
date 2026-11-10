"""A type says what its instances have, reach, must satisfy, do and are measured by."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from catalyst_platform.ontology_concepts import (
    adopt_concept_pack,
    concept_projection,
    concept_set_of,
    define_concept,
    empty_concept_state,
)
from catalyst_platform.ontology_types import (
    Action,
    Attribute,
    Concept,
    ConceptError,
    ConceptSet,
    Constraint,
    Metric,
    Relation,
    STARTER_PACK,
    declared_counts,
)
from catalyst_platform.semantic_score import score_items, score_wiki
from catalyst_platform.wiki import ProjectWiki

REPO = Path(__file__).resolve().parents[1]


def _wiki(tmp_path) -> ProjectWiki:
    roots = tmp_path / "sources"
    roots.mkdir(exist_ok=True)
    return ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="ent", project_id="declared")


def _declared_ward() -> Concept:
    return Concept(
        "Ward", "病区", "Organization", "病区、护理单元：医院里独立收治的一段病床",
        attributes=(Attribute("bed_count", "number", True, "核定床位数"),),
        relations=(Relation("yields", "Deliverable", "many", "病区产出交付物"),),
        constraints=(Constraint("出院日 >= 入院日"),),
        actions=(Action("收治", "办理病人入院"),),
        metrics=(Metric("平均住院日", "天", "出院日期 - 入院日期"),),
    )


def test_a_declared_type_reads_back_with_everything_it_said(tmp_path):
    wiki = _wiki(tmp_path)
    wiki.update_concept_state(
        lambda state: define_concept(state, _declared_ward(), actor="owner", reason="医院资料里有病区"))

    reopened = _wiki(tmp_path)
    ward = reopened.concept_set().by_id("Ward")

    assert ward.attributes == (Attribute("bed_count", "number", True, "核定床位数"),)
    assert ward.relations == (Relation("yields", "Deliverable", "many", "病区产出交付物"),)
    assert ward.constraints == (Constraint("出院日 >= 入院日"),)
    assert ward.actions == (Action("收治", "办理病人入院"),)
    assert ward.metrics == (Metric("平均住院日", "天", "出院日期 - 入院日期"),)
    assert declared_counts(reopened.concept_set().concepts) == {
        "concepts": 12, "attributes": 1, "relations": 1, "constraints": 1, "actions": 1, "metrics": 1}


def test_a_type_that_says_one_thing_twice_is_refused():
    with pytest.raises(ConceptError) as refused:
        Concept("Ward", "病区", "Organization", "病区",
                attributes=(Attribute("bed_count"), Attribute("bed_count", "text")))
    assert refused.value.code == "concept_declaration_duplicated"


@pytest.mark.parametrize(
    "row, code",
    [
        ({"name": "bed_count", "value_type": "money"}, "concept_declaration_invalid"),
        ({"name": "  "}, "concept_declaration_invalid"),
        ({"name": "bed_count", "required": "yes"}, "concept_declaration_invalid"),
    ],
)
def test_an_attribute_row_the_ledger_could_not_read_is_refused(row, code):
    with pytest.raises(ConceptError) as refused:
        Concept.from_dict({**_declared_ward().to_dict(), "attributes": [row]})
    assert refused.value.code == code


def test_a_relation_cardinality_outside_the_two_choices_is_refused():
    with pytest.raises(ConceptError) as refused:
        Concept.from_dict({**_declared_ward().to_dict(),
                           "relations": [{"predicate": "yields", "target": "Deliverable", "cardinality": "few"}]})
    assert refused.value.code == "concept_declaration_invalid"


def test_a_relation_whose_target_the_set_does_not_hold_is_reported_not_refused():
    state = empty_concept_state()
    concept = Concept("Ward", "病区", "Organization", "病区",
                      relations=(Relation("reports_to", "Nowhere"),))
    define_concept(state, concept, actor="owner", reason="先写关系")

    projection = concept_projection(state)

    # The ledger keeps what the scope said; a reader can see the target that resolves nowhere.
    assert concept_set_of(state).by_id("Ward").relations == (Relation("reports_to", "Nowhere"),)
    assert projection["unresolved_relation_targets"] == [
        {"concept_id": "Ward", "predicate": "reports_to", "target": "Nowhere"}]


def test_adopting_a_pack_keeps_what_its_concepts_declare():
    state = empty_concept_state()
    pack = ConceptSet((Concept("Ward", "病区", "Organization", "病区",
                               metrics=(Metric("床位使用率", "%"),)),), "only-1")

    adopt_concept_pack(state, actor="owner", reason="按本项目的包走", pack=pack)

    assert concept_projection(state)["declarations"] == {
        "concepts": 1, "attributes": 0, "relations": 0, "constraints": 0, "actions": 0, "metrics": 1}


def test_the_score_says_what_is_declared_and_what_is_only_read():
    measured = {row["id"]: row for row in score_items(
        [], declarations={"concepts": 3, "actions": 2, "constraints": 5, "metrics": 1})["metrics"]}

    for number in (11, 12, 13):
        assert measured[number]["instance_value"] == 0
        assert measured[number]["passed"] is True
    assert measured[11]["declared_value"] == 2
    assert measured[12]["declared_value"] == 5
    assert measured[13]["declared_value"] == 1


def test_the_score_without_declarations_still_reports_zero():
    report = score_items([])
    measured = {row["id"]: row for row in report["metrics"]}

    assert report["declared_structure"] == {}
    assert (measured[11]["value"], measured[12]["value"], measured[13]["value"]) == (0, 0, 0)


def test_the_prompt_states_declared_structure_and_leaves_the_starter_pack_text_alone():
    assert "已声明的结构" not in STARTER_PACK.prompt_rules()
    declared = ConceptSet((_declared_ward(),), "concepts-1", "declared")

    rules = declared.prompt_rules()

    assert "已声明的结构" in rules
    assert "属性 bed_count(number，必填)" in rules
    assert "关系 yields→Deliverable(多)" in rules
    assert "动作 收治" in rules
    assert "指标 平均住院日(天)" in rules


def _seed_candidate(wiki: ProjectWiki) -> str:
    candidate_id = "candidate_declared_1"
    wiki.update_semantic_state(lambda state: state["candidates"].__setitem__(candidate_id, {
        "candidate_id": candidate_id,
        "scope_id": wiki.scope_id,
        "source_id": "source_declared",
        "source_revision": "a" * 64,
        "parent_version_id": None,
        "proposer_origin": "codex_fixture",
        "entries": [],
        "status": "PROPOSED",
        "created_run_id": "run_declared",
        "latest_evaluation_id": None,
        "latest_decision_id": None,
    }))
    return candidate_id


def test_the_wiki_score_counts_the_declared_metric_a_reader_never_passed_as_an_entry(tmp_path):
    wiki = _wiki(tmp_path)
    wiki.update_concept_state(
        lambda state: define_concept(state, _declared_ward(), actor="owner", reason="医院资料里有病区"))
    _seed_candidate(wiki)

    report = score_wiki(wiki)
    measured = {row["id"]: row for row in report["metrics"]}

    assert report["concept_set"]["declarations"]["metrics"] == 1
    assert measured[13]["passed"] is True and measured[13]["declared_value"] == 1
    assert measured[12]["passed"] is False


def _cli(*args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    return completed.returncode, json.loads(completed.stdout) if completed.stdout.strip() else {}


def test_the_cli_declares_the_five_kinds_and_shows_them(tmp_path):
    (tmp_path / "sources").mkdir()
    common = ["--workspace", str(tmp_path / "workspace"), "--wiki-root", str(tmp_path / "sources"),
              "--enterprise-id", "ent", "--project-id", "declared"]
    code, defined = _cli(
        "ontology", "concepts", "define", *common,
        "--concept-id", "Ward", "--name", "病区", "--meta-kind", "Organization",
        "--criteria", "病区、护理单元", "--attribute", "bed_count:number!",
        "--relation", "yields:Deliverable:one", "--constraint", "出院日 >= 入院日",
        "--action", "收治", "--metric", "平均住院日:天", "--reason", "医院资料里有病区")
    assert code == 0, defined
    row = defined["result"]["concept"]
    assert row["attributes"] == [{"name": "bed_count", "value_type": "number", "required": True, "description": ""}]
    assert row["relations"] == [{"predicate": "yields", "target": "Deliverable", "cardinality": "one", "description": ""}]

    code, shown = _cli("ontology", "concepts", "show", *common)
    assert code == 0, shown
    assert shown["declarations"] == {
        "concepts": 12, "attributes": 1, "relations": 1, "constraints": 1, "actions": 1, "metrics": 1}
    ward = next(row for row in shown["scope_concept_set"]["concepts"] if row["concept_id"] == "Ward")
    assert ward["metrics"] == [{"name": "平均住院日", "unit": "天", "definition": ""}]


def test_the_cli_refuses_a_relation_flag_it_cannot_read(tmp_path):
    (tmp_path / "sources").mkdir()
    common = ["--workspace", str(tmp_path / "workspace"), "--wiki-root", str(tmp_path / "sources"),
              "--enterprise-id", "ent", "--project-id", "declared"]
    code, refused = _cli(
        "ontology", "concepts", "define", *common,
        "--concept-id", "Ward", "--name", "病区", "--meta-kind", "Organization",
        "--criteria", "病区", "--relation", "yields", "--reason", "医院资料里有病区")

    assert code == 2
    assert "PREDICATE:TARGET" in refused["error"]["message"]
