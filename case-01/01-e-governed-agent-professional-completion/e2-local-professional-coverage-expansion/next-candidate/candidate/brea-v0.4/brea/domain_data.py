from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_professional_data() -> dict:
    path = Path(__file__).with_name("professional_data.json")
    return json.loads(path.read_text(encoding="utf-8"))


def routes() -> tuple[dict, ...]:
    return tuple(load_professional_data()["routes"])


def route_by_name(name: str) -> dict:
    for route in routes():
        if route["name"] == name:
            return route
    raise KeyError(f"unknown professional route: {name}")


def fact_descriptors() -> dict:
    return load_professional_data()["fact_descriptors"]
