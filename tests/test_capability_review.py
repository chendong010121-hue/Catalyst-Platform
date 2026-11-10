"""Read-only capability review over a workspace's claims."""
import json
import shutil
from pathlib import Path

from catalyst_platform import capability_review as review

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "examples" / "capability_claims"


def write_claim(directory, name, claim):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.claim.json").write_text(json.dumps(claim, ensure_ascii=False), encoding="utf-8")


def sample(name):
    return json.loads((SAMPLES / f"{name}.claim.json").read_text(encoding="utf-8"))


def test_empty_workspace_falls_back_to_the_shipped_examples(tmp_path):
    result = review.review(tmp_path)
    assert result["source"] == "examples"
    assert result["write_enabled"] is False
    assert result["scope"] == "READ_ONLY_COMPARISON_NO_WIKI_WRITE"
    assert [item["relation"] for item in result["items"]] == ["COMPLEMENTARY"]
    pair = result["items"][0]
    assert {pair["left"]["id"], pair["right"]["id"]} == {"skill-porting", "plugin-porting"}
    assert pair["coverage"]["matched"] >= 0


def test_workspace_claims_take_precedence_over_examples(tmp_path):
    claims = tmp_path / ".catalyst" / "capability-claims"
    write_claim(claims, "skill", sample("skill-porting"))
    result = review.review(tmp_path)
    assert result["source"] == "workspace"
    assert result["claims_dir"] == str(claims)
    assert result["items"] == []
    assert len(result["claims"]) == 1


def test_competing_claims_of_the_same_duty_surface_for_review(tmp_path):
    claims = tmp_path / ".catalyst" / "capability-claims"
    base = sample("skill-porting")
    other = json.loads(json.dumps(base))
    other["capability"]["id"] = "skill-porting-alt"
    other["capability"]["version"] = "1.0.0"
    other["what"]["obligations"].append({
        "statement": "安装时把技能里的可执行脚本一并复制到目标目录",
        "evidence": [other["why"]["evidence"][0]["id"]],
        "evidence_class": "EXPLICIT",
    })
    write_claim(claims, "a", base)
    write_claim(claims, "b", other)
    result = review.review(tmp_path)
    assert result["source"] == "workspace"
    (pair,) = result["items"]
    assert (pair["relation"], pair["action"]) == ("SIMILAR", "EVALUATE_IN_DEVELOPMENT")
    assert pair["requires_owner_confirmation"] is True
    assert pair["evaluation_questions"]
    assert pair["coverage"]["right_only"] == 1


def test_different_responsibilities_are_not_paired(tmp_path):
    claims = tmp_path / ".catalyst" / "capability-claims"
    base = sample("skill-porting")
    other = json.loads(json.dumps(base))
    other["capability"]["id"] = "report-writer"
    other["capability"]["responsibility_key"] = "write-reports"
    write_claim(claims, "a", base)
    write_claim(claims, "b", other)
    result = review.review(tmp_path)
    assert len(result["claims"]) == 2
    assert result["items"] == []


def test_invalid_claim_is_reported_and_excluded(tmp_path):
    claims = tmp_path / ".catalyst" / "capability-claims"
    broken = sample("skill-porting")
    broken["what"]["obligations"][0]["evidence"] = []
    write_claim(claims, "broken", broken)
    write_claim(claims, "good", sample("plugin-porting"))
    result = review.review(tmp_path)
    assert [error["file"] for error in result["errors"]] == ["broken.claim.json"]
    assert len(result["claims"]) == 1
    assert result["items"] == []


def test_unreadable_claim_file_does_not_break_the_page(tmp_path):
    claims = tmp_path / ".catalyst" / "capability-claims"
    claims.mkdir(parents=True)
    (claims / "junk.claim.json").write_text("{not json", encoding="utf-8")
    result = review.review(tmp_path)
    assert result["source"] == "workspace"
    assert result["errors"][0]["violation"].startswith("unreadable:")
    assert result["claims"] == []


def test_review_never_creates_the_claims_directory(tmp_path):
    review.review(tmp_path)
    assert not (tmp_path / ".catalyst").exists()


def test_pairs_are_ordered_by_relation_strength(tmp_path):
    claims = tmp_path / ".catalyst" / "capability-claims"
    base = sample("skill-porting")
    same = json.loads(json.dumps(base))
    same["capability"]["version"] = "2026.11.01.1"
    distinct = json.loads(json.dumps(base))
    distinct["capability"]["id"] = "other"
    distinct["capability"]["responsibility_key"] = "elsewhere"
    write_claim(claims, "a", base)
    write_claim(claims, "b", same)
    write_claim(claims, "c", distinct)
    result = review.review(tmp_path)
    assert [item["relation"] for item in result["items"]] == ["SAME"]
    assert result["truncated"] is False
