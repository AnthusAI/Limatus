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
from .editorial_eval_metrics import (
    finding_kind_counts,
    micro_precision_recall,
    option_unsupported_claim_rate,
)
from .editorial_judge import JUDGE_PROMPT_VERSION
from .editorial_options_schema import validate_options
from .editorial_style import load_style_profile

_DEFAULT_FORBIDDEN_KEYS = ("revised_text", "rewritten_prose", "revisedText", "revisedProse", "options", "patches")
_OPTIONS_PAYLOAD_FORBIDDEN = tuple(key for key in _DEFAULT_FORBIDDEN_KEYS if key != "options")


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


def _diagnosis_for_entry(
    entry: dict[str, Any], *, profile_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    selected_profile = Path(entry.get("profile", profile_path))
    draft_path = Path(entry["draftPath"])
    diagnosis = diagnose_draft(
        draft_path.read_text(encoding="utf-8"), style_profile=load_style_profile(selected_profile)
    )
    findings = _findings(diagnosis)
    kinds = {str(finding.get("kind")) for finding in findings}
    return diagnosis, findings, kinds


def _evaluate_entry(
    entry: dict[str, Any],
    *,
    section: str,
    manifest_path: Path,
    profile_path: Path,
    diagnosis: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
    kinds: set[str] | None = None,
) -> tuple[bool, str]:
    if diagnosis is None or findings is None or kinds is None:
        diagnosis, findings, kinds = _diagnosis_for_entry(entry, profile_path=profile_path)
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


def _evaluate_options_entry(entry: dict[str, Any]) -> tuple[bool, str, list[dict[str, Any]]]:
    raw = json.loads(Path(entry["optionsPath"]).read_text(encoding="utf-8"))
    validated = validate_options(raw)
    manifest_forbidden = {
        key
        for key in entry.get("optionSafety", {}).get("forbidKeys", [])
        if str(key).strip() and str(key).strip() != "options"
    }
    forbidden = set(_OPTIONS_PAYLOAD_FORBIDDEN) | manifest_forbidden
    violation = _contains_forbidden(validated, forbidden)
    if violation:
        return False, f"option safety key present at {violation}", validated["findings"]
    return True, f"{len(validated['findings'])} finding option group(s)", validated["findings"]


def run_offline_evals(manifest_path: str | Path) -> tuple[int, list[str]]:
    path = Path(manifest_path).resolve()
    manifest = load_editorial_corpus_manifest(path)
    profile_path = Path(manifest.get("profile", path.parent / "style-profile.yml")).resolve()
    lines: list[str] = []
    passed = failed = 0
    total_tp = total_fp = total_fn = 0
    for section in ("mustFail", "mustPass"):
        for entry in manifest[section]:
            diagnosis, findings, kinds = _diagnosis_for_entry(entry, profile_path=profile_path)
            expected_kinds = set(entry.get("expectKinds", []))
            tp, fp, fn = finding_kind_counts(expected_kinds, kinds)
            total_tp += tp
            total_fp += fp
            total_fn += fn
            ok, detail = _evaluate_entry(
                entry,
                section=section,
                manifest_path=path,
                profile_path=profile_path,
                diagnosis=diagnosis,
                findings=findings,
                kinds=kinds,
            )
            label = f"{section}/{entry['id']}"
            lines.append(f"{'PASS' if ok else 'FAIL'} {label}: {detail}")
            passed += ok
            failed += not ok
    precision, recall = micro_precision_recall(total_tp, total_fp, total_fn)
    lines.append(
        "finding metrics: "
        f"precision={precision:.4f} recall={recall:.4f} "
        f"tp={total_tp} fp={total_fp} fn={total_fn}"
    )
    option_entries = manifest.get("options", [])
    if option_entries:
        all_findings: list[dict[str, Any]] = []
        for entry in option_entries:
            ok, detail, findings = _evaluate_options_entry(entry)
            label = f"options/{entry['id']}"
            lines.append(f"{'PASS' if ok else 'FAIL'} {label}: {detail}")
            passed += ok
            failed += not ok
            if ok:
                all_findings.extend(findings)
        rate, count = option_unsupported_claim_rate(all_findings)
        lines.append(f"option metrics: unsupportedClaimRate={rate:.4f} n={count}")
    lines.append(f"judgePromptVersion={JUDGE_PROMPT_VERSION}")
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
