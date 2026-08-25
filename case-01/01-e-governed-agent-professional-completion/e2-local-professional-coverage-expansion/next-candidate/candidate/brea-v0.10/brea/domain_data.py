from __future__ import annotations

from .corpus import Corpus, extract_level_scope, norm


def routes(knowledge: dict) -> tuple[dict, ...]:
    return tuple(knowledge["routes"])


def standard_aliases(knowledge: dict) -> dict[str, tuple[str, ...]]:
    return {
        standard_id: tuple(record.get("aliases", ()))
        for standard_id, record in knowledge.get("standards", {}).items()
    }


def standard_meta(knowledge: dict, standard_id: str) -> tuple[str, str, str]:
    record = knowledge.get("standards", {}).get(standard_id)
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


def _standard_hint_matches(standard_hint: str, route: dict, knowledge: dict) -> bool:
    if not standard_hint:
        return False
    standard_id = route.get("standard_id")
    return standard_hint == standard_id or standard_hint in standard_aliases(knowledge).get(standard_id, ())


def _fact_scope_score(facts: dict, route: dict) -> int:
    score = 0
    for fact, terms in route.get("scope_terms", {}).items():
        actual = facts.get(fact)
        if actual not in (None, "") and any(term in str(actual) for term in terms):
            score += 1
    return score


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


def match_route(
    question: str,
    facts: dict,
    dbj: Corpus | dict | None,
    knowledge: dict,
    regulation_context: dict | None = None,
) -> dict | None:
    """Resolve one declarative professional route without family dispatch."""
    standard_hint = (regulation_context or {}).get("standard_hint", "")
    scored: list[tuple[tuple[int, int, int], dict]] = []
    for route in routes(knowledge):
        terms = route.get("intent_terms", [])
        matched = sum(term in question for term in terms)
        if route.get("intent_match", "any") == "all" and matched != len(terms):
            continue
        if matched == 0:
            continue
        score = (
            int(_standard_hint_matches(standard_hint, route, knowledge)),
            matched,
            _fact_scope_score(facts, route),
        )
        scored.append((score, route))
    if not scored:
        return None
    best_score = max(score for score, _route in scored)
    candidates = [route for score, route in scored if score == best_score]
    if len(candidates) != 1:
        return {"ambiguous": True, "candidates": candidates}
    route = candidates[0]
    level_corpus = dbj.get(route["standard_id"]) if isinstance(dbj, dict) else dbj
    return {
        "route": route,
        "standard_id": route["standard_id"] if _jurisdiction_matches(facts, route) else None,
        "level": _resolve_level(level_corpus, facts, route),
    }


def fact_descriptors(knowledge: dict) -> dict:
    return knowledge["fact_descriptors"]
