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
DIAGNOSIS_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_loop import assert_scan_has_no_steering_decisions  # noqa: E402
from limatus.editorial_options_schema import validate_decisions  # noqa: E402


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    env.pop("OPENAI_API_KEY", None)
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


def _collect_leaf_finding_ids(diagnosis: dict) -> list[str]:
    ids: list[str] = []
    for key in ("generic_passages", "unsupported_claims", "voice_observations", "required_facts"):
        for finding in diagnosis.get(key, []):
            ids.append(finding["id"])
    for group in diagnosis.get("repetition_groups", []):
        for member in group.get("members", []):
            ids.append(member["id"])
    return ids


@given("a CLI scan fixture draft and style profile")
def step_given_cli_scan_fixture(context):
    context.tempdir = Path(tempfile.mkdtemp(prefix="limatus-cli-decide-"))
    context.draft_path = DIAGNOSIS_FIXTURE_ROOT / "sloppy-draft.md"
    context.profile_path = DIAGNOSIS_FIXTURE_ROOT / "style-profile.yml"
    context.draft_snapshot = context.draft_path.read_bytes()
    context.diagnosis_path = context.tempdir / "diagnosis.json"
    context.decisions_path = context.tempdir / "decisions.json"


@when("I run python -m limatus scan with output diagnosis.json")
def step_when_cli_scan_to_file(context):
    completed = _run_limatus(
        "scan",
        "--draft",
        str(context.draft_path),
        "--profile",
        str(context.profile_path),
        "--output",
        str(context.diagnosis_path),
    )
    assert completed.returncode == 0, completed.stderr
    context.diagnosis = json.loads(context.diagnosis_path.read_text(encoding="utf-8"))
    context.finding_ids = _collect_leaf_finding_ids(context.diagnosis)
    assert context.finding_ids, "expected at least one finding from scan"


@when("I run python -m limatus decide for rewrite on one finding")
def step_when_cli_decide_rewrite(context):
    completed = _run_limatus(
        "decide",
        "--finding-id",
        context.finding_ids[0],
        "--decision",
        "rewrite",
        "--note",
        "needs options",
        "--decisions",
        str(context.decisions_path),
    )
    assert completed.returncode == 0, completed.stderr
    context.decisions = json.loads(completed.stdout)
    context.rewrite_finding_id = context.finding_ids[0]


@when("I run python -m limatus decide for skip on another finding when available")
def step_when_cli_decide_skip_if_possible(context):
    if len(context.finding_ids) < 2:
        return
    completed = _run_limatus(
        "decide",
        "--finding-id",
        context.finding_ids[1],
        "--decision",
        "skip",
        "--decisions",
        str(context.decisions_path),
    )
    assert completed.returncode == 0, completed.stderr
    context.decisions = json.loads(completed.stdout)
    context.skip_finding_id = context.finding_ids[1]


@then("the diagnosis JSON has no steering decision fields")
def step_then_diagnosis_has_no_steering(context):
    assert_scan_has_no_steering_decisions(context.diagnosis)


@then("the decisions file validates")
def step_then_decisions_file_validates(context):
    payload = json.loads(context.decisions_path.read_text(encoding="utf-8"))
    validate_decisions(payload)
    rewrite_entries = [entry for entry in payload if entry.get("decision") == "rewrite"]
    assert rewrite_entries, payload
    assert rewrite_entries[0]["finding_id"] == context.rewrite_finding_id
    if len(context.finding_ids) >= 2:
        skip_entries = [entry for entry in payload if entry.get("decision") == "skip"]
        assert skip_entries, payload
        assert skip_entries[0]["finding_id"] == context.skip_finding_id
