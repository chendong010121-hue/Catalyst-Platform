"""The relation method ships with the Skill, so it has to reach the generation call.

The reference that carries it also carries the object-catalog contract this Port does not
speak: its head declares {summary,items,questions,limitations} and calls catalog objects the
only allowed endpoints, while this Port asks for entity rows and its own envelope. So the
assertions below are of two kinds - the guidance section is in front of the model, and the
contract around it is not.
"""
from pathlib import Path

from catalyst_platform.understand_manifest import _SKILL_ROOT
from catalyst_platform.understand_only import UnderstandPort
from tests.test_understand_capacity_and_endpoints import _Provider, _request, _rows, _source

RELATIONS = (_SKILL_ROOT / "understand-enterprise-semantics"
             / "references/ontology-catalog-relations-v2.md")


def _system(tmp_path: Path) -> str:
    provider = _Provider(lambda evidence_id: _rows(1, evidence_id))
    UnderstandPort().understand(_request(_source(tmp_path)), source_root=tmp_path,
                                semantic_provider=provider)
    return provider.requests[0].messages[0].content


def test_the_relation_method_reaches_the_generation_call(tmp_path: Path):
    system = _system(tmp_path)
    assert "ATOMIC_RELATION_COVERAGE_V1" in system
    assert "change polarity" in system
    assert "that same single proposition" in system


def test_the_catalog_contract_around_it_stays_out(tmp_path: Path):
    system = _system(tmp_path)
    # A head that says the catalog is the only source of endpoints would ask this Port for
    # a candidate it never accepts, so only the guidance section may travel.
    assert "SHARED_OBJECT_RELATIONS_V2" not in system
    assert "{summary,items,questions,limitations}" not in system.replace(" ", "")
    # The Port's own envelope still comes last, after both method bodies.
    assert "only top-level key is items" in system
    assert system.index("ATOMIC_RELATION_COVERAGE_V1") < system.index("only top-level key is items")


def test_the_method_in_the_call_is_the_shipped_file_not_a_copy(tmp_path: Path):
    # A copy beside the Port would drift from the file the Skill ships; this reads the file.
    shipped = RELATIONS.read_text(encoding="utf-8")
    section = shipped[shipped.index("ATOMIC_RELATION_COVERAGE_V1"):].strip()
    assert section in _system(tmp_path)


def test_the_modeling_method_comes_before_the_relation_method(tmp_path: Path):
    # The relation guidance refines the candidate the modeling method produces - it says
    # "the original candidate schema remains" - and the reference list sorts it first by
    # name, so the order of the request has to be decided by role rather than by file name.
    system = _system(tmp_path)
    assert system.index("# Method B") < system.index("ATOMIC_RELATION_COVERAGE_V1")
    assert system.index("ATOMIC_RELATION_COVERAGE_V1") < system.index("only top-level key is items")
