"""Ledger: levels, coverage and depth are derived, never written."""
import copy
import json
from pathlib import Path

import pytest

from catalyst_platform import capability_claim as cc
from catalyst_platform import capability_ledger as cl

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "examples" / "capability_claims"
OWNER_DIGEST = "a" * 64


def sample(name):
    return cc.load_claim(SAMPLES / f"{name}.claim.json")


def binding_for(claim, **kwargs):
    return cl.build_binding(claim, owner_digest=OWNER_DIGEST, **kwargs)


def row(**overrides):
    base = {
        "id": "ob-1",
        "statement": "x",
        "owner": {"kind": "self", "ref": "demo"},
        "evidence": ["e1"],
        "evidence_authority": ["QUOTED"],
        "proofs": [],
        "required_authority": "STRUCTURAL",
    }
    base.update(overrides)
    return base


def ledger_of(rows, status_contradictions=()):
    return {
        "ledger_version": 1,
        "subject": {"kind": "group", "key": "demo"},
        "members": [{"id": "demo", "version": "1", "claim_digest": "b" * 64, "owner_digest": OWNER_DIGEST,
                     "binding_digest": "c" * 64}],
        "obligations": rows,
        "contradictions": list(status_contradictions),
        "derived": {
            "obligations": [{"id": item["id"], "member": "demo", "level": cl.derive_level(item)} for item in rows],
            "coverage": cl.derive_coverage(rows),
            "status": cl.derive_status(rows, status_contradictions),
        },
    }


def test_binding_covers_every_obligation_with_an_owner():
    claim = sample("skill-porting")
    binding = binding_for(claim)
    assert len(binding["obligations"]) == len(claim["what"]["obligations"])
    assert {item["id"] for item in binding["obligations"]} == {
        f"ob-{index + 1}" for index in range(len(claim["what"]["obligations"]))
    }
    assert all(item["owner"] == {"kind": "self", "ref": "skill-porting"} for item in binding["obligations"])
    assert cl.validate_binding(binding, claim) == []


def test_binding_may_not_store_a_level():
    claim = sample("skill-porting")
    binding = binding_for(claim)
    binding["obligations"][0]["level"] = "VERIFIED"
    assert "binding:derived_field_stored:obligations[0].level" in cl.validate_binding(binding, claim)


def test_binding_statement_drift_is_refused():
    claim = sample("skill-porting")
    binding = binding_for(claim)
    binding["obligations"][1]["statement"] = "a different promise"
    assert "binding:statement_drift:ob-2" in cl.validate_binding(binding, claim)


def test_binding_is_tied_to_the_claim_that_produced_it():
    claim = sample("skill-porting")
    binding = binding_for(claim)
    assert cl.validate_binding(binding, copy.deepcopy(claim)) == []
    changed = copy.deepcopy(claim)
    changed["capability"]["statement"] = "changed"
    assert "binding:claim_digest_mismatch" in cl.validate_binding(binding, changed)


def test_owner_digest_must_be_a_digest():
    claim = sample("skill-porting")
    binding = cl.build_binding(claim, owner_digest="")
    assert "binding:owner_digest_missing" in cl.validate_binding(binding, claim)


@pytest.mark.parametrize(
    "evidence_authority,required,expected",
    [
        ([], "STRUCTURAL", "MISSING"),
        (["QUOTED"], "STRUCTURAL", "DECLARED"),
        (["STRUCTURAL"], "STRUCTURAL", "BOUND"),
        (["EXECUTED"], "STRUCTURAL", "VERIFIED"),
        (["MEASURED"], "MEASURED", "VERIFIED"),
        (["EXECUTED"], "MEASURED", "BOUND"),
    ],
)
def test_level_follows_the_authority_rung(evidence_authority, required, expected):
    assert cl.derive_level(row(evidence_authority=evidence_authority, required_authority=required)) == expected


def test_missing_owner_is_missing_whatever_the_evidence_says():
    assert cl.derive_level(row(owner={"kind": "none", "ref": ""}, evidence_authority=["MEASURED"])) == "MISSING"


def test_a_receipt_closes_what_a_quote_cannot():
    with_receipt = row(evidence_authority=["STRUCTURAL"], proofs=[{"id": "r1", "authority": "EXECUTED"}])
    assert cl.derive_level(with_receipt) == "VERIFIED"


def test_coverage_and_status_are_counted_not_guessed():
    rows = [
        row(id="ob-1", evidence_authority=["STRUCTURAL"]),
        row(id="ob-2", evidence_authority=["EXECUTED"]),
        row(id="ob-3", evidence_authority=[]),
    ]
    assert cl.derive_coverage(rows) == {"declared": 0, "bound": 1, "verified": 1, "missing": 1, "unowned": 0}
    assert cl.derive_status(rows) == "PARTIAL"
    assert cl.derive_status(rows[:2]) == "CLOSED"
    assert cl.derive_status(rows, ["drift"]) == "CONTRADICTED"


def test_a_stored_level_that_overstates_the_evidence_is_refused():
    rows = [row()]
    ledger = ledger_of(rows)
    ledger["derived"]["obligations"][0]["level"] = "VERIFIED"
    assert "ledger:derived_mismatch:obligations[0].level" in cl.validate_ledger(ledger)


def test_a_tampered_coverage_count_is_refused():
    ledger = ledger_of([row()])
    ledger["derived"]["coverage"]["bound"] = 99
    assert "ledger:derived_mismatch:coverage.bound" in cl.validate_ledger(ledger)


def test_a_tampered_status_is_refused():
    ledger = ledger_of([row(evidence_authority=[])])
    ledger["derived"]["status"] = "CLOSED"
    assert "ledger:derived_mismatch:status" in cl.validate_ledger(ledger)


def test_a_ledger_without_its_derived_block_is_refused():
    ledger = ledger_of([row()])
    ledger.pop("derived")
    assert cl.validate_ledger(ledger) == ["ledger:derived_missing"]


def test_raising_a_level_without_new_evidence_is_refused():
    before = ledger_of([row(evidence_authority=["QUOTED"])])
    after = ledger_of([row(evidence_authority=["STRUCTURAL"])])
    assert cl.revise_ledger(before, after) == ["level:raised_without_evidence:ob-1"]
    after["obligations"][0]["proofs"] = []
    with_new = copy.deepcopy(after)
    with_new["obligations"][0]["evidence"] = ["e1", "e2"]
    assert cl.revise_ledger(before, with_new) == []


def test_lowering_a_level_needs_a_receipt():
    before = ledger_of([row(evidence_authority=["EXECUTED"])])
    after = ledger_of([row(evidence_authority=["EXECUTED"], proofs=[])])
    after["obligations"][0]["evidence_authority"] = ["QUOTED"]
    assert cl.revise_ledger(before, after) == ["level:lowered_without_receipt:ob-1"]
    after["demotions"] = [{"id": "ob-1", "receipt": "run-7"}]
    assert cl.revise_ledger(before, after) == []


def test_depth_walks_from_identity_to_measurement():
    claim = sample("skill-porting")
    assert cl.derive_depth({"what": {}, "why": {}}) == "L0"
    assert cl.derive_depth(claim) == "L1"
    graphed = copy.deepcopy(claim)
    graphed["graph"] = {"steps": [{"id": "s1", "capability": "understand", "on_failure": "fail_fast"}]}
    assert cl.derive_depth(graphed) == "L2"
    assert cl.derive_depth(graphed, receipts=[{"status": "DONE"}]) == "L3"
    measured = copy.deepcopy(graphed)
    measured["why"]["evidence"][0]["strength"] = "MEASURED"
    assert cl.derive_depth(measured) == "L4"


def test_ledger_digest_ignores_the_derived_block():
    ledger = ledger_of([row()])
    digest = cl.ledger_digest(ledger)
    ledger["derived"]["coverage"]["bound"] = 0
    assert cl.ledger_digest(ledger) == digest


def test_a_member_claim_that_changed_after_the_ledger_was_built_is_refused():
    claim = sample("skill-porting")
    binding = binding_for(claim)
    ledger = cl.build_ledger({"kind": "group", "key": "port-external-package"}, [(claim, binding)])
    assert cl.validate_ledger(ledger, {"skill-porting": claim}) == []
    changed = copy.deepcopy(claim)
    changed["capability"]["version"] = "9.9.9"
    assert "ledger:member_claim_drift:skill-porting" in cl.validate_ledger(ledger, {"skill-porting": changed})


def test_next_evidence_must_name_an_obligation_that_exists():
    claim = sample("skill-porting")
    binding = binding_for(claim)
    ledger = cl.build_ledger({"kind": "group", "key": "port-external-package"}, [(claim, binding)])
    ledger["obligations"][0]["next_evidence"] = {
        "operation": "run", "subject_id": "ob-99", "requires_authority": "EXECUTED"
    }
    assert "ledger:next_evidence_unknown_subject:ob-1:ob-99" in cl.validate_ledger(ledger, {"skill-porting": claim})


def test_building_a_ledger_from_two_real_skills_closes_nothing_it_cannot_see():
    left, right = sample("skill-porting"), sample("plugin-porting")
    ledger = cl.build_ledger(
        {"kind": "group", "key": "port-external-package"},
        [(left, binding_for(left)), (right, binding_for(right))],
    )
    assert len(ledger["members"]) == 2
    assert len(ledger["obligations"]) == len(left["what"]["obligations"]) + len(right["what"]["obligations"])
    assert ledger["derived"]["coverage"]["declared"] >= 1
    assert ledger["derived"]["coverage"]["verified"] == 0
    assert cl.validate_ledger(ledger, {"skill-porting": left, "plugin-porting": right}) == []


def test_ledger_writes_only_json_safe_values():
    claim = sample("plugin-porting")
    ledger = cl.build_ledger({"kind": "group", "key": "port-external-package"}, [(claim, binding_for(claim))])
    assert json.loads(json.dumps(ledger)) == ledger
