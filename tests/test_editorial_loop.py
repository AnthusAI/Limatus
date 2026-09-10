from __future__ import annotations

import json
import unittest
from pathlib import Path

from limatus import (
    candidates_from_options,
    compare,
    compose_loop_record,
    generate_options,
    load_config,
    preview_patch_text,
    record_decision,
)
from limatus.editorial_judge import JUDGE_PROMPT_VERSION, make_judge_finding, resolved_judge_model
from limatus.editorial_loop import assert_scan_has_no_steering_decisions
from limatus.editorial_scan import scan_draft

ROOT = Path(__file__).resolve().parents[1]
OPTIONS_ROOT = ROOT / "features/fixtures/editorial-options"
PROFILE = ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml"
LOOP_FIXTURE = ROOT / "features/fixtures/editorial-loop"
SLOPPY_DRAFT = ROOT / "features/fixtures/editorial-diagnosis/sloppy-draft.md"
SCAN_PROFILE = LOOP_FIXTURE / "style-profile-with-judge.yml"
ARTICLE = OPTIONS_ROOT / "article.md"


def _union_test_judge_resolver(draft_text, style_profile, judge_config):
    model = resolved_judge_model(judge_config)
    return [
        make_judge_finding(
            "vague_claim",
            draft_text,
            0,
            min(len(draft_text), 24),
            "Judge lane clarity signal for union coverage.",
            model=model,
            prompt_version=JUDGE_PROMPT_VERSION,
        )
    ]


class FakeResolver:
    def __call__(self, *, draft_text, finding, style_profile, skill, model):
        span = finding["span"]
        return [
            {
                "patch": {"span": span, "replacement": "Teams can verify this claim."},
                "reason": "Concrete language.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
            {
                "patch": {"span": span, "replacement": "The claim needs evidence."},
                "reason": "Preserve uncertainty.",
                "factVerificationRequired": True,
                "unresolvedQuestions": ["Which source supports this claim?"],
            },
        ]


class EditorialLoopTests(unittest.TestCase):
    def test_preview_patch_text_splices_span(self):
        draft = "The platform will revolutionize workflows."
        text = preview_patch_text(
            draft,
            {"span": {"start": 18, "end": 31}, "replacement": "improve"},
        )
        self.assertEqual(text, "The platform will improve workflows.")

    def test_scan_decisions_then_options_for_rewrite_only(self):
        draft = SLOPPY_DRAFT.read_text(encoding="utf-8")
        config = load_config(SCAN_PROFILE)
        diagnosis = scan_draft(
            draft,
            style_profile=config,
            judge_resolver=_union_test_judge_resolver,
        )
        assert_scan_has_no_steering_decisions(diagnosis)
        finding_ids = [
            item["id"]
            for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts")
            for item in diagnosis.get(key, [])
        ]
        self.assertGreaterEqual(len(finding_ids), 2)
        decisions = record_decision([], finding_ids[0], "skip")
        decisions = record_decision(decisions, finding_ids[1], "rewrite")
        options = generate_options(
            draft,
            config=load_config(PROFILE),
            diagnosis=diagnosis,
            decisions=decisions,
            skill_path=OPTIONS_ROOT / "editorial-rewrite-skill.yml",
            resolver=FakeResolver(),
        )
        self.assertEqual([entry["findingId"] for entry in options["findings"]], [finding_ids[1]])

    def test_candidates_from_options_and_compose_record(self):
        draft = ARTICLE.read_text(encoding="utf-8")
        diagnosis = json.loads((OPTIONS_ROOT / "diagnosis.json").read_text(encoding="utf-8"))
        decisions = json.loads((OPTIONS_ROOT / "empty-leadin-decisions.json").read_text(encoding="utf-8"))
        config = load_config(PROFILE)
        options = generate_options(
            draft,
            config=config,
            diagnosis=diagnosis,
            decisions=decisions,
            skill_path=OPTIONS_ROOT / "editorial-rewrite-skill.yml",
            resolver=FakeResolver(),
        )
        candidates = candidates_from_options(draft, options)
        self.assertGreaterEqual(len(candidates), 2)
        report = compare(draft, candidates, config=config)
        record = compose_loop_record(
            diagnosis,
            decisions,
            options,
            report,
            options_model="gpt-test",
            skill_path="skill.yml",
        )
        self.assertEqual(record["schemaVersion"], 1)
        self.assertIn("compareReport", record)
        self.assertEqual(len(record["compareReport"]["candidates"]), len(candidates))


if __name__ == "__main__":
    unittest.main()
