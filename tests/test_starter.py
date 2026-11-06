"""Tests for starter ledgers and sprite discovery."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import check_ledger  # noqa: E402

NEW_STORY = ROOT / "tools" / "new_story.py"
CHECK_LEDGER = ROOT / "tools" / "check_ledger.py"
LIST_SPRITES = ROOT / "tools" / "list_sprites.py"
BUILD = ROOT / "engine" / "build.py"


class StarterToolTests(unittest.TestCase):
    def run_tool(self, tool, *args):
        return subprocess.run(
            [sys.executable, str(tool), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def make_story(self, folder):
        result = self.run_tool(
            NEW_STORY,
            "starter-test",
            "--dir",
            folder,
            "--title",
            "Starter test",
            "--pages",
            "1",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return Path(folder) / "starter-test"

    def test_scaffold_ledger_matches_story_sources_and_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_dir = self.make_story(tmp)
            result = self.run_tool(
                CHECK_LEDGER,
                story_dir / "research" / "fact-ledger.schema.json",
                story_dir / "research" / "ledger-template.json",
                "--story",
                story_dir / "story.json",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3 facts, 0 errors", result.stdout)

            output = Path(tmp) / "book.html"
            build = self.run_tool(BUILD, story_dir / "story.json", "-o", output)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            self.assertTrue(output.read_text().startswith("<!doctype html>"))

    def test_broken_ledger_fails_schema_and_source_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            story_dir = self.make_story(tmp)
            ledger = json.loads((story_dir / "research" / "ledger-template.json").read_text())
            del ledger["facts"][0]["source"]
            ledger["facts"][1]["source"] = "missing-source"
            broken = Path(tmp) / "broken.json"
            broken.write_text(json.dumps(ledger))

            result = self.run_tool(
                CHECK_LEDGER,
                broken,
                "--schema",
                story_dir / "research" / "fact-ledger.schema.json",
                "--story",
                story_dir / "story.json",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required field 'source'", result.stdout)
            self.assertIn("'missing-source' is not", result.stdout)

    def test_schema_requires_story_source_id(self):
        schema = json.loads((ROOT / "templates" / "fact-ledger.schema.json").read_text())
        fact = schema["properties"]["facts"]["items"]
        self.assertIn("source", fact["required"])
        self.assertEqual(fact["properties"]["source"]["type"], "string")

    def test_sprite_list_is_searchable_and_document_is_current(self):
        search = self.run_tool(LIST_SPRITES, "character")
        self.assertEqual(search.returncode, 0, search.stdout + search.stderr)
        self.assertIn("robot\t16x16\tcharacter", search.stdout)
        self.assertNotIn("shelf\t", search.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "SPRITES.md"
            result = self.run_tool(LIST_SPRITES, "--markdown", generated)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Count from the library itself, so adding a sprite never breaks this test.
            count = len(json.loads((ROOT / "engine" / "library" / "sprites.json").read_text())["sprites"])
            self.assertIn(f"{count} sprites", result.stdout)
            self.assertEqual(generated.read_text(), (ROOT / "docs" / "SPRITES.md").read_text())

    def test_claim_tokens_normalize_grouped_numbers_and_dates(self):
        self.assertEqual(
            check_ledger.claim_tokens("On 12 May 2026 there were 4,357 files and version 0.9."),
            {"12", "2026", "4357", "0.9"},
        )

    def test_claim_tokens_ignore_empty_text(self):
        self.assertEqual(check_ledger.claim_tokens(""), set())

    def test_claim_findings_report_unbacked_tokens(self):
        story = {
            "sources": {
                "count": {"kind": "fixture", "ref": "Counted files", "excerpt": "12 May 2026"}
            },
            "chapters": [{
                "number": 1,
                "status": "written",
                "text": ["On 12 May 2026 there were 4,357 files and 99 gaps."],
                "tab": {"text": "The count stayed at 4,357."},
                "flap": {"text": "One check found 99 gaps."},
                "facts": [{"label": "Files", "value": "checked", "source": "count"}],
            }],
            "finale": {
                "title": "Finale",
                "text": ["We closed with 4,357 files and 88 bells."],
                "facts": [{"label": "Files", "value": "checked", "source": "count"}],
            },
        }
        ledgers = [{"facts": [{
            "id": "f1",
            "claim": "The count found files.",
            "value": 4357,
            "source": "count",
            "source_kind": "fixture",
            "ref": "Counted files",
            "excerpt": "files counted",
            "date": "12 May 2026",
            "verified_by": "test",
            "notes": "",
        }]}]
        findings = check_ledger.claim_findings(story, ledgers)
        self.assertEqual(
            [(item["field"], item["token"]) for item in findings],
            [
                ("chapters[0].text[0]", "99"),
                ("chapters[0].flap.text", "99"),
                ("finale.text[0]", "88"),
            ],
        )

    def test_claim_findings_skip_open_chapters(self):
        story = {
            "sources": {},
            "chapters": [{
                "number": 1,
                "status": "open",
                "text": ["Page 1 has 999 unbacked numbers."],
            }],
        }
        self.assertEqual(check_ledger.claim_findings(story, []), [])

    def test_cli_claim_modes_report_and_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            story_path = folder / "story.json"
            ledger_path = folder / "ledger.json"
            story_path.write_text(json.dumps({
                "sources": {"count": {"kind": "fixture", "ref": "Counted 4,357 files", "excerpt": "12 May 2026"}},
                "chapters": [{
                    "number": 1,
                    "status": "written",
                    "text": ["On 12 May 2026 there were 4,357 files and 99 gaps."],
                    "facts": [{"label": "Files", "value": "4,357", "source": "count"}],
                }],
            }))
            ledger_path.write_text(json.dumps({
                "facts": [{
                    "id": "f1",
                    "claim": "The count found 4,357 files.",
                    "value": 4357,
                    "source": "count",
                    "source_kind": "fixture",
                    "ref": "Counted files",
                    "excerpt": "4,357 files",
                    "date": "12 May 2026",
                    "verified_by": "test",
                    "notes": "",
                }]
            }))
            report = self.run_tool(CHECK_LEDGER, ledger_path, "--story", story_path, "--claims", "report")
            self.assertEqual(report.returncode, 0, report.stdout + report.stderr)
            self.assertIn("WARN claim chapter 1 chapters[0].text[0]: unsupported token 99", report.stdout)
            self.assertIn("PASS: 1 ledger files, 1 facts, 0 errors, 1 claim warnings", report.stdout)

            strict = self.run_tool(CHECK_LEDGER, ledger_path, "--story", story_path, "--claims", "strict")
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("ERROR claim chapter 1 chapters[0].text[0]: unsupported token 99", strict.stdout)
            self.assertIn("FAIL: 1 ledger files, 1 facts, 1 errors, 1 claim errors", strict.stdout)

    def test_check_ledger_handles_legacy_object_source_without_traceback(self):
        story = {
            "sources": {"s1": {"kind": "git", "ref": "abc"}},
            "chapters": [{
                "number": 1,
                "status": "written",
                "text": ["It happened at 11 at night with 39 files."],
                "facts": [{"label": "Files", "value": "39", "source": "s1"}],
            }],
        }
        ledgers = [{"facts": [{
            "id": "c1-01",
            "chapter": 1,
            "claim": "Fixed at 11 at night.",
            "value": 11,
            "source": {"kind": "git", "ref": "abc", "excerpt": "11 pm"},
        }]}]
        self.assertEqual(check_ledger.claim_findings(story, ledgers), [])

    def test_strict_claims_mode_rejects_legacy_lane_ledger_schema_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            story_path = folder / "story.json"
            ledger_path = folder / "legacy.json"
            story_path.write_text(json.dumps({
                "sources": {"s1": {"kind": "git", "ref": "abc"}},
                "chapters": [{
                    "number": 1,
                    "status": "written",
                    "text": ["We fixed 11 files."],
                    "facts": [{"label": "Files", "value": "11", "source": "s1"}],
                }],
            }))
            ledger_path.write_text(json.dumps({
                "lane": "ch01",
                "facts": [{
                    "id": "c1-01",
                    "chapter": 1,
                    "claim": "Fixed 11 files.",
                    "value": 11,
                    "source": {"kind": "git", "ref": "abc"},
                }],
            }))
            report = self.run_tool(CHECK_LEDGER, ledger_path, "--story", story_path, "--claims", "report")
            self.assertEqual(report.returncode, 0, report.stdout + report.stderr)

            strict = self.run_tool(CHECK_LEDGER, ledger_path, "--story", story_path, "--claims", "strict")
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("unexpected field 'lane'", strict.stdout)

    def test_malformed_story_entries_report_clean_errors_without_traceback(self):
        story = {
            "sources": {"s1": "not-a-dict"},
            "chapters": ["not-a-chapter", {
                "number": 1,
                "status": "written",
                "text": ["We moved 5 boxes."],
                "tab": "not-a-dict",
                "facts": ["not-a-fact", {"label": "Boxes", "value": "5", "source": "s1"}],
            }],
            "finale": "not-a-dict",
        }
        self.assertEqual(check_ledger.claim_findings(story, []), [])


if __name__ == "__main__":
    unittest.main()
