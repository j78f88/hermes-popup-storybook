"""Tests for physical pop-up craft mounts (box folds, chapter v-folds, low wings and notched wheel)."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import build  # noqa: E402
import validate as V  # noqa: E402

EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())


class CraftMountTests(unittest.TestCase):
    def test_chapter_box_vfold_and_low_wings_validate_and_render(self):
        story = copy.deepcopy(EXAMPLE)
        sc = story["chapters"][0]["scene"]
        sc["wings"] = "low"
        sc["pieces"][1]["mount"] = "box"
        sc["pieces"].append(
            {
                "id": "arch",
                "sprite": "bridge_arch",
                "x": 50,
                "depth": 3,
                "scale": 2.8,
                "mount": "vfold",
            }
        )
        errors, warnings = V.validate(story)
        self.assertEqual(errors, [])
        html = build.render(story)
        self.assertIn("mount-box", html)
        self.assertIn("mount-vfold", html)
        self.assertIn("stage-wings-low", html)
        self.assertIn("wheel-notch-rim", html)

    def test_invalid_chapter_mount_or_wings_is_rejected(self):
        story = copy.deepcopy(EXAMPLE)
        sc = story["chapters"][0]["scene"]
        sc["wings"] = "giant-border"
        sc["pieces"][1]["mount"] = "spring"
        errors, _ = V.validate(story)
        self.assertTrue(any("wings must be" in e for e in errors), errors)
        self.assertTrue(any("mount must be" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
