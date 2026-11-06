"""Tests for the optional ingest questionnaire pathway."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE = ROOT / "tools" / "questionnaire.py"
VALIDATE = ROOT / "engine" / "validate.py"
CHECK_LEDGER = ROOT / "tools" / "check_ledger.py"
BUILD = ROOT / "engine" / "build.py"


class QuestionnairePathwayTests(unittest.TestCase):
    def test_questionnaire_compiles_answers_into_strict_valid_book_and_html_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            form_html = tmp_path / "intake.html"
            r_form = subprocess.run(
                [sys.executable, str(QUESTIONNAIRE), "--html", str(form_html)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r_form.returncode, 0, r_form.stdout + r_form.stderr)
            self.assertTrue(form_html.exists())
            self.assertIn("Pop-up book intake questionnaire", form_html.read_text())

            answers = {
                "name": "field-notes",
                "title": "Field notes",
                "subtitle": "Four weeks of testing in 2026",
                "byline": "Curated for the team",
                "unit": "Page",
                "skip_terms": ["secret-project"],
                "cast": ["robot", "person", "owl", "robin"],
                "chapters": [
                    {
                        "title": "First map",
                        "when": "1 August 2026",
                        "setting": "map_room",
                        "summary": [
                            "On 1 August 2026 we mapped 4 questions across 2 notebooks so the team could see the whole job.",
                            "The first draft hid the point until we put the 1 recommendation at the top.",
                        ],
                        "trial": "The first draft repeated 3 sections before naming the decision.",
                        "lesson": "Put the recommendation at the top and keep the notes short.",
                        "facts": [
                            {
                                "label": "Questions mapped",
                                "value": "4",
                                "source_title": "Notebook A",
                                "ref": "note-a:1",
                                "excerpt": "Four questions mapped across two notebooks on 1 August 2026.",
                            },
                            {
                                "label": "Notebooks used",
                                "value": "2",
                                "source_title": "Notebook A",
                                "ref": "note-a:2",
                                "excerpt": "Two notebooks held the first draft on 1 August 2026.",
                            },
                            {
                                "label": "Sections repeated",
                                "value": "3",
                                "source_title": "Notebook B",
                                "ref": "note-b:4",
                                "excerpt": "Three sections repeated before 1 recommendation.",
                            },
                        ],
                    }
                ],
            }
            ans_path = tmp_path / "answers.json"
            ans_path.write_text(json.dumps(answers))

            r_compile = subprocess.run(
                [sys.executable, str(QUESTIONNAIRE), "--from", str(ans_path), "--dir", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r_compile.returncode, 0, r_compile.stdout + r_compile.stderr)

            story_dir = tmp_path / "field-notes"
            story_json = story_dir / "story.json"
            self.assertTrue((story_dir / "brief.md").exists())
            self.assertTrue((story_dir / "sources.md").exists())
            self.assertTrue((story_dir / "outline.md").exists())
            self.assertTrue((story_dir / "storyboard.md").exists())

            v = subprocess.run(
                [sys.executable, str(VALIDATE), str(story_json), "--strict"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(v.returncode, 0, v.stdout + v.stderr)

            cl = subprocess.run(
                [
                    sys.executable,
                    str(CHECK_LEDGER),
                    str(story_dir / "research" / "facts-01.json"),
                    "--story",
                    str(story_json),
                    "--claims",
                    "strict",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(cl.returncode, 0, cl.stdout + cl.stderr)

            out_html = tmp_path / "book.html"
            b = subprocess.run(
                [sys.executable, str(BUILD), str(story_json), "-o", str(out_html)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(b.returncode, 0, b.stdout + b.stderr)


if __name__ == "__main__":
    unittest.main()
