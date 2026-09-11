from __future__ import annotations

from typing import Any

from .editorial_diagnosis_schema import assert_no_forbidden_output_keys


class EditorialCompareValidationError(ValueError):
    """Raised when compare JSON fails schema validation."""


def validate_compare_report(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EditorialCompareValidationError("Compare JSON must be a mapping.")
    assert_no_forbidden_output_keys(payload)
    if payload.get("schemaVersion") != 1:
        raise EditorialCompareValidationError("Unsupported schemaVersion for compare report.")
    if payload.get("mode") not in {"rank", "regression"}:
        raise EditorialCompareValidationError("mode must be rank or regression.")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise EditorialCompareValidationError("candidates must be a non-empty list.")
    ranks = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise EditorialCompareValidationError(f"candidates[{index}] must be a mapping.")
        rank = candidate.get("rank")
        if not isinstance(rank, int) or rank < 1:
            raise EditorialCompareValidationError(f"candidates[{index}].rank must be a positive integer.")
        ranks.append(rank)
        if "alwaysLaneDeltas" not in candidate:
            raise EditorialCompareValidationError(f"candidates[{index}] missing alwaysLaneDeltas.")
    if sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise EditorialCompareValidationError("candidate ranks must be a permutation of 1..N.")
    alignment = payload.get("guidelineAlignment")
    if alignment is not None:
        if not isinstance(alignment, dict):
            raise EditorialCompareValidationError("guidelineAlignment must be a mapping when present.")
        required_keys = {"question", "winnerId", "rationale"}
        if set(alignment.keys()) != required_keys:
            raise EditorialCompareValidationError(
                "guidelineAlignment must contain exactly question, winnerId, and rationale."
            )
        if not isinstance(alignment["question"], str) or not alignment["question"].strip():
            raise EditorialCompareValidationError("guidelineAlignment.question must be a non-empty string.")
        winner_id = alignment["winnerId"]
        if winner_id is not None and (not isinstance(winner_id, str) or not winner_id.strip()):
            raise EditorialCompareValidationError(
                "guidelineAlignment.winnerId must be a non-empty string or null."
            )
        if not isinstance(alignment["rationale"], str):
            raise EditorialCompareValidationError("guidelineAlignment.rationale must be a string.")
    return payload


__all__ = ["EditorialCompareValidationError", "validate_compare_report"]
