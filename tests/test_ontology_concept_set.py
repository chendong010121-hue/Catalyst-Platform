"""Type has two levels: an upper kind the code fixes, and a concept a scope declares."""

from __future__ import annotations

import pytest

from catalyst_platform.ontology_types import (
    BUSINESS_TYPES,
    META_KINDS,
    STARTER_CONCEPTS,
    STARTER_PACK,
    Concept,
    ConceptError,
    ConceptSet,
    canonical_business_type,
    resolve_concept,
)
from catalyst_platform.understand_semantic import (
    _SEMANTIC_EXTRACTION_RULES,
    semantic_extraction_rules,
)

WARD = Concept("Ward", "病区", "Organization", "病区、护理单元：医院里独立收治的一段病床",
               aliases=("bingqu",))
PRODUCT = Concept("Product", "产品", "Artifact", "账户、额度、产品：银行对外提供的东西",
                  aliases=("product",))


def _scoped(*extra: Concept) -> ConceptSet:
    return ConceptSet((*STARTER_CONCEPTS, *extra), "scope-1", "declared")


def test_every_starter_concept_has_a_kind_and_every_kind_holds_one():
    assert {concept.meta_kind for concept in STARTER_CONCEPTS} == set(META_KINDS)


def test_the_starter_pack_is_still_the_eleven_of_the_standard():
    assert list(BUSINESS_TYPES) == [
        "Department", "Position", "Responsibility", "ProcessStep",
        "Deliverable", "Rule", "Exception", "Metric",
        "GovernanceBody", "BusinessUnit", "ExternalParty",
    ]
    assert STARTER_PACK.ids() == tuple(BUSINESS_TYPES)


def test_each_kind_names_the_published_term_it_stands_for():
    # An alignment label a reviewer can check, not a claim to have imported the standard.
    assert all(meta.grounding.strip() for meta in META_KINDS.values())
    assert META_KINDS["Role"].grounding.startswith("ArchiMate")


def test_a_concept_the_code_has_never_seen_resolves_without_a_commit():
    below = _scoped(WARD, PRODUCT)

    assert canonical_business_type("ward", below) == "Ward"
    assert canonical_business_type("bingqu", below) == "Ward"
    assert canonical_business_type("病区", below) == "Ward"
    # The same name still means nothing to a scope that never declared it.
    assert canonical_business_type("Ward") is None
    assert resolve_concept("Ward") is None


def test_the_prompt_lists_the_concepts_of_the_scope_not_the_pack():
    scoped = semantic_extraction_rules(_scoped(WARD))

    assert "Ward（病区，Organization）" in scoped
    assert "Department（部门，Organization）" in scoped
    assert "declared by this scope" in scoped
    assert "declared by this scope" not in _SEMANTIC_EXTRACTION_RULES
    # Every starter concept is still named in the default contract.
    assert all(concept_id in _SEMANTIC_EXTRACTION_RULES for concept_id in BUSINESS_TYPES)


def test_two_concepts_may_not_answer_to_one_spelling():
    with pytest.raises(ConceptError) as refused:
        ConceptSet((*STARTER_CONCEPTS, Concept("Ward", "部门", "Organization", "另一段床位")))

    assert refused.value.code == "concept_spelling_shared"


def test_one_id_may_not_appear_twice():
    with pytest.raises(ConceptError) as refused:
        ConceptSet((*STARTER_CONCEPTS, Concept("Department", "科室", "Organization", "科室")))

    assert refused.value.code == "concept_id_duplicated"


def test_a_concept_must_name_a_kind_of_the_model():
    with pytest.raises(ConceptError) as refused:
        ConceptSet((*STARTER_CONCEPTS, Concept("Bed", "床位", "Furniture", "床")))

    assert refused.value.code == "concept_meta_kind_unknown"


def test_a_declared_concept_set_round_trips_through_json():
    scoped = _scoped(WARD)
    restored = ConceptSet.from_dict(scoped.to_dict())

    assert restored.version_id == "scope-1"
    assert restored.origin == "declared"
    assert restored.resolve("ward") == WARD
    assert restored.concepts == scoped.concepts


def test_a_declared_row_without_a_kind_is_refused_by_name():
    with pytest.raises(ConceptError) as refused:
        Concept.from_dict({"concept_id": "Ward", "name": "病区", "criteria": "床位"})

    assert refused.value.code == "concept_meta_kind_unknown"
