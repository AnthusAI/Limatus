"""Deterministic, offline editorial regression evaluation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from .editorial_corpus import load_editorial_corpus_manifest
from .editorial_diagnosis import diagnose_draft
from .editorial_style import load_style_profile

_DEFAULT_FORBIDDEN_KEYS = ("revised_text", "rewritten_prose", "revisedText", "revisedProse", "options", "patches")


def _findings(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        found.extend(diagnosis.get(key, []))
    for group in diagnosis.get("repetition_groups", []):
        found.append(group)
        found.extend(group.get("members", []))
    return found


def _contains_forbidden(value: Any, forbidden: set[str], path: str = "") -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            current = f"{path}.{key}" if path else str(key)
            if key in forbidden or re.sub(r"[^a-z0-9]", "", str(key).lower()) in {
                re.sub(r"[^a-z0-9]", "", item.lower()) for item in forbidden
            }:
                return current
            violation = _contains_forbidden(nested, forbidden, current)
            if violation:
                return violation
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            violation = _contains_forbidden(nested, forbidden, f"{path}[{index}]")
            if violation:
                return violation
    return None


def _evaluate_entry(entry: dict[str, Any], *, section: str, manifest_path: Path, profile_path: Path) -> tuple[bool, str]:
    selected_profile = Path(entry.get("profile", profile_path))
    draft_path = Path(entry["draftPath"])
    diagnosis = diagnose_draft(draft_path.read_text(encoding="utf-8"), style_profile=load_style_profile(selected_profile))
    findings = _findings(diagnosis)
    kinds = {str(finding.get("kind")) for finding in findings}
    expected_kinds = set(entry.get("expectKinds", []))
    missing_kinds = sorted(expected_kinds - kinds)
    if missing_kinds:
        return False, f"missing finding kinds: {', '.join(missing_kinds)}"
    max_findings = entry.get("maxFindings")
    if max_findings is not None and len(findings) > max_findings:
        return False, f"found {len(findings)} findings (maximum {max_findings})"
    rendered_findings = json.dumps(findings, sort_keys=True).lower()
    missing_terms = [term for term in entry.get("expectTerms", []) if term.lower() not in rendered_findings]
    if missing_terms:
        return False, f"missing expected terms: {', '.join(missing_terms)}"
    forbidden = set(_DEFAULT_FORBIDDEN_KEYS) | set(entry.get("optionSafety", {}).get("forbidKeys", []))
    violation = _contains_forbidden(diagnosis, forbidden)
    if violation:
        return False, f"option safety key present at {violation}"
    return True, f"{len(findings)} finding(s), {len(kinds)} kind(s)"


def run_offline_evals(manifest_path: str | Path) -> tuple[int, list[str]]:
    path = Path(manifest_path).resolve()
    manifest = load_editorial_corpus_manifest(path)
    profile_path = Path(manifest.get("profile", path.parent / "style-profile.yml")).resolve()
    lines: list[str] = []
    passed = failed = 0
    for section in ("mustFail", "mustPass"):
        for entry in manifest[section]:
            ok, detail = _evaluate_entry(entry, section=section, manifest_path=path, profile_path=profile_path)
            label = f"{section}/{entry['id']}"
            lines.append(f"{'PASS' if ok else 'FAIL'} {label}: {detail}")
            passed += ok
            failed += not ok
    lines.append(f"offline eval: {passed} passed, {failed} failed")
    return (0 if failed == 0 else 1), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="limatus eval")
    parser.add_argument("--manifest", required=True, help="Checked-in offline eval manifest")
    args = parser.parse_args(argv)
    try:
        code, lines = run_offline_evals(args.manifest)
    except Exception as exc:
        print(f"FAIL manifest: {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
