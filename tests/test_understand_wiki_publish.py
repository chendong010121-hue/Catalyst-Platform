"""A publish is judged by what it introduces, never by what it inherited."""
import hashlib

import pytest

from catalyst_platform.understand_wiki import (
    UnderstandWikiError,
    ensure_publishable,
    entry_errors,
    introduced_errors,
    stored_publish_entries,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _entry(key, *, kind="claim", meaning="职责说明", quote="财务部门负责月度经营分析。",
           span=None, evidence=True):
    row = {"kind": kind, "key": key, "meaning": meaning}
    if evidence:
        row["evidence"] = {"line_start": 1, "line_end": 1, "quote": quote,
                           "span_sha256": span if span is not None else _sha(quote)}
    return row


def test_a_clean_set_has_no_errors():
    assert entry_errors([_entry("duty")]) == []


def test_a_quote_that_does_not_hash_to_its_span_is_named_field_by_field():
    [row] = entry_errors([_entry("duty", span="0" * 64)])
    assert (row["item_key"], row["field"], row["code"]) == ("duty", "evidence.span_sha256", "span_sha256_mismatch")
    assert row["message"]


def test_a_publish_that_inherits_a_stored_defect_is_not_blocked_by_it():
    stored = [_entry("duty", span="0" * 64)]
    publishing = [_entry("duty", span="0" * 64), _entry("team", kind="entity", meaning="财务部门")]
    report = ensure_publishable(stored, publishing)
    assert report["blocked"] is False
    assert report["counts"] == {"introduced": 0, "carried_over": 1}
    # The inherited defect is reported, not silently accepted.
    assert report["carried_over"][0]["code"] == "span_sha256_mismatch"


def test_a_publish_that_introduces_one_bad_reference_is_refused_with_the_row():
    stored = [_entry("duty")]
    publishing = [_entry("duty"), _entry("team", kind="entity", meaning="财务部门", span="f" * 64)]
    with pytest.raises(UnderstandWikiError) as raised:
        ensure_publishable(stored, publishing)
    assert raised.value.code == "introduced_errors"
    [row] = raised.value.report["introduced"]
    assert (row["item_key"], row["field"], row["code"]) == ("team", "evidence.span_sha256", "span_sha256_mismatch")


def test_missing_evidence_duplicate_keys_and_empty_meanings_are_all_named():
    rows = entry_errors([
        _entry("duty", evidence=False),
        _entry("duty"),
        _entry("blank", meaning="  "),
    ])
    assert {row["code"] for row in rows} == {"evidence_missing", "duplicate_key", "empty_meaning"}
    assert all(set(row) == {"item_key", "field", "code", "message"} for row in rows)


def test_an_entry_of_the_wrong_shape_is_one_error_and_not_a_crash():
    rows = entry_errors(["not an entry"])
    assert [row["code"] for row in rows] == ["entry_not_an_object"]


def test_a_row_read_back_from_the_ledger_counts_as_evidence_and_is_not_a_defect():
    """The ledger keeps the passage by digest, so a stored row must not read as evidenceless."""
    stored = [{"kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析。",
               "evidence": {"line_start": 1, "line_end": 1, "span_sha256": _sha("原文")}}]
    assert entry_errors(stored) == []


def test_a_blank_quote_is_still_missing_evidence_even_with_a_digest():
    rows = entry_errors([{"kind": "claim", "key": "duty", "meaning": "职责",
                          "evidence": {"line_start": 1, "line_end": 1, "quote": "   ",
                                       "span_sha256": _sha("原文")}}])
    assert [row["code"] for row in rows] == ["evidence_missing"]


def test_two_relations_are_told_apart_by_the_endpoints_they_join():
    def relation(subject, predicate, object_):
        return {"kind": "relation", "subject": subject, "predicate": predicate, "object": object_,
                "evidence": {"line_start": 1, "line_end": 1, "quote": "批复", "span_sha256": _sha("批复")}}

    assert entry_errors([relation("@finance", "reports_to", "@board"),
                         relation("@board", "reports_to", "@group")]) == []
    [row] = entry_errors([relation("@finance", "reports_to", "@board"),
                          relation("@finance", "reports_to", "@board")])
    assert (row["code"], row["item_key"]) == ("duplicate_key", "@finance|reports_to|@board")


def _candidate(source_id, *entries):
    return {"candidate_id": f"candidate_{source_id}", "source_id": source_id, "entries": list(entries)}


def test_the_stored_set_names_each_key_once_across_candidates():
    state = {"candidates": {
        "c_1": _candidate("src_1", {"kind": "claim", "key": "duty", "meaning": "职责",
                                    "line_start": 1, "line_end": 1, "span_sha256": _sha("原文")}),
        "c_2": _candidate("src_2", {"kind": "claim", "key": "duty", "meaning": "另一份材料里的职责",
                                    "line_start": 3, "line_end": 3, "span_sha256": _sha("原文")}),
    }}
    rows = stored_publish_entries(state)
    assert len(rows) == 1
    assert entry_errors(rows) == []


def test_a_publish_over_a_stored_ledger_passes_when_it_adds_nothing_broken():
    state = {"candidates": {"c_1": _candidate("src_1", {
        "kind": "entity", "key": "finance", "canonical_key": "finance", "meaning": "财务部门",
        "line_start": 2, "line_end": 2, "span_sha256": _sha("财务部门")})}}
    report = ensure_publishable(stored_publish_entries(state), [
        _entry("duty"), _entry("team", kind="entity", meaning="财务部门")])
    assert report["blocked"] is False
    assert report["counts"] == {"introduced": 0, "carried_over": 0}


def test_a_publish_over_a_stored_ledger_is_refused_for_the_defect_it_adds():
    state = {"candidates": {"c_1": _candidate("src_1", {
        "kind": "claim", "key": "duty", "meaning": "职责",
        "line_start": 1, "line_end": 1, "span_sha256": _sha("原文")})}}
    with pytest.raises(UnderstandWikiError) as raised:
        ensure_publishable(stored_publish_entries(state),
                           [_entry("duty"), _entry("team", kind="entity", meaning="财务部门", span="f" * 64)])
    assert [row["code"] for row in raised.value.report["introduced"]] == ["span_sha256_mismatch"]
