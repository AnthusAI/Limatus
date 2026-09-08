from __future__ import annotations

import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
PROFILE = REPO_ROOT / "features/fixtures/editorial-diagnosis/style-profile.yml"


def _verify(context):
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from limatus.editorial_style import load_style_profile
    from limatus.editorial_verifier import verify_revision

    return verify_revision(
        context.original,
        context.working,
        style_profile=load_style_profile(PROFILE),
    )


@given("an original draft and an explicitly applied working draft")
def step_given_improved_revision(context):
    context.original = "In today's tools, everyone knows this is transformative."
    context.working = "Inspect latency and cost before choosing a model."
    context.original_snapshot = context.original
    context.working_snapshot = context.working


@given("a working draft with a new unsupported claim or a factual-change risk")
def step_given_riskier_revision(context):
    context.original = "Inspect latency and cost before choosing a model."
    context.working = "This model is always 10x faster and eliminates every failure."
    context.original_snapshot = context.original
    context.working_snapshot = context.working


@when("an operator runs verification with local style rules")
def step_when_verify_with_profile(context):
    context.verification = _verify(context)


@when("an operator runs verification")
def step_when_verify(context):
    context.verification = _verify(context)


@then("Limatus reports quality dimensions and evidence-backed findings")
def step_then_dimensions_and_findings(context):
    assert {"specificity", "clarity", "audience_fit", "voice_match"} <= set(context.verification["dimensions"])
    assert isinstance(context.verification["findings"], list)
    assert "weights" in context.verification


@then("it recommends acceptance only when the threshold is met and unsupported claims have not increased")
def step_then_acceptance_gate(context):
    result = context.verification
    assert result["recommendation"] == "accept"
    assert result["net_improvement"] >= result["threshold"]
    assert result["unsupported_claims"]["working"] <= result["unsupported_claims"]["original"]


@then("neither draft is changed")
def step_then_drafts_unchanged(context):
    assert context.original == context.original_snapshot
    assert context.working == context.working_snapshot


@then("Limatus advises against acceptance")
def step_then_reject(context):
    assert context.verification["recommendation"] == "reject"


@then("it does not publish or modify either draft")
def step_then_no_publish_or_modify(context):
    assert context.original == context.original_snapshot
    assert context.working == context.working_snapshot
    assert "published" not in context.verification
    assert "revised_text" not in context.verification
