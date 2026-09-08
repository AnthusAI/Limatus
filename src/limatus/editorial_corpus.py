from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .editorial_style import StyleProfileValidationError


def load_editorial_corpus_manifest(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    manifest_path = Path(path).resolve()
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise StyleProfileValidationError(f"Editorial corpus manifest must be a mapping: {manifest_path}")

    manifest: dict[str, Any] = {"mustFail": [], "mustPass": []}
    profile = raw.get("profile")
    if profile is not None:
        if not isinstance(profile, str) or not profile.strip():
            raise StyleProfileValidationError(f"profile must be a non-empty path in {manifest_path}")
        profile_path = (manifest_path.parent / profile).resolve()
        if not profile_path.is_file():
            raise StyleProfileValidationError(f"Corpus profile not found: {profile_path}")
        manifest["profile"] = str(profile_path)
    for section in ("mustFail", "mustPass"):
        entries = raw.get(section)
        if entries is None:
            continue
        if not isinstance(entries, list):
            raise StyleProfileValidationError(f"{section} must be a list in {manifest_path}")
        normalized: list[dict[str, Any]] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise StyleProfileValidationError(f"{section}[{index}] must be a mapping in {manifest_path}")
            entry_id = str(entry.get("id", "")).strip()
            rel_path = str(entry.get("path", "")).strip()
            if not entry_id or not rel_path:
                raise StyleProfileValidationError(
                    f"{section}[{index}] requires id and path in {manifest_path}"
                )
            draft_path = (manifest_path.parent / rel_path).resolve()
            if not draft_path.is_file():
                raise StyleProfileValidationError(f"Corpus draft not found: {draft_path}")
            normalized_entry = {"id": entry_id, "path": rel_path, "draftPath": str(draft_path)}
            entry_profile = entry.get("profile")
            if entry_profile is not None:
                if not isinstance(entry_profile, str) or not entry_profile.strip():
                    raise StyleProfileValidationError(
                        f"{section}[{index}].profile must be a non-empty path in {manifest_path}"
                    )
                entry_profile_path = (manifest_path.parent / entry_profile).resolve()
                if not entry_profile_path.is_file():
                    raise StyleProfileValidationError(f"Corpus profile not found: {entry_profile_path}")
                normalized_entry["profile"] = str(entry_profile_path)
            expect_kinds = entry.get("expectKinds", [])
            if not isinstance(expect_kinds, list) or any(not str(kind).strip() for kind in expect_kinds):
                raise StyleProfileValidationError(
                    f"{section}[{index}].expectKinds must be a list of non-empty strings in {manifest_path}"
                )
            normalized_entry["expectKinds"] = [str(kind).strip() for kind in expect_kinds]
            max_findings = entry.get("maxFindings")
            if max_findings is not None and (isinstance(max_findings, bool) or not isinstance(max_findings, int) or max_findings < 0):
                raise StyleProfileValidationError(
                    f"{section}[{index}].maxFindings must be a non-negative integer in {manifest_path}"
                )
            if max_findings is not None:
                normalized_entry["maxFindings"] = max_findings
            option_safety = entry.get("optionSafety", {})
            if not isinstance(option_safety, dict):
                raise StyleProfileValidationError(
                    f"{section}[{index}].optionSafety must be a mapping in {manifest_path}"
                )
            forbidden_keys = option_safety.get("forbidKeys", [])
            if not isinstance(forbidden_keys, list) or any(not str(key).strip() for key in forbidden_keys):
                raise StyleProfileValidationError(
                    f"{section}[{index}].optionSafety.forbidKeys must be a list of non-empty strings in {manifest_path}"
                )
            normalized_entry["optionSafety"] = {"forbidKeys": [str(key).strip() for key in forbidden_keys]}
            if section == "mustFail":
                expect_terms = entry.get("expectTerms")
                if not isinstance(expect_terms, list) or not expect_terms:
                    raise StyleProfileValidationError(
                        f"{section}[{index}].expectTerms must be a non-empty list in {manifest_path}"
                    )
                normalized_entry["expectTerms"] = [str(term).strip() for term in expect_terms if str(term).strip()]
            else:
                source_sample = entry.get("sourceSample")
                if isinstance(source_sample, str) and source_sample.strip():
                    normalized_entry["sourceSample"] = source_sample.strip()
            normalized.append(normalized_entry)
        manifest[section] = normalized
    return manifest
