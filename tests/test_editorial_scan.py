from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.editorial_diagnosis_schema import (  # noqa: E402
    FINDING_SOURCE_JUDGE,
    FINDING_SOURCE_PROFILE,
    EditorialDiagnosisValidationError,
    validate_diagnosis,
)
from limatus.editorial_judge import JUDGE_PROMPT_VERSION, make_judge_finding, resolved_judge_model  # noqa: E402
from limatus.editorial_scan import scan_draft, union_judge_findings  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

PROFILE = ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml"
JUDGE_PROFILE = ROOT / "features/fixtures/editorial-scan/judge-enabled-profile.yml"
BANNED_DRAFT = ROOT / "features/fixtures/editorial-scan/banned-phrase-draft.md"


class EditorialScanTests(unittest.TestCase):
    def test_profile_findings_include_source_without_judge(self):
        config = load_style_profile(PROFILE)
        diagnosis = scan_draft("In today's tools, everyone knows this is transformative.", style_profile=config)
        findings = diagnosis["generic_passages"] + diagnosis["voice_observations"]
        self.assertTrue(findings)
        for finding in findings:
            self.assertEqual(finding["source"], FINDING_SOURCE_PROFILE)
            self.assertNotIn("model", finding)
            self.assertNotIn("promptVersion", finding)

    def test_union_preserves_profile_when_judge_adds_findings(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")

        def fake_judge(_draft, loaded, judge_config):
            model = resolved_judge_model(judge_config)
            return [
                make_judge_finding(
                    "vague_claim",
                    draft_text,
                    0,
                    10,
                    "Injected judge signal.",
                    model=model,
                )
            ]

        diagnosis = scan_draft(draft_text, style_profile=config, judge_resolver=fake_judge)
        profile_hits = [
            finding
            for finding in diagnosis["generic_passages"]
            if finding.get("source") == FINDING_SOURCE_PROFILE and "seamless" in finding["excerpt"].lower()
        ]
        judge_hits = [finding for finding in diagnosis["generic_passages"] if finding.get("source") == FINDING_SOURCE_JUDGE]
        self.assertEqual(len(profile_hits), 1)
        self.assertEqual(len(judge_hits), 1)
        self.assertEqual(judge_hits[0]["promptVersion"], JUDGE_PROMPT_VERSION)

    def test_default_judge_resolver_without_api_key_is_empty(self):
        config = load_style_profile(JUDGE_PROFILE)
        draft_text = BANNED_DRAFT.read_text(encoding="utf-8")
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        previous = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ.pop("OPENAI_API_KEY", None)
            diagnosis = scan_draft(draft_text, style_profile=config)
        finally:
            if previous is not None:
                os.environ["OPENAI_API_KEY"] = previous
        judge_findings = [
            finding
            for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts")
            for finding in diagnosis[key]
            if finding.get("source") == FINDING_SOURCE_JUDGE
        ]
        self.assertEqual(judge_findings, [])

    def test_schema_rejects_profile_finding_with_model(self):
        payload = {
            "schemaVersion": 1,
            "document_intent": "Test intent.",
            "audience": "Readers",
            "generic_passages": [
                {
                    "id": "finding-0123456789abcdef",
                    "kind": "vague_claim",
                    "excerpt": "sample",
                    "span": {"start": 0, "end": 6},
                    "rationale": "reason",
                    "source": FINDING_SOURCE_PROFILE,
                    "model": "gpt-test",
                }
            ],
            "unsupported_claims": [],
            "repetition_groups": [],
            "voice_observations": [],
            "required_facts": [],
        }
        with self.assertRaises(EditorialDiagnosisValidationError):
            validate_diagnosis(payload)

    def test_scan_and_diagnose_cli_match(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{SRC}:{ROOT}"
        env.pop("OPENAI_API_KEY", None)
        text = "In today's tools, everyone knows this is transformative."
        scan = subprocess.run(
            [
                sys.executable,
                "-m",
                "limatus",
                "scan",
                "--text",
                text,
                "--profile",
                str(PROFILE),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        diagnose = subprocess.run(
            [
                sys.executable,
                "-m",
                "limatus",
                "diagnose",
                "--text",
                text,
                "--profile",
                str(PROFILE),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(scan.stdout), json.loads(diagnose.stdout))

    def test_union_helper_only_appends(self):
        base = {
            "schemaVersion": 1,
            "document_intent": "Lead.",
            "audience": "Readers",
            "generic_passages": [
                {
                    "id": "finding-aaaaaaaaaaaaaaaa",
                    "kind": "vague_claim",
                    "excerpt": "Lead.",
                    "span": {"start": 0, "end": 5},
                    "rationale": "r",
                    "source": FINDING_SOURCE_PROFILE,
                }
            ],
            "unsupported_claims": [],
            "repetition_groups": [],
            "voice_observations": [],
            "required_facts": [],
        }
        judge = [
            make_judge_finding("vague_claim", "Lead.", 0, 4, "judge", model="gpt-5.6-terra"),
        ]
        merged = union_judge_findings(base, judge)
        self.assertEqual(len(merged["generic_passages"]), 2)


if __name__ == "__main__":
    unittest.main()
