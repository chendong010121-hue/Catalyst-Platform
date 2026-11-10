"""Capability claim build: select declared structure, declare the rest unknown."""
import hashlib
import json
from pathlib import Path

import pytest

from catalyst_platform import capability_claim_build as build
from catalyst_platform.capability_claim import claim_digest, validate_claim
from catalyst_platform.capability_compare import compare_claims

ROOT = Path(__file__).resolve().parent.parent
REPO_SKILLS = ROOT / "platform-harness" / "skills"

FRONTMATTER = """---
name: {name}
description: {description}
version: 2026.10.28.1
---
"""


def write_package(root: Path, name: str, *, description="Do a bounded thing.", body="", files=None) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        FRONTMATTER.format(name=name, description=description) + "\n" + body,
        encoding="utf-8",
    )
    for relative, text in (files or {}).items():
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return directory


@pytest.fixture
def rules_package(tmp_path):
    body = """# Demo skill

## Rules

- Read every file before acting; never install unread content.
- `scripts/run.mjs`: the runner the skill ships.
- Prefer a pinned revision over a branch.

## Known limits

- Only single-line `key: value` frontmatter is understood.

## Failure modes

- When the source is unreachable, stop and say so.

```text
This block must not become an obligation.
```

| field | required |
"""
    return tmp_path, write_package(tmp_path, "demo-skill", description="Install demo content from one source.", body=body)


def test_real_repository_package_builds_a_valid_claim():
    result = build.build_claim(
        source_root=REPO_SKILLS,
        package="understand-asset-inspector",
        responsibility_key="inspect-asset-manifest",
    )
    assert result.status == build.CLAIM_BUILT, result.reason
    assert validate_claim(result.claim) == []
    assert result.claim["capability"]["kind"] == "skill"
    assert result.claim["capability"]["id"] == "understand-asset-inspector"
    assert result.claim["what"]["obligations"]
    assert all(item["evidence"] for item in result.claim["what"]["obligations"])


def test_every_quote_is_the_exact_line_it_claims_and_hashes_to_its_span(rules_package):
    root, _ = rules_package
    result = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.CLAIM_BUILT, result.reason
    for row in result.claim["why"]["evidence"]:
        relative, _, line = row["locator"].rpartition(":L")
        text = (root / "demo-skill" / relative).read_text(encoding="utf-8").splitlines()
        quote = text[int(line) - 1]
        assert row["quote"] == quote, row
        assert row["span_sha256"] == hashlib.sha256(row["quote"].encode("utf-8")).hexdigest()
        assert row["revision"] == hashlib.sha256((root / "demo-skill" / relative).read_bytes()).hexdigest()


def test_selection_follows_declared_structure_not_prose_swallowing(rules_package):
    root, _ = rules_package
    result = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    statements = [item["statement"] for item in result.claim["what"]["obligations"]]
    assert "Read every file before acting; never install unread content." in statements
    assert "Prefer a pinned revision over a branch." in statements
    assert not any("This block must not become" in text for text in statements)
    assert not any(text.startswith("|") for text in statements)
    assert not any("the runner the skill ships" in text for text in statements)


def test_declared_sections_become_evidenced_items(rules_package):
    root, _ = rules_package
    result = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    limits = result.claim["what"]["known_limits"]
    failures = result.claim["what"]["failure_modes"]
    assert [item["statement"] for item in limits] == ["Only single-line `key: value` frontmatter is understood."]
    assert [item["statement"] for item in failures] == ["When the source is unreachable, stop and say so."]
    assert {item["evidence_class"] for item in limits + failures} == {"EXPLICIT"}


def test_fields_the_package_never_declares_are_unknown_not_blank(rules_package):
    root, _ = rules_package
    result = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    unknown_fields = {row["field"] for row in result.claim["why"]["unknowns"]}
    assert {"what.inputs", "what.outputs", "what.applicability.include", "what.applicability.exclude"} <= unknown_fields
    assert {"how.side_effects", "how.permissions", "what.performance", "what.quality"} <= unknown_fields
    assert validate_claim(result.claim) == []


def test_quick_start_is_declared_unobserved_with_unknown_cost(rules_package):
    root, _ = rules_package
    result = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    quick_start = result.claim["quick_start"]
    assert quick_start["observable"] is False
    assert quick_start["limitation"]
    assert quick_start["cost"] == "unknown"
    assert quick_start["prompt"] == "use demo-skill skill"
    assert result.receipt["quick_start_source"] == "description"


def test_build_is_deterministic_and_independent_of_the_source_root(tmp_path):
    first = write_package(tmp_path / "a", "demo-skill", body="## Rules\n\n- Never act before reading.\n")
    second = tmp_path / "b" / "demo-skill"
    second.parent.mkdir()
    second.mkdir()
    (second / "SKILL.md").write_bytes((first / "SKILL.md").read_bytes())
    left = build.build_claim(source_root=tmp_path / "a", package="demo-skill", responsibility_key="install-content")
    right = build.build_claim(source_root=tmp_path / "b", package="demo-skill", responsibility_key="install-content")
    again = build.build_claim(source_root=tmp_path / "a", package="demo-skill", responsibility_key="install-content")
    assert left.status == right.status == build.CLAIM_BUILT
    assert claim_digest(left.claim) == claim_digest(right.claim) == claim_digest(again.claim)


def test_referenced_text_files_are_read_for_rules(tmp_path):
    directory = write_package(
        tmp_path,
        "demo-skill",
        body="## Rules\n\n- Never skip the review.\n",
        files={"references/extra.md": "# Extra\n\n- The package must never phone home.\n"},
    )
    assert directory.is_dir()
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.CLAIM_BUILT, result.reason
    locators = [row["locator"] for row in result.claim["why"]["evidence"]]
    assert any(locator.startswith("references/extra.md:L") for locator in locators)
    assert any("phone home" in item["statement"] for item in result.claim["what"]["obligations"])


def test_package_without_a_declared_obligation_is_refused(tmp_path):
    write_package(tmp_path, "demo-skill", body="# Demo\n\nThis skill describes a thing that exists.\n")
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.INSUFFICIENT_SOURCE
    assert result.claim is None
    assert "义务" in result.reason


def test_block_scalar_description_is_read_from_the_line_that_carries_it(tmp_path):
    directory = tmp_path / "demo-skill"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: >-\n  Install demo content\n  from one source.\nversion: 1\n---\n\n## Rules\n\n- Never act.\n",
        encoding="utf-8",
    )
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.CLAIM_BUILT, result.reason
    assert result.claim["capability"]["statement"] == "Install demo content from one source."
    statement = next(row for row in result.claim["why"]["evidence"] if row["field"] == "capability.statement")
    assert statement["locator"] == "SKILL.md:L4"
    assert statement["quote"] == "Install demo content"


def test_block_marker_without_indented_content_is_refused(tmp_path):
    directory = tmp_path / "demo-skill"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: >-\nversion: 1\n---\n\n## Rules\n\n- Never act.\n",
        encoding="utf-8",
    )
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.INSUFFICIENT_SOURCE
    assert result.claim is None
    assert "description" in result.reason


def test_reference_folder_singular_is_read_as_well(tmp_path):
    write_package(
        tmp_path,
        "demo-skill",
        body="## Rules\n\n- Never skip the review.\n",
        files={"reference/extra.md": "# Extra\n\n- The package must never phone home.\n"},
    )
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.CLAIM_BUILT, result.reason
    assert result.receipt["references"]["read"] == ["demo-skill/reference/extra.md"]
    assert any("phone home" in item["statement"] for item in result.claim["what"]["obligations"])


def test_package_without_manifest_is_unsupported(tmp_path):
    (tmp_path / "demo-skill").mkdir()
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.UNSUPPORTED_PACKAGE
    assert result.claim is None
    assert result.receipt["detection"]["kind"] == "repository"


def test_package_form_is_detected_from_the_marker_it_declares(tmp_path):
    skill = write_package(tmp_path / "a", "demo-skill", body="## Rules\n\n- Never act.\n")
    claude_plugin = tmp_path / "b" / "claude-plugin"
    (claude_plugin / ".claude-plugin").mkdir(parents=True)
    (claude_plugin / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    codex_plugin = tmp_path / "b" / "codex-plugin"
    (codex_plugin / ".codex-plugin").mkdir(parents=True)
    (codex_plugin / ".codex-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    penguin_plugin = tmp_path / "b" / "penguin-package"
    penguin_plugin.mkdir()
    (penguin_plugin / "package.json").write_text(json.dumps({"name": "x", "penguin": {}}), encoding="utf-8")
    agent = tmp_path / "b" / "demo-agent"
    (agent / "agent_state").mkdir(parents=True)
    (agent / "agent_state" / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    code = tmp_path / "b" / "demo-code"
    code.mkdir()
    (code / "main.py").write_text("print(1)\n", encoding="utf-8")
    repository = tmp_path / "b" / "demo-repo"
    repository.mkdir()
    (repository / "README.md").write_text("# Repo\n", encoding="utf-8")
    plain_package = tmp_path / "b" / "plain-package"
    plain_package.mkdir()
    (plain_package / "package.json").write_text(json.dumps({"name": "x"}), encoding="utf-8")

    assert build.detect_kind(skill)[0] == "skill"
    assert "SKILL.md" in build.detect_kind(skill)[1]
    assert build.detect_kind(claude_plugin)[0] == "plugin"
    assert build.detect_kind(codex_plugin)[0] == "plugin"
    assert build.detect_kind(penguin_plugin)[0] == "plugin"
    assert build.detect_kind(agent)[0] == "agent"
    assert build.detect_kind(code)[0] == "code"
    assert build.detect_kind(repository)[0] == "repository"
    assert build.detect_kind(plain_package)[0] == "repository"
    assert build.detect_kind(tmp_path / "missing")[0] == "repository"


def test_a_plugin_package_is_identified_and_refused_until_its_decoder_lands(tmp_path):
    directory = tmp_path / "demo-plugin"
    (directory / ".claude-plugin").mkdir(parents=True)
    (directory / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    result = build.build_claim(source_root=tmp_path, package="demo-plugin", responsibility_key="install-external-plugin")
    assert result.status == build.UNSUPPORTED_PACKAGE
    assert result.claim is None
    assert result.receipt["detection"] == {
        "kind": "plugin",
        "reason": "存在 .claude-plugin/plugin.json",
        "decoder": "PLANNED",
    }
    assert "plugin" in result.reason


def test_an_agent_package_is_identified_and_refused_until_its_decoder_lands(tmp_path):
    directory = tmp_path / "demo-agent"
    (directory / "agent_state").mkdir(parents=True)
    (directory / "agent_state" / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
    result = build.build_claim(source_root=tmp_path, package="demo-agent", responsibility_key="run-agent")
    assert result.status == build.UNSUPPORTED_PACKAGE
    assert result.claim is None
    assert result.receipt["detection"]["kind"] == "agent"
    assert "agent" in result.reason


def test_responsibility_key_is_required_and_nothing_is_read_without_it(tmp_path):
    result = build.build_claim(source_root=tmp_path, package="does-not-exist", responsibility_key=None)
    assert result.status == build.NEEDS_RESPONSIBILITY_KEY
    assert result.claim is None
    assert "understand" not in result.receipt


def test_malformed_responsibility_key_is_refused(tmp_path):
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="Port_External")
    assert result.status == build.NEEDS_RESPONSIBILITY_KEY
    assert result.claim is None


def test_package_outside_the_trusted_root_is_refused(tmp_path):
    write_package(tmp_path / "inside", "demo-skill", body="## Rules\n\n- Never act.\n")
    write_package(tmp_path / "outside", "demo-skill", body="## Rules\n\n- Never act.\n")
    result = build.build_claim(
        source_root=tmp_path / "outside",
        package=tmp_path / "inside" / "demo-skill",
        responsibility_key="install-content",
    )
    assert result.status == build.UNSUPPORTED_PACKAGE
    assert result.claim is None


def test_undeclared_version_falls_back_to_the_content_revision(tmp_path):
    directory = write_package(tmp_path, "demo-skill", body="## Rules\n\n- Never act.\n")
    manifest = (directory / "SKILL.md").read_text(encoding="utf-8").replace("version: 2026.10.28.1\n", "")
    (directory / "SKILL.md").write_text(manifest, encoding="utf-8")
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.status == build.CLAIM_BUILT, result.reason
    assert result.claim["capability"]["version"].startswith("content-")
    assert result.receipt["version"]["from"] == "content-digest"


def test_classification_defaults_to_the_artifact_that_was_read(rules_package):
    root, _ = rules_package
    result = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    assert result.claim["capability"]["kind"] == "skill"
    assert result.claim["how"]["interface"] == {"id": "agent-skill", "version": "1"}
    assert result.receipt["classification"]["kind"]["from"] == "package"
    assert result.receipt["classification"]["interface"]["from"] == "host-format"


def test_a_reviewer_may_declare_a_form_the_builder_cannot_read(rules_package):
    root, _ = rules_package
    result = build.build_claim(
        source_root=root,
        package="demo-skill",
        responsibility_key="install-content",
        kind="plugin",
        interface_id="penguin-plugin",
    )
    assert result.status == build.CLAIM_BUILT, result.reason
    assert result.claim["capability"]["kind"] == "plugin"
    assert result.claim["how"]["interface"] == {"id": "penguin-plugin", "version": "1"}
    assert result.receipt["classification"]["kind"]["from"] == "argument"
    assert validate_claim(result.claim) == []


def test_unknown_kind_is_refused(rules_package):
    root, _ = rules_package
    with pytest.raises(ValueError):
        build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content", kind="magic")


def test_obligation_limit_is_reported_when_it_cuts(tmp_path):
    body = "## Rules\n\n" + "".join(f"- Never do thing {index} before acting.\n" for index in range(5))
    write_package(tmp_path, "demo-skill", body=body)
    result = build.build_claim(
        source_root=tmp_path,
        package="demo-skill",
        responsibility_key="install-content",
        obligation_limit=2,
    )
    assert result.status == build.CLAIM_BUILT, result.reason
    assert len(result.claim["what"]["obligations"]) == 2
    assert result.receipt["obligations"]["truncated"] is True


def test_receipt_keeps_the_understand_trail(tmp_path):
    write_package(tmp_path, "demo-skill", body="## Rules\n\n- Never act.\n")
    result = build.build_claim(source_root=tmp_path, package="demo-skill", responsibility_key="install-content")
    assert result.receipt["understand"]["status"] in {"COMPLETE", "PARTIAL"}
    assert result.receipt["detection"] == {"kind": "skill", "reason": "存在 SKILL.md", "decoder": "READY"}
    assert result.receipt["understand"]["request_id"].startswith("claim-build:demo-skill:")
    assert result.receipt["obligations"]["selected"] == len(result.claim["what"]["obligations"])
    assert result.receipt["claim_digest"] == claim_digest(result.claim)
    assert result.receipt["evidence_used"] == len(result.claim["why"]["evidence"])


def test_a_hand_off_to_another_skill_becomes_a_declared_exclusion(tmp_path):
    body = (
        "## Rules\n\n- Never install content you have not read.\n\n"
        "To install onto the whole server instead, use the `port-plugins` skill.\n"
    )
    write_package(tmp_path, "port-skills", body=body)
    result = build.build_claim(source_root=tmp_path, package="port-skills", responsibility_key="port-external-package")
    assert result.status == build.CLAIM_BUILT, result.reason
    excludes = result.claim["what"]["applicability"]["exclude"]
    assert [item["statement"] for item in excludes] == ["To install onto the whole server instead, use the `port-plugins` skill."]
    assert "what.applicability.exclude" not in {row["field"] for row in result.claim["why"]["unknowns"]}
    evidence = next(row for row in result.claim["why"]["evidence"] if row["id"] == excludes[0]["evidence"][0])
    assert evidence["quote"].startswith("To install onto the whole server instead")
    assert evidence["field"] == "what.applicability.exclude[0]"


def test_mentioning_another_skill_without_a_hand_off_is_not_a_boundary(tmp_path):
    body = "## Rules\n\n- Never install unread content.\n\nThe `port-plugins` skill installs plugins for a whole server.\n"
    write_package(tmp_path, "port-skills", body=body)
    result = build.build_claim(source_root=tmp_path, package="port-skills", responsibility_key="port-external-package")
    assert result.claim["what"]["applicability"]["exclude"] == []
    assert "what.applicability.exclude" in {row["field"] for row in result.claim["why"]["unknowns"]}


def test_a_hand_off_to_the_capability_itself_is_not_a_boundary(tmp_path):
    body = "## Rules\n\n- Never install unread content.\n\nTo review it first instead, use the `port-skills` skill.\n"
    write_package(tmp_path, "port-skills", body=body)
    result = build.build_claim(source_root=tmp_path, package="port-skills", responsibility_key="port-external-package")
    assert result.claim["what"]["applicability"]["exclude"] == []


def test_two_packages_that_hand_off_to_each_other_compare_as_a_split(tmp_path):
    write_package(
        tmp_path, "port-skills",
        body="## Rules\n\n- Never install unread content.\n\nFor a whole-server install instead, use the `port-plugins` skill.\n",
    )
    write_package(
        tmp_path, "port-plugins",
        body="## Rules\n\n- Never install unread content.\n\nFor one agent only instead, use the `port-skills` skill.\n",
    )
    left = build.build_claim(source_root=tmp_path, package="port-skills", responsibility_key="port-external-package")
    right = build.build_claim(source_root=tmp_path, package="port-plugins", responsibility_key="port-external-package")
    result = compare_claims(left.claim, right.claim)
    assert (result["relation"], result["action"]) == ("COMPLEMENTARY", "KEEP_BOTH")
    assert "分工" in result["reason"]


def test_result_is_json_ready_for_a_reader(rules_package):
    root, _ = rules_package
    built = build.build_claim(source_root=root, package="demo-skill", responsibility_key="install-content")
    refused = build.build_claim(source_root=root, package="missing", responsibility_key="install-content")
    for result in (built, refused):
        payload = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        assert payload["status"] == result.status
        assert set(payload) == {"status", "reason", "claim", "receipt", "violations"}
    assert json.loads(json.dumps(built.to_dict()))["claim"]["capability"]["id"] == "demo-skill"
    assert json.loads(json.dumps(refused.to_dict()))["claim"] is None


def test_cli_writes_the_claim_and_refuses_without_one(tmp_path, capsys):
    write_package(tmp_path, "demo-skill", body="## Rules\n\n- Never act.\n")
    target = tmp_path / "out" / "demo-skill.claim.json"
    code = build._main([
        "--source-root", str(tmp_path),
        "--package", "demo-skill",
        "--responsibility-key", "install-content",
        "--out", str(target),
    ])
    assert code == 0
    written = json.loads(target.read_text(encoding="utf-8"))
    assert validate_claim(written) == []
    capsys.readouterr()

    write_package(tmp_path / "empty-root", "silent-skill", body="# Silent\n\nNo duties here.\n")
    code = build._main([
        "--source-root", str(tmp_path / "empty-root"),
        "--package", "silent-skill",
        "--responsibility-key", "install-content",
        "--out", str(tmp_path / "never" / "silent.claim.json"),
    ])
    assert code == 2
    assert not (tmp_path / "never").exists()
