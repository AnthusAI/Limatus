from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.editorial_canary import (  # noqa: E402
    assert_calibration_matches_code,
    load_canary_manifest,
    run_canary,
)
from limatus.editorial_judge import JUDGE_PROMPT_VERSION  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

MANIFEST = ROOT / "features/fixtures/editorial-canary/manifest.yml"


class EditorialCanaryTests(unittest.TestCase):
    def test_checked_in_canary_passes_with_fixture_judge(self):
        code, report, lines = run_canary(MANIFEST, judge_mode="fixture")
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertEqual(len(report["results"]), 5)

    def test_calibration_mismatch_fails(self):
        manifest = load_canary_manifest(MANIFEST)
        style_profile = load_style_profile(manifest["profilePath"])
        manifest["calibration"]["judgePromptVersion"] = "stale-version"
        with self.assertRaises(ValueError) as ctx:
            assert_calibration_matches_code(manifest, style_profile)
        self.assertIn("calibration drift", str(ctx.exception))

    def test_each_result_includes_judge_provenance(self):
        _, report, _ = run_canary(MANIFEST, judge_mode="fixture")
        for result in report["results"]:
            judge = result["judge"]
            self.assertEqual(judge["promptVersion"], JUDGE_PROMPT_VERSION)
            self.assertTrue(judge["model"])


if __name__ == "__main__":
    unittest.main()
