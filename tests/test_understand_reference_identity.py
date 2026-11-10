"""The method text is part of a card's identity, not just its file path.

The modeling method reaches the model from `references/` (18K characters in
`ontology-generator.md`), while `instruction_sha256` covers only the Skill body.
Without a content hash for each reference, editing one line of the method leaves
every recorded identity unchanged, and two cards read under different methods
compare as if they shared one (independent audit, 2026-10-31, finding F).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from catalyst_platform.understand_manifest import _SkillResolver, _generator_method


def _write_skill(root: Path, reference_body: str) -> Path:
    skill_dir = root / "understand-enterprise-semantics"
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: understand-enterprise-semantics\nversion: 0.1.0\ndescription: model\n---\n"
        "Separate explicit entities from claims.\n",
        encoding="utf-8",
    )
    reference = skill_dir / "references" / "ontology-generator.md"
    reference.write_text(reference_body, encoding="utf-8")
    return reference


def test_reference_content_is_hashed_and_fed_to_the_model(tmp_path: Path):
    body = "# Method B: scene-first design\n\nStart from the business decision.\n"
    reference = _write_skill(tmp_path / "skills", body)

    skill = _SkillResolver(tmp_path / "skills").load(
        ["understand-enterprise-semantics"], progressive=True
    )[0]

    relative = "understand-enterprise-semantics/references/ontology-generator.md"
    assert skill.loaded_reference_paths == (relative,)
    assert skill.reference_sha256 == (
        (relative, hashlib.sha256(body.encode("utf-8")).hexdigest()),
    )
    # The method text still reaches the call, and the hash names the text it came from.
    assert "Start from the business decision." in _generator_method((skill,))

    reference.write_text(body + "\nNever merge two units by name alone.\n", encoding="utf-8")
    changed = _SkillResolver(tmp_path / "skills").load(
        ["understand-enterprise-semantics"], progressive=True
    )[0]
    assert changed.loaded_reference_paths == skill.loaded_reference_paths
    assert changed.reference_sha256 != skill.reference_sha256
    assert changed.instruction_sha256 == skill.instruction_sha256
