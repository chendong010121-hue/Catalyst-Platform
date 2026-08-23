"""E1 — benchmark + generalization tests runner (Stage Spec §14/§15/§16).

Runs:
  1. v0.2 candidate structural/conformance checks (FN/SEAM/OBL + anti-hardcode)
  2. E1 benchmark B-E1-01..13 (data from tests/benchmark/E1_BENCHMARK_V0.1.json)
  3. historical T-C01/02/03 regression through the v0.2 whole Agent

Writes evidence/E1_TEST_RESULTS.log.txt and evidence/E1_BENCHMARK_RESULTS_V0.1.json.
Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
E1_DIR = REPO_ROOT / "case-01" / "01-e-governed-agent-professional-completion" / "e1-local-evidence-query-generalization"
CANDIDATE = E1_DIR / "candidate" / "brea-v0.2"
FIXTURES = CANDIDATE / "tests" / "fixtures" / "requests"

sys.path.insert(0, str(CANDIDATE))

from brea.runner import answer  # noqa: E402
from brea.identity import BREA_FUNCTION_MAP, OBLIGATIONS, SEAM_MAP  # noqa: E402
from brea.query import classify_query  # noqa: E402

RESULTS: list[dict] = []


def report(test_id: str, description: str, passed: bool, detail: str) -> None:
    RESULTS.append({"test_id": test_id, "description": description,
                    "passed": bool(passed), "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {test_id} — {description}\n    {detail}")


def load_fixture(name: str) -> dict:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data["request"]


def run_question(request: dict):
    return answer(
        request["request_id"], request["question"], request["project_context"],
        request["regulation_context"], request["enterprise_context"],
    )


# ---------------------------------------------------------------------------
# 1. structural / conformance / anti-hardcode
# ---------------------------------------------------------------------------

def check_structural() -> None:
    expected_fns = [f"FN-{index:02d}" for index in range(1, 12)]
    report("E1-S-01", "FN-01..11 decomposition preserved",
           sorted(BREA_FUNCTION_MAP) == sorted(expected_fns),
           f"FN set: {sorted(BREA_FUNCTION_MAP)}")
    report("E1-S-02", "SEAM-01..03 preserved",
           set(SEAM_MAP) == {"SEAM-01", "SEAM-02", "SEAM-03"},
           f"SEAM set: {sorted(SEAM_MAP)}")
    report("E1-S-03", "OBL-01..06 preserved",
           sorted(OBLIGATIONS) == [f"OBL-{index:02d}" for index in range(1, 7)],
           f"OBL: {sorted(OBLIGATIONS)}")
    report("E1-S-04", "no provider / no prompt authority",
           not (CANDIDATE / "brea" / "provider.py").exists()
           and not any(p.name.endswith((".prompt", ".prompts")) or p.name == "AGENTS.md"
                       for p in CANDIDATE.rglob("*") if p.is_file()),
           "provider.py absent; no prompt files")


def check_anti_hardcode() -> None:
    """Inspect Candidate source for benchmark-specific literals (spec §4/§15)."""
    source_texts = []
    for path in sorted((CANDIDATE / "brea").rglob("*.py")):
        source_texts.append(path.read_text(encoding="utf-8"))

    # Benchmark-specific literals that MUST NOT appear in runtime code:
    # - benchmark question fragments
    # - benchmark clause ids (2.1.1 / 4.1.2 / 99.9.9 — not professional rules)
    # - benchmark table ids (5.0.2 — not a professional rule table)
    # - benchmark conclusions
    forbidden = [
        "人员密集场所？", "怎么规定？", "2.1.1", "4.1.2", "99.9.9", "表5.0.2",
        "机动车出入口的规定", "防雷", "商业（建筑面积", "配建指标应为多少",
    ]
    hits = []
    for literal in forbidden:
        for index, text in enumerate(source_texts):
            if literal in text:
                hits.append((literal, index))
    # Allowlist: professional rules may reference 3.1.3 / 表5.0.1 / 表5.0.4 / 配建指标
    allowed_professional = {"3.1.3", "表5.0.1", "表5.0.4", "配建指标"}
    real_hits = [h for h in hits if h[0] not in allowed_professional]
    report("E1-A-01", "no benchmark question literals in runtime code",
           all(not (lit in text) for text in source_texts for lit in forbidden
               if lit not in allowed_professional),
           f"forbidden-literal hits: {real_hits or 'none'}")
    report("E1-A-02", "no per-benchmark clause-id branches",
           not any(re.search(r'if\s+.*(?:2\.1\.1|4\.1\.2|99\.9\.9)', text) for text in source_texts),
           "no branch condition references benchmark clause ids")
    report("E1-A-03", "reusable locator/retrieval path exists",
           any("classify_query" in text for text in source_texts)
           and any("topic_search" in text for text in source_texts),
           "classify_query + topic_search present in brea/query.py")


# ---------------------------------------------------------------------------
# 2. benchmark
# ---------------------------------------------------------------------------

def run_benchmark() -> dict:
    bench = json.loads((E1_DIR / "tests" / "benchmark" / "E1_BENCHMARK_V0.1.json").read_text(encoding="utf-8"))
    entries = []
    for entry in bench["entries"]:
        entry_id = entry["id"]
        question = entry["question"]
        if question.startswith("fixture:"):
            request = load_fixture(question.split(":", 1)[1])
            result = run_question(request)
        else:
            result = run_question({
                "request_id": entry_id,
                "question": question,
                "project_context": {},
                "regulation_context": {},
                "enterprise_context": {"organization_id": "org-hangzhou-001", "user_id": "user-pilot-001"},
            })
        md = result.implementation_metadata.to_dict()
        status_ok = result.status == entry["expected_status"]
        source_ok = True
        if entry.get("expected_source") and result.status not in (
            "no_reliable_evidence", "insufficient_context",
        ):
            def _src_norm(value: str) -> str:
                return value.replace(" ", "").replace("/", "")
            source_ok = any(
                _src_norm(item.source_identity) == _src_norm(entry["expected_source"])
                for item in result.evidence_items
            )
        if entry.get("expected_locator_constraint"):
            constraint = entry["expected_locator_constraint"]
            if "contains " in constraint:
                needle = constraint.split("contains ", 1)[1]
                locator_ok = any(needle in item.locator for item in result.evidence_items)
            elif "evidence_type " in constraint:
                etype = constraint.split("evidence_type ", 1)[1]
                locator_ok = any(item.evidence_type == etype for item in result.evidence_items)
            elif constraint == "none":
                locator_ok = len(result.evidence_items) == 0
            elif constraint.startswith(">="):
                match = re.match(r">=\s*(\d+)\s+evidence", constraint)
                locator_ok = match is not None and len(result.evidence_items) >= int(match.group(1))
        # numeric safety: normative numeric claims must be absent from conclusions
        # that are fail-closed / retrieval-only. Clause locators in the conclusion
        # (e.g. "99.9.9") are identifiers, not normative values — allowed.
        normative_pattern = re.compile(
            r"(?:不应|不宜|应|须|不得)\s*(?:小于|大于|为|采用|低于|高于)\s*\d+"
            r"|\d+(?:\.\d+)?\s*(?:m|车位|㎡|米)"
        )
        numeric_ok = True
        if result.status in ("no_reliable_evidence", "insufficient_context"):
            numeric_ok = not normative_pattern.search(result.conclusion)
        elif result.status == "evidence_retrieved":
            numeric_ok = not normative_pattern.search(result.conclusion)
        passed = status_ok and source_ok and locator_ok and numeric_ok
        report(
            entry_id,
            f"{entry['expected_behavior']}",
            passed,
            f"status={result.status} (want {entry['expected_status']}) "
            f"source_ok={source_ok} locator_ok={locator_ok} numeric_ok={numeric_ok}",
        )
        entries.append({
            "id": entry_id,
            "question": question,
            "expected_status": entry["expected_status"],
            "actual_status": result.status,
            "status_ok": status_ok,
            "source_ok": source_ok,
            "locator_ok": locator_ok,
            "numeric_ok": numeric_ok,
            "passed": passed,
            "conclusion": result.conclusion,
            "evidence_items": [item.to_dict() for item in result.evidence_items],
            "query_mode": md.get("query_mode"),
        })
    return {"benchmark": bench["benchmark"], "version": bench["version"], "entries": entries}


# ---------------------------------------------------------------------------
# 3. historical regression
# ---------------------------------------------------------------------------

def run_regression() -> None:
    expectations = {
        "T-C01": ("accepted_with_evidence", 1),
        "T-C02": ("accepted_with_evidence", 2),
        "T-C03": ("insufficient_context", 0),
    }
    for name, (status, min_items) in expectations.items():
        result = run_question(load_fixture(name))
        report(
            f"E1-R-{name}",
            f"historical {name} preserved in v0.2",
            result.status == status and len(result.evidence_items) >= min_items,
            f"status={result.status} evidence_items={len(result.evidence_items)}",
        )


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def main() -> int:
    print("== E1 TESTS (structural / anti-hardcode / benchmark / regression) ==")
    check_structural()
    check_anti_hardcode()
    benchmark = run_benchmark()
    run_regression()

    passed = sum(1 for r in RESULTS if r["passed"])
    failed = len(RESULTS) - passed
    print(f"== E1 RESULT: {passed}/{len(RESULTS)} PASS ==")

    evidence = E1_DIR / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    lines = [
        "== E1 TEST RESULTS — CASE 01-E / E1 ==",
        f"generated_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
    ]
    for r in RESULTS:
        lines.append(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['test_id']} — {r['description']}")
        lines.append(f"    {r['detail']}")
    lines.append("")
    lines.append(f"== E1 RESULT: {passed}/{len(RESULTS)} PASS ==")
    log = evidence / "E1_TEST_RESULTS.log.txt"
    log.write_text("\n".join(lines), encoding="utf-8")

    bench_out = evidence / "E1_BENCHMARK_RESULTS_V0.1.json"
    bench_out.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"log written: {log}")
    print(f"benchmark results written: {bench_out}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
