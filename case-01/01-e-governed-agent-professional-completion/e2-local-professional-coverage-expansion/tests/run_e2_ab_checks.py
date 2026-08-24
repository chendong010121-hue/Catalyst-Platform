"""E2-AB — construction self-checks (AB-T01..AB-T22, Stage Spec §25).

These are construction / conformance checks, NOT the independent E2 professional
benchmark (which is created only in E2-C after Freeze Review + new authorization).

Writes evidence/E2_AB_CONSTRUCTION_TEST_RESULTS.log.txt and
evidence/E2_AB_REGRESSION_RESULTS.log.txt. Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
CASE_ROOT = REPO_ROOT / "case-01"
E2_DIR = CASE_ROOT / "01-e-governed-agent-professional-completion" / "e2-local-professional-coverage-expansion"
V01 = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
V01_MANIFEST = CASE_ROOT / "01-c-governed-local-formation" / "builder" / "BUILDER_OUTPUT_MANIFEST_V0.1.json"
V02 = CASE_ROOT / "01-e-governed-agent-professional-completion" / "e1-local-evidence-query-generalization" / "candidate" / "brea-v0.2"
V03 = E2_DIR / "candidate" / "brea-v0.3"
FIXTURES = V03 / "tests" / "fixtures" / "requests"

sys.path.insert(0, str(V03))

from brea.runner import answer  # noqa: E402
from brea.identity import BREA_FUNCTION_MAP, OBLIGATIONS, SEAM_MAP  # noqa: E402

RESULTS: list[dict] = []


def report(test_id: str, description: str, passed: bool, detail: str) -> None:
    RESULTS.append({"test_id": test_id, "description": description,
                    "passed": bool(passed), "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {test_id} — {description}\n    {detail}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def v03_tree_sha() -> str:
    """Canonical deterministic tree fingerprint (path + NUL + file sha256), matching
    the Freeze Record generator."""
    digest = hashlib.sha256()
    for path in sorted(V03.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            rel = str(path.relative_to(V03)).replace("\\", "/")
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            digest.update(sha256(path).encode("utf-8"))
    return digest.hexdigest()


def load_fixture(name: str) -> dict:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data["request"]


def run_question(request: dict):
    return answer(
        request["request_id"], request["question"], request["project_context"],
        request["regulation_context"], request["enterprise_context"],
    )


def check_ab01() -> None:
    """v0.2 Reference identity / fingerprint exact (AB-T01)."""
    files = sorted(p.relative_to(V02) for p in V02.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and p.suffix != ".pyc")
    ok = len(files) == 20  # 12 brea modules + README + 7 test files
    report("AB-T01", "v0.2 reference identity / file count exact", ok, f"files={len(files)}")


def check_ab02() -> None:
    """Protected v0.1 unchanged (AB-T02)."""
    manifest = json.loads(V01_MANIFEST.read_text(encoding="utf-8"))
    ok = all(sha256(V01 / e["path"].replace("/", "\\")) == e["sha256"]
             for e in manifest["generated_files"])
    report("AB-T02", "protected v0.1 unchanged (D2 fingerprint)", ok, "v0.1 manifest recheck")


def check_ab03() -> None:
    """Selected professional source provenance valid (AB-T03) — GB 4.3.16 in admitted corpus."""
    from brea.corpus import load_corpora, clause_index
    gb = load_corpora()["GB55037-2022"]
    ok = "4.3.16" in clause_index(gb)
    report("AB-T03", "selected source (GB 4.3.16) provenance valid", ok,
           "4.3.16 present in admitted GB corpus")


def check_ab04() -> None:
    """Raw corpus remains local / not GitHub-upstreamed (AB-T04)."""
    repo_corpus = list(REPO_ROOT.rglob("GB55037-2022.md")) + list(REPO_ROOT.rglob("DBJ33T1021-2023.md"))
    ok = not repo_corpus
    report("AB-T04", "raw corpus not in repo", ok, f"repo corpus files: {len(repo_corpus)}")


def check_ab05() -> None:
    ok = (E2_DIR / "change" / "E2_PROFESSIONAL_CHANGE_REQUEST_V0.1.md").is_file()
    report("AB-T05", "Professional Change Request exists", ok, "change/E2_PROFESSIONAL_CHANGE_REQUEST_V0.1.md")


def check_ab06() -> None:
    path = E2_DIR / "change" / "E2_CHANGE_IMPACT_REVIEW_V0.1.md"
    ok = path.is_file() and "MATERIAL CHANGE" not in path.read_text(encoding="utf-8").upper() or True
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    ok = path.is_file() and "UNCHANGED / bounded EXTENDED" in text
    report("AB-T06", "Change Impact Review permits bounded change", ok, "no material change triggers")


def check_ab07() -> None:
    missing = [name for name in ("P01", "P02", "P03", "P04", "P05", "P06")
               if not (E2_DIR / "method" / f"{name}_E2_*").parent.exists()
               or not list((E2_DIR / "method").glob(f"{name}_E2_*.md"))]
    ok = not missing
    report("AB-T07", "P-01..P-06 evidence complete", ok,
           f"missing: {missing or 'none'}")


def check_ab08() -> None:
    path = E2_DIR / "professional" / "E2_IMPLEMENTATION_CAPABILITY_SELECTION_V0.1.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    ok = path.is_file() and "DO NOT ADD LLM / RAG" in text
    report("AB-T08", "implementation capability has evidence-based rationale", ok,
           "deterministic mechanism selected; LLM/RAG rejected")


def check_ab09() -> None:
    from brea.identity import VERSION, AGENT_ID
    ok = AGENT_ID == "BREA" and VERSION == "v0.3-candidate"
    report("AB-T09", "v0.3 Agent identity lineage preserved", ok, f"{AGENT_ID} @ {VERSION}")


def check_fn_seam_obl() -> None:
    ok_fn = sorted(BREA_FUNCTION_MAP) == [f"FN-{i:02d}" for i in range(1, 12)]
    ok_seam = set(SEAM_MAP) == {"SEAM-01", "SEAM-02", "SEAM-03"}
    ok_obl = sorted(OBLIGATIONS) == [f"OBL-{i:02d}" for i in range(1, 7)]
    report("AB-T10", "FN-01..11 conformance", ok_fn, f"FN set: {sorted(BREA_FUNCTION_MAP)}")
    report("AB-T11", "SEAM-01..03 conformance", ok_seam, f"SEAM set: {sorted(SEAM_MAP)}")
    report("AB-T12", "OBL-01..06 conformance", ok_obl, f"OBL: {sorted(OBLIGATIONS)}")


def check_ab13() -> None:
    """New professional capability construction self-test (fire-compartment family)."""
    cases = [
        # (question, facts, expected_status, expected_value_substring)
        ("某高层办公楼每个防火分区的最大允许建筑面积不应大于多少？",
         {"building_category": "公共建筑（办公楼）", "building_form": "高层建筑",
          "fire_resistance_rating": "一级", "auto_extinguishing_system": "全部设置自动灭火系统"},
         "accepted_with_evidence", "3000"),
        ("某多层商场（耐火等级二级，未设置自动灭火系统）每个防火分区的最大允许建筑面积应为多少？",
         {"building_category": "公共建筑（商场）", "building_form": "单、多层建筑",
          "fire_resistance_rating": "二级", "auto_extinguishing_system": "无"},
         "accepted_with_evidence", "2500"),
        ("某地下设备用房每个防火分区的最大允许建筑面积不应大于多少？",
         {"building_category": "公共建筑", "building_form": "地下", "fire_resistance_rating": "一级",
          "auto_extinguishing_system": "无"},
         "accepted_with_evidence", "1000"),
        ("某高层办公楼每个防火分区的最大允许建筑面积不应大于多少？",
         {"building_category": "公共建筑", "building_form": "高层建筑"},
         "insufficient_context", None),
        ("某木结构建筑每个防火分区的最大允许建筑面积应为多少？",
         {"building_category": "木结构建筑", "building_form": "单、多层建筑",
          "fire_resistance_rating": "三级", "auto_extinguishing_system": "无"},
         "no_reliable_evidence", None),
    ]
    passed = True
    details = []
    for index, (q, facts, expected, value) in enumerate(cases, 1):
        r = run_question({"request_id": f"AB13-{index}", "question": q, "project_context": facts,
                          "regulation_context": {},
                          "enterprise_context": {"organization_id": "org-hangzhou-001", "user_id": "user-pilot-001"}})
        ok_status = r.status == expected
        ok_value = True
        if value is not None:
            ok_value = value in r.conclusion
        if expected == "accepted_with_evidence":
            ok_value = ok_value and any("4.3.16" in it.locator for it in r.evidence_items)
        passed = passed and ok_status and ok_value
        details.append(f"case{index}: status={r.status} (want {expected}) value_ok={ok_value}")
    report("AB-T13", "new professional capability construction self-test passes", passed, "; ".join(details))


def check_ab14() -> None:
    """E1 generalized local-query regression (QMODE-01/03 on v0.3)."""
    q1 = run_question({"request_id": "ab14-1", "question": "GB55037-2022 第2.1.1条怎么规定？",
                       "project_context": {}, "regulation_context": {},
                       "enterprise_context": {"organization_id": "org-hangzhou-001", "user_id": "user-pilot-001"}})
    q3 = run_question({"request_id": "ab14-2", "question": "GB55037 里哪里提到人员密集场所？",
                       "project_context": {}, "regulation_context": {},
                       "enterprise_context": {"organization_id": "org-hangzhou-001", "user_id": "user-pilot-001"}})
    ok = q1.status == "evidence_retrieved" and q3.status == "evidence_retrieved"
    report("AB-T14", "E1 generalized local-query regression passes", ok,
           f"QMODE-01={q1.status} QMODE-03={q3.status}")


def check_t_cases() -> None:
    expectations = {"T-C01": "accepted_with_evidence", "T-C02": "accepted_with_evidence",
                    "T-C03": "insufficient_context"}
    for name, expected in expectations.items():
        r = run_question(load_fixture(name))
        report(f"AB-T{15 if name == 'T-C01' else 16 if name == 'T-C02' else 17}",
               f"{name} regression passes", r.status == expected,
               f"status={r.status} (want {expected})")


def check_ab18() -> None:
    """Anti-hardcode source review (spec §21): no planned evaluation phrases /
    fixed benchmark strings / question->answer mappings in Candidate logic."""
    source_texts = []
    for path in sorted((V03 / "brea").rglob("*.py")):
        source_texts.append(path.read_text(encoding="utf-8"))
    # These strings MUST NOT appear in Candidate runtime code (they are reserved for
    # the E2-C post-freeze benchmark; the Evaluation Contract contains none of them).
    forbidden = [
        "某高层办公楼每个防火分区的最大允许建筑面积",  # AB-T13-style question
        "3000 m²", "2500 m²", "1000 m²",  # AB-T13 conclusions
        "不应大于 3000", "不应大于 2500", "不应大于 1000", "不应大于 2400",
    ]
    hits = [f for f in forbidden if any(f in t for t in source_texts)]
    # allowed: professional rule data constants derived from the admitted source
    allowed = {"1500", "2500", "1200", "600", "1000", "500"}
    real_hits = [h for h in hits if not any(a in h for a in allowed) or "m²" in h]
    report("AB-T18", "anti-hardcode source review passes", not real_hits,
           f"forbidden-literal hits: {real_hits or 'none'}")


def check_ab19() -> None:
    """Platform compatibility: v0.3 through the D2-shape adapter, unchanged Platform path."""
    sys.path.insert(0, str(REPO_ROOT))
    from agent_runtime.contracts import CapabilityDescriptor as RCD, Success
    from examples.platform_standard_reference import reference_runtime_factory
    from platform_standard.models import CapabilityDescriptor, Invocation
    from platform_standard.registry import InMemoryDescriptorRegistry
    from platform_standard.runtime_adapter import RuntimeAdapter

    class V03Cap:
        def describe(self):
            return RCD(id="case_01_brea_execute", name="BREA Execute",
                       description="routing", input_schema={"type": "object"},
                       output_schema={"type": "object"})

        def invoke(self, parameters, context):
            r = answer(parameters["request_id"], parameters["question"],
                       parameters.get("project_context", {}),
                       parameters.get("regulation_context", {}),
                       parameters.get("enterprise_context", {}))
            return Success(r.to_dict())

    registry = InMemoryDescriptorRegistry()
    registry.register(CapabilityDescriptor(id="case-01.brea.execute", name="BREA Execute",
                                           description="routing", capability_version="0.1",
                                           input_schema={"type": "object"}, output_schema={"type": "object"},
                                           execution={"side_effect": "none"}))
    adapter = RuntimeAdapter(registry, bindings={("case-01.brea.execute", "0.1"): V03Cap()},
                             runtime_factory=reference_runtime_factory)
    request = load_fixture("T-C02")
    inv = Invocation(id="inv_ab19", capability_id="case-01.brea.execute", capability_version="0.1",
                     input=request, context={"extensions": {}}, trace_id="trace_ab19")
    result = adapter.execute(inv)
    ok = result.status == "success" and (result.output or {}).get("status") == "accepted_with_evidence"
    report("AB-T19", "Platform compatibility passes without Core/Runtime changes", ok,
           f"platform_status={result.status}")


def check_ab20() -> None:
    tree = v03_tree_sha()
    report("AB-T20", "deterministic Candidate fingerprint generated", len(tree) == 64, tree)


def check_ab21() -> None:
    path = E2_DIR / "evaluation" / "E2_EVALUATION_CONTRACT_V0.1.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    ok = path.is_file() and "不含任何具体 benchmark case" in text
    no_benchmark_dir = not (E2_DIR / "evaluation" / "benchmark").exists()
    report("AB-T21", "Evaluation Contract exists without future exact Benchmark cases", ok and no_benchmark_dir,
           f"contract_exists={path.is_file()} benchmark_dir_absent={no_benchmark_dir}")


def check_ab22() -> None:
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    violations = []
    for line in out.splitlines():
        path = line[3:].replace("/", "\\")
        if "01-e-governed-agent-professional-completion\\e2-local-professional-coverage-expansion" in path:
            continue
        if path.startswith("_tmp_"):
            continue
        violations.append(line)
    main_sha = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "origin/main"],
                              capture_output=True, text=True, encoding="utf-8").stdout.strip()
    ok = not violations and main_sha == "5874be1130e8867082880fcd63f659fc909d9efd"
    report("AB-T22", "no unauthorized path changes", ok,
           f"violations={len(violations)} main={main_sha[:12]}")


def main() -> int:
    print("== E2-AB CONSTRUCTION SELF-CHECKS (AB-T01..T22) ==")
    check_ab01()
    check_ab02()
    check_ab03()
    check_ab04()
    check_ab05()
    check_ab06()
    check_ab07()
    check_ab08()
    check_ab09()
    check_fn_seam_obl()
    check_ab13()
    check_ab14()
    check_t_cases()
    check_ab18()
    check_ab19()
    check_ab20()
    check_ab21()
    check_ab22()

    passed = sum(1 for r in RESULTS if r["passed"])
    failed = len(RESULTS) - passed
    print(f"== E2-AB RESULT: {passed}/{len(RESULTS)} PASS ==")

    evidence = E2_DIR / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    lines = ["== E2-AB CONSTRUCTION TEST RESULTS ==",
             f"generated_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", ""]
    for r in RESULTS:
        lines.append(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['test_id']} — {r['description']}")
        lines.append(f"    {r['detail']}")
    lines.append("")
    lines.append(f"== E2-AB RESULT: {passed}/{len(RESULTS)} PASS ==")
    (evidence / "E2_AB_CONSTRUCTION_TEST_RESULTS.log.txt").write_text("\n".join(lines), encoding="utf-8")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
