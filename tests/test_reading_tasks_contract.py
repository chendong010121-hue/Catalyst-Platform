"""What the reading tasks need on screen: a name, an admission, and what is still unsettled.

These are contract tests, not layout tests: every answer they ask for comes from a field the
store already holds. A missing answer is written as missing, never filled in by the projection.
"""
from __future__ import annotations

import pytest

from catalyst_platform import wiki_model
from catalyst_platform.wiki_pages import project

from test_wiki_pages import VersionedWiki, meaning


BASIS = {
    "receipt_id": "receipt_234e8d232b06e385eeca3b23",
    "receipt_type": "owner_authority",
    "issuer_id": "test-owner",
    "authority_class": "test_only",
    "issued_at": 1760000000,
    "expires_at": 1900000000,
}


def _version(*, basis):
    entity = meaning("m1", "entity", "marketing_center", "市场营销中心",
                     canonical_id="c1", business_type="Department")
    version = {
        "version_id": "version_p1", "parent_version_id": None, "candidate_id": "candidate_p1",
        "decision_id": "decision_p1", "source_id": "source_a", "source_revision": "r1",
        "authority_class": "test_only", "confirmed_by_absence_count": 0,
        "meanings": {entity["meaning_id"]: entity},
        "diff": None,
    }
    if basis is not None:
        version["owner_acceptance_basis"] = basis
    return entity, version


def _wiki(tmp_path, *, basis=BASIS):
    entity, version = _version(basis=basis)
    return VersionedWiki(tmp_path, [entity], [], version=version)


def _version_page(wiki):
    return next(page for page in project(wiki).pages if page.path == "versions/version_p1.md")


def test_a_version_page_shows_the_basis_it_was_admitted_with(tmp_path):
    page = _version_page(_wiki(tmp_path))
    assert "业务批准依据：" in page.content
    assert "receipt_234e8d232b06e385eeca3b23" in page.content
    assert "test-owner" in page.content
    assert "不等于企业 Owner 批准" in page.content


def test_a_version_page_with_no_basis_writes_that_it_has_none(tmp_path):
    page = _version_page(_wiki(tmp_path, basis=None))
    assert "authority_class: \"test_only\"" in page.content
    assert "业务批准依据：未记录业务批准依据" in page.content
    assert "receipt_" not in page.content.split("## 改了什么")[0]


def test_the_model_reports_the_active_admission_and_its_basis(tmp_path):
    model = wiki_model.build(_wiki(tmp_path))
    authority = model["meta"]["authority"]
    assert authority["version_id"] == "version_p1"
    assert authority["authority_class"] == "test_only"
    assert authority["acceptance_basis_state"] == "recorded"
    assert authority["acceptance_basis"]["issuer_id"] == "test-owner"


def test_a_missing_basis_is_reported_as_missing_not_as_none(tmp_path):
    model = wiki_model.build(_wiki(tmp_path, basis=None))
    authority = model["meta"]["authority"]
    assert authority["acceptance_basis_state"] == "missing"
    assert authority["acceptance_basis"] is None


def test_the_version_page_carries_the_same_state_as_the_model(tmp_path):
    model = wiki_model.build(_wiki(tmp_path))
    page = next(row for row in model["pages"] if row["path"] == "versions/version_p1.md")
    assert page["fields"]["authority_class"] == "test_only"
    assert page["fields"]["owner_acceptance_basis"] == "recorded"
    assert page["fields"]["acceptance_basis_issuer"] == "test-owner"
