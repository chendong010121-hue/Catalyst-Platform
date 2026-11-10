"""The identity of one released capability line, derived from bytes on disk.

A release is quoted by this file, and every field in it is computed here rather than typed
by hand: which product entry points belong to the line, the exact method package a
workspace may admit, the concept set a scope extracts with, the extraction modes the
execution seam serves, what one run's record binds, and what this release does not include.

Two things are deliberately absent.

There is no commit or tree here. A file committed into a tree cannot name that tree, and a
digest that pins itself would be the one field nobody could check. The merge receipt names
the commit; this file names the bytes.

There is no test result here either. A test that writes its own pass into the artefact it
checks proves nothing, so this file names the command and the receipt carries what it said.

Nothing here calls a model, reads a workspace, or imports a method package's code:
`discover_local_component` validates a package by its bytes alone.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .components import ComponentError, discover_local_component
from .ontology_types import STARTER_PACK, concept_set_identity
from .semantic_method import EXTRACTION_MODES, SEMANTIC_INTERFACE

SCHEMA_VERSION = 1
RELEASE_NAME = "capability-consolidation-20261103"
METHOD_PATH = "methods/enterprise-ontology/0.1.0"
METHOD_COMPONENT = "enterprise-ontology"

# The product files this release is made of. Every one of them is read byte-for-byte, so a
# reader can tell "the same release" from "the same version number".
PRODUCT_ENTRY_POINTS = (
    ("catalyst_platform/knowledge_intake.py",
     "one explicit document enters Wiki as a candidate; the daily entry"),
    ("catalyst_platform/semantic_method.py",
     "the registered-method seam: acquire the lease, materialise the frozen files, run the "
     "port, record the run's identity, release the lease"),
    ("catalyst_platform/understand_wiki.py",
     "an Understand result submitted as one Wiki candidate"),
    ("catalyst_platform/semantic_wiki.py",
     "evaluate, decide and activate one candidate; read one version"),
    ("catalyst_platform/wiki.py",
     "the project Wiki store: sources, concepts, candidates, decisions, versions"),
    ("catalyst_platform/components.py",
     "admit one package by SHA-256 and freeze it for the length of a run"),
    ("catalyst_platform/method_bundle.py",
     "the data-only method contract (" + SEMANTIC_INTERFACE + ")"),
    ("catalyst_platform/ontology_types.py",
     "the concept set a scope extracts with, and how a spelling resolves to one type"),
    ("catalyst_platform/object_view.py",
     "one duty, event or condition read the same way from a candidate entry or an accepted one"),
    ("catalyst_platform/wiki_pages.py",
     "the page projection: what an entity page promises, including its object sections"),
    ("catalyst_platform/workspace_ui.py",
     "the local workbench: the Wiki route and the Enterprise routes"),
    ("catalyst_platform/review_surface.py",
     "the declared knowledge scopes, a run product read as it ran, and the review ledger"),
    ("catalyst_platform/workspace_assets/app.js",
     "the pages themselves: the Wiki entry, the Enterprise candidate picker and its tiers"),
    ("catalyst_platform/workspace_assets/styles.css",
     "how those pages lay out, including the bounded box a graph is browsed inside"),
    ("catalyst_platform/workspace_assets/index.html",
     "the workbench shell that loads the entry"),
    ("catalyst_platform/workspace_assets/wiki-contract.js",
     "the one reading contract: an address, a page, a version, a refusal, shared by both entries"),
    ("catalyst_platform/workspace_assets/business-graph.js",
     "the candidate's business picture: objects first, one-hop focus, evidence only on request"),
    ("catalyst_platform/workspace_assets/wiki.html",
     "the standalone reading page's shell"),
    ("catalyst_platform/workspace_assets/wiki.js",
     "the standalone reading page: pages, evidence, backlinks, scope and version in the address"),
    ("catalyst_platform/workspace_assets/wiki.css",
     "how the standalone reading page lays out"),
)

# What stays outside the product. Naming it here is the point: a reader of the release must
# not have to guess which of the files beside it are shipped and which are one card's repair.
NOT_SHIPPED = (
    ("p1-run-1/host", "the diagnosis host, per-card repairs and the delivery scripts"),
    ("p1-run-1/adapt", "adapters written to read one frozen card's answers"),
    ("p1-run-1/deliver", "candidate snapshots, receipts and review pages of past cards"),
    ("p1-run-1/m1-live2*", "the live cards and their captures"),
    ("p1-run-1/joint-handoff-20261103", "one joint hand-off's inputs, records and Wiki copy"),
    ("p1-run-1/methods/enterprise-ontology/build-0.1.0.py",
     "the builder that reproduced the package bytes from the live46 run snapshot"),
)

# Where one run's identity comes from. A run that cannot name all six is not identified:
# the package alone says nothing about what executed.
RUN_IDENTITY_FIELDS = (
    "method",            # component_id, version, package_sha256, skill_name
    "implementation",    # the product files above, by digest
    "concepts",          # the concept set version and its digest
    "extraction_mode",   # single_stage | source_local_two_stage
    "repairs",           # named and scoped, or explicitly "no repair was named"
    "sources",           # per-source digests as they were read
)

LIMITS = (
    "A candidate is a reading. It is not an accepted fact, and `CANDIDATE_ONLY` says so on the record.",
    "`authority_class=test_only` is a test admission inside a synthetic scope; it is never a business acceptance.",
    "The method package does not carry every rule that ran. Holder and type hints and the mechanical "
    "checks live in product code, so `package_sha256` alone is not a run identity; the release names both halves.",
    "The package's own `evaluation_refs` are v15-era. They are not evidence for this release, and no score "
    "in this line is a measurement of this build.",
    "A row the card marks unresolved stays in the card and is not carried into the candidate; it is still a "
    "question for a person, not a dropped fact.",
    "A graph is read with a limit (100 accepted objects, 500 candidate nodes). A larger graph is truncated "
    "and the reading says how many it kept.",
    "The starter concept set holds eleven types. A name with no concept is a gap in expression, not a zero, "
    "and `business_type` may stay empty while the entity is kept.",
)

ENABLE = (
    "PYTHONUTF8=1 python -m catalyst_platform component admit --workspace <workspace> "
    f"--source {METHOD_PATH} --expected-sha256 <package_sha256 from this file>",
    "PYTHONUTF8=1 python -m catalyst_platform component activate --workspace <workspace> "
    f"--component-id {METHOD_COMPONENT} --version 0.1.0",
)

VERIFY = (
    "PYTHONUTF8=1 python scripts/release_manifest.py --check",
    "PYTHONUTF8=1 python -m pytest tests/test_capability_release.py -q",
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def entry_points(repo_root: Path | str) -> list[dict[str, Any]]:
    """Each product file this release is made of, by digest. A missing file is an error."""
    root = Path(repo_root)
    rows = []
    for relative, role in PRODUCT_ENTRY_POINTS:
        path = relative.split("#", 1)[0]
        target = root / path
        if not target.is_file():
            raise FileNotFoundError(f"release entry point is missing: {path}")
        rows.append({"path": path, "role": role, "sha256": _sha(target.read_bytes())})
    return rows


def implementation_digest(entries: list[dict[str, Any]]) -> str:
    """One digest over the shipped files, in the order the release names them."""
    payload = "".join(f"{row['path']}\0{row['sha256']}\0" for row in entries)
    return _sha(("catalyst-release-implementation-v1\0" + payload).encode("utf-8"))


def method_identity(repo_root: Path | str) -> dict[str, Any]:
    """The package a workspace may admit, validated by the product's own admission gate."""
    root = Path(repo_root)
    package = root / METHOD_PATH
    try:
        candidate = discover_local_component(package)
    except ComponentError as exc:
        raise ComponentError(f"the shipped method package does not pass admission: {exc}") from exc
    if candidate.component_id != METHOD_COMPONENT:
        raise ComponentError("the shipped method package is not the component this release names")
    return {
        "path": METHOD_PATH,
        "component_id": candidate.component_id,
        "version": candidate.version,
        "skill_name": candidate.manifest["skill_name"],
        "interface": candidate.manifest["required_product_interface"],
        "provides": list(candidate.manifest["provides"]),
        "package_sha256": candidate.package_sha256,
        "manifest_sha256": candidate.manifest_sha256,
        "source_sha256": candidate.source_sha256,
        "files": dict(sorted(candidate.manifest["files"].items())),
    }


def concept_identity() -> dict[str, Any]:
    """The concept set a scope reads with before it declares one of its own."""
    return concept_set_identity(STARTER_PACK)


def manifest(repo_root: Path | str) -> dict[str, Any]:
    """Everything above, in one deterministic document."""
    entries = entry_points(repo_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "release": RELEASE_NAME,
        "interface": SEMANTIC_INTERFACE,
        "product": {
            "entry_points": entries,
            "implementation_sha256": implementation_digest(entries),
        },
        "method": method_identity(repo_root),
        "concepts": concept_identity(),
        "extraction_modes": list(EXTRACTION_MODES),
        "run_identity_fields": list(RUN_IDENTITY_FIELDS),
        "not_shipped": [{"path": path, "what": what} for path, what in NOT_SHIPPED],
        "limits": list(LIMITS),
        "enable": list(ENABLE),
        "verify": list(VERIFY),
    }


def differences(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Where a stored release file no longer describes the bytes beside it."""
    if expected == actual:
        return []
    out: list[str] = []

    def walk(left: Any, right: Any, path: str) -> None:
        if type(left) is not type(right):
            out.append(f"{path}: type {type(left).__name__} -> {type(right).__name__}")
            return
        if isinstance(left, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left:
                    out.append(f"{path}.{key}: added")
                elif key not in right:
                    out.append(f"{path}.{key}: removed")
                else:
                    walk(left[key], right[key], f"{path}.{key}" if path else key)
            return
        if isinstance(left, list):
            if len(left) != len(right):
                out.append(f"{path}: {len(left)} entries -> {len(right)}")
            for index, (one, other) in enumerate(zip(left, right)):
                walk(one, other, f"{path}[{index}]")
            return
        if left != right:
            out.append(f"{path}: {str(left)[:60]!r} -> {str(right)[:60]!r}")

    walk(expected, actual, "")
    return out


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]
