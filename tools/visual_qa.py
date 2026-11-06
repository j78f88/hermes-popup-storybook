#!/usr/bin/env python3
"""Send storybook screenshots to an OpenRouter vision model."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence

OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
PLACEHOLDER = re.compile(r"{{\s*([A-Za-z][A-Za-z0-9_-]*)\s*}}")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
STATE_LABELS = {
    "start": "at rest",
    "half": "with the slider pull tab half pulled",
    "pulled": "with the slider pull tab fully pulled",
    "lifted": "with the lesson flap lifted",
    "final": "in its final interactive state",
}


def render_brief(template: str, vars: Mapping[str, str]) -> str:
    """Replace every template placeholder or raise for missing values."""
    names = set(PLACEHOLDER.findall(template))
    missing = sorted(name for name in names if name not in vars)
    if missing:
        raise ValueError("Missing brief variables: " + ", ".join(missing))

    def replace(match: re.Match[str]) -> str:
        return str(vars[match.group(1)])

    rendered = PLACEHOLDER.sub(replace, template)
    unresolved = sorted(set(PLACEHOLDER.findall(rendered)))
    if unresolved:
        raise ValueError("Unresolved brief variables: " + ", ".join(unresolved))
    return rendered


def image_label(path: Path) -> str:
    """Explain the screenshot state encoded in a generated file name."""
    stem = path.stem
    lower = stem.lower()
    if lower.startswith("sheet-") or re.match(r"^s\d", lower):
        return f"Stage sheet {stem}. Compare the scene states across the sheet."
    if lower.startswith("p") and ("print" in lower or re.match(r"^p\d", lower)):
        return f"Printable edition page {stem}."

    state = next(
        (name for name in STATE_LABELS if re.search(rf"(?:^|[-_]){name}(?:$|[-_])", lower)),
        None,
    )
    page = re.search(r"(?:^|[-_])p(\d+)(?:$|[-_])", lower)
    if state and page:
        return f"Page {page.group(1)} {STATE_LABELS[state]}."
    if state:
        return f"Screenshot {stem}, {STATE_LABELS[state]}."
    return f"Screenshot {stem}."


def _image_part(path: Path) -> dict[str, Any]:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{encoded}"},
    }


def build_payload(
    model: str,
    brief: str,
    images: Sequence[Path],
    recheck: Any = None,
) -> dict[str, Any]:
    """Build an OpenRouter JSON request for the supplied images."""
    content: list[dict[str, Any]] = [{"type": "text", "text": brief}]
    if recheck is not None:
        prior = recheck.get("defects", recheck) if isinstance(recheck, dict) else recheck
        content.append(
            {
                "type": "text",
                "text": (
                    "Recheck every prior defect below against the supplied images. "
                    "Add a recheck array to the response. For each prior defect, include "
                    "its id, a status of fixed, still_present, partly_fixed, or not_visible, "
                    "and a short note.\n\nPrior defects:\n"
                    + json.dumps(prior, ensure_ascii=False, indent=2)
                ),
            }
        )
    for image in images:
        content.append(
            {"type": "text", "text": f"Image {image.name}: {image_label(image)}"}
        )
        content.append(_image_part(image))

    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 16000,
        "reasoning": {"effort": "high"},
        "response_format": {"type": "json_object"},
    }


def dry_run_summary(
    payload: Mapping[str, Any],
    images: Sequence[Path],
    brief: str,
    variables: Mapping[str, str] | None = None,
    brief_file: Path | None = None,
) -> dict[str, Any]:
    """Return request details without exposing encoded image data."""
    first_line = next((line.strip() for line in brief.splitlines() if line.strip()), "")
    payload_bytes = len(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    return {
        "image_count": len(images),
        "payload_bytes": payload_bytes,
        "brief_head": first_line[:200],
        "variables": dict(sorted((variables or {}).items())),
        "brief_file": str(brief_file) if brief_file else None,
    }


def _parse_vars(values: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Brief variable must use key=value: {value}")
        key, text = value.split("=", 1)
        if not key:
            raise ValueError("Brief variable key cannot be empty")
        parsed[key] = text
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="OpenRouter model id")
    parser.add_argument("--images", required=True, type=Path, help="Screenshot folder")
    parser.add_argument("--brief", required=True, type=Path, help="QA brief template")
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Template value. Repeat for each placeholder.",
    )
    parser.add_argument(
        "--recheck", type=Path, help="Previous raw QA JSON containing defects"
    )
    parser.add_argument("--out", required=True, type=Path, help="Output folder")
    parser.add_argument("--dry-run", action="store_true", help="Build but do not send")
    return parser


def _request(payload: Mapping[str, Any], key: str) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "popup-storybook visual QA",
        },
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.load(response)
    return result, time.monotonic() - started


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        variables = _parse_vars(args.var)
        template = args.brief.read_text(encoding="utf-8")
        brief = render_brief(template, variables)
        recheck = (
            json.loads(args.recheck.read_text(encoding="utf-8"))
            if args.recheck
            else None
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    images = sorted(
        path
        for path in args.images.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        parser.error(f"No JPG or PNG images found in {args.images}")

    payload = build_payload(args.model, brief, images, recheck=recheck)
    if args.dry_run:
        args.out.mkdir(parents=True, exist_ok=True)
        brief_file = args.out / "qa-dry-run-brief.md"
        brief_file.write_text(brief, encoding="utf-8")
        print(
            json.dumps(
                dry_run_summary(
                    payload,
                    images,
                    brief,
                    variables=variables,
                    brief_file=brief_file.resolve(),
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        parser.error("OPENROUTER_API_KEY is required unless --dry-run is used")

    response, seconds = _request(payload, key)
    choice = response["choices"][0]
    message = choice["message"].get("content") or ""
    if not isinstance(message, str):
        message = json.dumps(message, ensure_ascii=False)

    run_name = "recheck" if recheck is not None else "first-pass"
    meta = {
        "model_requested": args.model,
        "model_returned": response.get("model"),
        "provider": response.get("provider"),
        "usage": response.get("usage"),
        "seconds": round(seconds, 1),
        "images": [path.name for path in images],
        "finish_reason": choice.get("finish_reason"),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"qa-{run_name}-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / f"qa-{run_name}-raw.json").write_text(message + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
