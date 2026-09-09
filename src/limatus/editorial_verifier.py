"""Read-only, advisory verification for an explicitly applied draft revision.

The verifier compares two caller-owned strings.  It never writes either draft,
applies a patch, or publishes a result.  Scores are deliberately simple and
inspectable; they are editorial quality signals, not detector scores.
"""
from __future__ import annotations

import re
from typing import Any

from .editorial_diagnosis import _mask_yaml_frontmatter, diagnose_draft
from .editorial_style import LoadedStyleProfile
from .editorial_text import sentences, tokenize

DEFAULT_ACCEPTANCE_THRESHOLD = 0.05
SCORE_WEIGHTS = {
    "specificity": 0.25,
    "clarity": 0.25,
    "audience_fit": 0.25,
    "voice_match": 0.25,
    "redundancy": -0.10,
    "unsupported_claims": -0.20,
    "factual_change_risk": -0.20,
}

_FACT_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?%?\b|\b20\d{2}\b|https?://\S+|\b(?:always|never|eliminates?|proves?|guarantees?)\b)",
    re.IGNORECASE,
)
_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9']+")


def verify_revision(
    original_text: str,
    working_text: str,
    *,
    style_profile: LoadedStyleProfile,
    threshold: float = DEFAULT_ACCEPTANCE_THRESHOLD,
) -> dict[str, Any]:
    """Assess a working draft against an immutable original, without mutation.

    ``threshold`` is the required normalized net improvement.  Acceptance is
    advisory and requires both that improvement and no increase in unsupported
    claims.  The returned structure contains only inspectable editorial scores
    and evidence-backed findings.
    """
    if not isinstance(original_text, str) or not isinstance(working_text, str):
        raise TypeError("original_text and working_text must be strings")
    if not isinstance(style_profile, LoadedStyleProfile):
        raise TypeError("style_profile must be a loaded style profile")
    if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    # A leading YAML frontmatter block is metadata, not prose -- an edited
    # title or date should never register as a deleted claim or a factual
    # change. Masked once here so every text-scanning helper below sees the
    # same prose-only view diagnose_draft already uses internally.
    masked_original = _mask_yaml_frontmatter(original_text)
    masked_working = _mask_yaml_frontmatter(working_text)

    original_diagnosis = diagnose_draft(original_text, style_profile=style_profile)
    working_diagnosis = diagnose_draft(working_text, style_profile=style_profile)
    original_scores = _score_draft(masked_original, original_diagnosis, style_profile)
    working_scores = _score_draft(masked_working, working_diagnosis, style_profile)
    findings = _findings(masked_original, masked_working, original_diagnosis, working_diagnosis)
    factual_risk = _factual_change_risk(masked_original, masked_working)
    working_scores["factual_change_risk"] = factual_risk
    working_scores["total"] = _total_score(
        working_scores["specificity"],
        working_scores["clarity"],
        working_scores["audience_fit"],
        working_scores["voice_match"],
        working_scores["redundancy"],
        working_scores["unsupported_claims"],
        factual_risk,
    )

    original_unsupported = len(original_diagnosis["unsupported_claims"])
    working_unsupported = len(working_diagnosis["unsupported_claims"])
    net_improvement = round(working_scores["total"] - original_scores["total"], 4)
    recommendation = (
        "accept"
        if net_improvement >= threshold and working_unsupported <= original_unsupported
        else "reject"
    )
    return {
        "schemaVersion": 1,
        "recommendation": recommendation,
        "threshold": float(threshold),
        "net_improvement": net_improvement,
        "weights": dict(SCORE_WEIGHTS),
        "dimensions": {
            key: {"original": original_scores[key], "working": working_scores[key], "change": round(working_scores[key] - original_scores[key], 4)}
            for key in ("specificity", "clarity", "audience_fit", "voice_match")
        },
        "penalties": {
            key: {"original": original_scores[key], "working": working_scores[key], "change": round(working_scores[key] - original_scores[key], 4)}
            for key in ("redundancy", "unsupported_claims", "factual_change_risk")
        },
        "unsupported_claims": {"original": original_unsupported, "working": working_unsupported},
        "findings": findings,
    }


def _score_draft(text: str, diagnosis: dict[str, Any], profile: LoadedStyleProfile) -> dict[str, float]:
    words = tokenize(text)
    word_total = max(len(words), 1)
    finding_count = sum(len(diagnosis.get(key, [])) for key in ("generic_passages", "voice_observations", "required_facts"))
    redundancy = len(diagnosis.get("repetition_groups", []))
    unsupported = len(diagnosis.get("unsupported_claims", []))
    specific_tokens = sum(bool(re.search(r"\d|https?://|latency|cost|failure|verify|inspect", word, re.I)) for word in words)
    specificity = _clamp(0.55 + (specific_tokens / word_total) * 1.5 - finding_count * 0.04)
    clarity = _clamp(0.88 - finding_count * 0.06 - redundancy * 0.04)
    preferred = {term.lower() for term in profile.profile.lexicon_prefer}
    avoided = {term.lower() for term in profile.profile.lexicon_avoid}
    lowered = text.lower()
    audience_fit = _clamp(0.65 + min(sum(term in lowered for term in preferred), 4) * 0.07)
    voice_match = _clamp(0.88 - sum(term in lowered for term in avoided) * 0.12 - len(diagnosis.get("voice_observations", [])) * 0.06)
    factual_change_risk = 0.0
    return {
        "specificity": specificity,
        "clarity": clarity,
        "audience_fit": audience_fit,
        "voice_match": voice_match,
        "redundancy": _clamp(redundancy / 4),
        "unsupported_claims": _clamp(unsupported / 4),
        "factual_change_risk": factual_change_risk,
        "total": 0.0,
    } | {"total": _total_score(specificity, clarity, audience_fit, voice_match, redundancy / 4, unsupported / 4, factual_change_risk)}


def _total_score(specificity: float, clarity: float, audience_fit: float, voice_match: float, redundancy: float, unsupported: float, factual_change_risk: float) -> float:
    return round(
        SCORE_WEIGHTS["specificity"] * specificity
        + SCORE_WEIGHTS["clarity"] * clarity
        + SCORE_WEIGHTS["audience_fit"] * audience_fit
        + SCORE_WEIGHTS["voice_match"] * voice_match
        + SCORE_WEIGHTS["redundancy"] * redundancy
        + SCORE_WEIGHTS["unsupported_claims"] * unsupported
        + SCORE_WEIGHTS["factual_change_risk"] * factual_change_risk,
        4,
    )


def _findings(original: str, working: str, original_diagnosis: dict[str, Any], working_diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    original_sentences = {_normalize(sentence) for sentence in sentences(original)}
    working_sentences = {_normalize(sentence) for sentence in sentences(working)}
    for sentence in sentences(original):
        normalized = _normalize(sentence)
        if normalized and normalized not in working_sentences and _FACT_PATTERN.search(sentence):
            findings.append({"kind": "deleted_claim", "evidence": sentence})
    original_facts = set(_FACT_PATTERN.findall(original.lower()))
    working_facts = set(_FACT_PATTERN.findall(working.lower()))
    for fact in sorted(working_facts - original_facts):
        findings.append({"kind": "factual_change_risk", "evidence": f"new factual token: {fact}"})
    for finding in working_diagnosis.get("unsupported_claims", []):
        findings.append({"kind": "unsupported_claim", "evidence": finding["excerpt"], "rationale": finding["rationale"]})
    for group in working_diagnosis.get("repetition_groups", []):
        findings.append({"kind": "duplication", "evidence": group.get("excerpt", ""), "rationale": group.get("rationale", "Repeated phrasing.")})
    for finding in working_diagnosis.get("generic_passages", []):
        if finding.get("kind") in {"empty_leadin", "vague_claim", "list_shaped_prose"}:
            findings.append({"kind": "residual_boilerplate", "evidence": finding["excerpt"], "rationale": finding["rationale"]})
    return findings


def _factual_change_risk(original: str, working: str) -> float:
    original_facts = set(_FACT_PATTERN.findall(original.lower()))
    working_facts = set(_FACT_PATTERN.findall(working.lower()))
    deleted_claims = sum(
        1
        for sentence in sentences(original)
        if _FACT_PATTERN.search(sentence) and _normalize(sentence) not in {_normalize(item) for item in sentences(working)}
    )
    return _clamp((len(working_facts - original_facts) + deleted_claims) / 4)


def _normalize(value: str) -> str:
    return _NORMALIZE_PATTERN.sub(" ", value.lower()).strip()


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


__all__ = ["DEFAULT_ACCEPTANCE_THRESHOLD", "SCORE_WEIGHTS", "verify_revision"]
