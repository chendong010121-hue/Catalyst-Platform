"""One workbench, two knowledge scopes: the daily one, and a test result read-only.

The test scope is not merged into the daily one and cannot be written through the
workbench. What a reader can do there is read the whole modelling candidate -- including
the rows the hand-off did not carry -- and record a review disposition that binds the
candidate digest it was made under.
"""
from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.understand_wiki import UnderstandWikiAdapter
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workspace_ui import create_workspace_server

FIXTURE = Path(__file__).parent / "fixtures" / "u0_understand_handoff"
DAILY = "enterprise:synthetic/project:local-ui-demo"
TEST = "enterprise:synthetic/project:monthly"  # what the frozen hand-off declares


def _submit(wiki, gateway, root):
    frozen = json.loads((FIXTURE / "SemanticCandidate.json").read_text(encoding="utf-8-sig"))
    receipt = gateway.semantic_operation(
        operation="understand.candidate.submit",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"contract_version": "catalyst.understand_handoff.v1"},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).submit(frozen, declared_scope_id=wiki.scope_id),
    )
    return receipt["result"]["candidate_id"]


@pytest.fixture
def service(tmp_path):
    workspace = tmp_path / "workspace"
    inputs = workspace / "inputs"
    inputs.mkdir(parents=True)
    for path in (FIXTURE / "inputs").iterdir():
        shutil.copy2(path, inputs / path.name)
    test_wiki = ProjectWiki(workspace, [inputs], enterprise_id="synthetic",
                            project_id="monthly")
    candidate_id = _submit(test_wiki, CatalystGateway(workspace), inputs)

    state = test_wiki.semantic_state()
    result = state["candidates"][candidate_id]["understanding_result"]
    rows = [row for bucket in ("extracted_facts", "inferred_items", "unknowns")
            for row in (result.get(bucket) or [])]
    dropped_item = next(row["item_id"] for row in rows if row.get("item_id"))

    handoff = tmp_path / "handoff"
    handoff.mkdir()
    (handoff / "dropped.json").write_text(json.dumps(
        [{"item_key": dropped_item, "rule": "evidence_unresolved"}]), encoding="utf-8")
    (handoff / "receipt.json").write_text(json.dumps({"item_count": len(rows)}), encoding="utf-8")

    catalyst = workspace / ".catalyst"
    catalyst.mkdir(exist_ok=True)
    (catalyst / "scopes.json").write_text(json.dumps({"scopes": [
        {"scope_id": TEST, "label": "本体建模测试成果", "read_only": True}]}), encoding="utf-8")
    (catalyst / "run-products.json").write_text(json.dumps({"products": [{
        "product_id": "fixture-handoff", "label": "测试成果", "root": str(handoff),
        "scope_id": TEST, "candidate_id": candidate_id,
        "files": {"dropped": "dropped.json", "receipt": "receipt.json"}}]}), encoding="utf-8")

    server = create_workspace_server(workspace, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    with urlopen(base + "/api/config", timeout=30) as response:
        csrf = json.load(response)["csrf_token"]
    yield {"base": base, "workspace": workspace, "test_wiki": test_wiki,
           "candidate_id": candidate_id, "rows": rows, "csrf": csrf}
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _get(base, path):
    with urlopen(base + path, timeout=60) as response:
        return response.status, json.load(response)


def _post(base, csrf, body):
    request = Request(base + "/api/review-dispositions",
                      data=json.dumps(body).encode("utf-8"),
                      headers={"Content-Type": "application/json", "X-Catalyst-CSRF": csrf},
                      method="POST")
    with urlopen(request, timeout=60) as response:
        return response.status, json.load(response)


def test_the_test_scope_is_listed_as_read_only(service):
    status, body = _get(service["base"], "/api/knowledge-scopes")
    assert status == 200
    assert body["daily"] == DAILY
    by_id = {row["scope_id"]: row for row in body["scopes"]}
    assert by_id[DAILY]["read_only"] is False
    assert by_id[TEST]["read_only"] is True
    assert by_id[TEST]["has_store"] is True


def test_each_scope_lists_only_its_own_candidates(service):
    _s, daily = _get(service["base"], "/api/semantic/candidates")
    _s, test = _get(service["base"], "/api/semantic/candidates?scope=" + quote(TEST, safe=""))

    assert daily["scope_id"] == DAILY
    assert daily["candidates"] == []
    assert test["scope_id"] == TEST
    assert test["read_only"] is True
    ids = [row["candidate_id"] for row in test["candidates"]]
    # The hand-off also produced its typed candidate in the same scope; both are listed.
    assert service["candidate_id"] in ids
    assert any(row_id.startswith("candidate_") for row_id in ids)


def test_the_wiki_reader_reads_the_scope_it_was_asked_for(service):
    _s, model = _get(service["base"], "/api/wiki/model?scope=" + quote(TEST, safe=""))
    assert model["meta"]["scope"] == TEST
    # The scope has a store but no accepted version, so the reader shows its own skeleton
    # pages -- what matters here is that they are this scope's, not the daily one's.
    assert model["pages"]
    assert model["meta"]["store_index_sha256"]


def test_an_unknown_scope_is_named_instead_of_falling_back(service):
    with pytest.raises(HTTPError) as raised:
        _get(service["base"], "/api/semantic/candidates?scope=" + quote("enterprise:nope/project:nope", safe=""))
    assert raised.value.code == 404
    assert json.load(raised.value)["error"]["code"] == "scope_unknown"


def test_the_whole_candidate_is_readable_including_what_was_not_carried(service):
    status, body = _get(service["base"], "/api/run-products?scope=" + quote(TEST, safe=""))
    assert status == 200
    product = body["items"][0]
    assert product["readable"] is True
    assert product["counts"]["rows"] == len(service["rows"])
    assert product["counts"]["dropped"] == 1
    assert product["counts"]["carried"] == len(service["rows"]) - 1
    assert product["counts"]["receipt_item_count"] == len(service["rows"])
    dropped = [row for row in product["rows"] if row["status"] == "dropped"]
    assert dropped
    row = dropped[0]
    # The rule says why the row did not enter the candidate; it must not be read as a
    # diagnosis of the reference. The ladder states what is known, one fact per rung.
    assert row["rule"] == "evidence_unresolved"
    assert row["reason"] == "证据未解决（evidence_unresolved）"
    ladder = row["evidence"]
    assert ladder["declared"] >= 1
    assert 0 <= ladder["present"] <= ladder["declared"]
    assert ladder["original_readable"] is False
    ladder_counts = product["counts"]["dropped_ladder"]
    assert (ladder_counts["with_quote"] + ladder_counts["without_quote"]
            + ladder_counts["records_missing"]) == product["counts"]["dropped"]


def test_a_disposition_must_bind_the_digest_the_reader_saw(service):
    _s, candidates = _get(service["base"], "/api/semantic/candidates?scope=" + quote(TEST, safe=""))
    row = candidates["candidates"][0]
    with pytest.raises(HTTPError) as raised:
        _post(service["base"], service["csrf"], {
            "scope_id": TEST, "candidate_id": row["candidate_id"],
            "content_digest": "0" * 64, "action": "DEFERRED", "reason": "等待解释"})
    assert raised.value.code == 409
    assert json.load(raised.value)["error"]["code"] == "candidate_changed"


def test_a_disposition_is_recorded_with_a_receipt_and_can_be_withdrawn(service):
    _s, candidates = _get(service["base"], "/api/semantic/candidates?scope=" + quote(TEST, safe=""))
    row = candidates["candidates"][0]
    status, recorded = _post(service["base"], service["csrf"], {
        "scope_id": TEST, "candidate_id": row["candidate_id"],
        "content_digest": row["content_digest"], "action": "DEFERRED", "reason": "等待类型缺口解释"})
    assert status == 201
    receipt = recorded["receipt"]
    assert receipt["candidate_sha256"] == row["content_digest"]
    assert receipt["authority"] == "REVIEW_DISPOSITION_ONLY"
    assert len(receipt["line_sha256"]) == 64

    _s, view = _get(service["base"], "/api/review-dispositions?scope=" + quote(TEST, safe=""))
    assert [item["action"] for item in view["effective"]] == ["DEFERRED"]

    status, withdrawn = _post(service["base"], service["csrf"],
                              {"withdraw": recorded["record_id"], "reason": "改主意"})
    assert status == 201
    assert withdrawn["supersedes"] == recorded["record_id"]
    _s, after = _get(service["base"], "/api/review-dispositions?scope=" + quote(TEST, safe=""))
    assert after["effective"] == []
    assert [item["action"] for item in after["items"]] == ["DEFERRED", "WITHDRAWN"]


def test_a_disposition_never_writes_to_the_scope_or_creates_a_version(service):
    index = (service["workspace"] / ".catalyst" / "wiki" / "synthetic" / "monthly"
             / "wiki.json")
    before = index.read_bytes()
    before_state = service["test_wiki"].semantic_state()
    _s, candidates = _get(service["base"], "/api/semantic/candidates?scope=" + quote(TEST, safe=""))
    row = candidates["candidates"][0]
    _post(service["base"], service["csrf"], {
        "scope_id": TEST, "candidate_id": row["candidate_id"],
        "content_digest": row["content_digest"], "action": "REJECTED", "reason": "不接受"})

    assert index.read_bytes() == before
    after_state = service["test_wiki"].semantic_state()
    assert after_state["accepted_versions"] == before_state["accepted_versions"]
    assert after_state["decisions"] == before_state["decisions"]


# ------------------------------------------------------------------ item opinions

def _post_opinion(base, csrf, body):
    request = Request(base + "/api/review-item-opinions",
                      data=json.dumps(body).encode("utf-8"),
                      headers={"Content-Type": "application/json", "X-Catalyst-CSRF": csrf},
                      method="POST")
    with urlopen(request, timeout=60) as response:
        return response.status, json.load(response)


def _first_product(base):
    _s, body = _get(base, "/api/run-products?scope=" + quote(TEST, safe=""))
    product = next(item for item in body["items"] if item.get("readable"))
    return product


def test_an_opinion_binds_the_row_digest_the_reviewer_was_shown(service):
    product = _first_product(service["base"])
    row = product["rows"][0]
    assert len(row["digest"]) == 64
    before = service["test_wiki"].semantic_state()

    status, receipt = _post_opinion(service["base"], service["csrf"], {
        "scope_id": TEST, "candidate_id": product["candidate_id"], "item_id": row["item_id"],
        "content_digest": row["digest"], "stance": "question",
        "reason": "这一行的原句没有把工作挂到持有者身上"})
    assert status == 201
    assert receipt["receipt"]["stance"] == "question"

    _s, ledger = _get(service["base"],
                      "/api/review-item-opinions?scope=" + quote(TEST, safe="")
                      + "&candidate_id=" + quote(product["candidate_id"], safe=""))
    coverage = ledger["coverage"]
    assert coverage["items"] == len(product["rows"])
    assert coverage["with_opinion"] == 1
    assert coverage["still_question"] == 1
    assert coverage["uncovered"] == len(product["rows"]) - 1
    assert coverage["stale"] == 0

    after = service["test_wiki"].semantic_state()
    assert after["accepted_versions"] == before["accepted_versions"]
    assert after["decisions"] == before["decisions"]
    assert after["candidates"] == before["candidates"]


def test_an_opinion_whose_digest_no_longer_matches_is_refused(service):
    product = _first_product(service["base"])
    row = product["rows"][0]
    with pytest.raises(HTTPError) as caught:
        _post_opinion(service["base"], service["csrf"], {
            "scope_id": TEST, "candidate_id": product["candidate_id"], "item_id": row["item_id"],
            "content_digest": "0" * 64, "stance": "question", "reason": "看到的是旧内容"})
    assert caught.value.code == 409
    _s, ledger = _get(service["base"],
                      "/api/review-item-opinions?scope=" + quote(TEST, safe="")
                      + "&candidate_id=" + quote(product["candidate_id"], safe=""))
    assert ledger["items"] == []


def test_an_opinion_can_be_withdrawn_and_then_the_item_is_uncovered(service):
    product = _first_product(service["base"])
    row = product["rows"][0]
    _s, receipt = _post_opinion(service["base"], service["csrf"], {
        "scope_id": TEST, "candidate_id": product["candidate_id"], "item_id": row["item_id"],
        "content_digest": row["digest"], "stance": "reject", "reason": "这条与本页无关"})
    record_id = receipt["record_id"]
    _s, withdrawn = _post_opinion(service["base"], service["csrf"], {
        "withdraw": record_id, "reason": "探针写入撤回"})
    assert withdrawn["supersedes"] == record_id

    _s, ledger = _get(service["base"],
                      "/api/review-item-opinions?scope=" + quote(TEST, safe="")
                      + "&candidate_id=" + quote(product["candidate_id"], safe=""))
    assert ledger["effective"] == []
    assert ledger["coverage"]["with_opinion"] == 0
    assert ledger["coverage"]["uncovered"] == len(product["rows"])
    assert [item.get("action") for item in ledger["items"]] == [None, "WITHDRAWN"]


def test_an_opinion_saved_under_an_older_rule_is_named_not_covered(service):
    product = _first_product(service["base"])
    row = product["rows"][0]
    ledger_path = service["workspace"] / ".catalyst" / "review-item-opinions.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    # A record written before the digest covered the holder, the qualification and the
    # evidence: same row digest, no rule named. It must not count as coverage today.
    legacy = {"record_id": "opinion_legacy000000000000000000", "at": "2026-11-01T00:00:00+00:00",
              "authority": "local-workspace-note", "actor": "local-workspace-review",
              "scope_id": TEST, "candidate_id": product["candidate_id"],
              "item_id": row["item_id"], "content_digest": row["digest"],
              "stance": "question", "reason": "旧规则下留的意见"}
    with open(ledger_path, "ab") as stream:
        stream.write((json.dumps(legacy, ensure_ascii=False) + "\n").encode("utf-8"))

    _s, body = _get(service["base"],
                    "/api/review-item-opinions?scope=" + quote(TEST, safe="")
                    + "&candidate_id=" + quote(product["candidate_id"], safe=""))
    coverage = body["coverage"]
    assert coverage["legacy"] == 1
    assert coverage["with_opinion"] == 0
    assert coverage["still_question"] == 0
    assert coverage["stale"] == 0
    assert coverage["uncovered"] == len(product["rows"])
    assert "重新核对" in coverage["note"]


def test_an_opinion_needs_a_reason_and_a_known_stance(service):
    product = _first_product(service["base"])
    row = product["rows"][0]
    for body in ({"stance": "question", "reason": ""}, {"stance": "maybe", "reason": "说不清"}):
        with pytest.raises(HTTPError) as caught:
            _post_opinion(service["base"], service["csrf"], {
                "scope_id": TEST, "candidate_id": product["candidate_id"],
                "item_id": row["item_id"], "content_digest": row["digest"], **body})
        assert caught.value.code == 400
