"""The concept set belongs to the scope: versioned per decision, retired not deleted."""

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
    concept_state_is_valid,
    define_concept,
    deprecate_concept,
    empty_concept_state,
    resolve_concept_in,
)
from catalyst_platform.ontology_types import Concept, ConceptError, ConceptSet
from catalyst_platform.semantic_score import score_items
from catalyst_platform.wiki import ProjectWiki, WikiUnavailable

REPO = Path(__file__).resolve().parents[1]

WARD = Concept("Ward", "病区", "Organization", "病区、护理单元：医院里独立收治的一段病床",
               aliases=("bingqu",))


def _wiki(tmp_path) -> ProjectWiki:
    roots = tmp_path / "sources"
    roots.mkdir(exist_ok=True)
    return ProjectWiki(tmp_path / "workspace", [roots], enterprise_id="ent", project_id="concepts")


def _cli(*args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    return completed.returncode, json.loads(completed.stdout) if completed.stdout.strip() else {}


def test_a_scope_that_declared_nothing_reads_the_starter_pack(tmp_path):
    wiki = _wiki(tmp_path)
    projection = concept_projection(wiki.concept_state())

    assert wiki.concept_set().version_id == "starter-1"
    assert projection["declared"] is False
    assert projection["versions"] == []
    assert len(wiki.concept_set().concepts) == 11
    assert set(concept.meta_kind for concept in wiki.concept_set().concepts) == set(projection["meta_kinds"])


def _common(tmp_path) -> list[str]:
    return ["--workspace", str(tmp_path / "workspace"), "--wiki-root", str(tmp_path / "sources"),
            "--enterprise-id", "ent", "--project-id", "concepts"]


def test_defining_a_concept_publishes_a_version_the_scope_reads_back(tmp_path):
    (tmp_path / "sources").mkdir()
    code, defined = _cli(
        "ontology", "concepts", "define", *_common(tmp_path),
        "--concept-id", "Ward", "--name", "病区", "--meta-kind", "Organization",
        "--criteria", "病区、护理单元", "--alias", "bingqu", "--reason", "医院资料里有病区")
    assert code == 0 and defined["status"] == "success", defined
    assert defined["result"]["parent_version_id"] is None

    code, shown = _cli("ontology", "concepts", "show", *_common(tmp_path))
    assert code == 0, shown
    assert shown["declared"] is True
    assert shown["scope_concept_set"]["version_id"] == "concepts-1"
    assert "Ward" in [row["concept_id"] for row in shown["scope_concept_set"]["concepts"]]
    assert shown["history"][0]["reason"] == "医院资料里有病区"
    # A scope never restates eleven types to add a twelfth.
    assert shown["history"][0]["started_from"] == "starter_pack"

    wiki = ProjectWiki(tmp_path / "workspace", [tmp_path / "sources"], enterprise_id="ent",
                       project_id="concepts")
    assert wiki.concept_set().resolve("bingqu") == Concept("Ward", "病区", "Organization", "病区、护理单元",
                                                          aliases=("bingqu",), origin="manager_acceptance")


def test_a_second_decision_builds_on_the_first(tmp_path):
    wiki = _wiki(tmp_path)
    first = wiki.update_concept_state(
        lambda state: define_concept(state, WARD, actor="owner", reason="医院资料里有病区"))
    second = wiki.update_concept_state(
        lambda state: define_concept(state, Concept("CareUnit", "护理单元", "Organization", "护理单元"),
                                     actor="owner", reason="护理单元要单独统计"))

    assert (first["version_id"], second["version_id"]) == ("concepts-1", "concepts-2")
    assert second["parent_version_id"] == "concepts-1"
    assert second["concept_count"] == 13
    assert wiki.concept_set().ids()[-2:] == ("Ward", "CareUnit")


def test_a_retired_concept_keeps_the_spellings_it_answered_to(tmp_path):
    wiki = _wiki(tmp_path)
    wiki.update_concept_state(lambda state: define_concept(state, WARD, actor="owner", reason="有病区"))
    retired = wiki.update_concept_state(
        lambda state: deprecate_concept(state, "Ward", actor="owner", reason="改用护理单元",
                                        replacement="Department"))

    state = wiki.concept_state()
    assert retired["replacement"] == "Department"
    assert "Ward" not in concept_set_of(state).ids()
    # A card read under the old set still says 病区, and it now means the replacement.
    assert resolve_concept_in(state, "病区").concept_id == "Department"
    assert resolve_concept_in(state, "bingqu").concept_id == "Department"
    assert concept_projection(state)["retired"][0]["name"] == "病区"


def test_a_concept_may_not_be_replaced_by_one_the_scope_does_not_hold(tmp_path):
    wiki = _wiki(tmp_path)
    wiki.update_concept_state(lambda state: define_concept(state, WARD, actor="owner", reason="有病区"))

    with pytest.raises(ConceptError) as refused:
        wiki.update_concept_state(lambda state: deprecate_concept(
            state, "Ward", actor="owner", reason="换掉", replacement="CareUnit"))

    assert refused.value.code == "concept_replacement_not_found"


def test_the_last_concept_may_not_be_deprecated():
    state = empty_concept_state()
    adopt_concept_pack(state, actor="owner", reason="起始包",
                       pack=ConceptSet((Concept("Ward", "病区", "Organization", "病区"),), "only-1"))

    with pytest.raises(ConceptError) as refused:
        deprecate_concept(state, "Ward", actor="owner", reason="不要了")

    assert refused.value.code == "concept_set_empty"
    assert concept_set_of(state).ids() == ("Ward",)


def test_a_decision_without_a_reason_is_refused(tmp_path):
    wiki = _wiki(tmp_path)

    with pytest.raises(ConceptError) as refused:
        wiki.update_concept_state(lambda state: define_concept(state, WARD, actor="owner", reason="  "))

    assert refused.value.code == "concept_reason_required"


def test_a_declared_concept_that_the_ledger_could_not_load_is_refused(tmp_path):
    wiki = _wiki(tmp_path)

    with pytest.raises(ConceptError) as refused:
        wiki.update_concept_state(lambda state: define_concept(
            state, Concept("Ward", "病区", "Ward", "病区"), actor="owner", reason="有床"))

    assert refused.value.code == "concept_meta_kind_unknown"
    assert wiki.concept_state()["versions"] == {}


def test_adopting_the_pack_makes_the_scope_own_its_concepts(tmp_path):
    wiki = _wiki(tmp_path)
    adopted = wiki.update_concept_state(
        lambda state: adopt_concept_pack(state, actor="owner", reason="本项目按标准的起始包走"))

    assert adopted["concept_count"] == 11
    assert concept_projection(wiki.concept_state())["declared"] is True
    assert wiki.concept_set().origin == "starter_pack"


def test_an_unreadable_concept_ledger_fails_closed(tmp_path):
    wiki = _wiki(tmp_path)
    wiki.update_concept_state(lambda state: define_concept(state, WARD, actor="owner", reason="有病区"))
    store_path = tmp_path / "workspace" / ".catalyst" / "wiki" / "ent" / "concepts" / "wiki.json"
    document = json.loads(store_path.read_text(encoding="utf-8"))
    document["concepts"]["active_version_id"] = "concepts-99"
    store_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    reopened = ProjectWiki(tmp_path / "workspace", [tmp_path / "sources"], enterprise_id="ent",
                           project_id="concepts")
    with pytest.raises(WikiUnavailable, match="concept state is unreadable"):
        reopened.concept_state()
    assert concept_state_is_valid(document["concepts"]) is False


def test_the_ledger_records_the_decision_that_made_it(tmp_path):
    (tmp_path / "sources").mkdir()
    code, defined = _cli(
        "ontology", "concepts", "define", *_common(tmp_path),
        "--concept-id", "Ward", "--name", "病区", "--meta-kind", "Organization",
        "--criteria", "病区、护理单元", "--reason", "医院资料里有病区")
    assert code == 0, defined

    code, refused = _cli(
        "ontology", "concepts", "define", *_common(tmp_path),
        "--concept-id", "Ward", "--name", "病区", "--meta-kind", "Organization",
        "--criteria", "病区", "--reason", "重复定义一次")
    assert code == 1
    assert refused["error"]["code"] == "concept_already_defined"

def _resolver(state):
    def resolve(value):
        concept = resolve_concept_in(state, value)
        return concept.concept_id if concept is not None else None
    return resolve


ENTRIES = [
    {"kind": "entity", "key": "ward_a", "meaning": "病区甲", "business_type": "Ward",
     "source_id": "s1", "line_start": 1, "span_sha256": "a"},
    {"kind": "entity", "key": "bed_a", "meaning": "床位甲", "business_type": "Bed",
     "source_id": "s1", "line_start": 2, "span_sha256": "b"},
]


def test_the_score_reads_a_type_against_the_scope_concept_set():
    state = empty_concept_state()
    define_concept(state, WARD, actor="owner", reason="医院资料里有病区")
    measured = {row["id"]: row for row in score_items(
        ENTRIES, sources={"s1": "病区甲\n床位甲\n"}, target={}, resolve_type=_resolver(state))["metrics"]}

    # Ward is the scope's; Bed is a spelling it never declared, so only one entity is typed.
    assert measured[2]["value"] == 0.5


def test_a_type_the_scope_retired_still_counts_for_what_it_typed():
    state = empty_concept_state()
    define_concept(state, WARD, actor="owner", reason="医院资料里有病区")
    deprecate_concept(state, "Ward", actor="owner", reason="改用护理单元", replacement="Department")
    measured = {row["id"]: row for row in score_items(
        ENTRIES, sources={"s1": "病区甲\n床位甲\n"}, target={}, resolve_type=_resolver(state))["metrics"]}

    assert measured[2]["value"] == 0.5
