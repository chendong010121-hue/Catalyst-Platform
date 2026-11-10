"""A run product is read as it was run, and a review disposition binds what was read.

The counts here are the point: 380 rows, 296 delivered and 84 not, and the 84 carry the
run's own reason instead of a re-derivation from text. A disposition is not an acceptance;
it names the candidate digest it was made under and a later change makes it stale.
"""
from __future__ import annotations

import json

import pytest

from catalyst_platform.review_surface import (
    ReadingError,
    ReviewDispositions,
    declared_products,
    product_rows,
    registered_scopes,
)

DAILY = "enterprise:synthetic/project:local-ui-demo"
TEST = "enterprise:synthetic-joint/project:m1-test-scope"


def _workspace(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / ".catalyst").mkdir(parents=True)
    return workspace


def _declare(workspace, scopes=None, products=None):
    if scopes is not None:
        (workspace / ".catalyst" / "scopes.json").write_text(
            json.dumps({"scopes": scopes}, ensure_ascii=False), encoding="utf-8")
    if products is not None:
        (workspace / ".catalyst" / "run-products.json").write_text(
            json.dumps({"products": products}, ensure_ascii=False), encoding="utf-8")


def test_the_daily_scope_is_the_only_writable_one(tmp_path):
    workspace = _workspace(tmp_path)
    store = workspace / ".catalyst" / "wiki" / "synthetic-joint" / "m1-test-scope"
    store.mkdir(parents=True)
    (store / "wiki.json").write_text("{}", encoding="utf-8")
    _declare(workspace, [{"scope_id": TEST, "label": "本体建模测试成果", "read_only": True}])

    body = registered_scopes(workspace, DAILY)

    assert body["daily"] == DAILY
    daily, declared = body["scopes"]
    assert daily["read_only"] is False and daily["role"] == "daily"
    assert declared["read_only"] is True and declared["has_store"] is True


def test_a_declaration_cannot_redeclare_the_daily_scope(tmp_path):
    workspace = _workspace(tmp_path)
    _declare(workspace, [{"scope_id": DAILY, "label": "重复", "read_only": True}])
    with pytest.raises(ReadingError) as raised:
        registered_scopes(workspace, DAILY)
    assert raised.value.code == "declaration_invalid"


def test_a_declared_scope_without_a_store_is_not_opened(tmp_path):
    workspace = _workspace(tmp_path)
    _declare(workspace, [{"scope_id": TEST, "label": "空的", "read_only": True}])
    body = registered_scopes(workspace, DAILY)
    assert body["scopes"][1]["has_store"] is False


def test_a_product_row_keeps_the_runs_own_reason(tmp_path):
    root = tmp_path / "handoff"
    root.mkdir()
    (root / "dropped.json").write_text(json.dumps([
        {"item_key": "item_1", "rule": "evidence_unresolved"},
        {"item_key": "item_2", "rule": "absence_without_scope"},
    ]), encoding="utf-8")
    (root / "receipt.json").write_text(json.dumps({"item_count": 4}), encoding="utf-8")
    product = {"product_id": "p", "label": "测试成果", "root": str(root), "scope_id": TEST,
               "candidate_id": "understand_" + "a" * 24, "note": None,
               "files": {"dropped": {"name": "dropped.json", "sha256": "x", "bytes": 1},
                         "receipt": {"name": "receipt.json", "sha256": "x", "bytes": 1}}}
    result = {
        "extracted_facts": [{"item_id": "item_1", "kind": "entity", "meaning": "甲"},
                            {"item_id": "item_3", "kind": "duty", "meaning": "乙"}],
        "inferred_items": [{"item_id": "item_4", "kind": "relation", "meaning": "丙"}],
        "unknowns": [{"item_id": "item_2", "kind": "unknown", "meaning": "丁"}],
    }

    detail = product_rows(product, result)

    assert detail["counts"]["rows"] == 4
    assert detail["counts"]["carried"] == 2
    assert detail["counts"]["dropped"] == 2
    assert detail["counts"]["dropped_unaccounted"] == 0
    assert detail["counts"]["by_rule"] == {"evidence_unresolved": 1, "absence_without_scope": 1}
    dropped = [row for row in detail["rows"] if row["status"] == "dropped"]
    assert all(row["reason"] and row["reason"] != row["rule"] for row in dropped)
    assert detail["counts"]["receipt_item_count"] == 4


def test_a_dropped_row_the_candidate_does_not_hold_is_named_not_hidden(tmp_path):
    root = tmp_path / "handoff"
    root.mkdir()
    (root / "dropped.json").write_text(json.dumps([
        {"item_key": "item_missing", "rule": "evidence_unresolved"}]), encoding="utf-8")
    product = {"product_id": "p", "label": "测试成果", "root": str(root), "scope_id": TEST,
               "candidate_id": "understand_" + "a" * 24, "note": None,
               "files": {"dropped": {"name": "dropped.json", "sha256": "x", "bytes": 1}}}
    detail = product_rows(product, {"extracted_facts": [{"item_id": "item_1", "kind": "entity"}]})
    # The run named a row the candidate does not hold: the row it does hold reads as
    # carried, and the disagreement is reported instead of being folded into a count.
    assert detail["counts"]["dropped_declared"] == 1
    assert detail["counts"]["dropped"] == 0
    assert detail["counts"]["carried"] == 1
    assert detail["counts"]["dropped_unaccounted"] == 1
    assert detail["unaccounted"] == ["item_missing"]


def test_a_product_must_point_at_a_candidate_that_exists(tmp_path):
    workspace = _workspace(tmp_path)
    root = tmp_path / "handoff"
    root.mkdir()
    (root / "dropped.json").write_text("[]", encoding="utf-8")
    _declare(workspace, products=[{"product_id": "p", "label": "测试成果", "root": str(root),
                                   "scope_id": TEST, "candidate_id": "not-a-candidate",
                                   "files": {"dropped": "dropped.json"}}])
    with pytest.raises(ReadingError) as raised:
        declared_products(workspace)
    assert raised.value.code == "declaration_invalid"


def test_a_product_file_may_not_leave_its_own_directory(tmp_path):
    workspace = _workspace(tmp_path)
    root = tmp_path / "handoff"
    root.mkdir()
    (tmp_path / "outside.json").write_text("[]", encoding="utf-8")
    _declare(workspace, products=[{"product_id": "p", "label": "测试成果", "root": str(root),
                                   "scope_id": TEST, "candidate_id": "understand_" + "a" * 24,
                                   "files": {"dropped": "..\\outside.json"}}])
    with pytest.raises(ReadingError) as raised:
        declared_products(workspace)
    assert raised.value.code == "declaration_invalid"


def test_a_disposition_binds_the_digest_it_was_made_under(tmp_path):
    workspace = _workspace(tmp_path)
    ledger = ReviewDispositions(workspace)
    digest = "a" * 64

    first = ledger.record(scope_id=TEST, candidate_id="understand_" + "b" * 24,
                          content_digest=digest, action="DEFERRED", reason="等待类型缺口解释")
    assert first["receipt"]["candidate_sha256"] == digest
    assert first["receipt"]["authority"] == "REVIEW_DISPOSITION_ONLY"
    again = ledger.record(scope_id=TEST, candidate_id="understand_" + "b" * 24,
                          content_digest=digest, action="DEFERRED", reason="等待类型缺口解释")
    assert again["duplicate"] is True
    assert len(ledger.records()) == 1

    view = ledger.view(scope_id=TEST)
    assert [row["action"] for row in view["effective"]] == ["DEFERRED"]

    withdrawal = ledger.withdraw(record_id=first["record_id"], reason="改主意")
    assert withdrawal["supersedes"] == first["record_id"]
    after = ledger.view(scope_id=TEST)
    assert after["effective"] == []
    assert [row["action"] for row in after["items"]] == ["DEFERRED", "WITHDRAWN"]


def test_a_disposition_needs_a_reason_and_a_digest(tmp_path):
    ledger = ReviewDispositions(_workspace(tmp_path))
    with pytest.raises(ReadingError) as raised:
        ledger.record(scope_id=TEST, candidate_id="understand_" + "b" * 24,
                      content_digest="a" * 64, action="REJECTED", reason="  ")
    assert raised.value.code == "disposition_reason_required"
    with pytest.raises(ReadingError) as raised:
        ledger.record(scope_id=TEST, candidate_id="understand_" + "b" * 24,
                      content_digest="short", action="REJECTED", reason="理由")
    assert raised.value.code == "disposition_digest_invalid"


def test_withdrawing_something_unknown_is_refused(tmp_path):
    ledger = ReviewDispositions(_workspace(tmp_path))
    with pytest.raises(ReadingError) as raised:
        ledger.withdraw(record_id="disposition_missing", reason="理由")
    assert raised.value.code == "disposition_unknown"
