from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
COMPARE_FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-compare"
PROFILE_PATH = REPO_ROOT / "features" / "fixtures" / "editorial-diagnosis" / "style-profile.yml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_style import load_style_profile  # noqa: E402


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_compare_cli(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    env.pop("OPENAI_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "limatus", "compare", *command],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@given("a style profile and three candidate texts")
def step_given_three_candidates(context):
    context.profile_path = PROFILE_PATH
    context.baseline_path = COMPARE_FIXTURE_ROOT / "baseline.md"
    context.candidate_paths = [
        COMPARE_FIXTURE_ROOT / "candidate-best.md",
        COMPARE_FIXTURE_ROOT / "candidate-middle.md",
        COMPARE_FIXTURE_ROOT / "candidate-weakest.md",
    ]
    context.candidate_digests = {path: _file_digest(path) for path in context.candidate_paths}
    assert context.profile_path.is_file()
    assert context.baseline_path.is_file()


@given("an original draft and a candidate that adds an unsupported claim")
def step_given_unsupported_candidate(context):
    context.profile_path = PROFILE_PATH
    context.baseline_path = COMPARE_FIXTURE_ROOT / "original.md"
    context.candidate_paths = [
        COMPARE_FIXTURE_ROOT / "working-unsupported.md",
        COMPARE_FIXTURE_ROOT / "working-improved.md",
    ]
    context.candidate_ids = ["unsupported", "improved"]
    context.candidate_digests = {path: _file_digest(path) for path in context.candidate_paths}


@given("an original draft and a working copy after a trial edit")
def step_given_regression_pair(context):
    context.profile_path = PROFILE_PATH
    context.original_path = COMPARE_FIXTURE_ROOT / "original.md"
    context.working_path = COMPARE_FIXTURE_ROOT / "working-improved.md"
    context.original_digest = _file_digest(context.original_path)
    context.working_digest = _file_digest(context.working_path)
    context.style_profile = load_style_profile(context.profile_path)


@when("I run limatus compare")
def step_when_compare(context):
    if hasattr(context, "original_path"):
        completed = _run_compare_cli(
            [
                "--profile",
                str(context.profile_path),
                "--original",
                str(context.original_path),
                "--working-copy",
                str(context.working_path),
            ]
        )
    else:
        command = [
            "--profile",
            str(context.profile_path),
            "--baseline",
            str(context.baseline_path),
        ]
        for path in context.candidate_paths:
            command.extend(["--candidate", str(path)])
        for candidate_id in getattr(context, "candidate_ids", []):
            command.extend(["--candidate-id", candidate_id])
        completed = _run_compare_cli(command)

    assert completed.returncode == 0, completed.stderr
    context.compare_report = json.loads(completed.stdout)


@then("the JSON lists all three candidates")
def step_then_lists_three(context):
    assert len(context.compare_report["candidates"]) == 3


@then("each has a rank and always-lane deltas versus the baseline")
def step_then_rank_and_deltas(context):
    for candidate in context.compare_report["candidates"]:
        assert isinstance(candidate.get("rank"), int)
        deltas = candidate.get("alwaysLaneDeltas") or {}
        assert "arrays" in deltas
        assert "kinds" in deltas
        assert "density" in deltas
        assert "unsupported_claims" in deltas["arrays"]


@then("no candidate is omitted because it lost")
def step_then_no_omission(context):
    ids = {item["id"] for item in context.compare_report["candidates"]}
    expected = {path.stem for path in context.candidate_paths}
    assert ids == expected


@then("none of the candidate files are modified")
def step_then_candidates_unmodified(context):
    for path, digest in context.candidate_digests.items():
        assert _file_digest(path) == digest


@then("the candidate is not rank 1")
def step_then_not_rank_one(context):
    bad = next(item for item in context.compare_report["candidates"] if item["id"] == "unsupported")
    assert bad["rank"] != 1


@then("the report names the unsupported-claim increase")
def step_then_names_increase(context):
    bad = next(item for item in context.compare_report["candidates"] if item["id"] == "unsupported")
    violations = bad.get("hardConstraintViolations") or []
    assert violations
    violation = violations[0]
    assert violation.get("constraint") == "unsupported_claims_increase"
    assert violation.get("delta", 0) > 0


@then("detector score is not an input")
def step_then_no_detector_score(context):
    rendered = json.dumps(context.compare_report).lower()
    assert "detector" not in rendered
    assert "ai_score" not in rendered
    assert "weights" not in context.compare_report


@then("the report includes always-lane deltas")
def step_then_regression_deltas(context):
    working = context.compare_report["candidates"][0]
    deltas = working.get("alwaysLaneDeltas") or {}
    assert "arrays" in deltas
    assert "kinds" in deltas


@then("optional rubric deltas if a judge is configured")
def step_then_optional_rubric(context):
    working = context.compare_report["candidates"][0]
    assert "rubricDeltas" in working
    if context.style_profile.profile.judge is None:
        assert working["rubricDeltas"] is None


@then("both files are unchanged")
def step_then_regression_files_unchanged(context):
    assert _file_digest(context.original_path) == context.original_digest
    assert _file_digest(context.working_path) == context.working_digest
