from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GROUPS = ["G-BASE", "G-SCOPE", "G-CONDITION", "G-NUMERIC"]
RESULT_KEYS = [
    "case_id",
    "track",
    "status",
    "contract_ok",
    "conclusion",
    "evidence_trace",
    "pc_results",
    "diagnostics",
]


def load_lab_data() -> dict[str, Any]:
    return json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))


def source_for(case: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    source = dict(case["source"])
    registered = registry[source["id"]]
    source["version"] = registered["version"]
    source["jurisdiction"] = registered["jurisdiction"]
    source["sha256"] = registered["sha256"]
    return source
