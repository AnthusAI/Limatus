from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.usability_profile import (  # noqa: E402
    UsabilityProfileValidationError,
    load_usability_profile,
)
from limatus.usability_scan import (  # noqa: E402
    USABILITY_FORBIDDEN_OUTPUT_KEYS,
    scan_html_page,
    validate_usability_findings,
)

FIXTURE_ROOT = ROOT / "tests/fixtures/usability-scan"
BOTH_PAGE = FIXTURE_ROOT / "both-findings.html"
MINIMAL_PAGE = FIXTURE_ROOT / "minimal.html"
PROFILE = FIXTURE_ROOT / "profile.yml"


class UsabilityScanTests(unittest.TestCase):
    def test_both_findings_page_reports_missing_alt_and_low_contrast(self):
        profile = load_usability_profile(PROFILE)
        html = BOTH_PAGE.read_text(encoding="utf-8")
        payload = scan_html_page(html, profile=profile)
        self.assertEqual(payload["schemaVersion"], 1)
        kinds = {entry["kind"] for entry in payload["findings"]}
        self.assertEqual(kinds, {"missing_alt", "low_contrast"})
        for key in USABILITY_FORBIDDEN_OUTPUT_KEYS:
            self.assertNotIn(key, json.dumps(payload))
        missing = next(entry for entry in payload["findings"] if entry["kind"] == "missing_alt")
        self.assertIn("img", missing["selector"])
        low = next(entry for entry in payload["findings"] if entry["kind"] == "low_contrast")
        self.assertIn("ratio", low)
        self.assertLess(low["ratio"], 4.5)

    def test_minimal_page_has_no_findings(self):
        profile = load_usability_profile(PROFILE)
        html = MINIMAL_PAGE.read_text(encoding="utf-8")
        payload = scan_html_page(html, profile=profile)
        self.assertEqual(payload["findings"], [])

    def test_profile_rejects_unknown_keys(self):
        bad_path = FIXTURE_ROOT / "bad-profile.yml"
        bad_path.write_text("contrast:\n  minRatio: 4.5\nunknown: true\n", encoding="utf-8")
        try:
            with self.assertRaises(UsabilityProfileValidationError):
                load_usability_profile(bad_path)
        finally:
            bad_path.unlink(missing_ok=True)

    def test_cli_usability_scan_writes_json(self):
        env = {**os.environ, "PYTHONPATH": str(SRC)}
        output_path = FIXTURE_ROOT / "_cli-out.json"
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "limatus",
                    "usability",
                    "scan",
                    "--page",
                    str(BOTH_PAGE),
                    "--profile",
                    str(PROFILE),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(completed.stdout, "")
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            validate_usability_findings(payload)
            self.assertEqual(len(payload["findings"]), 2)
        finally:
            output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
