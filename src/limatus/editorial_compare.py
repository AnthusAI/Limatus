"""Read-only comparison and ranking of editorial draft candidates."""
from __future__ import annotations

from typing import Any, Callable

from .editorial_diagnosis_schema import (
    FINDING_ARRAY_KEYS,
    RUBRIC_DIMENSIONS,
    coerce_rubric,
)
from .editorial_judge import JudgeResolver
from .editorial_scan import scan_draft
from .editorial_style import (
    COMPARE_HARD_CONSTRAINT_UNSUPPORTED_CLAIMS_INCREASE,
    LoadedStyleProfile,
    StyleProfile,
)

COMPARE_SCHEMA_VERSION = 1
RANKING_METHOD = "always_lane_lexicographic_v1"
HARD_CONSTRAINT_UNSUPPORTED_INCREASE = COMPARE_HARD_CONSTRAINT_UNSUPPORTED_CLAIMS_INCREASE

AlignmentResolver = Callable[
    [str, list[dict[str, str]], LoadedStyleProfile],
    dict[str, Any],
]

_ARRAY_KEYS_FOR_DELTA = tuple(FINDING_ARRAY_KEYS) + ("repetition_groups",)


def compare_candidates(
    baseline_text: str,
    candidates: list[dict[str, str]],
    *,
    style_profile: LoadedStyleProfile,
    surface: str | None = None,
    mode: str = "rank",
    judge_resolver: JudgeResolver | None = None,
    alignment_resolver: AlignmentResolver | None = None,
) -> dict[str, Any]:
    """Rank candidates against a baseline using inspectable always-lane deltas."""
    if not isinstance(baseline_text, str):
        raise TypeError("baseline_text must be a string")
    if not isinstance(style_profile, LoadedStyleProfile):
        raise TypeError("style_profile must be a loaded style profile")
    if mode not in {"rank", "regression"}:
        raise ValueError("mode must be 'rank' or 'regression'")
    if not candidates:
        raise ValueError("at least one candidate is required")
    for entry in candidates:
        if not isinstance(entry, dict):
            raise TypeError("each candidate must be a mapping")
        if not isinstance(entry.get("id"), str) or not entry["id"].strip():
            raise ValueError("each candidate requires a non-empty id")
        if not isinstance(entry.get("text"), str):
            raise TypeError("each candidate text must be a string")

    if mode == "rank" and len(candidates) < 2:
        raise ValueError("rank mode requires at least two candidates")

    hard_constraints = style_profile.profile.compare_hard_constraints

    baseline_scan = scan_draft(
        baseline_text,
        style_profile=style_profile,
        surface=surface,
        judge_resolver=judge_resolver,
    )

    scored: list[dict[str, Any]] = []
    for entry in candidates:
        candidate_scan = scan_draft(
            entry["text"],
            style_profile=style_profile,
            surface=surface,
            judge_resolver=judge_resolver,
        )
        always_lane_deltas = _always_lane_deltas(baseline_scan, candidate_scan)
        violations = _hard_constraint_violations(always_lane_deltas, hard_constraints)
        rubric_deltas = _rubric_deltas(baseline_scan, candidate_scan)
        sort_key = _sort_key(always_lane_deltas, rubric_deltas, entry["id"])
        scored.append(
            {
                "id": entry["id"],
                "eligible_for_rank_1": not violations,
                "hard_constraint_violations": violations,
                "always_lane_deltas": always_lane_deltas,
                "rubric_deltas": rubric_deltas,
                "_sort_key": sort_key,
            }
        )

    ordered = _assign_ranks(scored)

    report: dict[str, Any] = {
        "schemaVersion": COMPARE_SCHEMA_VERSION,
        "mode": mode,
        "baseline": {"id": "baseline"},
        "ranking": {
            "method": RANKING_METHOD,
            "description": "Inspectable finding-count deltas; hard constraints; stable id tie-break.",
        },
        "candidates": [
            {
                "id": item["id"],
                "rank": item["rank"],
                "eligibleForRank1": item["eligible_for_rank_1"],
                "hardConstraintViolations": item["hard_constraint_violations"],
                "alwaysLaneDeltas": item["always_lane_deltas"],
                "rubricDeltas": item["rubric_deltas"],
            }
            for item in ordered
        ],
    }
    if alignment_resolver is not None:
        alignment = alignment_resolver(baseline_text, candidates, style_profile)
        report["guidelineAlignment"] = {
            "question": _guideline_alignment_question(style_profile.profile),
            "winnerId": alignment.get("winnerId"),
            "rationale": alignment.get("rationale"),
        }
    return report


def compare_regression(
    original_text: str,
    working_text: str,
    *,
    style_profile: LoadedStyleProfile,
    surface: str | None = None,
    judge_resolver: JudgeResolver | None = None,
) -> dict[str, Any]:
    return compare_candidates(
        original_text,
        [{"id": "working", "text": working_text}],
        style_profile=style_profile,
        surface=surface,
        mode="regression",
        judge_resolver=judge_resolver,
    )


def _always_lane_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    arrays: dict[str, dict[str, int]] = {}
    for key in _ARRAY_KEYS_FOR_DELTA:
        baseline_count = len(baseline.get(key, []))
        candidate_count = len(candidate.get(key, []))
        arrays[key] = {
            "baseline": baseline_count,
            "candidate": candidate_count,
            "delta": candidate_count - baseline_count,
        }

    kinds: dict[str, dict[str, int]] = {}
    baseline_kinds = _count_kinds(baseline)
    candidate_kinds = _count_kinds(candidate)
    for kind in sorted(set(baseline_kinds) | set(candidate_kinds)):
        base = baseline_kinds.get(kind, 0)
        cand = candidate_kinds.get(kind, 0)
        kinds[kind] = {"baseline": base, "candidate": cand, "delta": cand - base}

    density: dict[str, dict[str, float | int]] = {}
    baseline_density = baseline.get("density")
    candidate_density = candidate.get("density")
    if isinstance(baseline_density, dict) or isinstance(candidate_density, dict):
        for field in ("wordCount", "sentenceCount", "lexicalDensity", "gzipRatio"):
            base_val = _density_field(baseline_density, field)
            cand_val = _density_field(candidate_density, field)
            if base_val is None and cand_val is None:
                continue
            base_num = base_val if base_val is not None else 0
            cand_num = cand_val if cand_val is not None else 0
            delta = cand_num - base_num if isinstance(base_num, (int, float)) else 0
            density[field] = {
                "baseline": base_num,
                "candidate": cand_num,
                "delta": round(delta, 4) if isinstance(delta, float) else delta,
            }

    return {"arrays": arrays, "kinds": kinds, "density": density}


def _density_field(density: Any, field: str) -> float | int | None:
    if not isinstance(density, dict):
        return None
    value = density.get(field)
    if isinstance(value, (int, float)):
        return value
    return None


def _count_kinds(diagnosis: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in _ARRAY_KEYS_FOR_DELTA:
        for finding in diagnosis.get(key, []):
            if not isinstance(finding, dict):
                continue
            kind = str(finding.get("kind") or "unknown")
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def _guideline_alignment_question(profile: StyleProfile) -> str:
    tone = "; ".join(profile.tone)
    aim_text = profile.editorial_aim if profile.editorial_aim else "(not specified)"
    return (
        f"Which candidate better matches this profile's audience ({profile.audience}), "
        f"tone ({tone}), and editorial aim ({aim_text})?"
    )


def _hard_constraint_violations(
    always_lane_deltas: dict[str, Any],
    constraints: tuple[str, ...],
) -> list[dict[str, Any]]:
    if HARD_CONSTRAINT_UNSUPPORTED_INCREASE not in constraints:
        return []
    unsupported = always_lane_deltas["arrays"]["unsupported_claims"]
    delta = unsupported["delta"]
    if delta > 0:
        return [
            {
                "constraint": HARD_CONSTRAINT_UNSUPPORTED_INCREASE,
                "baseline": unsupported["baseline"],
                "candidate": unsupported["candidate"],
                "delta": delta,
            }
        ]
    return []


def _rubric_deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    baseline_rubric = coerce_rubric(baseline.get("rubric"))
    candidate_rubric = coerce_rubric(candidate.get("rubric"))
    if baseline_rubric is None or candidate_rubric is None:
        return None
    deltas: dict[str, dict[str, int]] = {}
    for name in RUBRIC_DIMENSIONS:
        base_score = int(baseline_rubric[name]["score"])
        cand_score = int(candidate_rubric[name]["score"])
        deltas[name] = {
            "baseline": base_score,
            "candidate": cand_score,
            "delta": cand_score - base_score,
        }
    return deltas


def _sort_key(
    always_lane_deltas: dict[str, Any],
    rubric_deltas: dict[str, Any] | None,
    candidate_id: str,
) -> tuple[Any, ...]:
    arrays = always_lane_deltas["arrays"]
    positive_finding_delta = sum(max(0, arrays[key]["delta"]) for key in _ARRAY_KEYS_FOR_DELTA)
    unsupported_delta = arrays["unsupported_claims"]["delta"]
    repetition_delta = arrays["repetition_groups"]["delta"]
    kind_delta_sum = sum(
        max(0, value["delta"]) for value in always_lane_deltas["kinds"].values()
    )
    rubric_tiebreak = 0
    if rubric_deltas is not None:
        rubric_tiebreak = -sum(int(item["delta"]) for item in rubric_deltas.values())
    return (
        positive_finding_delta,
        unsupported_delta,
        repetition_delta,
        kind_delta_sum,
        rubric_tiebreak,
        candidate_id,
    )


def _assign_ranks(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [item for item in scored if item["eligible_for_rank_1"]]
    ineligible = [item for item in scored if not item["eligible_for_rank_1"]]
    eligible.sort(key=lambda item: item["_sort_key"])
    ineligible.sort(key=lambda item: item["_sort_key"])

    ordered = eligible + ineligible
    if eligible:
        # Hard constraint: ineligible cannot be rank 1.
        for index, item in enumerate(ordered, start=1):
            item["rank"] = index
        if not ordered[0]["eligible_for_rank_1"]:
            # All ineligible — still rank everyone, none eligible for rank 1.
            pass
    else:
        for index, item in enumerate(ordered, start=1):
            item["rank"] = index

    return ordered


__all__ = [
    "AlignmentResolver",
    "COMPARE_SCHEMA_VERSION",
    "HARD_CONSTRAINT_UNSUPPORTED_INCREASE",
    "RANKING_METHOD",
    "compare_candidates",
    "compare_regression",
]
