"""Earlier units' identifiers come back as a hint, so one fact keeps one key.

The merge chooses between two rows that share a key by keeping the first, which is
why a deck that names the same department on six slides produced six keys for it.
The hint offers the names already taken — never their meaning, never their evidence —
so a later unit can describe the same thing in its own words and still land on one key.
"""
import json

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    _key_reuse_hint,
)


class _TwoUnits:
    """One entity per source, each named in its own text."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, second_key="legal", second_meaning=None, prefixed=False):
        self.second_key = second_key
        self.second_meaning = second_meaning
        self.prefixed = prefixed
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        if len(self.requests) == 1:
            key, meaning = "finance", "财务部门"
        else:
            key, meaning = self.second_key, {"legal": "法务部门", "finance": "财务部门"}[self.second_key]
            meaning = self.second_meaning or meaning
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": ("entity:" + key) if self.prefixed else key,
             "meaning": meaning,
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}]},
            ensure_ascii=False), finish_reason="stop")


def _run(tmp_path, provider):
    first = tmp_path / "a.md"
    first.write_text("财务部门负责月度经营分析。", encoding="utf-8")
    second = tmp_path / "b.md"
    second.write_text("法务部门复核合同预算，财务部门配合。", encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("hints", "整理职责", source_refs=(first, second),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)


def test_the_hint_says_nothing_about_meaning_or_evidence():
    assert _key_reuse_hint([]) == ""
    hint = _key_reuse_hint(["finance"])
    assert "finance" in hint
    assert "financial" not in hint.casefold()


def test_no_unit_is_offered_the_identifiers_another_unit_used(tmp_path):
    provider = _TwoUnits()
    result = _run(tmp_path, provider)
    first, second = provider.requests
    assert "Identifiers already used" not in first.messages[0].content
    # Measured on three cards: the hint cost coverage and produced names the store
    # could not take, so the hint is no longer sent.
    assert "Identifiers already used" not in second.messages[0].content
    assert result.producer_attribution["key_reuse_hints"] == 0


def test_a_key_the_model_spells_kind_colon_key_is_read_as_the_key(tmp_path):
    provider = _TwoUnits(prefixed=True)
    result = _run(tmp_path, provider)
    entities = [item.key for item in result.semantic_candidate.items if item.kind == "entity"]
    assert entities == ["finance", "legal"]


def test_a_quote_mark_around_the_same_name_is_not_a_second_meaning(tmp_path):
    provider = _TwoUnits(second_key="finance", second_meaning="「财务部门」")
    result = _run(tmp_path, provider)
    assert result.producer_attribution["duplicate_items_dropped"] == 1
    assert result.producer_attribution["duplicate_items_conflicting_meaning"] == []


def test_a_key_the_model_offers_twice_merges_into_one_item_and_is_not_a_conflict(tmp_path):
    provider = _TwoUnits(second_key="finance")
    result = _run(tmp_path, provider)
    assert [item.key for item in result.semantic_candidate.items if item.kind == "entity"] == ["finance"]
    # The same thing said twice under one key merges, and says nothing new.
    assert result.producer_attribution["duplicate_items_dropped"] == 1
    assert result.producer_attribution["duplicate_items_conflicting_meaning"] == []
