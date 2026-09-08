from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
MANIFEST = REPO_ROOT / "features/fixtures/editorial-diagnosis/editorial-corpus/manifest.yml"


@given("the checked-in editorial eval manifest")
def step_given_eval_manifest(context):
    context.eval_manifest = MANIFEST


@given("a temporary eval manifest expecting a missing finding kind")
def step_given_regressed_manifest(context):
    context.temp_dir = tempfile.TemporaryDirectory()
    root = Path(context.temp_dir.name)
    context.eval_manifest = root / "manifest.yml"
    # Keep all paths portable while changing only the expected behavior.
    context.eval_manifest.write_text(
        "schemaVersion: 1\n"
        f"profile: {MANIFEST.parent.parent / 'style-profile.yml'}\n"
        "mustFail:\n"
        "  - id: regression\n"
        f"    path: {MANIFEST.parent.parent / 'must-fail/brochure-hedges.md'}\n"
        "    expectKinds: [not_a_real_finding]\n"
        "    expectTerms: [game-changing]\n"
        "mustPass: []\n",
        encoding="utf-8",
    )


@when("I run the offline eval command")
def step_when_run_eval(context):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = f"{SRC_ROOT}:{REPO_ROOT}"
    context.eval_result = subprocess.run(
        [sys.executable, "-m", "limatus.cli", "eval", "--manifest", str(context.eval_manifest)],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@then("the offline eval exits successfully")
def step_then_eval_succeeds(context):
    assert context.eval_result.returncode == 0, context.eval_result.stderr


@then("it reports pass and fail corpus coverage")
def step_then_eval_coverage(context):
    assert "PASS mustFail/brochure-hedges" in context.eval_result.stdout
    assert "PASS mustPass/latency-and-repo" in context.eval_result.stdout
    assert "offline eval: 2 passed, 0 failed" in context.eval_result.stdout


@then("the offline eval exits with a regression failure")
def step_then_eval_fails(context):
    assert context.eval_result.returncode != 0
    assert "FAIL mustFail/regression" in context.eval_result.stdout
    assert "offline eval: 0 passed, 1 failed" in context.eval_result.stdout
