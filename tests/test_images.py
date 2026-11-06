"""Tests for offline user and stock image ingestion and stage/booklet rendering."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "tools" / "ingest_image.py"
BUILD = ROOT / "engine" / "build.py"
EXAMPLE = json.loads((ROOT / "stories" / "example" / "story.json").read_text())


@unittest.skipUnless(Image is not None, 'Pillow is not installed')
class ImageIngestTests(unittest.TestCase):
    def test_cutout_polaroid_and_pixel_modes_strip_exif_and_build_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            story_path = tmp_path / "story.json"
            story = copy.deepcopy(EXAMPLE)
            story_path.write_text(json.dumps(story))

            img_path = tmp_path / "sample.jpg"
            img = Image.new("RGB", (96, 72), (41, 173, 255))
            exif = img.getexif()
            exif[0x010F] = "SecretCameraMake"
            img.save(img_path, format="JPEG", exif=exif.tobytes())
            self.assertIn(b"Exif", img_path.read_bytes())

            r1 = subprocess.run(
                [
                    sys.executable,
                    str(INGEST),
                    str(img_path),
                    "--story",
                    str(story_path),
                    "--id",
                    "user_badge",
                    "--mode",
                    "cutout",
                    "--source",
                    "arrival-example",
                    "--licence",
                    "Owner photo",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)

            r2 = subprocess.run(
                [
                    sys.executable,
                    str(INGEST),
                    str(img_path),
                    "--story",
                    str(story_path),
                    "--id",
                    "user_pix",
                    "--mode",
                    "pixel",
                    "--width",
                    "16",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

            r3 = subprocess.run(
                [
                    sys.executable,
                    str(INGEST),
                    str(img_path),
                    "--story",
                    str(story_path),
                    "--id",
                    "fact_clip",
                    "--mode",
                    "polaroid",
                    "--source",
                    "arrival-example",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)

            updated = json.loads(story_path.read_text())
            self.assertIn("user_badge", updated["images"])
            self.assertIn("fact_clip", updated["images"])
            self.assertIn("user_pix", updated["sprites"])
            updated["chapters"][0]["scene"]["pieces"].append(
                {"id": "ub", "image": "user_badge", "x": 52, "depth": 2, "scale": 2.0}
            )
            updated["chapters"][0]["facts"][0]["image"] = "fact_clip"
            story_path.write_text(json.dumps(updated))

            out_html = tmp_path / "index.html"
            b = subprocess.run(
                [sys.executable, str(BUILD), str(story_path), "-o", str(out_html)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(b.returncode, 0, b.stdout + b.stderr)
            rendered = out_html.read_text()
            self.assertIn("data:image/", rendered)
            self.assertNotIn("SecretCameraMake", rendered)


if __name__ == "__main__":
    unittest.main()
