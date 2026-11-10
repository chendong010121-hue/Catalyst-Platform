"""Which channels a reading has, decided by what the material and the model can do.

A source can be read three ways, and the reading uses every one of them that applies:

* **structure** — the connections and boxes a page draws. Deterministic, free, and the
  only channel that can state a hierarchy outright. Always on when a source has them.
* **vision** — the page as a picture. Needs a model that can see (a declared capability,
  recorded from a probe rather than assumed from a model's name) *and* a page that only
  exists as pixels. Off otherwise: a channel that cannot run must not be quietly
  substituted by a guess.
* **questions** — everything the other two cannot settle, handed to the Owner with the
  locators that raised it. This is not a failure path: a drawn org chart is the only
  place a hierarchy is stated, and a page that does not draw it has nothing to assert.

The choice is a function of observed facts — does this model read pictures, does this
material have pages that are only pictures — never of a model's name or a brand.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

_CONFIG_DIR = Path(__file__).resolve().parent / "config"
_PROBE_FIELDS = {"schema_version", "model", "base_url", "probed_at", "prompt",
                 "answer_expected", "answer", "passed", "total_tokens"}


@dataclass(frozen=True)
class Channels:
    """Which reading channels a run may use, and why the others did not run."""
    structure: bool
    vision: bool
    questions: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"structure": self.structure, "vision": self.vision,
                "questions": self.questions, "reason": self.reason}


def probe_path(model: str) -> Path:
    return _CONFIG_DIR / f"vision-{re.sub(r'[^a-z0-9.-]+', '-', model.casefold())}.json"


def load_vision_record(model: str, *, path: Path | None = None) -> dict[str, Any] | None:
    """The recorded probe for this model, if one passed.

    A capability is declared by evidence: the probe asked a question a text-only model
    cannot answer, on a picture it did not see before. Anything else — a remembered
    feature, a family name, a vendor page — is not a declaration this reads.
    """
    selected = Path(path) if path is not None else probe_path(model)
    try:
        raw = selected.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or set(data) != _PROBE_FIELDS:
        return None
    if data.get("model") != model or data.get("passed") is not True:
        return None
    return data


def choose_channels(
    *,
    model: str,
    structure_cells: int,
    raster_pages: int,
    vision_record: Mapping[str, Any] | None = None,
) -> Channels:
    """The channels this run may use, and the reason for the ones it may not."""
    record = vision_record if vision_record is not None else load_vision_record(model)
    declared = bool(record and record.get("passed") is True and record.get("model") == model)
    structure = structure_cells > 0
    if raster_pages and not declared:
        reason = ("此模型没有通过识图探针，"+f"{raster_pages} 页只有图像；这些页的内容只能提问")
    elif raster_pages and declared:
        reason = f"此模型通过识图探针，{raster_pages} 页按图像读"
    elif not structure_cells:
        reason = "材料里没有画出来的连线：关系只能提问"
    else:
        reason = f"{structure_cells} 个画出来的格子按结构读；没有只有图像的页"
    return Channels(structure=structure, vision=bool(raster_pages and declared), questions=True,
                    reason=reason)
