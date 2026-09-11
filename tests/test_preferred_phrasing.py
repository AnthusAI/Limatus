from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.editorial_diagnosis import PROFILE_RULE_PREFIX, check_rules_only, diagnose_draft  # noqa: E402
from limatus.editorial_diagnosis_schema import FINDING_SOURCE_PROFILE  # noqa: E402
from limatus.editorial_style import StyleProfileValidationError, load_style_profile  # noqa: E402

PROFILE = ROOT / "features/fixtures/preferred-phrasing/style-profile.yml"


class PreferredPhrasingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loaded = load_style_profile(PROFILE)

    def test_profile_loads_preferred_phrasing_pair(self) -> None:
        pairs = self.loaded.profile.rules.preferred_phrasing
        self.assertEqual(pairs, (("thrift family", "family of thrift"),))

    def test_validation_rejects_empty_from_or_to(self) -> None:
        base = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
        for field in ("from", "to"):
            broken = dict(base)
            rules = dict(broken["rules"])
            other = "to" if field == "from" else "from"
            rules["preferredPhrasing"] = [{field: "   ", other: "valid phrase"}]
            broken["rules"] = rules
            with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as handle:
                yaml.safe_dump(broken, handle)
                path = Path(handle.name)
            try:
                with self.assertRaises(StyleProfileValidationError) as ctx:
                    load_style_profile(path)
                self.assertIn(f"rules.preferredPhrasing[0].{field}", str(ctx.exception))
            finally:
                path.unlink(missing_ok=True)

    def _preferred_findings(self, draft: str) -> list[dict]:
        diagnosis = diagnose_draft(draft, style_profile=self.loaded)
        prefix = f"{PROFILE_RULE_PREFIX} prefer "
        return [
            finding
            for finding in diagnosis["generic_passages"]
            if finding.get("source") == FINDING_SOURCE_PROFILE
            and str(finding.get("rationale", "")).startswith(prefix)
        ]

    def test_thrift_family_triggers_preferred_phrasing_finding(self) -> None:
        findings = self._preferred_findings("The thrift family runs many shops.")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["excerpt"].lower(), "thrift family")
        self.assertEqual(
            findings[0]["rationale"],
            f'{PROFILE_RULE_PREFIX} prefer "family of thrift" over "thrift family"',
        )
        self.assertEqual(findings[0]["kind"], "vague_claim")

    def test_family_of_thrift_does_not_trigger(self) -> None:
        self.assertEqual(self._preferred_findings("The family of thrift runs many shops."), [])

    def test_unrelated_phrase_does_not_trigger(self) -> None:
        self.assertEqual(self._preferred_findings("The data center runs hot."), [])

    def test_check_rules_only_includes_preferred_phrasing(self) -> None:
        findings = check_rules_only("We met the thrift family yesterday.", style_profile=self.loaded)
        self.assertTrue(
            any(
                finding.get("rationale")
                == f'{PROFILE_RULE_PREFIX} prefer "family of thrift" over "thrift family"'
                for finding in findings
            )
        )


if __name__ == "__main__":
    unittest.main()
