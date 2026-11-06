"""Browser tests for angle-coupled and hand-driven page turns."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import build  # noqa: E402

EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright is not installed")
class PageTurnTests(unittest.TestCase):
    def built_book(self, folder: str) -> Path:
        output = Path(folder) / "book.html"
        output.write_text(build.render(EXAMPLE), encoding="utf-8")
        return output

    @staticmethod
    def drag(page, context, phone: bool, fraction: float) -> tuple[float, int]:
        leaf = page.locator(".page.right").bounding_box()
        surface = page.locator(".stage").bounding_box()
        x0 = surface["x"] + surface["width"] - 8
        y = surface["y"] + surface["height"] * 0.55
        x1 = x0 - leaf["width"] * fraction
        if phone:
            session = context.new_cdp_session(page)
            session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y, "id": 1}]})
            for step in range(1, 19):
                x = x0 + (x1 - x0) * step / 18
                session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y, "id": 1}]})
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
            angle = page.evaluate("window.__book.turn().angle")
            session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            session.detach()
        else:
            page.mouse.move(x0, y)
            page.mouse.down()
            page.mouse.move(x1, y, steps=18)
            angle = page.evaluate("window.__book.turn().angle")
            page.mouse.up()
        page.wait_for_function("window.__book.turn() === null")
        return float(angle), int(page.evaluate("window.__book.cur()"))

    def test_leaf_and_popups_share_one_angle_on_desktop_and_phone(self):
        with tempfile.TemporaryDirectory() as folder, sync_playwright() as playwright:
            output = self.built_book(folder)
            browser = playwright.chromium.launch(headless=True)
            for phone in (False, True):
                context = browser.new_context(
                    viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
                    has_touch=phone,
                    is_mobile=phone,
                )
                page = context.new_page()
                page.goto(output.as_uri() + f"?phone={phone}#ch1")
                # Codex model: forward (and on phones) the leaf's front carries the old picture,
                # folding shut as the leaf rises; the new picture lies under the leaf and rises with it.
                # Drive the turn by hand in steps and read both pop-ups after each step, so frame timing
                # on a slow host cannot thin the samples.
                page.wait_for_function("window.__book && window.__book.cur() === 2")
                read = """() => { const t = window.__book.turn(); if (!t) return null;
                  const fold = (sel) => { const e = document.querySelector(sel); return e ? parseFloat(getComputedStyle(e).getPropertyValue('--fold-angle')) : null; };
                  const id = (sel) => { const e = document.querySelector(sel); return e ? e.dataset.stage : null; };
                  return { angle: t.angle, closing: fold('.leaf .face.f .stage'), opening: fold('.page.right .stage'),
                           closingId: id('.leaf .face.f .stage'), openingId: id('.page.right .stage') }; }"""
                leaf = page.locator(".page.right").bounding_box()
                surface = page.locator(".stage").bounding_box()
                x0 = surface["x"] + surface["width"] - 8
                y = surface["y"] + surface["height"] * 0.55
                samples = []
                session = context.new_cdp_session(page) if phone else None
                if phone:
                    session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y, "id": 1}]})
                else:
                    page.mouse.move(x0, y)
                    page.mouse.down()
                for step in range(1, 11):
                    x = x0 - leaf["width"] * 0.9 * step / 10
                    if phone:
                        session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y, "id": 1}]})
                    else:
                        page.mouse.move(x, y)
                    page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
                    sample = page.evaluate(read)
                    if sample and 5 <= sample["angle"] <= 175:
                        samples.append(sample)
                if phone:
                    session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                    session.detach()
                else:
                    page.mouse.up()
                page.wait_for_function("window.__book.turn() === null && window.__book.cur() === 3")
                self.assertGreaterEqual(len(samples), 6, samples)
                for sample in samples:
                    self.assertEqual(sample["closingId"], "ch1")
                    self.assertEqual(sample["openingId"], "ch2")
                    # Both spreads move at once, all the way through the turn.
                    self.assertAlmostEqual(sample["closing"], sample["angle"] * 88 / 180, delta=2)
                    self.assertAlmostEqual(sample["opening"], (180 - sample["angle"]) * 88 / 180, delta=2)
                context.close()
            browser.close()

    def test_drag_before_half_returns_and_after_half_turns(self):
        with tempfile.TemporaryDirectory() as folder, sync_playwright() as playwright:
            output = self.built_book(folder)
            browser = playwright.chromium.launch(headless=True)
            for phone in (False, True):
                context = browser.new_context(
                    viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 900},
                    has_touch=phone,
                    is_mobile=phone,
                )
                page = context.new_page()
                page.goto(output.as_uri() + f"?phone={phone}-40#ch1")
                angle, current = self.drag(page, context, phone, 0.4)
                self.assertAlmostEqual(angle, 72, delta=2)
                self.assertEqual(current, 2)
                page.goto(output.as_uri() + f"?phone={phone}-60#ch1")
                angle, current = self.drag(page, context, phone, 0.6)
                self.assertAlmostEqual(angle, 108, delta=2)
                self.assertEqual(current, 3)
                context.close()
            browser.close()


if __name__ == "__main__":
    unittest.main()
