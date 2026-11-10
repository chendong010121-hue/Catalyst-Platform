"""Two levels of type: an upper kind the code fixes, and a concept a scope declares.

A name alone is not a model: an entity that cannot say what kind of thing it is says only
that something was mentioned. Type has two levels, and only the lower one belongs to one
customer.

**The upper level** is :data:`META_KINDS`: the ways a thing in an organization can exist -
someone or something that acts, an organization or a unit of one, a role, a duty, a step of
work, an artifact, a rule (with the exceptions it carves out) and a measure. A hospital
ward, a bank product and a machine shop's工序 all land in one of them, and none of the eight
is a customer's word. Each kind names the published upper-ontology term it stands for
(``grounding``) so a reviewer can check the frame instead of trusting it; that is an
alignment label, not an import and not a conformance claim.

**The lower level** is a :class:`ConceptSet`: ``concept -> parent kind -> criteria ->
aliases``, declared per scope, stored in that scope's Wiki, versioned and deprecable, put
into the extraction prompt, and checked against every entity that names a type. The eleven
concepts of ``ONTOLOGY_MODELING_STANDARD_V0.2`` section 4 are the :data:`STARTER_PACK`: what a
new scope starts from, not what the code knows. A scope that needs ``Ward``, ``Product`` or
``Account`` declares it - no commit, no release, and no effect on the next card's types.

What stays fixed is the rule, not the list: a type outside the scope's concept set is still
refused rather than invented, and the refusal is counted (``concept_unmapped``) with the
entity kept, so a missing concept becomes a decision the Owner can make instead of a row
that quietly disappeared.
"""

from __future__ import annotations

import re

from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Mapping, Sequence

_CONCEPT_ID = re.compile(r"[A-Za-z][A-Za-z0-9]{0,63}")


class ConceptError(ValueError):
    """A concept or a concept set that cannot be stored, read or resolved."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class MetaKind:
    """One way a thing in an organization can exist, whatever the industry calls it."""

    kind_id: str
    name: str
    criteria: str
    # The published term this kind stands for, for a reviewer to check the frame against.
    # An alignment label, never an import: nothing here is validated against that standard.
    grounding: str


META_KINDS: dict[str, MetaKind] = {
    "Actor": MetaKind(
        "Actor", "主体",
        "能成为一句话主语的实体：人、机构、本组织之外的单位",
        "ArchiMate Business Actor; FOAF Agent",
    ),
    "Organization": MetaKind(
        "Organization", "组织",
        "有边界的组织及其内部单位：谁决策、谁经营、谁干活",
        "ArchiMate Business Actor（有内部边界的）",
    ),
    "Role": MetaKind(
        "Role", "角色",
        "一个人承担的岗位身份：人换了角色还在",
        "ArchiMate Business Role",
    ),
    "Duty": MetaKind(
        "Duty", "职责",
        "被交办要做的事：职能、义务",
        "ArchiMate Business Function",
    ),
    "Activity": MetaKind(
        "Activity", "活动",
        "工作过程中的一个步骤或环节",
        "ArchiMate Business Process",
    ),
    "Artifact": MetaKind(
        "Artifact", "产出物",
        "产出的或使用的物：单据、表单、报告、文件",
        "ArchiMate Business Object",
    ),
    "Rule": MetaKind(
        "Rule", "规则",
        "约束行为的规定，以及规定自己留出的例外",
        "ArchiMate Constraint",
    ),
    "Measure": MetaKind(
        "Measure", "度量",
        "可度量或可定义的量：指标、口径",
        "ArchiMate Meaning（近似：ArchiMate 无度量层）",
    ),
}


ATTRIBUTE_VALUE_TYPES: tuple[str, ...] = ("text", "number", "date", "boolean", "reference")
CARDINALITIES: tuple[str, ...] = ("one", "many")
CONSTRAINT_SEVERITIES: tuple[str, ...] = ("must", "must_not")

# A type says five kinds of thing about its instances, and each one is a declaration, not an
# instance: a Ward that declares ``bed_count(number)`` and ``yields→Deliverable`` has said
# something checkable about every ward, before any sentence is read. Nothing here is inferred
# from text; a declaration is the scope's own statement of what its type means.
MAX_DECLARATIONS = 32


def _declaration_line(value: object, *, concept_id: str, field: str, limit: int = 200,
                      required: bool = False) -> str:
    if value is None and not required:
        return ""
    if (
        not isinstance(value, str)
        or value != value.strip()
        or len(value) > limit
        or "\n" in value
        or "\r" in value
        or (required and not value)
    ):
        raise ConceptError(
            "concept_declaration_invalid",
            f"{concept_id}: {field} is one non-empty line of at most {limit} characters",
        )
    return value


@dataclass(frozen=True)
class Attribute:
    """A property this type's instances carry: a name, and what kind of value it holds."""

    name: str
    value_type: str = "text"
    required: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value_type": self.value_type,
            "required": self.required,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, row: object, *, concept_id: str) -> "Attribute":
        if not isinstance(row, Mapping):
            raise ConceptError("concept_declaration_invalid", f"{concept_id}: an attribute is a JSON object")
        name = _declaration_line(row.get("name"), concept_id=concept_id, field="attribute name",
                                 limit=64, required=True)
        value_type = row.get("value_type", "text")
        if value_type not in ATTRIBUTE_VALUE_TYPES:
            raise ConceptError(
                "concept_declaration_invalid",
                f"{concept_id}: attribute {name} value_type is one of {', '.join(ATTRIBUTE_VALUE_TYPES)}",
            )
        required = row.get("required", False)
        if not isinstance(required, bool):
            raise ConceptError("concept_declaration_invalid",
                               f"{concept_id}: attribute {name} required is a boolean")
        return cls(
            name=name,
            value_type=value_type,
            required=required,
            description=_declaration_line(row.get("description"), concept_id=concept_id,
                                          field=f"attribute {name} description"),
        )


@dataclass(frozen=True)
class Relation:
    """A way this type reaches another: the predicate, the type it reaches, and how many."""

    predicate: str
    target: str
    cardinality: str = "many"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "target": self.target,
            "cardinality": self.cardinality,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, row: object, *, concept_id: str) -> "Relation":
        if not isinstance(row, Mapping):
            raise ConceptError("concept_declaration_invalid", f"{concept_id}: a relation is a JSON object")
        predicate = _declaration_line(row.get("predicate"), concept_id=concept_id,
                                      field="relation predicate", limit=64, required=True)
        target = _declaration_line(row.get("target"), concept_id=concept_id,
                                   field=f"relation {predicate} target", limit=64, required=True)
        cardinality = row.get("cardinality", "many")
        if cardinality not in CARDINALITIES:
            raise ConceptError(
                "concept_declaration_invalid",
                f"{concept_id}: relation {predicate} cardinality is one of {', '.join(CARDINALITIES)}",
            )
        return cls(
            predicate=predicate,
            target=target,
            cardinality=cardinality,
            description=_declaration_line(row.get("description"), concept_id=concept_id,
                                          field=f"relation {predicate} description"),
        )


@dataclass(frozen=True)
class Constraint:
    """A statement this type's instances must satisfy, and which way it binds."""

    statement: str
    severity: str = "must"

    def to_dict(self) -> dict[str, Any]:
        return {"statement": self.statement, "severity": self.severity}

    @classmethod
    def from_dict(cls, row: object, *, concept_id: str) -> "Constraint":
        if not isinstance(row, Mapping):
            raise ConceptError("concept_declaration_invalid", f"{concept_id}: a constraint is a JSON object")
        statement = _declaration_line(row.get("statement"), concept_id=concept_id,
                                      field="constraint statement", limit=400, required=True)
        severity = row.get("severity", "must")
        if severity not in CONSTRAINT_SEVERITIES:
            raise ConceptError(
                "concept_declaration_invalid",
                f"{concept_id}: constraint severity is one of {', '.join(CONSTRAINT_SEVERITIES)}",
            )
        return cls(statement=statement, severity=severity)


@dataclass(frozen=True)
class Action:
    """Something an instance of this type does, as the scope names it."""

    name: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, row: object, *, concept_id: str) -> "Action":
        if not isinstance(row, Mapping):
            raise ConceptError("concept_declaration_invalid", f"{concept_id}: an action is a JSON object")
        name = _declaration_line(row.get("name"), concept_id=concept_id, field="action name",
                                 limit=64, required=True)
        return cls(
            name=name,
            description=_declaration_line(row.get("description"), concept_id=concept_id,
                                          field=f"action {name} description"),
        )


@dataclass(frozen=True)
class Metric:
    """A quantity this type is measured by: its name, its unit and how it is worked out."""

    name: str
    unit: str = ""
    definition: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "unit": self.unit, "definition": self.definition}

    @classmethod
    def from_dict(cls, row: object, *, concept_id: str) -> "Metric":
        if not isinstance(row, Mapping):
            raise ConceptError("concept_declaration_invalid", f"{concept_id}: a metric is a JSON object")
        name = _declaration_line(row.get("name"), concept_id=concept_id, field="metric name",
                                 limit=64, required=True)
        return cls(
            name=name,
            unit=_declaration_line(row.get("unit"), concept_id=concept_id,
                                   field=f"metric {name} unit", limit=32),
            definition=_declaration_line(row.get("definition"), concept_id=concept_id,
                                         field=f"metric {name} definition", limit=400),
        )


DECLARATION_FIELDS: tuple[str, ...] = ("attributes", "relations", "constraints", "actions", "metrics")
_DECLARATION_ROW: dict[str, Any] = {
    "attributes": Attribute, "relations": Relation, "constraints": Constraint,
    "actions": Action, "metrics": Metric,
}
_DECLARATION_KEY: dict[str, Callable[[Any], str]] = {
    "attributes": lambda row: row.name, "relations": lambda row: f"{row.predicate}\u2192{row.target}",
    "constraints": lambda row: row.statement, "actions": lambda row: row.name,
    "metrics": lambda row: row.name,
}


def _declaration_rows(rows: object, *, concept_id: str, field: str) -> tuple[Any, ...]:
    if rows is None:
        return ()
    if isinstance(rows, (str, bytes)) or not isinstance(rows, (list, tuple)):
        raise ConceptError("concept_declaration_invalid", f"{concept_id}: {field} is an array of declarations")
    if len(rows) > MAX_DECLARATIONS:
        raise ConceptError(
            "concept_declaration_invalid",
            f"{concept_id}: {field} holds at most {MAX_DECLARATIONS} declarations",
        )
    parser = _DECLARATION_ROW[field]
    return tuple(parser.from_dict(row, concept_id=concept_id) for row in rows)


def declaration_clauses(concept: "Concept") -> list[str]:
    """One readable clause per declared field, for the prompt and for a page."""
    clauses: list[str] = []
    if concept.attributes:
        clauses.append("属性 " + "、".join(
            f"{row.name}({row.value_type}{'，必填' if row.required else ''})" for row in concept.attributes))
    if concept.relations:
        clauses.append("关系 " + "、".join(
            f"{row.predicate}→{row.target}({'多' if row.cardinality == 'many' else '一'})"
            for row in concept.relations))
    if concept.constraints:
        clauses.append("约束 " + "、".join(f"[{row.severity}] {row.statement}" for row in concept.constraints))
    if concept.actions:
        clauses.append("动作 " + "、".join(row.name for row in concept.actions))
    if concept.metrics:
        clauses.append("指标 " + "、".join(
            f"{row.name}({row.unit})" if row.unit else row.name for row in concept.metrics))
    return clauses


def declared_counts(concepts: Sequence["Concept"]) -> dict[str, int]:
    """How much of an ontology is declared rather than instantiated."""
    return {
        "concepts": len(concepts),
        **{field: sum(len(getattr(concept, field)) for concept in concepts) for field in DECLARATION_FIELDS},
    }


@dataclass(frozen=True)
class Concept:
    """One type a scope actually uses: what it is, which kind it is, and what belongs to it.

    ``criteria`` is the rule a producer and a reviewer both read: "部门、处、科、室、中心：
    组织自己开展工作的一个单位，绝不是组织本身" tells an extractor where a name goes and a
    reviewer how to refuse it. ``aliases`` are other spellings the same thing is written
    with (``dept``, ``板块``); a spelling resolves to exactly one concept in its set.
    """

    concept_id: str
    name: str
    meta_kind: str
    criteria: str
    aliases: tuple[str, ...] = ()
    # Where the concept came from: the starter pack, or a scope that declared it.
    origin: str = "starter_pack"
    attributes: tuple[Attribute, ...] = ()
    relations: tuple[Relation, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    actions: tuple[Action, ...] = ()
    metrics: tuple[Metric, ...] = ()

    def __post_init__(self) -> None:
        # A type that declares one property twice would leave a reviewer two answers.
        for field in DECLARATION_FIELDS:
            rows = getattr(self, field)
            keys = [_DECLARATION_KEY[field](row) for row in rows]
            if len(set(keys)) != len(keys):
                raise ConceptError(
                    "concept_declaration_duplicated",
                    f"{self.concept_id}: two {field} declarations repeat one {'name' if field != 'relations' else 'predicate and target'}",
                )

    def to_dict(self) -> dict[str, Any]:
        declared = {
            field: [row.to_dict() for row in getattr(self, field)]
            for field in DECLARATION_FIELDS
            if getattr(self, field)
        }
        return {
            "concept_id": self.concept_id,
            "name": self.name,
            "meta_kind": self.meta_kind,
            "criteria": self.criteria,
            "aliases": list(self.aliases),
            "origin": self.origin,
            **declared,
        }

    @classmethod
    def from_dict(cls, row: object, *, origin: str | None = None) -> "Concept":
        if not isinstance(row, Mapping):
            raise ConceptError("concept_not_an_object", "a concept must be a JSON object")
        concept_id = row.get("concept_id")
        if not isinstance(concept_id, str) or not _CONCEPT_ID.fullmatch(concept_id):
            raise ConceptError(
                "concept_id_invalid",
                "a concept_id is 1-64 ascii letters and digits, starting with a letter",
            )
        name = row.get("name")
        if not isinstance(name, str) or not name.strip() or name != name.strip() or len(name) > 64:
            raise ConceptError("concept_name_required", f"{concept_id}: name is one non-empty line")
        meta_kind = row.get("meta_kind")
        if not isinstance(meta_kind, str) or meta_kind not in META_KINDS:
            raise ConceptError(
                "concept_meta_kind_unknown",
                f"{concept_id}: meta_kind must be one of {', '.join(META_KINDS)}",
            )
        criteria = row.get("criteria")
        if not isinstance(criteria, str) or not criteria.strip() or criteria != criteria.strip() or len(criteria) > 400:
            raise ConceptError(
                "concept_criteria_required",
                f"{concept_id}: criteria is one non-empty line of at most 400 characters",
            )
        raw_aliases = row.get("aliases", ())
        if isinstance(raw_aliases, str) or not isinstance(raw_aliases, (list, tuple)):
            raise ConceptError("concept_aliases_invalid", f"{concept_id}: aliases is an array of spellings")
        aliases: list[str] = []
        for alias in raw_aliases:
            if (not isinstance(alias, str) or not alias.strip() or alias != alias.strip()
                    or len(alias) > 64 or "\n" in alias or "\r" in alias):
                raise ConceptError("concept_aliases_invalid", f"{concept_id}: one alias is not a single spelling")
            if alias.casefold() not in {item.casefold() for item in aliases}:
                aliases.append(alias)
        declared = row.get("origin") if origin is None else origin
        return cls(
            concept_id=concept_id, name=name, meta_kind=meta_kind, criteria=criteria,
            aliases=tuple(aliases), origin=str(declared or "starter_pack"),
            **{field: _declaration_rows(row.get(field), concept_id=concept_id, field=field)
               for field in DECLARATION_FIELDS},
        )


@dataclass(frozen=True)
class ConceptSet:
    """The types one scope uses, resolved by concept id, name or alias.

    A set is data: it is stored in the scope's Wiki, versioned, and injected into the
    extraction prompt. The class refuses to hold two concepts that answer to the same
    spelling, because a producer's ``板块`` must mean one thing.
    """

    concepts: tuple[Concept, ...]
    version_id: str = "starter-1"
    origin: str = "starter_pack"
    # Derived at construction (``__post_init__``), never a field: two sets holding the same
    # concepts are the same set whatever order their spellings were built in.
    _spellings: ClassVar[dict[str, Concept]]

    def __post_init__(self) -> None:
        if not self.concepts:
            raise ConceptError("concept_set_empty", "a concept set needs at least one concept")
        spellings: dict[str, str] = {}
        seen_ids: set[str] = set()
        for concept in self.concepts:
            if not isinstance(concept, Concept):
                raise ConceptError("concept_set_invalid", "a concept set holds only Concept rows")
            if concept.concept_id in seen_ids:
                # A concept is one thing however many rows claim it; two rows with one id
                # would leave the criteria and the parent kind of a type undecidable.
                raise ConceptError("concept_id_duplicated", f"{concept.concept_id} appears twice in one set")
            seen_ids.add(concept.concept_id)
            for spelling in (concept.concept_id, concept.name, *concept.aliases):
                key = spelling.casefold()
                owner = spellings.get(key)
                if owner is not None and owner != concept.concept_id:
                    raise ConceptError(
                        "concept_spelling_shared",
                        f"{spelling!r} is claimed by both {owner} and {concept.concept_id}",
                    )
                spellings[key] = concept.concept_id
        # The spelling index is derived, not a field: two sets that hold the same concepts
        # are the same set, whatever order the spellings were built in.
        object.__setattr__(self, "_spellings", {key: self.by_id(owner) for key, owner in spellings.items()})
        for concept in self.concepts:
            if concept.meta_kind not in META_KINDS:
                raise ConceptError(
                    "concept_meta_kind_unknown",
                    f"{concept.concept_id}: meta_kind must be one of {', '.join(META_KINDS)}",
                )

    def by_id(self, concept_id: object) -> Concept | None:
        if not isinstance(concept_id, str):
            return None
        for concept in self.concepts:
            if concept.concept_id == concept_id:
                return concept
        return None

    def resolve(self, value: object) -> Concept | None:
        """The concept this spelling names, or None when the set does not hold it."""
        if not isinstance(value, str):
            return None
        return self._spellings.get(value.strip().casefold())

    def ids(self) -> tuple[str, ...]:
        return tuple(concept.concept_id for concept in self.concepts)

    def prompt_rules(self) -> str:
        """The type segment of the extraction prompt, written from this set alone."""
        count = len(self.concepts)
        listing = "; ".join(
            f"{concept.concept_id}（{concept.name}，{concept.meta_kind}）: {concept.criteria}"
            for concept in self.concepts
        )
        declared = ("every concept name is declared by this scope, never invented"
                    if self.origin != "starter_pack" else "")
        structure = "; ".join(
            f"{concept.concept_id}: " + "；".join(clauses)
            for concept in self.concepts
            if (clauses := declaration_clauses(concept))
        )
        return (
            "Every entity states business_type - exactly one of " + ", ".join(self.ids()) + " - "
            "unless none of them classifies it. "
            "What each one covers - " + listing + ". "
            f"An entity the source supports and none of the {count} classifies keeps its row, "
            "leaves business_type out, and names in uncertainty the kind the source would need; "
            "it is not a claim, and the nearest type is not assigned in its place. "
            f"A type outside the {count} is refused. "
            + declared + ("已声明的结构 - " + structure + "。" if structure else "")
        ).strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "origin": self.origin,
            "concepts": [concept.to_dict() for concept in self.concepts],
        }

    @classmethod
    def from_dict(cls, payload: object, *, origin: str | None = None) -> "ConceptSet":
        if not isinstance(payload, Mapping):
            raise ConceptError("concept_set_invalid", "a concept set is a JSON object")
        rows = payload.get("concepts")
        if isinstance(rows, str) or not isinstance(rows, Sequence) or not rows:
            raise ConceptError("concept_set_empty", "a concept set needs a non-empty concepts array")
        declared_origin = payload.get("origin") if origin is None else origin
        concepts = []
        for row in rows:
            row_origin = row.get("origin") if isinstance(row, Mapping) else None
            concepts.append(Concept.from_dict(row, origin=row_origin or declared_origin))
        version_id = payload.get("version_id")
        return cls(
            concepts=tuple(concepts),
            version_id=version_id if isinstance(version_id, str) and version_id else "declared-1",
            origin=str(declared_origin or "declared"),
        )


STARTER_CONCEPTS: tuple[Concept, ...] = (
    Concept("Department", "部门", "Organization", "部门、处、科、室、中心：组织自己开展工作的一个单位，绝不是组织本身"),
    Concept("Position", "岗位", "Role", "岗位、职位、角色"),
    Concept("Responsibility", "职责", "Duty", "职责、职能：被交办要完成的事"),
    Concept("ProcessStep", "流程步骤", "Activity", "流程步骤、环节"),
    Concept("Deliverable", "交付物", "Artifact", "单据、表单、报告、文件"),
    Concept("Rule", "制度", "Rule", "制度、办法、规定、规则"),
    Concept("Exception", "例外", "Rule", "例外、特批情形：规则留出的那个口子"),
    Concept("Metric", "指标", "Measure", "指标、口径"),
    Concept("GovernanceBody", "治理机构", "Organization",
            "治理与决策机构：党委会、董事会、监事会、经理层；它做决策，不做日常工作"),
    Concept("BusinessUnit", "经营单位", "Organization",
            "子公司、分公司、参控股单位、对外投资单位、事业部；独立经营或独立法人"),
    Concept("ExternalParty", "外部方", "Actor",
            "本组织之外的单位或个人：政府、客户、合作方；它不在本组织自己的结构里"),
)

STARTER_PACK = ConceptSet(STARTER_CONCEPTS, "starter-1", "starter_pack")

def concept_set_identity(concept_set: ConceptSet) -> dict[str, Any]:
    """The version, the origin, and one digest over the concepts themselves.

    A card read against eleven types and a card read against thirteen are different
    readings; the version alone does not say which, because a scope's version is its own
    id. The digest is over the rows in concept-id order, so two sets holding the same
    concepts in a different spelling order are the same set.
    """
    import hashlib
    import json

    rows = sorted((concept.to_dict() for concept in concept_set.concepts),
                  key=lambda row: row["concept_id"])
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"version": concept_set.version_id, "origin": concept_set.origin,
            "count": len(rows), "digest": hashlib.sha256(payload.encode("utf-8")).hexdigest()}

# The eleven of the standard, still readable as one mapping so a document, a test or a
# producer that only knows the starter pack keeps working: what each one covers.
BUSINESS_TYPES: dict[str, str] = {concept.concept_id: concept.criteria for concept in STARTER_CONCEPTS}


def resolve_concept(value: object, concepts: ConceptSet | None = None) -> Concept | None:
    """The concept a producer's spelling means in this set, in any capitalisation."""
    return (concepts or STARTER_PACK).resolve(value)


def canonical_business_type(value: object, concepts: ConceptSet | None = None) -> str | None:
    """The canonical spelling of one concept of the set, or None when it is not one.

    A producer that writes `position` meant Position; losing the entity over a capital
    letter would cost data for a spelling, so the store rewrites it to the one spelling
    the standard and the score both use.
    """
    concept = resolve_concept(value, concepts)
    return concept.concept_id if concept is not None else None


def is_business_type(value: object, concepts: ConceptSet | None = None) -> bool:
    """True only for one concept of the set, in any capitalisation the producer used."""
    return resolve_concept(value, concepts) is not None
