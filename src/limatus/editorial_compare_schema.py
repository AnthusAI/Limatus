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
    return payload


__all__ = ["EditorialCompareValidationError", "validate_compare_report"]
