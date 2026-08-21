"""FN-01 / FN-07 contracts — Case-local input/output boundary.

Stable Case-local equivalent of RegulationEvidenceResult. Not a Platform Standard contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EnterpriseContext:
    organization_id: str
    user_id: str
    project_id: str | None = None


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    question: str
    project_context: dict[str, Any]
    regulation_context: dict[str, Any]
    enterprise_context: EnterpriseContext


@dataclass(frozen=True)
class EvidenceItem:
    source_identity: str
    source_title: str
    source_version_or_date: str
    locator: str
    evidence_type: str
    evidence_content: str
    claim_relation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    title: str
    path: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Uncertainty:
    level: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImplementationMetadata:
    engine: str
    deterministic: bool
    model_used: str
    corpus: dict[str, str]
    enterprise_context_attribution: dict[str, str | None]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegulationEvidenceResult:
    request_id: str
    status: str
    conclusion: str
    evidence_items: tuple[EvidenceItem, ...]
    artifacts: tuple[ArtifactRef, ...]
    uncertainty: Uncertainty
    implementation_metadata: ImplementationMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status,
            "conclusion": self.conclusion,
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "uncertainty": self.uncertainty.to_dict(),
            "implementation_metadata": self.implementation_metadata.to_dict(),
        }
