#!/usr/bin/env python3
"""Shared browser helpers for popup-storybook QA tools."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "engine" / "build.py"
FREEZE_CSS = ".set{animation:none!important}.piece.bob .mech>svg{animation:none!important}.piece.twinkle .mech>svg{animation:none!important}.lf-cue .up{animation:none!important}"


@contextmanager
def built_book(source: str | Path):
    """Yield an HTML path, building JSON inputs inside a temporary directory."""
    source = Path(source).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() in {".html", ".htm"}:
        yield source
        return
    if source.suffix.lower() != ".json":
        raise ValueError("input must be a story JSON file or built HTML book")
    with tempfile.TemporaryDirectory(prefix="popup-storybook-") as folder:
        output = Path(folder) / "book.html"
        result = subprocess.run(
            [sys.executable, str(BUILD), str(source), "-o", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            message = (result.stdout + result.stderr).strip()
            raise RuntimeError(f"book build failed\n{message}")
        yield output


def load_story(source: str | Path) -> dict:
    """Read story data from JSON source or the embedded HTML payload."""
    source = Path(source).expanduser().resolve()
    if source.suffix.lower() == ".json":
        return json.loads(source.read_text(encoding="utf-8"))
    text = source.read_text(encoding="utf-8")
    marker = '<script id="story" type="application/json">'
    start = text.find(marker)
    if start < 0:
        marker = '<script type="application/json" id="story">'
        start = text.find(marker)
    if start < 0:
        return {}
    start += len(marker)
    end = text.find("</script>", start)
    if end < 0:
        return {}
    return json.loads(text[start:end].replace("<\\/", "</").replace("<\\!--", "<!--"))


def browser_context(
    playwright,
    phone: bool = False,
    browser_name: str = "chromium",
    reduced_motion: bool = False,
):
    """Launch one supported browser with the required viewport and motion setting."""
    browser_type = getattr(playwright, browser_name, None)
    if browser_type is None or browser_name not in {"chromium", "firefox", "webkit"}:
        raise ValueError(f"unsupported browser: {browser_name}")
    browser = browser_type.launch(headless=True)
    options = {
        "viewport": {"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
        "device_scale_factor": 2 if phone else 1,
        "reduced_motion": "reduce" if reduced_motion else "no-preference",
    }
    if phone:
        options.update(
            {
                # Firefox Playwright suppresses pointer events when is_mobile is true.
                # Keep its real touch capability and coarse pointer at the phone viewport,
                # while allowing page.mouse to exercise drag mechanics.
                "is_mobile": browser_name != "firefox",
                "has_touch": True,
                "screen": {"width": 390, "height": 844},
            }
        )
    return browser, browser.new_context(**options)


def open_book(page, html: str | Path, fragment: str = "") -> list[str]:
    """Open a built book and return its page keys."""
    url = Path(html).resolve().as_uri()
    if fragment:
        url += "#" + fragment.lstrip("#")
    page.goto(url, wait_until="load")
    page.wait_for_function("window.__book && window.__book.pages")
    page.add_style_tag(content=FREEZE_CSS)
    return page.evaluate("window.__book.pages()")


def go_to(page, index: int) -> None:
    """Turn directly to one page and wait for its layout."""
    page.evaluate("i => window.__book.go(i)", index)
    page.wait_for_function("i => window.__book.cur() === i", arg=index)
    page.wait_for_timeout(750)


def dispatch_key(page, selector: str, key: str) -> bool:
    """Dispatch one keyboard event to the first matching element."""
    return page.evaluate(
        """([selector,key]) => {
          const el=document.querySelector(selector);
          if(!el) return false;
          el.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true}));
          return true;
        }""",
        [selector, key],
    )


def set_start(page) -> None:
    """Reset available paper mechanisms."""
    dispatch_key(page, ".slider .tab", "Home")
    expanded = page.locator(".lflap[aria-expanded='true']")
    if expanded.count():
        dispatch_key(page, ".lflap", "Enter")
        page.wait_for_function(
            "() => { const l = document.querySelector('.page.right [data-lesson]'); return !l || l.style.getPropertyValue('--flap') === '0.0000'; }"
        )
    else:
        page.wait_for_timeout(80)


def set_half(page) -> None:
    """Set the pull tab to its halfway position."""
    dispatch_key(page, ".slider .tab", "Home")
    for _ in range(5):
        dispatch_key(page, ".slider .tab", "ArrowRight")
    page.wait_for_timeout(80)


def set_final(page) -> None:
    """Pull the tab and lift the lesson flap when present."""
    dispatch_key(page, ".slider .tab", "End")
    flap = page.locator(".lflap")
    if flap.count() and flap.get_attribute("aria-expanded") != "true":
        dispatch_key(page, ".lflap", "Enter")
        page.wait_for_function(
            "() => { const l = document.querySelector('.page.right [data-lesson]'); return !l || l.style.getPropertyValue('--flap') === '1.0000'; }"
        )
    else:
        page.wait_for_timeout(100)


def apply_state(page, state: str) -> None:
    """Move available mechanisms into one named state."""
    if state == "start":
        set_start(page)
    elif state == "half":
        set_half(page)
    elif state == "pulled":
        dispatch_key(page, ".slider .tab", "End")
        page.wait_for_timeout(80)
    elif state in {"lifted", "final"}:
        set_final(page)
    else:
        raise ValueError(f"unknown state: {state}")


def entry_for_key(story: dict, key: str) -> dict:
    """Return the story entry dict for one engine page key."""
    if key.startswith("ch"):
        number = key[2:]
        return next(
            (item for item in story.get("chapters", []) if str(item.get("number")) == number),
            {},
        )
    if key in {"contents", "numbers", "finale", "back"}:
        value = story.get(key)
        return value if isinstance(value, dict) else {}
    return {}


def scene_for_page(story: dict, key: str) -> tuple[dict, list[dict]]:
    """Return the scene and effects rendered for one engine page key."""
    entry = entry_for_key(story, key)
    if not entry:
        return {}, []
    effects = []
    for gadget in ("tab", "flap"):
        effects.extend((entry.get(gadget) or {}).get("effects") or [])
    return entry.get("scene") or {}, effects


def overlap_ratio(left: dict, right: dict) -> float:
    """Return intersection area divided by the smaller rectangle area."""
    width = max(0.0, min(left["right"], right["right"]) - max(left["left"], right["left"]))
    height = max(0.0, min(left["bottom"], right["bottom"]) - max(left["top"], right["top"]))
    intersection = width * height
    left_area = max(0.0, left["right"] - left["left"]) * max(0.0, left["bottom"] - left["top"])
    right_area = max(0.0, right["right"] - right["left"]) * max(0.0, right["bottom"] - right["top"])
    smaller = min(left_area, right_area)
    return intersection / smaller if smaller else 0.0
