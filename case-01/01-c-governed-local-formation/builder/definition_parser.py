"""Case-scoped parser for the accepted BUILDER_CONSUMABLE_DEFINITION (C-01 closure).

The accepted governed definition is the AUTHORITATIVE architecture input. This
parser extracts identity / purpose / functions / seams / obligations / allowed
assets / corpus reference / private freedom deterministically. Intentionally
case-scoped — not a generic schema engine.
"""
from __future__ import annotations

import re

EXPECTED_DEFINITION_SHA = "6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4"

_FN_ROW = re.compile(r"^\|\s*FN-(\d{2})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$")
_SEAM_LINE = re.compile(r"^SEAM-(\d{2})\s+(.+?)（(.+?)；FN-(.+?)）$")
_OBL_TOKEN = re.compile(r"OBL-\d{2}")
_ASSET_TOKEN = re.compile(r"A-\d+[a-z]?")


def _sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d+)\.\s+(.*)$", line)
        if match:
            current = match.group(1)
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def parse_identity(section: str) -> dict[str, str]:
    identity: dict[str, str] = {}
    for line in section.splitlines():
        match = re.match(r"^\s*(ID|VERSION|OWNER|DOMAIN)\s+(.+)$", line)
        if match:
            identity[match.group(1).lower()] = match.group(2).strip()
    return identity


def parse_functions(section: str) -> dict[str, dict[str, str]]:
    functions: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        match = _FN_ROW.match(line.strip())
        if match:
            fn = f"FN-{match.group(1)}"
            functions[fn] = {
                "name": match.group(2).strip().strip("**"),
                "governance": match.group(3).strip().strip("**"),
                "deps": match.group(4).strip().strip("**"),
            }
    return functions


def parse_seams(section: str) -> dict[str, dict[str, str]]:
    seams: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        match = _SEAM_LINE.match(line.strip())
        if match:
            seam = f"SEAM-{match.group(1)}"
            seams[seam] = {
                "name": match.group(2).strip(),
                "owner": match.group(3).strip(),
                "functions": match.group(4).strip(),
            }
    return seams


def parse_obligations(section: str) -> set[str]:
    # Accepted obligations are declared on the first OBL-bearing line of §4;
    # the continuation line only lists DEFERRED OBL-07..10.
    for line in section.splitlines():
        tokens = {token for token in _OBL_TOKEN.findall(line)}
        if tokens:
            return tokens
    return set()


def parse_allowed_assets(section: str) -> set[str]:
    return {token for token in _ASSET_TOKEN.findall(section)}


def parse_purpose(section: str) -> str:
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            return stripped.lstrip("> ").strip()
    return ""


def parse_definition(text: str) -> dict:
    sections = _sections(text)
    return {
        "identity": parse_identity(sections.get("1", "")),
        "purpose": parse_purpose(sections.get("2", "")),
        "functions": parse_functions(sections.get("5", "")),
        "seams": parse_seams(sections.get("10", "")),
        "obligations": parse_obligations(sections.get("4", "")),
        "allowed_assets": parse_allowed_assets(sections.get("7", "")),
        "corpus_manifest_referenced": "LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md" in sections.get("8", ""),
        "private_freedom_present": bool(sections.get("11", "").strip()),
    }


def validate_architecture(parsed: dict) -> None:
    expected_fns = {f"FN-{index:02d}" for index in range(1, 12)}
    expected_seams = {"SEAM-01", "SEAM-02", "SEAM-03"}
    expected_obls = {f"OBL-{index:02d}" for index in range(1, 7)}
    if set(parsed["functions"]) != expected_fns:
        raise ValueError(f"definition FN set mismatch: {sorted(set(parsed['functions']) ^ expected_fns)}")
    if set(parsed["seams"]) != expected_seams:
        raise ValueError("definition SEAM set mismatch")
    if parsed["obligations"] != expected_obls:
        raise ValueError("definition OBL set mismatch")
    if not parsed["purpose"] or "test Catalyst" in parsed["purpose"]:
        raise ValueError("definition purpose missing or invalid")
    if not parsed["identity"].get("id") or not parsed["identity"].get("version"):
        raise ValueError("definition identity incomplete")
    if not parsed["corpus_manifest_referenced"]:
        raise ValueError("definition does not reference the corpus manifest")
    if not parsed["private_freedom_present"]:
        raise ValueError("definition lacks private implementation freedom")
    for seam, info in parsed["seams"].items():
        if not info["functions"]:
            raise ValueError(f"{seam} has no function membership")
