#!/usr/bin/env python3
"""Capture popup-storybook page states and stage contact sheets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _browser import (
    apply_state,
    browser_context,
    built_book,
    go_to,
    open_book,
)


def page_number(key: str, fallback: int) -> str:
    """Return a compact page number for one engine page key."""
    return key[2:] if key.startswith("ch") and key[2:] else str(fallback)


def poster_key(value: int | str) -> str:
    """Return the engine page key for a 1-indexed chapter number."""
    return f"ch{int(value)}"


def screenshot(page, path: Path, phone: bool) -> None:
    """Save one stable full-spread or full-phone screenshot."""
    page.screenshot(path=str(path), full_page=phone, animations="disabled")


def right_page_capture(page, path: Path) -> None:
    """Capture the rendered right page using its actual browser bounds."""
    target = page.locator(".page.right")
    if not target.count():
        raise RuntimeError("right page was not rendered")
    target.screenshot(path=str(path), animations="disabled")


def make_contact_sheets(rows: list[tuple[str, list[Path]]], output: Path) -> list[Path]:
    """Build three-row, four-state contact sheets from stage captures."""
    from PIL import Image, ImageDraw

    states = ("start", "half", "pulled", "lifted")
    sheets: list[Path] = []
    for sheet_index, start in enumerate(range(0, len(rows), 3), 1):
        group = rows[start : start + 3]
        opened = [(label, [Image.open(path).convert("RGB") for path in paths]) for label, paths in group]
        cell_width = max(image.width for _, images in opened for image in images)
        cell_height = max(image.height for _, images in opened for image in images)
        label_height = 28
        canvas = Image.new(
            "RGB",
            (cell_width * len(states), (cell_height + label_height) * len(opened)),
            "white",
        )
        draw = ImageDraw.Draw(canvas)
        for row_index, (label, images) in enumerate(opened):
            for column, image in enumerate(images):
                x = column * cell_width
                y = row_index * (cell_height + label_height) + label_height
                canvas.paste(image, (x, y))
                state = states[column]
                draw.text((x + 8, y - label_height + 7), f"{label} {state}", fill="#241f2e")
        destination = output / f"sheet-{sheet_index}.jpg"
        canvas.save(destination, "JPEG", quality=90, optimize=True)
        for _, images in opened:
            for image in images:
                image.close()
        sheets.append(destination)
    return sheets


def run(
    source: str | Path,
    output: str | Path,
    phone: bool = False,
    poster: bool = False,
    poster_page: int = 1,
    poster_only: bool = False,
) -> list[Path]:
    """Capture every book page and return all public output files."""
    if poster_only:
        poster = True
    if poster and phone:
        raise ValueError("--poster uses the desktop layout. Run it without --phone")
    from playwright.sync_api import sync_playwright

    output = Path(output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    contact_rows: list[tuple[str, list[Path]]] = []
    poster_file: Path | None = None
    target_key = poster_key(poster_page) if poster else None
    with built_book(source) as html, sync_playwright() as playwright:
        browser, context = browser_context(playwright, phone=phone)
        page = context.new_page()
        pages = open_book(page, html)
        if target_key is not None and target_key not in pages:
            raise ValueError(f"poster page '{target_key}' is not in {pages}")
        if poster_only and target_key is not None:
            go_to(page, pages.index(target_key))
            apply_state(page, "lifted")
            page.wait_for_function(
                "() => !document.querySelector('.book.turning') && !!document.querySelector('.page.right .stage:not(.folded)')"
            )
            poster_file = output / "cover-card.jpg"
            page.screenshot(path=str(poster_file), type="jpeg", quality=92, animations="disabled")
            context.close()
            browser.close()
            return [poster_file]
        for index, key in enumerate(pages):
            go_to(page, index)
            if key.startswith("ch"):
                number = page_number(key, index)
                prefix = f"{index:02d}"
                state_files: list[Path] = []
                stage_files: list[Path] = []
                for code, state in (("a", "start"), ("b", "half"), ("c", "pulled"), ("d", "lifted")):
                    apply_state(page, state)
                    state_file = output / f"{prefix}{code}-p{number}-{state}.png"
                    screenshot(page, state_file, phone)
                    saved.append(state_file)
                    if poster and key == target_key and state == "lifted":
                        from PIL import Image

                        poster_file = output / "cover-card.jpg"
                        with Image.open(state_file) as lifted_image:
                            lifted_image.convert("RGB").save(poster_file, "JPEG", quality=92)
                    stage_file = output / f".{prefix}{code}-p{number}-stage.png"
                    right_page_capture(page, stage_file)
                    state_files.append(state_file)
                    stage_files.append(stage_file)
                contact_rows.append((f"p{number}", stage_files))
            else:
                name = "cover" if key == "cover" else key
                destination = output / f"{index:02d}-{name}.png"
                screenshot(page, destination, phone)
                saved.append(destination)
        context.close()
        browser.close()
    saved.extend(make_contact_sheets(contact_rows, output))
    if poster_file is not None:
        saved.append(poster_file)
    for _, files in contact_rows:
        for path in files:
            path.unlink(missing_ok=True)
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="story JSON or built HTML book")
    parser.add_argument("-o", "--out", required=True, help="screenshot directory")
    parser.add_argument("--phone", action="store_true", help="capture the phone layout")
    parser.add_argument(
        "--poster",
        action="store_true",
        help="also export a settled 1440x900 cover-card.jpg preview",
    )
    parser.add_argument(
        "--poster-only",
        action="store_true",
        help="export only the settled 1440x900 cover-card.jpg preview",
    )
    parser.add_argument(
        "--poster-page",
        type=int,
        default=1,
        help="1-indexed chapter number to use for --poster (default: 1)",
    )
    args = parser.parse_args(argv)
    try:
        files = run(
            args.book,
            args.out,
            phone=args.phone,
            poster=args.poster,
            poster_page=args.poster_page,
            poster_only=args.poster_only,
        )
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: saved {len(files)} screenshots and sheets in {Path(args.out).resolve()}")
    for path in files:
        print(path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
