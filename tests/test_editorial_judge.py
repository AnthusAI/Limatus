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
    DEFAULT_JUDGE_OUTPUT_TOKENS,
    JUDGE_REFERENCE_EXCERPT_CHARS,
    MAX_JUDGE_OUTPUT_TOKENS,
    JudgeUnavailableError,
    _judge_output_budget,
    _judge_output_schema,
    _map_openai_findings,
    build_judge_user_prompt,
    drop_frontmatter_findings,
    judge_system_prompt,
    run_default_judge_lane,
    scrub_rubric_frontmatter,
)
from limatus.editorial_scan import scan_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

JUDGE_PROFILE = ROOT / "features/fixtures/editorial-scan/judge-enabled-profile.yml"
VOICE_PROMPT_PROFILE = ROOT / "features/fixtures/editorial-judge/voice-prompt-profile.yml"
BANNED_DRAFT = ROOT / "features/fixtures/editorial-scan/banned-phrase-draft.md"

_SAMPLE_RUBRIC = {
    "clarity": {"score": 3, "evidence": [{"start": 0, "end": 5, "note": "ok"}]},
    "directness": {"score": 4, "evidence": []},
    "specificity": {"score": 3, "evidence": []},
    "voice": {"score": 4, "evidence": []},
    "fidelity": {"score": 5, "evidence": []},
}


class EditorialJudgeTests(unittest.TestCase):
    def test_map_openai_findings_skips_mid_word_spans(self):
        draft = "We are staying alert."
        word_start = draft.index("staying")
        mid_start = word_start + 2
        mid_end = word_start + 5
        raw = [
            {
                "kind": "vague_claim",
                "start": mid_start,
                "end": mid_end,
                "rationale": "Mid-word cut.",
            },
            {
                "kind": "vague_claim",
                "start": draft.index("."),
                "end": draft.index(".") + 1,
                "rationale": "Punctuation span.",
            },
        ]
        mapped = _map_openai_findings(raw, draft, model="test-model")
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["excerpt"], ".")

    def test_map_openai_findings_skips_span_after_apostrophe(self):
        draft = "Magnanti's door."
        apostrophe = draft.index("'")
        s_start = apostrophe + 1
        self.assertEqual(draft[s_start], "s")
        raw = [
            {
                "kind": "vague_claim",
                "start": s_start,
                "end": s_start + 3,
                "rationale": "Inside possessive.",
            },
            {
                "kind": "vague_claim",
                "start": draft.index("."),
                "end": draft.index(".") + 1,
                "rationale": "Punctuation span.",
            },
        ]
        mapped = _map_openai_findings(raw, draft, model="test-model")
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["excerpt"], ".")

    def test_judge_output_budget_bounds(self):
        self.assertEqual(_judge_output_budget(""), DEFAULT_JUDGE_OUTPUT_TOKENS)
        tiny = "ab"
        self.assertEqual(_judge_output_budget(tiny), DEFAULT_JUDGE_OUTPUT_TOKENS)
        mid = "x" * 12000
        mid_budget = _judge_output_budget(mid)
        self.assertGreater(mid_budget, DEFAULT_JUDGE_OUTPUT_TOKENS)
        self.assertLessEqual(mid_budget, MAX_JUDGE_OUTPUT_TOKENS)
        long_draft = "y" * 300_000
        self.assertEqual(_judge_output_budget(long_draft), MAX_JUDGE_OUTPUT_TOKENS)

    def test_judge_output_schema_root_required_matches_properties(self):
        schema = _judge_output_schema()
        props = schema["properties"]
        required = schema["required"]
        self.assertEqual(set(required), set(props.keys()))
        self.assertIn("rubric", required)
        self.assertIn("findings", required)

    def test_build_judge_user_prompt_includes_voice_fields(self):
        config = load_style_profile(VOICE_PROMPT_PROFILE)
        prompt = build_judge_user_prompt("Draft.", config)
        self.assertIn("JUDGE_FIXTURE_SENTENCE_STYLE_MARKER", prompt)
        self.assertIn("JUDGE_FIXTURE_STRUCTURE_MARKER", prompt)
        self.assertIn("JUDGE_FIXTURE_VOICE_PATTERNS_MARKER", prompt)
        self.assertIn("Reference samples (voice/register only", prompt)

    def test_build_judge_user_prompt_truncates_long_reference_sample(self):
        config = load_style_profile(VOICE_PROMPT_PROFILE)
        prompt = build_judge_user_prompt("Draft.", config)
        self.assertIn("JUDGE_FIXTURE_SHORT_SAMPLE_BODY_MARKER", prompt)
        self.assertNotIn("JUDGE_FIXTURE_LONG_SAMPLE_TAIL_MARKER", prompt)
        long_sample = next(s for s in config.samples if s.id == "long-sample")
        self.assertGreater(len(long_sample.body.strip()), JUDGE_REFERENCE_EXCERPT_CHARS)
        self.assertIn(long_sample.body.strip()[:JUDGE_REFERENCE_EXCERPT_CHARS], prompt)
        self.assertIn("…", prompt)

    def test_openai_judge_lane_mocked(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")
        payload = {
            "findings": [
                {
                    "kind": "vague_claim",
                    "start": 0,
                    "end": 4,
                    "rationale": "Judge signal.",
                }
            ],
            "rubric": _SAMPLE_RUBRIC,
        }
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = "test-key"
        captured: dict[str, str] = {}

        def capture_api(**kwargs):
            captured["user_prompt"] = kwargs["user_prompt"]
            captured["max_output_tokens"] = kwargs["max_output_tokens"]
            return payload

        with patch.dict(os.environ, env, clear=False):
            with patch(
                "limatus.editorial_judge.call_structured_responses_api",
                side_effect=capture_api,
            ):
                diagnosis = scan_draft(draft_text, style_profile=config)
        expected_budget = _judge_output_budget(draft_text)
        self.assertEqual(captured["max_output_tokens"], expected_budget)
        self.assertNotEqual(captured["max_output_tokens"], 2400)
        self.assertIn("Sentence style:", captured["user_prompt"])
        self.assertIn("Structure:", captured["user_prompt"])
        self.assertIn("Reference samples (voice/register only", captured["user_prompt"])
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

    def test_build_judge_user_prompt_blanks_yaml_title(self):
        config = load_style_profile(VOICE_PROMPT_PROFILE)
        draft = (
            "---\n"
            "title: Secret Title Token\n"
            "standfirst: Standfirst must not leak.\n"
            "---\n\n"
            "Body prose here.\n"
        )
        prompt = build_judge_user_prompt(draft, config)
        self.assertNotIn("Secret Title Token", prompt)
        self.assertNotIn("Standfirst must not leak.", prompt)
        self.assertIn("Body prose here.", prompt)
        self.assertIn("judge the article body", prompt)

    def test_judge_system_prompt_is_body_pass(self):
        text = judge_system_prompt()
        self.assertIn("later pass", text)
        self.assertIn("article-body pass", text)

    def test_drop_frontmatter_findings_and_rubric_evidence(self):
        draft = "---\ntitle: Hello World Title\n---\n\nBody after yaml.\n"
        yaml_end = draft.index("Body")
        title_start = draft.index("Hello")
        findings = [
            {
                "id": "finding-yaml",
                "span": {"start": title_start, "end": title_start + 5},
            },
            {
                "id": "finding-body",
                "span": {"start": yaml_end, "end": yaml_end + 4},
            },
        ]
        kept = drop_frontmatter_findings(findings, draft)
        self.assertEqual([f["id"] for f in kept], ["finding-body"])
        rubric = {
            "clarity": {
                "score": 3,
                "evidence": [
                    {"start": 7, "end": 12, "note": "title"},
                    {"start": yaml_end, "end": yaml_end + 4, "note": "body"},
                ],
            }
        }
        scrubbed = scrub_rubric_frontmatter(rubric, draft)
        self.assertEqual(scrubbed["clarity"]["evidence"], [
            {"start": yaml_end, "end": yaml_end + 4, "note": "body"},
        ])


if __name__ == "__main__":
    unittest.main()
