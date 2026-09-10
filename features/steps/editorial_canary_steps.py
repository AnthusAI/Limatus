from __future__ import annotations

import os
import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
MANIFEST = REPO_ROOT / "features" / "fixtures" / "editorial-canary" / "manifest.yml"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_canary import run_canary  # noqa: E402

DENSITY_ALWAYS_LANE_KINDS = frozenset({"low_lexical_density", "high_compressibility"})


@given("the canary fixture drafts")
def step_given_canary_fixture_drafts(context):
    assert MANIFEST.is_file(), MANIFEST
    context.canary_manifest = MANIFEST


@given("the canary judge mode is fixture")
def step_given_canary_judge_mode_fixture(context):
    context.canary_judge_mode = "fixture"


@given("the canary judge mode is live")
def step_given_canary_judge_mode_live(context):
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        context.scenario.skip("OPENAI_API_KEY not set; live canary is optional")
    context.canary_judge_mode = "live"


@when("the eval runner scans them with the configured judge fake or live")
def step_when_run_canary_judge(context):
    # CI uses the manifest fixture judge; live mode is available via context.canary_judge_mode.
    judge_mode = getattr(context, "canary_judge_mode", "fixture")
    code, report, lines = run_canary(context.canary_manifest, judge_mode=judge_mode)
    context.canary_exit_code = code
    context.canary_report = report
    context.canary_lines = lines


@then("each result records promptVersion and model")
def step_then_each_result_records_provenance(context):
    assert context.canary_exit_code == 0, "\n".join(context.canary_lines)
    results = context.canary_report.get("results", [])
    assert results, "expected canary results"
    for result in results:
        judge = result.get("judge") or {}
        assert isinstance(judge.get("promptVersion"), str) and judge["promptVersion"].strip()
        assert isinstance(judge.get("model"), str) and judge["model"].strip()


@then("house-voice canary drafts do not gain density flags on the always-lane")
def step_then_house_voice_no_density_flags(context):
    house = next(
        (item for item in context.canary_report.get("results", []) if item.get("entryId") == "house-voice"),
        None,
    )
    assert house is not None, "missing house-voice canary result"
    kinds = set(house.get("alwaysLaneKinds", []))
    overlap = kinds & DENSITY_ALWAYS_LANE_KINDS
    assert not overlap, f"unexpected density kinds on house-voice: {sorted(overlap)}"
