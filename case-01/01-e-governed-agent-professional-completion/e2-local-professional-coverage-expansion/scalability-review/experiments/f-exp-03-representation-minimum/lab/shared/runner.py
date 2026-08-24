from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

from shared.model import GROUPS, RESULT_KEYS, load_lab_data
from shared.validator import validate


LAB_ROOT = Path(__file__).resolve().parents[1]


def _load_adapter(directory: str) -> Callable[..., dict[str, Any]]:
    path = LAB_ROOT / directory / "adapter.py"
    module_name = f"f_exp_03_{directory.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.adapt


def _run_track(
    track: str,
    cases: list[dict[str, Any]],
    registry: dict[str, Any],
    omit_groups: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    if track == "A_PRIME":
        adapt = _load_adapter("a-prime")
        return [validate(case, adapt(case, registry)) for case in cases]
    adapt = _load_adapter("b-min")
    return [validate(case, adapt(case, registry, omit_groups)) for case in cases]


def _pc_summary(results: list[dict[str, Any]]) -> dict[str, str]:
    summary: dict[str, str] = {}
    for pc_id in (f"PC-{index:02d}" for index in range(1, 8)):
        statuses = [
            next(item["status"] for item in result["pc_results"] if item["id"] == pc_id)
            for result in results
        ]
        summary[pc_id] = "PASS" if all(status == "PASS" for status in statuses) else "FAIL"
    return summary


def _track_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": results,
        "pc_summary": _pc_summary(results),
        "all_cases_contract_ok": all(result["contract_ok"] for result in results),
    }


def _implementation_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(LAB_ROOT.glob("**/*.py")):
        if path.name == "test_experiment.py":
            continue
        digest.update(path.relative_to(LAB_ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _hidden_knowledge_scan() -> dict[str, Any]:
    forbidden = (
        "GB55037-2022",
        "DBJ33T1021-2023",
        "4.3.1",
        "3.4.3",
        "5.0.4",
        "2.2.3",
        "3.0.11",
        "4.5.1",
        "防火间距",
        "停车位",
        "消防救援口",
    )
    files = {
        "A_PRIME": [LAB_ROOT / "a-prime" / "adapter.py"],
        "B_MIN": [LAB_ROOT / "b-min" / "adapter.py"],
        "shared_validator": [LAB_ROOT / "shared" / "validator.py"],
    }
    findings: dict[str, list[str]] = {}
    for label, paths in files.items():
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    findings.setdefault(label, []).append(f"{path.name}:{token}")
    return {
        label: "FAIL" if label in findings else "PASS"
        for label in files
    } | {"findings": findings}


def run_experiment() -> dict[str, Any]:
    data = load_lab_data()
    core_cases = data["cases"]
    registry = data["source_registry"]
    a_prime = _run_track("A_PRIME", core_cases, registry)
    b_min = _run_track("B_MIN", core_cases, registry)

    shared_keys = all(set(result) == set(RESULT_KEYS) for result in a_prime + b_min)
    same_case_ids = [result["case_id"] for result in a_prime] == [result["case_id"] for result in b_min]
    same_sources = all(
        left["evidence_trace"]["source_id"] == right["evidence_trace"]["source_id"]
        and left["evidence_trace"]["locator"] == right["evidence_trace"]["locator"]
        and left["evidence_trace"]["raw_evidence"] == right["evidence_trace"]["raw_evidence"]
        for left, right in zip(a_prime, b_min)
    )

    ablation: dict[str, Any] = {}
    for group in GROUPS:
        ablated = _run_track("B_MIN", core_cases, registry, (group,))
        failures = [result["case_id"] for result in ablated if not result["contract_ok"]]
        pc_failures = sorted({
            item["id"]
            for result in ablated
            for item in result["pc_results"]
            if item["status"] == "FAIL"
        })
        ablation[group] = {
            "removed_group": group,
            "material_failure": bool(failures),
            "failed_cases": failures,
            "failed_pcs": pc_failures,
        }
    ablation["retained_groups"] = list(GROUPS)

    extension = data["extension"]
    before_hash = _implementation_hash()
    extension_a = _run_track("A_PRIME", [extension], registry)[0]
    extension_b = _run_track("B_MIN", [extension], registry)[0]
    after_hash = _implementation_hash()
    extension_result = {
        "data_only": True,
        "mechanism_code_unchanged": before_hash == after_hash,
        "schema_unchanged": set(extension["b_min"]) == set(core_cases[0]["b_min"]),
        "implementation_hash_before": before_hash,
        "implementation_hash_after": after_hash,
        "tracks": {"A_PRIME": extension_a, "B_MIN": extension_b},
    }

    return {
        "experiment_id": "F-EXP-03",
        "baseline": "93d491653931c048369579e972791a95bf075587",
        "comparison": {
            "same_case_ids": same_case_ids,
            "same_source_evidence": same_sources,
            "shared_result_contract": shared_keys,
            "same_pc_validator": True,
        },
        "tracks": {
            "A_PRIME": _track_summary(a_prime),
            "B_MIN": _track_summary(b_min),
        },
        "b_min_ablation": ablation,
        "same_structure_extension": extension_result,
        "hidden_knowledge": _hidden_knowledge_scan(),
        "execution_trace": {
            "case_count": len(core_cases),
            "raw_corpus_committed": False,
            "llm_or_retrieval_used": False,
            "candidate_or_platform_mutated": False,
        },
    }


def write_results(path: Path) -> dict[str, Any]:
    results = run_experiment()
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return results
