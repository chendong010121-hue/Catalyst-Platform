"""A row the Port folds away is not a row the extraction lost.

live40 was the first card a verifier ever read, and it could not have passed whatever the
review said: its integrity carried `relation_duplicated_by_entity_merge: 10`, and the gate
reads any entry under `dropped_invalid_items` as "this candidate lost rows". A row lost
that way is the same sentence held twice because two names turned out to be one thing, so
a deck that names a thing twice - every real deck - could never produce a reviewable card.

The counters are now split: what the extraction lost stays under `dropped_invalid_items`
and still caps the verdict, and what the Port folded away is reported beside it under
`dropped_derived_by_entity_merge` and does not. These tests take both sides of that line.
"""
import json
from types import SimpleNamespace

import pytest

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import SemanticVerificationError, verify_candidate


class _Verifier:
    model = "verifier-fixture"
    structured_output_token_limit = 16384

    def __init__(self, verdict="REVIEWABLE"):
        self.verdict = verdict
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return ModelResponse(content=json.dumps({"verdict": self.verdict, "findings": []}),
                             finish_reason="stop")


def _candidate(dropped):
    item = SimpleNamespace(key="finance", kind="entity", meaning="财务部门",
                           evidence_class="observed_from_source", uncertainty=None,
                           subject=None, object=None, evidence_refs=())
    return SimpleNamespace(semantic_candidate=SimpleNamespace(items=(item,)), evidence_refs=(),
                           request_id="folded",
                           producer_attribution={"dropped_invalid_items": dict(dropped)})


def _integrity(verifier):
    return json.loads(verifier.requests[0].messages[-1].content)["integrity"]


def test_a_relation_folded_by_a_name_merge_does_not_cap_the_verdict():
    verifier = _Verifier("REVIEWABLE")
    record = verify_candidate(_candidate({"relation_duplicated_by_entity_merge": 10,
                                          "relation_collapsed_by_entity_merge": 2}),
                              verifier, goal="整理职责")
    assert record["verdict"] == "REVIEWABLE" and record["clamped_by"] == []
    # Still counted and still told to the reviewer - only not as a loss.
    assert record["integrity"]["dropped_invalid_items"] == {}
    assert record["integrity"]["dropped_derived_by_entity_merge"] == {
        "relation_duplicated_by_entity_merge": 10, "relation_collapsed_by_entity_merge": 2}


def test_a_row_the_extraction_lost_still_caps_the_verdict():
    verifier = _Verifier("REVIEWABLE")
    with pytest.raises(SemanticVerificationError) as raised:
        verify_candidate(_candidate({"entity_name_not_in_evidence": 1,
                                     "relation_duplicated_by_entity_merge": 10}),
                         verifier, goal="整理职责")
    # The model said REVIEWABLE and returned no finding: the capped verdict is the Port's.
    assert raised.value.verdict == "REVISE" and raised.value.findings == ()
    # The two kinds are told apart on both sides of the split.
    assert _integrity(verifier)["dropped_invalid_items"] == {"entity_name_not_in_evidence": 1}
    assert _integrity(verifier)["dropped_derived_by_entity_merge"] == {
        "relation_duplicated_by_entity_merge": 10}


def test_the_review_is_told_the_folded_rows_are_not_a_loss():
    verifier = _Verifier()
    verify_candidate(_candidate({"relation_duplicated_by_entity_merge": 3}), verifier,
                     goal="整理职责")
    system = " ".join(verifier.requests[0].messages[0].content.split())
    assert "`dropped_derived_by_entity_merge` is reported beside the losses and is not one" in system
    assert "a card is not incomplete for them" in system
