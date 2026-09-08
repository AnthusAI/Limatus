from __future__ import annotations

import json
import subprocess
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PROFILE = ROOT / "features/fixtures/editorial-style-profile/portable-profile.json"
DRAFT = ROOT / "features/fixtures/editorial-diagnosis/sloppy-draft.md"


class ReadmeExampleTests(unittest.TestCase):
    def test_documented_portable_diagnose_command_runs_against_fixtures(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn("--profile features/fixtures/editorial-style-profile/portable-profile.json", readme)
        self.assertIn("--draft features/fixtures/editorial-diagnosis/sloppy-draft.md", readme)

        with tempfile.TemporaryDirectory(prefix="limatus-readme-") as directory:
            output = Path(directory) / "diagnosis.json"
            completed = subprocess.run(
                [
                    "limatus",
                    "diagnose",
                    "--draft",
                    str(DRAFT),
                    "--profile",
                    str(PROFILE),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.stdout, "")
            diagnosis = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(diagnosis["schemaVersion"], 1)
            self.assertIn("generic_passages", diagnosis)


if __name__ == "__main__":
    unittest.main()
