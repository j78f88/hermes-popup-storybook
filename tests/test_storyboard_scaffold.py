"""Tests for the story scaffold and storyboard view."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TOOL = ROOT / "tools" / "new_story.py"
VALIDATOR = ROOT / "engine" / "validate.py"
BUILD = ROOT / "engine" / "build.py"
EXAMPLE = ROOT / "stories" / "example" / "story.json"


class StoryScaffoldTests(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOL), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_creates_process_files_and_strict_valid_story(self):
        with tempfile.TemporaryDirectory() as tmp:
            stories = Path(tmp) / "stories"
            result = self.run_tool(
                "quiet-garden",
                "--dir",
                stories,
                "--title",
                "The Quiet Garden",
                "--pages",
                "2",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            target = stories / "quiet-garden"
            expected = {
                "brief.md",
                "sources.md",
                "outline.md",
                "storyboard.md",
                "research/fact-ledger.schema.json",
                "research/ledger-template.json",
                "page-checklist.md",
                "owner-review.md",
                "qa-log.md",
                "README.md",
                "story.json",
            }
            actual = {
                str(path.relative_to(target))
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertTrue(expected <= actual)

            copies = {
                "brief.md": "brief.md",
                "sources.md": "sources.md",
                "outline.md": "outline.md",
                "storyboard.md": "storyboard.md",
                "research/fact-ledger.schema.json": "fact-ledger.schema.json",
                "research/ledger-template.json": "ledger-template.json",
                "page-checklist.md": "page-checklist.md",
                "owner-review.md": "owner-review.md",
                "qa-log.md": "qa-log.md",
            }
            for destination, template in copies.items():
                self.assertEqual(
                    (target / destination).read_text(),
                    (ROOT / "templates" / template).read_text(),
                )

            story = json.loads((target / "story.json").read_text())
            self.assertEqual(story["title"], "The Quiet Garden")
            self.assertEqual(len(story["chapters"]), 2)
            self.assertEqual([page["number"] for page in story["chapters"]], [1, 2])
            self.assertEqual([page["status"] for page in story["chapters"]], ["written", "open"])
            starter = story["chapters"][0]
            self.assertEqual(len(starter["facts"]), 3)
            self.assertEqual(starter["tab"]["effects"][0]["fx"], "move")
            self.assertEqual(starter["flap"]["effects"][0]["fx"], "move")
            self.assertTrue({"contents", "numbers", "back"} <= story.keys())

            validation = subprocess.run(
                [sys.executable, str(VALIDATOR), target / "story.json", "--strict"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            self.assertIn("PASS: 2 chapters", validation.stdout)
            self.assertIn("Work order", result.stdout)
            for step in range(1, 13):
                self.assertIn(f"{step}.", result.stdout)
            for command in (
                "tools/check_ledger.py",
                "engine/validate.py",
                "engine/build.py",
                "tools/check_layout.py dist/quiet-garden/index.html --phone",
                "tools/check_mechanics.py dist/quiet-garden/index.html --phone",
                "tools/shoot.py dist/quiet-garden/index.html -o shots/quiet-garden --phone",
                "tools/shoot.py dist/quiet-garden/index.html -o shots/quiet-garden --poster-only --poster-page 1",
                "tools/export_pdf.py dist/quiet-garden/index.html",
                "tools/release_check.py",
            ):
                self.assertIn(command, result.stdout)

    def test_work_order_commands_exist_and_support_help(self):
        import re
        import tools.new_story as new_story

        order = new_story.work_order(Path("stories/demo/story.json"), "demo")
        scripts = re.findall(r"python3\s+((?:tools|engine)/[A-Za-z0-9_.-]+\.py)", order)
        expected = {
            "tools/check_ledger.py",
            "engine/validate.py",
            "engine/build.py",
            "tools/check_layout.py",
            "tools/check_mechanics.py",
            "tools/shoot.py",
            "tools/export_pdf.py",
            "tools/release_check.py",
        }
        self.assertEqual(set(scripts), expected)
        for rel in sorted(set(scripts)):
            script_path = ROOT / rel
            self.assertTrue(script_path.is_file(), f"missing {rel}")
            help_run = subprocess.run(
                [sys.executable, str(script_path), "--help"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(help_run.returncode, 0, help_run.stderr)

    def test_refuses_to_overwrite_an_existing_story(self):
        with tempfile.TemporaryDirectory() as tmp:
            stories = Path(tmp) / "stories"
            target = stories / "existing"
            target.mkdir(parents=True)
            marker = target / "keep.txt"
            marker.write_text("keep me")

            result = self.run_tool("existing", "--dir", stories)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr.lower())
            self.assertEqual(marker.read_text(), "keep me")
            self.assertEqual({path.name for path in target.iterdir()}, {"keep.txt"})

    def test_docs_name_six_upgrade_goals_and_adrs(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        adr_path = ROOT / "docs" / "ADR.md"
        self.assertTrue(adr_path.is_file(), "docs/ADR.md is missing")
        decisions = adr_path.read_text(encoding="utf-8")
        for phrase in (
            "Safe intake",
            "Flow-first pages",
            "Grounded copy",
            "Measured accessibility",
            "Readable paper motion",
            "Comfortable optional sound",
            "Shareable private preview",
        ):
            self.assertIn(phrase, readme)
        for adr in range(1, 9):
            self.assertIn(f"ADR-{adr:03d}", decisions)

    def test_docs_describe_safer_authoring_pathway_commands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        tools_doc = (ROOT / "docs" / "TOOLS.md").read_text(encoding="utf-8")
        process = (ROOT / "docs" / "PROCESS.md").read_text(encoding="utf-8")
        design_rules = (ROOT / "docs" / "DESIGN-RULES.md").read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        combined = readme + "\n" + tools_doc
        for fragment in (
            "--claims strict",
            "--phone",
            "--poster",
            "--poster-page",
            "check_mechanics.py",
        ):
            self.assertIn(fragment, combined)
        self.assertIn("--claims strict", process)
        self.assertIn("contrast", process)
        self.assertIn("--poster", process)
        self.assertIn("stagger", design_rules.lower())
        self.assertIn("2800", design_rules)
        self.assertIn("check_mechanics.py", contributing)
        self.assertIn("--claims strict", contributing)

    def test_scaffold_contains_safe_intake_questions_and_skip_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            stories = Path(tmp) / "stories"
            result = self.run_tool("safe-intake", "--dir", stories)
            self.assertEqual(result.returncode, 0, result.stderr)
            target = stories / "safe-intake"
            brief = (target / "brief.md").read_text(encoding="utf-8")
            sources = (target / "sources.md").read_text(encoding="utf-8")
            for heading in (
                "## Audience",
                "## Why now",
                "## Voice",
                "## Length",
                "## Formats",
                "## Privacy and exclusions",
                "## What changes from start to finish",
                "## Reader takeaway",
                "## Success test",
            ):
                self.assertIn(heading, brief)
            for token in (".env", "*.pem", "*.key", "secrets/", "credentials/", ".git/"):
                self.assertIn(token, sources)
            self.assertIn("skip list", result.stdout)

    def test_scaffold_plans_start_action_and_result_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            stories = Path(tmp) / "stories"
            result = self.run_tool("flow-first", "--dir", stories)
            self.assertEqual(result.returncode, 0, result.stderr)
            target = stories / "flow-first"
            outline = (target / "outline.md").read_text(encoding="utf-8")
            storyboard = (target / "storyboard.md").read_text(encoding="utf-8")
            checklist = (target / "page-checklist.md").read_text(encoding="utf-8")
            for phrase in ("Start", "Hand action", "Result"):
                self.assertIn(phrase, outline)
            for heading in ("### Start state", "### Hand-driven change", "### Result state"):
                self.assertIn(heading, storyboard)
            self.assertIn("start, half-pulled, fully pulled and lifted states", checklist)


class StoryboardBuildTests(unittest.TestCase):
    def build_example(self, output):
        return subprocess.run(
            [sys.executable, str(BUILD), str(EXAMPLE), "--out", str(output)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_example_build_contains_storyboard_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            result = self.build_example(output)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            html = output.read_text()
            self.assertTrue("#storyboard" in html, "build has no #storyboard route")
            self.assertTrue("storyboard-card" in html, "build has no storyboard card renderer")

    def test_storyboard_shows_one_card_per_entry(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            result = self.build_example(output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            story = json.loads(EXAMPLE.read_text())
            expected = len(story["chapters"]) + 3 + (1 if story.get("finale") else 0)

            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    page.set_default_timeout(5000)
                    page.goto(output.as_uri() + "#storyboard")
                    page.wait_for_selector(".storyboard-card")
                    cards = page.locator(".storyboard-card")
                    self.assertEqual(cards.count(), expected)
                    self.assertTrue(all(cards.nth(i).is_visible() for i in range(expected)))
                    browser.close()
            except Exception as exc:
                if "Executable doesn't exist" in str(exc):
                    self.skipTest("Playwright Chromium is not installed")
                raise


if __name__ == "__main__":
    unittest.main()
