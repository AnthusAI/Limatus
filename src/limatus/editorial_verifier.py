"""Read-only, advisory verification for an explicitly applied draft revision.

The verifier compares two caller-owned strings.  It never writes either draft,
applies a patch, or publishes a result.  Scores are deliberately simple and
inspectable; they are editorial quality signals, not detector scores.
"""
from __future__ import annotations

import re
from typing import Any

from .editorial_compare import compare_regression
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
# Same as _FACT_PATTERN minus the bare-URL branch. Used only for the
# "did a brand-new risky claim appear" diff: a newly added citation link is
# the encouraged edit under this profile's own evidenceRules ("link a
# source in the sentence it supports"), so adding one must never by itself
# read as introducing a new, unverified fact. A newly added number, year, or
# absolute word still does -- that is a real new claim, not a citation.
_RISK_FACT_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?%?\b|\b20\d{2}\b|\b(?:always|never|eliminates?|proves?|guarantees?)\b)",
    re.IGNORECASE,
)
_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9']+")

# Two thresholds decide whether a working-copy sentence still carries the
# same claim as an original sentence whose exact wording is gone.
#
# FACT_OVERLAP is checked first and is strict: the two sentences must share
# almost all of the same concrete facts (numbers, years, links, absolute
# words) -- this is what actually identifies "the same claim," and it is
# what a citation-adding rewrite always preserves.
#
# WORD_OVERLAP is a lower-bar sanity check on top: it guards against two
# sentences that coincidentally cite the same fact (two different claims
# that both happen to mention "2018") being treated as one claim just
# because they share that one token.
_SIMILAR_CLAIM_FACT_OVERLAP = 0.75
_SIMILAR_CLAIM_WORD_OVERLAP = 0.35


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

    compare_regression(
        original_text,
        working_text,
        style_profile=style_profile,
    )

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


def _fact_tokens(sentence: str) -> set[str]:
    return set(_FACT_PATTERN.findall(sentence.lower()))


def _claim_preserved(original_sentence: str, working_sentences: list[str]) -> bool:
    """Whether some sentence in the working copy still carries the same claim
    as `original_sentence`, even if no working sentence matches it exactly.

    Exact match (after normalization) is checked first and is enough on its
    own -- most of a draft is untouched between revisions, and this keeps the
    common case cheap. Where the wording did change, a working sentence
    counts as carrying the same claim only if it contains almost all of the
    *original's own* facts -- containment, not symmetric overlap, because a
    legitimate edit adds a citation alongside a kept fact, and a symmetric
    measure would count that added fact against the match precisely when it
    should not. Requiring enough general vocabulary overlap on top still
    rules out a coincidental match between two unrelated claims that happen
    to cite the same year or number.
    """
    normalized_original = _normalize(original_sentence)
    if normalized_original in {_normalize(candidate) for candidate in working_sentences}:
        return True

    original_facts = _fact_tokens(original_sentence)
    if not original_facts:
        return False
    original_words = set(tokenize(original_sentence))

    for candidate in working_sentences:
        candidate_facts = _fact_tokens(candidate)
        if not candidate_facts:
            continue
        fact_containment = len(original_facts & candidate_facts) / len(original_facts)
        if fact_containment < _SIMILAR_CLAIM_FACT_OVERLAP:
            continue
        # Containment here too, for the same reason as the fact check: a
        # common legitimate edit merges two short sentences into one longer
        # one (or the reverse), which shrinks symmetric Jaccard by inflating
        # the union even when almost every word of the original is still
        # present somewhere in the candidate.
        candidate_words = set(tokenize(candidate))
        word_containment = len(original_words & candidate_words) / len(original_words)
        if word_containment >= _SIMILAR_CLAIM_WORD_OVERLAP:
            return True
    return False


def _sentence_carrying_fact(working: str, fact: str) -> str | None:
    """The first sentence in the working copy that actually contains a newly
    introduced factual token, so a finding points at readable context instead
    of a bare token like "1993"."""
    for sentence in sentences(working):
        if fact in sentence.lower():
            return sentence
    return None


def _findings(original: str, working: str, original_diagnosis: dict[str, Any], working_diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    working_sentence_list = sentences(working)
    for sentence in sentences(original):
        if not _FACT_PATTERN.search(sentence):
            continue
        if _claim_preserved(sentence, working_sentence_list):
            continue
        findings.append(
            {
                "kind": "deleted_claim",
                "evidence": sentence,
                "rationale": (
                    "This sentence's claim does not appear, in this or any "
                    "sufficiently similar reworded form, anywhere in the working copy."
                ),
            }
        )
    original_facts = set(_RISK_FACT_PATTERN.findall(original.lower()))
    working_facts = set(_RISK_FACT_PATTERN.findall(working.lower()))
    for fact in sorted(working_facts - original_facts):
        carrying_sentence = _sentence_carrying_fact(working, fact)
        findings.append(
            {
                "kind": "factual_change_risk",
                "evidence": carrying_sentence or fact,
                "rationale": f"Introduces '{fact}', a factual token not present in the original.",
            }
        )
    for finding in working_diagnosis.get("unsupported_claims", []):
        findings.append({"kind": "unsupported_claim", "evidence": finding["excerpt"], "rationale": finding["rationale"]})
    for group in working_diagnosis.get("repetition_groups", []):
        members = group.get("members") or []
        excerpts = [member["excerpt"] for member in members if member.get("excerpt")]
        evidence = excerpts[0] if excerpts else ""
        rationale = group.get("rationale", "Repeated phrasing.")
        if len(excerpts) > 1:
            rationale = f"{rationale} Repeats {len(excerpts)} times, including: " + " / ".join(excerpts)
        findings.append({"kind": "duplication", "evidence": evidence, "rationale": rationale})
    for finding in working_diagnosis.get("generic_passages", []):
        if finding.get("kind") in {"empty_leadin", "vague_claim", "list_shaped_prose"}:
            findings.append({"kind": "residual_boilerplate", "evidence": finding["excerpt"], "rationale": finding["rationale"]})
    return findings


def _factual_change_risk(original: str, working: str) -> float:
    original_facts = set(_RISK_FACT_PATTERN.findall(original.lower()))
    working_facts = set(_RISK_FACT_PATTERN.findall(working.lower()))
    working_sentence_list = sentences(working)
    deleted_claims = sum(
        1
        for sentence in sentences(original)
        if _FACT_PATTERN.search(sentence) and not _claim_preserved(sentence, working_sentence_list)
    )
    return _clamp((len(working_facts - original_facts) + deleted_claims) / 4)


def _normalize(value: str) -> str:
    return _NORMALIZE_PATTERN.sub(" ", value.lower()).strip()


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


__all__ = ["DEFAULT_ACCEPTANCE_THRESHOLD", "SCORE_WEIGHTS", "verify_revision"]
