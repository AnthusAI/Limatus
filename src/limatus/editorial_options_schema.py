from __future__ import annotations

import re
from typing import Any

from .editorial_diagnosis import normalize_finding_decision
from .editorial_diagnosis_schema import STABLE_ID_PATTERN
from ._util import hash_short

SCHEMA_VERSION = 1

OPTION_ID_PATTERN = re.compile(r"^option-[a-f0-9]{16}$")
CANDIDATE_ID_PATTERN = re.compile(r"^candidate-[a-f0-9]{16}$")

FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "revised_text",
        "rewritten_prose",
        "revisedProse",
        "revisedText",
        "embedder",
    }
)


class EditorialOptionsValidationError(ValueError):
    """Raised when editorial options or decisions JSON fails schema validation."""


def stable_option_id(finding_id: str, replacement: str, reason: str) -> str:
    return f"option-{hash_short([SCHEMA_VERSION, finding_id, replacement, reason])}"


def assert_no_forbidden_output_keys(value: Any, key_path: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            current_path = f"{key_path}.{key_text}" if key_path else key_text
            if key_text in FORBIDDEN_OUTPUT_KEYS:
                raise EditorialOptionsValidationError(
                    f"Editorial options JSON contains forbidden rewrite field '{current_path}'"
                )
            assert_no_forbidden_output_keys(nested, current_path)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            assert_no_forbidden_output_keys(nested, f"{key_path}[{index}]")


def validate_decisions(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise EditorialOptionsValidationError("Decisions JSON must be a list.")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise EditorialOptionsValidationError(f"decisions[{index}] must be a mapping.")
        if entry.get("schemaVersion") != SCHEMA_VERSION:
            raise EditorialOptionsValidationError(
                f"decisions[{index}].schemaVersion must be {SCHEMA_VERSION}."
            )
        finding_id = entry.get("finding_id")
        if not isinstance(finding_id, str) or not STABLE_ID_PATTERN.match(finding_id):
            raise EditorialOptionsValidationError(
                f"decisions[{index}].finding_id must match finding-<16 hex chars>."
            )
        decision = normalize_finding_decision(entry.get("decision"))
        note = entry.get("note", "")
        if note is not None and not isinstance(note, str):
            raise EditorialOptionsValidationError(f"decisions[{index}].note must be a string.")
        validated.append(
            {
                "schemaVersion": SCHEMA_VERSION,
                "finding_id": finding_id,
                "decision": decision,
                "note": str(note or "").strip(),
            }
        )
    return validated


def validate_options(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EditorialOptionsValidationError("Editorial options JSON must be a mapping.")

    assert_no_forbidden_output_keys(payload)

    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise EditorialOptionsValidationError(
            f"Unsupported schemaVersion: expected {SCHEMA_VERSION}."
        )

    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise EditorialOptionsValidationError("findings must be a list.")

    validated_findings: list[dict[str, Any]] = []
    for index, entry in enumerate(findings):
        validated_findings.append(_validate_finding_options(entry, f"findings[{index}]"))

    return {"schemaVersion": SCHEMA_VERSION, "findings": validated_findings}


def stable_candidate_id(candidate_text: str, rationale: str) -> str:
    return f"candidate-{hash_short([SCHEMA_VERSION, candidate_text, rationale])}"


def validate_suggestions(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate review-only, document-level rewrite candidates.

    Candidate text is deliberately represented as data plus a full-document patch;
    this schema never writes or applies it.
    """
    if not isinstance(payload, dict):
        raise EditorialOptionsValidationError("Suggestions JSON must be a mapping.")
    assert_no_forbidden_output_keys(payload)
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise EditorialOptionsValidationError(f"Unsupported schemaVersion: expected {SCHEMA_VERSION}.")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise EditorialOptionsValidationError("candidates must be a non-empty list.")
    if len(candidates) > 3:
        raise EditorialOptionsValidationError("candidates must contain at most 3 candidates.")
    validated: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        location = f"candidates[{index}]"
        if not isinstance(candidate, dict):
            raise EditorialOptionsValidationError(f"{location} must be a mapping.")
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not CANDIDATE_ID_PATTERN.match(candidate_id):
            raise EditorialOptionsValidationError(f"{location}.id must match candidate-<16 hex chars>.")
        text = candidate.get("candidateText")
        if not isinstance(text, str):
            raise EditorialOptionsValidationError(f"{location}.candidateText must be a string.")
        rationale = candidate.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise EditorialOptionsValidationError(f"{location}.rationale must be a non-empty string.")
        diff = candidate.get("diff")
        if not isinstance(diff, str):
            raise EditorialOptionsValidationError(f"{location}.diff must be a string.")
        questions = candidate.get("unresolvedQuestions")
        if not isinstance(questions, list) or not all(isinstance(item, str) for item in questions):
            raise EditorialOptionsValidationError(f"{location}.unresolvedQuestions must be a list of strings.")
        warnings = candidate.get("factualVerificationWarnings")
        if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
            raise EditorialOptionsValidationError(
                f"{location}.factualVerificationWarnings must be a list of strings."
            )
        fact_required = candidate.get("factVerificationRequired")
        if not isinstance(fact_required, bool):
            raise EditorialOptionsValidationError(f"{location}.factVerificationRequired must be a boolean.")
        patch = candidate.get("patch")
        if not isinstance(patch, dict) or not isinstance(patch.get("span"), dict):
            raise EditorialOptionsValidationError(f"{location}.patch must contain a span mapping.")
        span = patch["span"]
        if span.get("start") != 0 or not isinstance(span.get("end"), int) or span["end"] < 0:
            raise EditorialOptionsValidationError(f"{location}.patch.span must cover the document from zero.")
        if patch.get("replacement") != text:
            raise EditorialOptionsValidationError(f"{location}.patch.replacement must equal candidateText.")
        validated.append({
            "id": candidate_id,
            "candidateText": text,
            "patch": {"span": {"start": 0, "end": span["end"]}, "replacement": text},
            "diff": diff,
            "rationale": rationale.strip(),
            "unresolvedQuestions": list(questions),
            "factualVerificationWarnings": list(warnings),
            "factVerificationRequired": fact_required,
        })
    return {"schemaVersion": SCHEMA_VERSION, "candidates": validated}


def _validate_finding_options(entry: Any, location: str) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise EditorialOptionsValidationError(f"{location} must be a mapping.")
    finding_id = entry.get("findingId")
    if not isinstance(finding_id, str) or not STABLE_ID_PATTERN.match(finding_id):
        raise EditorialOptionsValidationError(
            f"{location}.findingId must match finding-<16 hex chars>."
        )
    options = entry.get("options")
    if not isinstance(options, list) or not options:
        raise EditorialOptionsValidationError(f"{location}.options must be a non-empty list.")
    if len(options) > 3:
        raise EditorialOptionsValidationError(f"{location}.options must contain at most 3 options.")
    validated_options = [
        _validate_option(option, f"{location}.options[{option_index}]")
        for option_index, option in enumerate(options)
    ]
    return {"findingId": finding_id, "options": validated_options}


def _validate_option(entry: Any, location: str) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise EditorialOptionsValidationError(f"{location} must be a mapping.")
    option_id = entry.get("id")
    if not isinstance(option_id, str) or not OPTION_ID_PATTERN.match(option_id):
        raise EditorialOptionsValidationError(
            f"{location}.id must match option-<16 hex chars>."
        )
    patch = entry.get("patch")
    if not isinstance(patch, dict):
        raise EditorialOptionsValidationError(f"{location}.patch must be a mapping.")
    span = patch.get("span")
    if not isinstance(span, dict):
        raise EditorialOptionsValidationError(f"{location}.patch.span must be a mapping.")
    for coord in ("start", "end"):
        if not isinstance(span.get(coord), int) or span[coord] < 0:
            raise EditorialOptionsValidationError(
                f"{location}.patch.span.{coord} must be a non-negative integer."
            )
    if span["end"] < span["start"]:
        raise EditorialOptionsValidationError(f"{location}.patch.span end must be >= start.")
    replacement = patch.get("replacement")
    if not isinstance(replacement, str):
        raise EditorialOptionsValidationError(f"{location}.patch.replacement must be a string.")
    reason = entry.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise EditorialOptionsValidationError(f"{location}.reason must be a non-empty string.")
    fact_verification = entry.get("factVerificationRequired")
    if not isinstance(fact_verification, bool):
        raise EditorialOptionsValidationError(
            f"{location}.factVerificationRequired must be a boolean."
        )
    unresolved = entry.get("unresolvedQuestions")
    if not isinstance(unresolved, list):
        raise EditorialOptionsValidationError(
            f"{location}.unresolvedQuestions must be a list."
        )
    for question_index, question in enumerate(unresolved):
        if not isinstance(question, str):
            raise EditorialOptionsValidationError(
                f"{location}.unresolvedQuestions[{question_index}] must be a string."
            )
    voice_fidelity_warning = entry.get("voiceFidelityWarning")
    if voice_fidelity_warning is not None and not isinstance(voice_fidelity_warning, str):
        raise EditorialOptionsValidationError(
            f"{location}.voiceFidelityWarning must be a string or null."
        )
    return {
        "id": option_id,
        "patch": {
            "span": {"start": span["start"], "end": span["end"]},
            "replacement": replacement,
        },
        "reason": reason.strip(),
        "factVerificationRequired": fact_verification,
        "unresolvedQuestions": list(unresolved),
        "voiceFidelityWarning": voice_fidelity_warning,
    }
