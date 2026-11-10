"""An edge the page's arrangement gave, and a finding that takes itself back.

live40 was refused on four fifths of nothing: 36 of its 43 relations were read off a page's
layout rather than off a sentence, the Port stores those as unconfirmed, and the review
refused every one of them with "no sentence names both ends" - the very fact the card
already states. Nothing in the candidate claimed they were established. A card made of an
organisation chart can therefore never pass, whatever it says, unless the review is told
what an unconfirmed edge is for.

The other half of the same run: one finding was filed as `hard_stop` with a reason that ended
"本项撤销" - it withdrew itself and still held the card. Both are readings the review decides,
so both are stated in the contract, and these tests hold the two halves together: the Port
marks the unconfirmed count as a local check, and the contract says what to do with it.
"""
import json
from types import SimpleNamespace

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import verify_candidate


class _Verifier:
    model = "verifier-fixture"
    structured_output_token_limit = 16384

    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return ModelResponse(content=json.dumps({"verdict": "REVIEWABLE", "findings": []}),
                             finish_reason="stop")


def _reviewed():
    item = SimpleNamespace(key="kexin_jiance_shu_shiye", kind="relation", meaning="科信检测隶属专业化子公司",
                           evidence_class="inferred", uncertainty=None, subject="kexin_jiance",
                           object="zhuanyehua_zigongsi", predicate="隶属", relation_source="LAYOUT",
                           evidence_refs=())
    result = SimpleNamespace(semantic_candidate=SimpleNamespace(items=(item,)), evidence_refs=(),
                             request_id="layout",
                             producer_attribution={"relation_verification": {"confirmed": 3,
                                                                             "unconfirmed": 36}})
    verifier = _Verifier()
    verify_candidate(result, verifier, goal="整理职责")
    payload = json.loads(verifier.requests[0].messages[-1].content)
    system = " ".join(verifier.requests[0].messages[0].content.split())
    return payload, system


def test_the_port_tells_the_reviewer_how_many_edges_are_unconfirmed():
    payload, _ = _reviewed()
    [check] = [row for row in payload["local_checks"] if row["rule"] == "layout_relation_unconfirmed"]
    assert check["counts"] == {"confirmed": 3, "unconfirmed": 36}


def test_an_unconfirmed_edge_may_stand_and_is_judged_only_when_it_is_claimed():
    _, system = _reviewed()
    assert "A relation whose `relation_source` is LAYOUT is stored as unconfirmed" in system
    assert "report it only where the candidate presents it as established" in system
    assert "where a conclusion is built on it" in system


def test_a_finding_that_withdraws_itself_is_not_a_finding():
    _, system = _reviewed()
    assert "a finding you withdraw while writing it is not a finding" in system
    assert "Nothing withdrawn can be a hard_stop" in system
