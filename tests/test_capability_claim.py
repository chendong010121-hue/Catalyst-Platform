"""Capability claim: every field is backed by evidence or declared unknown."""
import copy
import json
from pathlib import Path

import pytest

from catalyst_platform import capability_claim as cc

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "examples" / "capability_claims"


def sample(name):
    return cc.load_claim(SAMPLES / f"{name}.claim.json")


@pytest.fixture(params=["skill-porting", "plugin-porting"])
def claim(request):
    return sample(request.param)


def test_real_samples_validate(claim):
    assert cc.validate_claim(claim) == []


def test_samples_cover_the_same_shared_evidence_shape(claim):
    ids = [row["id"] for row in claim["why"]["evidence"]]
    assert ids == sorted(set(ids), key=ids.index)
    for row in claim["why"]["evidence"]:
        assert len(row["span_sha256"]) == 64
        assert cc.resolve_path(claim, row["field"])[0]


def test_missing_quick_start_is_a_schema_violation(claim):
    broken = copy.deepcopy(claim)
    broken.pop("quick_start")
    violations = cc.validate_claim(broken)
    assert any(item.startswith("schema:") and "required" in item for item in violations)


def test_dangling_evidence_reference_is_refused(claim):
    broken = copy.deepcopy(claim)
    broken["what"]["obligations"][0]["evidence"] = ["missing-id"]
    assert "evidence:dangling:what.obligations[0].evidence:missing-id" in cc.validate_claim(broken)


def test_item_without_evidence_must_be_declared_unknown(claim):
    broken = copy.deepcopy(claim)
    broken["what"]["failure_modes"][0]["evidence"] = []
    assert "claim:unbacked:what.failure_modes[0]" in cc.validate_claim(broken)


def test_declaring_an_absent_subfield_is_allowed(claim):
    """A field the source never mentions may be declared unknown."""
    more = copy.deepcopy(claim)
    more["why"]["unknowns"].append({"field": "what.latency", "reason": "source makes no latency claim"})
    assert cc.validate_claim(more) == []


def test_declaring_unknown_with_a_missing_parent_is_a_typo(claim):
    broken = copy.deepcopy(claim)
    broken["why"]["unknowns"].append({"field": "whatt.latency", "reason": "typo"})
    assert "unknown:parent_not_found:whatt.latency" in cc.validate_claim(broken)


def test_backed_and_unknown_at_once_is_a_contradiction(claim):
    broken = copy.deepcopy(claim)
    broken["why"]["unknowns"].append({"field": "what.obligations[0]", "reason": "contradiction"})
    assert "unknown:contradicts_evidence:what.obligations[0]" in cc.validate_claim(broken)


def test_evidence_pointing_outside_the_claim_is_refused(claim):
    broken = copy.deepcopy(claim)
    broken["why"]["evidence"][0]["field"] = "what.nothing_here[9]"
    assert "evidence:field_not_in_claim:what.nothing_here[9]" in cc.validate_claim(broken)


def test_unobservable_quick_start_must_say_why(claim):
    broken = copy.deepcopy(claim)
    broken["quick_start"]["observable"] = False
    assert "quick_start:unobservable_without_limitation" in cc.validate_claim(broken)
    broken["quick_start"]["limitation"] = "需要外部账号，离线无法复现"
    assert cc.validate_claim(broken) == []


def test_duplicate_evidence_ids_are_refused(claim):
    broken = copy.deepcopy(claim)
    broken["why"]["evidence"].append(copy.deepcopy(broken["why"]["evidence"][0]))
    assert any(item.startswith("evidence:duplicate_id:") for item in cc.validate_claim(broken))


def test_digest_is_stable_and_order_independent():
    first = sample("skill-porting")
    reordered = json.loads(json.dumps(first, sort_keys=False))
    assert cc.claim_digest(first) == cc.claim_digest(reordered)


def test_comparability_levels_separate_behaviour_from_text():
    assert cc.comparability_for("capability.id") == "exact"
    assert cc.comparability_for("how.interface") == "exact"
    assert cc.comparability_for("what.obligations[0]") == "normalized"
    assert cc.comparability_for("what.performance") == "behavioral"
    assert cc.comparability_for("something.else") == "behavioral"


def test_two_samples_share_a_responsibility_key_but_differ_in_applicability():
    left, right = sample("skill-porting"), sample("plugin-porting")
    assert left["capability"]["responsibility_key"] == right["capability"]["responsibility_key"]
    assert left["what"]["applicability"] != right["what"]["applicability"]
    assert left["quick_start"]["prompt"] != right["quick_start"]["prompt"]


# --- v2 fields: contract, requirements, obligation ids, anchors ---------------

SAMPLE_DIGESTS = {
    "skill-porting": "a84aa75ab7f99ff23ccafdb6aa4285617acb00a2a413ee544081fc26d4fdccfa",
    "plugin-porting": "4ecce00055f87480fd2fde8b92e0ee6f6474b525faf2603945fc909375cda9ac",
}


def enriched(name="skill-porting"):
    """A real sample carrying every v2 field, so the rules can be exercised."""
    claim = copy.deepcopy(sample(name))
    claim["capability"]["anchors"] = [
        {"object": "外部技能包", "action": "安装进本 Agent", "evidence": ["e1"]}
    ]
    claim["what"]["obligations"][0].update(
        {
            "id": "ob-1",
            "verifier": {"kind": "command", "detail": "python -m pytest tests/test_skill_porting.py"},
            "required_authority": "STRUCTURAL",
            "next_evidence": {"operation": "run", "subject_id": "ob-1", "requires_authority": "EXECUTED"},
        }
    )
    claim["what"]["inputs"][0].update({"form": "path", "required": True})
    claim["what"]["outputs"][0].update({"form": "path", "required": None})
    claim["how"]["invocation"] = {"mode": "prompt", "detail": "use skill-porting skill", "evidence": ["e1"]}
    claim["how"]["requirements"] = {
        "tools": ["Bash"],
        "secrets": [{"key": "GITHUB_TOKEN", "purpose": "读取外部仓库"}],
        "network": True,
        "writes": ["agent_state/skills"],
        "runtime": None,
        "mcp_servers": [{"name": "github", "transport": "http"}],
        "evidence": ["e1"],
    }
    claim["why"]["evidence"][0].update({"asserted_by": "claim-builder", "asserted_at": "2026-10-28T10:00:00Z"})
    return claim


@pytest.mark.parametrize("name", sorted(SAMPLE_DIGESTS))
def test_the_digest_of_a_real_sample_does_not_move(name):
    assert cc.claim_digest(sample(name)) == SAMPLE_DIGESTS[name]


def test_a_claim_carrying_every_v2_field_still_validates():
    claim = enriched()
    assert cc.validate_claim(claim) == []
    assert cc.claim_digest(claim) != SAMPLE_DIGESTS["skill-porting"]


def test_an_obligation_without_a_verifier_cannot_demand_an_execution():
    claim = enriched()
    claim["what"]["obligations"][0]["verifier"] = {"kind": "none"}
    assert "obligation:verifier_none_above_quoted:what.obligations[0]" in cc.validate_claim(claim)
    claim["what"]["obligations"][0]["required_authority"] = "QUOTED"
    assert cc.validate_claim(claim) == []


def test_an_unknown_form_must_be_declared():
    claim = enriched()
    claim["what"]["inputs"][0]["form"] = "unknown"
    assert "claim:form_unknown_not_declared:what.inputs[0].form" in cc.validate_claim(claim)
    claim["why"]["unknowns"].append({"field": "what.inputs[0].form", "reason": "来源没有说明输入形态"})
    assert cc.validate_claim(claim) == []


def test_an_unknown_invocation_mode_must_be_declared():
    claim = enriched()
    claim["how"]["invocation"] = {"mode": "unknown"}
    assert "claim:invocation_unknown_not_declared:how.invocation.mode" in cc.validate_claim(claim)
    claim["why"]["unknowns"].append({"field": "how.invocation.mode", "reason": "来源没有说明怎么调用"})
    assert cc.validate_claim(claim) == []


def test_a_pasted_secret_value_is_refused():
    claim = enriched()
    claim["how"]["requirements"]["tools"] = ["sk-abcdefgh12345678"]
    assert "secret:literal_value:how.requirements.tools[0]" in cc.validate_claim(claim)


def test_a_secret_is_recorded_by_key_name_only():
    claim = enriched()
    claim["how"]["requirements"]["secrets"] = [{"key": "sk-live-abc", "purpose": "x"}]
    violations = cc.validate_claim(claim)
    assert any(item.startswith("schema:how/requirements/secrets/0/key") for item in violations)


def test_next_evidence_must_name_something_that_exists():
    claim = enriched()
    claim["what"]["obligations"][0]["next_evidence"] = {
        "operation": "run",
        "subject_id": "ob-9",
        "requires_authority": "EXECUTED",
    }
    assert "next_evidence:unknown_subject:what.obligations[0]:ob-9" in cc.validate_claim(claim)


def test_next_evidence_may_name_a_declared_unknown_instead_of_an_obligation():
    claim = enriched()
    claim["why"]["unknowns"].append({"field": "what.cost", "reason": "来源没有成本声明"})
    claim["what"]["obligations"][0]["next_evidence"] = {
        "operation": "measure",
        "subject_id": "what.cost",
        "requires_authority": "MEASURED",
    }
    assert cc.validate_claim(claim) == []


def test_raising_an_evidence_strength_in_place_is_refused():
    before = enriched()
    after = copy.deepcopy(before)
    after["why"]["evidence"][0]["strength"] = "MEASURED"
    assert cc.evidence_carryover_violations(before, after) == ["evidence:rewritten:e1:strength"]


def test_rewriting_a_quote_in_place_is_refused():
    before = enriched()
    after = copy.deepcopy(before)
    after["why"]["evidence"][0]["quote"] = after["why"]["evidence"][0]["quote"] + " tail"
    assert "evidence:rewritten:e1:quote" in cc.evidence_carryover_violations(before, after)


def test_adding_a_receipt_is_the_way_to_raise_authority():
    before = enriched()
    after = copy.deepcopy(before)
    after["why"]["evidence"].append(
        {
            "id": "e99",
            "source_id": "run:7",
            "revision": "run-7",
            "locator": "receipt.json",
            "quote": "installed into agent_state/skills/demo",
            "span_sha256": "0" * 64,
            "strength": "EXECUTED",
            "asserted_by": "executor",
            "asserted_at": "2026-10-28T11:00:00Z",
            "field": "what.outputs[0]",
        }
    )
    assert cc.evidence_carryover_violations(before, after) == []
    assert cc.validate_claim(after) == []


def test_withdrawing_an_evidence_record_is_allowed():
    """Dropping a record is how a claim disowns something; only rewriting is refused."""
    before = enriched()
    after = copy.deepcopy(before)
    after["why"]["evidence"] = [row for row in after["why"]["evidence"] if row["id"] != "e1"]
    assert [item for item in cc.evidence_carryover_violations(before, after) if "e1" in item] == []


