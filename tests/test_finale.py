"""Tests for the optional centre-spread finale."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import build  # noqa: E402
import validate as V  # noqa: E402

EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())


class FinaleValidationTests(unittest.TestCase):
    def test_example_finale_is_valid_without_facts(self):
        errors, _ = V.validate(EXAMPLE)
        self.assertFalse([error for error in errors if "finale" in error])
        self.assertEqual(EXAMPLE["finale"].get("facts", []), [])

    def test_finale_requires_title_text_and_scene(self):
        story = copy.deepcopy(EXAMPLE)
        story["finale"] = {}
        errors, _ = V.validate(story)
        self.assertTrue(any("finale: missing 'title'" in error for error in errors))
        self.assertTrue(any("finale: missing 'text'" in error for error in errors))
        self.assertTrue(any("finale: missing 'scene'" in error for error in errors))

    def test_finale_effects_and_fact_sources_are_checked(self):
        story = copy.deepcopy(EXAMPLE)
        story["finale"]["tab"]["effects"][0]["piece"] = "missing-piece"
        story["finale"]["facts"] = [
            {"label": "A claim", "value": "1", "source": "missing-source"}
        ]
        errors, _ = V.validate(story)
        self.assertTrue(any("finale tab" in error and "missing-piece" in error for error in errors))
        self.assertTrue(any("finale" in error and "missing-source" in error for error in errors))

    def test_finale_requires_a_central_vfold_and_three_cast_tiers(self):
        story = copy.deepcopy(EXAMPLE)
        pieces = story["finale"]["scene"]["pieces"]
        structure = next(piece for piece in pieces if piece.get("finaleRole") == "structure")
        structure["mount"] = "platform"
        for piece in pieces:
            if piece.get("finaleRole") == "cast":
                piece["tier"] = 1
        errors, _ = V.validate(story)
        self.assertTrue(any("central structure" in error for error in errors))
        self.assertTrue(any("at least three tiers" in error for error in errors))

    def test_finale_rejects_unknown_roles_mounts_and_tiers(self):
        story = copy.deepcopy(EXAMPLE)
        piece = story["finale"]["scene"]["pieces"][1]
        piece.update({"finaleRole": "sticker", "mount": "ceiling", "tier": 7})
        errors, _ = V.validate(story)
        self.assertTrue(any("finaleRole" in error for error in errors))
        self.assertTrue(any("mount" in error for error in errors))
        self.assertTrue(any("tier must be 1..4" in error for error in errors))

    def test_finale_cast_shares_one_rising_platform_height_per_tier(self):
        story = copy.deepcopy(EXAMPLE)
        pieces = story["finale"]["scene"]["pieces"]
        cast = [piece for piece in pieces if piece.get("finaleRole") == "cast"]
        cast[0].pop("tier")
        cast[2].update({"tier": 3, "lift": 12})
        errors, _ = V.validate(story)
        self.assertTrue(any("needs a tier" in error for error in errors))
        self.assertTrue(any("share one platform height" in error for error in errors))


class FinaleBuildTests(unittest.TestCase):
    def test_build_contains_finale_screen_storyboard_and_print_views(self):
        html = build.render(EXAMPLE)
        self.assertIn('kind: "finale"', html)
        self.assertIn('data-entry="finale"', html)
        self.assertIn('class="pfin"', html)
        self.assertIn('class="finale-layer"', html)

    def test_finale_fills_desktop_spread_and_phone_stage(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "book.html"
            output.write_text(build.render(EXAMPLE))
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                for viewport, phone in [({"width": 1440, "height": 900}, False), ({"width": 390, "height": 844}, True)]:
                    page = browser.new_page(viewport=viewport)
                    page.emulate_media(reduced_motion="reduce")
                    page.goto(output.as_uri() + "#finale")
                    page.wait_for_selector(".finale-stage")
                    # Wait for the arch to be laid out, not a fixed delay: slower hosts take up to ~2 s.
                    page.wait_for_function(
                        "() => { const s = document.querySelector('.finale-stage'), a = document.querySelector('.finale-role-structure .mech > svg');"
                        " return s && a && a.getBoundingClientRect().height > s.getBoundingClientRect().height * 0.3; }",
                        timeout=8000,
                    )
                    stage = page.locator(".finale-stage").bounding_box()
                    spread = page.locator(".book").bounding_box()
                    self.assertIsNotNone(stage)
                    self.assertIsNotNone(spread)
                    if phone:
                        self.assertGreater(stage["height"], stage["width"])
                    else:
                        self.assertAlmostEqual(stage["x"], spread["x"], delta=2)
                        self.assertAlmostEqual(stage["width"], spread["width"], delta=3)

                    self.assertEqual(page.locator(".finale-role-structure.finale-mount-vfold").count(), 1)
                    self.assertEqual(page.locator(".finale-platform").count(), 3)
                    self.assertEqual(page.locator(".finale-platform-top").count(), 3)
                    self.assertEqual(page.locator(".finale-platform-front").count(), 3)
                    self.assertEqual(page.locator(".finale-wing").count(), 2)
                    self.assertEqual(page.locator(".finale-low-layer").count(), 2)
                    self.assertEqual(page.locator(".finale-banner").count(), 1)
                    tiers = page.locator(".finale-role-cast").evaluate_all(
                        "els => new Set(els.flatMap(el => [...el.classList].filter(c => c.startsWith('finale-tier-')))).size"
                    )
                    self.assertGreaterEqual(tiers, 3)
                    banner = page.locator(".finale-banner").bounding_box()
                    structure = page.locator(".finale-role-structure .mech > svg").bounding_box()
                    self.assertGreaterEqual(banner["y"], stage["y"] + stage["height"] - 1)
                    self.assertGreaterEqual(structure["y"], stage["y"] - 1)
                    self.assertLess(structure["y"], stage["y"] + stage["height"] * 0.12)
                    floor_transform = page.locator(".finale-stage .floor").evaluate(
                        "el => getComputedStyle(el).transform"
                    )
                    self.assertNotEqual(floor_transform, "none")
                    contacts = page.locator(".finale-role-cast").evaluate_all(
                        "els => els.filter(el => +getComputedStyle(el.querySelector('.mech')).opacity > 0.2).map(el => [getComputedStyle(el.querySelector('.foot')).opacity, getComputedStyle(el.querySelector('.shadow')).opacity])"
                    )
                    self.assertTrue(all(float(foot) > 0.5 and float(shadow) > 0.5 for foot, shadow in contacts))
                    for selector in (".finale-banner .tab", ".finale-stage .lflap"):
                        target = page.locator(selector).evaluate(
                            "el => ({width: el.offsetWidth, height: el.offsetHeight})"
                        )
                        self.assertGreaterEqual(target["width"], 44)
                        self.assertGreaterEqual(target["height"], 44)
                    page.close()
                browser.close()

    def test_finale_folds_the_rig_banner_and_structure_with_the_page(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "book.html"
            output.write_text(build.render(EXAMPLE))
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(output.as_uri() + "#finale")
                page.wait_for_selector(".finale-stage")
                delays = page.locator(".finale-role-cast .hinge").evaluate_all(
                    "els => [...new Set(els.map(el => getComputedStyle(el).transitionDelay))]"
                )
                self.assertEqual(delays, ["0s"])
                page.evaluate("""() => {
                  window.__finaleTurn=[];
                  const selectors=['.finale-role-structure .hinge','.finale-wing-left','.finale-platform-front','.finale-role-cast .hinge'];
                  let seen=false;
                  const tick=()=>{
                    const turn=window.__book.turn();
                    if(turn) seen=true;
                    if(turn) window.__finaleTurn.push(selectors.map(selector=>{
                      const element=document.querySelector(selector), style=getComputedStyle(element);
                      return {transform:style.transform,opacity:+style.opacity};
                    }));
                    if(seen&&!turn)return;
                    requestAnimationFrame(tick);
                  };
                  requestAnimationFrame(tick);
                }""")
                page.locator("[data-next]").click()
                page.wait_for_function("window.__book.turn() === null && window.__book.cur() === window.__book.pages().length - 1")
                samples = page.evaluate("window.__finaleTurn")
                self.assertGreaterEqual(len(samples), 6)
                for index in range(4):
                    transforms = {sample[index]["transform"] for sample in samples}
                    self.assertGreaterEqual(len(transforms), 3)
                    self.assertTrue(all(sample[index]["opacity"] == 1 for sample in samples))
                browser.close()


if __name__ == "__main__":
    unittest.main()
