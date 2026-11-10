"""Bounded data-only method packages; no import, execution, or separate registry.

ADAPT: Penguin directory-skills regular-file/cap checks and snapshot identity
separation (2b8116ce278656cbc184f7c40ceff1d358a87394, Apache-2.0).
No upstream production code or runtime dependencies are copied.
"""
from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

from .components import ComponentError, _sha256, _COMPONENT_ID, _VERSION

MAX_METHOD_FILE_BYTES = 128 * 1024
MAX_METHOD_TOTAL_BYTES = 512 * 1024
MAX_METHOD_FILES = 64
PRODUCT_INTERFACE = "project-analysis.v1"
METHOD_SERVICES = {"project_inspect", "project_expand_evidence", "project_submit_analysis"}
_FIELDS = {"manifest_version", "component_id", "resource_type", "version", "skill_name",
           "required_product_interface", "provides", "requires", "files", "license_sources",
           "evaluation_refs", "llm_visibility"}


def freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    return value


def _real_entry(path: Path, *, directory: bool = False) -> os.stat_result:
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        or (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode))):
        raise ComponentError("method package requires regular files/directories without symlinks or reparse points")
    return info


def _safe_path(name: Any) -> bool:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\0" in name:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ("", ".", "..") for p in name.split("/")):
        return False
    return name == "SKILL.md" or (
        name.startswith("references/") and path.suffix in (".md", ".json")
        and all(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", p) for p in path.parts)
    )


@dataclass(frozen=True)
class MethodCandidate:
    package_dir: Path
    manifest: dict[str, Any]
    manifest_bytes: bytes
    files: dict[str, bytes]
    package_sha256: str
    manifest_sha256: str
    source_sha256: str

    @property
    def component_id(self) -> str:
        return self.manifest["component_id"]

    @property
    def version(self) -> str:
        return self.manifest["version"]

    def public_record(self) -> dict[str, Any]:
        return {key: self.manifest[key] for key in (
            "component_id", "resource_type", "version", "skill_name", "required_product_interface",
            "provides", "requires", "llm_visibility")}

    def snapshot(self) -> Any:
        return freeze({"component_id": self.component_id, "version": self.version,
                       "package_sha256": self.package_sha256,
                       "files": {key: value.decode("utf-8") for key, value in self.files.items()},
                       "manifest": self.manifest})


def validate_method_bundle(package_dir: Path, manifest: dict, manifest_bytes: bytes) -> MethodCandidate:
    """Validate the complete allowlisted payload before any installation/state change."""
    try:
        # Check the original path and each ancestor before resolving a junction.
        for ancestor in (package_dir, *package_dir.parents):
            _real_entry(ancestor, directory=True)
        package_dir = package_dir.resolve(strict=True)
        if set(manifest) != _FIELDS or manifest.get("resource_type") != "method_data":
            raise ComponentError("method manifest has missing or unsupported fields")
        if type(manifest["manifest_version"]) is not int or manifest["manifest_version"] != 1:
            raise ComponentError("method manifest version is unsupported")
        if not isinstance(manifest["component_id"], str) or not _COMPONENT_ID.fullmatch(manifest["component_id"]):
            raise ComponentError("method component_id is invalid")
        if not isinstance(manifest["version"], str) or not _VERSION.fullmatch(manifest["version"]):
            raise ComponentError("method version must be an exact semantic version")
        if (manifest["skill_name"] == "understand-project" and manifest["provides"] == ["understand-project"]):
            interface, services = PRODUCT_INTERFACE, METHOD_SERVICES
        elif (manifest["component_id"] == "development-workflow" and
              manifest["skill_name"] == "development-workflow" and
              manifest["provides"] == ["development-workflow"]):
            interface, services = "evaluation-workflow.v1", {"prepare_evaluation_workflow"}
        elif (manifest["component_id"] == "enterprise-ontology"
              and manifest["skill_name"] == "understand-enterprise-semantics"
              and manifest["provides"] == ["enterprise-ontology"]):
            # A second contract, added only together with the entry point that consumes it
            # (`semantic_method.run_semantic_method`): admission alone would say a method is
            # "registered" while nothing could execute it, which is the state this contract
            # exists to end. The services named here are the ones that entry point provides.
            interface, services = "semantic-proposal.v1", {"semantic_submit_candidate"}
        else:
            raise ComponentError("method provides an unknown Skill contract")
        if manifest["required_product_interface"] != interface:
            raise ComponentError("method requires an unavailable product interface")
        requires = manifest["requires"]
        if (not isinstance(requires, list) or any(not isinstance(v, str) for v in requires)
            or len(requires) != len(set(requires)) or set(requires) != services):
            raise ComponentError("method requires unavailable product services")
        if manifest["llm_visibility"] != "explicit":
            raise ComponentError("method visibility must be explicit")
        licenses = manifest["license_sources"]
        if not isinstance(licenses, list) or not licenses or any(
            not isinstance(item, dict) or set(item) != {"name", "revision", "license", "adaptation"}
            or any(not isinstance(v, str) or not v.strip() for v in item.values()) for item in licenses):
            raise ComponentError("method requires explicit license provenance")
        refs = manifest["evaluation_refs"]
        if not isinstance(refs, list) or not refs or any(not isinstance(v, str) or not v.strip() for v in refs):
            raise ComponentError("method evaluation references are invalid")
        allowlist = manifest["files"]
        if (not isinstance(allowlist, dict) or "SKILL.md" not in allowlist
            or not 1 <= len(allowlist) <= MAX_METHOD_FILES
            or any(not _safe_path(name) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                   for name, digest in allowlist.items())
            or len({name.casefold() for name in allowlist}) != len(allowlist)):
            raise ComponentError("method file allowlist is invalid or exceeds its cap")
        if interface == 'evaluation-workflow.v1' and not {
            'references/build-eval.md', 'references/eval-audit.md', 'references/hillclimb.md'
        } <= set(allowlist):
            raise ComponentError('development method is missing required workflow guides')
        total = len(manifest_bytes)
        if total > MAX_METHOD_FILE_BYTES:
            raise ComponentError("method manifest exceeds file size limit")
        files = {}
        for current, dirs, names in os.walk(package_dir, followlinks=False):
            for name in dirs:
                directory = Path(current) / name
                _real_entry(directory, directory=True)
                rel = directory.relative_to(package_dir).as_posix()
                if not any(key.startswith(rel + "/") for key in allowlist):
                    raise ComponentError("method package contains an unlisted directory")
            for name in names:
                path = Path(current) / name
                info = _real_entry(path)
                rel = path.relative_to(package_dir).as_posix()
                if rel == "manifest.json":
                    continue
                if rel not in allowlist:
                    raise ComponentError("method package contains an unlisted or executable file")
                total += info.st_size
                if info.st_size > MAX_METHOD_FILE_BYTES or total > MAX_METHOD_TOTAL_BYTES:
                    raise ComponentError("method package exceeds file or total size limit")
                data = path.read_bytes()
                if len(data) != info.st_size or _sha256(data) != allowlist[rel]:
                    raise ComponentError("method file SHA-256 does not match manifest")
                text = data.decode("utf-8")
                if path.suffix == ".json":
                    from .components import _no_duplicate_pairs
                    import json
                    json.loads(text, object_pairs_hook=_no_duplicate_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ComponentError("non-finite method JSON")))
                files[rel] = data
        if set(files) != set(allowlist):
            raise ComponentError("method package is missing allowlisted files")
        payload = b"".join(name.encode("utf-8") + b"\0" + files[name] + b"\0" for name in sorted(files))
        return MethodCandidate(package_dir, manifest, manifest_bytes, files,
                               _sha256(b"catalyst-method-data-v1\0" + manifest_bytes + b"\0" + payload),
                               _sha256(manifest_bytes), _sha256(payload))
    except ComponentError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ComponentError("method package contains unreadable or invalid data") from exc
