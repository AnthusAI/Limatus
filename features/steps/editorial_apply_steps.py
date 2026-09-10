from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    return env


def _run_limatus(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "limatus", *args],
        cwd=REPO_ROOT,
        env=_cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )


@given("an original draft, a separate working copy, and one options payload")
def step_given_apply_bundle(context):
    context.tempdir = Path(tempfile.mkdtemp(prefix="limatus-apply-"))
    context.original_path = context.tempdir / "original.md"
    context.working_path = context.tempdir / "working.md"
    context.log_path = context.tempdir / "changes.json"
    context.options_path = context.tempdir / "options.json"
    context.original_text = "The platform will revolutionize workflows.\n"
    context.original_path.write_text(context.original_text, encoding="utf-8")
    context.working_path.write_text(context.original_text, encoding="utf-8")
    context.options = {
        "schemaVersion": 1,
        "findings": [{
            "findingId": "finding-a6b95ac741d27015",
            "options": [{
                "id": "option-0123456789abcdef",
                "patch": {"span": {"start": 18, "end": 31}, "replacement": "improve"},
                "reason": "Use an operational verb.",
                "factVerificationRequired": False,
                "unresolvedQuestions": [],
            }],
        }],
    }
    context.options_path.write_text(json.dumps(context.options), encoding="utf-8")


@when("I apply the selected option with its exact anchor")
def step_when_apply_option(context):
    completed = _run_limatus(
        "apply",
        "--original",
        str(context.original_path),
        "--working-copy",
        str(context.working_path),
        "--options",
        str(context.options_path),
        "--finding-id",
        "finding-a6b95ac741d27015",
        "--option-id",
        "option-0123456789abcdef",
        "--anchor",
        "revolutionize",
        "--change-log",
        str(context.log_path),
    )
    assert completed.returncode == 0, completed.stderr
    context.result = json.loads(completed.stdout)
    diff_completed = _run_limatus(
        "diff",
        "--original",
        str(context.original_path),
        "--working-copy",
        str(context.working_path),
    )
    assert diff_completed.returncode == 0, diff_completed.stderr
    context.diff = diff_completed.stdout


@then("only the selected span changes in the working copy")
def step_then_only_selected_span(context):
    assert context.working_path.read_text(encoding="utf-8") == "The platform will improve workflows.\n"


@then("the original draft is unchanged")
def step_then_original_unchanged(context):
    assert context.original_path.read_text(encoding="utf-8") == context.original_text


@then("a machine-readable change log records the selected option")
def step_then_log_records_option(context):
    payload = json.loads(context.log_path.read_text(encoding="utf-8"))
    assert payload["changes"][0]["optionId"] == "option-0123456789abcdef"
    assert payload["changes"][0]["action"] == "replace"


@then("the original-versus-working diff contains the selected replacement")
def step_then_diff_contains_replacement(context):
    assert "-The platform will revolutionize workflows." in context.diff
    assert "+The platform will improve workflows." in context.diff


@when("I apply the selected option with a stale anchor")
def step_when_apply_stale(context):
    context.before = context.working_path.read_bytes()
    completed = _run_limatus(
        "apply",
        "--original",
        str(context.original_path),
        "--working-copy",
        str(context.working_path),
        "--options",
        str(context.options_path),
        "--finding-id",
        "finding-a6b95ac741d27015",
        "--option-id",
        "option-0123456789abcdef",
        "--anchor",
        "old-word",
    )
    context.error = completed.stderr
    assert completed.returncode != 0, "stale anchor unexpectedly applied"


@then("the apply fails safely")
def step_then_apply_fails(context):
    assert "anchor" in context.error.lower()


@then("the working copy is unchanged")
def step_then_working_unchanged(context):
    assert context.working_path.read_bytes() == context.before
