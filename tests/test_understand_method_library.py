"""The enterprise-semantics method library ships with the product and stays lazy.

Onboarding step A2: the capability line's own skill package must carry the same
method references the ontology line carries, the port must load them only for a
request that asked for semantic depth, and the Understand capability must remain
registered but inactive in the plugin profile.  No test here calls a model.
"""
from __future__ import annotations

from pathlib import Path

from catalyst_platform.understand_only import (
    _SKILL_ROOT,
    _SKILL_STRATEGIES,
    _SkillResolver,
)
from catalyst_platform.workbench import CatalystWorkbench

PACKAGE = "understand-enterprise-semantics"

METHOD_REFERENCES = (
    "ontology-catalog-relations-v2.md",
    "ontology-catalog-relations.md",
    "ontology-evolver.md",
    "ontology-generator.md",
    "ontology-inventory-binding.md",
    "ontology-object-catalog-v2.md",
    "ontology-object-catalog.md",
    "ontology-verifier.md",
)


def test_method_library_ships_inside_the_default_skill_root():
    root = _SKILL_ROOT.resolve()
    folder = (root / PACKAGE / "references").resolve()
    assert folder.is_dir()
    assert folder.is_relative_to(root)
    assert not folder.is_symlink()
    assert sorted(path.name for path in folder.iterdir() if path.is_file()) == list(METHOD_REFERENCES)
    for name in METHOD_REFERENCES:
        path = folder / name
        assert not path.is_symlink()
        assert 0 < path.stat().st_size <= 64 * 1024


def test_references_load_only_when_the_request_asked_for_semantic_depth():
    resolver = _SkillResolver()
    lazy = resolver.load((PACKAGE,), progressive=False)
    deep = resolver.load((PACKAGE,), progressive=True)
    assert lazy[0].loaded_reference_paths == ()
    assert deep[0].loaded_reference_paths == tuple(
        sorted(f"{PACKAGE}/references/{name}" for name in METHOD_REFERENCES)
    )
    assert deep[0].skill_id == PACKAGE
    assert len(deep[0].reference_texts) == len(METHOD_REFERENCES)


def test_every_declared_skill_still_resolves_from_the_shipped_root():
    resolver = _SkillResolver()
    loaded = resolver.load(tuple(_SKILL_STRATEGIES), progressive=True)
    assert {item.skill_id for item in loaded} == set(_SKILL_STRATEGIES)
    for item in loaded:
        assert item.version
        assert item.instructions.strip()


def test_understand_stays_registered_but_inactive(tmp_path: Path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    app = CatalystWorkbench(workspace=workspace, wiki_roots=[tmp_path])
    assert app.plugins.service("understand.port") is not None
    # Registered, but not active: the catalog only lists what has been activated,
    # so an onboarded capability is invisible to callers until someone activates it.
    assert app._catalog.is_active("understand", "1.0.0") is False
    assert all(item.id != "understand" for item in app._catalog.list())
    app._catalog.activate("understand", "1.0.0")
    assert app._catalog.is_active("understand", "1.0.0") is True
    assert any(item.id == "understand" for item in app._catalog.list())
    app._catalog.deactivate("understand", "1.0.0")
    assert app._catalog.is_active("understand", "1.0.0") is False
