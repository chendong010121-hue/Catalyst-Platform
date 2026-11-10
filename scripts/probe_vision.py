"""Ask a model whether it can see, and record the answer beside the model's name.

    CATALYST_LLM_API_KEY=... PYTHONUTF8=1 python scripts/probe_vision.py \
        --model deepseek-flash --base-url https://api.deepseek.com

The probe is one picture the model has never seen: a dark square with a white block in
one corner only. A text-only model cannot answer where the block is; a model that sees
answers it in a word. The answer, the token count and the picture's sha256 are written to
``catalyst_platform/config/vision-<model>.json``, which is what the router reads — a
capability recorded from evidence, not remembered from a model's family name.

Cost: one request, a few hundred tokens. Nothing else is sent.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalyst_platform.understand_route import probe_path  # noqa: E402

PROMPT = "图中白色方块在哪个角？只回答方位词：左上、右上、左下、右下。"
EXPECTED = "右下"


def picture() -> bytes:
    """A 200x200 dark square with a white block in the bottom-right corner only."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        raise SystemExit("Pillow is required for the probe picture")
    image = Image.new("RGB", (200, 200), (20, 20, 20))
    ImageDraw.Draw(image).rectangle([120, 120, 190, 190], fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def ask(base_url: str, model: str, key: str, png: bytes) -> tuple[str, int]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(png).decode()}}]}],
        "max_tokens": 40, "stream": False, "thinking": {"type": "disabled"},
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"probe refused: HTTP {error.code} {error.read().decode('utf-8', 'replace')[:200]}")
    message = payload.get("choices", [{}])[0].get("message", {})
    return str(message.get("content") or "").strip(), int(payload.get("usage", {}).get("total_tokens") or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="write the record shape without a request")
    args = parser.parse_args()
    png = picture()
    digest = hashlib.sha256(png).hexdigest()
    if args.dry_run:
        print(json.dumps({"model": args.model, "picture_sha256": digest,
                          "prompt": PROMPT, "answer_expected": EXPECTED}, ensure_ascii=False))
        return 0
    key = os.environ.get("CATALYST_LLM_API_KEY", "").strip()
    if not key:
        raise SystemExit("CATALYST_LLM_API_KEY is not set")
    answer, tokens = ask(args.base_url, args.model, key, png)
    record = {
        "schema_version": 1,
        "model": args.model,
        "base_url": args.base_url,
        "probed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "prompt": PROMPT,
        "answer_expected": EXPECTED,
        "answer": answer,
        "passed": EXPECTED in answer,
        "total_tokens": tokens,
    }
    out = args.out or probe_path(args.model)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), **record}, ensure_ascii=False))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
