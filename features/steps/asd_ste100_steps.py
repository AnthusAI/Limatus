from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from behave import given, then

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "asd-ste100"

BOT_SLOP_KINDS = {
    "empty_leadin",
    "list_shaped_prose",
    "vague_claim",
    "overused_word",
    "uncontracted_form",
    "unsupported_certainty",
    "uniform_cadence",
    "voice_mismatch",
    "missing_attribution",
    "redundancy",
}

PROFILES = {
    "default": "asd-ste100-profile.yml",
    "beside": "asd-ste100-beside-profile.yml",
    "exclusive": "asd-ste100-exclusive-profile.yml",
    "unknown-option": "asd-ste100-unknown-option-profile.yml",
    "invalid-limit": "asd-ste100-invalid-limit-profile.yml",
    "unknown-checks-key": "asd-ste100-unknown-checks-key-profile.yml",
}
DRAFTS = {
    "procedure": "procedure-draft.md",
    "sloppy": "sloppy-draft.md",
}


def _run_diagnose_cli(profile_path: Path, draft_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    command = [
        sys.executable,
        "-m",
        "limatus",
        "diagnose",
        "--profile",
        str(profile_path),
        "--draft",
        str(draft_path),
    ]
    return subprocess.run(command, cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)


def _collect_kinds(diagnosis: dict) -> set[str]:
    kinds: set[str] = set()
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        for finding in diagnosis.get(key, []):
            kinds.add(finding.get("kind"))
    for group in diagnosis.get("repetition_groups", []):
        kinds.add(group.get("kind"))
    return kinds


def _given_profile(context, name: str) -> None:
    context.profile_path = FIXTURE_ROOT / PROFILES[name]
    assert context.profile_path.is_file(), context.profile_path


def _given_draft(context, name: str) -> None:
    context.draft_path = FIXTURE_ROOT / DRAFTS[name]
    assert context.draft_path.is_file(), context.draft_path


@given("an ASD-STE100 style profile with default limits")
def step_given_asd_default_profile(context):
    _given_profile(context, "default")
    _given_draft(context, "procedure")


@given("an ASD-STE100 style profile in STE-only mode")
def step_given_asd_exclusive_profile(context):
    _given_profile(context, "exclusive")
    _given_draft(context, "sloppy")


@given("an ASD-STE100 style profile beside the bot-slop checks")
def step_given_asd_beside_profile(context):
    _given_profile(context, "beside")
    _given_draft(context, "sloppy")


@given("an ASD-STE100 style profile with an unknown option")
def step_given_asd_unknown_option_profile(context):
    _given_profile(context, "unknown-option")
    _given_draft(context, "procedure")


@given("an ASD-STE100 style profile with a non-positive word limit")
def step_given_asd_invalid_limit_profile(context):
    _given_profile(context, "invalid-limit")
    _given_draft(context, "procedure")


@given("an ASD-STE100 style profile with an unknown checks key")
def step_given_asd_unknown_checks_key_profile(context):
    _given_profile(context, "unknown-checks-key")
    _given_draft(context, "procedure")


@when("I run the diagnose command on a procedure draft")
def step_when_run_diagnose_procedure(context):
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@when("I run the diagnose command on a sloppy draft")
def step_when_run_diagnose_sloppy(context):
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@then("the diagnosis includes an asdSte100 summary")
def step_then_diagnosis_includes_summary(context):
    assert context.cli_result.returncode == 0, context.cli_result.stderr
    context.diagnosis = json.loads(context.cli_result.stdout)
    assert "asdSte100" in context.diagnosis, context.diagnosis.keys()
    assert isinstance(context.diagnosis["asdSte100"], dict)


@then("the asdSte100 summary reports mode auto with 20-word procedure and 25-word description limits")
def step_then_summary_defaults(context):
    summary = context.diagnosis["asdSte100"]
    assert summary["mode"] == "auto"
    assert summary["maxWordsProcedure"] == 20
    assert summary["maxWordsDescription"] == 25


@then("the diagnosis contains no bot-slop kinds")
def step_then_no_bot_slop_kinds(context):
    kinds = _collect_kinds(context.diagnosis)
    overlap = kinds & BOT_SLOP_KINDS
    assert not overlap, f"unexpected bot-slop kinds in STE-only diagnosis: {sorted(overlap)}"


@then("the diagnosis contains at least one bot-slop kind")
def step_then_some_bot_slop_kinds(context):
    kinds = _collect_kinds(context.diagnosis)
    assert kinds & BOT_SLOP_KINDS, f"expected bot-slop kinds, found: {sorted(kinds)}"


@then("the command fails naming the unknown option")
def step_then_fails_unknown_option(context):
    assert context.cli_result.returncode != 0, context.cli_result.stdout
    assert "maxWordzProcedure" in context.cli_result.stderr


@then("the command fails naming the word limit")
def step_then_fails_invalid_limit(context):
    assert context.cli_result.returncode != 0, context.cli_result.stdout
    assert "maxWordsProcedure" in context.cli_result.stderr


@then("the command fails naming the unknown checks key")
def step_then_fails_unknown_checks_key(context):
    assert context.cli_result.returncode != 0, context.cli_result.stdout
    assert "asdVocabulary" in context.cli_result.stderr
