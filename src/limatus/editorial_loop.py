"""Read-only helpers for the agent copy-edit loop (scan → decide → options → compare)."""
from __future__ import annotations

from typing import Any

from .editorial_apply import preview_patch_text
from .editorial_compare_schema import validate_compare_report
from .editorial_diagnosis_schema import (
    EditorialDiagnosisValidationError,
    FINDING_ARRAY_KEYS,
    assert_no_forbidden_output_keys,
    validate_diagnosis,
)
from .editorial_judge import JUDGE_PROMPT_VERSION
from .editorial_options_schema import validate_decisions, validate_options

LOOP_RECORD_SCHEMA_VERSION = 1


class EditorialLoopValidationError(ValueError):
    """Raised when a composed loop record fails validation."""


def _collect_leaf_findings(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key in FINDING_ARRAY_KEYS:
        findings.extend(diagnosis.get(key, []))
    for group in diagnosis.get("repetition_groups", []):
        if isinstance(group, dict):
            findings.extend(group.get("members", []))
    return findings


def assert_scan_has_no_steering_decisions(diagnosis: dict[str, Any]) -> None:
    """Scan output must not include steering decisions invented by the scanner."""

    validated = validate_diagnosis(diagnosis)
    if "decisions" in validated:
        raise EditorialDiagnosisValidationError("Scan JSON must not include a decisions field.")
    for finding in _collect_leaf_findings(validated):
        if "decision" in finding:
            raise EditorialDiagnosisValidationError(
                f"Finding {finding.get('id')} must not include a decision field from scan."
            )


def candidates_from_options(draft_text: str, options: dict[str, Any]) -> list[dict[str, str]]:
    """Expand patch options into full-draft candidate texts without mutating files."""

    if not isinstance(draft_text, str):
        raise ValueError("draft_text must be a string.")
    validated = validate_options(options)
    candidates: list[dict[str, str]] = []
    for finding in validated["findings"]:
        for option in finding["options"]:
            option_id = option["id"]
            candidates.append(
                {
                    "id": option_id,
                    "text": preview_patch_text(draft_text, option["patch"]),
                }
            )
    return candidates


def _judge_prompt_versions(scan: dict[str, Any]) -> list[str]:
    versions: list[str] = []
    for finding in _collect_leaf_findings(scan):
        if finding.get("source") == "judge":
            version = finding.get("promptVersion")
            if isinstance(version, str) and version.strip():
                versions.append(version.strip())
    return sorted(set(versions))


def compose_loop_record(
    scan: dict[str, Any],
    decisions: list[dict[str, Any]],
    options: dict[str, Any],
    compare_report: dict[str, Any],
    *,
    options_model: str = "",
    skill_path: str = "",
) -> dict[str, Any]:
    """Assemble an audit record for a loop pass without persistence or I/O."""

    assert_scan_has_no_steering_decisions(scan)
    validated_decisions = validate_decisions(decisions)
    validated_options = validate_options(options)
    validated_compare = validate_compare_report(compare_report)

    record: dict[str, Any] = {
        "schemaVersion": LOOP_RECORD_SCHEMA_VERSION,
        "scan": scan,
        "decisions": validated_decisions,
        "options": validated_options,
        "compareReport": validated_compare,
        "provenance": {
            "optionsModel": options_model.strip(),
            "skillPath": skill_path.strip(),
            "judgePromptVersions": _judge_prompt_versions(scan),
        },
    }
    if not record["provenance"]["judgePromptVersions"]:
        record["provenance"]["judgePromptVersionDefault"] = JUDGE_PROMPT_VERSION
    return validate_loop_record(record)


def validate_loop_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise EditorialLoopValidationError("Loop record must be a mapping.")
    for forbidden in ("revised_text", "rewritten_prose", "revisedProse", "revisedText"):
        if forbidden in payload:
            raise EditorialLoopValidationError(f"Loop record must not include '{forbidden}'.")
    if payload.get("schemaVersion") != LOOP_RECORD_SCHEMA_VERSION:
        raise EditorialLoopValidationError(
            f"Unsupported schemaVersion: expected {LOOP_RECORD_SCHEMA_VERSION}."
        )
    for key in ("scan", "decisions", "options", "compareReport", "provenance"):
        if key not in payload:
            raise EditorialLoopValidationError(f"Loop record missing required field '{key}'.")
    assert_no_forbidden_output_keys(payload["scan"])
    validate_diagnosis(payload["scan"])
    assert_scan_has_no_steering_decisions(payload["scan"])
    assert_no_forbidden_output_keys(payload["compareReport"])
    validate_decisions(payload["decisions"])
    validate_options(payload["options"])
    validate_compare_report(payload["compareReport"])
    provenance = payload["provenance"]
    if not isinstance(provenance, dict):
        raise EditorialLoopValidationError("provenance must be a mapping.")
    return payload


__all__ = [
    "EditorialLoopValidationError",
    "LOOP_RECORD_SCHEMA_VERSION",
    "assert_scan_has_no_steering_decisions",
    "candidates_from_options",
    "compose_loop_record",
    "validate_loop_record",
]
