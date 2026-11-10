"""An entity no concept of the scope classifies keeps its row, and the missing kind is named.

The type segment of the prompt used to end with "a thing that fits none of the 11 is a claim,
not an entity". On V6 that sentence is what turned a staff group and two specialty lines into
`Position`, and a working group into `Position` as well: the answer had to give every entity
one of the eleven, so it gave the nearest one. The contract now says the opposite - the row
keeps its entity, leaves business_type out, and the kind it would have needed is recorded by
name. A gap the answer did not state is recorded as unstated: never filled with the nearest
type, and never turned back into a claim.
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.ontology_types import STARTER_PACK
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = ("分公司其他员工：负责分公司项目具体执行\n"
        "市场营销专业条线\n"
        "组织升级小组\n"
        "分公司经理\n")


class _Answer:
    model = "stub-type-gap"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _evidence(evidence, name):
    return next(item["evidence_id"] for item in evidence if name in item["quote"])


def _run(tmp_path, build):
    source = tmp_path / "org.md"
    source.write_text(TEXT, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("type-gap", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_type_gap",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _entity(evidence, key, name, **extra):
    row = {"kind": "entity", "key": key, "meaning": name, "evidence_class": "SOURCE_DIRECT",
           "evidence_refs": [_evidence(evidence, name)]}
    row.update(extra)
    return row


# --- positive: the entity stays, the gap is named -------------------------------------------

def test_an_unclassified_entity_keeps_its_row_and_names_the_gap(tmp_path):
    """The source supports the group; none of the eleven classifies it; the row stays a row."""
    def build(evidence):
        return [_entity(evidence, "qita_yuangong", "分公司其他员工",
                        uncertainty="type_gap: 员工群体（现有 11 个概念都不涵盖）")]

    result = _run(tmp_path, build)
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    attribution = result.producer_attribution

    assert entity.meaning == "分公司其他员工"
    assert entity.business_type is None
    assert entity.evidence_class == "observed_from_source"
    assert entity.evidence_refs
    assert attribution["type_gaps_count"] == 1
    assert attribution["type_gaps_unnamed_count"] == 1
    assert attribution["type_gaps_without_note_count"] == 0
    gap = attribution["type_gaps"][0]
    # The note is recorded as what it is - something the producer wrote - not as proof
    # that the gap was explained.
    assert (gap["item_key"], gap["name"], gap["named_kind"], gap["has_note"]) == \
        ("qita_yuangong", "分公司其他员工", None, True)


def test_a_type_the_set_does_not_hold_keeps_the_row_and_names_the_kind(tmp_path):
    """Naming a kind the scope lacks is a decision the scope has not made, not a defect."""
    def build(evidence):
        return [_entity(evidence, "shichang_tiaoxian", "市场营销专业条线", business_type="SpecialtyLine")]

    result = _run(tmp_path, build)
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    attribution = result.producer_attribution

    assert (entity.kind, entity.business_type) == ("entity", None)
    assert attribution["concept_unmapped"] == [{"spelling": "SpecialtyLine", "entities": 1}]
    gap = attribution["type_gaps"][0]
    assert (gap["name"], gap["named_kind"], gap["has_note"]) == \
        ("市场营销专业条线", "SpecialtyLine", False)


# --- negative: nothing is filled in, nothing is turned into a claim -------------------------

def test_an_untyped_entity_with_no_note_is_recorded_as_unstated_not_degraded(tmp_path):
    """No type and no note is still a gap: recorded, and the row is not demoted for it."""
    def build(evidence):
        return [_entity(evidence, "zuzhi_shengji_xiaozu", "组织升级小组")]

    result = _run(tmp_path, build)
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    attribution = result.producer_attribution

    assert entity.kind == "entity"
    assert entity.business_type is None
    assert entity.evidence_class == "observed_from_source"
    assert attribution["type_gaps_count"] == 1
    assert attribution["type_gaps_unnamed_count"] == 1
    assert attribution["type_gaps_without_note_count"] == 1
    assert attribution["item_contract_degraded"] == []


def test_a_held_type_is_canonicalised_and_records_no_gap(tmp_path):
    """A concept the set holds is not a gap, whatever letter the answer used."""
    def build(evidence):
        return [_entity(evidence, "fen_gongsi_jingli", "分公司经理", business_type="position")]

    result = _run(tmp_path, build)
    entity = next(item for item in result.semantic_candidate.items if item.kind == "entity")
    attribution = result.producer_attribution

    assert entity.business_type == "Position"
    assert attribution["type_gaps_count"] == 0


def test_a_claim_that_no_concept_classifies_is_not_promoted_and_not_a_gap(tmp_path):
    """A sentence about a list stays the claim it is; a gap only exists for an entity."""
    def build(evidence):
        return [{"kind": "claim", "key": "c_list", "meaning": "市场营销专业条线由市场部管理",
                 "evidence_class": "SOURCE_DIRECT",
                 "evidence_refs": [_evidence(evidence, "市场营销专业条线")]}]

    result = _run(tmp_path, build)
    row = next(item for item in result.semantic_candidate.items if item.key == "c_list")

    assert row.kind == "claim"
    assert result.producer_attribution["type_gaps_count"] == 0


# --- the contract the request carries -------------------------------------------------------

def test_the_prompt_keeps_an_unclassified_entity_and_never_calls_it_a_claim():
    rules = STARTER_PACK.prompt_rules()

    assert "keeps its row" in rules
    assert "leaves business_type out" in rules
    assert "names in uncertainty the kind" in rules
    assert "is not a claim" in rules
    assert "is a claim, not an entity" not in rules


def test_the_request_carries_the_type_contract_it_was_checked_against(tmp_path):
    """A positive example carried end to end: the contract reaches the model's system text."""
    def build(evidence):
        return [_entity(evidence, "qita_yuangong", "分公司其他员工",
                        uncertainty="type_gap: 员工群体")]

    provider = _Answer(build)
    source = tmp_path / "org.md"
    source.write_text(TEXT, encoding="utf-8")
    UnderstandPort().understand(
        UnderstandingRequest("type-gap-request", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_type_gap_request",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=provider)

    system = provider.requests[0].messages[0].content
    assert "leaves business_type out" in system
    assert "is a claim, not an entity" not in system


def test_more_than_twenty_gaps_are_all_listed_and_the_remainder_is_counted(tmp_path):
    """Knowing a gap exists but not which row it is on is the thing a ledger must never do."""
    names = [f"员工群体{i}" for i in range(25)]
    text = chr(10).join(f"{name}：负责本条线的具体执行" for name in names) + chr(10)

    def build(evidence):
        return [_entity(evidence, f"group_{i}", name) for i, name in enumerate(names)]

    source = tmp_path / "org.md"
    source.write_text(text, encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("type-gap-limit", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_type_gap_limit",
                             requested_depth="semantic", budget_steps=8),
        source_root=tmp_path, semantic_provider=_Answer(build))
    attribution = result.producer_attribution

    assert attribution["type_gaps_count"] == 25
    assert len(attribution["type_gaps"]) == 25
    assert attribution["type_gaps_omitted"] == 0
    assert attribution["type_gaps_without_note_count"] == 25
