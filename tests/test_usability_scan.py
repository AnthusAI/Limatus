from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from limatus.usability_profile import (  # noqa: E402
    UsabilityProfileValidationError,
    load_usability_profile,
)
from limatus.usability_scan import (  # noqa: E402
    USABILITY_FORBIDDEN_OUTPUT_KEYS,
    parse_css_color,
    scan_html_page,
    validate_usability_findings,
)

FIXTURE_ROOT = ROOT / "tests/fixtures/usability-scan"
BOTH_PAGE = FIXTURE_ROOT / "both-findings.html"
MINIMAL_PAGE = FIXTURE_ROOT / "minimal.html"
PROFILE = FIXTURE_ROOT / "profile.yml"


class UsabilityScanTests(unittest.TestCase):
    def test_both_findings_page_reports_missing_alt_and_low_contrast(self):
        profile = load_usability_profile(PROFILE)
        html = BOTH_PAGE.read_text(encoding="utf-8")
        payload = scan_html_page(html, profile=profile)
        self.assertEqual(payload["schemaVersion"], 1)
        kinds = {entry["kind"] for entry in payload["findings"]}
        self.assertEqual(kinds, {"missing_alt", "low_contrast"})
        self.assertNotIn("suppressed_focus_outline", kinds)
        for key in USABILITY_FORBIDDEN_OUTPUT_KEYS:
            self.assertNotIn(key, json.dumps(payload))
        missing = next(entry for entry in payload["findings"] if entry["kind"] == "missing_alt")
        self.assertIn("img", missing["selector"])
        low = next(entry for entry in payload["findings"] if entry["kind"] == "low_contrast")
        self.assertIn("ratio", low)
        self.assertLess(low["ratio"], 4.5)

    def test_minimal_page_has_no_findings(self):
        profile = load_usability_profile(PROFILE)
        html = MINIMAL_PAGE.read_text(encoding="utf-8")
        payload = scan_html_page(html, profile=profile)
        self.assertEqual(payload["findings"], [])

    def test_small_tap_target_flags_16px_button(self):
        profile = load_usability_profile(PROFILE)
        html = '<!DOCTYPE html><html><body><button width="16" height="16">Go</button></body></html>'
        payload = scan_html_page(html, profile=profile)
        tap = [entry for entry in payload["findings"] if entry["kind"] == "small_tap_target"]
        self.assertEqual(len(tap), 1)
        self.assertEqual(tap[0]["width"], 16.0)
        self.assertEqual(tap[0]["height"], 16.0)
        validate_usability_findings(payload)

    def test_24px_control_does_not_flag_small_tap_target(self):
        profile = load_usability_profile(PROFILE)
        html = '<!DOCTYPE html><html><body><button width="24" height="24">Go</button></body></html>'
        payload = scan_html_page(html, profile=profile)
        tap = [entry for entry in payload["findings"] if entry["kind"] == "small_tap_target"]
        self.assertEqual(tap, [])

    def test_unsized_link_does_not_flag_small_tap_target(self):
        profile = load_usability_profile(PROFILE)
        html = '<!DOCTYPE html><html><body><a href="/x">Home</a></body></html>'
        payload = scan_html_page(html, profile=profile)
        tap = [entry for entry in payload["findings"] if entry["kind"] == "small_tap_target"]
        self.assertEqual(tap, [])

    def test_suppressed_focus_outline_flags_button_focus_none(self):
        profile = load_usability_profile(PROFILE)
        html = """<!DOCTYPE html><html><head><style>
        button:focus { outline: none }
        </style></head><body><button>Go</button></body></html>"""
        payload = scan_html_page(html, profile=profile)
        suppressed = [
            entry for entry in payload["findings"] if entry["kind"] == "suppressed_focus_outline"
        ]
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["selector"], "button")

    def test_suppressed_focus_outline_skips_when_box_shadow_focus_ring(self):
        profile = load_usability_profile(PROFILE)
        html = """<!DOCTYPE html><html><head><style>
        button:focus { outline: none; box-shadow: 0 0 0 2px #000 }
        </style></head><body><button>Go</button></body></html>"""
        payload = scan_html_page(html, profile=profile)
        suppressed = [
            entry for entry in payload["findings"] if entry["kind"] == "suppressed_focus_outline"
        ]
        self.assertEqual(suppressed, [])

    def test_flag_suppressed_outline_false_disables_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "no-focus.yml"
            profile_path.write_text(
                "focus:\n  flagSuppressedOutline: false\n",
                encoding="utf-8",
            )
            profile = load_usability_profile(profile_path)
            html = """<!DOCTYPE html><html><head><style>
            button:focus { outline: none }
            </style></head><body><button>Go</button></body></html>"""
            payload = scan_html_page(html, profile=profile)
            suppressed = [
                entry for entry in payload["findings"] if entry["kind"] == "suppressed_focus_outline"
            ]
            self.assertEqual(suppressed, [])

    def test_tap_target_only_profile_uses_default_focus_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "tap-only.yml"
            profile_path.write_text("tapTarget:\n  minPx: 24\n", encoding="utf-8")
            loaded = load_usability_profile(profile_path)
            self.assertTrue(loaded.profile.focus.flag_suppressed_outline)
            html = """<!DOCTYPE html><html><head><style>
            button:focus { outline: none }
            </style></head><body><button>Go</button></body></html>"""
            payload = scan_html_page(html, profile=loaded)
            self.assertEqual(
                len([f for f in payload["findings"] if f["kind"] == "suppressed_focus_outline"]),
                1,
            )

    def test_contrast_only_profile_uses_default_tap_target_min_px(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "contrast-only.yml"
            profile_path.write_text("contrast:\n  minRatio: 4.5\n", encoding="utf-8")
            loaded = load_usability_profile(profile_path)
            self.assertEqual(loaded.profile.tap_target.min_px, 24)
            html = '<!DOCTYPE html><html><body><button width="16" height="16">Go</button></body></html>'
            payload = scan_html_page(html, profile=loaded)
            self.assertEqual(len([f for f in payload["findings"] if f["kind"] == "small_tap_target"]), 1)

    def test_profile_rejects_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad-profile.yml"
            bad_path.write_text(
                "contrast:\n  minRatio: 4.5\nunknown: true\n",
                encoding="utf-8",
            )
            with self.assertRaises(UsabilityProfileValidationError):
                load_usability_profile(bad_path)

    def test_void_img_does_not_swallow_following_siblings(self):
        profile = load_usability_profile(PROFILE)
        html = """<!DOCTYPE html>
<html><head><style>.muted { color: #777777; background-color: #888888; }</style></head>
<body><img src="x"><p class="muted">Low contrast</p></body></html>"""
        payload = scan_html_page(html, profile=profile)
        missing = next(entry for entry in payload["findings"] if entry["kind"] == "missing_alt")
        low = next(entry for entry in payload["findings"] if entry["kind"] == "low_contrast")
        self.assertEqual(missing["selector"], "img")
        self.assertEqual(low["selector"], "p.muted")

    def test_invalid_three_digit_hex_color_returns_none(self):
        self.assertIsNone(parse_css_color("#ggg"))

    def test_cli_usability_scan_writes_json(self):
        env = {**os.environ, "PYTHONPATH": str(SRC)}
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "findings.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "limatus",
                    "usability",
                    "scan",
                    "--page",
                    str(BOTH_PAGE),
                    "--profile",
                    str(PROFILE),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(completed.stdout, "")
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            validate_usability_findings(payload)
            self.assertEqual(len(payload["findings"]), 2)

    def test_cli_scan_does_not_modify_page_file(self):
        env = {**os.environ, "PYTHONPATH": str(SRC)}
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            page_copy = tmp_path / "page.html"
            page_copy.write_bytes(BOTH_PAGE.read_bytes())
            before = page_copy.read_bytes()
            output_path = tmp_path / "findings.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "limatus",
                    "usability",
                    "scan",
                    "--page",
                    str(page_copy),
                    "--profile",
                    str(PROFILE),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(page_copy.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
