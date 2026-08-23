"""Agent identity / version / purpose — E1 v0.2-candidate (IMPLEMENTATION-ONLY change).

Same governed Agent lineage (case-01.brea); new professional implementation Candidate.
Domain: Building Regulation / Engineering Construction Standards — architecture_pre_design.
Professional purpose unchanged (E1 Change Impact Review: UNCHANGED).
"""
from __future__ import annotations

AGENT_ID = "BREA"
AGENT_NAME = "Building Regulation Evidence Agent"
VERSION = "v0.2-candidate"
STATE = "CASE 01-E governed candidate (professional completion slice)"
DOMAIN = "Building Regulation / Engineering Construction Standards — architecture_pre_design"

PROFESSIONAL_PURPOSE = (
    "Use project context to provide reliable, applicable, traceable building-regulation "
    "evidence for architectural / preliminary design work, and explicitly return "
    "uncertainty or fail closed when reliable evidence is unavailable."
)

# Accepted functional decomposition (ST-01) and governed seams (ST-02).
# E1 change: FN-04/05/09 completion now also resolves through brea.query
# (generalized local evidence-query mechanism); decomposition itself UNCHANGED.
BREA_FUNCTION_MAP: dict[str, tuple[str, str, str]] = {
    "FN-01": ("Question & Context Intake", "brea.runner + brea.query", "DECLARED FUNCTION BOUNDARY"),
    "FN-02": ("Professional Fact Normalization", "brea.facts", "GOVERNED SEAM - SEAM-01"),
    "FN-03": ("Regulation Applicability Resolution", "brea.applicability", "GOVERNED SEAM - SEAM-02"),
    "FN-04": ("Evidence Locating & Extraction", "brea.evidence + brea.query", "GOVERNED SEAM - SEAM-03"),
    "FN-05": ("Evidence Binding & Numeric Safety", "brea.evidence", "GOVERNED SEAM - SEAM-03"),
    "FN-06": ("Uncertainty & Fail-Closed Decision", "brea.uncertainty", "DECLARED FUNCTION BOUNDARY"),
    "FN-07": ("Result Composition & Attribution", "brea.result", "DECLARED FUNCTION BOUNDARY"),
    "FN-08": ("Artifact & Provenance Preservation", "brea.evidence", "GOVERNED SEAM - SEAM-03"),
    "FN-09": ("Corpus Access & Parsing", "brea.corpus + brea.query", "PRIVATE IMPLEMENTATION"),
    "FN-10": ("Provider & Execution Plumbing", "brea.runner (deferred)", "PRIVATE / DEFERRED"),
    "FN-11": ("Local Runner / Service Shell", "brea.runner", "PRIVATE / DEFERRED"),
}

SEAM_MAP: dict[str, tuple[str, str, tuple[str, ...], str]] = {
    "SEAM-01": ("Professional Project Facts", "Domain", ("FN-02",), "brea.facts"),
    "SEAM-02": ("Regulation Applicability", "Domain", ("FN-03",), "brea.applicability"),
    "SEAM-03": ("Regulation Evidence", "Domain + Agent", ("FN-04", "FN-05", "FN-08"), "brea.evidence + brea.query"),
}

OBLIGATIONS = ("OBL-01", "OBL-02", "OBL-03", "OBL-04", "OBL-05", "OBL-06")
