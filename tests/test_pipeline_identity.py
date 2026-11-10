"""A card names the prompts it was asked with and, now, the code that read the answer.

Two live cards of the same deck carried the same method package sha256 and the same card
sha256, and still differed structurally: `live-m4b` predates scope-state inheritance, so
it has no `scope_state_inheritance` and 17 duplicate-entity merges, while `live-m4e` has
3 inherited units and 1 merge. Nothing in either card said the code had changed, so the
two scores looked comparable when they were not.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from agent_runtime.contracts import ModelResponse
from catalyst_platform.pipeline_identity import digest_of, pipeline_sha256
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


def test_the_digest_is_stable_and_named_the_same_every_time():
    first = pipeline_sha256()
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert pipeline_sha256() == first


def test_a_changed_module_changes_the_digest(tmp_path):
    (tmp_path / "alpha.py").write_text("A = 1\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("B = 2\n", encoding="utf-8")
    before = digest_of(tmp_path)
    (tmp_path / "beta.py").write_text("B = 3\n", encoding="utf-8")
    assert digest_of(tmp_path) != before


def test_a_renamed_module_changes_the_digest(tmp_path):
    """The name is hashed with the bytes: a rename is a different pipeline too."""
    (tmp_path / "alpha.py").write_text("A = 1\n", encoding="utf-8")
    before = digest_of(tmp_path)
    (tmp_path / "alpha.py").rename(tmp_path / "gamma.py")
    assert digest_of(tmp_path) != before


def test_a_file_that_is_not_a_module_is_not_part_of_the_pipeline(tmp_path):
    (tmp_path / "alpha.py").write_text("A = 1\n", encoding="utf-8")
    before = digest_of(tmp_path)
    (tmp_path / "notes.txt").write_text("rewritten\n", encoding="utf-8")
    assert digest_of(tmp_path) == before


class _OneEntity:
    """One answer per unit, citing the line that spells the name."""

    model = "stub-pipeline-identity"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        row = next(item for item in evidence if "财务部门" in item["quote"])
        item = {"kind": "entity", "key": "finance", "meaning": "财务部门",
                "evidence_class": "SOURCE_DIRECT", "evidence_refs": [row["evidence_id"]]}
        return ModelResponse(content=json.dumps({"items": [item]}, ensure_ascii=False),
                             finish_reason="stop")


def test_the_card_attributes_the_code_that_read_the_answer(tmp_path):
    source = tmp_path / "deck.md"
    source.write_text("水利集团现有组织结构：\n财务部门\n", encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("pipeline-identity", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_pipeline",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_OneEntity())
    assert result.producer_attribution["pipeline_sha256"] == pipeline_sha256()


def test_the_source_reader_is_part_of_the_pipeline_digest(tmp_path):
    """What a card can see is decided by understand_sources; a reader change is a code change.

    The deck cards of 2026-10-31 and the 2026-11-01 card of the same deck were read one
    run per cell and one text box per cell respectively. Nothing about that difference is
    visible in the source manifest or the method package, so it has to be visible here: the
    reader module is inside the digest, and a one-character change to it moves the number.
    """
    from catalyst_platform import understand_sources
    package = understand_sources.__file__
    for path in Path(package).parent.glob("*.py"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    before = digest_of(tmp_path)
    reader = tmp_path / "understand_sources.py"
    reader.write_bytes(reader.read_bytes() + b"\n")
    assert digest_of(tmp_path) != before
