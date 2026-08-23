"""BREA — Building Regulation Evidence Agent (CASE 01 Governed Candidate v0.1).

Whole-Agent package: FN-01 intake -> FN-02..FN-08 governed/private composition
-> FN-07 RegulationEvidenceResult. Deterministic, stdlib-only.
"""
from .identity import AGENT_ID, AGENT_NAME, VERSION, PROFESSIONAL_PURPOSE
from .contracts import (
    ArtifactRef,
    EnterpriseContext,
    EvidenceItem,
    ImplementationMetadata,
    RegulationEvidenceResult,
    RequestContext,
    Uncertainty,
)
from .runner import answer

__version__ = VERSION
__all__ = [
    "AGENT_ID",
    "AGENT_NAME",
    "VERSION",
    "PROFESSIONAL_PURPOSE",
    "answer",
    "ArtifactRef",
    "EnterpriseContext",
    "EvidenceItem",
    "ImplementationMetadata",
    "RegulationEvidenceResult",
    "RequestContext",
    "Uncertainty",
]
