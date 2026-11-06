import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())

spec = importlib.util.spec_from_file_location("validate", ROOT / "engine" / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)
spec = importlib.util.spec_from_file_location("build", ROOT / "engine" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

INSTRUMENT_AUDIO = r"""
(() => {
  const log = window.__audioLog = [];
  let nextId = 0;
  const record = (op, data = {}) => log.push(Object.assign({op, wall: performance.now()}, data));
  class FakeParam {
    constructor(name, node) { this.name = name; this.node = node; this._value = 0; }
    set value(v) { this._value = v; record('value', {node: this.node.id, type: this.node.kind, param: this.name, value: v}); }
    get value() { return this._value; }
    setValueAtTime(v, at) { this._value = v; record('set', {node: this.node.id, type: this.node.kind, param: this.name, value: v, at}); }
    linearRampToValueAtTime(v, at) { this._value = v; record('linear', {node: this.node.id, type: this.node.kind, param: this.name, value: v, at}); }
    exponentialRampToValueAtTime(v, at) { this._value = v; record('exponential', {node: this.node.id, type: this.node.kind, param: this.name, value: v, at}); }
    setTargetAtTime(v, at, constant) { this._value = v; record('target', {node: this.node.id, type: this.node.kind, param: this.name, value: v, at, constant}); }
    cancelScheduledValues(at) { record('cancel', {node: this.node.id, type: this.node.kind, param: this.name, at}); }
  }
  class FakeNode {
    constructor(kind) { this.kind = kind; this.id = ++nextId; record('create', {node: this.id, type: kind}); }
    connect(to) { record('connect', {node: this.id, type: this.kind, to: to && to.id}); return to; }
  }
  class FakeGain extends FakeNode { constructor() { super('gain'); this.gain = new FakeParam('gain', this); } }
  class FakeFilter extends FakeNode { constructor() { super('filter'); this.frequency = new FakeParam('frequency', this); this.Q = new FakeParam('Q', this); } }
  class FakeSource extends FakeNode {
    constructor() { super('buffer'); this.playbackRate = new FakeParam('playbackRate', this); this.loop = false; }
    start(at = 0) { record('start', {node: this.id, type: this.kind, at}); }
    stop(at = 0) { record('stop', {node: this.id, type: this.kind, at}); }
  }
  class FakeOscillator extends FakeNode {
    constructor() { super('oscillator'); this.frequency = new FakeParam('frequency', this); }
    start(at = 0) { record('start', {node: this.id, type: this.kind, at}); }
    stop(at = 0) { record('stop', {node: this.id, type: this.kind, at}); }
  }
  class FakeAudioContext {
    constructor() { this.sampleRate = 48000; this.state = 'suspended'; this.destination = new FakeNode('destination'); record('context'); }
    get currentTime() { return performance.now() / 1000; }
    createGain() { return new FakeGain(); }
    createBufferSource() { return new FakeSource(); }
    createBiquadFilter() { return new FakeFilter(); }
    createOscillator() { return new FakeOscillator(); }
    createBuffer(channels, length) { return {getChannelData: () => new Float32Array(length)}; }
    resume() { this.state = 'running'; record('resume'); return Promise.resolve(); }
  }
  window.AudioContext = FakeAudioContext;
  window.webkitAudioContext = undefined;
})();
"""


class SoundValidationTests(unittest.TestCase):
    def test_optional_volume_accepts_only_numbers_from_zero_to_one(self):
        for value in (0, 0.4, 1):
            story = copy.deepcopy(EXAMPLE)
            story["sound"] = {"volume": value}
            self.assertFalse(any("sound.volume" in e for e in validate.validate(story)[0]))
        for value in (-0.01, 1.01, True, "quiet", None):
            story = copy.deepcopy(EXAMPLE)
            story["sound"] = {"volume": value}
            self.assertTrue(any("sound.volume" in e for e in validate.validate(story)[0]), value)
        story = copy.deepcopy(EXAMPLE)
        story["sound"] = "loud"
        self.assertTrue(any("'sound' must be an object" in e for e in validate.validate(story)[0]))

    def test_sound_frequency_ceilings_are_named(self):
        source = (ROOT / "engine" / "book.js").read_text(encoding="utf-8")
        self.assertIn("oneShotHz: 2800", source)
        self.assertIn("repeatedHz: 2200", source)
        self.assertIn("movementHz: 2600", source)


class SoundBrowserTests(unittest.TestCase):
    def setUp(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")
        self.sync_playwright = sync_playwright
        self.temp = tempfile.TemporaryDirectory()
        story = copy.deepcopy(EXAMPLE)
        story["sound"] = {"volume": 0.37}
        self.book = Path(self.temp.name) / "book.html"
        self.book.write_text(build.render(story))

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def starts(log, kind=None):
        return [e for e in log if e.get("op") == "start" and (kind is None or e.get("type") == kind)]

    @staticmethod
    def drag_to(page, selector, fraction, pause_ms=40, pointer_id=7):
        state = page.eval_on_selector(
            selector,
            """(el, fraction) => {
              const slider = el.closest('[data-pull]');
              const track = slider.querySelector('.track').getBoundingClientRect();
              const tab = el.getBoundingClientRect();
              const current = +(el.getAttribute('aria-valuenow') || 0) / 100;
              return {x: tab.left + tab.width / 2, y: tab.top + tab.height / 2,
                      target: tab.left + tab.width / 2 + (fraction - current) * (track.width - tab.width)};
            }""",
            fraction,
        )
        page.dispatch_event(selector, "pointerdown", {"pointerId": pointer_id, "clientX": state["x"], "clientY": state["y"], "bubbles": True})
        page.wait_for_timeout(pause_ms)
        page.dispatch_event(selector, "pointermove", {"pointerId": pointer_id, "clientX": state["target"], "clientY": state["y"], "bubbles": True})
        page.wait_for_timeout(20)
        page.dispatch_event(selector, "pointerup", {"pointerId": pointer_id, "clientX": state["target"], "clientY": state["y"], "bubbles": True})

    def test_sounds_follow_mechanisms_and_toggle(self):
        errors = []
        metrics = {}
        try:
            with self.sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                context.add_init_script(INSTRUMENT_AUDIO)
                page = context.new_page()
                page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(self.book.as_uri())

                page.locator("[data-open]").click()
                page.wait_for_timeout(800)
                self.assertEqual(page.evaluate("window.__audioLog.filter(x => x.op === 'context').length"), 0)
                metrics["starts_before_toggle"] = len(self.starts(page.evaluate("window.__audioLog")))
                self.assertEqual(metrics["starts_before_toggle"], 0)

                page.locator("[data-sound]").click()
                self.assertEqual(page.evaluate("window.__audioLog.filter(x => x.op === 'context').length"), 0)
                page.evaluate("window.__audioLog.length = 0")

                page.locator("[data-next]").click()
                page.wait_for_timeout(80)
                early = page.evaluate("window.__audioLog")
                metrics["page_turn_noise_starts"] = len(self.starts(early, "buffer"))
                self.assertGreaterEqual(metrics["page_turn_noise_starts"], 3)
                page.wait_for_timeout(1000)
                after_rise = page.evaluate("window.__audioLog")
                metrics["rise_pop_starts"] = len(self.starts(after_rise, "oscillator"))
                self.assertGreater(metrics["rise_pop_starts"], 0)
                master_values = [e["value"] for e in after_rise if e.get("op") == "value" and e.get("type") == "gain"]
                self.assertIn(0.37, master_values)
                metrics["story_volume"] = 0.37

                page.evaluate("window.__audioLog.length = 0")
                tab = ".tab"
                box = page.locator(tab).bounding_box()
                page.dispatch_event(tab, "pointerdown", {"pointerId": 11, "clientX": box["x"] + box["width"] / 2, "clientY": box["y"] + box["height"] / 2, "bubbles": True})
                page.wait_for_timeout(120)
                page.dispatch_event(tab, "pointermove", {"pointerId": 11, "clientX": box["x"] + box["width"] / 2 + 12, "clientY": box["y"] + box["height"] / 2, "bubbles": True})
                page.wait_for_timeout(135)
                slow_log = page.evaluate("window.__audioLog")
                slow_targets = [e for e in slow_log if e.get("op") == "target" and e.get("param") == "gain" and e.get("value", 0) > 0.001]
                slow_freqs = [e["value"] for e in slow_log if e.get("op") == "target" and e.get("param") == "frequency"]
                zero_targets = [e for e in slow_log if e.get("op") == "target" and e.get("param") == "gain" and e.get("value") == 0.0001]
                self.assertTrue(slow_targets and slow_freqs and zero_targets)
                metrics["slow_scrape_gain"] = max(e["value"] for e in slow_targets)
                metrics["slow_scrape_hz"] = max(slow_freqs)
                move_wall = slow_targets[-1]["wall"]
                stopped = next(e for e in zero_targets if e["wall"] >= move_wall)
                metrics["scrape_silence_ms"] = round(stopped["wall"] - move_wall, 1)
                self.assertGreaterEqual(metrics["scrape_silence_ms"], 0)
                self.assertLessEqual(metrics["scrape_silence_ms"], 150)
                page.dispatch_event(tab, "pointerup", {"pointerId": 11, "clientX": box["x"] + box["width"] / 2 + 12, "clientY": box["y"] + box["height"] / 2, "bubbles": True})

                page.evaluate("window.__audioLog.length = 0")
                box = page.locator(tab).bounding_box()
                page.dispatch_event(tab, "pointerdown", {"pointerId": 12, "clientX": box["x"] + box["width"] / 2, "clientY": box["y"] + box["height"] / 2, "bubbles": True})
                page.wait_for_timeout(8)
                page.dispatch_event(tab, "pointermove", {"pointerId": 12, "clientX": box["x"] + box["width"] / 2 + 40, "clientY": box["y"] + box["height"] / 2, "bubbles": True})
                page.wait_for_timeout(20)
                fast_log = page.evaluate("window.__audioLog")
                fast_targets = [e["value"] for e in fast_log if e.get("op") == "target" and e.get("param") == "gain" and e.get("value", 0) > 0.001]
                fast_freqs = [e["value"] for e in fast_log if e.get("op") == "target" and e.get("param") == "frequency"]
                metrics["fast_scrape_gain"] = max(fast_targets)
                metrics["fast_scrape_hz"] = max(fast_freqs)
                self.assertGreater(metrics["fast_scrape_gain"], metrics["slow_scrape_gain"])
                self.assertGreater(metrics["fast_scrape_hz"], metrics["slow_scrape_hz"])
                self.assertLessEqual(metrics["fast_scrape_hz"], 2600)
                page.dispatch_event(tab, "pointerup", {"pointerId": 12, "clientX": box["x"] + box["width"] / 2 + 40, "clientY": box["y"] + box["height"] / 2, "bubbles": True})

                self.drag_to(page, tab, 0, 20, 20)
                self.drag_to(page, tab, 0.2, 30, 21)
                crossings = []
                for pointer_id, fraction in ((22, 0.45), (23, 0.2), (24, 0.45)):
                    page.evaluate("window.__audioLog.length = 0")
                    self.drag_to(page, tab, fraction, 30, pointer_id)
                    crossings.append(len(self.starts(page.evaluate("window.__audioLog"), "oscillator")))
                metrics["piece_snap_crossings"] = crossings
                self.assertEqual(crossings, [1, 1, 1])

                page.evaluate("window.__audioLog.length = 0")
                page.locator(tab).click()
                page.wait_for_timeout(1200)
                click_log = page.evaluate("window.__audioLog")
                click_freqs = [
                    e["value"]
                    for e in click_log
                    if e.get("op") == "value" and e.get("type") == "filter" and e.get("param") == "frequency"
                ]
                self.assertTrue(click_freqs)
                self.assertLessEqual(max(click_freqs), 2200)
                metrics["click_pull_noise_starts"] = len(self.starts(click_log, "buffer"))
                metrics["end_tap_starts"] = len(self.starts(click_log, "oscillator"))
                self.assertGreaterEqual(metrics["click_pull_noise_starts"], 1)
                self.assertGreaterEqual(metrics["end_tap_starts"], 1)

                page.evaluate("window.__audioLog.length = 0")
                page.locator(".lflap").click()
                page.wait_for_timeout(950)
                flap_open = page.evaluate("window.__audioLog")
                self.assertTrue(self.starts(flap_open, "buffer") and self.starts(flap_open, "oscillator"))
                page.evaluate("window.__audioLog.length = 0")
                page.locator(".lesson-card").click()
                page.wait_for_timeout(950)
                flap_close = page.evaluate("window.__audioLog")
                self.assertTrue(self.starts(flap_close, "buffer") and self.starts(flap_close, "oscillator"))
                metrics["flap_open_starts"] = len(self.starts(flap_open))
                metrics["flap_close_starts"] = len(self.starts(flap_close))

                page.evaluate("window.__audioLog.length = 0")
                flap_box = page.locator(".lflap").bounding_box()
                fx, fy = flap_box["x"] + flap_box["width"] / 2, flap_box["y"] + flap_box["height"] / 2
                page.dispatch_event(".lflap", "pointerdown", {"pointerId": 41, "clientX": fx, "clientY": fy, "bubbles": True})
                page.wait_for_timeout(120)
                page.dispatch_event(".lflap", "pointermove", {"pointerId": 41, "clientX": fx, "clientY": fy + 10, "bubbles": True})
                page.wait_for_timeout(20)
                flap_slow_log = page.evaluate("window.__audioLog")
                page.dispatch_event(".lflap", "pointerup", {"pointerId": 41, "clientX": fx, "clientY": fy + 10, "bubbles": True})
                page.wait_for_timeout(700)
                page.evaluate("window.__audioLog.length = 0")
                flap_box = page.locator(".lflap").bounding_box()
                fx, fy = flap_box["x"] + flap_box["width"] / 2, flap_box["y"] + flap_box["height"] / 2
                page.dispatch_event(".lflap", "pointerdown", {"pointerId": 42, "clientX": fx, "clientY": fy, "bubbles": True})
                page.wait_for_timeout(8)
                page.dispatch_event(".lflap", "pointermove", {"pointerId": 42, "clientX": fx, "clientY": fy + 60, "bubbles": True})
                page.wait_for_timeout(20)
                flap_fast_log = page.evaluate("window.__audioLog")
                page.dispatch_event(".lflap", "pointerup", {"pointerId": 42, "clientX": fx, "clientY": fy + 60, "bubbles": True})
                flap_slow_gain = max(e["value"] for e in flap_slow_log if e.get("op") == "target" and e.get("param") == "gain" and e.get("value", 0) > 0.001)
                flap_fast_gain = max(e["value"] for e in flap_fast_log if e.get("op") == "target" and e.get("param") == "gain" and e.get("value", 0) > 0.001)
                metrics["slow_flap_swish_gain"] = flap_slow_gain
                metrics["fast_flap_swish_gain"] = flap_fast_gain
                self.assertGreater(flap_fast_gain, flap_slow_gain)
                page.wait_for_timeout(700)
                if page.locator(".lesson").evaluate("el => el.classList.contains('up')"):
                    page.locator(".lesson-card").click()
                    page.wait_for_timeout(950)

                page.evaluate("window.__audioLog.length = 0")
                page.locator("[data-facts]").click()
                page.wait_for_timeout(50)
                opened = page.evaluate("window.__audioLog")
                self.assertTrue(self.starts(opened, "buffer") and self.starts(opened, "oscillator"))
                page.evaluate("window.__audioLog.length = 0")
                page.locator("[data-bk='1']").click()
                page.wait_for_timeout(600)
                riffle = page.evaluate("window.__audioLog")
                riffle_freqs = [
                    e["value"]
                    for e in riffle
                    if e.get("op") == "value" and e.get("type") == "filter" and e.get("param") == "frequency"
                ]
                self.assertTrue(riffle_freqs)
                self.assertLessEqual(max(riffle_freqs), 2200)
                self.assertGreaterEqual(len(self.starts(riffle, "buffer")), 2)
                page.evaluate("window.__audioLog.length = 0")
                page.locator(".bk-close").click()
                closed = page.evaluate("window.__audioLog")
                self.assertTrue(self.starts(closed, "buffer") and self.starts(closed, "oscillator"))
                metrics["booklet_open_starts"] = len(self.starts(opened))
                metrics["booklet_riffle_starts"] = len(self.starts(riffle))
                metrics["booklet_close_starts"] = len(self.starts(closed))

                numbers_index = page.evaluate("window.__book.pages().indexOf('numbers')")
                page.evaluate("i => window.__book.go(i)", numbers_index)
                page.wait_for_timeout(1000)
                wheel = page.locator("[data-wheel]").bounding_box()
                cx, cy = wheel["x"] + wheel["width"] / 2, wheel["y"] + wheel["height"] / 2
                radius = wheel["width"] * 0.35
                page.evaluate("window.__audioLog.length = 0")
                page.dispatch_event("[data-wheel]", "pointerdown", {"pointerId": 31, "clientX": cx + radius, "clientY": cy, "bubbles": True})
                page.dispatch_event("[data-wheel]", "pointermove", {"pointerId": 31, "clientX": cx, "clientY": cy + radius, "bubbles": True})
                page.dispatch_event("[data-wheel]", "pointermove", {"pointerId": 31, "clientX": cx - radius, "clientY": cy, "bubbles": True})
                page.dispatch_event("[data-wheel]", "pointerup", {"pointerId": 31, "clientX": cx - radius, "clientY": cy, "bubbles": True})
                wheel_log = page.evaluate("window.__audioLog")
                wheel_freqs = [
                    e["value"]
                    for e in wheel_log
                    if e.get("op") == "value" and e.get("type") == "filter" and e.get("param") == "frequency"
                ]
                self.assertTrue(wheel_freqs)
                self.assertLessEqual(max(wheel_freqs), 2200)
                metrics["wheel_detents_passed"] = 2
                metrics["wheel_clicks"] = len(self.starts(wheel_log, "oscillator"))
                self.assertEqual(metrics["wheel_clicks"], metrics["wheel_detents_passed"])

                page.locator("[data-sound]").click()
                page.evaluate("window.__audioLog.length = 0")
                page.locator("[data-spin='1']").click()
                page.locator("[data-prev]").click()
                page.wait_for_timeout(800)
                metrics["starts_after_toggle_off"] = len(self.starts(page.evaluate("window.__audioLog")))
                self.assertEqual(metrics["starts_after_toggle_off"], 0)
                self.assertEqual(errors, [])
                metrics["console_errors"] = len(errors)
                print("SOUND_METRICS " + json.dumps(metrics, sort_keys=True))
                browser.close()
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                self.skipTest("Playwright Chromium is not installed")
            raise

    def test_missing_web_audio_never_throws(self):
        errors = []
        try:
            with self.sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                context.add_init_script("delete window.AudioContext; delete window.webkitAudioContext;")
                page = context.new_page()
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(self.book.as_uri())
                page.locator("[data-sound]").click()
                page.locator("[data-open]").click()
                page.wait_for_timeout(800)
                page.locator("[data-next]").click()
                page.wait_for_timeout(800)
                self.assertEqual(errors, [])
                browser.close()
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                self.skipTest("Playwright Chromium is not installed")
            raise


if __name__ == "__main__":
    unittest.main()
