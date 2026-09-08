from __future__ import annotations

import sys
from pathlib import Path

from behave import given, then, when

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_ROOT = REPO_ROOT / "features" / "fixtures" / "editorial-surface-rules"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from limatus.editorial_diagnosis import diagnose_draft  # noqa: E402
from limatus.editorial_style import load_style_profile  # noqa: E402

PROFILE_PATH = FIXTURE_ROOT / "style-profile.yml"


@given("a draft containing an emoji character")
def step_given_draft_with_emoji(context):
    context.draft_text = "Shipping this today \U0001F680 and it feels great."


@given('a draft with two "X, not Y" contrast constructions')
def step_given_draft_with_two_contrasts(context):
    context.draft_text = (
        "This is about specifics, not hype. It is about evidence, not vibes. "
        "Every claim here is checkable against a real system."
    )


@when("I diagnose it with the surface-rules profile")
def step_when_diagnose_default_surface(context):
    style_profile = load_style_profile(PROFILE_PATH)
    context.diagnosis = diagnose_draft(context.draft_text, style_profile=style_profile)


@when('I diagnose it with the surface-rules profile for the "{surface}" surface')
def step_when_diagnose_with_surface(context, surface):
    style_profile = load_style_profile(PROFILE_PATH)
    context.diagnosis = diagnose_draft(context.draft_text, style_profile=style_profile, surface=surface)


def _all_findings(diagnosis):
    findings = list(diagnosis.get("generic_passages", []))
    findings += diagnosis.get("unsupported_claims", [])
    findings += diagnosis.get("voice_observations", [])
    findings += diagnosis.get("required_facts", [])
    return findings


@then("diagnosis reports a finding about the emoji")
def step_then_reports_emoji_finding(context):
    findings = _all_findings(context.diagnosis)
    assert any("emoji" in finding["rationale"].lower() for finding in findings), findings


@then("diagnosis reports a contrast cap finding")
def step_then_reports_contrast_cap_finding(context):
    findings = _all_findings(context.diagnosis)
    assert any("contrast construction" in finding["rationale"].lower() for finding in findings), findings


@then("diagnosis reports no contrast cap finding")
def step_then_reports_no_contrast_cap_finding(context):
    findings = _all_findings(context.diagnosis)
    assert not any("contrast construction" in finding["rationale"].lower() for finding in findings), findings
