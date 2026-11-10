"""What the holder-source rule would do to a recorded answer, without sending anything.

The rule has two halves. The prompt asks the reader to bind a duty to the group its sentence
prints; this script measures only the half that runs in code - the row check that refuses a
holder read off the cell beside the named group. It replays an already recorded capture, so it
is zero-API and changes nothing: the card is read at `calls/*_response.json`, and every duty row
is put through the same `_duty_named_group` / `_same_group` the pipeline calls.

What it can and cannot say:

* it can say the substituted holder would now stop being a fact (SAFE_STOP);
* it cannot make the group appear. Declaring 「分公司其他员工」 as an entity is the model's half,
  and only a real run produces it. A row that flips to SAFE_STOP here is an incomplete answer,
  not a corrected one.

    PYTHONUTF8=1 python scripts/m1_offline_control.py
    PYTHONUTF8=1 python scripts/m1_offline_control.py --capture <run dir>
"""
from __future__ import annotations

import argparse
import io
import json
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalyst_platform.understand_semantic import (  # noqa: E402
    _DUTY_LABEL_PREFIXES,
    _duty_named_group,
    _same_group,
)

DEFAULT_CAPTURE = Path(
    r"E:/Catalyst_Project_Understand/20261027-capability-infra/p1-run-1/live46/.catalyst/"
    r"ts/bba65199bf4871a5/.catalyst/captures/run_c3d2e2cc7b7140c3bbb836e58c036dbf"
)


def _load(path: Path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _items(call: Path) -> list[dict]:
    content = _load(call).get("content") or "{}"
    try:
        parsed = json.loads(content)
    except ValueError:
        return []
    items = parsed.get("items") if isinstance(parsed, dict) else None
    return [item for item in items or [] if isinstance(item, dict)]


def _declared(items: list[dict]) -> dict[str, str]:
    return {str(item.get("key")): str(item.get("meaning") or "")
            for item in items if item.get("kind") in {"entity", "alias"} and item.get("key")}


def verdict(meaning: str, holder: str, declared: dict[str, str]) -> tuple[str, str]:
    """The rule's decision for one row, and the group the sentence printed."""
    named = _duty_named_group(meaning)
    if not named:
        return "NO_NAMED_GROUP", ""
    if "".join(named.split()) in _DUTY_LABEL_PREFIXES:
        return "LABEL_HEADING", named
    if _same_group(named, declared.get(holder, "")):
        return "BOUND_TO_NAMED_GROUP", named
    if named not in {name.strip() for name in declared.values()}:
        return "NAMED_GROUP_NOT_DECLARED", named
    return "NAMED_GROUP_ELSEWHERE", named


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    args = parser.parse_args()

    calls = sorted((args.capture / "calls").glob("*_response.json"))
    if not calls:
        raise SystemExit(f"no recorded responses under {args.capture}")

    counts: dict[str, int] = {}
    print("| 调用 | duty 键 | 句子点名的群体 | subject | 已声明名 | 规则判定 |")
    print("|---|---|---|---|---|---|")
    for call in calls:
        items = _items(call)
        declared = _declared(items)
        for item in items:
            if item.get("kind") != "duty":
                continue
            subject = str(item.get("subject") or "")
            state, named = verdict(str(item.get("meaning") or ""), subject, declared)
            counts[state] = counts.get(state, 0) + 1
            mark = {"BOUND_TO_NAMED_GROUP": "保持为 duty（正向）",
                    "LABEL_HEADING": "不动（栏目标签）",
                    "NO_NAMED_GROUP": "不动（无冒号前缀）",
                    "NAMED_GROUP_ELSEWHERE": "**降为未解析（SAFE_STOP）**",
                    "NAMED_GROUP_NOT_DECLARED": "**降为未解析（SAFE_STOP，群体未声明）**"}[state]
            print(f"| {call.name[:3]} | `{item.get('key')}` | {named or '—'} | {subject or '—'} | "
                  f"{declared.get(subject, '—')} | {mark} |")

    print()
    print("汇总：" + " / ".join(f"{key} {value}" for key, value in sorted(counts.items())))
    stopped = counts.get("NAMED_GROUP_ELSEWHERE", 0) + counts.get("NAMED_GROUP_NOT_DECLARED", 0)
    print(f"这条规则会把 {stopped} 条 duty 从「有持有人」改成「未解析」；"
          "它不会造出任何实体，群体出现仍是模型那一半的事。")


if __name__ == "__main__":
    main()
