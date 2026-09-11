"""Pure helpers for offline editorial eval aggregate metrics."""
from __future__ import annotations


def finding_kind_counts(expected_kinds: set[str], diagnosis_kinds: set[str]) -> tuple[int, int, int]:
    """Return (tp, fp, fn) for kind-level micro-averaging."""
    tp = len(expected_kinds & diagnosis_kinds)
    fn = len(expected_kinds - diagnosis_kinds)
    fp = len(diagnosis_kinds - expected_kinds)
    return tp, fp, fn


def ratio_from_counts(numerator: int, denominator: int) -> float:
    """Precision/recall style ratio; empty denominator is perfect (1.0)."""
    if denominator == 0:
        return 1.0
    return numerator / denominator


def micro_precision_recall(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = ratio_from_counts(tp, tp + fp)
    recall = ratio_from_counts(tp, tp + fn)
    return precision, recall


def option_unsupported_claim_rate(options: list[dict[str, object]]) -> tuple[float, int]:
    """Share of rewrite option candidates flagged ``factVerificationRequired``."""
    total = 0
    flagged = 0
    for entry in options:
        for candidate in entry.get("options", []):
            if not isinstance(candidate, dict):
                continue
            total += 1
            if candidate.get("factVerificationRequired") is True:
                flagged += 1
    rate = ratio_from_counts(flagged, total)
    return rate, total
