"""Two keys a reader would call one thing wait for a decision; nothing is merged on a hunch.

The deck drew its current org chart and its proposed one, so 市场营销中心 and 营销中心,
工程管理中心 and 工程中心 stood as separate identities. No framework that reads
enterprise material merges on similarity: exact names fold, a vector match stays a
`similar` edge, and identity is an explicit decision. The port names the pairs and keeps
them apart.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_semantic import _identity_candidates
from catalyst_platform.understand_verify import verification_integrity, verification_local_checks
from catalyst_platform.understand_wiki import admission_plan


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_identity_candidates",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_identity_candidates",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    model = "stub-identity-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        return ModelResponse(content=json.dumps({"items": self._build(payload["evidence"])},
                                                ensure_ascii=False),
                             finish_reason="stop")


def _ids(evidence):
    return {row["quote"]: row["evidence_id"] for row in evidence}


def _entity(key, meaning, evidence_id):
    return {"kind": "entity", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id]}


def _run(tmp_path, build, names):
    source = tmp_path / "org.md"
    source.write_text("\n".join(names), encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build))


CHART = ["市场营销中心", "营销中心", "纪检室"]


def _two_charts(evidence):
    ids = _ids(evidence)
    return [_entity("shichang_yinxiaozhongxin", "市场营销中心", ids["市场营销中心"]),
            _entity("yingxiao_zhongxin", "营销中心", ids["营销中心"]),
            _entity("jijianshi", "纪检室", ids["纪检室"])]


def test_two_spellings_of_one_chart_are_named_and_kept_apart(tmp_path):
    result = _run(tmp_path, _two_charts, CHART)
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # Nothing merged: the deck may be drawing a current chart and a proposed one.
    assert keys == {"shichang_yinxiaozhongxin", "yingxiao_zhongxin", "jijianshi"}
    attribution = result.producer_attribution
    assert attribution["merged_duplicate_entities"] == []
    [pair] = attribution["identity_candidates"]
    assert pair["keys"] == ["shichang_yinxiaozhongxin", "yingxiao_zhongxin"]
    assert pair["names"] == ["市场营销中心", "营销中心"]
    assert pair["basis"] == "contains"
    assert attribution["identity_candidate_count"] == 1


def test_names_that_are_not_one_thing_are_not_a_pair(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("shichang_yinxiaozhongxin", "市场营销中心", ids["市场营销中心"]),
                _entity("jijianshi", "纪检室", ids["纪检室"])]

    result = _run(tmp_path, build, CHART)
    assert result.producer_attribution["identity_candidates"] == []


def test_the_same_name_is_still_one_entity_and_not_a_pair(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity("yingxiao_a", "营销中心", ids["营销中心"]),
                _entity("yingxiao_b", "「营销中心」", ids["营销中心"])]

    result = _run(tmp_path, build, CHART)
    keys = [item.key for item in result.semantic_candidate.items if item.kind == "entity"]
    # The exact-name merge settles it, so there is nothing left for a decision.
    assert len(keys) == 1
    assert result.producer_attribution["identity_candidates"] == []


def test_a_kind_word_alone_does_not_make_two_names_one_thing():
    class Item:
        def __init__(self, key, meaning):
            self.kind, self.key, self.meaning = "entity", key, meaning

    rows = _identity_candidates([
        Item("gcgl", "工程管理中心"), Item("gc", "工程中心"),
        Item("ht", "后台部门"), Item("htzn", "后台职能部门"),
        Item("jt", "天津市水利工程集团有限公司")])
    pairs = {frozenset(row["names"]) for row in rows}
    # The kind word is dropped before the two names are compared, so the two centres and
    # the two 后台 headings pair up where the raw names never would.
    assert frozenset(("工程管理中心", "工程中心")) in pairs
    assert frozenset(("后台部门", "后台职能部门")) in pairs
    # A long name that shares one word with a short one is two names.
    assert not any("天津市水利工程集团有限公司" in names for names in pairs)


def test_a_short_name_of_the_whole_company_is_a_pair():
    class Item:
        def __init__(self, key, meaning):
            self.kind, self.key, self.meaning = "entity", key, meaning

    rows = _identity_candidates([
        Item("shuilijituan", "水利集团"),
        Item("tianjin_shuili_gongcheng_jituan_youxian_gongsi", "天津市水利工程集团有限公司")])
    # 水利集团 is not a run inside the full name, only its characters in order, so literal
    # containment missed the pair and one company stood as two keys.
    [pair] = rows
    assert pair["names"] == ["水利集团", "天津市水利工程集团有限公司"]
    assert pair["basis"] == "abbreviation"
    assert pair["score"] == round(4 / 13, 3)


def test_a_short_name_that_drops_a_rank_names_another_post():
    class Item:
        def __init__(self, key, meaning):
            self.kind, self.key, self.meaning = "entity", key, meaning

    rows = _identity_candidates([
        Item("fen_gongsi_jingli", "分公司经理"),
        Item("fen_gongsi_changwu_fujingli", "分公司常务副经理")])
    # 常务副 is not a word the full name sheds; it is the post the longer name is.
    assert rows == []


def test_a_duty_read_as_a_name_is_not_a_shortening():
    class Item:
        def __init__(self, key, meaning):
            self.kind, self.key, self.meaning = "entity", key, meaning

    rows = _identity_candidates([
        Item("jishu_yanfa_zhongxin", "技术研发中心"),
        Item("fuze_jishu_zhiliang_yanfa", "负责分公司技术、质量、研发工作")])
    assert rows == []


def test_the_company_short_and_full_reach_the_plan_as_one_decision(tmp_path):
    lines = ["天津市水利工程集团有限公司", "水利集团", "一分公司"]

    def build(evidence):
        ids = _ids(evidence)
        return [_entity("tianjin_shuili_gongcheng_jituan_youxian_gongsi",
                        "天津市水利工程集团有限公司",
                        ids["天津市水利工程集团有限公司"]),
                _entity("shuili_jituan", "水利集团", ids["水利集团"]),
                _entity("yifengongsi", "一分公司", ids["一分公司"]),
                {"kind": "relation", "key": "yi_li_quancheng", "meaning": "「一分公司」列于「天津市水利工程集团有限公司」之下",
                 "subject": "yifengongsi", "object": "tianjin_shuili_gongcheng_jituan_youxian_gongsi",
                 "predicate": "隶属", "relation_source": "LAYOUT", "layout_ref": "org.md 版面",
                 "evidence_class": "INFERRED",
                 "evidence_refs": [ids["一分公司"], ids["天津市水利工程集团有限公司"]]},
                {"kind": "relation", "key": "yi_li_jiancheng", "meaning": "「一分公司」隶属「水利集团」",
                 "subject": "yifengongsi", "object": "shuili_jituan", "predicate": "隶属",
                 "relation_source": "LAYOUT", "layout_ref": "org.md 版面",
                 "evidence_class": "INFERRED",
                 "evidence_refs": [ids["一分公司"], ids["水利集团"]]}]

    source = tmp_path / "org.md"
    source.write_text("\n".join(lines), encoding="utf-8")
    result = UnderstandPort().understand(_request(source), source_root=tmp_path,
                                         semantic_provider=_Rows(build))
    attribution = result.producer_attribution
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # The pair is a decision, so both keys and both relations stand until the Owner answers.
    assert keys == {"tianjin_shuili_gongcheng_jituan_youxian_gongsi", "shuili_jituan", "yifengongsi"}
    [pair] = attribution["identity_candidates"]
    assert pair["names"] == ["水利集团", "天津市水利工程集团有限公司"]
    assert pair["basis"] == "abbreviation"
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    [check] = [row for row in checks if row["rule"] == "identity_decision_required"]
    assert check["pairs"][0]["names"] == ["水利集团", "天津市水利工程集团有限公司"]
    plan = admission_plan(result)
    assert plan["identity_candidates"][0]["basis"] == "abbreviation"


def test_a_two_character_word_does_not_take_the_room_the_company_needs():
    class Item:
        def __init__(self, key, meaning):
            self.kind, self.key, self.meaning = "entity", key, meaning

    rows = _identity_candidates([
        Item("gongcheng", "工程"), Item("gongcheng_yewu", "工程业务"),
        Item("shuilijituan", "水利集团"),
        Item("tianjin_shuili_gongcheng_jituan_youxian_gongsi", "天津市水利工程集团有限公司")],
        limit=1)
    # 工程 covers half of 工程业务 and scores higher, but a word is not a name.
    [pair] = rows
    assert pair["names"] == ["水利集团", "天津市水利工程集团有限公司"]


def test_the_review_and_the_plan_both_show_the_pair(tmp_path):
    result = _run(tmp_path, _two_charts, CHART)
    attribution = result.producer_attribution
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    [check] = [row for row in checks if row["rule"] == "identity_decision_required"]
    assert check["pairs"][0]["keys"] == ["shichang_yinxiaozhongxin", "yingxiao_zhongxin"]
    assert "nothing was merged" in check["detail"]
    plan = admission_plan(result)
    assert plan["identity_candidates"][0]["names"] == ["市场营销中心", "营销中心"]
