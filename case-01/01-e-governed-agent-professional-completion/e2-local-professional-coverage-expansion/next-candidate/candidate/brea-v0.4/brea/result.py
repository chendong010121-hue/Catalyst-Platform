"""FN-07 — Result Composition & Attribution (AGENT-OWNED BEHAVIOR).

Assembles RegulationEvidenceResult; enterprise attribution is metadata only and
never participates in professional regulation meaning (OBL-06).

E1 (IMPLEMENTATION-ONLY): backward-compatible Case-local metadata extension —
`query_mode` / `standard_id` record the evidence-query mode and resolved standard,
so retrieval vs applicability is observable (spec §13) without changing the
7-field Result contract (spec §11).
"""
from __future__ import annotations

from datetime import datetime, timezone

from .contracts import (
    ArtifactRef,
    EvidenceItem,
    ImplementationMetadata,
    RegulationEvidenceResult,
    Uncertainty,
)


def build_result(
    request_id: str,
    status: str,
    conclusion: str,
    evidence_items: list[EvidenceItem],
    artifacts: list[ArtifactRef],
    uncertainty: Uncertainty,
    attribution: dict[str, str | None],
    corpus_sha: dict[str, str],
    out_dir=None,  # noqa: ARG001  (reserved for FN-08 output routing)
    engine: str = "brea-deterministic-v0.4",
    query_mode: str = "QMODE-05",
    standard_id: str | None = None,
    professional_trace: dict | None = None,
) -> RegulationEvidenceResult:
    metadata = ImplementationMetadata(
        engine=engine,
        deterministic=True,
        model_used="none",
        corpus=corpus_sha,
        enterprise_context_attribution=attribution,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        query_mode=query_mode,
        standard_id=standard_id,
        professional_trace=professional_trace or {},
    )
    return RegulationEvidenceResult(
        request_id=request_id,
        status=status,
        conclusion=conclusion,
        evidence_items=tuple(evidence_items),
        artifacts=tuple(artifacts),
        uncertainty=uncertainty,
        implementation_metadata=metadata,
    )
