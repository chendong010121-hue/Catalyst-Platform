"""Compatibility characterization through existing candidate consumer interfaces."""
import shutil
from pathlib import Path

import pytest

from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.understand_wiki import UnderstandWikiAdapter
from test_understand_wiki_u0 import _load_result, _submit, _workspace


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("scenario", ["fresh", "stale", "missing", "ambiguous", "outside", "read_error",
                                      "duplicate_root", "escape"])
def test_graph_and_evidence_keep_source_status_contract(tmp_path, monkeypatch, backend, scenario):
    root, wiki, gateway = _workspace(tmp_path, backend)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    recorder = RunRecorder(JsonlTraceStore(tmp_path / "architecture-trace"),
                           run_id="architecture-source", request_id="source-request",
                           invocation_id="source-characterization")
    recorder.start(request_kind="architecture.source.characterization")
    port = UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), root)
    target = root / "monthly_rules.md"
    if scenario == "stale":
        target.write_text("changed synthetic source", encoding="utf-8")
    elif scenario == "missing":
        target.unlink()
    elif scenario == "ambiguous":
        second = tmp_path / "second"
        shutil.copytree(root, second)
        wiki.roots = (root, second)
    elif scenario == "outside":
        # A missing admitted root may not fall through to an unrelated source.
        wiki.roots = (tmp_path / "nonexistent-root",)
    elif scenario == "duplicate_root":
        wiki.roots = (root, root)
    elif scenario == "escape":
        # Same bytes outside the admitted root must still be unavailable.
        (root.parent / "outside.md").write_bytes(target.read_bytes())
        candidate = port._candidate(candidate_id)
        binding = next(row for row in candidate["source_bindings"]
                       if row["relative_path"] == "monthly_rules.md")
        binding["relative_path"] = "../outside.md"
        monkeypatch.setattr(port, "_candidate", lambda _: candidate)
    elif scenario == "read_error":
        original = Path.read_bytes

        def denied(path):
            if path == target:
                raise PermissionError("synthetic source read denial")
            return original(path)

        monkeypatch.setattr(Path, "read_bytes", denied)

    graph = port.candidate_graph(candidate_id)
    relative_path = "../outside.md" if scenario == "escape" else "monthly_rules.md"
    source = next(row for row in graph["nodes"]
                  if row["type"] == "source_revision" and row["relative_path"] == relative_path)
    expected = "fresh" if scenario == "fresh" else "stale" if scenario == "stale" else "unknown"
    assert source["freshness_status"] == expected
    evidence_id = _load_result()["evidence_refs"][1]["evidence_id"]
    if scenario == "read_error":
        # Preserve the evidence consumer's existing exception contract.
        with pytest.raises(PermissionError):
            port.evidence(candidate_id, evidence_id)
    else:
        evidence = port.evidence(candidate_id, evidence_id)
        assert evidence["status"] == ("RESOLVED" if scenario == "fresh" else
                                       "STALE_SOURCE_REVISION" if scenario == "stale" else
                                       "SOURCE_UNAVAILABLE")
        assert "quote" not in evidence
    assert wiki.semantic_state()["active_version_id"] is None
