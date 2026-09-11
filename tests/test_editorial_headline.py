from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from limatus.editorial_headline import generate_headline_options  # noqa: E402
from limatus.editorial_rewrite_options import generate_rewrite_suggestions  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402
from limatus.editorial_yaml import locate_yaml_scalar_span  # noqa: E402

FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-headline"
SKILL_PATH = FIXTURE_ROOT / "editorial-rewrite-skill.yml"


class EditorialYamlSpanTests(unittest.TestCase):
    def test_quoted_title_scalar_span(self):
        text = '---\ntitle: "Quoted headline value"\n---\n\nBody.\n'
        span = locate_yaml_scalar_span(text, "title")
        self.assertEqual(span.value, "Quoted headline value")
        self.assertEqual(text[span.start : span.end], "Quoted headline value")

    def test_folded_subtitle_scalar_span(self):
        text = (
            "---\n"
            "standfirst: >-\n"
            "  Folded line one\n"
            "  continues here\n"
            "---\n"
            "\nBody.\n"
        )
        span = locate_yaml_scalar_span(text, "standfirst")
        self.assertIn("Folded line one", span.value)
        self.assertEqual(text[span.start : span.end].strip(), "Folded line one\n  continues here")


class EditorialHeadlineTests(unittest.TestCase):
    def test_generate_title_options(self):
        working_copy = FIXTURE_ROOT / "working-copy.md"
        text = working_copy.read_text(encoding="utf-8")
        profile = load_style_profile(FIXTURE_ROOT / "style-profile.yml")

        def resolver(**kwargs):
            return [
                {
                    "patch": {"span": kwargs["finding"]["span"], "replacement": "Better title"},
                    "reason": "Clearer title.",
                    "factVerificationRequired": False,
                    "unresolvedQuestions": [],
                },
                {
                    "patch": {"span": kwargs["finding"]["span"], "replacement": "Another title"},
                    "reason": "Alternate title.",
                    "factVerificationRequired": False,
                    "unresolvedQuestions": [],
                },
            ]

        payload = generate_headline_options(
            text,
            job="title",
            style_profile=profile,
            skill_path=SKILL_PATH,
            llm_resolver=resolver,
        )
        self.assertEqual(len(payload["findings"]), 1)
        self.assertGreaterEqual(len(payload["findings"][0]["options"]), 2)


class SuggestRewriteFrontmatterTests(unittest.TestCase):
    def test_body_only_candidate_restores_frontmatter(self):
        draft_path = FIXTURE_ROOT / "working-copy.md"
        draft_text = draft_path.read_text(encoding="utf-8")
        profile = load_style_profile(FIXTURE_ROOT / "style-profile.yml")
        diagnosis = json.loads(
            (REPO_ROOT / "features/fixtures/editorial-options/diagnosis.json").read_text(encoding="utf-8")
        )

        def resolver(**_kwargs):
            return [
                {
                    "candidateText": "Revised body without frontmatter.",
                    "rationale": "Body-only rewrite.",
                    "factVerificationRequired": False,
                    "factualVerificationWarnings": [],
                    "unresolvedQuestions": [],
                }
            ]

        payload = generate_rewrite_suggestions(
            draft_text,
            style_profile=profile,
            diagnosis=diagnosis,
            skill_path=SKILL_PATH,
            llm_resolver=resolver,
        )
        candidate = payload["candidates"][0]["candidateText"]
        self.assertTrue(candidate.startswith("---\n"))
        self.assertIn("title:", candidate)
        self.assertIn("Revised body without frontmatter.", candidate)


if __name__ == "__main__":
    unittest.main()
