"""PRIVATE — generalized local evidence-query mechanism (E1; FN-04/05/09 completion).

Deterministic local retrieval over the admitted two regulations. NO LLM / RAG / Web /
vector DB (spec §10). All clause/table resolution is data-driven from the admitted
corpus — the mechanism contains NO benchmark-specific clause ids, table ids or
question literals (spec §4 / §15).

Query modes supported (spec §9):
  QMODE-01 explicit standard + clause locator
  QMODE-02 explicit standard + unknown/missing clause -> no_reliable_evidence
  QMODE-03 local topic evidence search (token scoring, bounded candidates)
  QMODE-04 explicit table / table-region query
  QMODE-05 existing professional applicability (handled by runner/applicability)
"""
from __future__ import annotations

import re

from .corpus import Corpus, clause_index, norm, resolve_table_caption, search_units

# Standard aliases -> corpus key (admitted manifest stems). Data, not per-benchmark.
STANDARD_ALIASES: dict[str, tuple[str, ...]] = {
    "GB55037-2022": ("GB55037-2022", "GB 55037-2022", "GB55037", "GB 55037", "防火通用规范", "建筑防火通用规范"),
    "DBJ33T1021-2023": (
        "DBJ33T1021-2023", "DBJ33/T1021-2023", "DBJ33T1021", "DBJ33/T1021",
        "停车场（库）设置规则和配建指标标准", "配建指标标准", "城市建筑工程停车场",
    ),
}

_CLAUSE_LOCATOR_RE = re.compile(r"第\s*(\d+\.\d+\.\d+)\s*条")
_CLAUSE_LOOSE_RE = re.compile(r"(\d+\.\d+\.\d+)\s*条")
_TABLE_LOCATOR_RE = re.compile(r"表\s*(\d+(?:\.\d+)+)(?:[-—](\d+))?")
_STOPWORDS = frozenset(
    "的了吗呢怎么什么哪些哪里规定要求内容有关于条文条款查查询看一下找检索标准规范原文"
    "以及和或为应在中是对于按照依据按我们请给我把要"
)
# Explicit evidence-query intent markers: presence routes standard+no-locator
# questions to QMODE-03 topic search instead of professional applicability.
_RETRIEVAL_INTENT = ("哪里提到", "查一下", "查", "原文", "内容", "有哪些", "相关", "条文", "条款", "关于")


def resolve_standard(question: str, regulation_context: dict | None = None) -> str | None:
    """Resolve the question to one admitted standard id (data-driven aliases).

    regulation_context.standard_hint is consulted only as an alias-level hint and
    must itself match an admitted standard key.
    """
    hint = (regulation_context or {}).get("standard_hint") or ""
    for standard_id, aliases in STANDARD_ALIASES.items():
        for alias in aliases:
            if alias in question:
                return standard_id
        if hint == standard_id or hint in aliases:
            return standard_id
    return None


def extract_clause_locator(question: str) -> str | None:
    """Extract an explicit clause locator (`第X.Y.Z条` / `X.Y.Z条`)."""
    match = _CLAUSE_LOCATOR_RE.search(question) or _CLAUSE_LOOSE_RE.search(question)
    return match.group(1) if match else None


def extract_table_locator(question: str) -> str | None:
    """Extract an explicit table locator (`表X.Y.Z`)."""
    match = _TABLE_LOCATOR_RE.search(question)
    if not match:
        return None
    base = match.group(1)
    suffix = match.group(2)
    return f"{base}-{suffix}" if suffix else base


def _topic_tokens(question: str, standard_id: str | None) -> list[str]:
    """Deterministic topic tokens: strip standard aliases, emit CJK n-grams + latin words.

    N-gram windows (2/3/4 chars) let a phrase like 人员密集场所 match any clause that
    contains it, without treating the whole question sentence as one opaque token.
    Pure-stopword grams are dropped.
    """
    text = question
    if standard_id is not None:
        for alias in STANDARD_ALIASES.get(standard_id, ()):
            text = text.replace(alias, " ")
    grams: set[str] = set()
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        run = norm(run)
        if not run:
            continue
        for size in (2, 3, 4):
            for index in range(len(run) - size + 1):
                gram = run[index:index + size]
                if gram and not all(ch in _STOPWORDS for ch in gram):
                    grams.add(gram)
    for word in re.findall(r"[A-Za-z]{2,}", text):
        grams.add(word)
    return sorted(grams)


def topic_search(corpus: Corpus, question: str, standard_id: str | None, top_n: int = 3) -> list[dict]:
    """QMODE-03 — deterministic token-scored retrieval over clause units.

    Returns bounded candidates sorted by match score; every candidate is a real
    clause from the admitted corpus (verbatim + locator). Lexical scoring only.

    Scoring: only grams of length >= 3 count (a bare 2-gram is not a meaningful
    topic signal); weight = len(gram)**2 so longer phrase matches rank first and a
    topic that is absent from the corpus does not match clauses that merely contain
    a common 2-gram of it (e.g. a query about a lightning-protection topic must not
    match clauses that only discuss general design).
    """
    tokens = _topic_tokens(question, standard_id)
    meaningful = [token for token in tokens if len(token) >= 3]
    if not meaningful:
        return []
    units = search_units(corpus)
    scored: list[tuple[int, dict]] = []
    for unit in units:
        score = 0
        best = 0
        for token in meaningful:
            if norm(token) in unit["norm"]:
                score += len(token) ** 2
                best = max(best, len(token))
        if score > 0:
            scored.append((score, best, unit))
    scored.sort(key=lambda triple: (-triple[0], -triple[1], triple[2]["unit_id"]))
    return [unit for _score, _best, unit in scored[:top_n]]


def clause_exists(corpus: Corpus, clause_id: str) -> bool:
    """QMODE-02 — does this clause exist in the admitted corpus (data-driven)?"""
    return clause_id in clause_index(corpus)


def table_caption_for(corpus: Corpus, table_number: str) -> str | None:
    """QMODE-04 — resolve table number to full caption (or None if not parseable)."""
    return resolve_table_caption(corpus, table_number)


def classify_query(question: str, regulation_context: dict | None = None) -> dict:
    """Classify the question into an evidence-query mode (spec §9).

    Returns {"mode": QMODE-01..05, "standard_id", "clause_id", "table_number",
    "topic_tokens"}.

    Rules (data-driven; no per-benchmark branches):
      standard + clause locator          -> QMODE-01 (missing clause -> QMODE-02 at lookup)
      standard + table locator           -> QMODE-04
      standard + explicit retrieval intent -> QMODE-03 (topic search)
      otherwise                          -> QMODE-05 (professional applicability)
    """
    standard_id = resolve_standard(question, regulation_context)
    clause_id = extract_clause_locator(question)
    table_number = extract_table_locator(question)

    if standard_id is not None and clause_id is not None:
        return {"mode": "QMODE-01", "standard_id": standard_id, "clause_id": clause_id,
                "table_number": None, "topic_tokens": []}
    if standard_id is not None and table_number is not None:
        return {"mode": "QMODE-04", "standard_id": standard_id, "clause_id": None,
                "table_number": table_number, "topic_tokens": []}
    if standard_id is not None and any(marker in question for marker in _RETRIEVAL_INTENT):
        return {"mode": "QMODE-03", "standard_id": standard_id, "clause_id": None,
                "table_number": None, "topic_tokens": _topic_tokens(question, standard_id)}
    return {"mode": "QMODE-05", "standard_id": None, "clause_id": None,
            "table_number": None, "topic_tokens": []}
