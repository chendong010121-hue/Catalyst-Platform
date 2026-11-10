"""One business object, read the same way from a candidate entry or an accepted meaning.

The two shapes differ only in what the store keeps around them, never in what a reader needs:

* an accepted meaning carries a list of ``evidence`` spans, the version it was accepted into
  and the candidate that produced it;
* a candidate entry carries one flattened span (``source_id`` / ``line_start`` /
  ``line_end`` / ``span_sha256``) and belongs to a candidate the reader has not accepted.

So both adapters return the same ``ObjectView``, and the view keeps each row's origin
(``accepted_meaning`` / ``candidate_entry``) plus the identifiers it came with.

Nothing here decides whether an object is true. ``qualification``, ``qualification_basis``
and ``verification`` are copied as the row saved them; a caller that recomputed them would
be reporting its own reading as the store's confirmation. In particular
``duty_carried_by_its_sentence`` says *the sentence it cites says this*, not that the
organisation does it, and no label here may be worded as "business confirmed".

A condition or exception is attached through the ``applies_to`` it was saved with. A row
whose ``applies_to`` is empty stays unattached - it is reported, not hung on the nearest
object that looks related.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

OBJECT_KINDS: tuple[str, ...] = ("duty", "event", "condition")

KIND_LABEL = {"duty": "职责", "event": "事件", "condition": "条件", "entity": "实体",
              "relation": "关系", "alias": "别名", "exception": "例外", "claim": "主张",
              "negative_claim": "否定主张", "unknown": "未知"}

QUALIFICATION_LABEL = {
    "pending": "待审（pending）",
    "inferred": "推断读出（inferred）",
    "stated": "原句陈述（stated）",
    "confirmed": "已确认（confirmed）",
}

VERIFICATION_LABEL = {
    "unconfirmed": "未经校验（unconfirmed）",
    "confirmed": "引文自身支持（confirmed）",
}

# The basis codes are the run record's own; the gloss says what was missing, never that the
# object was approved. Every code below is one the reading gate can return.
BASIS_LABEL = {
    "holder_not_in_evidence": "引用它的那段话里没有出现持有者",
    "duty_text_not_in_evidence": "原句里没有这条工作",
    "duty_attached_to_another_unit": "这条工作有一半挂在另一个单位名下",
    "holder_and_duty_not_in_one_sentence": "持有者与工作分处两个片段，不在同一句",
    "duty_not_attached_to_holder": "原句没有把这条工作挂到持有者身上",
    "polarity_not_carried": "肯定与否定与原句不一致",
    "condition_not_carried": "原句带条件，这一条没有带上",
    "restriction_not_carried": "原句还有这一条没有带的限定语",
    "content_read_by_inference": "这条内容是推断读出来的",
    "content_not_established": "原句没有建立这条内容",
    "roles_or_endpoints_unsettled": "角色或端点没有定下来",
    "duty_carried_by_its_sentence": "引用它的那一句话自己就说完了这条工作（不是业务已确认）",
}

ROLE_LABEL = {"holder": "持有者", "from": "起点", "to": "终点", "applies_to": "适用对象",
              "subject": "主体", "object": "客体"}

EVIDENCE_CLASS_LABEL = {
    "inferred": "派生记录（inferred）",
    "observed_from_source": "原文陈述（observed_from_source）",
    "unresolved": "未解析（unresolved）",
}


@dataclass(frozen=True)
class Citation:
    """One citation exactly as the row recorded it, with what that record can and cannot show."""

    source_id: str
    title: str
    locator: str
    line_start: int | None
    line_end: int | None
    span_sha256: str
    evidence_class: str
    revision: str
    # Whether the source is derived is a property of the source. A span that does not say is
    # None, which is not the same as False: silence must not read as "this is the original".
    derived: bool | None

    @property
    def origin_label(self) -> str:
        if self.derived is True:
            return "派生来源"
        if self.derived is False:
            return "原件"
        return "来源属性未记录"

    def line(self) -> str:
        span = self.locator
        if self.line_start and self.line_end and self.line_end != self.line_start:
            span = f"line:{self.line_start}-{self.line_end}"
        elif self.line_start:
            span = f"line:{self.line_start}"
        revision = f"，revision {self.revision[:12]}…" if self.revision else ""
        return (f"`{self.title}` @ `{span}`（{self.origin_label}；"
                f"{EVIDENCE_CLASS_LABEL.get(self.evidence_class, self.evidence_class)}"
                f"{revision}；本轮只核对了记录，没有回读原件）")


@dataclass(frozen=True)
class Role:
    """A place a key was saved in, and whether this version can name the object behind it.

    ``via`` is set when the key was resolved through another object - a condition saved
    against a duty reaches the duty's holder, and the page says through which duty.
    """

    name: str
    key: str
    title: str | None = None
    page: str | None = None
    via: str | None = None

    @property
    def label(self) -> str:
        return ROLE_LABEL.get(self.name, self.name)

    @property
    def resolved(self) -> bool:
        return bool(self.title)


@dataclass(frozen=True)
class ObjectView:
    """The display structure both adapters hand to a card or a page section."""

    kind: str
    title: str
    statement: str
    roles: tuple[Role, ...]
    qualification: str
    basis: str
    verification: str
    scope_state: str | None
    citations: tuple[Citation, ...]
    identity: Mapping[str, Any]
    origin: str
    unattached: bool
    # What the row itself recorded as still open: an absence it observed (`observed_absence`)
    # or an uncertainty it wrote down. None means the row recorded neither - the page then
    # says so instead of inventing a question.
    unsettled: str | None = None
    unsettled_source: str | None = None

    @property
    def kind_label(self) -> str:
        return KIND_LABEL.get(self.kind, self.kind)

    @property
    def qualification_label(self) -> str:
        return QUALIFICATION_LABEL.get(self.qualification, self.qualification or "未记录")

    @property
    def verification_label(self) -> str:
        return VERIFICATION_LABEL.get(self.verification, self.verification or "未记录")

    @property
    def basis_label(self) -> str:
        return BASIS_LABEL.get(self.basis, self.basis or "未记录")

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(role.key for role in self.roles if role.key)

    @property
    def attached(self) -> bool:
        return any(role.resolved for role in self.roles)

    @property
    def unresolved_roles(self) -> tuple[Role, ...]:
        return tuple(role for role in self.roles if role.key and not role.resolved)

    def to_dict(self) -> dict[str, Any]:
        """What a card or a panel reads: the five answers, and the identifiers as advanced info."""
        return {
            "kind": self.kind,
            "kind_label": self.kind_label,
            "title": self.title,
            "statement": self.statement,
            "roles": [{"name": role.name, "label": role.label, "key": role.key,
                       "title": role.title, "page": role.page, "resolved": role.resolved,
                       "via": role.via}
                      for role in self.roles],
            "qualification": self.qualification,
            "qualification_label": self.qualification_label,
            "basis": self.basis,
            "basis_label": self.basis_label,
            "verification": self.verification,
            "verification_label": self.verification_label,
            "scope_state": self.scope_state,
            "unsettled": self.unsettled,
            "unsettled_source": self.unsettled_source,
            "unattached_reason": unattached_reason(self) if self.unattached else None,
            "citations": [_citation_dict(citation) for citation in self.citations],
            "origin": self.origin,
            "unattached": self.unattached,
            # Shown under "高级信息" only, never in place of the answers above.
            "advanced": {"identity": dict(self.identity),
                         "citations": [_citation_dict(citation) for citation in self.citations]},
        }


def _citation_dict(citation: Citation) -> dict[str, Any]:
    return {
        "source_id": citation.source_id,
        "title": citation.title,
        "line": citation.line(),
        "locator": citation.locator,
        "line_start": citation.line_start,
        "line_end": citation.line_end,
        "span_sha256": citation.span_sha256,
        "revision": citation.revision,
        "evidence_class": citation.evidence_class,
        "derived": citation.derived,
    }


def _citation_from_span(span: Mapping[str, Any], titles: Mapping[str, str]) -> Citation:
    source_id = str(span.get("source_id") or "")
    evidence_class = str(span.get("evidence_class") or "unresolved")
    return Citation(
        source_id=source_id,
        title=str(titles.get(source_id) or source_id or "来源未记录"),
        locator=str(span.get("locator") or ""),
        line_start=span.get("line_start") if isinstance(span.get("line_start"), int) else None,
        line_end=span.get("line_end") if isinstance(span.get("line_end"), int) else None,
        span_sha256=str(span.get("span_sha256") or ""),
        evidence_class=evidence_class,
        revision=str(span.get("source_revision") or ""),
        derived=span.get("derived") if isinstance(span.get("derived"), bool) else None,
    )


def role_keys(row: Mapping[str, Any]) -> tuple[str, ...]:
    """The keys a row was saved with, in the role each one stands in. No lookup, no guessing."""
    if row.get("kind") == "event":
        sides = (*tuple(row.get("from") or ()), *tuple(row.get("to") or ()))
        return tuple(key for key in sides if isinstance(key, str) and key)
    if row.get("kind") == "condition":
        return tuple(key for key in (row.get("applies_to") or []) if isinstance(key, str) and key)
    if row.get("kind") == "relation":
        sides = (row.get("subject"), row.get("object"))
        return tuple(key for key in sides if isinstance(key, str) and key)
    holder = row.get("holder")
    return (holder,) if isinstance(holder, str) and holder else ()


def _roles(row: Mapping[str, Any], entities: Mapping[str, tuple[str, str]]) -> tuple[Role, ...]:
    def role(name: str, key: Any) -> Role | None:
        if not isinstance(key, str) or not key:
            return None
        title, page = entities.get(key, (None, None))
        return Role(name=name, key=key, title=title, page=page)

    if row.get("kind") == "event":
        rows = [role("from", key) for key in (row.get("from") or [])]
        rows += [role("to", key) for key in (row.get("to") or [])]
    elif row.get("kind") == "condition":
        rows = [role("applies_to", key) for key in (row.get("applies_to") or [])]
    elif row.get("kind") == "relation":
        rows = [role("subject", row.get("subject")), role("object", row.get("object"))]
    else:
        rows = [role("holder", row.get("holder"))]
    return tuple(item for item in rows if item is not None)


def _build(row: Mapping[str, Any], *, origin: str, entities: Mapping[str, tuple[str, str]],
           titles: Mapping[str, str], identity: Mapping[str, Any],
           spans: Sequence[Mapping[str, Any]]) -> ObjectView:
    kind = str(row.get("kind"))
    statement = str(row.get("meaning") or "").strip()
    key = str(row.get("key") or row.get("meaning_id") or "")
    roles = _roles(row, entities)
    title = next((role.title for role in roles if role.resolved and role.name == "holder"), None)
    if not title and kind == "relation":
        # The saved triple in reading order, with each side named the way the store names it;
        # the direction is the edge's job, not the title's.
        named = {role.name: (role.title or role.key) for role in roles}
        title = " ".join(part for part in (named.get("subject"), row.get("predicate"),
                                           named.get("object"))
                         if isinstance(part, str) and part) or key
    if not title and kind in {"event", "condition"} and statement:
        # An event or a condition has no holder to name it; its own sentence is what a reader
        # recognises, and the key stays in the advanced block.
        title = statement if len(statement) <= 60 else statement[:59] + "…"
    if not title:
        title = key or statement[:24]
    absence = row.get("observed_absence")
    uncertainty = row.get("uncertainty")
    absence = absence.strip() if isinstance(absence, str) and absence.strip() else None
    uncertainty = uncertainty.strip() if isinstance(uncertainty, str) and uncertainty.strip() else None
    return ObjectView(
        kind=kind,
        title=str(title),
        statement=statement,
        roles=roles,
        qualification=str(row.get("qualification") or ""),
        basis=str(row.get("qualification_basis") or ""),
        verification=str(row.get("verification") or ""),
        scope_state=row.get("scope_state") if isinstance(row.get("scope_state"), str) else None,
        citations=tuple(_citation_from_span(span, titles) for span in spans),
        identity=dict(identity),
        origin=origin,
        unattached=not any(role.resolved for role in roles),
        unsettled=absence or uncertainty,
        unsettled_source="observed_absence" if absence else ("uncertainty" if uncertainty else None),
    )


def from_meaning(row: Mapping[str, Any], *, scope_id: str | None = None,
                 candidate_id: str | None = None, version_id: str | None = None,
                 entities: Mapping[str, tuple[str, str]] | None = None,
                 titles: Mapping[str, str] | None = None) -> ObjectView:
    """Read an accepted meaning. Its own ``evidence`` list is the citation set."""
    spans = [span for span in (row.get("evidence") or []) if isinstance(span, Mapping)]
    if not spans:
        # An accepted row still records the span it was read from; use it rather than pretend
        # the row has no citation.
        spans = [row] if row.get("source_id") else []
    return _build(row, origin="accepted_meaning", entities=entities or {}, titles=titles or {},
                  spans=spans,
                  identity={"meaning_id": row.get("meaning_id"), "key": row.get("key"),
                            "scope_id": scope_id, "candidate_id": candidate_id,
                            "version_id": version_id, "source": "accepted_version"})


def from_item(row: Mapping[str, Any], *, scope_id: str | None = None,
              candidate_id: str | None = None, version_id: str | None = None,
              entities: Mapping[str, tuple[str, str]] | None = None,
              titles: Mapping[str, str] | None = None) -> ObjectView:
    """Read one candidate entry. Its span is flattened onto the row itself."""
    spans: list[Mapping[str, Any]] = [span for span in (row.get("evidence") or [])
                                      if isinstance(span, Mapping)]
    if not spans and row.get("source_id"):
        spans = [row]
    return _build(row, origin="candidate_entry", entities=entities or {}, titles=titles or {},
                  spans=spans,
                  identity={"meaning_id": row.get("meaning_id"), "key": row.get("key"),
                            "scope_id": scope_id, "candidate_id": candidate_id,
                            "version_id": version_id, "source": "candidate_entry"})


def attach_conditions(views: Sequence[ObjectView]) -> tuple[ObjectView, ...]:
    """Follow a saved ``applies_to`` one hop: condition -> duty or event -> the entities it names.

    A condition saved against a duty is not unattached - it belongs wherever that duty
    belongs. Only a key this version cannot resolve stays a key, and then the reason is
    written down instead of the row being dropped from every page.
    """
    by_key: dict[str, ObjectView] = {}
    for view in views:
        key = view.identity.get("key")
        if isinstance(key, str) and key:
            by_key.setdefault(key, view)
    out: list[ObjectView] = []
    for view in views:
        if view.kind != "condition" or not view.roles:
            out.append(view)
            continue
        roles: list[Role] = []
        for role in view.roles:
            if role.resolved:
                roles.append(role)
                continue
            target = by_key.get(role.key)
            if target is None or target is view:
                roles.append(role)  # nothing saved under that key: keep it, and say so
                continue
            reached = [Role(name="applies_to", key=inner.key, title=inner.title,
                            page=inner.page, via=role.key)
                       for inner in target.roles if inner.resolved]
            roles.extend(reached or [role])
        out.append(replace(view, roles=tuple(roles),
                           unattached=not any(item.resolved for item in roles)))
    return tuple(out)


def unattached_reason(view: ObjectView) -> str:
    """Why this object is on no page, in the row's own terms."""
    if not view.roles:
        return f"{view.kind_label} · 没有记录持有者或适用对象"
    missing = [role.key for role in view.unresolved_roles]
    return f"{view.kind_label} · 这些键在本版没有对应对象：{'、'.join(missing)}"


def collect(rows: Iterable[Mapping[str, Any]], *, adapter: str = "meaning",
            **kwargs: Any) -> tuple[ObjectView, ...]:
    """Every duty / event / condition in ``rows``, read through one adapter, in row order."""
    build = from_meaning if adapter == "meaning" else from_item
    views = [build(row, **kwargs) for row in rows if row.get("kind") in OBJECT_KINDS]
    return attach_conditions(views)


def attached_to(views: Sequence[ObjectView], key: str) -> tuple[ObjectView, ...]:
    """The objects whose own saved roles name ``key`` - never the ones that merely look close."""
    return tuple(view for view in views if key in view.keys)


def unattached(views: Sequence[ObjectView]) -> tuple[ObjectView, ...]:
    return tuple(view for view in views if view.unattached)
