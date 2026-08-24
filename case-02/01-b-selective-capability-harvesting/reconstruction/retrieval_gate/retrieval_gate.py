"""Unbound, Case-local reconstruction of WAKU-A01.

This module owns only one decision boundary:

    current turn -> RETRIEVE + query | SKIP

It deliberately has no prompt builder, ranking policy, durable write path,
Agent loop, Domain semantics, Enterprise policy, or Waku-specific state.
"""

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class Decision:
    decision: str
    query: str
    reason: str


@dataclass(frozen=True)
class RetrievalResult:
    decision: str
    query: str
    reason: str
    retrieved_material: list[str]
    trace: list[dict[str, object]]


class ScriptedDecisionProvider:
    """Deterministic provider for an independent behavior proof."""

    def __init__(self, decisions: Iterable[Decision | BaseException]):
        self._decisions = list(decisions)

    def decide(self, turn: str) -> Decision:
        del turn  # the scripted provider is intentionally input-independent
        item = self._decisions.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class InMemoryMemoryStore:
    """Tiny read-only search seam used only by the Case-local proof."""

    def __init__(self, records: Mapping[str, Iterable[str]]):
        self._records = {query: list(material) for query, material in records.items()}
        self.searches: list[str] = []
        self.writes = 0

    def search(self, query: str) -> list[str]:
        self.searches.append(query)
        return list(self._records.get(query, []))


class RetrievalGate:
    """The unbound retrieval decision and query handoff only."""

    def __init__(self, decision_provider, store: InMemoryMemoryStore):
        self._decision_provider = decision_provider
        self._store = store

    def run(self, turn: str) -> RetrievalResult:
        try:
            decision = self._decision_provider.decide(turn)
            if decision.decision == "SKIP":
                event = {
                    "decision": "SKIP",
                    "query": "",
                    "reason": decision.reason,
                    "fallback": False,
                }
                return RetrievalResult("SKIP", "", decision.reason, [], [event])
            if decision.decision != "RETRIEVE":
                raise ValueError(f"unsupported decision {decision.decision!r}")
            query = decision.query
            reason = decision.reason
            fallback = False
        except Exception as exc:  # fail open: stale context is safer than none
            query = turn
            reason = f"decision provider failure ({type(exc).__name__}): {exc}"
            fallback = True

        event = {
            "decision": "RETRIEVE",
            "query": query,
            "reason": reason,
            "fallback": fallback,
        }
        material = self._store.search(query)
        return RetrievalResult("RETRIEVE", query, reason, material, [event])
