from __future__ import annotations

import unittest

from limatus.editorial_eval_metrics import (
    finding_kind_counts,
    micro_precision_recall,
    option_unsupported_claim_rate,
    ratio_from_counts,
)


class EditorialEvalMetricsTests(unittest.TestCase):
    def test_ratio_empty_denominator_is_perfect(self) -> None:
        self.assertEqual(ratio_from_counts(0, 0), 1.0)

    def test_micro_precision_recall_zero_counts(self) -> None:
        precision, recall = micro_precision_recall(0, 0, 0)
        self.assertEqual(precision, 1.0)
        self.assertEqual(recall, 1.0)

    def test_finding_kind_counts_mixed(self) -> None:
        tp, fp, fn = finding_kind_counts({"a", "b"}, {"b", "c"})
        self.assertEqual((tp, fp, fn), (1, 1, 1))
        precision, recall = micro_precision_recall(tp, fp, fn)
        self.assertAlmostEqual(precision, 0.5)
        self.assertAlmostEqual(recall, 0.5)

    def test_option_unsupported_claim_rate(self) -> None:
        findings = [
            {
                "findingId": "finding-0000000000000001",
                "options": [
                    {"factVerificationRequired": False},
                    {"factVerificationRequired": True},
                ],
            }
        ]
        rate, count = option_unsupported_claim_rate(findings)
        self.assertEqual(count, 2)
        self.assertAlmostEqual(rate, 0.5)


if __name__ == "__main__":
    unittest.main()
