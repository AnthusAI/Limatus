from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from limatus.editorial_apply import _replacement_skips_span_prefix, apply_patch
from limatus.editorial_rewrite_options import _normalize_options_for_finding


class ReplacementSkipsSpanPrefixTests(unittest.TestCase):
    def test_detects_later_sentence_alignment(self):
        excerpt = "gap in a wall.\n\nIt ended the way it started."
        replacement = "It ended the way it started."
        self.assertTrue(_replacement_skips_span_prefix(excerpt, replacement))

    def test_allows_rewrite_from_excerpt_start(self):
        excerpt = "gap in a wall.\n\nIt ended the way it started."
        replacement = "gap in a wall. It ended differently."
        self.assertFalse(_replacement_skips_span_prefix(excerpt, replacement))

    def test_deletion_does_not_skip(self):
        excerpt = "gap in a wall.\n\nIt ended the way it started."
        self.assertFalse(_replacement_skips_span_prefix(excerpt, ""))


class ApplyPatchSpanPrefixTests(unittest.TestCase):
    def _options_payload(
        self,
        *,
        finding_id: str,
        option_id: str,
        span: dict[str, int],
        replacement: str,
    ) -> dict:
        return {
            "schemaVersion": 1,
            "findings": [
                {
                    "findingId": finding_id,
                    "options": [
                        {
                            "id": option_id,
                            "patch": {"span": span, "replacement": replacement},
                            "reason": "Rewrite aligned with span.",
                            "factVerificationRequired": False,
                            "unresolvedQuestions": [],
                        },
                        {
                            "id": "option-fedcba9876543210",
                            "patch": {"span": span, "replacement": "Full span rewrite."},
                            "reason": "Alternate rewrite.",
                            "factVerificationRequired": False,
                            "unresolvedQuestions": [],
                        },
                    ],
                }
            ],
        }

    def test_apply_rejects_replacement_that_skips_prefix(self):
        prefix = "gap in a wall.\n\n"
        suffix = "It ended the way it started."
        excerpt = prefix + suffix
        body = f"Water finds the lower ground. {excerpt} The end."
        start = body.index(excerpt)
        end = start + len(excerpt)
        finding_id = "finding-0123456789abcdef"
        option_id = "option-0123456789abcdef"
        replacement = "It ended the way it started."
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.md"
            working = Path(tmp) / "working.md"
            original.write_text(body, encoding="utf-8")
            working.write_text(body, encoding="utf-8")
            before = working.read_bytes()
            with self.assertRaisesRegex(ValueError, "skips the start of the span"):
                apply_patch(
                    original_path=original,
                    working_copy_path=working,
                    options=self._options_payload(
                        finding_id=finding_id,
                        option_id=option_id,
                        span={"start": start, "end": end},
                        replacement=replacement,
                    ),
                    finding_id=finding_id,
                    anchor=excerpt,
                    option_id=option_id,
                )
            self.assertEqual(working.read_bytes(), before)

    def test_apply_allows_replacement_from_span_start(self):
        excerpt = "gap in a wall.\n\nIt ended the way it started."
        replacement = "gap in a wall. It ended the way water flows."
        body = f"Intro. {excerpt} Outro."
        start = body.index(excerpt)
        end = start + len(excerpt)
        finding_id = "finding-0123456789abcdef"
        option_id = "option-0123456789abcdef"
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.md"
            working = Path(tmp) / "working.md"
            original.write_text(body, encoding="utf-8")
            working.write_text(body, encoding="utf-8")
            apply_patch(
                original_path=original,
                working_copy_path=working,
                options=self._options_payload(
                    finding_id=finding_id,
                    option_id=option_id,
                    span={"start": start, "end": end},
                    replacement=replacement,
                ),
                finding_id=finding_id,
                anchor=excerpt,
                option_id=option_id,
            )
            expected = body[:start] + replacement + body[end:]
            self.assertEqual(working.read_text(encoding="utf-8"), expected)


class NormalizeOptionsSpanPrefixTests(unittest.TestCase):
    def test_normalize_drops_option_that_skips_prefix(self):
        excerpt = "gap in a wall.\n\nIt ended the way it started."
        finding = {
            "id": "finding-0123456789abcdef",
            "excerpt": excerpt,
            "span": {"start": 0, "end": len(excerpt)},
        }
        options = _normalize_options_for_finding(
            finding,
            [
                {
                    "patch": {"replacement": "It ended the way it started."},
                    "reason": "Bad: starts mid-span.",
                },
                {
                    "patch": {"replacement": "gap in a wall. It ended cleanly."},
                    "reason": "Good: rewrites from excerpt start.",
                },
                {
                    "patch": {"replacement": "gap in a wall. A cleaner ending."},
                    "reason": "Another full-span rewrite.",
                },
            ],
        )
        replacements = [option["patch"]["replacement"] for option in options]
        self.assertEqual(len(replacements), 2)
        self.assertNotIn("It ended the way it started.", replacements)
        self.assertIn("gap in a wall. It ended cleanly.", replacements)


if __name__ == "__main__":
    unittest.main()
