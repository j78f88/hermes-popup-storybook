"""Engine tests: run with  python3 -m unittest discover -s tests"""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import build  # noqa: E402
import validate as V  # noqa: E402

EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())


def errs(story, **kw):
    return V.validate(story, **kw)[0]


class LibraryTests(unittest.TestCase):
    def test_sprites_are_rectangular_and_use_palette(self):
        lib, _ = V.load_library()
        for name, rows in lib["sprites"].items():
            self.assertEqual(len({len(r) for r in rows}), 1, name)
            for r in rows:
                for ch in r:
                    self.assertTrue(ch == "." or ch in lib["palette"], f"{name}: {ch}")

    def test_font_glyphs_are_seven_rows(self):
        _, font = V.load_library()
        for k, g in font["glyphs"].items():
            self.assertEqual(len(g), 7, k)
            self.assertEqual(len({len(r) for r in g}), 1, k)

    def test_library_is_generated_from_sources(self):
        # The JSON library must match its Python sources, so nobody hand-edits it.
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copytree(ROOT / "tools", tmp / "tools")
            (tmp / "engine" / "library").mkdir(parents=True)
            for t in ("sprites_src.py", "font_src.py"):
                subprocess.run([sys.executable, str(tmp / "tools" / t)], check=True, capture_output=True)
            for f in ("sprites.json", "font.json"):
                self.assertEqual((tmp / "engine/library" / f).read_text(), (ROOT / "engine/library" / f).read_text(), f)
        finally:
            shutil.rmtree(tmp)


class ValidateTests(unittest.TestCase):
    def test_example_passes(self):
        e, w = V.validate(EXAMPLE)
        self.assertEqual(e, [])

    def test_unknown_source(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["facts"][0]["source"] = "nope"
        self.assertTrue(any("unknown source 'nope'" in x for x in errs(s)))

    def test_too_few_facts(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["facts"] = s["chapters"][0]["facts"][:1]
        self.assertTrue(any("at least 3 facts" in x for x in errs(s)))

    def test_open_chapter_needs_no_facts(self):
        s = copy.deepcopy(EXAMPLE)
        open_chapter = s["chapters"][-1]
        self.assertEqual(open_chapter["status"], "open")
        self.assertFalse(any(f"chapter {open_chapter['number']}" in x and "facts" in x for x in errs(s)))

    def test_unknown_sprite_and_effect_target(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["scene"]["pieces"][0]["sprite"] = "dragon"
        s["chapters"][0]["tab"]["effects"][0]["piece"] = "ghost"
        e = errs(s)
        self.assertTrue(any("unknown sprite 'dragon'" in x for x in e))
        self.assertTrue(any("unknown piece 'ghost'" in x for x in e))

    def test_move_effect_needs_target(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["flap"]["effects"] = [{"piece": "hero", "fx": "move"}]
        self.assertTrue(any("needs a 'to' object" in x for x in errs(s)))
        s["chapters"][0]["flap"]["effects"] = [{"piece": "hero", "fx": "move", "to": {"x": 140}}]
        self.assertTrue(any("outside 0..100" in x for x in errs(s)))
        s["chapters"][0]["flap"]["effects"] = [{"piece": "hero", "fx": "move", "to": {"x": 40, "lift": 10}}]
        self.assertFalse(any("move" in x for x in errs(s)))

    def test_chapter_numbers_in_order(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][1]["number"] = 5
        self.assertTrue(any(f"run 1..{len(s['chapters'])}" in x for x in errs(s)))

    def test_secret_scan(self):
        cases = [
            "token ghp_" + "a" * 30,
            "key sk-" + "b" * 30,
            "host 100." + "64.1.2",
            "lan 192." + "168.1.20",
            "box.tail1234." + "ts.net",
            "mail someone@example.com",
            "password: hunter2hunter2",
        ]
        for text in cases:
            s = copy.deepcopy(EXAMPLE)
            s["chapters"][0]["text"] = [text]
            self.assertTrue(any("possible" in x for x in errs(s)), text)

    def test_deny_terms(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["text"] = ["We met Acme Widgets today."]
        self.assertTrue(any("denied term" in x for x in errs(s, deny_terms=["acme widgets"])))

    def test_custom_sprite_validation(self):
        s = copy.deepcopy(EXAMPLE)
        s["sprites"] = {"blob": ["kk", "k"]}
        self.assertTrue(any("same length" in x for x in errs(s)))
        s["sprites"] = {"blob": ["kQ", "kk"]}
        self.assertTrue(any("unknown palette keys" in x for x in errs(s)))

    def test_nearby_hide_show_windows_must_be_staggered(self):
        story = copy.deepcopy(EXAMPLE)
        chapter = story["chapters"][0]
        chapter["scene"]["pieces"].extend([
            {"id": "old", "sprite": "box", "x": 50},
            {"id": "new", "sprite": "book_closed", "x": 54, "depth": 2, "hidden": True},
        ])
        chapter["tab"]["effects"] = [
            {"piece": "old", "fx": "hide", "at": [0.2, 0.6]},
            {"piece": "new", "fx": "show", "at": [0.4, 0.8]},
        ]
        warnings = V.validate(story)[1]
        self.assertTrue(
            any("stagger hide 'old' before show 'new'" in item for item in warnings),
            warnings,
        )

        chapter["tab"]["effects"] = [
            {"piece": "old", "fx": "hide", "at": [0.2, 0.4]},
            {"piece": "new", "fx": "show", "at": [0.4, 0.8]},
        ]
        self.assertFalse(
            any("stagger hide 'old' before show 'new'" in item for item in V.validate(story)[1])
        )

    def test_setting_balance_warns_on_repeated_setting_not_recurring_characters(self):
        story = copy.deepcopy(EXAMPLE)
        base = copy.deepcopy(story["chapters"][0])
        story["chapters"] = []
        for idx in range(1, 5):
            ch = copy.deepcopy(base)
            ch["number"] = idx
            ch["scene"]["sky"] = ["dawn", "day", "dusk", "night"][idx - 1]
            ch["scene"]["ground"] = ["grass", "wood", "stone", "carpet"][idx - 1]
            ch["scene"]["wall"] = []
            ch["scene"]["pieces"] = [
                {"id": "bg", "sprite": "workbench", "x": 30, "depth": 4, "scale": 3},
                {"id": "hero", "sprite": "robot", "x": 70, "depth": 3, "scale": 2.5},
            ]
            ch["tab"]["effects"] = [{"piece": "hero", "fx": "hop", "at": [0.1, 0.8]}]
            ch["flap"]["effects"] = [{"piece": "hero", "fx": "move", "to": {"x": 55}, "at": [0.1, 0.8]}]
            story["chapters"].append(ch)
        warnings = V.validate(story)[1]
        self.assertTrue(any("setting sprite 'workbench' repeats" in w for w in warnings), warnings)
        self.assertFalse(any("setting sprite 'robot' repeats" in w for w in warnings), warnings)

    def test_complexity_and_motion_guards_warn_on_clutter_and_static_tabs(self):
        story = copy.deepcopy(EXAMPLE)
        ch = story["chapters"][0]
        ch["scene"]["pieces"] = [
            {"id": f"p{i}", "sprite": "paper", "x": 10 + i * 7, "depth": 1, "scale": 1.5}
            for i in range(10)
        ]
        ch["tab"]["effects"] = [{"piece": "p0", "fx": "show", "at": [0.1, 0.9]}]
        warnings = V.validate(story)[1]
        self.assertTrue(any("10 floor pieces" in w for w in warnings), warnings)
        self.assertTrue(any("only static show/hide" in w for w in warnings), warnings)

    def test_image_validation_checks_data_uri_size_and_exif(self):
        story = copy.deepcopy(EXAMPLE)
        story["images"] = {
            "bad_scheme": {"src": "https://example.com/a.png", "width": 80, "height": 80, "source": "arrival-example"},
            "huge_img": {"src": "data:image/png;base64," + ("A" * 260000), "width": 80, "height": 80, "source": "arrival-example"},
        }
        errors, _ = V.validate(story)
        self.assertTrue(any("must be an offline data:image/" in e for e in errors), errors)
        self.assertTrue(any("exceeds 180 KB" in e for e in errors), errors)


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build.render(EXAMPLE)

    def test_single_file_no_external_fetches(self):
        self.assertNotRegex(self.html, r"""(?:src|href)\s*=\s*["']https?://""")
        self.assertNotIn("@import", self.html)
        self.assertNotRegex(self.html, r"url\(\s*['\"]?https?://")

    def test_story_payload_cannot_close_script(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["text"] = ["</script><script>alert(1)</script>"]
        html = build.render(s)
        payload = html.split('<script id="story" type="application/json">')[1].split("</script>")[0]
        self.assertIn("<\\/script>", payload)
        json.loads(payload.replace("<\\/", "</"))

    def test_placeholders_filled(self):
        self.assertNotRegex(self.html, r"\{\{(css|js|story|title|lang|version)\}\}")

    def test_engine_js_parses(self):
        if not shutil.which("node"):
            self.skipTest("node not installed")
        js = self.html.split("<script>\n", 1)[1].rsplit("</script>", 1)[0]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(js)
        try:
            r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            Path(f.name).unlink()

    def test_engine_runs_in_a_fake_dom(self):
        """Smoke-run the engine's pure helpers under node with a tiny DOM stub."""
        if not shutil.which("node"):
            self.skipTest("node not installed")
        js = (ROOT / "engine" / "book.js").read_text()
        # Expose helpers by intercepting start(): stub a DOM just rich enough for shell() and paint().
        harness = r"""
const store = {};
function el(tag){ const e={tag, children:[], style:{setProperty(){}, }, dataset:{}, classList:{_s:new Set(),add(...c){c.forEach(x=>this._s.add(x))},remove(...c){c.forEach(x=>this._s.delete(x))},toggle(c,on){on===undefined?(this._s.has(c)?this._s.delete(c):this._s.add(c)):(on?this._s.add(c):this._s.delete(c))},contains(c){return this._s.has(c)}},
  _html:'', set innerHTML(v){this._html=v}, get innerHTML(){return this._html}, textContent:'', setAttribute(){}, getAttribute(){return null}, addEventListener(){}, appendChild(c){this.children.push(c)},
  querySelector(){return el('x')}, querySelectorAll(){return []}, closest(){return null}, clientHeight:600, clientWidth:500, scrollHeight:0, focus(){}, getBoundingClientRect(){return {left:0,top:0,width:500,height:600}} }; return e; }
const storyEl = el('script'); storyEl.textContent = STORY;
global.document = { getElementById: (id) => id==='story'? storyEl : el(id), querySelector: () => el('q'), querySelectorAll: () => [], createElement: el, body: el('body'), addEventListener(){}, documentElement: el('html'), title:'' };
global.window = global; global.innerWidth = 1440; global.innerHeight = 900; global.scrollY = 0; global.location = {hash:'#ch1'}; global.history = {replaceState(){}};
global.matchMedia = () => ({matches:false}); global.getComputedStyle = () => ({ paddingRight: "0px", getPropertyValue() { return ""; } }); global.localStorage = {getItem(){return null}, setItem(){}}; global.addEventListener = () => {}; global.requestAnimationFrame = (f) => 0; global.cancelAnimationFrame = () => {}; global.CSS = {escape: (s)=>s};
"""
        story = build.render(EXAMPLE).split('<script id="story" type="application/json">')[1].split("</script>")[0]
        code = harness.replace("STORY", json.dumps(story.replace("<\\/", "</"))) + js + "\nconsole.log(JSON.stringify(window.__book.pages()));"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(code)
        try:
            r = subprocess.run(["node", f.name], capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            expected_pages = ["cover", "contents"] + [f"ch{c['number']}" for c in EXAMPLE["chapters"]] + ["numbers", "finale", "back"]
            self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), expected_pages)
        finally:
            Path(f.name).unlink()

    def test_cli_refuses_invalid_story(self):
        s = copy.deepcopy(EXAMPLE)
        s["chapters"][0]["facts"] = []
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "story.json"
            p.write_text(json.dumps(s))
            out = Path(d) / "out.html"
            r = subprocess.run([sys.executable, str(ROOT / "engine/build.py"), str(p), "-o", str(out)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
