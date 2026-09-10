"""Small fixture canary for judge prompt and Terra-default calibration."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

import yaml

from .editorial_compare import compare_regression
from .editorial_diagnosis_schema import FINDING_SOURCE_JUDGE
from .editorial_judge import (
    JUDGE_PROMPT_VERSION,
    JudgeResolver,
    default_judge_resolver,
    make_judge_finding,
    resolved_judge_model,
)
from .editorial_scan import scan_draft
from .editorial_style import LoadedStyleProfile, StyleProfileValidationError, load_style_profile

JudgeMode = Literal["fixture", "live"]

_FINDING_ARRAY_KEYS = (
    "generic_passages",
    "unsupported_claims",
    "voice_observations",
    "required_facts",
)


def _collect_leaf_findings(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key in _FINDING_ARRAY_KEYS:
        findings.extend(diagnosis.get(key, []))
    for group in diagnosis.get("repetition_groups", []):
        if isinstance(group, dict):
            findings.extend(group.get("members", []))
    return findings


def _finding_kinds(diagnosis: dict[str, Any]) -> set[str]:
    return {str(finding.get("kind") or "") for finding in _collect_leaf_findings(diagnosis)}


def _judge_findings(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        finding
        for finding in _collect_leaf_findings(diagnosis)
        if finding.get("source") == FINDING_SOURCE_JUDGE
    ]


def _judge_record(
    diagnosis: dict[str, Any],
    *,
    mode: JudgeMode,
    default_model: str,
    default_prompt_version: str,
) -> dict[str, str]:
    judge_hits = _judge_findings(diagnosis)
    models = {str(f.get("model") or "").strip() for f in judge_hits if str(f.get("model") or "").strip()}
    versions = {
        str(f.get("promptVersion") or "").strip()
        for f in judge_hits
        if str(f.get("promptVersion") or "").strip()
    }
    if len(models) > 1:
        raise ValueError(f"inconsistent judge models in one scan: {sorted(models)}")
    if len(versions) > 1:
        raise ValueError(f"inconsistent judge prompt versions in one scan: {sorted(versions)}")
    model = next(iter(models)) if models else default_model
    prompt_version = next(iter(versions)) if versions else default_prompt_version
    if not model or not prompt_version:
        raise ValueError("judge record requires non-empty model and promptVersion")
    return {"mode": mode, "model": model, "promptVersion": prompt_version}


def _require_string_list(value: Any, location: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not str(item).strip() for item in value):
        raise StyleProfileValidationError(f"{location} must be a list of non-empty strings")
    return [str(item).strip() for item in value]


def _resolve_manifest_path(manifest_dir: Path, rel_path: str, location: str) -> Path:
    if not rel_path.strip():
        raise StyleProfileValidationError(f"{location} requires a non-empty path")
    resolved = (manifest_dir / rel_path).resolve()
    if not resolved.is_file():
        raise StyleProfileValidationError(f"{location} file not found: {resolved}")
    return resolved


def load_canary_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path).resolve()
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise StyleProfileValidationError(f"Canary manifest must be a mapping: {manifest_path}")

    manifest_dir = manifest_path.parent
    schema_version = raw.get("schemaVersion")
    if schema_version != 1:
        raise StyleProfileValidationError(f"Unsupported canary schemaVersion {schema_version!r} in {manifest_path}")

    profile_rel = str(raw.get("profile", "")).strip()
    profile_path = _resolve_manifest_path(manifest_dir, profile_rel, "profile")
    manifest: dict[str, Any] = {
        "manifestPath": str(manifest_path),
        "manifestDir": str(manifest_dir),
        "profilePath": str(profile_path),
    }

    calibration = raw.get("calibration")
    if not isinstance(calibration, dict):
        raise StyleProfileValidationError(f"calibration must be a mapping in {manifest_path}")
    prompt_version = str(calibration.get("judgePromptVersion", "")).strip()
    judge_model = str(calibration.get("judgeModel", "")).strip()
    if not prompt_version or not judge_model:
        raise StyleProfileValidationError(
            f"calibration.judgePromptVersion and calibration.judgeModel are required in {manifest_path}"
        )
    manifest["calibration"] = {"judgePromptVersion": prompt_version, "judgeModel": judge_model}

    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise StyleProfileValidationError(f"entries must be a non-empty list in {manifest_path}")

    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(entries_raw):
        if not isinstance(entry, dict):
            raise StyleProfileValidationError(f"entries[{index}] must be a mapping in {manifest_path}")
        entry_id = str(entry.get("id", "")).strip()
        kind = str(entry.get("kind", "")).strip()
        if not entry_id or kind not in {"scan", "compareRegression"}:
            raise StyleProfileValidationError(
                f"entries[{index}] requires id and kind scan|compareRegression in {manifest_path}"
            )
        normalized: dict[str, Any] = {"id": entry_id, "kind": kind}
        if kind == "scan":
            draft_path = _resolve_manifest_path(
                manifest_dir,
                str(entry.get("draft", "")).strip(),
                f"entries[{index}].draft",
            )
            normalized["draftPath"] = str(draft_path)
            always_lane = entry.get("alwaysLane", {})
            if not isinstance(always_lane, dict):
                raise StyleProfileValidationError(f"entries[{index}].alwaysLane must be a mapping in {manifest_path}")
            normalized["alwaysLane"] = {
                "expectKinds": _require_string_list(
                    always_lane.get("expectKinds"), f"entries[{index}].alwaysLane.expectKinds"
                ),
                "forbidKinds": _require_string_list(
                    always_lane.get("forbidKinds"), f"entries[{index}].alwaysLane.forbidKinds"
                ),
            }
        else:
            baseline_path = _resolve_manifest_path(
                manifest_dir,
                str(entry.get("baseline", "")).strip(),
                f"entries[{index}].baseline",
            )
            working_path = _resolve_manifest_path(
                manifest_dir,
                str(entry.get("working", "")).strip(),
                f"entries[{index}].working",
            )
            normalized["baselinePath"] = str(baseline_path)
            normalized["workingPath"] = str(working_path)
            compare = entry.get("compare", {})
            if not isinstance(compare, dict):
                raise StyleProfileValidationError(f"entries[{index}].compare must be a mapping in {manifest_path}")
            normalized["compare"] = {
                "expectHardConstraints": _require_string_list(
                    compare.get("expectHardConstraints"),
                    f"entries[{index}].compare.expectHardConstraints",
                ),
            }
        entries.append(normalized)
    manifest["entries"] = entries

    fixture_raw = raw.get("fixtureJudge", {})
    if not isinstance(fixture_raw, dict):
        raise StyleProfileValidationError(f"fixtureJudge must be a mapping in {manifest_path}")
    fixture_judge: dict[str, Any] = {}
    for entry in entries:
        raw_specs = fixture_raw.get(entry["id"], [])
        if raw_specs is None:
            raw_specs = []
        if entry["kind"] == "compareRegression" and isinstance(raw_specs, dict):
            parsed_entry: dict[str, list[dict[str, Any]]] = {}
            for role in ("baseline", "working"):
                role_specs = raw_specs.get(role, [])
                if role_specs is None:
                    role_specs = []
                if not isinstance(role_specs, list):
                    raise StyleProfileValidationError(
                        f"fixtureJudge.{entry['id']}.{role} must be a list in {manifest_path}"
                    )
                parsed_entry[role] = _parse_fixture_specs(
                    role_specs, f"fixtureJudge.{entry['id']}.{role}", manifest_path
                )
            fixture_judge[entry["id"]] = parsed_entry
            continue
        if not isinstance(raw_specs, list):
            raise StyleProfileValidationError(
                f"fixtureJudge.{entry['id']} must be a list in {manifest_path}"
            )
        fixture_judge[entry["id"]] = _parse_fixture_specs(
            raw_specs, f"fixtureJudge.{entry['id']}", manifest_path
        )
    manifest["fixtureJudge"] = fixture_judge
    return manifest


def _parse_fixture_specs(
    specs: list[Any],
    location: str,
    manifest_path: Path,
) -> list[dict[str, Any]]:
    parsed_specs: list[dict[str, Any]] = []
    for spec_index, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise StyleProfileValidationError(f"{location}[{spec_index}] must be a mapping in {manifest_path}")
        kind = str(spec.get("kind", "")).strip()
        rationale = str(spec.get("rationale", "")).strip()
        start = spec.get("start")
        end = spec.get("end")
        if not kind or not rationale:
            raise StyleProfileValidationError(
                f"{location}[{spec_index}] requires kind and rationale in {manifest_path}"
            )
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
            raise StyleProfileValidationError(
                f"{location}[{spec_index}] requires valid start/end in {manifest_path}"
            )
        parsed_specs.append({"kind": kind, "rationale": rationale, "start": start, "end": end})
    return parsed_specs


def assert_calibration_matches_code(
    manifest: dict[str, Any],
    style_profile: LoadedStyleProfile,
) -> None:
    expected_prompt = manifest["calibration"]["judgePromptVersion"]
    expected_model = manifest["calibration"]["judgeModel"]
    if expected_prompt != JUDGE_PROMPT_VERSION:
        raise ValueError(
            "calibration drift: manifest judgePromptVersion "
            f"{expected_prompt!r} != code {JUDGE_PROMPT_VERSION!r}"
        )
    if style_profile.profile.judge is None:
        raise ValueError("calibration drift: canary profile must enable the OpenAI judge")
    resolved_model = resolved_judge_model(style_profile.profile.judge)
    if expected_model != resolved_model:
        raise ValueError(
            "calibration drift: manifest judgeModel "
            f"{expected_model!r} != resolved profile model {resolved_model!r}"
        )


def fixture_judge_resolver_from_manifest(manifest: dict[str, Any]) -> JudgeResolver:
    text_to_specs: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest["entries"]:
        raw_specs = manifest["fixtureJudge"].get(entry["id"], [])
        if entry["kind"] == "scan":
            draft_text = Path(entry["draftPath"]).read_text(encoding="utf-8")
            text_to_specs[draft_text] = raw_specs if isinstance(raw_specs, list) else []
        else:
            role_specs = raw_specs if isinstance(raw_specs, dict) else {"baseline": [], "working": raw_specs}
            baseline_text = Path(entry["baselinePath"]).read_text(encoding="utf-8")
            working_text = Path(entry["workingPath"]).read_text(encoding="utf-8")
            text_to_specs[baseline_text] = role_specs.get("baseline", [])
            text_to_specs[working_text] = role_specs.get("working", [])

    def resolver(draft_text: str, _style_profile: LoadedStyleProfile, judge_config) -> list[dict[str, Any]]:
        specs = text_to_specs.get(draft_text, [])
        model = resolved_judge_model(judge_config)
        findings: list[dict[str, Any]] = []
        draft_len = len(draft_text)
        for spec in specs:
            start = spec["start"]
            end = min(spec["end"], draft_len)
            if end <= start and draft_len:
                continue
            findings.append(
                make_judge_finding(
                    spec["kind"],
                    draft_text,
                    start,
                    end,
                    spec["rationale"],
                    model=model,
                    prompt_version=JUDGE_PROMPT_VERSION,
                )
            )
        return findings

    return resolver


def _assert_always_lane(entry: dict[str, Any], diagnosis: dict[str, Any]) -> str | None:
    kinds = _finding_kinds(diagnosis)
    always_lane = entry.get("alwaysLane", {})
    missing = sorted(set(always_lane.get("expectKinds", [])) - kinds)
    if missing:
        return f"missing always-lane kinds: {', '.join(missing)}"
    forbidden = set(always_lane.get("forbidKinds", [])) & kinds
    if forbidden:
        return f"forbidden always-lane kinds present: {', '.join(sorted(forbidden))}"
    return None


def _assert_compare(entry: dict[str, Any], report: dict[str, Any]) -> str | None:
    expected = entry.get("compare", {}).get("expectHardConstraints", [])
    if not expected:
        return None
    candidates = report.get("candidates", [])
    if not candidates:
        return "compare report missing candidates"
    raw_violations = candidates[0].get("hardConstraintViolations", [])
    violation_ids = {
        str(item.get("constraint") or item)
        for item in raw_violations
        if isinstance(item, dict) or isinstance(item, str)
    }
    missing = sorted(set(expected) - violation_ids)
    if missing:
        return f"missing expected hard constraints: {', '.join(missing)}"
    return None


def run_canary(
    manifest_path: str | Path,
    *,
    judge_mode: JudgeMode = "fixture",
    judge_resolver: JudgeResolver | None = None,
    require_judge: bool = False,
    skip_calibration: bool = False,
) -> tuple[int, dict[str, Any], list[str]]:
    manifest = load_canary_manifest(manifest_path)
    style_profile = load_style_profile(Path(manifest["profilePath"]))
    if not skip_calibration:
        assert_calibration_matches_code(manifest, style_profile)

    if judge_resolver is None:
        if judge_mode == "fixture":
            judge_resolver = fixture_judge_resolver_from_manifest(manifest)
        else:
            judge_resolver = default_judge_resolver

    default_model = resolved_judge_model(style_profile.profile.judge)  # type: ignore[arg-type]
    default_prompt = JUDGE_PROMPT_VERSION

    results: list[dict[str, Any]] = []
    lines: list[str] = []
    failed = 0

    for entry in manifest["entries"]:
        label = f"canary/{entry['id']}"
        try:
            if entry["kind"] == "scan":
                draft_text = Path(entry["draftPath"]).read_text(encoding="utf-8")
                diagnosis = scan_draft(
                    draft_text,
                    style_profile=style_profile,
                    judge_resolver=judge_resolver,
                    require_judge=require_judge,
                )
                judge = _judge_record(
                    diagnosis,
                    mode=judge_mode,
                    default_model=default_model,
                    default_prompt_version=default_prompt,
                )
                lane_error = _assert_always_lane(entry, diagnosis)
                result = {
                    "entryId": entry["id"],
                    "kind": "scan",
                    "judge": judge,
                    "alwaysLaneKinds": sorted(_finding_kinds(diagnosis)),
                }
                if lane_error:
                    raise ValueError(lane_error)
            else:
                baseline_text = Path(entry["baselinePath"]).read_text(encoding="utf-8")
                working_text = Path(entry["workingPath"]).read_text(encoding="utf-8")
                baseline_scan = scan_draft(
                    baseline_text,
                    style_profile=style_profile,
                    judge_resolver=judge_resolver,
                    require_judge=require_judge,
                )
                report = compare_regression(
                    baseline_text,
                    working_text,
                    style_profile=style_profile,
                    judge_resolver=judge_resolver,
                )
                judge = _judge_record(
                    baseline_scan,
                    mode=judge_mode,
                    default_model=default_model,
                    default_prompt_version=default_prompt,
                )
                compare_error = _assert_compare(entry, report)
                result = {
                    "entryId": entry["id"],
                    "kind": "compareRegression",
                    "judge": judge,
                    "compare": {
                        "schemaVersion": report.get("schemaVersion"),
                        "mode": report.get("mode"),
                        "hardConstraintViolations": report.get("candidates", [{}])[0].get(
                            "hardConstraintViolations", []
                        ),
                    },
                }
                if compare_error:
                    raise ValueError(compare_error)
            results.append(result)
            lines.append(
                f"PASS {label}: judge {judge['promptVersion']}/{judge['model']} ({judge['mode']})"
            )
        except Exception as exc:
            failed += 1
            lines.append(f"FAIL {label}: {exc}")

    passed = len(results)
    lines.append(f"canary eval: {passed} passed, {failed} failed")
    report = {
        "schemaVersion": 1,
        "judgeMode": judge_mode,
        "calibration": manifest["calibration"],
        "results": results,
    }
    return (0 if failed == 0 else 1), report, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="limatus canary")
    parser.add_argument("--manifest", required=True, help="Checked-in canary manifest YAML")
    parser.add_argument(
        "--judge-mode",
        choices=("fixture", "live"),
        default="fixture",
        help="fixture uses manifest fixtureJudge; live calls OpenAI when a key is set",
    )
    parser.add_argument(
        "--require-judge",
        action="store_true",
        help="Fail when a configured judge cannot run (missing OPENAI_API_KEY or API error).",
    )
    parser.add_argument("--output", default="", help="Optional path to write JSON report")
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="Skip manifest vs code calibration checks (testing only).",
    )
    args = parser.parse_args(argv)
    try:
        code, report, lines = run_canary(
            args.manifest,
            judge_mode=args.judge_mode,
            require_judge=args.require_judge,
            skip_calibration=args.skip_calibration,
        )
    except Exception as exc:
        print(f"FAIL canary: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        Path(args.output).resolve().write_text(rendered, encoding="utf-8")
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
