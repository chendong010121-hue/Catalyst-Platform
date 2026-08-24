"""SEAM-01 — Professional Project Facts (DOMAIN-OWNED MEANING; FN-02).

Domain asset: professional fact vocabulary + deterministic normalization.
Prompt / retrieval / provider must never redefine these semantics (ST-03/ST-04).

v0.5 retains the bounded professional facts required by the existing conditional
rule coverage:
  building_form · fire_resistance_rating · auto_extinguishing_system
Existing v0.1/v0.2 facts are unchanged.
"""
from __future__ import annotations

import re

FACT_VOCABULARY: dict[str, str] = {
    "jurisdiction": "project jurisdiction (province/city)",
    "building_category": "building use category",
    "floor_area_m2": "floor area in square metres",
    "city_class": "city planning-population class (Table 5.0.1 scope)",
    "vehicle_goods_category": "vehicle/goods fire category",
    "adjacent_building_nature": "nature of the adjacent building/place",
    "building_form": "building form: 高层建筑 / 单、多层建筑 / 地下",
    "fire_resistance_rating": "fire resistance rating: 一/二/三/四级",
    "auto_extinguishing_system": "automatic extinguishing system: 全部设置/局部设置/无",
}

REQUIRED_FACTS: frozenset[str] = frozenset(FACT_VOCABULARY)

# Human-readable Domain labels for professional facts (no digits; used in fail-closed output).
FACT_LABELS: dict[str, str] = {
    "jurisdiction": "项目所在地（省份/城市）",
    "building_category": "建筑业态分类",
    "floor_area_m2": "建筑面积",
    "city_class": "城市类别（规划人口分级）",
    "vehicle_goods_category": "车辆/物品火灾类别",
    "adjacent_building_nature": "相邻对象性质",
    # E2 — fire-compartment family labels
    "building_form": "建筑形式（高层/单多层/地下）",
    "fire_resistance_rating": "耐火等级（一/二/三/四级）",
    "auto_extinguishing_system": "自动灭火系统设置（全部/局部/无）",
}


def normalize_key(key: str) -> str:
    normalized = re.sub(r"[^\w]+", "_", key.strip().casefold(), flags=re.UNICODE).strip("_")
    if not normalized:
        raise ValueError("fact key cannot be empty after normalization")
    return normalized


def normalize_value(key: str, value: object) -> object:
    if key == "floor_area_m2":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("floor_area_m2 must be numeric")
        return float(value)
    if value is None:
        return None
    return str(value).strip()


def normalize_facts(raw: dict) -> dict:
    out: dict = {}
    for key, value in raw.items():
        normalized_key = normalize_key(str(key))
        out[normalized_key] = normalize_value(normalized_key, value)
    return out


def missing_facts(facts: dict, required: set[str] | None = None) -> list[str]:
    required_set = sorted(required or set(REQUIRED_FACTS))
    return [
        key for key in required_set
        if key not in facts or facts[key] in (None, "")
    ]
