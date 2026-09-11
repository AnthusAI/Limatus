from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from limatus import diagnose  # noqa: E402
from limatus.editorial_diagnosis import _mask_for_redundancy_shingling  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

PROFILE = ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml"
FIXTURE_ROOT = ROOT / "features/fixtures/editorial-diagnosis"


def _redundancy_groups(diagnosis: dict) -> list[dict]:
    return [group for group in diagnosis.get("repetition_groups", []) if group.get("kind") == "redundancy"]


class EditorialRedundancyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_style_profile(PROFILE)

    def test_mask_preserves_length_and_blanks_image_markup(self) -> None:
        text = (
            "See [![pilobolus mid leap](../assets/a.jpg)](https://example.com) "
            "and ![alt text](../b.jpg) plus <img src=\"x\" alt=\"y\"> end."
        )
        masked = _mask_for_redundancy_shingling(text)
        self.assertEqual(len(masked), len(text))
        self.assertNotIn("pilobolus", masked.lower())
        link_text = "Read [click through](../guide.md) for more."
        masked_links = _mask_for_redundancy_shingling(link_text)
        self.assertIn("click through", masked_links)

    def test_repeated_image_alts_are_not_redundancy_findings(self) -> None:
        draft = (FIXTURE_ROOT / "redundancy-image-alts.md").read_text(encoding="utf-8")
        diagnosis = diagnose(draft, config=self.config)
        self.assertEqual(_redundancy_groups(diagnosis), [])

    def test_repeated_phrase_only_in_blockquotes_is_not_redundancy(self) -> None:
        draft = (FIXTURE_ROOT / "redundancy-blockquote-refrain.md").read_text(encoding="utf-8")
        diagnosis = diagnose(draft, config=self.config)
        self.assertEqual(_redundancy_groups(diagnosis), [])

    def test_italic_formula_and_pull_quote_refrain_is_not_redundancy(self) -> None:
        draft = (FIXTURE_ROOT / "redundancy-italic-pull-quote.md").read_text(encoding="utf-8")
        diagnosis = diagnose(draft, config=self.config)
        self.assertEqual(_redundancy_groups(diagnosis), [])

    def test_repeated_body_prose_still_reports_redundancy(self) -> None:
        draft = (FIXTURE_ROOT / "redundancy-body-prose.md").read_text(encoding="utf-8")
        diagnosis = diagnose(draft, config=self.config)
        groups = _redundancy_groups(diagnosis)
        self.assertTrue(groups)
        shared = " ".join(
            " ".join(re.findall(r"[a-z0-9']+", member["excerpt"].lower()))
            for group in groups
            for member in group["members"]
        )
        self.assertIn("editorial team reviewed the manuscript", shared)

    def test_blockquote_plus_body_repetition_still_flags(self) -> None:
        draft = (FIXTURE_ROOT / "redundancy-blockquote-mixed.md").read_text(encoding="utf-8")
        diagnosis = diagnose(draft, config=self.config)
        self.assertTrue(_redundancy_groups(diagnosis))
