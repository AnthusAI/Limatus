from __future__ import annotations

import copy
from typing import Any

from .editorial_diagnosis import diagnose_draft
from .editorial_diagnosis_schema import FINDING_ARRAY_KEYS, coerce_rubric, validate_diagnosis
from .editorial_judge import JudgeResolver, resolve_judge_lane
from .editorial_style import LoadedStyleProfile

_KIND_TO_ARRAY: dict[str, str] = {
    "unsupported_certainty": "unsupported_claims",
    "missing_attribution": "required_facts",
    "required_fact": "required_facts",
    "voice_mismatch": "voice_observations",
    "uniform_cadence": "voice_observations",
    "uncontracted_form": "voice_observations",
}


def _array_key_for_finding(finding: dict[str, Any]) -> str:
    kind = str(finding.get("kind") or "")
    return _KIND_TO_ARRAY.get(kind, "generic_passages")


def union_judge_findings(profile_diagnosis: dict[str, Any], judge_findings: list[dict[str, Any]]) -> dict[str, Any]:
    if not judge_findings:
        return profile_diagnosis
    merged = copy.deepcopy(profile_diagnosis)
    for finding in judge_findings:
        array_key = _array_key_for_finding(finding)
        if array_key not in FINDING_ARRAY_KEYS:
            array_key = "generic_passages"
        merged[array_key].append(finding)
    return merged


def scan_draft(
    draft_text: str,
    *,
    style_profile: LoadedStyleProfile,
    surface: str | None = None,
    judge_resolver: JudgeResolver | None = None,
    require_judge: bool = False,
) -> dict[str, Any]:
    profile_diagnosis = diagnose_draft(draft_text, style_profile=style_profile, surface=surface)
    judge_config = style_profile.profile.judge
    if judge_config is None:
        return profile_diagnosis

    lane = resolve_judge_lane(
        draft_text,
        style_profile,
        judge_config,
        judge_resolver=judge_resolver,
        require_judge=require_judge,
    )
    merged = union_judge_findings(profile_diagnosis, lane.findings)
    rubric = coerce_rubric(lane.rubric)
    if rubric is not None:
        merged = copy.deepcopy(merged)
        merged["rubric"] = rubric
    return validate_diagnosis(merged)
