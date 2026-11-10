"""A chart boundary survives the steps that come after the grouping.

The deck this set came from draws the organisation as it stands on one page and the one it
proposes on another, and the second chart reuses keys the first chart spells differently.
The fold groups by name and chart, so it must not take the other chart's row, evidence or
references when it merges a key: a reference the merging chart cannot claim keeps the key it
was written with, and the existing unresolved exit names it when that key is gone.
"""

from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


class _TwoChartsSharingOneKey:
    """The current page spells 市场营销中心 two ways; the proposed page reuses one key."""

    model = "stub-fold-boundary"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        quotes = " ".join(row["quote"] for row in evidence)
        page = "proposed" if "拟设" in quotes else "current"
        named = [row["evidence_id"] for row in evidence if "市场营销中心" in row["quote"]]
        mark, later_mark = named[0], named[-1]
        other = next(row["evidence_id"] for row in evidence if "市场营销中心" not in row["quote"])
        if page == "proposed":
            items = [
                {"kind": "entity", "key": "yingxiao_zhongxin", "meaning": "市场营销中心",
                 "business_type": "Department", "scope_state": "proposed",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [mark]},
                {"kind": "entity", "key": "cehua_bu", "meaning": "策划部",
                 "business_type": "Department", "scope_state": "proposed",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [other]},
                {"kind": "relation", "key": "cehua_bu|belongs|yingxiao_zhongxin",
                 "subject": "cehua_bu", "predicate": "隶属", "object": "yingxiao_zhongxin",
                 "meaning": "策划部 隶属 市场营销中心", "scope_state": "proposed",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [mark]},
            ]
        else:
            items = [
                {"kind": "entity", "key": "shichang_yingxiao", "meaning": "市场营销中心",
                 "business_type": "Department", "scope_state": "current",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [mark]},
                # The same name, a second spelling, inside the same chart: these two fold.
                {"kind": "entity", "key": "yingxiao_zhongxin", "meaning": "市场营销中心",
                 "business_type": "Department", "scope_state": "current",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [later_mark]},
                {"kind": "entity", "key": "zhaobiao_bu", "meaning": "招投标部",
                 "business_type": "Department", "scope_state": "current",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [other]},
                {"kind": "relation", "key": "zhaobiao_bu|belongs|yingxiao_zhongxin",
                 "subject": "zhaobiao_bu", "predicate": "隶属", "object": "yingxiao_zhongxin",
                 "meaning": "招投标部 隶属 市场营销中心", "scope_state": "current",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [later_mark]},
            ]
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                             finish_reason="stop")


def _sources(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "1-now.md").write_text("组织现状：市场营销中心\n招投标部\n", encoding="utf-8")
    (sources / "2-later.md").write_text("拟设：市场营销中心\n策划部\n", encoding="utf-8")
    return sources


def _understand(tmp_path, provider):
    sources = _sources(tmp_path)
    return UnderstandPort().understand(
        UnderstandingRequest("fold-boundary", "整理组织",
                             source_refs=tuple(sorted(sources.glob("*"))),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_fold",
                             requested_depth="semantic", budget_steps=8),
        source_root=sources, semantic_provider=provider)


def _entities(result):
    return sorted((item.key, item.scope_state) for item in result.semantic_candidate.items
                  if item.kind == "entity")


def _relations(result):
    return {item.subject: item.object for item in result.semantic_candidate.items
            if item.kind == "relation"}


def test_a_row_the_other_arrangement_reused_a_key_for_is_named_not_silently_counted(tmp_path):
    result = _understand(tmp_path, _TwoChartsSharingOneKey())
    attribution = result.producer_attribution

    # The store holds one row per key, so the proposed copy cannot be published beside the
    # current one - but what was left out is named with its state and the evidence it carried.
    record, = attribution["chart_key_reuse"]
    assert record["kind"] == "entity"
    assert record["item_key"] == "yingxiao_zhongxin"
    assert (record["kept_scope_state"], record["dropped_scope_state"]) == ("current", "proposed")
    assert record["meaning"] == "市场营销中心"
    # It did not reach the candidate, and the record says so rather than reading as content
    # that was read; the counts state what is listed and what is left out.
    assert record["in_candidate"] is False
    assert record["evidence_count"] == 1
    assert record["evidence_refs_listed"] == len(record["evidence_refs"]) == 1
    assert record["evidence_refs_omitted"] == 0
    assert attribution["chart_key_reuse_count"] == 1
    assert attribution["chart_key_reuse_listed"] == 1
    assert attribution["chart_key_reuse_omitted"] == 0
    assert _entities(result) == [("cehua_bu", "proposed"),
                                 ("shichang_yingxiao", "current"),
                                 ("zhaobiao_bu", "current")]


def test_the_fold_rewrites_only_the_references_of_its_own_chart(tmp_path):
    result = _understand(tmp_path, _TwoChartsSharingOneKey())

    relations = {item.key: item for item in result.semantic_candidate.items
                 if item.kind == "relation"}
    current = relations["zhaobiao_bu_belongs_yingxiao_zhongxin"]
    proposed = relations["cehua_bu_belongs_yingxiao_zhongxin"]
    # The chart whose name folded follows its survivor; the other chart's edge keeps the
    # key its page wrote instead of being handed to an organisation of the wrong chart.
    assert (current.subject, current.object) == ("zhaobiao_bu", "shichang_yingxiao")
    assert proposed.object == "yingxiao_zhongxin"
    # Its end no longer resolves, and that is said rather than papered over.
    assert proposed.evidence_class == "unresolved"
    assert "reference_not_declared" in (proposed.uncertainty or "")


def test_the_fold_record_names_the_chart_it_happened_in(tmp_path):
    result = _understand(tmp_path, _TwoChartsSharingOneKey())

    record, = result.producer_attribution["merged_duplicate_entities"]
    assert (record["name"], record["kept_key"], record["scope_state"]) == (
        "市场营销中心", "shichang_yingxiao", "current")
    assert record["merged_keys"] == ["yingxiao_zhongxin"]
    # Every passage both spellings carried stands behind the one row.
    kept = next(item for item in result.semantic_candidate.items
                if item.kind == "entity" and item.key == "shichang_yingxiao")
    assert record["evidence_count"] == len(kept.evidence_refs)


class _OneArrangementOneEvent:
    """A change row names a department the fold of its own arrangement merges away."""

    model = "stub-fold-event"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        mark = evidence[0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "shichang_yingxiao", "meaning": "市场营销中心",
             "business_type": "Department", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [mark]},
            {"kind": "entity", "key": "yingxiao_zhongxin", "meaning": "市场营销中心",
             "business_type": "Department", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [mark]},
            {"kind": "event", "key": "yingxiao_zhenghe", "predicate": "整合",
             "from": ["yingxiao_zhongxin"], "to": ["shichang_yingxiao"],
             "meaning": "整合市场营销中心", "scope_state": "current",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [mark]},
        ]}, ensure_ascii=False), finish_reason="stop")


def test_a_change_row_is_never_rewritten_across_its_ends(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "1-now.md").write_text("组织现状：市场营销中心\n", encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("fold-event", "整理组织", source_refs=(sources / "1-now.md",),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_fold_event",
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=_OneArrangementOneEvent())

    event = next(item for item in result.semantic_candidate.items if item.kind == "event")
    # A change row's own arrangement state does not prove its two ends are one name, so the
    # fold leaves both lists as written: the source is not moved onto the survivor, the end
    # that still resolves keeps resolving, and the removed end is named where it is missing.
    assert event.event_from == ("yingxiao_zhongxin",)
    assert event.event_to == ("shichang_yingxiao",)
    assert event.evidence_class == "unresolved"
    assert "reference_not_declared" in (event.uncertainty or "")
    assert "event_from=yingxiao_zhongxin" in (event.uncertainty or "")
    assert "event_to" not in (event.uncertainty or "")
