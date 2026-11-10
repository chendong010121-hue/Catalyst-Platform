"""The Wiki product surface: list a native document, stage one file, withdraw it.

These tests cover what a user does from the local Workspace - open a native
document without an error, put one file into Wiki, and take it back out - and
they assert the boundary that matters: nothing here accepts knowledge.
"""

import base64
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from catalyst_platform.knowledge_intake import KnowledgeIntakeError, intake_source
from catalyst_platform.wiki import ProjectWiki, WikiScopeError
from catalyst_platform.workspace_ui import create_workspace_server
from tests.test_understand_only import _docx, _pptx_table, _text_pdf

MAKERS = {"_docx": _docx, "_pptx_table": _pptx_table, "_text_pdf": _text_pdf}
NATIVE_MAKERS = [("_docx", "docx"), ("_pptx_table", "pptx"), ("_text_pdf", "pdf")]
# Each body carries one name nobody has accepted yet: a staged document reaches the
# candidate layer only when there is something in it to propose.
NOVEL_BODIES = {
    "_docx": "新设数字化运营中心，负责集团数据资产。",
    "_pptx_table": "数字化运营中心",
    "_text_pdf": "HUARONG CAPITAL",
}


def _wiki(tmp_path, backend="sqlite"):
    root = tmp_path / "inputs"
    root.mkdir()
    wiki = ProjectWiki(
        tmp_path / "workspace",
        [root],
        enterprise_id="synthetic",
        project_id="surface",
        backend=backend,
    )
    return wiki, root


@pytest.mark.parametrize("maker,extension", NATIVE_MAKERS)
def test_native_source_is_listed_by_identity_not_as_missing(tmp_path, maker, extension):
    wiki, root = _wiki(tmp_path)
    source = root / f"policy.{extension}"
    MAKERS[maker](source)
    receipt = wiki.stage_native_source(source)

    row = wiki.read_knowledge("*", mode="source_discovery", limit=100)["documents"][0]

    assert row["source_id"] == receipt["source_id"]
    assert row["revision_status"] == "native_not_parsed"
    assert row["freshness_status"] == "fresh"
    assert row["knowledge_status"] == "current"
    assert row["source_format"] == extension
    assert row["content_status"] == "NOT_PARSED"
    assert row["title"] == "policy"


def test_withdrawing_a_source_stops_reads_and_search_but_keeps_its_history(tmp_path):
    wiki, root = _wiki(tmp_path)
    source = root / "policy.md"
    source.write_text("# Hiring\nRULE: the hiring board owns hiring.\n", encoding="utf-8")
    receipt = wiki.stage_markdown(source)
    assert wiki.search("hiring")["claims"]

    withdrawn = wiki.withdraw_source(receipt["source_id"])

    assert withdrawn["status"] == "withdrawn"
    assert withdrawn["withdrawn_claim_count"] == 1
    assert wiki.search("hiring")["claims"] == []
    assert wiki.read_knowledge("*", mode="source_discovery", limit=100)["documents"] == []
    history = wiki.claim_history(receipt["source_id"])
    assert [claim["status"] for claim in history] == ["WITHDRAWN"]
    assert wiki.source_snapshot(receipt["source_id"])["content"].startswith("# Hiring")
    assert wiki.withdraw_source(receipt["source_id"])["status"] == "no_op"


def test_registering_a_withdrawn_document_again_restores_it(tmp_path):
    wiki, root = _wiki(tmp_path)
    source = root / "policy.md"
    source.write_text("# Hiring\nRULE: the hiring board owns hiring.\n", encoding="utf-8")
    first = intake_source(wiki, source, source_root=root)
    wiki.withdraw_source(first["source"]["source_id"])
    assert wiki.search("hiring")["claims"] == []

    second = intake_source(wiki, source, source_root=root)

    assert second["source"]["status"] == "restored"
    assert wiki.search("hiring")["claims"]


def test_withdrawing_an_unknown_source_is_refused(tmp_path):
    wiki, _root = _wiki(tmp_path)
    with pytest.raises(WikiScopeError):
        wiki.withdraw_source("source_unknown")


def test_intake_stages_one_markdown_file_and_stops_at_the_candidate_layer(tmp_path):
    wiki, root = _wiki(tmp_path)
    source = root / "policy.md"
    source.write_text("# Hiring\nRULE: the hiring board owns hiring.\n", encoding="utf-8")

    result = intake_source(wiki, source, source_root=root)

    assert result["status"] == "CANDIDATE_STAGED"
    assert result["authority"] == "CANDIDATE_ONLY"
    assert result["evidence_count"] >= 1
    assert result["candidate"]["authority"] == "CANDIDATE_ONLY"
    assert result["candidate"]["mapping_status"] == "COMPLETE"
    assert wiki.semantic_state()["active_version_id"] is None
    assert wiki.semantic_state()["candidates"][result["candidate"]["candidate_id"]]["status"] == "PROPOSED"


@pytest.mark.parametrize("maker,extension", NATIVE_MAKERS)
def test_intake_lets_one_native_document_reach_the_candidate_layer(tmp_path, maker, extension):
    wiki, root = _wiki(tmp_path)
    source = root / f"evidence.{extension}"
    MAKERS[maker](source, text=NOVEL_BODIES[maker])

    result = intake_source(wiki, source, source_root=root)

    assert result["status"] == "CANDIDATE_STAGED"
    assert result["candidate"]["mapping_status"] == "COMPLETE"
    assert result["candidate"]["mapped_evidence_count"] == result["candidate"]["evidence_count"]
    assert wiki.semantic_state()["active_version_id"] is None
    # A native document never becomes source-level claims by being read.
    assert wiki.claim_history(result["source"]["source_id"]) == []
    # What intake can say about a native document is how far reading got, not what it means.
    record = wiki.source_record(result["source"]["source_id"])
    assert record["content_status"] == "PARSED"
    assert record["extraction"]["status"] == "complete"


def test_intake_refuses_a_format_wiki_does_not_hold(tmp_path):
    wiki, root = _wiki(tmp_path)
    source = root / "script.exe"
    source.write_bytes(b"not a document")
    with pytest.raises(KnowledgeIntakeError) as refused:
        intake_source(wiki, source, source_root=root)
    assert refused.value.code == "source_format_unsupported"


def test_workspace_stages_one_document_then_shows_and_withdraws_it(tmp_path):
    server = create_workspace_server(tmp_path / "ui", port=0, mode="BLOCKED")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def get(path):
        with urlopen(base + path, timeout=20) as response:
            return json.load(response)

    def post(path, payload):
        request = Request(
            base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Catalyst-CSRF": csrf},
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    try:
        csrf = get("/api/config")["csrf_token"]
        source = tmp_path / "blueprint.pdf"
        _text_pdf(source, "HUARONG CAPITAL")
        payload = {
            "name": "blueprint.pdf",
            "data_base64": base64.b64encode(source.read_bytes()).decode("ascii"),
        }

        status, staged = post("/api/knowledge/stage", payload)

        assert status == 201, staged
        assert staged["status"] == "CANDIDATE_STAGED"
        assert staged["candidate"]["authority"] == "CANDIDATE_ONLY"
        source_id = staged["source"]["source_id"]

        listed = get("/api/knowledge")["items"]
        row = next(item for item in listed if item["source_id"] == source_id)
        assert row["revision_status"] == "native_not_parsed"
        assert row["source_format"] == "pdf"

        document = get("/api/document?id=" + source_id)
        assert document["content"] is None
        assert document["preview_status"] == "NATIVE_DOCUMENT_NOT_PARSED"
        assert document["fresh"] is True
        assert document["authority"] == "NATIVE_SOURCE_IDENTITY_ONLY"

        # The candidate layer is visible where a reviewer looks, and it opens.
        candidate_id = staged["candidate"]["candidate_id"]
        reviews = get("/api/reviews")["items"]
        assert candidate_id in {row["candidate_id"] for row in reviews}
        assert all(row["can_accept"] is False for row in reviews)
        graph = get("/api/ontology?candidate_id=" + candidate_id)
        assert graph["view_tier"] == "candidate"
        assert graph["active_version_id"] is None
        assert get("/api/reviews")["active_version_id"] is None

        status, withdrawn = post("/api/knowledge/withdraw", {"source_id": source_id})

        assert status == 200 and withdrawn["status"] == "withdrawn"
        assert all(item["source_id"] != source_id for item in get("/api/knowledge")["items"])
        # The history stays readable after withdrawal; only reads and search stop.
        assert get("/api/document?id=" + source_id)["status"] == "WITHDRAWN"

        status, refused = post(
            "/api/knowledge/stage",
            {"name": "script.exe", "data_base64": base64.b64encode(b"x").decode("ascii")},
        )
        assert status == 400 and refused["error"]["code"] == "knowledge_upload_unsupported_format"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
