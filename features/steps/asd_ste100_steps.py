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
    "punchline_cadence",
    "opening_screen",
    "voice_mismatch",
    "missing_attribution",
    "redundancy",
}

PROFILES = {
    "default": "asd-ste100-profile.yml",
    "procedure": "asd-ste100-procedure-profile.yml",
    "beside": "asd-ste100-beside-profile.yml",
    "exclusive": "asd-ste100-exclusive-profile.yml",
    "overrides": "asd-ste100-overrides-profile.yml",
    "unknown-option": "asd-ste100-unknown-option-profile.yml",
    "invalid-limit": "asd-ste100-invalid-limit-profile.yml",
    "unknown-checks-key": "asd-ste100-unknown-checks-key-profile.yml",
}
DRAFTS = {
    "procedure": "procedure-draft.md",
    "sloppy": "sloppy-draft.md",
    "unapproved": "unapproved-word-draft.md",
    "clean-technical": "clean-technical-draft.md",
    "multi-meaning": "multi-meaning-draft.md",
    "override-approved": "override-approved-draft.md",
    "override-unapproved": "override-unapproved-draft.md",
    "long-description": "long-description-draft.md",
    "at-limit-description": "at-limit-description-draft.md",
    "long-procedure": "long-procedure-draft.md",
    "at-limit-procedure": "at-limit-procedure-draft.md",
    "two-instructions": "two-instructions-draft.md",
    "non-imperative": "non-imperative-draft.md",
    "passive": "passive-draft.md",
    "ing-form": "ing-form-draft.md",
    "technical-ing": "technical-ing-draft.md",
    "missing-article": "missing-article-draft.md",
    "article-clean": "article-clean-draft.md",
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


@given("an ASD-STE100 style profile with dictionary overrides")
def step_given_asd_overrides_profile(context):
    _given_profile(context, "overrides")


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


@when("I run the diagnose command on the unapproved-word draft")
def step_when_run_diagnose_unapproved(context):
    _given_draft(context, "unapproved")
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@when("I run the diagnose command on the clean technical draft")
def step_when_run_diagnose_clean_technical(context):
    _given_draft(context, "clean-technical")
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@when("I run the diagnose command on the multi-meaning draft")
def step_when_run_diagnose_multi_meaning(context):
    _given_draft(context, "multi-meaning")
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@when("I run the diagnose command on the override-approved draft")
def step_when_run_diagnose_override_approved(context):
    _given_draft(context, "override-approved")
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@when("I run the diagnose command on the override-unapproved draft")
def step_when_run_diagnose_override_unapproved(context):
    _given_draft(context, "override-unapproved")
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


@then("the diagnosis reports an asd_unapproved_word finding naming the approved alternative")
def step_then_reports_unapproved_word(context):
    assert context.cli_result.returncode == 0, context.cli_result.stderr
    context.diagnosis = json.loads(context.cli_result.stdout)
    kinds = _collect_kinds(context.diagnosis)
    assert "asd_unapproved_word" in kinds, sorted(kinds)
    findings = [f for f in context.diagnosis["generic_passages"] if f["kind"] == "asd_unapproved_word"]
    assert findings, "expected an asd_unapproved_word finding with an approved alternative"
    assert any("approved alternative" in f["rationale"].lower() for f in findings)


@then("the diagnosis reports an asd_multi_meaning finding for the noun usage")
def step_then_reports_multi_meaning(context):
    assert context.cli_result.returncode == 0, context.cli_result.stderr
    context.diagnosis = json.loads(context.cli_result.stdout)
    kinds = _collect_kinds(context.diagnosis)
    assert "asd_multi_meaning" in kinds, sorted(kinds)


@then("the diagnosis reports no asd_ findings")
def step_then_reports_no_asd_findings(context):
    assert context.cli_result.returncode == 0, context.cli_result.stderr
    context.diagnosis = json.loads(context.cli_result.stdout)
    asd_kinds = {k for k in _collect_kinds(context.diagnosis) if str(k).startswith("asd_")}
    assert not asd_kinds, sorted(asd_kinds)


@given("an ASD-STE100 style profile in procedure mode")
def step_given_asd_procedure_profile(context):
    _given_profile(context, "procedure")
    _given_draft(context, "procedure")


@when("I run the diagnose command on the {draft_key} draft")
def step_when_run_diagnose_named_draft(context, draft_key):
    _given_draft(context, draft_key)
    context.cli_result = _run_diagnose_cli(context.profile_path, context.draft_path)


@then("the diagnosis reports an asd_{expected_kind} finding")
def step_then_reports_asd_finding(context, expected_kind):
    assert context.cli_result.returncode == 0, context.cli_result.stderr
    context.diagnosis = json.loads(context.cli_result.stdout)
    kinds = _collect_kinds(context.diagnosis)
    assert f"asd_{expected_kind}" in kinds, sorted(kinds)


@then(
    "the diagnosis reports an asd_sentence_too_long finding naming the {expected_words:d}-word"
    " {expected_mode} limit"
)
def step_then_reports_sentence_too_long(context, expected_words, expected_mode):
    assert context.cli_result.returncode == 0, context.cli_result.stderr
    context.diagnosis = json.loads(context.cli_result.stdout)
    findings = [f for f in context.diagnosis["generic_passages"] if f["kind"] == "asd_sentence_too_long"]
    assert findings, sorted(_collect_kinds(context.diagnosis))
    for finding in findings:
        assert str(expected_words) in finding["rationale"], finding["rationale"]
        assert expected_mode in finding["rationale"], finding["rationale"]
