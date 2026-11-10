"""An entity says what kind of thing it is; a name alone is a claim about something."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agent_runtime.contracts import ModelResponse

from catalyst_platform.ontology_types import BUSINESS_TYPES, STARTER_CONCEPTS, Concept, ConceptSet
from catalyst_platform.semantic_score import score_wiki
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.wiki import ProjectWiki

REPO = Path(__file__).resolve().parents[1]


class _OneEntity:
    """One source, one entity, and whichever type the test asks for."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, business_type="Position", kind="entity"):
        self.business_type = business_type
        self.kind = kind
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        item = {"kind": self.kind, "key": "review_lead", "meaning": "复核负责人",
                "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}
        if self.business_type is not None:
            item["business_type"] = self.business_type
        return ModelResponse(content=json.dumps({"items": [item]}, ensure_ascii=False),
                             finish_reason="stop")


def _run(tmp_path, provider, concepts=None):
    source = tmp_path / "org.md"
    source.write_text("复核负责人负责单据复核。", encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("business-type", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider,
        **({"concepts": concepts} if concepts is not None else {}))


def _cli(*args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    return completed.returncode, json.loads(completed.stdout) if completed.stdout.strip() else {}


class _OneRelation:
    """Two named things and the hierarchy sentence that joins them."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, predicate="隶属"):
        self.predicate = predicate
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "tech_dept", "meaning": "技术部",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [evidence]},
            {"kind": "entity", "key": "tech_lead", "meaning": "技术主管",
             "business_type": "Position", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [evidence]},
            {"kind": "relation", "key": "tech_lead|belongs|tech_dept",
             "subject": "tech_lead", "predicate": self.predicate, "object": "tech_dept",
             "meaning": "技术主管 隶属 技术部",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
        ]}, ensure_ascii=False), finish_reason="stop")


def test_a_hierarchy_line_becomes_a_relation_of_the_six(tmp_path):
    source = tmp_path / "org.md"
    source.write_text("技术部：技术主管 隶属 技术部。", encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("hierarchy", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=_OneRelation())
    relations = [item for item in result.semantic_candidate.items if item.kind == "relation"]

    assert len(relations) == 1
    assert relations[0].predicate == "隶属"
    assert (relations[0].subject, relations[0].object) == ("tech_lead", "tech_dept")


def test_the_vocabulary_is_the_one_of_the_standard():
    assert list(BUSINESS_TYPES) == [
        "Department", "Position", "Responsibility", "ProcessStep",
        "Deliverable", "Rule", "Exception", "Metric",
        # An org chart names three kinds of thing that are not departments at all.
        "GovernanceBody", "BusinessUnit", "ExternalParty",
    ]


def test_a_governing_body_is_not_a_department(tmp_path):
    result = _run(tmp_path, _OneEntity(business_type="governancebody"))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert [item.business_type for item in entities] == ["GovernanceBody"]


def test_an_entity_may_say_what_kind_of_thing_it_is(tmp_path):
    result = _run(tmp_path, _OneEntity(business_type="Position"))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert len(entities) == 1
    assert entities[0].business_type == "Position"


def test_a_type_outside_the_scope_is_counted_and_the_entity_is_kept(tmp_path):
    result = _run(tmp_path, _OneEntity(business_type="Thing"))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]
    attribution = result.producer_attribution

    # The name is what the source spells, so it stays; the type is the scope's decision
    # and is named instead of silently costing the row.
    assert [item.business_type for item in entities] == [None]
    assert attribution["concept_unmapped"] == [{"spelling": "Thing", "entities": 1}]
    assert attribution["concept_unmapped_count"] == 1
    assert attribution["dropped_invalid_items"] == {}


def test_a_scope_concept_is_accepted_and_named_in_the_prompt(tmp_path):
    pack = ConceptSet((*STARTER_CONCEPTS, Concept("Ward", "病区", "Organization", "病区、护理单元")),
                      "scope-1", "declared")
    provider = _OneEntity(business_type="ward")
    result = _run(tmp_path, provider, concepts=pack)

    assert [item.business_type for item in result.semantic_candidate.items
            if item.kind == "entity"] == ["Ward"]
    assert "Ward（病区，Organization）" in provider.requests[0].messages[0].content
    assert result.producer_attribution["concept_set_version"] == "scope-1"


def test_a_type_on_something_that_is_not_an_entity_is_refused(tmp_path):
    result = _run(tmp_path, _OneEntity(business_type="Position", kind="claim"))
    dropped = result.producer_attribution["dropped_invalid_items"]

    assert dropped.get("business_type_not_applicable") == 1


def test_a_lowercase_type_is_rewritten_to_the_one_spelling(tmp_path):
    result = _run(tmp_path, _OneEntity(business_type="position"))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert [item.business_type for item in entities] == ["Position"]


def test_an_entity_without_a_type_still_comes_through(tmp_path):
    result = _run(tmp_path, _OneEntity(business_type=None))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert len(entities) == 1
    assert entities[0].business_type is None


def test_the_wiki_stores_the_type_and_the_score_counts_it(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "org.md"
    lines = [
        "# 合成组织",
        "Entity: review_lead | 复核负责人",
        "Entity: release_gate | 发布放行门",
    ]
    source_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    common = ["--workspace", str(workspace), "--wiki-root", str(roots),
              "--enterprise-id", "synthetic-enterprise", "--project-id", "business-type"]

    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0 and staged["status"] == "success", staged
    source = staged["result"]

    def evidence(line_no: int) -> dict:
        quote = lines[line_no - 1]
        return {"line_start": line_no, "line_end": line_no, "quote": quote,
                "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest()}

    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [
            {"kind": "entity", "canonical_key": "review_lead", "display_name": "复核负责人",
             "business_type": "Position", "evidence_class": "observed_from_source",
             "evidence": evidence(2)},
            {"kind": "entity", "canonical_key": "release_gate", "display_name": "发布放行门",
             "evidence_class": "observed_from_source", "evidence": evidence(3)},
        ],
    }
    schema = Draft202012Validator(json.loads(
        (REPO / "schemas/external_candidate_submission_v2.schema.json").read_text(encoding="utf-8")))
    assert not list(schema.iter_errors(submission))

    submission_path = tmp_path / "candidate.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")
    code, proposed = _cli("ontology", "external", "submit-v2", *common,
                          "--correlation-id", "business-type-v2", "--submission", str(submission_path))
    assert code == 0 and proposed["status"] == "success", proposed

    wiki = ProjectWiki(workspace.resolve(), [roots.resolve()], enterprise_id="synthetic-enterprise",
                       project_id="business-type")
    entries = wiki.semantic_state()["candidates"][proposed["result"]["candidate_id"]]["entries"]
    typed = {entry["canonical_key"]: entry.get("business_type")
             for entry in entries if entry["kind"] == "entity"}
    assert typed == {"review_lead": "Position", "release_gate": None}

    measured = {row["id"]: row for row in score_wiki(wiki)["metrics"]}
    assert measured[2]["value"] == 0.5
    assert measured[2]["note"] == "1/2 个实体带概念集内的 business_type（概念集 starter-1）"


def test_a_type_outside_the_vocabulary_is_refused_by_the_store(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "org.md"
    lines = ["# 合成组织", "Entity: review_lead | 复核负责人"]
    source_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    common = ["--workspace", str(workspace), "--wiki-root", str(roots),
              "--enterprise-id", "synthetic-enterprise", "--project-id", "business-type"]

    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0, staged
    source = staged["result"]
    quote = lines[1]
    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [
            {"kind": "entity", "canonical_key": "review_lead", "display_name": "复核负责人",
             "business_type": "Job", "evidence_class": "observed_from_source",
             "evidence": {"line_start": 2, "line_end": 2, "quote": quote,
                          "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest()}},
        ],
    }
    submission_path = tmp_path / "candidate.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")

    code, refused = _cli("ontology", "external", "submit-v2", *common,
                         "--correlation-id", "business-type-bad", "--submission", str(submission_path))
    assert code == 1
    assert refused["error"]["code"] == "invalid_business_type"


def _submit_typed_entity(common: list[str], source: dict, lines: list[str], business_type: str,
                         correlation: str) -> tuple[int, dict]:
    quote = lines[1]
    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [
            {"kind": "entity", "canonical_key": "ward_a", "display_name": "病区甲",
             "business_type": business_type, "evidence_class": "observed_from_source",
             "evidence": {"line_start": 2, "line_end": 2, "quote": quote,
                          "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest()}},
        ],
    }
    submission_path = Path(common[1]).parent / f"candidate-{correlation}.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")
    return _cli("ontology", "external", "submit-v2", *common,
                "--correlation-id", correlation, "--submission", str(submission_path))


def test_a_concept_the_scope_declared_is_stored_under_its_own_id(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "hospital.md"
    lines = ["# 合成医院", "Entity: ward_a | 病区甲"]
    source_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    common = ["--workspace", str(workspace), "--wiki-root", str(roots),
              "--enterprise-id", "synthetic-enterprise", "--project-id", "hospital"]

    code, defined = _cli("ontology", "concepts", "define", *common,
                         "--concept-id", "Ward", "--name", "病区", "--meta-kind", "Organization",
                         "--criteria", "病区、护理单元", "--reason", "医院资料里有病区")
    assert code == 0, defined
    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0, staged
    code, proposed = _submit_typed_entity(common, staged["result"], lines, "病区", "ward-declared")
    assert code == 0, proposed

    wiki = ProjectWiki(workspace.resolve(), [roots.resolve()], enterprise_id="synthetic-enterprise",
                       project_id="hospital")
    entries = wiki.semantic_state()["candidates"][proposed["result"]["candidate_id"]]["entries"]
    assert [entry.get("business_type") for entry in entries if entry["kind"] == "entity"] == ["Ward"]
