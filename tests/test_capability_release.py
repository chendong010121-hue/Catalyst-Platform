"""The release file describes the tree beside it, and says what it does not cover."""
from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from catalyst_platform.capability_release import (
    METHOD_PATH,
    NOT_SHIPPED,
    RUN_IDENTITY_FIELDS,
    differences,
    entry_points,
    implementation_digest,
    manifest,
    method_identity,
    repository_root,
)

ROOT = repository_root()
STORED = ROOT / "docs" / "engineering" / "CAPABILITY_RELEASE_20261103.json"


def test_the_stored_release_still_describes_this_tree():
    assert STORED.is_file(), "the release identity file is missing"
    stored = json.loads(STORED.read_text(encoding="utf-8"))
    assert differences(stored, manifest(ROOT)) == []


def test_every_named_entry_point_exists_and_is_hashed():
    rows = entry_points(ROOT)
    assert len(rows) >= 8
    paths = [row["path"] for row in rows]
    assert len(set(paths)) == len(paths), "one file is named twice"
    for row in rows:
        data = (ROOT / row["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        assert row["role"].strip()


def test_one_changed_byte_changes_the_release_identity():
    rows = entry_points(ROOT)
    before = implementation_digest(rows)
    changed = [dict(row) for row in rows]
    changed[0]["sha256"] = "0" * 64
    assert implementation_digest(changed) != before


def test_the_shipped_method_package_is_the_one_admission_accepts():
    method = method_identity(ROOT)
    assert method["component_id"] == "enterprise-ontology"
    assert method["version"] == "0.1.0"
    assert method["skill_name"] == "understand-enterprise-semantics"
    assert method["interface"] == "semantic-proposal.v1"
    assert method["provides"] == ["enterprise-ontology"]
    assert len(method["package_sha256"]) == 64
    assert set(method["files"]) == {
        "SKILL.md",
        "references/ontology-catalog-relations-v2.md",
        "references/ontology-catalog-relations.md",
        "references/ontology-evolver.md",
        "references/ontology-generator.md",
        "references/ontology-inventory-binding.md",
        "references/ontology-object-catalog-v2.md",
        "references/ontology-object-catalog.md",
        "references/ontology-verifier.md",
    }


def test_an_edited_package_file_is_refused_by_admission(tmp_path):
    package = tmp_path / "enterprise-ontology" / "0.1.0"
    shutil.copytree(ROOT / METHOD_PATH, package)
    target = package / "SKILL.md"
    target.write_bytes(target.read_bytes() + b"\n")
    from catalyst_platform.components import ComponentError, discover_local_component

    with pytest.raises(ComponentError, match="SHA-256|digest"):
        discover_local_component(package)


def test_a_package_file_that_is_not_in_the_manifest_is_refused(tmp_path):
    package = tmp_path / "enterprise-ontology" / "0.1.0"
    shutil.copytree(ROOT / METHOD_PATH, package)
    (package / "references" / "extra.md").write_text("# extra\n", encoding="utf-8")
    from catalyst_platform.components import ComponentError, discover_local_component

    with pytest.raises(ComponentError, match="unlisted"):
        discover_local_component(package)


def test_research_trees_are_named_and_are_not_in_this_repository():
    assert NOT_SHIPPED
    for relative, what in NOT_SHIPPED:
        assert what.strip()
        assert not (ROOT / relative).exists(), f"{relative} is inside the product tree"


def test_the_release_states_its_limits_and_run_identity():
    body = manifest(ROOT)
    assert body["limits"] and all(line.strip() for line in body["limits"])
    assert tuple(body["run_identity_fields"]) == RUN_IDENTITY_FIELDS
    assert set(RUN_IDENTITY_FIELDS) == {
        "method", "implementation", "concepts", "extraction_mode", "repairs", "sources"}
    assert body["interface"] == "semantic-proposal.v1"
    assert body["extraction_modes"] == ["single_stage", "source_local_two_stage"]
    assert body["concepts"]["version"] == "starter-1"
    assert body["concepts"]["count"] == 11
    assert len(body["concepts"]["digest"]) == 64


def test_the_check_names_what_drifted():
    stored = json.loads(STORED.read_text(encoding="utf-8"))
    current = manifest(ROOT)
    drifted = json.loads(json.dumps(current))
    drifted["method"]["package_sha256"] = "0" * 64
    lines = differences(stored, drifted)
    assert lines and any("package_sha256" in line for line in lines)


def test_the_release_names_enable_and_verify_commands():
    body = manifest(ROOT)
    assert any("component admit" in line for line in body["enable"])
    assert any("component activate" in line for line in body["enable"])
    assert any("release_manifest.py --check" in line for line in body["verify"])
