from __future__ import annotations

import unittest
from pathlib import Path

from limatus.editorial_rewrite_options import generate_rewrite_options
from limatus.editorial_style import load_style_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = load_style_profile(ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml")
SKILL_PATH = ROOT / "features/fixtures/editorial-options/editorial-rewrite-skill.yml"

FINDING_ID = "finding-a6b95ac741d27015"
EXCERPT = "gap in a wall.\n\nIt ended the way it started."


def _diagnosis_for_finding(finding: dict) -> dict:
    return {
        "schemaVersion": 1,
        "document_intent": "Test document intent for rewrite options.",
        "audience": "Test readers.",
        "generic_passages": [finding],
        "unsupported_claims": [],
        "repetition_groups": [],
        "voice_observations": [],
        "required_facts": [],
    }


def _finding(span: dict[str, int]) -> dict:
    return {
        "id": FINDING_ID,
        "kind": "vague_claim",
        "excerpt": EXCERPT,
        "span": span,
        "rationale": "Test finding for prefix-skip retry.",
        "source": "profile",
    }


def _patch_option(replacement: str, reason: str, span: dict[str, int]) -> dict:
    return {
        "patch": {"span": span, "replacement": replacement},
        "reason": reason,
        "factVerificationRequired": False,
        "unresolvedQuestions": [],
    }


class GenerateRewriteOptionsPrefixSkipRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.body = f"Water finds the lower ground. {EXCERPT} The end."
        start = self.body.index(EXCERPT)
        self.span = {"start": start, "end": start + len(EXCERPT)}
        self.finding = _finding(self.span)
        self.diagnosis = _diagnosis_for_finding(self.finding)
        self.decisions = [
            {
                "schemaVersion": 1,
                "finding_id": FINDING_ID,
                "decision": "rewrite",
                "note": "",
            }
        ]

    def test_retries_resolver_after_prefix_skip_drops_options(self) -> None:
        prefix_skip = "It ended the way it started."
        full_a = "gap in a wall. It ended differently."
        full_b = "gap in a wall.\n\nIt closed the way it opened."
        call_count = 0

        def resolver(**_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [
                    _patch_option(prefix_skip, "Skip prefix A.", self.span),
                    _patch_option(prefix_skip, "Skip prefix B.", self.span),
                ]
            return [
                _patch_option(full_a, "Full span rewrite A.", self.span),
                _patch_option(full_b, "Full span rewrite B.", self.span),
            ]

        draft = self.body
        payload = generate_rewrite_options(
            draft,
            style_profile=PROFILE,
            diagnosis=self.diagnosis,
            decisions=self.decisions,
            skill_path=SKILL_PATH,
            llm_resolver=resolver,
        )
        self.assertEqual(draft, self.body)
        self.assertEqual(call_count, 2)
        self.assertEqual(len(payload["findings"]), 1)
        self.assertEqual(len(payload["findings"][0]["options"]), 2)

    def test_raises_when_retry_still_has_prefix_skips(self) -> None:
        prefix_skip = "It ended the way it started."
        call_count = 0

        def resolver(**_kwargs):
            nonlocal call_count
            call_count += 1
            return [
                _patch_option(prefix_skip, f"Skip prefix attempt {call_count} A.", self.span),
                _patch_option(prefix_skip, f"Skip prefix attempt {call_count} B.", self.span),
            ]

        draft = self.body
        with self.assertRaisesRegex(ValueError, "requires at least two rewrite options"):
            generate_rewrite_options(
                draft,
                style_profile=PROFILE,
                diagnosis=self.diagnosis,
                decisions=self.decisions,
                skill_path=SKILL_PATH,
                llm_resolver=resolver,
            )
        self.assertEqual(draft, self.body)
        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()
