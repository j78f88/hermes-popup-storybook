"""Browser checks for direct, accessible storybook interactions."""

import copy
import json
import math
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import build  # noqa: E402

EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())

FAKE_AUDIO = r"""
(() => {
  window.__audioContexts = 0;
  window.__audioStarts = 0;
  class Param {
    constructor() { this.value = 0; }
    setValueAtTime(v) { this.value = v; }
    linearRampToValueAtTime(v) { this.value = v; }
    exponentialRampToValueAtTime(v) { this.value = v; }
    setTargetAtTime(v) { this.value = v; }
    cancelScheduledValues() {}
  }
  class Node {
    constructor() {
      this.gain = new Param();
      this.frequency = new Param();
      this.Q = new Param();
      this.playbackRate = new Param();
    }
    connect(node) { return node; }
    start() { window.__audioStarts += 1; }
    stop() {}
  }
  class AudioContext {
    constructor() {
      window.__audioContexts += 1;
      this.sampleRate = 48000;
      this.state = 'suspended';
      this.destination = new Node();
    }
    get currentTime() { return performance.now() / 1000; }
    resume() { this.state = 'running'; return Promise.resolve(); }
    createGain() { return new Node(); }
    createBufferSource() { return new Node(); }
    createBiquadFilter() { return new Node(); }
    createOscillator() { return new Node(); }
    createBuffer(channels, length) {
      return {getChannelData: () => new Float32Array(length)};
    }
  }
  window.AudioContext = AudioContext;
  window.webkitAudioContext = undefined;
})();
"""


def luminance(colour):
    values = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    values = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def white_contrast(colour):
    return 1.05 / (luminance(colour) + 0.05)


class InteractionBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
        except ImportError as exc:
            raise unittest.SkipTest("Playwright is not installed") from exc
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception as exc:
            cls.playwright.stop()
            raise unittest.SkipTest("Playwright Chromium is not installed") from exc
        cls.temp = tempfile.TemporaryDirectory()
        cls.book = Path(cls.temp.name) / "book.html"
        cls.book.write_text(build.render(EXAMPLE))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.contexts = []

    def tearDown(self):
        for context in self.contexts:
            context.close()

    def open_page(self, fragment="", phone=False, reduced=True, init_script=None):
        options: dict = {"viewport": {"width": 390, "height": 844} if phone else {"width": 1440, "height": 900}}
        if phone:
            options.update({"has_touch": True, "is_mobile": True})
        if reduced:
            options["reduced_motion"] = "reduce"
        context = self.browser.new_context(**options)
        self.contexts.append(context)
        if init_script:
            context.add_init_script(init_script)
        page = context.new_page()
        page.goto(self.book.as_uri() + fragment)
        page.wait_for_function("window.__book || window.__storyboard")
        return page

    @staticmethod
    def dispatch_drag(page, selector, start, moves, pointer_id):
        page.dispatch_event(selector, "pointerdown", {"pointerId": pointer_id, "clientX": start[0], "clientY": start[1], "bubbles": True})
        for x, y in moves:
            page.dispatch_event(selector, "pointermove", {"pointerId": pointer_id, "clientX": x, "clientY": y, "bubbles": True})
        page.dispatch_event(selector, "pointerup", {"pointerId": pointer_id, "clientX": moves[-1][0], "clientY": moves[-1][1], "bubbles": True})

    def test_flap_follows_signed_drag_and_escape_closes_it(self):
        page = self.open_page("#ch1")
        flap = page.locator(".lflap")
        box = flap.bounding_box()
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        self.dispatch_drag(page, ".lflap", (x, y), [(x, y + box["height"] * 0.6)], 11)
        self.assertAlmostEqual(float(page.locator(".lesson").evaluate("el => getComputedStyle(el).getPropertyValue('--flap')")), 0, places=3)
        self.assertEqual(flap.get_attribute("aria-expanded"), "false")

        def pointer_y(value):
            return y + box["height"] * (math.cos(math.radians(82) * value) - 1)

        page.dispatch_event(".lflap", "pointerdown", {"pointerId": 12, "clientX": x, "clientY": y, "bubbles": True})
        page.dispatch_event(".lflap", "pointermove", {"pointerId": 12, "clientX": x, "clientY": pointer_y(0.7), "bubbles": True})
        opened = float(page.locator(".lesson").evaluate("el => getComputedStyle(el).getPropertyValue('--flap')"))
        page.dispatch_event(".lflap", "pointermove", {"pointerId": 12, "clientX": x, "clientY": pointer_y(0.25), "bubbles": True})
        reversed_value = float(page.locator(".lesson").evaluate("el => getComputedStyle(el).getPropertyValue('--flap')"))
        self.assertAlmostEqual(opened, 0.7, delta=0.03)
        self.assertAlmostEqual(reversed_value, 0.25, delta=0.03)
        page.dispatch_event(".lflap", "pointerup", {"pointerId": 12, "clientX": x, "clientY": pointer_y(0.25), "bubbles": True})
        self.assertEqual(flap.get_attribute("aria-expanded"), "false")

        flap.focus()
        page.keyboard.press("Enter")
        self.assertEqual(flap.get_attribute("aria-expanded"), "true")
        page.keyboard.press("Escape")
        self.assertEqual(flap.get_attribute("aria-expanded"), "false")

    def test_booklet_is_modal_traps_focus_and_returns_it(self):
        page = self.open_page("#ch1")
        trigger = page.locator("[data-facts]")
        trigger.click()
        dialog = page.locator(".bk-wrap")
        self.assertEqual(dialog.get_attribute("role"), "dialog")
        self.assertEqual(dialog.get_attribute("aria-modal"), "true")

        page.locator(".bk-close").focus()
        page.keyboard.press("Tab")
        self.assertTrue(page.locator(".bk-wrap").evaluate("el => el.contains(document.activeElement)"))
        page.keyboard.press("Shift+Tab")
        self.assertTrue(page.locator(".bk-wrap").evaluate("el => el.contains(document.activeElement)"))

        page.keyboard.press("Escape")
        self.assertEqual(dialog.count(), 0)
        self.assertTrue(trigger.evaluate("el => document.activeElement === el"))

    def test_reduced_motion_keeps_sound_toggle_truthful(self):
        page = self.open_page(reduced=True, init_script=FAKE_AUDIO)
        sound = page.locator("[data-sound]")
        sound.click()
        self.assertEqual(sound.get_attribute("aria-pressed"), "true")
        self.assertEqual(sound.inner_text(), "Sound on")
        page.locator("[data-open]").click()
        page.wait_for_timeout(50)
        self.assertGreater(page.evaluate("window.__audioContexts"), 0)
        self.assertGreater(page.evaluate("window.__audioStarts"), 0)

    def test_phone_booklet_opens_inside_text_page(self):
        page = self.open_page("#ch1", phone=True)
        left_before = page.locator(".page.left").bounding_box()
        page.locator("[data-facts]").click()
        wrap = page.locator(".bk-wrap")
        left_after = page.locator(".page.left").bounding_box()
        geometry = wrap.evaluate(
            """el => {
              const r=el.getBoundingClientRect(), p=el.closest('.page.left').getBoundingClientRect();
              return {parent:el.parentElement.className, position:getComputedStyle(el).position,
                      background:getComputedStyle(el).backgroundColor,
                      inside:r.left>=p.left-1 && r.right<=p.right+1, directBody:el.parentElement===document.body};
            }"""
        )
        self.assertIn("text", geometry["parent"])
        self.assertEqual(geometry["position"], "relative")
        self.assertIn(geometry["background"], {"rgba(0, 0, 0, 0)", "transparent"})
        self.assertTrue(geometry["inside"])
        self.assertFalse(geometry["directBody"])
        self.assertGreater(left_after["height"], left_before["height"] + 100)
        self.assertTrue(page.locator(".page.right").is_visible())

    def test_cover_surface_opens_book_and_keeps_button(self):
        page = self.open_page()
        button = page.locator("[data-open]")
        self.assertEqual(button.evaluate("el => el.tagName"), "BUTTON")
        page.locator(".cover .hero").click()
        page.wait_for_function("window.__book.cur() === 1")
        self.assertEqual(page.evaluate("window.__book.cur()"), 1)

    def test_phone_cues_are_printed_and_pointer_promise_is_hidden(self):
        page = self.open_page("#contents", phone=True)
        self.assertTrue(page.locator(".phone-page-cues").is_visible())
        self.assertTrue(page.locator("[data-stage-prev]").is_visible())
        self.assertTrue(page.locator("[data-stage-next]").is_visible())
        self.assertTrue(page.locator("[data-swipe-hint]").is_visible())
        self.assertEqual(page.locator(".stage-hint").evaluate("el => getComputedStyle(el).display"), "none")
        page.locator("[data-stage-next]").click()
        page.wait_for_function("window.__book.cur() === 2")
        page.wait_for_timeout(100)
        page.evaluate("window.__book.go(1)")
        page.wait_for_function("window.__book.cur() === 1")
        self.assertFalse(page.locator("[data-swipe-hint]").is_visible())

    def test_page_announcer_surface_escaping_and_storyboard_filters(self):
        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["scene"]["sky"] = 'linear-gradient(red, blue);" onpointerenter="window.__skyPwn=1'
        unsafe = Path(self.temp.name) / "unsafe.html"
        unsafe.write_text(build.render(story))
        context = self.browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        self.contexts.append(context)
        page = context.new_page()
        page.goto(unsafe.as_uri() + "#ch1")
        page.wait_for_function("window.__book")
        self.assertIsNone(page.locator("#app").get_attribute("aria-live"))
        self.assertEqual(page.locator(".nav .where").get_attribute("aria-live"), "polite")
        self.assertIsNone(page.locator(".stage").get_attribute("onpointerenter"))
        self.assertIsNone(page.evaluate("window.__skyPwn"))

        board = self.open_page("#storyboard", phone=True)
        cards = board.locator(".storyboard-card")
        index = board.locator(".storyboard-index button")
        self.assertEqual(index.count(), cards.count())
        self.assertEqual(board.locator(".storyboard-tools").evaluate("el => getComputedStyle(el).position"), "sticky")

        board.locator("[data-story-filter='open']").click()
        visible_open = board.locator(".storyboard-card:visible")
        self.assertGreater(visible_open.count(), 0)
        self.assertTrue(all(visible_open.nth(i).evaluate("el => el.classList.contains('open')") for i in range(visible_open.count())))
        board.locator("[data-story-filter='open']").click()
        board.locator("[data-story-filter='budget']").click()
        visible_budget = board.locator(".storyboard-card:visible")
        self.assertGreater(visible_budget.count(), 0)
        self.assertTrue(all(visible_budget.nth(i).locator(".storyboard-budget.under, .storyboard-budget.over").count() > 0 for i in range(visible_budget.count())))

    def test_orange_controls_meet_normal_text_contrast(self):
        css = (ROOT / "engine" / "book.css").read_text()
        accent_match = re.search(r"--accent:\s*(#[0-9a-fA-F]{6})", css)
        slider_match = re.search(r"\.slider \.tab.*?linear-gradient\(180deg,\s*(#[0-9a-fA-F]{6})", css, re.S)
        self.assertIsNotNone(accent_match)
        self.assertIsNotNone(slider_match)
        accent = accent_match.group(1) if accent_match else "#ffffff"
        slider = slider_match.group(1) if slider_match else "#ffffff"
        self.assertGreaterEqual(white_contrast(accent), 4.5)
        self.assertGreaterEqual(white_contrast(slider), 4.5)


if __name__ == "__main__":
    unittest.main()
