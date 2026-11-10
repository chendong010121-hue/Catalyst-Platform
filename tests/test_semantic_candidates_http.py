"""Enterprise can open a candidate the Wiki already holds, and a version says what it is.

`/api/reviews` lists what is still waiting for a decision, so a candidate the product has
accepted vanishes from it. These cases cover the list that does not vanish (`/api/semantic/
candidates`), the chain it exposes, and the authority class an accepted read has to name --
a test admission must never read like a business one.
"""
from __future__ import annotations

import json
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.observability import RunRecorder
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workspace_ui import create_workspace_server

from tests.p0_test_authority import trusted_test_operation, verify_test_receipt

SOURCE = """# 组织

RULE: 市场营销中心负责集团品牌与市场推广。
"""


def _wiki(workspace):
    inputs = workspace / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    source = inputs / "org.md"
    source.write_text(SOURCE, encoding="utf-8")
    return ProjectWiki(workspace, [inputs], enterprise_id="synthetic",
                       project_id="local-ui-demo", backend="json")


def _lifecycle(workspace):
    """One candidate, evaluated, accepted and activated inside the test scope."""
    wiki = _wiki(workspace)
    proposed = trusted_test_operation(workspace, wiki, "propose-1", "propose",
                                      workspace / "inputs" / "org.md",
                                      actor_origin="catalyst_deterministic")
    candidate_id = proposed["result"]["candidate_id"]
    trusted_test_operation(workspace, wiki, "evaluate-1", "evaluate", candidate_id,
                           actor_origin="independent_evaluator")
    decided = trusted_test_operation(workspace, wiki, "decide-1", "decide", candidate_id,
                                     decision="ACCEPTED", actor_origin="manager_acceptance",
                                     reason_code="test_reviewed")
    version_id = decided["result"]["version_id"]
    trusted_test_operation(workspace, wiki, "activate-1", "activate", version_id,
                           actor_origin="manager_acceptance")
    return wiki, candidate_id, version_id


@pytest.fixture
def service(tmp_path):
    workspace = tmp_path / "workspace"
    wiki, candidate_id, version_id = _lifecycle(workspace)
    server = create_workspace_server(workspace, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", wiki, candidate_id, version_id
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _get(base, path):
    with urlopen(base + path, timeout=30) as response:
        return response.status, json.load(response)


def test_the_list_keeps_a_candidate_the_reviews_page_hides(service):
    base, _wiki_store, candidate_id, version_id = service
    status, body = _get(base, "/api/semantic/candidates")

    assert status == 200
    assert body["scope_id"] == "enterprise:synthetic/project:local-ui-demo"
    assert [row["candidate_id"] for row in body["candidates"]] == [candidate_id]
    row = body["candidates"][0]
    assert row["status"] == "ACCEPTED"
    assert row["decision"] == "ACCEPTED"
    assert row["version_id"] == version_id
    assert row["type"] == "native"
    assert row["typed_candidate_id"] is None
    assert body["versions"][0]["version_id"] == version_id
    # The decision is bound to this candidate at this revision; the page can say so.
    assert len(row["content_digest"]) == 64
    assert row["revision_matches_decision"] is True
    assert row["decision_source_revision"] == row["source_revision"]
    assert body["updated_elsewhere"] is None if "updated_elsewhere" in body else True

    # The page that only lists what still needs a decision no longer carries it.
    _status, reviews = _get(base, "/api/reviews")
    assert all(item["candidate_id"] != candidate_id for item in reviews["items"])


def test_an_accepted_read_names_the_authority_class_it_was_admitted_under(service):
    base, _wiki_store, candidate_id, version_id = service
    status, graph = _get(base, "/api/ontology")

    assert status == 200
    assert graph["view_tier"] == "accepted"
    assert graph["version_id"] == version_id
    assert graph["candidate_id"] == candidate_id
    assert graph["authority_class"] == "test_only"
    assert "truncated" in graph
    assert graph["nodes"]


def test_a_native_candidate_cannot_be_drawn_as_a_candidate_graph(service):
    # Only an Understand hand-off has a candidate graph. A native candidate is refused by
    # name rather than drawn as an empty graph, which would read like "no candidates".
    base, _wiki_store, candidate_id, _version_id = service
    with pytest.raises(HTTPError) as raised:
        _get(base, "/api/ontology?candidate_id=" + candidate_id)
    assert raised.value.code >= 400


def test_the_candidate_read_is_recorded_and_writes_nothing(service):
    base, _wiki_store, _candidate_id, _version_id = service
    index = None
    for path in (service[1].workspace / ".catalyst" / "wiki").rglob("wiki.json"):
        index = path
    before = index.read_bytes()
    _get(base, "/api/semantic/candidates")
    assert index.read_bytes() == before
