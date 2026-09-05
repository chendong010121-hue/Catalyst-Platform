"""Small capability-owned seam for durable source-observation provenance."""

from __future__ import annotations

from collections.abc import Callable

from .contracts import Failure, SourceIdentity, SourceObservationProvenance, Success


class SourceObservationLedger:
    """Issue provenance only after a supplied source observation succeeds.

    The ledger owns one immutable source identity.  A failed reader is not
    recorded, and a locator that has not been successfully observed cannot be
    projected later as evidence.
    """

    def __init__(self, source_identity: SourceIdentity) -> None:
        if not isinstance(source_identity, SourceIdentity):
            raise TypeError("source_identity must be a SourceIdentity")
        self._source_identity = source_identity
        self._observed: dict[str, SourceObservationProvenance] = {}

    @property
    def source_identity(self) -> SourceIdentity:
        return self._source_identity

    def observe(self, locator: str, reader: Callable[[], object]) -> Success | Failure:
        if not isinstance(locator, str) or not locator:
            raise ValueError("locator must be a non-empty string")
        if not callable(reader):
            raise TypeError("reader must be callable")

        data = reader()
        if isinstance(data, Failure):
            return data
        provenance = SourceObservationProvenance(
            source_id=self._source_identity.source_id,
            source_revision=self._source_identity.revision,
            locator=locator,
        )
        self._observed[locator] = provenance
        return Success(data, provenance=provenance)

    def provenance_for(self, locator: str) -> SourceObservationProvenance:
        try:
            return self._observed[locator]
        except KeyError as exc:
            raise KeyError(f"source locator was not successfully observed: {locator!r}") from exc
