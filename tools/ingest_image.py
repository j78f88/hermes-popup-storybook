#!/usr/bin/env python3
"""Ingest a user or stock image into a story JSON file for offline use.

Supports three modes:
- cutout: strips EXIF/GPS metadata, resizes, encodes as an offline data URI
  in story["images"][ID] for use on stage or wall pieces via {"image": ID}.
- polaroid: strips EXIF/GPS metadata, resizes and stores in story["images"][ID]
  for taped fact booklet cards or wall clippings.
- pixel: converts the image into a 20-colour paper palette sprite grid in
  story["sprites"][ID].
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path
from typing import Any

Image: Any
try:
    from PIL import Image as _PILImage

    Image = _PILImage
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import validate as V  # noqa: E402


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def clean_image(path: Path) -> Image.Image:
    with Image.open(path) as src:
        rgba = src.convert("RGBA")
        fresh = Image.new("RGBA", rgba.size)
        fresh.putdata(list(rgba.getdata()))
        return fresh


def to_pixel_rows(img: Image.Image, target_w: int, palette: dict[str, str]) -> list[str]:
    w, h = img.size
    target_h = max(1, round(h * target_w / max(1, w)))
    small = img.resize((target_w, target_h), Image.Resampling.NEAREST)
    pal_rgb = {k: hex_to_rgb(v) for k, v in palette.items()}
    rows: list[str] = []
    for y in range(target_h):
        row = []
        for x in range(target_w):
            r, g, b, a = small.getpixel((x, y))
            if a < 64:
                row.append(".")
                continue
            best_k = min(
                pal_rgb,
                key=lambda k: (r - pal_rgb[k][0]) ** 2 + (g - pal_rgb[k][1]) ** 2 + (b - pal_rgb[k][2]) ** 2,
            )
            row.append(best_k)
        rows.append("".join(row))
    return rows


def encode_data_uri(img: Image.Image, max_size: int) -> tuple[str, int, int]:
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / float(max(w, h))
        w = max(1, round(w * scale))
        h = max(1, round(h * scale))
        img = img.resize((w, h), Image.Resampling.LANCZOS)
    for fmt, mime, kwargs in (
        ("WEBP", "image/webp", {"quality": 84, "method": 4}),
        ("PNG", "image/png", {"optimize": True}),
    ):
        buf = io.BytesIO()
        try:
            img.save(buf, format=fmt, **kwargs)
            raw = buf.getvalue()
            if len(raw) <= V.MAX_IMAGE_BYTES:
                b64 = base64.b64encode(raw).decode("ascii")
                return f"data:{mime};base64,{b64}", w, h
        except Exception:
            continue
    raise ValueError("Image could not be compressed under the 180 KB per-image limit; reduce --max-size")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="path to input PNG, JPEG or WebP image")
    parser.add_argument("--story", required=True, help="path to story.json to update")
    parser.add_argument("--id", required=True, help="sprite or image identifier")
    parser.add_argument("--mode", choices=("cutout", "polaroid", "pixel"), default="cutout")
    parser.add_argument("--source", help="source key in story['sources'] (required for cutout and polaroid)")
    parser.add_argument("--licence", default="Owner or licensed asset", help="licence note for stock or user image")
    parser.add_argument("--max-size", type=int, default=220, help="max pixel dimension for cutout/polaroid")
    parser.add_argument("--width", type=int, default=16, help="grid width for pixel mode")
    args = parser.parse_args(argv)
    if Image is None:
        print("FAIL: Pillow is required for ingest_image.py (pip install Pillow)", file=sys.stderr)
        return 1

    img_path = Path(args.image)
    story_path = Path(args.story)
    if not img_path.exists():
        print(f"FAIL: image file not found: {img_path}", file=sys.stderr)
        return 1
    if not story_path.exists():
        print(f"FAIL: story file not found: {story_path}", file=sys.stderr)
        return 1

    story = json.loads(story_path.read_text(encoding="utf-8"))
    lib, _ = V.load_library()
    palette = dict(lib["palette"], **story.get("palette", {}))
    clean = clean_image(img_path)

    if args.mode == "pixel":
        rows = to_pixel_rows(clean, args.width, palette)
        story.setdefault("sprites", {})[args.id] = rows
        story_path.write_text(json.dumps(story, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: wrote pixel sprite '{args.id}' ({len(rows[0])}x{len(rows)}) to {story_path}")
        return 0

    if not args.source:
        print("FAIL: --source is required for cutout and polaroid modes", file=sys.stderr)
        return 1
    if args.source not in story.get("sources", {}):
        print(f"FAIL: unknown source '{args.source}' in {story_path}", file=sys.stderr)
        return 1

    data_uri, w, h = encode_data_uri(clean, args.max_size)
    story.setdefault("images", {})[args.id] = {
        "src": data_uri,
        "width": w,
        "height": h,
        "mode": args.mode,
        "source": args.source,
        "licence": args.licence,
    }
    story_path.write_text(json.dumps(story, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: wrote {args.mode} image '{args.id}' ({w}x{h}) to {story_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
