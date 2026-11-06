#!/usr/bin/env python3
"""Export printable and storyboard PDF editions from a popup-storybook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _browser import browser_context, built_book, open_book


def print_pdf(page, destination: Path) -> None:
    """Print the current page using the book's CSS page size."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    page.emulate_media(media="print")
    page.pdf(
        path=str(destination),
        landscape=True,
        print_background=True,
        prefer_css_page_size=True,
    )


def run(source: str | Path, output: str | Path, storyboard: str | Path | None = None) -> tuple[Path, Path | None]:
    """Export the print edition and optionally export storyboard mode."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    output = Path(output).expanduser().resolve()
    storyboard_output = Path(storyboard).expanduser().resolve() if storyboard else None
    produced_storyboard = None
    with built_book(source) as html, sync_playwright() as playwright:
        browser, context = browser_context(playwright, phone=False)
        page = context.new_page()
        open_book(page, html)
        print_pdf(page, output)
        if storyboard_output:
            board_page = context.new_page()
            url = Path(html).resolve().as_uri() + "#storyboard"
            board_page.goto(url, wait_until="load")
            try:
                board_page.wait_for_selector(".storyboard", state="attached", timeout=5000)
            except PlaywrightTimeoutError:
                print("SKIP: storyboard mode did not render a .storyboard element")
            else:
                print_pdf(board_page, storyboard_output)
                produced_storyboard = storyboard_output
            board_page.close()
        context.close()
        browser.close()
    return output, produced_storyboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="story JSON or built HTML book")
    parser.add_argument("-o", "--out", required=True, help="print edition PDF")
    parser.add_argument("--storyboard", metavar="OUT2.pdf", help="optional storyboard PDF")
    args = parser.parse_args(argv)
    try:
        output, storyboard = run(args.book, args.out, args.storyboard)
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: wrote {output} ({output.stat().st_size} bytes)")
    if storyboard:
        print(f"PASS: wrote {storyboard} ({storyboard.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
