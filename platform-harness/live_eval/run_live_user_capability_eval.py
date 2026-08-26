"""Live user-capability evaluation for Catalyst Minimum Usable V0.2.

This runner intentionally uses real network dependencies:
- a real OpenAI-compatible model endpoint;
- the real GitHub REST API as an approved read-only external source.

It never falls back to scripted/fake model output.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from agent_runtime.contracts import (
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Continue,
    Goal,
    Stop,
    Success,
)
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.providers import OpenAICompatibleModelProvider
from agent_runtime.runtime import Runtime
from examples.fakes import InMemoryStateStore

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = Path(__file__).resolve().parent / "benchmark_v0_2"
PUBLIC = BENCHMARK_DIR / "public_cases.json"
PRIVATE = BENCHMARK_DIR / "private_rubric.json"
OUT = Path(os.getenv("CATALYST_LIVE_OUTPUT_DIR", ROOT / "live_evidence_v0_2"))
REPO = "chendong010121-hue/agent-runtime"


class LivePolicy:
    def __init__(self, max_steps: int = 8) -> None:
        self.max_steps = max_steps

    def check_action(self, action, state):
        return Allow()

    def should_stop(self, state, history):
        if len(history) >= self.max_steps:
            return Stop("live capability evaluation max-step guard")
        return Continue()


class GitHubRepositoryReadCapability:
    """Narrow read-only GitHub API tool for this case-local live proof."""

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN is required for the live external API proof")
        self._token = token

    def describe(self):
        return CapabilityDescriptor(
            id="github_repo_read",
            name="GitHub Repository Read",
            description=(
                "Read authoritative current Catalyst repository evidence. "
                "Use resource='readme' for the current README and resource='main_branch' "
                "for the exact current main commit. This tool is read-only."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "enum": ["readme", "main_branch"],
                    }
                },
                "required": ["resource"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        resource = parameters.get("resource")
        if resource == "readme":
            url = f"https://api.github.com/repos/{REPO}/contents/README.md?ref=main"
            data = self._get_json(url)
            content = base64.b64decode(data["content"]).decode("utf-8")
            return Success(
                {
                    "resource": "readme",
                    "repository": REPO,
                    "ref": "main",
                    "blob_sha": data.get("sha"),
                    "content": content,
                    "source_url": data.get("html_url"),
                }
            )
        if resource == "main_branch":
            url = f"https://api.github.com/repos/{REPO}/branches/main"
            data = self._get_json(url)
            sha = data["commit"]["sha"]
            return Success(
                {
                    "resource": "main_branch",
                    "repository": REPO,
                    "branch": "main",
                    "commit_sha": sha,
                    "source_url": data.get("_links", {}).get("html"),
                }
            )
        return Success({"error": "unsupported resource", "resource": resource})

    def _get_json(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "catalyst-live-eval-v0.2",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API HTTP {exc.code}: {body[:500]}") from exc
        except OSError as exc:
            raise RuntimeError(f"GitHub API transport error: {exc}") from exc
        return json.loads(raw.decode("utf-8"))


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if is_dataclass(value):
        return _jsonable(asdict(value))
    return repr(value)


def _case_goal(case: dict[str, Any]) -> str:
    parts = [
        "You are the tested Catalyst evidence assistant in a live user-capability benchmark.",
        "Answer the user's request naturally and concisely.",
        "Use supplied local evidence first when it is sufficient.",
        "When local evidence is absent or materially weaker than the current repository authority, use the github_repo_read tool.",
        "Never invent evidence, customer counts, source content, or commit identities.",
        "If authoritative evidence still cannot establish the requested claim, say so clearly and fail closed.",
        "When using repository evidence, mention that it came from the current repository authority.",
        "",
        f"CASE: {case['case_id']}",
        f"USER TASK: {case['statement']}",
    ]
    if case.get("local_evidence"):
        parts.append(f"LOCAL EVIDENCE:\n{case['local_evidence']}")
    else:
        parts.append("LOCAL EVIDENCE: none supplied")
    return "\n".join(parts)


def _tool_calls(history) -> list[dict[str, Any]]:
    calls = []
    for step in history:
        if isinstance(step.decision, Act):
            calls.append(
                {
                    "capability_id": step.decision.action.capability_id,
                    "parameters": _jsonable(step.decision.action.parameters),
                    "observation": _jsonable(step.observation),
                    "execution_id": step.execution_id,
                }
            )
    return calls


def _usage(history) -> dict[str, int]:
    input_tokens = 0
    output_tokens = 0
    known = False
    for step in history:
        record = step.model_call
        if record is not None and record.usage is not None:
            known = True
            input_tokens += record.usage.input_tokens
            output_tokens += record.usage.output_tokens
    return {
        "known": known,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _answer(snapshot) -> str:
    if not snapshot.history:
        return ""
    decision = snapshot.history[-1].decision
    if isinstance(decision, Complete):
        return decision.reason or ""
    return ""


def _contains_production_not_complete(text: str) -> bool:
    low = text.lower()
    return (
        ("not" in low and "production" in low and ("complete" in low or "ready" in low))
        or "not a production-complete enterprise platform" in low
        or "not production-complete" in low
    )


def _insufficient(text: str) -> bool:
    low = text.lower()
    phrases = [
        "cannot determine",
        "can't determine",
        "not stated",
        "not establish",
        "insufficient evidence",
        "does not provide",
        "doesn't provide",
        "no evidence",
        "not available",
    ]
    return any(p in low for p in phrases)


def _numeric_customer_claim(text: str) -> bool:
    return bool(
        re.search(r"(?:customers?|enterprises?).{0,24}\b\d+\b|\b\d+\b.{0,24}(?:customers?|enterprises?)", text, re.I)
    )


def _score(case_id: str, answer: str, calls: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    resources = [c.get("parameters", {}).get("resource") for c in calls if c.get("capability_id") == "github_repo_read"]
    gates: list[tuple[str, bool]] = []
    low = answer.lower()

    if case_id == "UC-001-local-grounded":
        gates = [
            ("core idea is correctly stated", "rich ecosystem" in low and "small constitutional core" in low),
            ("remote API is not used when local evidence is sufficient", not resources),
        ]
    elif case_id == "UC-002-remote-fallback":
        gates = [
            ("current README is fetched", "readme" in resources),
            ("answer rejects production-complete claim", _contains_production_not_complete(answer)),
            ("answer identifies repository authority", "repository" in low or "readme" in low),
        ]
    elif case_id == "UC-003-fail-closed":
        gates = [
            ("repository authority is checked", "readme" in resources),
            ("unsupported customer count is not invented", not _numeric_customer_claim(answer)),
            ("insufficient evidence is explicit", _insufficient(answer)),
        ]
    elif case_id == "UC-004-authority-conflict":
        gates = [
            ("current README is fetched", "readme" in resources),
            ("current repository outranks unverified note", "repository" in low or "readme" in low),
            ("production-ready claim is rejected", _contains_production_not_complete(answer)),
        ]
    elif case_id == "UC-005-current-state-multitool":
        main_sha = None
        for c in calls:
            obs = c.get("observation") or {}
            if isinstance(obs, dict):
                data = obs.get("data") if "data" in obs else obs
                if isinstance(data, dict) and data.get("resource") == "main_branch":
                    main_sha = data.get("commit_sha")
        gates = [
            ("current main identity is fetched", "main_branch" in resources),
            ("current README is fetched", "readme" in resources),
            ("exact fetched main SHA is returned", bool(main_sha and main_sha in answer)),
            ("README production-complete claim is rejected", _contains_production_not_complete(answer)),
        ]
    else:
        gates = [("known case", False)]

    rendered = [{"gate": name, "pass": passed} for name, passed in gates]
    return rendered, 100 if all(passed for _, passed in gates) else 0


def _write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Catalyst Minimum Usable V0.2 — Live Capability Evaluation",
        "",
        f"- status: **{report['status']}**",
        f"- provider base: `{report['provider']['base_url']}`",
        f"- model: `{report['provider']['model']}`",
        f"- benchmark: `{report['benchmark_id']}`",
        f"- passed: **{report['summary']['passed']}/{report['summary']['total']}**",
        "",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                f"## {case['case_id']} — {case['status']}",
                "",
                f"Score: **{case.get('score', 'N/A')}**",
                "",
                "### Real answer",
                "",
                case.get("answer", ""),
                "",
                "### Tool/API calls",
                "",
                "```json",
                json.dumps(case.get("tool_calls", []), ensure_ascii=False, indent=2),
                "```",
                "",
                "### Critical gates",
                "",
            ]
        )
        for gate in case.get("critical_gates", []):
            lines.append(f"- {'PASS' if gate['pass'] else 'FAIL'} — {gate['gate']}")
        if case.get("error"):
            lines.extend(["", f"Error: `{case['error']}`"])
        lines.append("")
    (OUT / "LIVE_CAPABILITY_EVALUATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("CATALYST_LIVE_API_KEY", "").strip()
    base_url = os.getenv("CATALYST_LIVE_BASE_URL", "https://api.deepseek.com").strip()
    model = os.getenv("CATALYST_LIVE_MODEL", "deepseek-v4-flash").strip()
    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    if not api_key or not github_token:
        blocked = {
            "status": "LIVE_GATE_BLOCKED",
            "reason": "CATALYST_LIVE_API_KEY and GITHUB_TOKEN are required; no fake fallback is permitted.",
            "api_key_present": bool(api_key),
            "github_token_present": bool(github_token),
        }
        (OUT / "LIVE_GATE_BLOCKED.json").write_text(json.dumps(blocked, indent=2), encoding="utf-8")
        print(json.dumps(blocked))
        return 2

    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    private = json.loads(PRIVATE.read_text(encoding="utf-8"))
    provider = OpenAICompatibleModelProvider(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=float(os.getenv("CATALYST_LIVE_TIMEOUT", "90")),
    )

    report: dict[str, Any] = {
        "status": "RUNNING",
        "benchmark_id": public["benchmark_id"],
        "provider": {"base_url": base_url, "model": model},
        "started_at_unix": time.time(),
        "cases": [],
    }

    for case in public["cases"]:
        started = time.time()
        result: dict[str, Any] = {"case_id": case["case_id"]}
        try:
            runtime = Runtime(
                reasoner=LLMReasoner(provider, decision_protocol="native_tools"),
                capabilities={"github_repo_read": GitHubRepositoryReadCapability(github_token)},
                policy=LivePolicy(),
                state_store=InMemoryStateStore(),
            )
            final = runtime.start(Goal(_case_goal(case)))
            answer = _answer(final)
            calls = _tool_calls(final.history)
            gates, score = _score(case["case_id"], answer, calls)
            result.update(
                {
                    "status": "PASS" if score == 100 else "FAIL",
                    "score": score,
                    "answer": answer,
                    "tool_calls": calls,
                    "usage": _usage(final.history),
                    "step_count": len(final.history),
                    "critical_gates": gates,
                    "duration_ms": round((time.time() - started) * 1000),
                }
            )
        except Exception as exc:  # preserve infrastructure failure separately
            result.update(
                {
                    "status": "INFRASTRUCTURE_FAILED",
                    "score": None,
                    "failure_owner": "live_model_or_external_api_or_runtime",
                    "error": f"{type(exc).__name__}: {exc}",
                    "duration_ms": round((time.time() - started) * 1000),
                }
            )
        report["cases"].append(result)

    passed = sum(1 for c in report["cases"] if c["status"] == "PASS")
    infra = sum(1 for c in report["cases"] if c["status"] == "INFRASTRUCTURE_FAILED")
    report["summary"] = {"passed": passed, "total": len(report["cases"]), "infrastructure_failed": infra}
    report["status"] = "PASS" if passed == len(report["cases"]) else "FAIL"
    report["finished_at_unix"] = time.time()
    (OUT / "live_capability_evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(report)
    print(json.dumps(report["summary"]))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
