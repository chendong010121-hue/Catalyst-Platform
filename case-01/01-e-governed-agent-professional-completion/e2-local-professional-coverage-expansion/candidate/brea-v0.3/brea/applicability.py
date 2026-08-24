"""SEAM-02 — Regulation Applicability (DOMAIN-OWNED MEANING; FN-03).

Standard identity / edition / jurisdiction / level resolution. The applicability
chain is observable (OBL-02) and traced from the admitted corpus (Table 5.0.1).
"""
from __future__ import annotations

from .corpus import Corpus, extract_level_scope, norm

STANDARDS: dict[str, dict[str, str]] = {
    "GB55037-2022": {
        "title": "《建筑防火通用规范》（全文强制性工程建设规范）",
        "jurisdiction": "全国",
        "version_note": "2022（OCR 副本未含公告页；施行日期以住房和城乡建设部公告为准）",
    },
    "DBJ33T1021-2023": {
        "title": "《城市建筑工程停车场（库）设置规则和配建指标标准》",
        "jurisdiction": "浙江省",
        "version_note": "2023-09-28 发布，2024-03-01 施行（废止 DB33/1021-2013）",
    },
}

# Table 5.0.4 column order: I, II, III, 内部, 外部.
LEVEL_COLUMN: dict[str, int] = {"I": 0, "II": 1, "Ⅲ": 2, "ⅢI": 2, "III": 2}


def resolve_level(dbj: Corpus, city_class: str) -> str | None:
    for label, scope in extract_level_scope(dbj, "表5.0.1"):
        if norm(scope) == norm(city_class):
            return label
    return None


def applicability_for_question(question: str, facts: dict, dbj: Corpus | None) -> dict:
    """Observable applicability chain. Domain meaning; never numeric authority."""
    chain: dict = {"standard_id": None, "reason": [], "level": None}
    if "防火间距" in question:
        if facts.get("vehicle_goods_category") and facts.get("adjacent_building_nature"):
            chain["standard_id"] = "GB55037-2022"
            chain["reason"].append("防火间距控制事项 → 全国强制性规范 GB 55037-2022")
        else:
            chain["reason"].append("防火间距控制事项但必要项目事实缺失")
        return chain
    if ("停车位" in question) or ("配建" in question):
        jurisdiction = facts.get("jurisdiction") or ""
        if "浙江" in jurisdiction:
            chain["standard_id"] = "DBJ33T1021-2023"
            chain["reason"].append("配建指标控制事项 + 浙江省法域 → DBJ33/T1021-2023")
            city_class = facts.get("city_class")
            if dbj is not None and city_class:
                level = resolve_level(dbj, city_class)
                if level is not None:
                    chain["level"] = level
                    chain["reason"].append(f"表5.0.1：{city_class} → 指标级别 {level}")
                else:
                    chain["reason"].append("表5.0.1：城市类别事实无法匹配指标级别")
        else:
            chain["reason"].append("配建指标控制事项但法域非浙江省 → 本地已接纳规范库无适用依据")
        return chain
    chain["reason"].append("未能识别控制事项")
    return chain
