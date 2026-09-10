from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.editorial_diagnosis_schema import FINDING_SOURCE_JUDGE  # noqa: E402
from limatus.editorial_judge import (  # noqa: E402
    JudgeUnavailableError,
    _judge_output_schema,
    run_default_judge_lane,
)
from limatus.editorial_scan import scan_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

JUDGE_PROFILE = ROOT / "features/fixtures/editorial-scan/judge-enabled-profile.yml"
BANNED_DRAFT = ROOT / "features/fixtures/editorial-scan/banned-phrase-draft.md"

_SAMPLE_RUBRIC = {
    "clarity": {"score": 3, "evidence": [{"start": 0, "end": 5, "note": "ok"}]},
    "directness": {"score": 4, "evidence": []},
    "specificity": {"score": 3, "evidence": []},
    "voice": {"score": 4, "evidence": []},
    "fidelity": {"score": 5, "evidence": []},
}


class EditorialJudgeTests(unittest.TestCase):
    def test_judge_output_schema_root_required_matches_properties(self):
        schema = _judge_output_schema()
        props = schema["properties"]
        required = schema["required"]
        self.assertEqual(set(required), set(props.keys()))
        self.assertIn("rubric", required)
        self.assertIn("findings", required)

    def test_openai_judge_lane_mocked(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")
        payload = {
            "findings": [
                {
                    "kind": "vague_claim",
                    "start": 0,
                    "end": 8,
                    "rationale": "Judge signal.",
                }
            ],
            "rubric": _SAMPLE_RUBRIC,
        }
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = "test-key"
        with patch.dict(os.environ, env, clear=False):
            with patch(
                "limatus.editorial_judge.call_structured_responses_api",
                return_value=payload,
            ):
                diagnosis = scan_draft(draft_text, style_profile=config)
        judge_hits = [
            f
            for f in diagnosis["generic_passages"]
            if f.get("source") == FINDING_SOURCE_JUDGE
        ]
        self.assertEqual(len(judge_hits), 1)
        self.assertIn("rubric", diagnosis)
        self.assertEqual(diagnosis["rubric"]["clarity"]["score"], 3)

    def test_require_judge_without_key_raises(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(JudgeUnavailableError):
                scan_draft(draft_text, style_profile=config, require_judge=True)
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous

    def test_api_error_omits_judge_without_require(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "limatus.editorial_judge.call_structured_responses_api",
                side_effect=RuntimeError("network down"),
            ):
                lane = run_default_judge_lane(draft_text, config, config.profile.judge)
        self.assertEqual(lane.findings, [])
        self.assertIsNone(lane.rubric)

    def test_api_error_with_require_judge_raises(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "limatus.editorial_judge.call_structured_responses_api",
                side_effect=RuntimeError("network down"),
            ):
                with self.assertRaises(JudgeUnavailableError):
                    run_default_judge_lane(
                        draft_text,
                        config,
                        config.profile.judge,
                        require_judge=True,
                    )


if __name__ == "__main__":
    unittest.main()
