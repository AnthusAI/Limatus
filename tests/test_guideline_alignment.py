import os
import unittest
from pathlib import Path
from unittest.mock import patch

from limatus.editorial_compare import compare_candidates
from limatus.editorial_compare_schema import validate_compare_report
from limatus.editorial_guideline_alignment import (
    default_alignment_resolver,
    openai_guideline_alignment,
)
from limatus.editorial_style import load_style_profile
from limatus import sdk

ROOT = Path(__file__).resolve().parents[1]
PROFILE = load_style_profile(ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml")
FIXTURE = ROOT / "features/fixtures/editorial-compare"


class TestOpenaiGuidelineAlignment(unittest.TestCase):
    def test_openai_guideline_alignment_maps_api_payload(self):
        baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
        candidates = [
            {"id": "a", "text": "draft a"},
            {"id": "b", "text": "draft b"},
        ]
        with patch(
            "limatus.editorial_guideline_alignment.call_structured_responses_api",
            return_value={"winnerId": "b", "rationale": "Closer to the editorial aim."},
        ):
            result = openai_guideline_alignment(baseline, candidates, PROFILE)
        self.assertEqual(result["winnerId"], "b")
        self.assertEqual(result["rationale"], "Closer to the editorial aim.")

    def test_openai_guideline_alignment_rejects_unknown_winner_id(self):
        baseline = "baseline"
        candidates = [{"id": "only", "text": "text"}]
        with patch(
            "limatus.editorial_guideline_alignment.call_structured_responses_api",
            return_value={"winnerId": "other", "rationale": "invalid"},
        ):
            result = openai_guideline_alignment(baseline, candidates, PROFILE)
        self.assertIsNone(result["winnerId"])

    def test_default_alignment_resolver_without_key(self):
        env = os.environ.copy()
        try:
            os.environ.pop("OPENAI_API_KEY", None)
            self.assertIsNone(default_alignment_resolver())
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_compare_via_sdk_includes_guideline_alignment_with_key_and_patch(self):
        baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
        candidates = [
            {"id": "unsupported", "text": (FIXTURE / "working-unsupported.md").read_text(encoding="utf-8")},
            {"id": "improved", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
        ]
        env = os.environ.copy()
        try:
            os.environ["OPENAI_API_KEY"] = "test-key"
            with patch(
                "limatus.editorial_guideline_alignment.call_structured_responses_api",
                return_value={"winnerId": "improved", "rationale": "Matches aim."},
            ):
                report = sdk.compare(baseline, candidates, config=PROFILE, mode="rank")
        finally:
            os.environ.clear()
            os.environ.update(env)
        self.assertEqual(report["guidelineAlignment"]["winnerId"], "improved")
        self.assertIn("audience", report["guidelineAlignment"]["question"].lower())

    def test_compare_candidates_with_default_resolver_patch(self):
        baseline = (FIXTURE / "original.md").read_text(encoding="utf-8")
        candidates = [
            {"id": "a", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
            {"id": "b", "text": (FIXTURE / "working-improved.md").read_text(encoding="utf-8")},
        ]
        env = os.environ.copy()
        try:
            os.environ["OPENAI_API_KEY"] = "test-key"
            resolver = default_alignment_resolver()
            self.assertIsNotNone(resolver)
            with patch(
                "limatus.editorial_guideline_alignment.call_structured_responses_api",
                return_value={"winnerId": "a", "rationale": "tie-break"},
            ):
                report = validate_compare_report(
                    compare_candidates(
                        baseline,
                        candidates,
                        style_profile=PROFILE,
                        mode="rank",
                        alignment_resolver=resolver,
                    )
                )
            self.assertEqual(report["guidelineAlignment"]["winnerId"], "a")
        finally:
            os.environ.clear()
            os.environ.update(env)


if __name__ == "__main__":
    unittest.main()
