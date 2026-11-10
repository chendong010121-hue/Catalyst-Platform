"""R1: discover actual local capability bindings and inspect that run."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


PRODUCT_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "catalyst_platform",
            *arguments,
            "--workspace",
            str(workspace),
        ],
        cwd=PRODUCT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _payload(process: subprocess.CompletedProcess[str]) -> dict:
    assert process.stdout, process.stderr
    return json.loads(process.stdout)


def test_discover_lists_bound_capabilities_with_cold_process_trace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    discover_process = _run_cli(workspace, "discover", "--wiki-root", str(wiki))

    assert discover_process.returncode == 0, discover_process.stderr
    discovered = _payload(discover_process)
    descriptors = discovered["capabilities"]
    ids = [item["id"] for item in descriptors]
    assert ids == sorted(ids)
    assert {item["id"] for item in descriptors} == {
        "compose_report",
        "read_file_title",
        "wiki_search",
        "write_artifact",
    }
    assert all(item["capability_version"] for item in descriptors)
    assert ("ripgrep_search", "1.0.0") not in {
        (item["id"], item["capability_version"]) for item in descriptors
    }
    assert discovered["catalog_scope"] == "local_registered_product_bindings"
    assert discovered["authorization"] == "not_evaluated_until_invocation"
    assert discovered["invocation_routes"] == [
        {
            "capability_id": item["id"],
            "capability_version": item["capability_version"],
            "command": "invoke",
        }
        for item in descriptors
    ]
    canonical_catalog = json.dumps(
        {
            "capabilities": descriptors,
            "invocation_routes": discovered["invocation_routes"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert discovered["catalog_sha256"] == hashlib.sha256(canonical_catalog).hexdigest()

    inspect_process = _run_cli(workspace, "inspect", "--run-id", discovered["run_id"])

    assert inspect_process.returncode == 0, inspect_process.stderr
    inspected = _payload(inspect_process)
    assert inspected["run_id"] == discovered["run_id"]
    assert inspected["terminal_status"] == "success"
    event_types = [event["event_type"] for event in inspected["events"]]
    assert event_types[0] == "request.started"
    assert event_types[1] == "span.started"
    assert event_types[-1] == "request.terminal"
    assert "span.ended" in event_types
    discovered_event = next(
        event for event in inspected["events"] if event["event_type"] == "capabilities.discovered"
    )
    assert discovered_event["capability_count"] == len(descriptors)
    assert discovered_event["catalog_sha256"] == discovered["catalog_sha256"]
    expected_event_summaries = []
    for descriptor in descriptors:
        canonical_descriptor = json.dumps(
            descriptor,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        expected_event_summaries.append(
            {
                "id": descriptor["id"],
                "capability_version": descriptor["capability_version"],
                "descriptor_sha256": hashlib.sha256(canonical_descriptor).hexdigest(),
                "side_effect": descriptor["execution"]["side_effect"],
            }
        )
    assert discovered_event["capabilities"] == expected_event_summaries
    assert discovered_event["invocation_routes"] == discovered["invocation_routes"]
    assert Path(discovered["trace_path"]).is_file()


@pytest.mark.parametrize(
    ("manifest_data", "expected_error_type"),
    [
        ({"manifest_version": 99, "external": {}}, "WorkbenchError"),
        ({"manifest_version": 1, "external": {"ripgrep_search": []}}, "AttributeError"),
    ],
)
def test_discovery_failure_has_a_terminal_trace_when_catalog_cannot_load(
    tmp_path: Path, manifest_data: dict, expected_error_type: str
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    manifest = workspace / ".catalyst" / "capabilities.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")

    discover_process = _run_cli(workspace, "discover", "--wiki-root", str(wiki))

    assert discover_process.returncode == 2
    failed = _payload(discover_process)
    assert failed["status"] == "failure"
    assert failed["error"]["type"] == expected_error_type
    assert Path(failed["trace_path"]).is_file()

    inspect_process = _run_cli(workspace, "inspect", "--run-id", failed["run_id"])

    assert inspect_process.returncode == 0, inspect_process.stderr
    inspected = _payload(inspect_process)
    assert inspected["terminal_status"] == "failure"
    assert any(
        event["event_type"] == "capabilities.discovery.failed"
        for event in inspected["events"]
    )
