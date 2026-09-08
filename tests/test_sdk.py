from __future__ import annotations

import unittest
from pathlib import Path

from limatus import (
    EditorialDiagnosisValidationError,
    EditorialOptionsValidationError,
    StyleProfileValidationError,
    diagnose,
    generate_options,
    load_config,
    record_decision,
    render_annotations,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml"
OPTIONS_ROOT = ROOT / "features/fixtures/editorial-options"


class FakeResolver:
    def __call__(self, *, draft_text, finding, style_profile, skill, model):
        span = finding["span"]
        return [
            {
                "patch": {"span": span, "replacement": "Teams can verify this claim."},
                "reason": "Use concrete language.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            },
            {
                "patch": {"span": span, "replacement": "The claim needs evidence."},
                "reason": "Preserve uncertainty until verified.",
                "factVerificationRequired": True,
                "unresolvedQuestions": ["Which source supports this claim?"],
            },
        ]


class PublicSdkContractTests(unittest.TestCase):
    def test_load_and_diagnose_are_importable_and_validated(self):
        config = load_config(PROFILE)
        self.assertEqual(config.profile.publication_key, "anthus-blog")
        diagnosis = diagnose("In today's tools, everyone knows this is transformative.", config=config)
        self.assertEqual(diagnosis["schemaVersion"], 1)
        self.assertIn("generic_passages", diagnosis)

    def test_decisions_options_and_annotations_share_core_shapes(self):
        config = load_config(PROFILE)
        diagnosis = diagnose("In today's tools, everyone knows this is transformative.", config=config)
        finding = diagnosis["generic_passages"][0]
        decisions = record_decision([], finding["id"], "rewrite", note="Needs a concrete claim")
        self.assertEqual(decisions[0]["decision"], "rewrite")

        options = generate_options(
            "In today's tools, everyone knows this is transformative.",
            config=config,
            diagnosis=diagnosis,
            decisions=decisions,
            skill_path=OPTIONS_ROOT / "editorial-rewrite-skill.yml",
            resolver=FakeResolver(),
        )
        self.assertEqual(options["schemaVersion"], 1)
        self.assertEqual(options["findings"][0]["findingId"], finding["id"])
        self.assertIn("::editorial-finding", render_annotations(
            "In today's tools, everyone knows this is transformative.", diagnosis, format="markus"
        ))
        self.assertIn("<editorialAnnotation", render_annotations(
            "In today's tools, everyone knows this is transformative.", diagnosis, format="xml"
        ))

    def test_public_functions_reject_invalid_contracts(self):
        with self.assertRaises(StyleProfileValidationError):
            load_config(ROOT / "features/fixtures/editorial-style-profile/malformed.yml")
        with self.assertRaises(EditorialDiagnosisValidationError):
            diagnose("draft", config={})
        with self.assertRaises(EditorialOptionsValidationError):
            record_decision([], "not-a-finding", "rewrite")

    def test_sdk_does_not_mutate_draft(self):
        draft = "In today's tools, everyone knows this is transformative."
        original = draft
        config = load_config(PROFILE)
        diagnosis = diagnose(draft, config=config)
        render_annotations(draft, diagnosis)
        self.assertEqual(draft, original)


if __name__ == "__main__":
    unittest.main()
