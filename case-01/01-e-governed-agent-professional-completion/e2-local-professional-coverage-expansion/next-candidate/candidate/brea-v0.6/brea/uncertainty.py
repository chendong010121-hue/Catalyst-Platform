"""FN-06 — Uncertainty & Fail-Closed Decision (AGENT-OWNED BEHAVIOR).

Never fabricate certainty or numeric values (OBL-04).
"""
from __future__ import annotations

from .contracts import Uncertainty


def decide(missing: list[str], applicability: dict, bound_ok: bool) -> tuple[str, str, Uncertainty]:
    if missing:
        return (
            "insufficient_context",
            "无法可靠回答：判定所需专业事实缺失（" + "、".join(missing) + "）。在补齐前不能给出结论或数值。",
            Uncertainty(level="explicit", description="缺失事实列表见结论"),
        )
    if not applicability.get("standard_id"):
        return (
            "no_reliable_evidence",
            "本地已接纳规范库中无适用依据，不能给出结论或数值。",
            Uncertainty(level="explicit", description="无适用标准"),
        )
    if not bound_ok:
        return (
            "no_reliable_evidence",
            "证据绑定失败，拒绝给出结论。",
            Uncertainty(level="explicit", description="证据绑定失败"),
        )
    return ("accepted_with_evidence", "", Uncertainty(level="low", description="条文/表格直接适用"))
