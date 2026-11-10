"""Route bounded Understand requests and project typed results over existing owners.

This module owns task-local routing and projections. ProjectWiki, SemanticWiki,
the Workbench Capability Catalog, and Run Observability remain the owners of
persistent source evidence, ontology transitions, bindings, and run records.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tomllib
import uuid
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .observability import RunRecorder
from .semantic_wiki import SemanticWiki
from .wiki import ProjectWiki


class Intent(str, Enum):
    TASK_USE = "TASK_USE"
    KNOWLEDGE_PROPOSE = "KNOWLEDGE_PROPOSE"
    ASSET_REGISTER = "ASSET_REGISTER"


@dataclass(frozen=True)
class IntentRoute:
    intent: Intent
    target: str
    reason: str


@dataclass(frozen=True)
class SourceInventoryEntry:
    inventory_id: str
    relative_path: str
    media_type: str
    sha256: str
    byte_size: int


@dataclass(frozen=True)
class GroundedClaim:
    claim_id: str
    quote: str
    source_locator: str
    source_sha256: str
    line_start: int
    line_end: int
    authority: str
    status: str


@dataclass(frozen=True)
class TaskContext:
    request: str
    sources: tuple[SourceInventoryEntry, ...]
    claims: tuple[GroundedClaim, ...]
    authority: str = "TASK_ONLY"
    status: str = "ready"
    wiki_write: str = "NONE"


@dataclass(frozen=True)
class SemanticCandidate:
    candidate_id: str
    source_id: str
    source_revision: str
    status: str
    active: bool
    accepted: bool
    item_kinds: tuple[str, ...]
    submission_schema: str = "catalyst.external_candidate.v2"


@dataclass(frozen=True)
class AssetCandidate:
    asset_type: str
    name: str
    source_relative_path: str
    source_sha256: str
    description: str = ""
    version: str | None = None
    declared_tools: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    entrypoints: tuple[str, ...] = ()
    detected_effects: tuple[str, ...] = ()
    candidate_capabilities: tuple[str, ...] = ()
    registration_status: str = "DISCOVERED_ONLY"
    binding_status: str = "UNBOUND"
    permission_status: str = "NOT_EVALUATED"
    evaluation_status: str = "NOT_EVALUATED"
    execution_status: str = "NOT_EXECUTED"


@dataclass
class ActorContextFixture:
    """Explicit synthetic identity context; it is not an IAM credential."""

    actor_id: str
    enterprise_id: str
    project_id: str
    department_ids: tuple[str, ...]
    active_department_id: str | None
    department_labels: Mapping[str, str]
    readable_scope_ids: tuple[str, ...]
    permissions: frozenset[str]
    verified: bool = False
    simulation: bool = True

    def __post_init__(self) -> None:
        self.department_ids = tuple(self.department_ids)
        self.readable_scope_ids = tuple(self.readable_scope_ids)
        self.permissions = frozenset(self.permissions)
        self.department_labels = dict(self.department_labels)

    @property
    def scope_id(self) -> str:
        return f"enterprise:{self.enterprise_id}/project:{self.project_id}"


_EXCLUDED_DIRECTORIES = {
    ".git", ".catalyst", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
}
_ALLOWED_SUFFIXES = {
    ".md", ".txt", ".rst", ".pptx", ".json", ".py", ".toml", ".yaml", ".yml", ".xml",
}
_MAX_TEXT_BYTES = 2 * 1024 * 1024
_MAX_PPTX_BYTES = 16 * 1024 * 1024
_MAX_PPTX_UNCOMPRESSED = 32 * 1024 * 1024


def route_request(request: str) -> IntentRoute:
    """Choose one of the three logical entry points using explicit local rules."""
    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be non-empty text")
    text = request.casefold()
    asset_terms = ("skill", "agent", "workflow", "repo", "代码库", "能力")
    if any(term in text for term in ("注册", "登记")) and any(term in text for term in asset_terms):
        return IntentRoute(Intent.ASSET_REGISTER, "ASSET_CANDIDATE", "explicit_asset_registration")
    if any(term in text for term in ("是否可以复用", "检查这个skill", "检查这个 agent", "评估这个skill")):
        return IntentRoute(Intent.ASSET_REGISTER, "ASSET_CANDIDATE", "explicit_asset_inspection")
    if any(term in text for term in ("企业知识", "企业语义", "更新知识", "沉淀制度", "职责语义", "知识候选")):
        return IntentRoute(Intent.KNOWLEDGE_PROPOSE, "SEMANTIC_CANDIDATE", "explicit_knowledge_change")
    if "纪要" in text and any(term in text for term in ("提交", "记录", "分工")):
        return IntentRoute(Intent.KNOWLEDGE_PROPOSE, "PROJECT_SUGGESTION", "employee_source_suggestion")
    if "agent" in text and any(term in text for term in ("建立", "创建", "搭建", "构建")):
        return IntentRoute(Intent.TASK_USE, "AGENT_COMPOSITION", "agent_creation_is_a_consumer_task")
    if any(term in text for term in ("ppt", "汇报稿", "项目报告", "帮我写")):
        return IntentRoute(Intent.TASK_USE, "DOCUMENT_TASK", "task_local_document_use")
    return IntentRoute(Intent.TASK_USE, "TASK_DELIVERY", "default_task_use")


def _safe_path(path: Path | str, source_root: Path | str) -> tuple[Path, Path]:
    root = Path(source_root).expanduser().resolve()
    selected = Path(path).expanduser().resolve()
    if not selected.is_relative_to(root):
        raise ValueError("selected source is outside the explicit source root")
    if not selected.is_file():
        raise ValueError("selected source is not a regular file")
    lowered = selected.name.casefold()
    if lowered in {".env", "credentials", "secrets.json"} or selected.suffix.casefold() in {
        ".pem", ".key", ".p12", ".pfx",
    }:
        raise ValueError("credential-like files are not valid Understand inputs")
    return selected, root


def _media_type(path: Path) -> str:
    return {
        ".pptx": "presentation",
        ".md": "markdown",
        ".txt": "plain_text",
        ".rst": "restructured_text",
        ".json": "json_manifest",
        ".py": "python_source",
        ".toml": "toml_manifest",
        ".yaml": "yaml_manifest",
        ".yml": "yaml_manifest",
        ".xml": "xml_source",
    }.get(path.suffix.casefold(), "unknown")


def _inventory_entry(path: Path, root: Path) -> SourceInventoryEntry:
    raw = path.read_bytes()
    if len(raw) > _MAX_PPTX_BYTES:
        raise ValueError("source exceeds the bounded inventory size")
    digest = hashlib.sha256(raw).hexdigest()
    relative = path.relative_to(root).as_posix()
    return SourceInventoryEntry(
        inventory_id="inventory_" + hashlib.sha256(f"{relative}\0{digest}".encode("utf-8")).hexdigest()[:20],
        relative_path=relative,
        media_type=_media_type(path),
        sha256=digest,
        byte_size=len(raw),
    )


def inventory_sources(path: Path | str, *, source_root: Path | str) -> tuple[SourceInventoryEntry, ...]:
    """Inventory selected files inside one explicit root without running them."""
    root = Path(source_root).expanduser().resolve()
    selected = Path(path).expanduser().resolve()
    if not selected.is_relative_to(root):
        raise ValueError("inventory target is outside the explicit source root")
    if selected.is_file():
        if selected.suffix.casefold() not in _ALLOWED_SUFFIXES:
            raise ValueError("unsupported source type")
        return (_inventory_entry(*_safe_path(selected, root),),)
    if not selected.is_dir():
        raise ValueError("inventory target must be a file or directory")
    entries: list[SourceInventoryEntry] = []
    for current, directories, filenames in os.walk(selected, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name for name in directories
            if name.casefold() not in _EXCLUDED_DIRECTORIES
            and not (current_path / name).is_symlink()
        ]
        for filename in sorted(filenames):
            candidate = current_path / filename
            if candidate.is_symlink() or candidate.suffix.casefold() not in _ALLOWED_SUFFIXES:
                continue
            lowered = filename.casefold()
            if lowered in {".env", "credentials", "secrets.json"} or candidate.suffix.casefold() in {
                ".pem", ".key", ".p12", ".pfx",
            }:
                continue
            entries.append(_inventory_entry(candidate, root))
    return tuple(sorted(entries, key=lambda item: item.relative_path))


def _text_units(path: Path) -> list[tuple[str, str, int]]:
    raw = path.read_bytes()
    if path.suffix.casefold() == ".pptx":
        if len(raw) > _MAX_PPTX_BYTES:
            raise ValueError("presentation exceeds the bounded inspection size")
        units: list[tuple[str, str, int]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as package:
                infos = [info for info in package.infolist() if not info.is_dir()]
                if len(infos) > 128 or sum(info.file_size for info in infos) > _MAX_PPTX_UNCOMPRESSED:
                    raise ValueError("presentation package exceeds the bounded inspection limits")
                slides = sorted(
                    (info for info in infos if re.fullmatch(r"ppt/slides/slide\d+\.xml", info.filename)),
                    key=lambda info: int(re.search(r"slide(\d+)", info.filename).group(1)),
                )
                for slide in slides:
                    slide_number = int(re.search(r"slide(\d+)", slide.filename).group(1))
                    root = ET.fromstring(package.read(slide))
                    text_index = 0
                    for element in root.iter():
                        if element.tag.endswith("}t") and element.text and element.text.strip():
                            text_index += 1
                            units.append(
                                (f"{slide.filename}#text:{text_index}", element.text.strip(), slide_number)
                            )
        except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
            raise ValueError("presentation could not be inspected safely") from exc
        return units
    if len(raw) > _MAX_TEXT_BYTES:
        raise ValueError("text source exceeds the bounded inspection size")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("text source must be UTF-8") from exc
    return [(f"line:{number}", line.strip(), number) for number, line in enumerate(text.splitlines(), 1) if line.strip()]


def _claim(path: Path, entry: SourceInventoryEntry, locator: str, quote: str, line: int, *, authority: str, status: str) -> GroundedClaim:
    claim_id = "grounded_" + hashlib.sha256(
        f"{entry.sha256}\0{locator}\0{quote}".encode("utf-8")
    ).hexdigest()[:24]
    return GroundedClaim(
        claim_id=claim_id,
        quote=quote,
        source_locator=locator,
        source_sha256=entry.sha256,
        line_start=line,
        line_end=line,
        authority=authority,
        status=status,
    )


def understand_document(
    path: Path | str,
    *,
    source_root: Path | str,
    request: str,
) -> TaskContext:
    selected, root = _safe_path(path, source_root)
    entry = _inventory_entry(selected, root)
    units = _text_units(selected)
    claims = tuple(
        _claim(selected, entry, locator, quote, line, authority="TASK_ONLY", status="observed_text")
        for locator, quote, line in units
    )
    return TaskContext(request=request, sources=(entry,), claims=claims)


def ground_employee_document(path: Path | str, *, source_root: Path | str) -> tuple[GroundedClaim, ...]:
    """Return line-anchored task/project suggestions without writing Wiki state."""
    selected, root = _safe_path(path, source_root)
    entry = _inventory_entry(selected, root)
    return tuple(
        _claim(
            selected,
            entry,
            locator,
            quote,
            line,
            authority="UNREVIEWED_PROJECT_SUGGESTION",
            status="unreviewed",
        )
        for locator, quote, line in _text_units(selected)
        if not quote.startswith("#")
    )


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip("\"'")
    return values


def inspect_asset(path: Path | str, *, source_root: Path | str) -> AssetCandidate:
    selected, root = _safe_path(path, source_root)
    entry = _inventory_entry(selected, root)
    if selected.name.casefold() == "skill.md":
        text = selected.read_text(encoding="utf-8-sig")
        manifest = _frontmatter(text)
        name = manifest.get("name", selected.parent.name)
        return AssetCandidate(
            asset_type="skill",
            name=name,
            source_relative_path=entry.relative_path,
            source_sha256=entry.sha256,
            description=manifest.get("description", ""),
            version=manifest.get("version"),
            candidate_capabilities=(),
        )
    if selected.suffix.casefold() == ".json":
        try:
            manifest = json.loads(selected.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("asset manifest is not valid JSON") from exc
        if not isinstance(manifest, dict):
            raise ValueError("asset manifest must be a JSON object")
        asset_type = str(manifest.get("type", manifest.get("resource_type", "asset"))).casefold()
        if asset_type not in {"agent", "workflow", "tool", "plugin", "repository"}:
            asset_type = "asset"
        tools = manifest.get("tools", [])
        dependencies = manifest.get("dependencies", [])
        entrypoint = manifest.get("entrypoint")
        return AssetCandidate(
            asset_type=asset_type,
            name=str(manifest.get("name", manifest.get("component_id", selected.stem))),
            source_relative_path=entry.relative_path,
            source_sha256=entry.sha256,
            description=str(manifest.get("description", "")),
            version=str(manifest["version"]) if manifest.get("version") is not None else None,
            declared_tools=tuple(str(item) for item in tools if isinstance(item, str)) if isinstance(tools, list) else (),
            dependencies=tuple(str(item) for item in dependencies if isinstance(item, str)) if isinstance(dependencies, list) else (),
            entrypoints=(str(entrypoint),) if isinstance(entrypoint, str) else (),
            candidate_capabilities=tuple(str(item) for item in manifest.get("candidate_capabilities", []) if isinstance(item, str)),
        )
    raise ValueError("asset inspection supports SKILL.md or JSON manifests")


def inspect_repository(path: Path | str, *, source_root: Path | str) -> AssetCandidate:
    selected = Path(path).expanduser().resolve()
    root = Path(source_root).expanduser().resolve()
    if not selected.is_relative_to(root) or not selected.is_dir():
        raise ValueError("repository must be a directory inside the explicit source root")
    inventory = inventory_sources(selected, source_root=root)
    files = {item.relative_path: item for item in inventory}
    dependencies: set[str] = set()
    entrypoints: set[str] = set()
    effects: set[str] = set()
    declared_name = selected.name
    pyproject = selected / "pyproject.toml"
    if pyproject.relative_to(root).as_posix() in files:
        try:
            project = tomllib.loads(pyproject.read_text(encoding="utf-8-sig")).get("project", {})
        except (OSError, tomllib.TOMLDecodeError):
            project = {}
        if isinstance(project, dict):
            declared_name = str(project.get("name", declared_name))
            for dependency in project.get("dependencies", []):
                if isinstance(dependency, str):
                    dependencies.add(re.split(r"[<>=!~\[]", dependency, maxsplit=1)[0])
            scripts = project.get("scripts", {})
            if isinstance(scripts, dict):
                entrypoints.update(str(value) for value in scripts.values() if isinstance(value, str))
    for relative, record in files.items():
        source = root / relative
        if source.name in {"agent.json", "agent_manifest.json", "manifest.json"}:
            try:
                manifest = json.loads(source.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
            if isinstance(manifest, dict):
                item_entrypoint = manifest.get("entrypoint")
                if isinstance(item_entrypoint, str):
                    entrypoints.add(item_entrypoint)
                for dependency in manifest.get("dependencies", []):
                    if isinstance(dependency, str):
                        dependencies.add(dependency)
        if source.name in {"main.py", "app.py", "__main__.py"}:
            entrypoints.add(relative)
        if source.suffix.casefold() == ".py" and record.byte_size <= _MAX_TEXT_BYTES:
            code = source.read_text(encoding="utf-8-sig", errors="replace")
            for name, pattern in (
                ("subprocess", r"\bsubprocess\b"),
                ("network", r"\b(requests|httpx|socket|urllib)\b"),
                ("filesystem_write", r"\b(write_text|write_bytes|open\s*\([^\n]*(?:['\"]w|['\"]a))"),
            ):
                if re.search(pattern, code):
                    effects.add(name)
    return AssetCandidate(
        asset_type="repository",
        name=declared_name,
        source_relative_path=selected.relative_to(root).as_posix(),
        source_sha256=hashlib.sha256(
            "\n".join(f"{key}:{value.sha256}" for key, value in sorted(files.items())).encode("utf-8")
        ).hexdigest(),
        dependencies=tuple(sorted(dependencies)),
        entrypoints=tuple(sorted(entrypoints)),
        detected_effects=tuple(sorted(effects)),
    )


def _actor_payload(actor: ActorContextFixture | None) -> dict[str, Any]:
    if actor is None:
        return {"actor": "unknown"}
    return {
        "actor_id": actor.actor_id,
        "enterprise_id": actor.enterprise_id,
        "project_id": actor.project_id,
        "department_ids": list(actor.department_ids),
        "active_department_id": actor.active_department_id,
        "readable_scope_ids": list(actor.readable_scope_ids),
        "permissions": sorted(actor.permissions),
        "verified": actor.verified,
        "simulation": actor.simulation,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")


def _recorded_run(
    gateway: Any,
    wiki: ProjectWiki,
    *,
    request_kind: str,
    input_value: Mapping[str, Any],
    action: Callable[[RunRecorder, SemanticWiki], dict[str, Any]],
) -> dict[str, Any]:
    run_id = "run_" + uuid.uuid4().hex
    request_id = "req_" + uuid.uuid4().hex
    invocation_id = "inv_" + uuid.uuid4().hex
    recorder = RunRecorder(
        gateway.traces,
        run_id=run_id,
        request_id=request_id,
        invocation_id=invocation_id,
        trace_id=uuid.uuid4().hex,
        correlation_id="understand-reuse-" + uuid.uuid4().hex[:16],
        event_schema_version="1.5",
    )
    recorder.start(
        request_kind=request_kind,
        input_sha256=hashlib.sha256(_canonical(input_value)).hexdigest(),
        actor="synthetic_actor_context",
        component="UnderstandReuseAdapter",
    )
    semantic = SemanticWiki(wiki, recorder=recorder)
    started = __import__("time").perf_counter()
    try:
        result = action(recorder, semantic)
        recorder.event(
            "result.emitted",
            status="success",
            result_sha256=hashlib.sha256(_canonical(result)).hexdigest(),
        )
        recorder.finish(
            "success",
            duration_ms=round((__import__("time").perf_counter() - started) * 1000, 3),
            model_calls=0,
            error_owner=None,
        )
        semantic.finalize_run(run_id, "success")
        return {"run_id": run_id, "status": "success", "result": result, "trace_path": str(gateway.traces.path)}
    except Exception as exc:
        if not recorder.is_finished:
            recorder.event("request.failed", error_type=type(exc).__name__, error_message="local Understand/Reuse operation failed")
            recorder.event("result.emitted", status="failure", error_code="understand_reuse_failed")
            recorder.finish(
                "failure",
                duration_ms=round((__import__("time").perf_counter() - started) * 1000, 3),
                model_calls=0,
                error_owner="understand_reuse",
                error_type=type(exc).__name__,
            )
        semantic.finalize_run(run_id, "failure")
        return {
            "run_id": run_id,
            "status": "failure",
            "error": {"type": type(exc).__name__, "code": "understand_reuse_failed"},
            "trace_path": str(gateway.traces.path),
        }


def propose_knowledge_candidate(
    *,
    source_path: Path | str,
    source_root: Path | str,
    items: Sequence[Mapping[str, Any]],
    wiki: ProjectWiki,
    gateway: Any,
    actor: ActorContextFixture,
) -> dict[str, Any]:
    """Submit a typed proposal through the existing External Candidate V2 owner."""
    selected, _root = _safe_path(source_path, source_root)
    if not actor.simulation or not actor.verified:
        raise PermissionError("this bounded adapter accepts only an explicitly verified synthetic actor fixture")
    if actor.scope_id != wiki.scope_id or actor.scope_id not in actor.readable_scope_ids:
        raise PermissionError("synthetic actor context does not authorize this Wiki scope")
    if "knowledge.propose" not in actor.permissions:
        raise PermissionError("synthetic actor context does not authorize candidate proposal")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or not items:
        raise ValueError("at least one typed candidate item is required")
    source_bytes = selected.read_bytes()
    input_value = {
        "scope_id": wiki.scope_id,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "item_count": len(items),
        "actor_sha256": hashlib.sha256(_canonical(_actor_payload(actor))).hexdigest(),
    }
    captured: dict[str, Any] = {}

    def propose(recorder: RunRecorder, semantic: SemanticWiki) -> dict[str, Any]:
        source = semantic.stage_source(selected, actor_origin="codex_external")
        submission = {
            "schema_version": "catalyst.external_candidate.v2",
            "producer_origin": "codex_external",
            "scope_id": wiki.scope_id,
            "source_id": source["source_id"],
            "source_revision": source["revision"],
            "origin_document_sha256": source["revision"],
            "items": [dict(item) for item in items],
        }
        proposal = semantic.propose_external_submission_v2(submission)
        state = wiki.semantic_state()
        stored = state["candidates"][proposal["candidate_id"]]
        candidate = SemanticCandidate(
            candidate_id=proposal["candidate_id"],
            source_id=proposal["source_id"],
            source_revision=proposal["source_revision"],
            status="proposed",
            active=False,
            accepted=False,
            item_kinds=tuple(sorted({entry["kind"] for entry in stored["entries"]})),
        )
        captured["candidate"] = candidate
        return {
            "candidate_id": candidate.candidate_id,
            "source_id": candidate.source_id,
            "source_revision": candidate.source_revision,
            "status": candidate.status,
            "item_kinds": list(candidate.item_kinds),
        }

    receipt = _recorded_run(
        gateway,
        wiki,
        request_kind="knowledge_propose_external_v2",
        input_value=input_value,
        action=propose,
    )
    if receipt["status"] == "success":
        receipt["candidate"] = captured["candidate"]
    return receipt


def _catalog_items(catalog: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    descriptors = catalog.list() if catalog is not None else ()
    available: dict[str, dict[str, Any]] = {}
    event_rows: list[dict[str, Any]] = []
    for descriptor in descriptors:
        capability_id = getattr(descriptor, "id", None)
        version = getattr(descriptor, "capability_version", None)
        if not isinstance(capability_id, str) or not isinstance(version, str):
            continue
        registration = catalog.get(capability_id, version)
        if registration is None:
            continue
        execution = getattr(descriptor, "execution", {})
        side_effect = execution.get("side_effect", "unknown") if isinstance(execution, Mapping) else "unknown"
        implementation = getattr(registration, "implementation", None)
        record = {
            "capability_id": capability_id,
            "capability_version": version,
            "name": str(getattr(descriptor, "name", capability_id)),
            "description": str(getattr(descriptor, "description", "")),
            "side_effect": str(side_effect),
            "implementation": (
                f"{type(implementation).__module__}.{type(implementation).__qualname__}"
                if implementation is not None
                else "UNKNOWN"
            ),
            "binding_status": "ACTIVE_LOCAL_BINDING",
            "authorization_status": "NOT_EVALUATED",
            "evaluation_status": "NOT_EVALUATED",
            "execution_status": "NOT_EXECUTED",
        }
        available[capability_id] = record
        descriptor_dict = descriptor.to_dict() if callable(getattr(descriptor, "to_dict", None)) else {
            "id": capability_id,
            "capability_version": version,
            "name": record["name"],
            "description": record["description"],
            "execution": {"side_effect": side_effect},
        }
        event_rows.append(
            {
                "id": capability_id,
                "capability_version": version,
                "descriptor_sha256": hashlib.sha256(_canonical(descriptor_dict)).hexdigest(),
                "side_effect": str(side_effect),
            }
        )
    return list(available.values()), sorted(event_rows, key=lambda row: (row["id"], row["capability_version"]))


def compose_agent_candidate(
    *,
    request: str,
    actor: ActorContextFixture | None,
    wiki: ProjectWiki,
    gateway: Any,
    capability_catalog: Any,
) -> dict[str, Any]:
    """Read authorized accepted meanings and active bindings into a plan-only candidate."""
    route = route_request(request)
    actor_hash = hashlib.sha256(_canonical(_actor_payload(actor))).hexdigest()
    input_value = {
        "request_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest(),
        "actor_context_sha256": actor_hash,
        "scope_id": wiki.scope_id,
        "intent": route.intent.value,
    }

    def compose(recorder: RunRecorder, semantic: SemanticWiki) -> dict[str, Any]:
        base = {
            "intent": route.intent.value,
            "target": route.target,
            "decision_status": "needs_review",
            "department_context": {"department_id": None, "label": None, "source": "UNKNOWN"},
            "knowledge": {
                "scope_id": wiki.scope_id,
                "active_version_id": None,
                "knowledge_status": "not_read",
                "freshness_status": "unknown",
                "meaning_ids": [],
                "references": [],
                "used": [],
            },
            "capabilities": [],
            "capability_discovery_status": "not_attempted",
            "unknowns": ["finance_data_source_binding", "metric_calculation_capability", "runtime_activation_authorization"],
            "runtime_execution": "NOT_EXECUTED",
            "deployment": "NOT_DEPLOYED",
            "execution_authorization": "NOT_GRANTED",
            "identity_mode": "SYNTHETIC_FIXTURE_ONLY",
        }
        if actor is None or not actor.simulation or not actor.verified:
            base["decision_status"] = "needs_context"
            return base
        if actor.scope_id != wiki.scope_id or actor.scope_id not in actor.readable_scope_ids:
            base["decision_status"] = "needs_authorization"
            base["unknowns"].append("actor_scope_not_authorized")
            return base
        if "agent.compose" not in actor.permissions or "knowledge.read" not in actor.permissions:
            base["decision_status"] = "needs_authorization"
            base["unknowns"].append("knowledge_read_or_compose_permission_missing")
            return base
        if len(actor.department_ids) > 1 and actor.active_department_id is None:
            base["decision_status"] = "needs_clarification"
            base["unknowns"].append("active_department_ambiguous")
            return base
        department_id = actor.active_department_id
        if not department_id or department_id not in actor.department_ids:
            base["decision_status"] = "needs_context"
            base["unknowns"].append("effective_department_unresolved")
            return base

        department_label = str(actor.department_labels.get(department_id, department_id))
        base["department_context"] = {
            "department_id": department_id,
            "label": department_label,
            "source": "SYNTHETIC_ACTOR_CONTEXT",
        }
        query = f"{request} {department_id} {department_label} 月度经营分析"
        read = semantic.read_knowledge(
            query,
            mode="accepted_enterprise_semantics",
            actor_origin="catalyst_deterministic",
            limit=32,
        )
        fresh_meanings = [
            row for row in read.get("meanings", [])
            if row.get("freshness_status") == "fresh"
            and all(item.get("freshness_status") == "fresh" for item in row.get("evidence", []))
        ]
        references: list[dict[str, Any]] = []
        used: list[dict[str, Any]] = []
        for meaning in fresh_meanings:
            used.append(
                {
                    "meaning_id": meaning["meaning_id"],
                    "kind": meaning.get("kind"),
                    "meaning": meaning.get("meaning"),
                }
            )
            for evidence in meaning.get("evidence", []):
                reference = {
                    "meaning_id": meaning["meaning_id"],
                    "source_id": evidence.get("source_id"),
                    "source_revision": evidence.get("source_revision"),
                    "claim_id": evidence.get("claim_id"),
                    "line_start": evidence.get("line_start"),
                    "line_end": evidence.get("line_end"),
                    "span_sha256": evidence.get("span_sha256"),
                    "freshness_status": evidence.get("freshness_status"),
                }
                references.append(reference)
                claim_id = evidence.get("claim_id")
                source_id = evidence.get("source_id")
                source_revision = evidence.get("source_revision")
                if isinstance(claim_id, str) and isinstance(source_id, str) and isinstance(source_revision, str):
                    recorder.event(
                        "knowledge.claim.used_for_decision",
                        scope_id=wiki.scope_id,
                        claim_id=claim_id,
                        source_id=source_id,
                        source_revision=source_revision,
                        capability_id="compose_report",
                        capability_version="1.0.0",
                        outcome="composition_candidate",
                    )
        can_read_catalog = "capability.read" in actor.permissions
        if can_read_catalog:
            available, event_rows = _catalog_items(capability_catalog)
            selected = [
                row for row in available
                if row["capability_id"] in {"wiki_search", "compose_report"}
                and row["side_effect"] == "none"
            ]
            base["capability_discovery_status"] = "discovered"
            catalog_scope = "local_registered_product_bindings"
            catalog_authorization = "not_evaluated_until_invocation"
        else:
            available, event_rows, selected = [], [], []
            base["capability_discovery_status"] = "not_authorized"
            catalog_scope = "not_read_permission_denied"
            catalog_authorization = "denied_missing_capability_read"
            base["unknowns"].append("capability_catalog_permission_missing")
        selected.sort(key=lambda row: row["capability_id"])
        selected_ids = {row["capability_id"] for row in selected}
        selected_events = [row for row in event_rows if row["id"] in selected_ids]
        catalog_payload = {
            "discovery_status": base["capability_discovery_status"],
            "capabilities": selected_events,
            "invocation_routes": [
                {
                    "capability_id": row["id"],
                    "capability_version": row["capability_version"],
                    "command": "invoke",
                }
                for row in selected_events
            ],
        }
        recorder.event(
            "capabilities.discovered",
            capability_count=len(selected_events),
            catalog_scope=catalog_scope,
            authorization=catalog_authorization,
            catalog_sha256=hashlib.sha256(_canonical(catalog_payload)).hexdigest(),
            capabilities=selected_events,
            invocation_routes=catalog_payload["invocation_routes"],
        )
        read_is_current = read.get("knowledge_status") == "current" and read.get("freshness_status") == "fresh"
        base["knowledge"] = {
            "scope_id": read.get("scope_id"),
            "active_version_id": read.get("active_version_id"),
            "knowledge_status": read.get("knowledge_status"),
            "freshness_status": read.get("freshness_status"),
            "meaning_ids": [row["meaning_id"] for row in fresh_meanings] if read_is_current else [],
            "references": references if read_is_current else [],
            "used": used if read_is_current else [],
            "stale_meaning_count": sum(row.get("freshness_status") != "fresh" for row in read.get("meanings", [])),
        }
        base["capabilities"] = selected
        if not read_is_current or not fresh_meanings:
            base["unknowns"].append("no_current_accepted_department_knowledge")
        if can_read_catalog and "compose_report" not in selected_ids:
            base["unknowns"].append("report_composition_capability_unavailable")
        if can_read_catalog and "wiki_search" not in selected_ids:
            base["unknowns"].append("knowledge_retrieval_capability_unavailable")
        if read_is_current and fresh_meanings and {"wiki_search", "compose_report"}.issubset(selected_ids):
            base["reuse_status"] = "KNOWLEDGE_AND_CAPABILITY_SELECTED_IN_PLAN"
        else:
            base["reuse_status"] = "PARTIAL_OR_UNKNOWN"
        return base

    return _recorded_run(
        gateway,
        wiki,
        request_kind="understand_reuse_agent_composition",
        input_value=input_value,
        action=compose,
    )

