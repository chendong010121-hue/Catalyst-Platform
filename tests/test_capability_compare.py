"""Deterministic claim comparison: a relation hypothesis, never a winner."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from catalyst_platform import capability_compare as cmp
from catalyst_platform import capability_state as cs

SAMPLES = Path(__file__).resolve().parent.parent / "examples" / "capability_claims"


def sample(name):
    return json.loads((SAMPLES / f"{name}.claim.json").read_text(encoding="utf-8"))


@pytest.fixture
def skill():
    return sample("skill-porting")


@pytest.fixture
def plugin():
    return sample("plugin-porting")


def variant(claim, *, id=None, version=None, key=None, extra_obligation=None):
    clone = copy.deepcopy(claim)
    if id:
        clone["capability"]["id"] = id
    if version:
        clone["capability"]["version"] = version
    if key:
        clone["capability"]["responsibility_key"] = key
    if extra_obligation:
        clone["what"]["obligations"].append({
            "statement": extra_obligation,
            "evidence": [clone["why"]["evidence"][0]["id"]],
            "evidence_class": "EXPLICIT",
        })
    return clone


def test_identical_claims_are_the_same_capability_and_a_no_op(skill):
    result = cmp.compare_claims(skill, skill)
    assert (result["relation"], result["action"]) == (cs.SAME, cs.IGNORE_DUPLICATE)
    assert result["blocked"] == []
    assert result["requires_owner_confirmation"] is False
    assert result["evaluation_questions"] == []


def test_new_version_of_one_capability_is_a_replacement_decision(skill):
    newer = variant(skill, version="2026.11.01.1")
    result = cmp.compare_claims(skill, newer)
    assert (result["relation"], result["action"]) == (cs.SAME, cs.REPLACE)
    assert result["requires_owner_confirmation"] is True


def test_real_samples_share_a_responsibility_and_declare_where_each_one_stops(skill, plugin):
    result = cmp.compare_claims(skill, plugin)
    assert result["relation"] == cs.COMPLEMENTARY
    assert result["action"] == cs.KEEP_BOTH
    assert "分工" in result["reason"]
    assert result["evaluation_questions"] == []


def test_same_responsibility_and_form_is_similar_and_asks_for_evaluation(skill):
    other = variant(skill, id="skill-porting-alt", version="1.0.0",
                    extra_obligation="安装时把技能里的可执行脚本一并复制到目标目录")
    result = cmp.compare_claims(skill, other)
    assert (result["relation"], result["action"]) == (cs.SIMILAR, cs.EVALUATE_IN_DEVELOPMENT)
    assert result["requires_owner_confirmation"] is True
    assert result["evaluation_questions"]
    assert "可执行脚本" in result["evaluation_questions"][0]


def test_different_responsibility_is_distinct_and_never_compared_as_competitors(skill):
    unrelated = variant(skill, id="report-writer", key="write-reports")
    result = cmp.compare_claims(skill, unrelated)
    assert (result["relation"], result["action"]) == (cs.DISTINCT, cs.KEEP_BOTH)


def test_same_id_with_two_responsibility_keys_is_inconsistent_metadata(skill):
    broken = variant(skill, key="something-else")
    result = cmp.compare_claims(skill, broken)
    assert result["relation"] == cs.COMPARISON_UNKNOWN
    assert result["action"] == cs.NEEDS_HUMAN_REVIEW
    assert "自相矛盾" in result["reason"]


def test_comparator_never_claims_superiority(skill, plugin):
    for other in (skill, plugin, variant(skill, id="x", version="9.9.9")):
        assert cmp.compare_claims(skill, other)["relation"] != "SUPERSEDES"


def test_invalid_claim_is_refused_before_comparison(skill):
    broken = copy.deepcopy(skill)
    broken["what"]["obligations"][0]["evidence"] = []
    with pytest.raises(ValueError):
        cmp.compare_claims(skill, broken)


def test_result_is_deterministic_symmetric_and_does_not_mutate_inputs(skill, plugin):
    before = copy.deepcopy((skill, plugin))
    first = cmp.compare_claims(skill, plugin)
    second = cmp.compare_claims(skill, plugin)
    assert first == second
    assert first["input_digest"] == cmp.compare_claims(plugin, skill)["input_digest"]
    assert (skill, plugin) == before


def test_field_rows_separate_exact_normalized_and_behavioural(skill, plugin):
    rows = {row["field"]: row for row in cmp.compare_claims(skill, plugin)["fields"]}
    assert rows["capability.id"]["comparability"] == "exact"
    assert rows["capability.id"]["same"] is False
    assert rows["what.obligations"]["comparability"] == "normalized"
    assert "matched" in rows["what.obligations"]
    assert all(row.get("comparable") is not False for row in rows.values())


def test_comparison_sorting_puts_the_same_capability_first(skill):
    same = variant(skill, version="2026.12.01.1")
    other = variant(skill, id="other", key="elsewhere")
    ordered = cmp.compare_many(skill, [other, same])
    assert ordered[0]["relation"] == cs.SAME
    assert ordered[-1]["relation"] == cs.DISTINCT


def test_similarity_threshold_is_fixed_and_language_agnostic():
    assert cmp.similarity("Read every file before installing", "read every file before installing") == 1.0
    assert cmp.similarity("安装前通读每一个文件", "安装前通读每个文件") >= cmp.MATCH_THRESHOLD
    assert cmp.similarity("安装前通读每一个文件", "生成季度财务报告") < 0.3

def base_claim(claim_id, *, exclude=(), include=(), version="1.0.0"):
    """A minimal valid claim, so a boundary case carries only what it is about."""
    evidence = []
    unknowns = []

    def bind(text, path):
        identifier = f"e{len(evidence) + 1}"
        evidence.append({
            "id": identifier,
            "source_id": "test",
            "revision": "1",
            "locator": "SKILL.md:L1",
            "quote": text,
            "span_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "strength": "DIRECT_QUOTE",
            "field": path,
        })
        return {"statement": text, "evidence": [identifier], "evidence_class": "EXPLICIT"}

    statement = "把外部包变成当前平台可用的能力"
    obligation = bind("安装前通读每一个文件", "what.obligations[0]")
    include_items = [bind(text, f"what.applicability.include[{index}]") for index, text in enumerate(include)]
    exclude_items = [bind(text, f"what.applicability.exclude[{index}]") for index, text in enumerate(exclude)]
    for field in ("what.known_limits", "what.failure_modes", "how.side_effects", "how.permissions", "what.performance"):
        unknowns.append({"field": field, "reason": "静态构建未声明"})
    if not include:
        unknowns.append({"field": "what.applicability.include", "reason": "未声明适用范围"})
    if not exclude:
        unknowns.append({"field": "what.applicability.exclude", "reason": "未声明不适用范围"})
    return {
        "claim_version": 1,
        "capability": {
            "id": claim_id,
            "responsibility_key": "port-external-package",
            "version": version,
            "kind": "skill",
            "statement": statement,
            "evidence": ["e1"],
        },
        "what": {
            "obligations": [obligation],
            "inputs": [],
            "outputs": [],
            "applicability": {"include": include_items, "exclude": exclude_items},
            "known_limits": [],
            "failure_modes": [],
        },
        "how": {
            "entry": "SKILL.md",
            "interface": {"id": "agent-skill", "version": "1"},
            "side_effects": [],
            "permissions": [],
        },
        "why": {"evidence": evidence, "unknowns": unknowns},
        "quick_start": {
            "prompt": f"use {claim_id} skill",
            "expected": statement,
            "observable": False,
            "limitation": "测试夹具：未执行",
            "cost": "unknown",
        },
    }


def test_a_stated_hand_off_on_both_sides_is_a_split_not_a_competition():
    left = base_claim("port-skills", exclude=["只装进单个 Agent 时改用 port-plugins"])
    right = base_claim("port-plugins", exclude=["装成服务端插件包时改用 port-skills"])
    result = cmp.compare_claims(left, right)
    assert (result["relation"], result["action"]) == (cs.COMPLEMENTARY, cs.KEEP_BOTH)
    assert "点名对方" in result["reason"]
    assert result["evaluation_questions"] == []
    assert result["requires_owner_confirmation"] is False


def test_one_side_naming_the_other_is_not_enough_to_split():
    left = base_claim("port-skills", exclude=["只装进单个 Agent 时改用 port-plugins"])
    right = base_claim("port-plugins")
    result = cmp.compare_claims(left, right)
    assert result["relation"] == cs.SIMILAR
    assert "竞争实现" in result["reason"]


def test_declared_scopes_that_do_not_overlap_split_the_job():
    left = base_claim("port-skills", include=["装进单个 Agent 的技能目录"])
    right = base_claim("port-plugins", include=["装成整个服务端共享的插件包"])
    result = cmp.compare_claims(left, right)
    assert (result["relation"], result["action"]) == (cs.COMPLEMENTARY, cs.KEEP_BOTH)
    assert "互不相交" in result["reason"]


def test_declared_scopes_that_overlap_stay_competitors():
    left = base_claim("port-skills", include=["安装外部技能到本机"])
    right = base_claim("port-plugins", include=["安装外部技能到本机"])
    assert cmp.compare_claims(left, right)["relation"] == cs.SIMILAR


def test_an_empty_applicability_is_silence_not_a_boundary():
    left = base_claim("port-skills")
    right = base_claim("port-plugins")
    assert cmp.compare_claims(left, right)["relation"] == cs.SIMILAR


def test_same_capability_is_a_version_question_even_with_a_split_scope():
    left = base_claim("skill-porting", version="1.0.0", exclude=["改用别的能力"])
    right = base_claim("skill-porting", version="2.0.0", exclude=["改用别的东西"])
    assert cmp.compare_claims(left, right)["relation"] == cs.SAME
