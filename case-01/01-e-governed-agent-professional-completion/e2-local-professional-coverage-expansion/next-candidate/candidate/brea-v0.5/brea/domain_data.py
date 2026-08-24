from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .corpus import Corpus, extract_level_scope, norm


@lru_cache(maxsize=1)
def load_professional_data() -> dict:
    path = Path(__file__).with_name("professional_data.json")
    return json.loads(path.read_text(encoding="utf-8"))


def routes() -> tuple[dict, ...]:
    return tuple(load_professional_data()["routes"])


def standard_aliases() -> dict[str, tuple[str, ...]]:
    return {
        standard_id: tuple(record.get("aliases", ()))
        for standard_id, record in load_professional_data().get("standards", {}).items()
    }


def standard_meta(standard_id: str) -> tuple[str, str, str]:
    record = load_professional_data().get("standards", {}).get(standard_id)
    if record is None:
        raise KeyError(f"unknown admitted standard: {standard_id}")
    return record["source_identity"], record["title"], record["version"]


def _intent_matches(question: str, route: dict) -> bool:
    terms = route.get("intent_terms", [])
    if route.get("intent_match", "any") == "all":
        return bool(terms) and all(term in question for term in terms)
    return any(term in question for term in terms)


def _jurisdiction_matches(facts: dict, route: dict) -> bool:
    rule = route.get("jurisdiction_rule")
    if not rule:
        return True
    actual = facts.get(rule.get("fact"), "")
    return any(term in str(actual) for term in rule.get("terms", []))


def _resolve_level(dbj: Corpus | None, facts: dict, route: dict) -> str | None:
    resolution = route.get("level_resolution") or {}
    caption = resolution.get("caption")
    fact = resolution.get("fact")
    city_class = facts.get(fact) if fact else None
    if dbj is None or not caption or not city_class:
        return None
    for label, scope in extract_level_scope(dbj, caption):
        if norm(scope) == norm(city_class):
            return label
    return None


def match_route(question: str, facts: dict, dbj: Corpus | dict | None = None) -> dict | None:
    """Resolve one declarative professional route without family dispatch."""
    candidates = [route for route in routes() if _intent_matches(question, route)]
    if not candidates:
        return None
    route = candidates[0]
    level_corpus = dbj.get(route["standard_id"]) if isinstance(dbj, dict) else dbj
    return {
        "route": route,
        "standard_id": route["standard_id"] if _jurisdiction_matches(facts, route) else None,
        "level": _resolve_level(level_corpus, facts, route),
    }


def fact_descriptors() -> dict:
    return load_professional_data()["fact_descriptors"]
