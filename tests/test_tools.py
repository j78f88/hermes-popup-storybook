import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import check_layout
import visual_qa


class LayoutHelperTests(unittest.TestCase):
    def test_desktop_states_cover_each_required_position(self):
        self.assertEqual(
            check_layout.state_names(phone=False),
            ["start", "half", "pulled", "lifted"],
        )

    def test_phone_states_cover_start_and_final(self):
        self.assertEqual(check_layout.state_names(phone=True), ["start", "final"])

    def test_overlap_ratio_uses_smaller_rectangle(self):
        left = {"left": 0, "top": 0, "right": 10, "bottom": 10}
        right = {"left": 5, "top": 0, "right": 15, "bottom": 10}
        self.assertEqual(check_layout.overlap_ratio(left, right), 0.5)

    def test_overlap_ratio_is_zero_for_disjoint_rectangles(self):
        left = {"left": 0, "top": 0, "right": 5, "bottom": 5}
        right = {"left": 6, "top": 0, "right": 9, "bottom": 5}
        self.assertEqual(check_layout.overlap_ratio(left, right), 0.0)

    def test_allowlist_combines_story_and_command_line_values(self):
        with tempfile.TemporaryDirectory() as folder:
            story = Path(folder) / "story.json"
            story.write_text(json.dumps({"qa": {"allowOffstage": ["waves"]}}))
            self.assertEqual(
                check_layout.read_allowlist(story, ["cloud", "waves"]),
                {"cloud", "waves"},
            )

    def test_contrast_ratio_matches_black_and_white(self):
        self.assertAlmostEqual(
            check_layout.contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=2
        )

    def test_contrast_threshold_uses_large_bold_rule(self):
        self.assertEqual(check_layout.required_contrast(16, 400), 4.5)
        self.assertEqual(check_layout.required_contrast(24, 400), 3.0)
        self.assertEqual(check_layout.required_contrast(18.66, 700), 3.0)

    def test_check_measurement_reports_contrast_and_zero_coverage(self):
        measured = {
            "edge": [],
            "underLesson": [],
            "nan": [],
            "pieces": [],
            "proseScroll": False,
            "textExpected": 1,
            "textChecked": 1,
            "textItems": [{
                "selector": ".prose p",
                "fg": [246, 238, 219],
                "bg": [246, 238, 219],
                "fontSize": 16.0,
                "fontWeight": 400,
                "text": "Invisible words",
            }],
        }
        errors, _ = check_layout.check_measurement(measured, set(), "desktop/ch1/start")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["type"], "contrast")
        self.assertEqual(errors[0]["selector"], ".prose p")

        zero_cov = {
            "edge": [],
            "underLesson": [],
            "nan": [],
            "pieces": [],
            "proseScroll": False,
            "textExpected": 1,
            "textChecked": 0,
            "textItems": [],
        }
        cov_errors, _ = check_layout.check_measurement(zero_cov, set(), "desktop/ch1/start")
        self.assertEqual(len(cov_errors), 1)
        self.assertEqual(cov_errors[0]["type"], "contrast-coverage")

    def test_check_measurement_evaluates_raw_text_items_in_python_and_formats_summary(self):
        measured = {
            "edge": [],
            "underLesson": [],
            "nan": [],
            "pieces": [],
            "proseScroll": False,
            "textExpected": 1,
            "textChecked": 1,
            "textItems": [{
                "selector": ".page.left .prose p",
                "fg": [246, 238, 219],
                "bg": [246, 238, 219],
                "fontSize": 16.0,
                "fontWeight": 400,
                "text": "Hidden in plain sight",
            }],
        }
        errors, _ = check_layout.check_measurement(measured, set(), "desktop/ch1/start")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["type"], "contrast")
        self.assertEqual(errors[0]["ratio"], 1.0)
        self.assertEqual(errors[0]["required"], 4.5)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check_layout.print_summary({
                "passed": False,
                "checks": 1,
                "textChecks": 1,
                "errors": errors,
                "warnings": [],
            })
        self.assertIn("1.0 < 4.5", buf.getvalue())

    def test_shared_browser_helpers_lookup_scene_and_overlap(self):
        import _browser

        story = _browser.load_story(ROOT / "stories" / "example" / "story.json")
        entry = _browser.entry_for_key(story, "ch1")
        self.assertEqual(entry["number"], 1)
        scene, effects = _browser.scene_for_page(story, "ch1")
        self.assertTrue(scene.get("pieces"))
        self.assertTrue(effects)
        box_a = {"left": 0, "top": 0, "right": 10, "bottom": 10}
        box_b = {"left": 5, "top": 0, "right": 15, "bottom": 10}
        self.assertAlmostEqual(_browser.overlap_ratio(box_a, box_b), 0.5)


class VisualQaHelperTests(unittest.TestCase):
    def test_brief_rendering_requires_and_replaces_placeholders(self):
        template = "{{book}} for {{audience}}. {{rules}} Notes: {{notes}}"
        rendered = visual_qa.render_brief(
            template,
            {
                "book": "The Tidy Robot",
                "audience": "young readers",
                "rules": "Keep text clear.",
                "notes": "Check the flap.",
            },
        )
        self.assertEqual(
            rendered,
            "The Tidy Robot for young readers. Keep text clear. Notes: Check the flap.",
        )

    def test_image_label_explains_generated_state_names(self):
        self.assertIn("half", visual_qa.image_label(Path("02b-p3-half.png")).lower())
        self.assertIn("sheet", visual_qa.image_label(Path("sheet-1.jpg")).lower())

    def test_dry_run_payload_contains_images_without_network_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "01a-p1-start.png"
            image.write_bytes(b"not a real png")
            payload = visual_qa.build_payload(
                "test/model", "Review this book.", [image], recheck=None
            )
            summary = visual_qa.dry_run_summary(payload, [image], "Review this book.")
            self.assertEqual(summary["image_count"], 1)
            self.assertGreater(summary["payload_bytes"], 20)
            self.assertEqual(summary["brief_head"], "Review this book.")
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            self.assertEqual(payload["reasoning"], {"effort": "high"})


try:
    import playwright  # noqa: F401

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright is not importable")
class LayoutIntegrationTests(unittest.TestCase):
    def test_example_story_passes_layout_check(self):
        with tempfile.TemporaryDirectory() as folder:
            report_path = Path(folder) / "layout.json"
            story_path = ROOT / "stories" / "example" / "story.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOLS / "check_layout.py"),
                    str(story_path),
                    "--json",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            story = json.loads(story_path.read_text(encoding="utf-8"))
            entries = story["chapters"] + ([story["finale"]] if story.get("finale") else [])
            expected = sum(1 for entry in entries if entry.get("tab"))
            self.assertEqual(len(report["dragTests"]), expected)
            self.assertGreaterEqual(report["textChecks"], report["checks"])

    def test_low_contrast_book_fails_layout_check(self):
        with tempfile.TemporaryDirectory() as folder:
            story_path = ROOT / "stories" / "example" / "story.json"
            html_path = Path(folder) / "low-contrast.html"
            subprocess.run(
                [sys.executable, str(ROOT / "engine" / "build.py"), str(story_path), "-o", str(html_path)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            html = html_path.read_text(encoding="utf-8")
            html_path.write_text(
                html.replace(
                    "</head>",
                    "<style>.page.left .prose p{color:#f6eedb!important;background:#f6eedb!important}</style></head>",
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(TOOLS / "check_layout.py"), str(html_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("ERROR contrast", result.stdout)


if __name__ == "__main__":
    unittest.main()
