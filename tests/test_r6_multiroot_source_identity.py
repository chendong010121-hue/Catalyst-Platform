import hashlib
import json

import pytest

from catalyst_platform import __main__ as cli
from catalyst_platform.wiki import ProjectWiki, WikiScopeError


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("root_order", ["ab", "ba"])
def test_ambiguous_same_relative_source_is_rejected_without_staling_existing_claim(
    tmp_path, backend, root_order
):
    root_a = tmp_path / "source-a"
    root_b = tmp_path / "source-b"
    root_a.mkdir()
    root_b.mkdir()
    source_a = root_a / "rules.md"
    source_b = root_b / "rules.md"
    source_a.write_text("# Source A\nRule: alpha approval stays active\n", encoding="utf-8")
    source_b.write_text("# Source B\nRule: beta review is required\n", encoding="utf-8")
    workspace = tmp_path / "workspace"

    # Preserve the historical one-root identity before introducing the second root.
    first_wiki = ProjectWiki(
        workspace, [root_a], enterprise_id="ent", project_id="proj", backend=backend
    )
    first = first_wiki.stage_markdown(source_a)
    expected_legacy_id = "source_" + hashlib.sha256(
        b"enterprise:ent/project:proj\0rules.md"
    ).hexdigest()[:24]
    assert first["source_id"] == expected_legacy_id

    roots = [root_a, root_b] if root_order == "ab" else [root_b, root_a]
    expanded_wiki = ProjectWiki(
        workspace, roots, enterprise_id="ent", project_id="proj", backend=backend
    )
    with pytest.raises(WikiScopeError, match="same relative path"):
        expanded_wiki.stage_markdown(source_b)

    history = expanded_wiki.claim_history(first["source_id"])
    assert history
    assert all(claim["revision"] == first["revision"] for claim in history)
    assert all(claim["status"] != "STALE" for claim in history)
    assert any("alpha approval stays active" in claim["meaning"] for claim in history)
    assert not any("beta review is required" in claim["meaning"] for claim in history)


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("root_order", ["ab", "ba"])
def test_ambiguous_roots_from_start_fail_closed_for_each_source(tmp_path, backend, root_order):
    root_a = tmp_path / "source-a"
    root_b = tmp_path / "source-b"
    root_a.mkdir()
    root_b.mkdir()
    source_a = root_a / "rules.md"
    source_b = root_b / "rules.md"
    source_a.write_text("# Source A\nRule: alpha source\n", encoding="utf-8")
    source_b.write_text("# Source B\nRule: beta source\n", encoding="utf-8")
    roots = [root_a, root_b] if root_order == "ab" else [root_b, root_a]
    wiki = ProjectWiki(
        tmp_path / "workspace", roots, enterprise_id="ent", project_id="proj", backend=backend
    )

    for source in (source_a, source_b):
        with pytest.raises(WikiScopeError, match="same relative path"):
            wiki.stage_markdown(source)

    assert wiki.claim_history("source_" + hashlib.sha256(
        b"enterprise:ent/project:proj\0rules.md"
    ).hexdigest()[:24]) == []


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_nested_configured_roots_are_rejected_as_ambiguous(tmp_path, backend):
    root = tmp_path / "sources"
    nested = root / "nested"
    nested.mkdir(parents=True)
    source = nested / "rules.md"
    source.write_text("# Nested\nRule: do not pick identity by root order\n", encoding="utf-8")
    wiki = ProjectWiki(
        tmp_path / "workspace", [root, nested], enterprise_id="ent", project_id="proj", backend=backend
    )

    with pytest.raises(WikiScopeError, match="multiple configured Wiki roots"):
        wiki.stage_markdown(source)


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_lexical_root_alias_keeps_single_root_identity_and_noop_behavior(tmp_path, backend):
    root = tmp_path / "sources"
    root.mkdir()
    source = root / "rules.md"
    source.write_text("# Alias\nRule: one canonical source identity\n", encoding="utf-8")
    wiki = ProjectWiki(
        tmp_path / "workspace", [root, root / "."], enterprise_id="ent", project_id="proj", backend=backend
    )

    first = wiki.stage_markdown(source)
    repeated = wiki.stage_markdown(source)

    assert first["status"] == "staged"
    assert repeated["status"] == "no_op"
    assert repeated["source_id"] == first["source_id"]


def test_product_entry_records_specific_identity_conflict_failure(tmp_path, capsys):
    root_a = tmp_path / "source-a"
    root_b = tmp_path / "source-b"
    root_a.mkdir()
    root_b.mkdir()
    source_a = root_a / "rules.md"
    source_b = root_b / "rules.md"
    source_a.write_text("# Source A\nRule: alpha source\n", encoding="utf-8")
    source_b.write_text("# Source B\nRule: beta source\n", encoding="utf-8")
    workspace = tmp_path / "workspace"

    code = cli.main([
        "ask", "--workspace", str(workspace), "--wiki-root", str(root_a), "--wiki-root", str(root_b),
        "--project-id", "proj", "--enterprise-id", "ent", "--message", "read the selected file",
        "--file", str(source_a), "--stage-source", str(source_a), "--offline-deterministic",
    ])
    run = json.loads(capsys.readouterr().out)

    assert code == 1
    assert run["status"] == "failure"
    assert run["error"]["code"] == "wiki_source_identity_ambiguous"
    trace = workspace / ".catalyst" / "traces" / "runs.jsonl"
    events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    events = [event for event in events if event.get("run_id") == run["run_id"]]
    failure = next(event for event in events if event["event_type"] == "knowledge.source.staging_failed")
    terminal = next(event for event in events if event["event_type"] == "request.terminal")
    assert failure["error_code"] == "wiki_source_identity_ambiguous"
    assert terminal["terminal_status"] == "failure"
