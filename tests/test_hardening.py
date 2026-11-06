"""Regression coverage for validator and QA hardening."""

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(TOOLS))

import build  # noqa: E402
import check_layout  # noqa: E402
import release_check  # noqa: E402
import shoot  # noqa: E402
import validate as V  # noqa: E402

EXAMPLE_PATH = ROOT / "stories" / "example" / "story.json"
EXAMPLE = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


class ValidatorHardeningTests(unittest.TestCase):
    def errors(self, story):
        return V.validate(story)[0]

    def test_non_numeric_scene_positions_are_clean_errors(self):
        for field, value in (("x", "middle"), ("x", True)):
            story = copy.deepcopy(EXAMPLE)
            story["chapters"][0]["scene"]["pieces"][0][field] = value
            with self.subTest(field=field, value=value):
                errors = self.errors(story)
                self.assertTrue(any("x must be a finite number" in item for item in errors), errors)

        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["scene"].setdefault("wall", []).append(
            {"sprite": "sun", "x": 50, "y": "low"}
        )
        errors = self.errors(story)
        self.assertTrue(any("y must be a finite number" in item for item in errors), errors)

    def test_wall_y_is_limited_to_zero_through_one_hundred(self):
        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["scene"].setdefault("wall", []).append(
            {"sprite": "sun", "x": 50, "y": 101}
        )
        self.assertTrue(any("y=101 outside 0..100" in item for item in self.errors(story)))

    def test_move_target_types_and_ranges_are_checked(self):
        cases = {
            "x": ("middle", "x must be a finite number"),
            "grow": (0, "grow must be greater than 0"),
            "z": (1.1, "z=1.1 outside 0..1"),
            "lift": ("high", "lift must be a finite number"),
            "depth": (2.5, "depth must be 1..4"),
        }
        for field, (value, fragment) in cases.items():
            story = copy.deepcopy(EXAMPLE)
            story["chapters"][0]["flap"]["effects"] = [
                {"piece": "hero", "fx": "move", "to": {field: value}}
            ]
            with self.subTest(field=field):
                errors = self.errors(story)
                self.assertTrue(any(fragment in item for item in errors), errors)

    def test_validator_rejects_each_uncovered_rule(self):
        cases = []
        for key in ("title", "sources"):
            story = copy.deepcopy(EXAMPLE)
            del story[key]
            cases.append((story, f"missing top-level '{key}'"))
        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["scene"]["sky"] = "unknown"
        cases.append((story, "unknown sky"))
        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["scene"]["pieces"][0]["depth"] = 9
        cases.append((story, "depth must be 1..4"))
        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["tab"]["effects"][0]["fx"] = "explode"
        cases.append((story, "unknown effect"))
        story = copy.deepcopy(EXAMPLE)
        story["chapters"][0]["tab"]["effects"][0]["at"] = [0.8, 0.2]
        cases.append((story, "must be [start, end]"))
        story = copy.deepcopy(EXAMPLE)
        source_id = next(iter(story["sources"]))
        del story["sources"][source_id]["kind"]
        cases.append((story, "needs 'kind' and 'ref'"))
        for story, fragment in cases:
            with self.subTest(rule=fragment):
                errors, _ = V.validate(story)
                self.assertTrue(any(fragment in error for error in errors), errors)

    def test_build_escapes_lang_and_title_attributes(self):
        story = copy.deepcopy(EXAMPLE)
        story["lang"] = 'en"><script>bad()</script>'
        story["title"] = '<img src=x onerror="bad()">'
        rendered = build.render(story)
        self.assertIn('lang="en&quot;&gt;&lt;script&gt;bad()&lt;/script&gt;"', rendered)
        title = rendered.split("<title>", 1)[1].split("</title>", 1)[0]
        self.assertEqual(title, '&lt;img src=x onerror=&quot;bad()&quot;&gt;')


class ReleaseCheckHardeningTests(unittest.TestCase):
    def test_release_check_uses_the_validator_patterns(self):
        self.assertEqual(
            [(name, regex.pattern) for name, regex in release_check.RULES],
            V.SECRET_PATTERNS,
        )

    def test_load_deny_is_shared_across_engine_and_release_check(self):
        with tempfile.TemporaryDirectory() as folder:
            deny_file = Path(folder) / "deny.txt"
            deny_file.write_text("# comment\n\n SecretProject \n", encoding="utf-8")
            self.assertEqual(V.load_deny(deny_file), ["SecretProject"])
            self.assertEqual(release_check.load_deny(deny_file), ["SecretProject"])

    def test_release_check_rules_and_structure(self):
        text = "\n".join(
            [
                "mail person@test.invalid",
                "host 192.168.1.9",
                "path /home/example/private",
                "token github_" + "pat_" + "a" * 30,
                "-----BEGIN " + "PRIVATE KEY-----",
                "password" + "=supersecret",
                "host box.tail1234.ts.net",
                "path C:\\Users\\example\\file",
            ]
        )
        rules = {finding[2] for finding in release_check.scan_text("fixture", text, ["private"])}
        expected = {
            "Email address",
            "Private IPv4",
            "Home directory path",
            "GitHub token",
            "Private key",
            "Password assignment",
            "Tailnet hostname",
            "deny word",
        }
        self.assertEqual(rules, expected)
        self.assertEqual(release_check.scan_text("fixture", "person@example.com", []), [])
        structure = release_check.structure_findings(
            ["dist/book.html", "stories/private/story.json"], set()
        )
        self.assertEqual(
            {item[2] for item in structure},
            {"built output in git", "story other than the example"},
        )

    def test_default_tree_scan_combines_tracked_and_untracked_files(self):
        seen = []

        def fake_scan(files, deny):
            seen.extend(files)
            return []

        output = io.StringIO()
        with (
            mock.patch.object(release_check, "tracked_files", return_value=["tracked.txt"]),
            mock.patch.object(release_check, "untracked_files", return_value=["draft.txt"]),
            mock.patch.object(release_check, "structure_findings", return_value=[]),
            mock.patch.object(release_check, "scan_tree", side_effect=fake_scan),
            redirect_stdout(output),
        ):
            self.assertEqual(release_check.main([]), 0)
        self.assertEqual(seen, ["tracked.txt", "draft.txt"])
        self.assertIn("1 tracked files and 1 untracked files", output.getvalue())

    def test_history_baseline_ignores_only_reviewed_findings(self):
        known = (
            "old.txt (history 12345678)",
            4,
            "Password assignment",
            "password" + "=fixture",
        )
        new = (
            "new.txt (history abcdef12)",
            7,
            "Tailnet hostname",
            "host.tail.ts.net",
        )
        baseline = {release_check.finding_id(known)}
        remaining, count, stale = release_check.filter_history([known, new], baseline)
        self.assertEqual(remaining, [new])
        self.assertEqual(count, 1)
        self.assertEqual(stale, set())


class ToolHardeningTests(unittest.TestCase):
    def test_overlap_warnings_have_stable_names_and_high_priority(self):
        scene = {
            "pieces": [
                {"id": "hero", "sprite": "robot"},
                {"sprite": "plant"},
            ]
        }
        annotations = check_layout.piece_annotations(
            scene, [{"piece": "hero", "fx": "move", "to": {"x": 20}}]
        )
        self.assertEqual(annotations[0], {"label": "hero", "active": True})
        self.assertEqual(annotations[1], {"label": "plant (scene 2)", "active": False})
        measured = {
            "edge": [],
            "underLesson": [],
            "nan": [],
            "proseScroll": False,
            "pieces": [
                {"id": "hero", "left": 0, "top": 0, "right": 10, "bottom": 10, "active": True},
                {"id": "plant (scene 2)", "left": 2, "top": 0, "right": 12, "bottom": 10, "active": False},
            ],
        }
        _, warnings = check_layout.check_measurement(measured, set(), "desktop/ch1/pulled")
        self.assertEqual(warnings[0]["severity"], "high")
        self.assertEqual(warnings[0]["pieces"], ["hero", "plant (scene 2)"])

    def test_measure_script_checks_growth_bottom_and_transform(self):
        self.assertIn("--grow", check_layout.MEASURE_JS)
        self.assertIn("e.style.bottom", check_layout.MEASURE_JS)
        self.assertIn("m.style.transform", check_layout.MEASURE_JS)
        self.assertIn("textItems", check_layout.MEASURE_JS)
        self.assertIn("textChecked", check_layout.MEASURE_JS)
        self.assertNotIn("contrastRatio", check_layout.MEASURE_JS)

    def test_contact_sheet_has_four_state_columns(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            paths = []
            for state in ("start", "half", "pulled", "lifted"):
                path = output / f"{state}.png"
                Image.new("RGB", (20, 10), "white").save(path)
                paths.append(path)
            sheets = shoot.make_contact_sheets([("p1", paths)], output)
            with Image.open(sheets[0]) as sheet:
                self.assertEqual(sheet.width, 80)

    def test_poster_key_and_flag_validation(self):
        self.assertEqual(shoot.poster_key(1), "ch1")
        self.assertEqual(shoot.poster_key("13"), "ch13")
        help_run = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "shoot.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("--poster", help_run.stdout)
        self.assertIn("--poster-only", help_run.stdout)
        self.assertIn("--poster-page", help_run.stdout)
        with tempfile.TemporaryDirectory() as folder_name:
            with self.assertRaises(ValueError):
                shoot.run(EXAMPLE_PATH, folder_name, phone=True, poster=True)
            with self.assertRaises(ValueError):
                shoot.run(EXAMPLE_PATH, folder_name, phone=True, poster_only=True)

    def test_poster_exports_settled_requested_page(self):
        try:
            from PIL import Image, ImageChops, ImageStat
            import playwright.sync_api  # noqa: F401
        except ImportError:
            self.skipTest("Pillow or Playwright is not installed")
        with tempfile.TemporaryDirectory() as folder_name:
            output = Path(folder_name)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "shoot.py"),
                    str(EXAMPLE_PATH),
                    "-o",
                    str(output),
                    "--poster",
                    "--poster-page",
                    "2",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if "Executable doesn't exist" in (result.stdout + result.stderr):
                self.skipTest("Playwright Chromium is not installed")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            poster = output / "cover-card.jpg"
            self.assertTrue(poster.is_file())
            ch2_lifted = output / "03d-p2-lifted.png"
            ch1_lifted = output / "02d-p1-lifted.png"
            with Image.open(poster) as image, Image.open(ch2_lifted) as p2, Image.open(ch1_lifted) as p1:
                rgb_poster = image.convert("RGB")
                self.assertEqual(image.size, (1440, 900))
                self.assertGreater(ImageStat.Stat(rgb_poster).var[0], 1)
                diff_p2 = ImageStat.Stat(ImageChops.difference(rgb_poster, p2.convert("RGB"))).mean[0]
                diff_p1 = ImageStat.Stat(ImageChops.difference(rgb_poster, p1.convert("RGB"))).mean[0]
                self.assertLess(diff_p2, 4.0)
                self.assertGreater(diff_p1, diff_p2)

        with tempfile.TemporaryDirectory() as poster_only_dir:
            only_out = Path(poster_only_dir)
            only_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "shoot.py"),
                    str(EXAMPLE_PATH),
                    "-o",
                    str(only_out),
                    "--poster-only",
                    "--poster-page",
                    "2",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if "Executable doesn't exist" in (only_run.stdout + only_run.stderr):
                self.skipTest("Playwright Chromium is not installed")
            self.assertEqual(only_run.returncode, 0, only_run.stdout + only_run.stderr)
            self.assertEqual([item.name for item in only_out.iterdir()], ["cover-card.jpg"])
            with Image.open(only_out / "cover-card.jpg") as image:
                self.assertEqual(image.size, (1440, 900))

    def test_every_cli_help_and_visual_qa_dry_run(self):
        scripts = [
            ROOT / "engine" / "validate.py",
            ROOT / "engine" / "build.py",
            ROOT / "tools" / "new_story.py",
            ROOT / "tools" / "check_layout.py",
            ROOT / "tools" / "shoot.py",
            ROOT / "tools" / "export_pdf.py",
            ROOT / "tools" / "visual_qa.py",
            ROOT / "tools" / "release_check.py",
            ROOT / "tools" / "ingest_image.py",
            ROOT / "tools" / "questionnaire.py",
            ROOT / "tools" / "build_and_check.py",
        ]
        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            images = folder / "images"
            images.mkdir()
            (images / "p1-start.png").write_bytes(b"fixture")
            brief = folder / "brief.md"
            brief.write_text("Review {{book}} for {{audience}}.", encoding="utf-8")
            out = folder / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "visual_qa.py"),
                    "--model",
                    "test/model",
                    "--images",
                    str(images),
                    "--brief",
                    str(brief),
                    "--var",
                    "book=Fixture",
                    "--var",
                    "audience=reviewers",
                    "--out",
                    str(out),
                    "--dry-run",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["image_count"], 1)
            self.assertEqual(
                summary["variables"], {"audience": "reviewers", "book": "Fixture"}
            )
            self.assertEqual(
                (out / "qa-dry-run-brief.md").read_text(encoding="utf-8"),
                "Review Fixture for reviewers.",
            )


class ValidatorInputFileTests(unittest.TestCase):
    """The validator reports missing or broken files in one plain line, never a traceback."""

    def run_validate(self, *args):
        return subprocess.run([sys.executable, str(ENGINE / "validate.py"), *args], capture_output=True, text=True)

    def test_missing_story_file_is_a_clean_failure(self):
        r = self.run_validate("no/such/story.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL: story file not found: no/such/story.json", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_broken_json_names_the_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "story.json"
            bad.write_text('{\n  "title": "x",\n  oops\n}\n')
            r = self.run_validate(str(bad))
        self.assertEqual(r.returncode, 1)
        self.assertIn("is not valid JSON: line 3", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_missing_deny_file_is_a_clean_failure(self):
        r = self.run_validate(str(EXAMPLE_PATH), "--deny", "no/such/deny.txt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL: deny file not found", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
