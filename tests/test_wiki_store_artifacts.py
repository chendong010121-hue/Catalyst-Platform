"""The store keeps a version's meanings beside it, and the index only names them."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from catalyst_platform import wiki_cold_read
from catalyst_platform.wiki import ProjectWiki, WikiUnavailable
from catalyst_platform.wiki_cold_read import cold_read
from catalyst_platform.wiki_pages import Page, PageSet, link_report, materialize, project

SOURCE_REVISION = "a" * 64
SPAN_SHA256 = "b" * 64
CANDIDATE_ID = "candidate_artifact_1"
EVALUATION_ID = "evaluation_artifact_1"
DECISION_ID = "decision_artifact_1"
VERSION_ID = "version_artifact_1"
MEANING_ID = "meaning_artifact_review_gate"


def _meaning(meaning_id: str = MEANING_ID) -> dict:
    evidence = {
        "source_id": "source_review",
        "source_revision": SOURCE_REVISION,
        "claim_id": None,
        "line_start": 1,
        "line_end": 1,
        "span_sha256": SPAN_SHA256,
        "evidence_class": "observed_from_source",
    }
    return {
        "meaning_id": meaning_id,
        "kind": "rule",
        "key": "review_gate",
        "meaning": "a review requires a source link",
        "source_id": "source_review",
        "source_revision": SOURCE_REVISION,
        "claim_id": None,
        "line_start": 1,
        "line_end": 1,
        "span_sha256": SPAN_SHA256,
        "evidence_class": "observed_from_source",
        "evidence": [evidence],
    }


def _scope_id() -> str:
    return "enterprise:ent/project:proj"


def _legacy_document() -> dict:
    """A document exactly as the previous release wrote it: every payload inline, schema 1."""
    meaning = _meaning()
    scope_id = _scope_id()
    return {
        "schema_version": 1,
        "scope_id": scope_id,
        "sources": {},
        "claims": {},
        "semantic": {
            "schema_version": 1,
            "candidates": {
                CANDIDATE_ID: {
                    "candidate_id": CANDIDATE_ID,
                    "scope_id": scope_id,
                    "source_id": "source_review",
                    "source_revision": SOURCE_REVISION,
                    "parent_version_id": None,
                    "proposer_origin": "codex_fixture",
                    "entries": [meaning],
                    "status": "PROPOSED",
                    "created_run_id": "run_propose",
                    "latest_evaluation_id": EVALUATION_ID,
                    "latest_decision_id": DECISION_ID,
                }
            },
            "evaluations": {
                EVALUATION_ID: {"evaluation_id": EVALUATION_ID, "candidate_id": CANDIDATE_ID, "status": "pass"}
            },
            "decisions": {
                DECISION_ID: {
                    "decision_id": DECISION_ID,
                    "candidate_id": CANDIDATE_ID,
                    "source_id": "source_review",
                    "source_revision": SOURCE_REVISION,
                    "evaluation_id": EVALUATION_ID,
                    "external_evaluation_id": "external_artifact_1",
                    "decision": "ACCEPTED",
                    "actor_origin": "manager_acceptance",
                    "reason_code": "reviewed",
                    "owner_acceptance_basis": None,
                    "created_run_id": "run_accept",
                    "version_id": VERSION_ID,
                }
            },
            "accepted_versions": {
                VERSION_ID: {
                    "version_id": VERSION_ID,
                    "parent_version_id": None,
                    "candidate_id": CANDIDATE_ID,
                    "source_id": "source_review",
                    "source_revision": SOURCE_REVISION,
                    "decision_id": DECISION_ID,
                    "scope_id": scope_id,
                    "meanings": {MEANING_ID: meaning},
                    "confirmed_by_absence_count": 0,
                    "structural_evaluation_id": EVALUATION_ID,
                    "external_evaluation_id": "external_artifact_1",
                    "owner_acceptance_basis": None,
                    "authority_class": "test_only",
                    "created_run_id": "run_accept",
                }
            },
            "active_version_id": VERSION_ID,
            "transitions": [
                {
                    "transition_id": "transition_artifact_1",
                    "run_id": "run_accept",
                    "operation": "candidate.decide",
                    "status": "committed",
                }
            ],
        },
    }


def _append_transition(state: dict, index: int) -> None:
    state["transitions"].append(
        {
            "transition_id": f"transition_artifact_{index}",
            "run_id": f"run_artifact_{index}",
            "operation": "candidate.propose",
            "status": "committed",
        }
    )


def _scope_root(workspace) -> "object":
    return workspace / ".catalyst" / "wiki" / "ent" / "proj"


def _wiki(tmp_path, backend: str = "json", name: str = "workspace") -> ProjectWiki:
    workspace = tmp_path / name
    roots = tmp_path / f"{name}-sources"
    roots.mkdir(parents=True, exist_ok=True)
    return ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj", backend=backend)


def test_a_read_alone_leaves_an_older_store_untouched(tmp_path):
    wiki = _wiki(tmp_path)
    store_path = _scope_root(wiki.workspace) / "wiki.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    legacy = json.dumps(_legacy_document())
    store_path.write_text(legacy, encoding="utf-8")

    state = wiki.semantic_state()

    assert state["schema_version"] == 2
    assert state["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["key"] == "review_gate"
    assert store_path.read_text(encoding="utf-8") == legacy
    assert not (_scope_root(wiki.workspace) / "versions").exists()


def test_a_write_puts_meanings_and_entries_beside_the_index(tmp_path):
    wiki = _wiki(tmp_path)
    store_path = _scope_root(wiki.workspace) / "wiki.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(_legacy_document()), encoding="utf-8")

    wiki.update_semantic_state(lambda state: _append_transition(state, 2))

    index = json.loads(store_path.read_text(encoding="utf-8"))
    assert index["schema_version"] == 2
    assert index["semantic"]["schema_version"] == 2
    meanings = index["semantic"]["accepted_versions"][VERSION_ID]["meanings"]
    assert list(meanings) == ["_artifact"]
    descriptor = meanings["_artifact"]
    # The file name carries its own digest: different bytes cannot land on committed content.
    assert descriptor["path"].startswith(f"versions/{VERSION_ID}/meanings.")
    assert descriptor["path"].endswith(".jsonl")
    assert descriptor["sha256"][:16] in descriptor["path"]
    assert descriptor["kind"] == "mapping"
    assert descriptor["key_field"] == "meaning_id"
    assert descriptor["count"] == 1
    entries = index["semantic"]["candidates"][CANDIDATE_ID]["entries"]["_artifact"]
    assert entries["path"].startswith(f"candidates/{CANDIDATE_ID}/entries.")
    assert entries["kind"] == "sequence"
    assert entries["count"] == 1

    stored = (_scope_root(wiki.workspace) / descriptor["path"]).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["meaning_id"] for line in stored] == [MEANING_ID]
    assert "a review requires a source link" not in store_path.read_text(encoding="utf-8")

    reloaded = wiki.semantic_state()
    assert reloaded["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["meaning"] == "a review requires a source link"
    assert reloaded["candidates"][CANDIDATE_ID]["entries"] == [_meaning()]
    assert reloaded["transitions"][-1]["transition_id"] == "transition_artifact_2"


def test_a_missing_or_altered_artifact_fails_closed(tmp_path):
    wiki = _wiki(tmp_path)
    store_path = _scope_root(wiki.workspace) / "wiki.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(_legacy_document()), encoding="utf-8")
    wiki.update_semantic_state(lambda state: _append_transition(state, 2))
    meanings_path = _artifact_file(wiki)
    original = meanings_path.read_bytes()

    meanings_path.unlink()
    with pytest.raises(WikiUnavailable, match="missing a stored artifact"):
        wiki.semantic_state()

    meanings_path.write_bytes(original.replace(b"review_gate", b"review_gat3"))
    with pytest.raises(WikiUnavailable, match="does not match its recorded digest"):
        wiki.semantic_state()

    meanings_path.write_bytes(original)
    assert wiki.semantic_state()["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["key"] == "review_gate"


def test_an_unchanged_payload_is_not_rewritten(tmp_path):
    wiki = _wiki(tmp_path)
    store_path = _scope_root(wiki.workspace) / "wiki.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(_legacy_document()), encoding="utf-8")
    wiki.update_semantic_state(lambda state: _append_transition(state, 2))

    meanings_path = _artifact_file(wiki, "version")
    entries_path = _artifact_file(wiki, "entries")
    before = (meanings_path.stat().st_mtime_ns, entries_path.stat().st_mtime_ns)

    wiki.update_semantic_state(lambda state: _append_transition(state, 3))

    assert (meanings_path.stat().st_mtime_ns, entries_path.stat().st_mtime_ns) == before


def test_the_sqlite_backend_migrates_in_place_and_keeps_payloads_inline(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")
    legacy = _legacy_document()

    def seed(state):
        state.update(legacy["semantic"])
        _append_transition(state, 2)

    wiki.update_semantic_state(seed)

    database = _scope_root(wiki.workspace) / "wiki.sqlite3"
    with sqlite3.connect(database) as connection:
        payload = connection.execute("SELECT payload FROM wiki_state").fetchone()[0]
    stored = json.loads(payload)
    assert stored["schema_version"] == 2
    assert stored["semantic"]["schema_version"] == 2
    assert stored["semantic"]["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["key"] == "review_gate"
    assert not (_scope_root(wiki.workspace) / "versions").exists()
    assert wiki.semantic_state()["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["meaning"] == (
        "a review requires a source link"
    )

def test_every_payload_shape_round_trips_through_its_own_file(tmp_path):
    from catalyst_platform.wiki import _hydrate_document, _split_document

    document = _legacy_document()
    candidate = document["semantic"]["candidates"][CANDIDATE_ID]
    candidate["understanding_result"] = {"items": [{"item_id": "item_artifact_1"}]}
    candidate["evidence_mappings"] = [{"evidence_id": "evidence_artifact_1", "mapping_status": "MAPPED"}]
    root = tmp_path / "store"
    root.mkdir()

    index = _split_document(document, root)

    assert index["schema_version"] == 2
    result = index["semantic"]["candidates"][CANDIDATE_ID]["understanding_result"]["_artifact"]
    mappings = index["semantic"]["candidates"][CANDIDATE_ID]["evidence_mappings"]["_artifact"]
    assert result["path"].startswith(f"candidates/{CANDIDATE_ID}/understanding_result.")
    assert result["path"].endswith(".json")
    assert mappings["path"].startswith(f"candidates/{CANDIDATE_ID}/evidence_mappings.")
    assert mappings["path"].endswith(".jsonl")
    assert (root / result["path"]).is_file() and (root / mappings["path"]).is_file()
    hydrated = _hydrate_document(index, root)
    assert hydrated["semantic"]["candidates"][CANDIDATE_ID]["entries"] == [_meaning()]
    assert hydrated["semantic"]["candidates"][CANDIDATE_ID]["understanding_result"] == {"items": [{"item_id": "item_artifact_1"}]}
    assert hydrated["semantic"]["candidates"][CANDIDATE_ID]["evidence_mappings"] == [
        {"evidence_id": "evidence_artifact_1", "mapping_status": "MAPPED"}
    ]
    assert hydrated["semantic"]["accepted_versions"][VERSION_ID]["meanings"] == {MEANING_ID: _meaning()}

def test_a_store_deeper_than_the_windows_path_limit_still_round_trips(tmp_path):
    deep = tmp_path
    while len(str(deep / "workspace" / ".catalyst" / "wiki" / "ent" / "proj"
                  / "versions" / VERSION_ID / "meanings.jsonl")) < 275:
        deep = deep / ("nested-" + "x" * 12)
    workspace = deep / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir(exist_ok=True)
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")

    def seed(state):
        state.update(_legacy_document()["semantic"])
        _append_transition(state, 2)

    wiki.update_semantic_state(seed)

    artifact = workspace / ".catalyst" / "wiki" / "ent" / "proj" / "versions" / VERSION_ID / "meanings.jsonl"
    if os.name == "nt":
        # The readable layout is the one that outruns MAX_PATH here; the store has to cope.
        assert len(str(artifact)) > 260
    assert wiki.semantic_state()["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["meaning"] == (
        "a review requires a source link"
    )



def test_an_unknown_schema_version_is_refused_rather_than_relabelled(tmp_path):
    """A version this build does not know is refused, never rewritten into the current one."""
    from catalyst_platform.wiki import _migrate_document

    for declared in (999, "2", None):
        with pytest.raises(WikiUnavailable, match="does not read"):
            _migrate_document(
                {"schema_version": declared, "scope_id": _scope_id(), "sources": {}, "claims": {}}
            )

    wiki = _seeded(tmp_path)
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["schema_version"] = 999
    index_path.write_text(json.dumps(index), encoding="utf-8")
    before = index_path.read_bytes()

    with pytest.raises(WikiUnavailable):
        wiki.semantic_state()
    report = wiki.verify()
    assert report["status"] == "BROKEN"
    assert [row["status"] for row in report["problems"]] == ["index_unsupported"]
    assert index_path.read_bytes() == before


def test_an_unknown_semantic_version_is_refused_rather_than_upgraded(tmp_path):
    wiki = _seeded(tmp_path)
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["semantic"]["schema_version"] = 999
    index_path.write_text(json.dumps(index), encoding="utf-8")

    with pytest.raises(WikiUnavailable, match="semantic ledger declares a schema version"):
        wiki.semantic_state()

    report = wiki.verify()
    assert report["status"] == "BROKEN"
    assert [(row.get("ledger"), row["status"]) for row in report["problems"]] == [("semantic", "schema_unsupported")]
    stored = json.loads(index_path.read_text(encoding="utf-8"))
    assert stored["semantic"]["schema_version"] == 999


def test_verify_names_a_semantic_ledger_it_cannot_read(tmp_path):
    wiki = _seeded(tmp_path)
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["semantic"]["candidates"] = []
    index_path.write_text(json.dumps(index), encoding="utf-8")

    with pytest.raises(WikiUnavailable, match="semantic state is unreadable"):
        wiki.semantic_state()

    report = wiki.verify()
    assert report["status"] == "BROKEN"
    assert [(row.get("ledger"), row["status"]) for row in report["problems"]] == [("semantic", "ledger_invalid")]


def test_verify_names_a_concepts_ledger_it_cannot_read(tmp_path):
    wiki = _wiki(tmp_path)
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    document = _legacy_document()
    document["concepts"] = {"schema_version": 999, "versions": {}, "history": []}
    index_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(WikiUnavailable, match="concept state is unreadable"):
        wiki.concept_state()

    report = wiki.verify()
    assert report["status"] == "BROKEN"
    assert [(row.get("ledger"), row["status"]) for row in report["problems"]] == [("concepts", "ledger_invalid")]


def test_the_sqlite_backend_refuses_an_unknown_version_without_writing(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")
    document = _legacy_document()
    document["semantic"]["schema_version"] = 999
    database = _scope_root(wiki.workspace) / "wiki.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS wiki_state (scope_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO wiki_state(scope_id, payload) VALUES(?, ?)", (_scope_id(), json.dumps(document))
        )

    with pytest.raises(WikiUnavailable, match="semantic ledger declares a schema version"):
        wiki.semantic_state()
    with pytest.raises(WikiUnavailable, match="semantic ledger declares a schema version"):
        wiki.update_semantic_state(lambda state: _append_transition(state, 2))

    with sqlite3.connect(database) as connection:
        payload = connection.execute("SELECT payload FROM wiki_state").fetchone()[0]
    assert json.loads(payload)["semantic"]["schema_version"] == 999
    assert wiki.verify()["status"] == "BROKEN"


def _artifact(wiki, record="version"):
    """The descriptor exactly as the committed index names it."""
    index = json.loads((_scope_root(wiki.workspace) / "wiki.json").read_text(encoding="utf-8"))
    if record == "version":
        return index["semantic"]["accepted_versions"][VERSION_ID]["meanings"]["_artifact"]
    return index["semantic"]["candidates"][CANDIDATE_ID][record]["_artifact"]


def _artifact_file(wiki, record="version"):
    return _scope_root(wiki.workspace) / _artifact(wiki, record)["path"]


def _seeded(tmp_path, name="workspace"):
    """A store with one version and one candidate, each payload already in its own file."""
    wiki = _wiki(tmp_path, name=name)
    store_path = _scope_root(wiki.workspace) / "wiki.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(_legacy_document()), encoding="utf-8")
    wiki.update_semantic_state(lambda state: _append_transition(state, 2))
    return wiki


def _cli(args):
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_verify_accepts_a_store_this_build_wrote(tmp_path):
    report = _seeded(tmp_path).verify()

    assert report["status"] == "OK"
    assert report["backend"] == "json"
    assert report["artifact_count"] == 2
    assert [row["status"] for row in report["artifacts"]] == ["ok", "ok"]
    assert {row["field"] for row in report["artifacts"]} == {
        f"accepted_versions/{VERSION_ID}/meanings",
        f"candidates/{CANDIDATE_ID}/entries",
    }
    assert report["orphans"] == []


def test_verify_names_a_missing_or_altered_artifact(tmp_path):
    wiki = _seeded(tmp_path)
    meanings_path = _artifact_file(wiki)
    original = meanings_path.read_bytes()

    meanings_path.unlink()
    missing = wiki.verify()
    assert missing["status"] == "BROKEN"
    assert [
        row["status"] for row in missing["artifacts"] if "/meanings." in str(row["path"])
    ] == ["missing"]

    meanings_path.write_bytes(original.replace(b"review_gate", b"review_gat3"))
    altered = wiki.verify()
    assert altered["status"] == "BROKEN"
    assert [
        row["status"] for row in altered["artifacts"] if "/meanings." in str(row["path"])
    ] == ["digest_mismatch"]

    meanings_path.write_bytes(original)
    assert wiki.verify()["status"] == "OK"


def test_verify_reports_a_file_the_index_does_not_name(tmp_path):
    wiki = _seeded(tmp_path)
    leftover = _scope_root(wiki.workspace) / "versions" / VERSION_ID / "meanings.old.jsonl"
    leftover.write_text('{"meaning_id": "meaning_old"}\n', encoding="utf-8")

    report = wiki.verify()

    assert report["status"] == "OK"
    assert report["orphans"] == [f"versions/{VERSION_ID}/meanings.old.jsonl"]


def test_verify_calls_an_empty_store_empty_rather_than_broken(tmp_path):
    report = _wiki(tmp_path).verify()

    assert report["status"] == "EMPTY"
    assert report["index_present"] is False
    assert report["artifact_count"] == 0


def test_verify_accepts_the_inline_sqlite_store(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")

    def seed(state):
        state.update(_legacy_document()["semantic"])
        _append_transition(state, 2)

    wiki.update_semantic_state(seed)

    report = wiki.verify()

    assert report["status"] == "OK"
    assert report["inline_payload"] is True
    assert report["artifacts"] == [] and report["orphans"] == []


def test_the_verify_command_exits_non_zero_once_an_artifact_is_gone(tmp_path):
    wiki = _seeded(tmp_path)
    common = [
        "wiki", "verify", "--workspace", str(wiki.workspace),
        "--enterprise-id", "ent", "--project-id", "proj",
    ]
    code, report = _cli(common)
    assert (code, report["status"]) == (0, "OK")

    relative = _artifact(wiki)["path"]
    (_scope_root(wiki.workspace) / relative).unlink()
    code, report = _cli(common)
    assert (code, report["status"]) == (1, "BROKEN")
    assert report["problems"][0]["path"] == relative


def test_a_failed_index_write_keeps_the_committed_generation_readable(tmp_path):
    """The old index still promises its own bytes, and those bytes are still on disk."""
    wiki = _seeded(tmp_path)
    committed = wiki.semantic_state()
    entries_before = committed["candidates"][CANDIDATE_ID]["entries"]
    meanings_before = committed["accepted_versions"][VERSION_ID]["meanings"]
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    old_index = index_path.read_bytes()

    store = wiki._store

    def refuse(_index):
        raise WikiUnavailable("index write refused for this test")

    store._write_index = refuse
    try:
        with pytest.raises(WikiUnavailable):
            wiki.update_semantic_state(
                lambda state: state["candidates"][CANDIDATE_ID].__setitem__(
                    "entries", [dict(entries_before[0], meaning="a review requires a second link")]))
    finally:
        del store._write_index

    assert index_path.read_bytes() == old_index
    after = wiki.semantic_state()
    assert after["candidates"][CANDIDATE_ID]["entries"] == entries_before
    assert after["accepted_versions"][VERSION_ID]["meanings"] == meanings_before
    report = wiki.verify()
    assert report["status"] == "OK"
    # The generation the failed commit wrote is named as an orphan, not deleted and not read.
    assert report["orphans"]
    assert all(path.startswith(f"candidates/{CANDIDATE_ID}/entries.") for path in report["orphans"])


def _replace_artifact(wiki, record, content, **changes):
    """Overwrite one artifact in place and re-sign it, so the descriptor still matches."""
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if record == "version":
        descriptor = index["semantic"]["accepted_versions"][VERSION_ID]["meanings"]["_artifact"]
    else:
        descriptor = index["semantic"]["candidates"][CANDIDATE_ID][record]["_artifact"]
    (_scope_root(wiki.workspace) / descriptor["path"]).write_bytes(content)
    descriptor["sha256"] = hashlib.sha256(content).hexdigest()
    descriptor.update(changes)
    index_path.write_text(json.dumps(index), encoding="utf-8")
    return descriptor


def test_verify_and_the_reader_reject_the_same_broken_bytes(tmp_path):
    """A digest that matches says the bytes are the committed ones, not that they parse."""
    wiki = _seeded(tmp_path)
    wiki.update_semantic_state(
        lambda state: state["candidates"][CANDIDATE_ID].__setitem__("understanding_result", {"items": []})
    )

    _replace_artifact(wiki, "understanding_result", b"{broken")

    report = wiki.verify()
    assert report["status"] == "BROKEN"
    row = next(item for item in report["artifacts"] if item["field"].endswith("/understanding_result"))
    assert row["status"] == "unreadable"
    with pytest.raises(WikiUnavailable, match="is unreadable"):
        wiki.semantic_state()


def test_verify_and_the_reader_reject_a_repeated_mapping_row_key(tmp_path):
    """Two rows under one key: the reader refuses, so the health check must too."""
    wiki = _seeded(tmp_path)
    row = json.dumps(_meaning(), sort_keys=True)
    _replace_artifact(wiki, "version", f"{row}\n{row}\n".encode("utf-8"), count=2)

    report = wiki.verify()
    assert report["status"] == "BROKEN"
    rows = [item for item in report["artifacts"] if item["field"] == f"accepted_versions/{VERSION_ID}/meanings"]
    assert [item["status"] for item in rows] == ["duplicate_row_key"]
    with pytest.raises(WikiUnavailable, match="repeats a row key"):
        wiki.semantic_state()
    assert len(_artifact_file(wiki).read_text(encoding="utf-8").splitlines()) == 2
    assert _artifact(wiki)["count"] == 2


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({"count": 99}, "count_mismatch"),
        ({"count": None}, "descriptor_unreadable"),
        ({"count": True}, "descriptor_unreadable"),
        ({"format": "invalid"}, "format_mismatch"),
    ],
)
def test_verify_and_the_reader_share_one_descriptor_contract(tmp_path, changes, status):
    """The descriptor's own fields are judged the same way whichever side reads it."""
    wiki = _seeded(tmp_path)
    _replace_artifact(wiki, "version", _artifact_file(wiki).read_bytes(), **changes)

    report = wiki.verify()
    assert report["status"] == "BROKEN"
    rows = [item for item in report["artifacts"] if item["field"] == f"accepted_versions/{VERSION_ID}/meanings"]
    assert [item["status"] for item in rows] == [status]
    with pytest.raises(WikiUnavailable):
        wiki.semantic_state()


def test_a_failed_artifact_write_keeps_the_committed_generation_readable(tmp_path, monkeypatch):
    import catalyst_platform.wiki as wiki_module

    wiki = _seeded(tmp_path)
    index_path = _scope_root(wiki.workspace) / "wiki.json"
    old_index = index_path.read_bytes()
    real = wiki_module._write_artifact
    calls = {"count": 0}

    def fail_second(root, relative, content):
        calls["count"] += 1
        if calls["count"] == 2:
            raise WikiUnavailable("artifact write refused for this test")
        return real(root, relative, content)

    monkeypatch.setattr(wiki_module, "_write_artifact", fail_second)
    with pytest.raises(WikiUnavailable):
        wiki.update_semantic_state(lambda state: _append_transition(state, 99))
    monkeypatch.undo()

    assert index_path.read_bytes() == old_index
    assert wiki.semantic_state()["transitions"][-1]["transition_id"] == "transition_artifact_2"
    assert wiki.verify()["status"] == "OK"


def test_reading_a_sqlite_store_leaves_the_file_byte_identical(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")

    def seed(state):
        state.update(_legacy_document()["semantic"])
        _append_transition(state, 2)

    wiki.update_semantic_state(seed)
    database = _scope_root(wiki.workspace) / "wiki.sqlite3"
    before = database.read_bytes()

    assert wiki.semantic_state()["accepted_versions"][VERSION_ID]["meanings"][MEANING_ID]["key"] == "review_gate"
    assert database.read_bytes() == before
    report = wiki.verify()
    assert report["status"] == "OK"
    assert report["table_present"] is True and report["scope_row_present"] is True
    assert database.read_bytes() == before


def test_a_sqlite_store_without_the_table_is_empty_and_left_alone(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")
    database = _scope_root(wiki.workspace) / "wiki.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE something_else (value INTEGER)")
    before = database.read_bytes()

    report = wiki.verify()

    assert report["status"] == "EMPTY"
    assert report["table_present"] is False
    assert report["scope_row_present"] is False
    assert wiki.semantic_state()["candidates"] == {}
    assert database.read_bytes() == before


def test_a_sqlite_store_without_this_scope_row_is_empty(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")
    database = _scope_root(wiki.workspace) / "wiki.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE wiki_state (scope_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        connection.execute("INSERT INTO wiki_state(scope_id, payload) VALUES(?, ?)", ("enterprise:other/project:other", "{}"))
    before = database.read_bytes()

    report = wiki.verify()

    assert report["status"] == "EMPTY"
    assert report["table_present"] is True
    assert report["scope_row_present"] is False
    assert wiki.semantic_state()["accepted_versions"] == {}
    assert database.read_bytes() == before


def test_verifying_a_sqlite_store_that_was_never_written_creates_no_file(tmp_path):
    wiki = _wiki(tmp_path, backend="sqlite")
    database = _scope_root(wiki.workspace) / "wiki.sqlite3"

    report = wiki.verify()

    assert report["status"] == "EMPTY"
    assert report["index_present"] is False
    assert not database.exists()
    assert wiki.semantic_state()["candidates"] == {}
    assert not database.exists()


SOURCE_ID_COLD = "source_cold"


def _cold_tree(tmp_path):
    """A published store with one Markdown source and a page tree beside it."""
    wiki = _seeded(tmp_path)
    source = wiki.roots[0] / "policy.md"
    source.write_text("Rule: a cold read reads its own copy.\n", encoding="utf-8")
    revision = hashlib.sha256(source.read_bytes()).hexdigest()

    def add_source(document):
        document["sources"][SOURCE_ID_COLD] = {
            "source_id": SOURCE_ID_COLD,
            "scope_id": _scope_id(),
            "relative_path": "policy.md",
            "revision": revision,
            "source_format": "markdown",
            "status": "ACTIVE",
        }

    wiki._store.update(add_source)
    pages = project(wiki)
    root = tmp_path / "pages"
    materialize(pages.pages, root, identity=pages.identity)
    return wiki, source, root


def _copy(tmp_path, wiki, root):
    cold_workspace = tmp_path / "cold" / "workspace"
    cold_pages = tmp_path / "cold" / "pages"
    shutil.copytree(wiki.workspace, cold_workspace)
    shutil.copytree(root, cold_pages)
    return cold_workspace, cold_pages


def _cold(cold_workspace, cold_pages, roots):
    return cold_read(
        workspace=cold_workspace, enterprise_id="ent", project_id="proj",
        roots=roots, pages_root=cold_pages,
    )


def test_a_cold_read_answers_from_the_copy_alone(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)

    # The original store moves out of the way: anything the copy needs, it has itself.
    original = wiki.workspace
    moved = tmp_path / "original-moved"
    original.rename(moved)
    try:
        report = _cold(cold_workspace, cold_pages, [source.parent])
    finally:
        moved.rename(original)

    assert report["status"] == "OK", report["problems"]
    assert report["workspace"] == str(cold_workspace.resolve())
    assert report["store"]["status"] == "OK"
    index = cold_workspace / ".catalyst" / "wiki" / "ent" / "proj" / "wiki.json"
    assert report["store"]["index_sha256"] == hashlib.sha256(index.read_bytes()).hexdigest()
    assert report["versions"]["count"] == 1
    assert report["versions"]["active_version_id"] == VERSION_ID
    assert report["versions"]["active_pointer_ok"] is True
    assert report["concepts"]["count"] >= 1
    assert report["sources"] == {
        "recorded": 1, "verified": 1, "missing": [], "changed": [],
        "ambiguous": [], "derived_missing": [],
    }
    assert report["pages"]["projected"] == report["pages"]["on_disk"]
    assert report["pages"]["projected"] == report["pages"]["recorded"] > 0
    assert report["pages"]["identity_match"] is True
    assert report["pages"]["human_edited"] == []


def test_a_cold_read_names_a_source_that_is_no_longer_there(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    source.rename(source.with_name("policy.moved"))

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "BROKEN"
    assert report["sources"]["missing"] == [SOURCE_ID_COLD]
    assert [row["code"] for row in report["problems"]] == ["missing_source"]


def test_a_cold_read_names_a_source_whose_bytes_changed(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    source.write_text("Rule: someone edited the file after it was staged.\n", encoding="utf-8")

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "BROKEN"
    assert report["sources"]["changed"] == [SOURCE_ID_COLD]


def test_a_cold_read_reports_a_page_a_person_edited_without_calling_it_a_failure(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    edited = cold_pages / "overview.md"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n人工补注：这一版核过。\n", encoding="utf-8")

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "OK", report["problems"]
    assert report["pages"]["human_edited"] == ["overview.md"]
    assert [(row["code"], row["severity"]) for row in report["problems"]] == [("page_human_edited", "note")]


def test_a_cold_read_names_a_page_missing_from_the_tree(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    (cold_pages / "overview.md").rename(cold_pages / "overview.moved")

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "BROKEN"
    assert report["pages"]["missing"] == ["overview.md"]
    assert "page_missing" in [row["code"] for row in report["problems"]]


def test_a_cold_read_notices_a_tree_from_another_store_generation(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    manifest_path = cold_pages / ".projection.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["identity"]["store_index_sha256"] = "f" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "BROKEN"
    assert report["pages"]["identity_match"] is False
    assert "identity_mismatch" in [row["code"] for row in report["problems"]]


def test_a_cold_read_reports_a_corrupt_artifact_in_the_copy(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    index_path = cold_workspace / ".catalyst" / "wiki" / "ent" / "proj" / "wiki.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    relative = index["semantic"]["accepted_versions"][VERSION_ID]["meanings"]["_artifact"]["path"]
    (cold_workspace / ".catalyst" / "wiki" / "ent" / "proj" / relative).write_bytes(b"{broken")

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "BROKEN"
    assert report["store"]["status"] == "BROKEN"
    assert "store_broken" in [row["code"] for row in report["problems"]]


def test_a_cold_read_says_whether_the_links_between_pages_lead_anywhere(tmp_path):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "OK", report["problems"]
    links = report["links"]
    assert links["links"] > 0
    assert len(links["resolved"]) == links["links"]
    assert links["unresolved"] == []
    assert links["ambiguous"] == []
    assert links["titles"] == report["pages"]["projected"] - len(links["duplicate_titles"])
    # Every edge names a file this copy actually holds.
    on_disk = {path.relative_to(cold_pages).as_posix() for path in cold_pages.rglob("*.md")}
    assert {row["path"] for row in links["resolved"]} <= on_disk


def test_a_cold_read_calls_a_link_that_leads_nowhere_a_defect_of_the_copy(tmp_path, monkeypatch):
    wiki, source, root = _cold_tree(tmp_path)
    cold_workspace, cold_pages = _copy(tmp_path, wiki, root)
    # The renderer cannot produce this on its own today, so the pages are handed in directly:
    # what is under test is the reading of the report, not the production of the defect.
    hand_made = (Page("overview.md", "overview", "概览", "# 概览\n\n- 还缺什么见 [[不存在的一页]]\n"),)
    monkeypatch.setattr(
        wiki_cold_read, "project",
        lambda *args, **kwargs: PageSet(pages=hand_made, stats={"links": link_report(hand_made)}))

    report = _cold(cold_workspace, cold_pages, [source.parent])

    assert report["status"] == "BROKEN"
    assert report["links"]["unresolved"] == [{"title": "不存在的一页", "from": "overview.md"}]
    errors = {row["code"] for row in report["problems"] if row["severity"] == "error"}
    assert "link_unresolved" in errors
