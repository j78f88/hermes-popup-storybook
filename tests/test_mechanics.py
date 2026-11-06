import concurrent.futures
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check_mechanics.py"
STORY = ROOT / "stories" / "example" / "story.json"

try:
    import playwright  # noqa: F401

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright is not importable")
class MechanicsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = []
        cls.temp = tempfile.TemporaryDirectory()

        def check(viewport, extra):
            report = Path(cls.temp.name) / f"{viewport}.json"
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(STORY), *extra, "--json", str(report)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=600,
            )
            if not report.exists():
                raise AssertionError(result.stdout + result.stderr)
            return json.loads(report.read_text(encoding="utf-8"))["results"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            jobs = [
                executor.submit(check, "desktop", []),
                executor.submit(check, "phone", ["--phone"]),
            ]
            for job in jobs:
                cls.results.extend(job.result())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_clause_passes(self, clause):
        results = [item for item in self.results if item["clause"] == clause]
        self.assertTrue(results, f"no results for {clause}")
        failures = [item for item in results if item["status"] != "PASS"]
        self.assertFalse(failures, json.dumps(failures, indent=2))


def add_test(clause, expected_failure=False):
    def test(self):
        self.assert_clause_passes(clause)

    test.__name__ = f"test_clause_{clause.lower()}"
    test.__doc__ = f"The example satisfies mechanics clause {clause}."
    if expected_failure:
        test = unittest.expectedFailure(test)
    setattr(MechanicsIntegrationTests, test.__name__, test)


for passing_clause in (
    "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9",
    "F1", "F2", "F3", "F4", "F5", "F6",
    "T1", "T2", "T3", "T4", "T5", "T6",
    "B1", "B2", "B3", "B4",
    "W1", "W2", "W3",
    "L1", "L3", "N1", "N2", "I1", "I3",
):
    add_test(passing_clause)


if __name__ == "__main__":
    unittest.main()
